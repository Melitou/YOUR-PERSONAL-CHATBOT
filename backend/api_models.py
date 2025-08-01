"""
Pydantic models for FastAPI request/response validation
"""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field
from enum import Enum


class ChunkingMethod(str, Enum):
    """Enumeration for chunking methods"""
    TOKEN = "token"
    SEMANTIC = "semantic"
    LINE = "line"
    RECURSIVE = "recursive"


class EmbeddingModel(str, Enum):
    """Enumeration for embedding models"""
    OPENAI_SMALL = "text-embedding-3-small"
    GEMINI = "gemini-embedding-001"


class AgentProvider(str, Enum):
    """Enumeration for agent providers"""
    GEMINI = "Gemini"
    OPENAI = "OpenAI"


class UserRole(str, Enum):
    """Enumeration for user roles"""
    USER = "User"
    SUPER_USER = "Super User"


# Request Models
class CreateAgentRequest(BaseModel):
    """Request model for creating an agent"""
    agent_provider: Optional[AgentProvider] = Field(None, description="Agent provider - if null, user is super user")
    chunking_method: Optional[ChunkingMethod] = Field(None, description="Chunking method - null for normal users")
    embedding_model: Optional[EmbeddingModel] = Field(None, description="Embedding model - null for normal users")
    user_name: str = Field(..., min_length=3, max_length=50, description="Username")
    password: str = Field(..., min_length=6, description="Password")
    first_name: str = Field(..., min_length=1, max_length=50, description="First name")
    last_name: str = Field(..., min_length=1, max_length=50, description="Last name")
    email: EmailStr = Field(..., description="Email address")
    agent_description: str = Field(..., min_length=10, max_length=500, description="Agent description")


class LoginRequest(BaseModel):
    """Request model for user login"""
    username: str = Field(..., description="Username")
    password: str = Field(..., description="Password")


class SigninRequest(BaseModel):
    """Request model for user registration"""
    user_name: str = Field(..., min_length=3, max_length=50, description="Username")
    password: str = Field(..., min_length=6, description="Password")
    first_name: str = Field(..., min_length=1, max_length=50, description="First name")
    last_name: str = Field(..., min_length=1, max_length=50, description="Last name")
    email: EmailStr = Field(..., description="Email address")
    role: UserRole = Field(..., description="User role")


# Response Models
class UserResponse(BaseModel):
    """Response model for user data"""
    id: str = Field(..., description="User ID")
    user_name: str = Field(..., description="Username")
    first_name: str = Field(..., description="First name")
    last_name: str = Field(..., description="Last name")
    email: EmailStr = Field(..., description="Email address")
    created_at: datetime = Field(..., description="Account creation date")
    role: UserRole = Field(..., description="User role")


class LoginResponse(BaseModel):
    """Response model for login"""
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    user: UserResponse = Field(..., description="User information")


class SigninResponse(BaseModel):
    """Response model for registration"""
    message: str = Field(..., description="Registration status message")
    user: UserResponse = Field(..., description="Created user information")


class ProcessingResult(BaseModel):
    """Model for processing results"""
    total_files: int = Field(..., description="Total number of files processed")
    processed: int = Field(..., description="Number of successfully processed files")
    failed: int = Field(..., description="Number of failed files")
    chunks_created: int = Field(..., description="Total chunks created")
    processing_time: float = Field(..., description="Processing time in seconds")


class CreateAgentResponse(BaseModel):
    """Response model for agent creation"""
    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Status message")
    user: UserResponse = Field(..., description="Created user information")
    namespace: str = Field(..., description="Generated namespace for the agent")
    processing_results: Optional[ProcessingResult] = Field(None, description="File processing results")
    embedding_results: Optional[dict] = Field(None, description="Embedding processing results")
    total_time: float = Field(..., description="Total processing time")


class ErrorResponse(BaseModel):
    """Standard error response model"""
    detail: str = Field(..., description="Error description")
    error_code: Optional[str] = Field(None, description="Error code")
    timestamp: datetime = Field(default_factory=datetime.now, description="Error timestamp")


# Internal Models
class FileMetadata(BaseModel):
    """Metadata for uploaded files"""
    filename: str
    content_type: str
    size: int
    file_hash: str