"""
Pydantic models for FastAPI request/response validation
"""
from datetime import datetime
from typing import List, Optional, Dict
from pydantic import BaseModel, EmailStr, Field
from enum import Enum


class CheckDocumentsRequest(BaseModel):
    hashes: List[str]


class ExistingDocumentInfo(BaseModel):
    hash: str
    file_name: str
    namespace: str
    chatbots: List[str]


class CheckDocumentsResponse(BaseModel):
    duplicates: List[ExistingDocumentInfo]


class ChunkingMethod(str, Enum):
    """Enumeration for chunking methods"""
    TOKEN = "token"
    SEMANTIC = "semantic"
    LINE = "line"
    RECURSIVE = "recursive"


class EmbeddingModel(str, Enum):
    """Enumeration for embedding models"""
    OPENAI_SMALL = "text-embedding-3-small"
    OPENAI_LARGE = "text-embedding-3-large"
    OPENAI_ADA = "text-embedding-ada-002"
    OPENAI_BEDROCK = "text-embedding-005"
    OPENAI_MULTILINGUAL = "text-multilingual-embedding-002"
    OPENAI_MULTILINGUAL_LARGE = "multilingual-e5-large"
    GEMINI = "gemini-embedding-001"


class AgentProvider(str, Enum):
    """Enumeration for agent providers"""
    GEMINI = "Gemini"
    OPENAI = "OpenAI"


class UserRole(str, Enum):
    """Enumeration for user roles"""
    USER = "User"
    SUPER_USER = "Super User"
    CLIENT = "Client"


# Request Models
class CreateAgentRequest(BaseModel):
    """Request model for creating an agent"""
    agent_provider: Optional[AgentProvider] = Field(
        None, description="Agent provider - if null, user is super user")
    chunking_method: Optional[ChunkingMethod] = Field(
        None, description="Chunking method - null for normal users")
    embedding_model: Optional[EmbeddingModel] = Field(
        None, description="Embedding model - null for normal users")
    user_name: str = Field(..., min_length=3,
                           max_length=50, description="Username")
    password: str = Field(..., min_length=6, description="Password")
    first_name: str = Field(..., min_length=1,
                            max_length=50, description="First name")
    last_name: str = Field(..., min_length=1,
                           max_length=50, description="Last name")
    email: EmailStr = Field(..., description="Email address")
    agent_description: str = Field(..., min_length=10,
                                   max_length=500, description="Agent description")


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


class LoginRequest(BaseModel):
    """Request model for user login"""
    username: str = Field(..., description="Username")
    password: str = Field(..., description="Password")


class SigninRequest(BaseModel):
    """Request model for user registration"""
    user_name: str = Field(..., min_length=3,
                           max_length=50, description="Username")
    password: str = Field(..., min_length=6, description="Password")
    first_name: str = Field(..., min_length=1,
                            max_length=50, description="First name")
    last_name: str = Field(..., min_length=1,
                           max_length=50, description="Last name")
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
    total_files: int = Field(...,
                             description="Total number of files processed")
    processed: int = Field(...,
                           description="Number of successfully processed files")
    failed: int = Field(..., description="Number of failed files")
    chunks_created: int = Field(..., description="Total chunks created")
    processing_time: float = Field(...,
                                   description="Processing time in seconds")


class CreateAgentResponse(BaseModel):
    """Response model for agent creation"""
    success: bool = Field(...,
                          description="Whether the operation was successful")
    message: str = Field(..., description="Status message")
    user: UserResponse = Field(..., description="Created user information")
    namespace: str = Field(...,
                           description="Generated namespace for the agent")
    processing_results: Optional[ProcessingResult] = Field(
        None, description="File processing results")
    embedding_results: Optional[dict] = Field(
        None, description="Embedding processing results")
    total_time: float = Field(..., description="Total processing time")
    # New fields for enhancement
    can_enhance: bool = True
    basic_summaries: bool = True
    enhancement_available: bool = True

# Not used
# class ChatbotResponse(BaseModel):
#     """Response model for chatbot"""
#     id: str = Field(..., description="Chatbot ID")
#     name: str = Field(..., description="Chatbot name")
#     description: str = Field(..., description="Chatbot description")


class LoadedFileInfo(BaseModel):
    """Information about a loaded file in a chatbot"""
    file_name: str = Field(..., description="Name of the file")
    file_type: str = Field(...,
                           description="Type of the file (pdf, docx, txt, csv)")
    status: str = Field(...,
                        description="Processing status (pending, processed, failed)")
    upload_date: datetime = Field(...,
                                  description="When the file was uploaded")
    total_chunks: int = Field(...,
                              description="Number of chunks created from this file")


class ChatbotDetailResponse(BaseModel):
    """Detailed response model for chatbot with all information"""
    id: str = Field(..., description="Chatbot ID")
    name: str = Field(..., description="Chatbot name")
    description: str = Field(..., description="Chatbot description")
    embedding_model: str = Field(..., description="Embedding model used")
    chunking_method: str = Field(..., description="Chunking method used")
    namespace: str = Field(..., description="Unique namespace for the chatbot")
    date_created: datetime = Field(...,
                                   description="When the chatbot was created")
    loaded_files: List[LoadedFileInfo] = Field(
        ..., description="List of files loaded into this chatbot")
    total_files: int = Field(..., description="Total number of files loaded")
    total_chunks: int = Field(...,
                              description="Total number of chunks across all files")


class Message(BaseModel):
    """Model for messages of a conversation"""
    message: str = Field(..., description="Message content")
    created_at: datetime = Field(...,
                                 description="When the message was created")
    role: str = Field(..., description="Role of the message (user, agent)")


class ConversationSummary(BaseModel):
    """Response model for conversation summary/basic information without the messages"""
    conversation_id: str = Field(..., description="Conversation ID")
    conversation_title: str = Field(...,
                                    description="Title of the conversation")
    created_at: datetime = Field(...,
                                 description="When the conversation was created")
    belonging_user_uid: str = Field(
        ..., description="User ID of the user who owns the conversation")
    belonging_chatbot_id: str = Field(
        ..., description="Chatbot ID of the chatbot that the conversation belongs to")


class ConversationMessagesResponse(BaseModel):
    """Response model for conversation messages"""
    conversation_id: str = Field(..., description="Conversation ID")
    messages: List[Message] = Field(...,
                                    description="List of messages in the conversation")


class UpdateConversationRequest(BaseModel):
    """Request model for updating the name of a conversation"""
    new_conversation_title: str = Field(...,
                                        description="New title of the conversation")


class UpdateConversationResponse(BaseModel):
    """Response model for updating the name of a conversation"""
    success: bool = Field(...,
                          description="Whether the operation was successful")
    message: str = Field(..., description="Status message")


class DeleteConversationResponse(BaseModel):
    """Response model for deleting a conversation"""
    success: bool = Field(...,
                          description="Whether the operation was successful")
    message: str = Field(..., description="Status message")

# Not used
# class CreateSessionRequest(BaseModel):
#     """Request model for creating a chat session"""
#     pass  # No additional data needed, chatbot_id comes from URL and user from JWT


class CreateSessionResponse(BaseModel):
    """Response model for chat session creation"""
    session_id: str = Field(...,
                            description="Unique session ID for WebSocket connection")
    conversation_id: str = Field(..., description="Conversation ID")
    chatbot_id: str = Field(..., description="Chatbot ID")
    chatbot_name: str = Field(..., description="Chatbot name")
    messages: List[Message] = Field(
        default=[], description="List of messages in the conversation")

# Not used
# class ChatMessageRequest(BaseModel):
#     """Request model for chat messages via WebSocket"""
#     message: str = Field(..., min_length=1, max_length=2000, description="User message content")
#     message_type: str = Field(default="text", description="Type of message (text, system, etc.)")

# Not used
# class ChatMessageResponse(BaseModel):
#     """Response model for chat messages"""
#     message: str = Field(..., description="Assistant response")
#     message_id: str = Field(..., description="Unique message ID")
#     timestamp: datetime = Field(..., description="Message timestamp")
#     is_complete: bool = Field(default=True, description="Whether this is the complete message or a chunk")
#     session_id: str = Field(..., description="Session ID")

# Not used
# class ErrorResponse(BaseModel):
#     """Standard error response model"""
#     detail: str = Field(..., description="Error description")
#     error_code: Optional[str] = Field(None, description="Error code")
#     timestamp: datetime = Field(default_factory=datetime.now, description="Error timestamp")

# Internal Models


class FileMetadata(BaseModel):
    """Metadata for uploaded files"""
    filename: str
    content_type: str
    size: int
    file_hash: str


class BatchJobStatus(str, Enum):
    SUBMITTED = "submitted"
    VALIDATING = "validating"
    IN_PROGRESS = "in_progress"
    FINALIZING = "finalizing"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class EnhancementStatus(BaseModel):
    """Response model for enhancement status"""
    batch_id: str
    status: BatchJobStatus
    total_requests: int
    request_counts: Dict[str, int]
    created_at: datetime
    completed_at: Optional[datetime] = None


# Client Assignment Models
class EmailAssignmentRequest(BaseModel):
    """Request model for assigning chatbot to client by email"""
    chatbot_id: str = Field(..., description="Chatbot ID")
    client_email: EmailStr = Field(..., description="Client email address")


class EmailAssignmentResponse(BaseModel):
    """Response model for email-based chatbot assignment"""
    message: str = Field(..., description="Success message")
    client_email: EmailStr = Field(..., description="Client email")
    new_client: bool = Field(...,
                             description="Whether a new client was created")
    assignment_id: str = Field(..., description="Assignment ID")


class ChatbotClientInfo(BaseModel):
    """Information about a client assigned to a chatbot"""
    client_id: str
    user_name: str
    first_name: str
    last_name: str
    email: EmailStr
    assigned_at: datetime
    is_active: bool
