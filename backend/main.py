import os
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict
from pydantic import BaseModel
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, status, Depends, UploadFile, File, Form, Query, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.websockets import WebSocket, WebSocketDisconnect

from api_models import (
    CreateAgentResponse, LoginRequest, LoginResponse,
    SigninRequest, SigninResponse, UserResponse,
    ChunkingMethod, EmbeddingModel, AgentProvider, ChatbotDetailResponse,
    CreateSessionResponse, ConversationSummary, ChatbotHealthResponse,
    CheckDocumentsRequest, CheckDocumentsResponse, ExistingDocumentInfo,
    EnhancementStatus, UpdateConversationRequest, UpdateConversationResponse,
    DeleteConversationResponse, EmailAssignmentRequest, EmailAssignmentResponse,
    ChatbotClientInfo
)
from auth_utils import (
    authenticate_user, create_user, create_access_token, verify_token,
    check_user_exists, get_user_by_username, get_password_hash
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


def validate_object_id(id_string: str) -> bool:
    """Validate that a string is a valid ObjectId format"""
    try:
        from bson import ObjectId
        from bson.errors import InvalidId
        ObjectId(id_string)
        return True
    except InvalidId:
        return False


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
    # allow_origins=["https://yourdomain.com"], # TODO: Add specific domains only
    allow_origins=["http://localhost:3000", "http://localhost:8000",
                   "http://127.0.0.1:3000", "http://127.0.0.1:8000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
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


def generate_random_password(length: int = 12) -> str:
    """Generate a random temporary password"""
    import string
    import secrets
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def send_welcome_email(email: str, temp_password: str, chatbot_name: str = ""):
    """Send welcome email to new client with login instructions"""
    try:
        subject = f"Welcome! You've been given access to {'a chatbot' if not chatbot_name else chatbot_name}"
        body = f"""
Hello!

You've been given access to {'a chatbot' if not chatbot_name else f'the chatbot "{chatbot_name}"'}. 

Here are your login credentials:
Email: {email}
Temporary Password: {temp_password}

Please log in and change your password as soon as possible.

Login at: {os.getenv('FRONTEND_URL', 'http://localhost:3000')}/auth

Best regards,
Your Chatbot Team
        """

        # TODO: Implement actual email sending using your preferred service
        # Example: SendGrid, AWS SES, etc.
        logger.info(f"Welcome email would be sent to {email}")
        print(f"Welcome email for {email}: {body}")

    except Exception as e:
        logger.error(f"Failed to send welcome email to {email}: {e}")
        # Don't fail the assignment if email fails
        pass


def validate_chatbot_access(user: User_Auth_Table, chatbot_id: str) -> bool:
    """Validate if user has access to chatbot based on their role"""
    logger.info(
        f"Validating chatbot access for user {user.user_name} (role: {user.role}) to chatbot {chatbot_id}")

    if user.role in ['User', 'Super User']:
        # Check if they own the chatbot (or Super User has access to all)
        if user.role == 'Super User':
            logger.info(
                f"Super User {user.user_name} granted access to chatbot {chatbot_id}")
            return True  # Super Users have access to all chatbots
        from db_service import ChatBots
        from bson import ObjectId
        try:
            chatbot = ChatBots.objects(id=ObjectId(
                chatbot_id), user_id=user.id).first()
            result = chatbot is not None
            logger.info(
                f"User {user.user_name} chatbot ownership check result: {result}")
            return result
        except Exception as e:
            logger.error(
                f"Error validating chatbot access for user {user.user_name}: {e}")
            return False
    elif user.role == 'Client':
        # Check if chatbot is assigned to them
        logger.info(
            f"Checking client assignment for user {user.user_name} to chatbot {chatbot_id}")
        from db_service import validate_client_chatbot_access
        result = validate_client_chatbot_access(str(user.id), chatbot_id)
        logger.info(f"Client assignment check result: {result}")
        return result

    logger.warning(f"Unknown role {user.role} for user {user.user_name}")
    return False


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


# ==============================================ENDPOINTS==============================================


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
    files: List[UploadFile] = File(..., max_size=10_000_000),  # 10MB limit
    # Authentication
    current_user: User_Auth_Table = Depends(get_current_user),
    use_basic_summaries: bool = Form(
        True, description="Use basic summaries instead of AI-enhanced summaries")
):
    """Create a new agent with document processing and embedding generation"""
    try:

        # TODO: DELETE THIS
        # For testing purposes, we will set use_basic_summaries to False to see the basic summaries
        use_basic_summaries = True

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
            agent_provider=agent_provider_enum,
            use_basic_summaries=use_basic_summaries
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


@app.post("/enhance_agent/{chatbot_id}", response_model=Dict[str, str], tags=["Agent Management"])
async def enhance_agent_summaries(
    chatbot_id: str,
    current_user: User_Auth_Table = Depends(get_current_user)
):
    """Start background enhancement of agent summaries using OpenAI Batch API"""
    try:
        from batch_enhancement_service import BatchEnhancementService
        from bson import ObjectId
        from db_service import ChatBots

        chatbot = ChatBots.objects(id=ObjectId(
            chatbot_id), user_id=current_user).first()
        if not chatbot:
            raise HTTPException(status_code=404, detail="Chatbot not found")

        service = BatchEnhancementService()
        batch_id = await service.start_enhancement_job(chatbot_id=chatbot_id, user_id=str(current_user.id))
        return {"batch_id": batch_id, "status": "submitted"}
    except HTTPException:
        raise
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(
            f"Error starting enhancement job for chatbot {chatbot_id}: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to start enhancement job")


@app.get("/enhancement_status/{chatbot_id}", response_model=EnhancementStatus, tags=["Agent Management"])
async def get_enhancement_status(
    chatbot_id: str,
    current_user: User_Auth_Table = Depends(get_current_user)
):
    """Get status of background enhancement job"""
    try:
        from bson import ObjectId
        from db_service import ChatBots, BatchSummarizationJob
        from api_models import EnhancementStatus, BatchJobStatus

        chatbot = ChatBots.objects(id=ObjectId(
            chatbot_id), user_id=current_user).first()
        if not chatbot:
            raise HTTPException(status_code=404, detail="Chatbot not found")

        job = BatchSummarizationJob.objects(
            chatbot=chatbot, user=current_user).order_by('-created_at').first()
        if not job:
            raise HTTPException(
                status_code=404, detail="No enhancement job found for this chatbot")

        return EnhancementStatus(
            batch_id=job.batch_id,
            status=BatchJobStatus(job.status),
            total_requests=job.total_requests,
            request_counts=job.request_counts_by_status or {},
            created_at=job.created_at,
            completed_at=job.completed_at
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error retrieving enhancement status for chatbot {chatbot_id}: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to retrieve enhancement status")


@app.post("/webhooks/openai/batch", tags=["Webhooks"])
async def openai_batch_webhook(request: Request):
    """Handle OpenAI batch completion webhooks"""
    try:
        from webhook_handlers import WebhookHandler

        body = await request.body()
        signature = (
            request.headers.get('OpenAI-Signature') or
            request.headers.get('OpenAI-Signature-256') or
            request.headers.get('x-openai-signature') or
            request.headers.get('X-OpenAI-Signature') or
            ''
        )

        webhook_secret = os.getenv('OPENAI_WEBHOOK_SECRET', '')
        if not webhook_secret:
            logger.warning(
                "OPENAI_WEBHOOK_SECRET not set; rejecting webhook for safety")
            raise HTTPException(
                status_code=401, detail="Webhook not configured")

        handler = WebhookHandler(webhook_secret)
        if not handler.verify_webhook_signature(body, signature):
            raise HTTPException(status_code=401, detail="Invalid signature")

        try:
            event_data = await request.json()
        except Exception:
            event_data = json.loads(body.decode('utf-8'))

        result = await handler.handle_batch_event(event_data)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error handling OpenAI webhook: {e}")
        raise HTTPException(status_code=500, detail="Webhook processing error")


@app.get("/notifications", response_model=List[Dict], tags=["User Management"])
async def get_user_notifications(
    current_user: User_Auth_Table = Depends(get_current_user),
    unread_only: bool = False
):
    """Get user notifications"""
    try:
        from notification_service import NotificationService

        notifications = NotificationService.get_user_notifications(
            current_user, unread_only)
        response: List[Dict] = []
        for n in notifications:
            response.append({
                "id": str(n.id),
                "type": n.notification_type,
                "title": n.title,
                "message": n.message,
                "is_read": bool(getattr(n, 'is_read', False)),
                "created_at": n.created_at.isoformat() if getattr(n, 'created_at', None) else None,
                "read_at": n.read_at.isoformat() if getattr(n, 'read_at', None) else None,
                "chatbot_id": str(n.chatbot.id) if getattr(n, 'chatbot', None) else None,
                "batch_id": n.batch_job.batch_id if getattr(n, 'batch_job', None) else None,
            })
        return response
    except Exception as e:
        logger.error(f"Error fetching user notifications: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to fetch notifications")


@app.get("/chatbots", response_model=List[ChatbotDetailResponse], tags=["Chatbot"])
async def get_user_chatbots(current_user: User_Auth_Table = Depends(get_current_user)):
    """Get chatbots for current user based on role"""
    try:
        if current_user.role == 'Client':
            # Clients see only assigned chatbots
            from db_service import get_client_assigned_chatbots, ChatbotDocumentsMapper, Chunks
            chatbots = get_client_assigned_chatbots(str(current_user.id))

            result = []
            for chatbot in chatbots:
                # Get loaded files for this chatbot
                chatbot_docs = ChatbotDocumentsMapper.objects(chatbot=chatbot)
                loaded_files = []
                total_chunks = 0

                for mapping in chatbot_docs:
                    doc = mapping.document

                    # Count chunks for this document
                    chunk_count = Chunks.objects(document=doc).count()
                    total_chunks += chunk_count

                    loaded_files.append({
                        "file_name": doc.file_name,
                        "file_type": doc.file_type,
                        "status": doc.status,
                        "upload_date": doc.created_at,
                        "total_chunks": chunk_count
                    })

                result.append(ChatbotDetailResponse(
                    id=str(chatbot.id),
                    name=chatbot.name,
                    description=chatbot.description,
                    embedding_model=chatbot.embedding_model,
                    chunking_method=chatbot.chunking_method,
                    date_created=chatbot.date_created,
                    namespace=chatbot.namespace,
                    loaded_files=loaded_files,
                    total_files=len(loaded_files),
                    total_chunks=total_chunks
                ))

            logger.info(
                f"Retrieved {len(result)} assigned chatbots for client {current_user.user_name}")
            return result

        elif current_user.role == 'User':
            # Users see owned chatbots
            chatbots = pipeline_handler.get_user_chatbots(str(current_user.id))
            logger.info(
                f"Retrieved {len(chatbots)} owned chatbots for user {current_user.user_name}")
            return chatbots

        elif current_user.role == 'Super User':
            # Super Users see all chatbots
            from db_service import ChatBots, ChatbotDocumentsMapper, Chunks
            all_chatbots = ChatBots.objects()

            result = []
            for chatbot in all_chatbots:
                # Get loaded files for this chatbot
                chatbot_docs = ChatbotDocumentsMapper.objects(chatbot=chatbot)
                loaded_files = []
                total_chunks = 0

                for mapping in chatbot_docs:
                    doc = mapping.document

                    # Count chunks for this document
                    chunk_count = Chunks.objects(document=doc).count()
                    total_chunks += chunk_count

                    loaded_files.append({
                        "file_name": doc.file_name,
                        "file_type": doc.file_type,
                        "status": doc.status,
                        "upload_date": doc.created_at,
                        "total_chunks": chunk_count
                    })

                result.append(ChatbotDetailResponse(
                    id=str(chatbot.id),
                    name=chatbot.name,
                    description=chatbot.description,
                    embedding_model=chatbot.embedding_model,
                    chunking_method=chatbot.chunking_method,
                    date_created=chatbot.date_created,
                    namespace=chatbot.namespace,
                    loaded_files=loaded_files,
                    total_files=len(loaded_files),
                    total_chunks=total_chunks
                ))

            logger.info(
                f"Retrieved {len(result)} total chatbots for super user {current_user.user_name}")
            return result

        else:
            # Invalid role
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid user role"
            )

    except HTTPException:
        raise
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
        # Validate user has access to this chatbot (owner or assigned client)
        if not validate_chatbot_access(current_user, chatbot_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chatbot not found or access denied"
            )

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
    # Validate ObjectId format
    if not validate_object_id(chatbot_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid chatbot ID format"
        )

    try:
        # Validate user has access to this chatbot (owner or assigned client)
        if not validate_chatbot_access(current_user, chatbot_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chatbot not found or access denied"
            )

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
        # Validate user has access to this chatbot (owner or assigned client)
        if not validate_chatbot_access(current_user, chatbot_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chatbot not found or access denied"
            )

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


@app.put("/chatbot/{chatbot_id}/conversation/{conversation_id}", response_model=UpdateConversationResponse, tags=["Conversation Name Update"])
async def update_name_of_conversation(
    chatbot_id: str,
    conversation_id: str,
    request: UpdateConversationRequest,
    current_user: User_Auth_Table = Depends(get_current_user)
):
    """Update the name of a conversation"""
    try:
        pipeline_handler.update_name_of_conversation(
            str(current_user.id), chatbot_id, conversation_id, request.new_conversation_title)
        logger.info(
            f"Updated name of conversation {conversation_id} for chatbot {chatbot_id} to {request.new_conversation_title} by user {current_user.user_name}")
        return UpdateConversationResponse(
            success=True,
            message=f"Conversation with ID {conversation_id} and new name {request.new_conversation_title} updated successfully for chatbot {chatbot_id} by user {current_user.user_name}"
        )
    except Exception as e:
        logger.error(
            f"Error updating name of conversation for chatbot {chatbot_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating name of conversation"
        )


@app.delete("/chatbot/{chatbot_id}/conversation/{conversation_id}", response_model=DeleteConversationResponse, tags=["Conversation Deletion"])
async def delete_conversation(
    chatbot_id: str,
    conversation_id: str,
    current_user: User_Auth_Table = Depends(get_current_user)
):
    """Delete a conversation"""
    try:
        pipeline_handler.delete_conversation(
            str(current_user.id), chatbot_id, conversation_id)
        logger.info(
            f"Deleted conversation {conversation_id} for chatbot {chatbot_id} by user {current_user.user_name}")
        return DeleteConversationResponse(
            success=True,
            message=f"Conversation with ID {conversation_id} deleted successfully for chatbot {chatbot_id} by user {current_user.user_name}"
        )
    except Exception as e:
        logger.error(f"Error deleting conversation: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to delete conversation")


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

        # Validate user has access to the chatbot from the session
        chatbot_id = str(session.chatbot_id.id)
        if not validate_chatbot_access(user, chatbot_id):
            logger.error(
                f"User {user.user_name} does not have access to chatbot {chatbot_id}")
            await safe_websocket_close(websocket, code=1008, reason="Chatbot access denied")
            return

        # Get the actual chatbot object from the session
        from db_service import ChatBots
        chatbot = ChatBots.objects(id=session.chatbot_id.id).first()
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

                # CASUAL CONVERSATION PRE-FILTERING
                # Check if this is a casual conversation that doesn't need RAG processing
                from casual_conversation_filter import is_casual_message, get_casual_response
                import time

                # Configuration: Enable/disable casual conversation pre-filtering
                ENABLE_CASUAL_PREFILTERING = os.getenv(
                    "ENABLE_CASUAL_PREFILTERING", "true").lower() == "true"

                start_time = time.time()
                casual_category = is_casual_message(
                    user_message) if ENABLE_CASUAL_PREFILTERING else None

                if casual_category:
                    logger.info(
                        f"🚀 FAST RESPONSE: Detected casual conversation '{user_message}' -> {casual_category}")

                    # Get appropriate casual response
                    casual_response = get_casual_response(
                        casual_category,
                        chatbot_description=chatbot.description
                    )

                    # Send immediate response without RAG processing
                    await safe_websocket_send(websocket, {
                        "type": "response_start",
                        "message": "Responding..."
                    })

                    # Send the casual response as a single chunk
                    await safe_websocket_send(websocket, {
                        "type": "response_chunk",
                        "chunk": casual_response
                    })

                    await safe_websocket_send(websocket, {
                        "type": "response_end"
                    })

                    # Save casual response to database
                    pipeline_handler.save_message_to_session(
                        session_id, casual_response, "agent"
                    )

                    # Log performance metrics
                    response_time = (time.time() - start_time) * \
                        1000  # Convert to milliseconds
                    logger.info(
                        f"⚡ CASUAL RESPONSE COMPLETE: '{user_message}' -> {casual_category} | Response time: {response_time:.2f}ms | Bypassed RAG: YES")
                    continue  # Skip RAG processing for this message
                else:
                    detection_time = (time.time() - start_time) * 1000
                    if ENABLE_CASUAL_PREFILTERING:
                        logger.info(
                            f"🔍 NON-CASUAL: '{user_message}' -> Proceeding to RAG | Detection time: {detection_time:.2f}ms")
                    else:
                        logger.info(
                            f"🔍 PREFILTERING DISABLED: '{user_message}' -> Proceeding to RAG")

                # Initialize RAG for this chatbot (only for non-casual conversations)
                from LLM.rag_llm_call import initialize_rag_config, ask_rag_assistant_stream

                logger.info(
                    f"Initializing RAG with user_id={str(user.id)}, namespace={chatbot.namespace}, embedding_model={chatbot.embedding_model}")

                # OPTIMIZATION: Use only chatbot's own namespace to avoid 500k token queries
                # Each chatbot now contains duplicated chunks in its own namespace
                # This eliminates the need to query multiple namespaces and reduces tokens by 90%
                chatbot_namespace = chatbot.namespace
                logger.info(
                    f"Using single namespace for RAG: {chatbot_namespace}")

                # Log chatbot description for debugging
                if chatbot.description:
                    logger.info(
                        f"Using personalized prompt for chatbot: {chatbot.description}")
                else:
                    logger.info(
                        "Using default prompt (no chatbot description provided)")

                initialize_rag_config(
                    user_id=str(user.id),
                    namespaces=[chatbot_namespace],  # Single namespace only
                    embedding_model=chatbot.embedding_model,
                    # Add chatbot description for personalized prompts
                    chatbot_description=chatbot.description
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
                        "type": "response_end",
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


# Client Assignment Endpoints
@app.post("/api/assign-chatbot-by-email", response_model=EmailAssignmentResponse, tags=["Client Management"])
async def assign_chatbot_by_email(
    request: EmailAssignmentRequest,
    current_user: User_Auth_Table = Depends(get_current_user)
):
    """Assign chatbot to existing client by email (Users and Super Users only)"""
    if current_user.role not in ['User', 'Super User']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Users and Super Users can assign chatbots to clients"
        )

    try:
        # Find existing client
        client = User_Auth_Table.objects(email=request.client_email).first()

        if not client:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No client found with email {request.client_email}. Client must exist before assignment."
            )

        if client.role != 'Client':
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot assign chatbot to Users - only Clients are allowed"
            )

        # Check if already assigned
        from db_service import ChatbotClientMapper
        from bson import ObjectId
        existing = ChatbotClientMapper.objects(
            chatbot=ObjectId(request.chatbot_id),
            client=client.id,
            is_active=True
        ).first()

        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Chatbot already assigned to {request.client_email}"
            )

        # Assign chatbot
        from db_service import assign_chatbot_to_client
        assignment = assign_chatbot_to_client(
            request.chatbot_id,
            str(client.id),
            str(current_user.id)
        )

        return EmailAssignmentResponse(
            message=f"Chatbot assigned to {request.client_email}",
            client_email=request.client_email,
            assignment_id=str(assignment.id)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to assign chatbot by email: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to assign chatbot: {str(e)}"
        )


@app.delete("/api/revoke-chatbot-from-client", tags=["Client Management"])
async def revoke_chatbot_from_client(
    chatbot_id: str,
    client_email: str,
    current_user: User_Auth_Table = Depends(get_current_user)
):
    """Revoke a chatbot assignment from a client by email"""
    if current_user.role not in ['User', 'Super User']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Users and Super Users can revoke chatbot assignments"
        )

    try:
        # Find client by email
        client = User_Auth_Table.objects(email=client_email).first()
        if not client:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Client with email {client_email} not found"
            )

        from db_service import revoke_chatbot_from_client
        success = revoke_chatbot_from_client(chatbot_id, str(client.id))

        if success:
            return {"message": f"Chatbot assignment revoked from {client_email}"}
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assignment not found"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to revoke chatbot from client: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to revoke chatbot assignment: {str(e)}"
        )


@app.get("/api/chatbot-assignments/{chatbot_id}", response_model=List[ChatbotClientInfo], tags=["Client Management"])
async def get_chatbot_assignments(
    chatbot_id: str,
    current_user: User_Auth_Table = Depends(get_current_user)
):
    """Get all clients assigned to a chatbot"""
    if current_user.role not in ['User', 'Super User']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Users and Super Users can view chatbot assignments"
        )

    try:
        from db_service import ChatbotClientMapper
        from bson import ObjectId

        # Get all active assignments for this chatbot
        assignments = ChatbotClientMapper.objects(
            chatbot=ObjectId(chatbot_id),
            is_active=True
        )

        result = []
        for assignment in assignments:
            client = assignment.client
            result.append(ChatbotClientInfo(
                client_id=str(client.id),
                user_name=client.user_name,
                first_name=client.first_name,
                last_name=client.last_name,
                email=client.email,
                assigned_at=assignment.assigned_at,
                is_active=assignment.is_active
            ))

        return result

    except Exception as e:
        logger.error(f"Failed to get chatbot assignments: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to get chatbot assignments: {str(e)}"
        )


@app.get("/api/my-assigned-chatbots", response_model=List[ChatbotDetailResponse], tags=["Client Management"])
async def get_my_assigned_chatbots(
    current_user: User_Auth_Table = Depends(get_current_user)
):
    """Get chatbots assigned to the current client"""
    if current_user.role != 'Client':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Clients can access assigned chatbots"
        )

    try:
        from db_service import get_client_assigned_chatbots, ChatbotDocumentsMapper
        chatbots = get_client_assigned_chatbots(str(current_user.id))

        result = []
        for chatbot in chatbots:
            # Get loaded files for this chatbot
            chatbot_docs = ChatbotDocumentsMapper.objects(chatbot=chatbot)
            loaded_files = []
            total_chunks = 0

            for mapping in chatbot_docs:
                doc = mapping.document

                # Count chunks for this document
                from db_service import Chunks
                chunk_count = Chunks.objects(document=doc).count()
                total_chunks += chunk_count

                loaded_files.append({
                    "file_name": doc.file_name,
                    "file_type": doc.file_type,
                    "status": doc.status,
                    "upload_date": doc.created_at,
                    "total_chunks": chunk_count
                })

            result.append(ChatbotDetailResponse(
                id=str(chatbot.id),
                name=chatbot.name,
                description=chatbot.description,
                embedding_model=chatbot.embedding_model,
                chunking_method=chatbot.chunking_method,
                date_created=chatbot.date_created,
                namespace=chatbot.namespace,
                loaded_files=loaded_files,
                total_files=len(loaded_files),
                total_chunks=total_chunks
            ))

        return result

    except Exception as e:
        logger.error(f"Failed to get assigned chatbots: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to get assigned chatbots: {str(e)}"
        )


# ==============================================Error handlers==============================================


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
