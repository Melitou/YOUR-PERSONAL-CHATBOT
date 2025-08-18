import os
import json
import logging
from datetime import datetime, timedelta
from typing import List
from pydantic import BaseModel
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, status, Depends, UploadFile, File, Form, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.websockets import WebSocket, WebSocketDisconnect

from api_models import (
    CreateAgentRequest, CreateAgentResponse, LoginRequest, LoginResponse,
    SigninRequest, SigninResponse, UserResponse, ErrorResponse,
    ChunkingMethod, EmbeddingModel, AgentProvider, ChatbotDetailResponse,
    CreateSessionRequest, CreateSessionResponse, ChatMessageRequest, ChatMessageResponse, ConversationMessagesResponse, ConversationSummary
)
from auth_utils import (
    authenticate_user, create_user, create_access_token, verify_token,
    check_user_exists, get_user_by_username
)
from pipeline_handler import PipelineHandler
from db_service import initialize_db, User_Auth_Table

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global pipeline handler
pipeline_handler = None

# Global shared embedding service instance to avoid repeated Pinecone client initialization
shared_embedding_service = None

# Security
security = HTTPBearer()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    global pipeline_handler, shared_embedding_service

    # Startup
    logger.info("Starting FastAPI RAG Pipeline Server...")

    try:
        # Initialize database
        client, db, fs = initialize_db()
        if client is None or db is None or fs is None:
            raise Exception("Failed to initialize database")

        # Initialize pipeline handler
        pipeline_handler = PipelineHandler()
        logger.info("✅ Pipeline handler initialized")

        # Initialize shared embedding service to avoid repeated Pinecone client initialization
        from embeddings import EmbeddingService
        shared_embedding_service = EmbeddingService()
        logger.info("✅ Shared embedding service initialized")

        logger.info("🚀 FastAPI server ready!")

    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        raise

    yield  # Server runs here

    # Shutdown
    logger.info("Shutting down FastAPI server...")
    if pipeline_handler:
        pipeline_handler.close()
    logger.info("✅ Shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="RAG Chatbot Pipeline API",
    description="API for creating AI agents with document processing and embedding generation",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Dependency to get current user from JWT token
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User_Auth_Table:
    """Get current user from JWT token"""
    try:
        payload = verify_token(credentials.credentials)
        username = payload.get("sub")

        user = get_user_by_username(username)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )

        return user
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


def user_to_response(user: User_Auth_Table) -> UserResponse:
    """Convert User_Auth_Table to UserResponse"""
    return UserResponse(
        id=str(user.id),
        user_name=user.user_name,
        first_name=user.first_name,
        last_name=user.last_name,
        email=user.email,
        created_at=user.created_at,
        role=user.role if user.role else "User"  # Default to "User" if role is None
    )


class CheckDocumentsRequest(BaseModel):
    hashes: List[str]


class ExistingDocumentInfo(BaseModel):
    hash: str
    file_name: str
    namespace: str
    chatbots: List[str]


class CheckDocumentsResponse(BaseModel):
    duplicates: List[ExistingDocumentInfo]


@app.post("/documents/check-exists", response_model=CheckDocumentsResponse, tags=["Documents"])
async def check_documents_exists(request: CheckDocumentsRequest, current_user: User_Auth_Table = Depends(get_current_user)):
    """Check which of the provided SHA256 hashes already exist for the current user.

    Returns matching document info and the chatbots they are mapped to.
    """
    try:
        from db_service import Documents, ChatbotDocumentsMapper, ChatBots
        user = current_user
        docs = Documents.objects(user=user, full_hash__in=request.hashes)
        duplicates: List[ExistingDocumentInfo] = []
        for doc in docs:
            mappings = ChatbotDocumentsMapper.objects(document=doc, user=user)
            chatbot_names = []
            for m in mappings:
                try:
                    chatbot = ChatBots.objects(id=m.chatbot.id).first()
                    if chatbot:
                        chatbot_names.append(chatbot.name)
                except Exception:
                    continue
            duplicates.append(ExistingDocumentInfo(
                hash=doc.full_hash,
                file_name=doc.file_name,
                namespace=doc.namespace,
                chatbots=chatbot_names
            ))
        return CheckDocumentsResponse(duplicates=duplicates)
    except Exception as e:
        logger.error(f"Error checking document existence: {e}")
        raise HTTPException(
            status_code=500, detail="Error checking document existence")


class ChatbotHealthResponse(BaseModel):
    chatbot_id: str
    name: str
    namespace: str
    provider: str
    embedding_model: str
    pinecone_index: str
    pinecone_vectors: int
    mongo_chunks_total: int
    mongo_embedded: int
    ready: bool


@app.get("/chatbots/{chatbot_id}/health", response_model=ChatbotHealthResponse, tags=["Chatbot"])
async def get_chatbot_health(chatbot_id: str, current_user: User_Auth_Table = Depends(get_current_user)):
    """Return Pinecone/Mongo readiness for a chatbot's namespace."""
    try:
        from bson import ObjectId
        from db_service import ChatBots, Documents, Chunks, ChatbotDocumentsMapper

        chatbot = ChatBots.objects(id=ObjectId(
            chatbot_id), user_id=current_user).first()
        if not chatbot:
            raise HTTPException(status_code=404, detail="Chatbot not found")

        # Use shared embedding service instance to avoid repeated Pinecone client initialization
        global shared_embedding_service
        es = shared_embedding_service
        pinecone_index = es.get_pinecone_index_for_model(
            chatbot.embedding_model)
        # Derive provider from embedding model (ChatBots has no explicit provider field)
        emb = (chatbot.embedding_model or "").lower()
        provider_str = "google" if (
            "gemini" in emb or "google" in emb) else "openai"

        # Pinecone vectors count for this namespace
        vectors = 0
        try:
            if es.initialize_pinecone_client():
                idx = es.pinecone_client.Index(pinecone_index)
                stats = idx.describe_index_stats(
                    filter=None, namespace=chatbot.namespace)
                ns = stats.get("namespaces", {}).get(chatbot.namespace, {})
                vectors = int(ns.get("vector_count", 0))
        except Exception:
            vectors = 0

        # Mongo counts for this chatbot via mapping
        mapped_docs = ChatbotDocumentsMapper.objects(
            chatbot=chatbot, user=current_user).only('document')
        doc_ids = [m.document.id for m in mapped_docs]
        if doc_ids:
            # Chunks are stored once per document (not per-namespace). For health, compare
            # Pinecone namespace vector count against total chunks of mapped documents.
            total_chunks = Chunks.objects(document__in=doc_ids).count()
            embedded_chunks = Chunks.objects(
                document__in=doc_ids, vector_id__ne=None).count()
        else:
            total_chunks = 0
            embedded_chunks = 0

        # Ready when Pinecone namespace has vectors for all chunks
        ready = total_chunks > 0 and vectors == total_chunks

        return ChatbotHealthResponse(
            chatbot_id=str(chatbot.id),
            name=chatbot.name,
            namespace=chatbot.namespace,
            provider=provider_str,
            embedding_model=chatbot.embedding_model,
            pinecone_index=pinecone_index,
            pinecone_vectors=vectors,
            mongo_chunks_total=total_chunks,
            mongo_embedded=embedded_chunks,
            ready=ready,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error computing chatbot health: {e}")
        raise HTTPException(
            status_code=500, detail="Error computing chatbot health")


@app.get("/", tags=["Health"])
async def root():
    """Health check endpoint"""
    return {
        "message": "RAG Chatbot Pipeline API",
        "status": "running",
        "timestamp": datetime.now().isoformat()
    }


@app.post("/login", response_model=LoginResponse, tags=["Authentication"])
async def login(request: LoginRequest):
    """Authenticate user and return JWT token"""
    try:
        # Authenticate user
        user = authenticate_user(request.username, request.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Create access token
        access_token_expires = timedelta(minutes=30)
        access_token = create_access_token(
            data={"sub": user.user_name},
            expires_delta=access_token_expires
        )

        logger.info(f"User logged in: {user.user_name}")

        return LoginResponse(
            access_token=access_token,
            token_type="bearer",
            user=user_to_response(user)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during login: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during login"
        )


@app.post("/signup", response_model=SigninResponse, tags=["Authentication"])
async def signup(request: SigninRequest):
    """Register a new user"""
    try:
        # Check if user already exists
        if check_user_exists(username=request.user_name, email=request.email):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User with this username or email already exists"
            )

        # Create user data
        user_data = {
            "user_name": request.user_name,
            "password": request.password,
            "first_name": request.first_name,
            "last_name": request.last_name,
            "email": request.email,
            "role": request.role
        }

        # Create user
        user = create_user(user_data)

        logger.info(
            f"New user registered: {user.user_name} with role: {request.role}")

        return SigninResponse(
            message="User registered successfully",
            user=user_to_response(user)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during user registration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during registration"
        )


@app.post("/create_agent", response_model=CreateAgentResponse, tags=["Agent Management"])
async def create_agent(
    # Form fields
    agent_provider: str = Form(
        None, description="Agent provider: 'Gemini', 'OpenAI', or null for super user"),
    chunking_method: str = Form(
        None, description="Chunking method (super users only)"),
    embedding_model: str = Form(
        None, description="Embedding model (super users only)"),
    agent_description: str = Form(..., description="Description of the agent"),
    user_namespace: str = Form(
        ..., description="Namespace prefix for the chatbot (no underscores, max 50 chars)"),
    # Files
    files: List[UploadFile] = File(...,
                                   description="Documents to process (PDF, DOCX, TXT, CSV)"),
    # Authentication
    current_user: User_Auth_Table = Depends(get_current_user)
):
    """Create a new agent with document processing and embedding generation"""
    try:

        # Log the request
        logger.info(f"\n\n\nCreating agent for user: {current_user.user_name}")
        logger.info(f"Agent description: {agent_description}")
        logger.info(f"User namespace: {user_namespace}")
        logger.info(f"Chunking method: {chunking_method}")
        logger.info(f"Embedding model: {embedding_model}")
        logger.info(f"Agent provider: {agent_provider}")
        logger.info(f"Files: {files}\n\n")

        # Validate and convert form inputs
        agent_provider_enum = None
        if agent_provider and agent_provider.strip():
            try:
                agent_provider_enum = AgentProvider(agent_provider.strip())
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid agent provider. Must be one of: {[e.value for e in AgentProvider]}"
                )

        chunking_method_enum = None
        if chunking_method and chunking_method.strip():
            try:
                chunking_method_enum = ChunkingMethod(chunking_method.strip())
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid chunking method. Must be one of: {[e.value for e in ChunkingMethod]}"
                )

        embedding_model_enum = None
        if embedding_model and embedding_model.strip():
            try:
                embedding_model_enum = EmbeddingModel(embedding_model.strip())
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid embedding model. Must be one of: {[e.value for e in EmbeddingModel]}"
                )

        # Validate business logic
        is_super_user = agent_provider_enum is None

        if not is_super_user:
            # Normal user - chunking_method and embedding_model should be null
            if chunking_method_enum is not None or embedding_model_enum is not None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Normal users cannot specify chunking_method or embedding_model"
                )

        # Validate user_namespace
        if '_' in user_namespace:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Namespace cannot contain underscores (used for user ID separation)"
            )

        if len(user_namespace) > 50:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Namespace prefix too long (max 50 characters)"
            )

        if not user_namespace.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Namespace cannot be empty"
            )

        # Use the authenticated user (no need to create a new user)
        user = current_user

        logger.info(
            f"Creating agent for user: {user.user_name} (Super User: {is_super_user})")

        # Process agent creation
        results = await pipeline_handler.process_agent_creation(
            user=user,
            files=files,
            agent_description=agent_description,
            user_namespace=user_namespace,
            chunking_method=chunking_method_enum,
            embedding_model=embedding_model_enum,
            agent_provider=agent_provider_enum
        )

        # Create response
        response = CreateAgentResponse(
            success=results['success'],
            message=results['message'],
            user=user_to_response(user),
            namespace=results['namespace'],
            processing_results=results.get('processing_results'),
            embedding_results=results.get('embedding_results'),
            total_time=results['total_time']
        )

        if results['success']:
            logger.info(
                f"✅ Agent created successfully for user {user.user_name}")
        else:
            logger.warning(
                f"⚠️ Agent creation completed with issues for user {user.user_name}")

        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating agent: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@app.get("/chatbots", response_model=List[ChatbotDetailResponse], tags=["Chatbot"])
async def get_user_chatbots(current_user: User_Auth_Table = Depends(get_current_user)):
    """Get all chatbots for a user with detailed information including loaded files"""
    try:
        chatbots = pipeline_handler.get_user_chatbots(str(current_user.id))
        logger.info(
            f"Retrieved {len(chatbots)} chatbots for user {current_user.user_name}")
        return chatbots
    except Exception as e:
        logger.error(
            f"Error retrieving chatbots for user {current_user.user_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving chatbots"
        )


@app.get("/chatbot/{chatbot_id}/conversations", response_model=List[ConversationSummary], tags=["Conversation"])
async def get_chatbot_conversations(chatbot_id: str, current_user: User_Auth_Table = Depends(get_current_user)):
    """Get all conversations for a chatbot"""
    try:
        conversations = pipeline_handler.get_chatbot_conversations(
            chatbot_id, str(current_user.id))
        logger.info(
            f"Retrieved {len(conversations)} conversations for user {current_user.user_name}")
        return conversations
    except Exception as e:
        logger.error(
            f"Error retrieving conversations for chatbot {chatbot_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving conversations"
        )


@app.post("/chatbot/{chatbot_id}/conversation/new", response_model=CreateSessionResponse, tags=["Conversation Session"])
async def create_new_conversation_with_session(
    chatbot_id: str,
    current_user: User_Auth_Table = Depends(get_current_user)
):
    """Create a new conversation and session for a chatbot"""
    try:
        session_response = pipeline_handler.create_new_conversation_with_session(
            str(current_user.id), chatbot_id)
        logger.info(
            f"Created new conversation session {session_response.session_id} for user {current_user.user_name}")
        return session_response
    except Exception as e:
        logger.error(
            f"Error creating new conversation session for chatbot {chatbot_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating new conversation session"
        )


@app.post("/chatbot/{chatbot_id}/conversation/{conversation_id}/session", response_model=CreateSessionResponse, tags=["Conversation Session"])
async def create_conversation_session(
    chatbot_id: str,
    conversation_id: str,
    current_user: User_Auth_Table = Depends(get_current_user)
):
    """Create a new conversation session"""
    try:
        session_response = pipeline_handler.create_conversation_session(
            str(current_user.id), chatbot_id, conversation_id)
        logger.info(
            f"Created conversation session {session_response.session_id} for user {current_user.user_name}")
        return session_response
    except Exception as e:
        logger.error(
            f"Error creating conversation session for chatbot {chatbot_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating conversation session"
        )


async def authenticate_websocket(websocket: WebSocket, token: str) -> User_Auth_Table:
    """Authenticate WebSocket connection using JWT token"""
    try:
        payload = verify_token(token)
        username = payload.get("sub")

        user = get_user_by_username(username)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )

        return user
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token"
        )


@app.websocket("/ws/conversation/session/{session_id}")
async def websocket_conversation(websocket: WebSocket, session_id: str):
    """Handle WebSocket conversation session with streaming responses"""
    user = None
    session = None

    # Extract token from query params (WebSocket routes do not support Query(...) parameters)
    token = websocket.query_params.get("token")
    logger.info(
        f"WebSocket connection attempt for session {session_id} with token: {str(token)[:20]}...")

    if not token:
        # Must accept the websocket before we can close it gracefully
        try:
            await websocket.accept()
        except Exception:
            return
        await safe_websocket_close(websocket, code=1008, reason="Unauthorized")
        return

    # Accept connection FIRST (required for WebSocket)
    try:
        await websocket.accept()
        logger.info("WebSocket connection accepted")
    except Exception as e:
        logger.error(f"Failed to accept WebSocket connection: {e}")
        return

    # Then authenticate user
    try:
        user = await authenticate_websocket(websocket, token)
        logger.info(f"User authenticated: {user.user_name} (ID: {user.id})")
    except HTTPException as e:
        logger.error(f"WebSocket authentication failed: {e.detail}")
        await safe_websocket_close(websocket, code=1008, reason="Unauthorized")
        return
    except Exception as e:
        logger.error(f"WebSocket authentication error: {e}")
        await safe_websocket_close(websocket, code=1008, reason="Authentication error")
        return

    try:
        # Validate session belongs to user
        logger.info(f"Validating session {session_id} for user {user.id}")
        session = pipeline_handler.get_conversation_session(
            session_id, str(user.id))
        if not session:
            logger.error(
                f"Session not found or does not belong to user for session {session_id}")
            await safe_websocket_close(websocket, code=1008, reason="Session not found")
            return
        logger.info(f"Session found: {session.session_id}")

        # Get the actual chatbot object from the session
        from db_service import ChatBots
        chatbot = ChatBots.objects(
            id=session.chatbot_id.id, user_id=user.id).first()
        if not chatbot:
            logger.error(f"Chatbot not found for session {session_id}")
            await safe_websocket_close(websocket, code=1008, reason="Chatbot not found")
            return

        logger.info(f"Chatbot found: {chatbot.name}")

        logger.info(
            f"WebSocket connected for session {session_id}, user {user.user_name}, chatbot {chatbot.name}")

        if not chatbot:
            await safe_websocket_close(websocket, code=1008, reason="Chatbot not found")
            return

        # Send initial session info
        await safe_websocket_send(websocket, {
            "type": "session_info",
            "session_id": session_id,
            "chatbot_name": chatbot.name,
            "message": f"Connected to {chatbot.name}. You can start chatting!"
        })

        while True:
            # Receive message from client
            try:
                data = await websocket.receive_text()
                message_data = json.loads(data)

                user_message = message_data.get("message", "").strip()
                if not user_message:
                    await safe_websocket_send(websocket, {
                        "type": "error",
                        "message": "Empty message received"
                    })
                    continue

                # Save user message to database
                user_msg_record = pipeline_handler.save_message_to_session(
                    session_id, user_message, "user"
                )

                # Send acknowledgment
                await safe_websocket_send(websocket, {
                    "type": "message_received",
                    "message_id": str(user_msg_record.id),
                    "timestamp": user_msg_record.created_at.isoformat()
                })

                # Initialize RAG for this chatbot
                from LLM.rag_llm_call import initialize_rag_config, ask_rag_assistant_stream

                logger.info(
                    f"Initializing RAG with user_id={str(user.id)}, namespace={chatbot.namespace}, embedding_model={chatbot.embedding_model}")

                # OPTIMIZATION: Use only chatbot's own namespace to avoid 500k token queries
                # Each chatbot now contains duplicated chunks in its own namespace
                # This eliminates the need to query multiple namespaces and reduces tokens by 90%
                chatbot_namespace = chatbot.namespace
                logger.info(
                    f"Using single namespace for RAG: {chatbot_namespace}")

                initialize_rag_config(
                    user_id=str(user.id),
                    namespaces=[chatbot_namespace],  # Single namespace only
                    embedding_model=chatbot.embedding_model
                )

                # Get conversation history for context
                from db_service import Messages, Conversation
                messages = Messages.objects(
                    conversation_id=session.conversation_id).order_by('created_at')

                # Build history for RAG
                # RAG system expects format: [{"user": "...", "assistant": "..."}, ...]
                history = []
                # Get more messages to form pairs
                recent_messages = list(messages)[-20:]

                # Group messages into user-assistant pairs
                i = 0
                while i < len(recent_messages) - 1:  # Exclude current message
                    current_msg = recent_messages[i]
                    next_msg = recent_messages[i + 1] if i + \
                        1 < len(recent_messages) else None

                    # Look for user-assistant pairs
                    if current_msg.role == "user" and next_msg and next_msg.role == "agent":
                        history.append({
                            "user": current_msg.message,
                            "assistant": next_msg.message
                        })
                        i += 2  # Skip both messages as we've processed them as a pair
                    else:
                        i += 1  # Move to next message

                # Keep only last 5 pairs
                history = history[-5:]

                logger.info(
                    f"Built conversation history with {len(history)} pairs for RAG")

                # Stream response from RAG assistant
                assistant_response = ""
                await safe_websocket_send(websocket, {
                    "type": "response_start",
                    "message": "Assistant is thinking..."
                })

                try:
                    async for event in ask_rag_assistant_stream(history, user_message):
                        if isinstance(event, dict):
                            event_type = event.get("type")

                            if event_type == "thinking_start":
                                await safe_websocket_send(websocket, {
                                    "type": "thinking_start",
                                    "message": event.get("message", "")
                                })

                            elif event_type == "thinking_step":
                                await safe_websocket_send(websocket, {
                                    "type": "thinking_step",
                                    "step": event.get("step", ""),
                                    "message": event.get("message", "")
                                })

                            elif event_type == "thinking_complete":
                                await safe_websocket_send(websocket, {
                                    "type": "thinking_complete",
                                    "message": event.get("message", "")
                                })

                            elif event_type == "response_chunk":
                                chunk = event.get("chunk", "")
                                if chunk.strip():
                                    assistant_response += chunk
                                    await safe_websocket_send(websocket, {
                                        "type": "response_chunk",
                                        "chunk": chunk
                                    })
                        else:
                            # Handle legacy string chunks for backward compatibility
                            if event.strip():
                                assistant_response += event
                                await safe_websocket_send(websocket, {
                                    "type": "response_chunk",
                                    "chunk": event
                                })

                except Exception as e:
                    logger.error(f"Error in RAG streaming: {e}")
                    await safe_websocket_send(websocket, {
                        "type": "error",
                        "message": "Error generating response. Please try again."
                    })
                    continue

                # Save assistant response to database
                if assistant_response.strip():
                    assistant_msg_record = pipeline_handler.save_message_to_session(
                        session_id, assistant_response, "agent"
                    )

                    # Send completion message
                    await safe_websocket_send(websocket, {
                        "type": "response_complete",
                        "message_id": str(assistant_msg_record.id),
                        "timestamp": assistant_msg_record.created_at.isoformat(),
                        "full_response": assistant_response
                    })

            except json.JSONDecodeError:
                await safe_websocket_send(websocket, {
                    "type": "error",
                    "message": "Invalid JSON format"
                })
            except WebSocketDisconnect:
                # Client disconnected normally
                logger.info(f"Client disconnected from session {session_id}")
                break
            except Exception as e:
                logger.error(
                    f"Error processing message in session {session_id}: {e}")
                await safe_websocket_send(websocket, {
                    "type": "error",
                    "message": "Error processing message. Please try again."
                })

    except HTTPException as e:
        logger.error(f"Session validation failed: {e.detail}")
        await safe_websocket_close(websocket, code=1008, reason=e.detail)
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for session {session_id}")
    except Exception as e:
        logger.error(
            f"Unexpected error in WebSocket for session {session_id}: {e}")
        await safe_websocket_close(websocket, code=1011, reason="Internal server error")
    finally:
        # Cleanup session if we have user info
        if user and session_id:
            try:
                pipeline_handler.close_conversation_session(
                    session_id, str(user.id))
            except Exception as e:
                logger.error(f"Error closing session in cleanup: {e}")


def _fetch_initial_documents_namespaces_for_current_chatbot(chatbot_id: str, user_id: str) -> list:
    """
    This function will find from the MongoDB the initial 
    namespaces that are assigned to the documents
    the chatbot is mapped to.
    Args:
        chatbot_id: The id of the chatbot that the user is in the socket connection
        user_id: The user id of the user that is in the socket connection and the chatbot is mapped to.
    Returns:
        A list of initial namespaces that are assigned to the documents the chatbot is mapped to.
    """
    try:
        from db_service import ChatbotDocumentsMapper, Documents
        from bson import ObjectId

        # Convert string IDs to ObjectId
        chatbot_object_id = ObjectId(chatbot_id)
        user_object_id = ObjectId(user_id)

        # Get the mapping records for this chatbot and user
        chatbot_documents_mapper_list = ChatbotDocumentsMapper.objects(
            chatbot=chatbot_object_id,
            user=user_object_id
        )

        if not chatbot_documents_mapper_list:
            logger.warning(
                f"No document mappings found for chatbot {chatbot_id}")
            return []

        # Extract document IDs from the mappings
        document_ids = [
            mapping.document.id for mapping in chatbot_documents_mapper_list]

        # Get the documents
        documents = Documents.objects(id__in=document_ids)
        if not documents:
            logger.warning(
                f"No documents found for document IDs: {document_ids}")
            return []

        # Extract unique namespaces
        unique_namespaces = list(set([doc.namespace for doc in documents]))

        logger.info(
            f"Found {len(unique_namespaces)} unique namespaces for chatbot {chatbot_id}: {unique_namespaces}")
        return unique_namespaces

    except Exception as e:
        logger.error(
            f"Error fetching initial document namespaces for chatbot {chatbot_id}: {e}")
        raise ValueError(
            f"Error fetching initial document namespaces for chatbot {chatbot_id}: {e}")


async def safe_websocket_send(websocket: WebSocket, data: dict) -> bool:
    """Safely send data via WebSocket, return True if successful"""
    try:
        if websocket.client_state.value == 1:  # CONNECTED state
            await websocket.send_text(json.dumps(data))
            return True
    except Exception as e:
        logger.debug(f"Failed to send WebSocket message: {e}")
    return False


async def safe_websocket_close(websocket: WebSocket, code: int = 1000, reason: str = "") -> bool:
    """Safely close WebSocket connection, return True if successful"""
    try:
        if websocket.client_state.value == 1:  # CONNECTED state
            await websocket.close(code=code, reason=reason)
            return True
    except Exception as e:
        logger.debug(f"Failed to close WebSocket: {e}")
    return False


@app.delete("/conversation/session/{session_id}", tags=["Conversation Session"])
async def close_conversation_session(
    session_id: str,
    current_user: User_Auth_Table = Depends(get_current_user)
):
    """Close/deactivate a conversation session"""
    try:
        pipeline_handler.close_conversation_session(
            session_id, str(current_user.id))
        return {"message": "Session closed successfully"}
    except Exception as e:
        logger.error(f"Error closing conversation session {session_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error closing conversation session"
        )


@app.post("/admin/cleanup-sessions", tags=["Admin"])
async def cleanup_inactive_sessions(
    hours: int = Query(24, description="Hours of inactivity before cleanup"),
    current_user: User_Auth_Table = Depends(get_current_user)
):
    """Cleanup inactive sessions (admin only)"""
    # You might want to add admin role check here
    try:
        pipeline_handler.cleanup_inactive_sessions(hours)
        return {"message": f"Cleaned up sessions inactive for more than {hours} hours"}
    except Exception as e:
        logger.error(f"Error cleaning up sessions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error cleaning up sessions"
        )


@app.get("/me", response_model=UserResponse, tags=["User"])
async def get_current_user_info(current_user: User_Auth_Table = Depends(get_current_user)):
    """Get current user information"""
    return user_to_response(current_user)


@app.post("/chatbots/{chatbot_id}/delete", tags=["Chatbot"])
async def delete_chatbot(chatbot_id: str, current_user: User_Auth_Table = Depends(get_current_user)):
    """Delete a chatbot and its Pinecone namespace; preserve shared documents."""
    try:
        from db_service import ChatBots, Conversation, Messages, ConversationSession, ChatbotDocumentsMapper
        from bson import ObjectId
        from embeddings import EmbeddingService

        chatbot = ChatBots.objects(id=ObjectId(
            chatbot_id), user_id=current_user).first()
        if not chatbot:
            raise HTTPException(status_code=404, detail="Chatbot not found")

        # Delete sessions, messages, conversations for this chatbot
        ConversationSession.objects(
            chatbot_id=chatbot, user_id=current_user).delete()
        conversations = Conversation.objects(chatbot=chatbot)
        if conversations:
            conv_ids = [c.id for c in conversations]
            Messages.objects(conversation_id__in=conv_ids).delete()
            conversations.delete()

        # Delete mapping rows (docs remain for other chatbots)
        ChatbotDocumentsMapper.objects(
            chatbot=chatbot, user=current_user).delete()

        # Delete Pinecone namespace
        es = EmbeddingService()
        index_name = es.get_pinecone_index_for_model(chatbot.embedding_model)
        es.delete_namespace(index_name, chatbot.namespace)

        # Delete the chatbot itself
        chatbot.delete()
        return {"deleted": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting chatbot {chatbot_id}: {e}")
        raise HTTPException(status_code=500, detail="Error deleting chatbot")


# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    """Handle HTTP exceptions"""
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "error_code": str(exc.status_code),
            "timestamp": datetime.now().isoformat()
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc: Exception):
    """Handle general exceptions"""
    from fastapi.responses import JSONResponse
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "error_code": "500",
            "timestamp": datetime.now().isoformat()
        }
    )


if __name__ == "__main__":
    import uvicorn

    # Get configuration from environment variables
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    reload = os.getenv("RELOAD", "true").lower() == "true"

    print("=" * 80)
    print("🚀 STARTING RAG CHATBOT PIPELINE API SERVER")
    print("=" * 80)
    print(f"📡 Host: {host}")
    print(f"🔌 Port: {port}")
    print(f"🔄 Reload: {reload}")
    print("=" * 80)

    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )
