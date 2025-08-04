import os
import logging
from datetime import datetime, timedelta
from typing import List
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, status, Depends, UploadFile, File, Form
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware

from api_models import (
    CreateAgentRequest, CreateAgentResponse, LoginRequest, LoginResponse,
    SigninRequest, SigninResponse, UserResponse, ErrorResponse,
    ChunkingMethod, EmbeddingModel, AgentProvider, ChatbotDetailResponse, ConversationsResponse
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

# Security
security = HTTPBearer()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    global pipeline_handler
    
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
        
        logger.info(f"New user registered: {user.user_name} with role: {request.role}")
        
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
    agent_provider: str = Form(None, description="Agent provider: 'Gemini', 'OpenAI', or null for super user"),
    chunking_method: str = Form(None, description="Chunking method (super users only)"),
    embedding_model: str = Form(None, description="Embedding model (super users only)"),
    agent_description: str = Form(..., description="Description of the agent"),
    user_namespace: str = Form(..., description="Namespace prefix for the chatbot (no underscores, max 50 chars)"),
    # Files
    files: List[UploadFile] = File(..., description="Documents to process (PDF, DOCX, TXT, CSV)"),
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
        
        logger.info(f"Creating agent for user: {user.user_name} (Super User: {is_super_user})")
        
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
            logger.info(f"✅ Agent created successfully for user {user.user_name}")
        else:
            logger.warning(f"⚠️ Agent creation completed with issues for user {user.user_name}")
        
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
        logger.info(f"Retrieved {len(chatbots)} chatbots for user {current_user.user_name}")
        return chatbots
    except Exception as e:
        logger.error(f"Error retrieving chatbots for user {current_user.user_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving chatbots"
        )

@app.get("/chatbot/conversations", response_model=List[ConversationsResponse], tags=["Chatbot"])
async def get_chatbot_conversations(chatbot_id: str, current_user: User_Auth_Table = Depends(get_current_user)):
    """Get all conversations for a specific chatbot"""
    try:
        conversations = pipeline_handler.get_chatbot_conversations(chatbot_id, str(current_user.id))
        return conversations
    except Exception as e:
        logger.error(f"Error retrieving conversations for chatbot {chatbot_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving conversations"
        )


@app.get("/me", response_model=UserResponse, tags=["User"])
async def get_current_user_info(current_user: User_Auth_Table = Depends(get_current_user)):
    """Get current user information"""
    return user_to_response(current_user)


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