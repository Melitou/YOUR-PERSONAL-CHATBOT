"""
Pipeline Handler for FastAPI Integration
Handles communication between FastAPI endpoints and the existing pipeline components
"""
import os
import tempfile
import hashlib
import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from fastapi import UploadFile, HTTPException, status
from bson import ObjectId

from master_pipeline import MasterPipeline

from db_service import initialize_db, User_Auth_Table, ChatBots, Documents, Chunks, Conversation, Messages, ConversationSession
from api_models import ChunkingMethod, EmbeddingModel, AgentProvider, FileMetadata, ChatbotDetailResponse, LoadedFileInfo, Message, CreateSessionResponse, ConversationSummary, ConversationMessagesResponse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PipelineHandler:
    """Handles the integration between FastAPI and the existing pipeline"""
    
    def __init__(self):
        """Initialize the pipeline handler"""
        # Initialize database connection
        self.client, self.db, self.fs = initialize_db()
        if self.client is None or self.db is None or self.fs is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to initialize database connection"
            )
        
        logger.info("Pipeline handler initialized successfully")
    
    def validate_files(self, files: List[UploadFile]) -> List[FileMetadata]:
        """Validate uploaded files and return metadata"""
        if not files:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No files provided"
            )
        
        # Supported file types
        supported_extensions = {'.pdf', '.docx', '.txt', '.csv'}
        supported_mime_types = {
            'application/pdf',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'text/plain',
            'text/csv',
            'application/csv'
        }
        
        file_metadata = []
        
        for file in files:
            if not file.filename:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="File must have a filename"
                )
            
            # Check file extension
            file_ext = Path(file.filename).suffix.lower()
            if file_ext not in supported_extensions:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Unsupported file type: {file_ext}. Supported types: {', '.join(supported_extensions)}"
                )
            
            # Check content type if available
            if file.content_type and file.content_type not in supported_mime_types:
                logger.warning(f"File {file.filename} has unsupported MIME type: {file.content_type}")
            
            # Create metadata (file hash will be calculated when reading content)
            metadata = FileMetadata(
                filename=file.filename,
                content_type=file.content_type or "application/octet-stream",
                size=0,  # Will be updated when reading content
                file_hash=""  # Will be calculated when reading content
            )
            file_metadata.append(metadata)
        
        return file_metadata
    
    async def save_files_to_temp_directory(self, files: List[UploadFile]) -> Tuple[str, List[FileMetadata]]:
        """Save uploaded files to a temporary directory and return the path with metadata"""
        # Create temporary directory
        temp_dir = tempfile.mkdtemp(prefix="fastapi_upload_")
        file_metadata = []
        
        try:
            for file in files:
                # Read file content
                content = await file.read()
                
                # Calculate file hash
                file_hash = hashlib.sha256(content).hexdigest()
                
                # Create file metadata
                metadata = FileMetadata(
                    filename=file.filename,
                    content_type=file.content_type or "application/octet-stream",
                    size=len(content),
                    file_hash=file_hash
                )
                file_metadata.append(metadata)
                
                # Save file to temp directory
                file_path = Path(temp_dir) / file.filename
                with open(file_path, 'wb') as f:
                    f.write(content)
                
                # Reset file pointer for potential future use
                await file.seek(0)
            
            logger.info(f"Saved {len(files)} files to temporary directory: {temp_dir}")
            return temp_dir, file_metadata
            
        except Exception as e:
            # Clean up temp directory if error occurs
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error saving files: {str(e)}"
            )
    
    def create_unique_namespace(self, user_namespace: str, user: User_Auth_Table) -> str:
        """Create unique namespace by concatenating user input with user ID

        Args:
            user_namespace: User-provided namespace prefix
            user: User object for getting user ID

        Returns:
            Unique namespace in format: {user_namespace}_{user_id}

        Raises:
            ValueError: If user_namespace contains underscores or is too long
        """
        # Validate user input
        if '_' in user_namespace:
            raise ValueError(
                "Namespace cannot contain underscores (used for user ID separation)")

        if len(user_namespace) > 50:  # Leave room for user ID
            raise ValueError("Namespace prefix too long (max 50 characters)")

        if not user_namespace.strip():
            raise ValueError("Namespace cannot be empty")

        # Create unique namespace
        unique_namespace = f"{user_namespace.strip()}_{user.id}"
        return unique_namespace
    
    def generate_chatbot_name(self, agent_description: str) -> str:
        """Generate a chatbot name from the agent description"""
        # Clean the description and limit length
        clean_name = "".join(c for c in agent_description if c.isalnum() or c in " -").strip()
        clean_name = " ".join(clean_name.split())  # Normalize spaces
        
        # Limit to 100 characters for the name
        if len(clean_name) > 100:
            clean_name = clean_name[:97] + "..."
        
        return clean_name if clean_name else "Untitled Chatbot"
    
    def determine_default_settings(self, agent_provider: Optional[AgentProvider]) -> Tuple[ChunkingMethod, EmbeddingModel]:
        """Determine default chunking method and embedding model based on agent provider"""
        if agent_provider == AgentProvider.GEMINI:
            return ChunkingMethod.TOKEN, EmbeddingModel.GEMINI
        elif agent_provider == AgentProvider.OPENAI:
            return ChunkingMethod.TOKEN, EmbeddingModel.OPENAI_SMALL
        else:
            # Super user - use OpenAI as default
            return ChunkingMethod.TOKEN, EmbeddingModel.OPENAI_SMALL
    
    async def process_agent_creation(
        self,
        user: User_Auth_Table,
        files: List[UploadFile],
        agent_description: str,
        user_namespace: str,
        chunking_method: Optional[ChunkingMethod] = None,
        embedding_model: Optional[EmbeddingModel] = None,
        agent_provider: Optional[AgentProvider] = None
    ) -> Dict:
        """Process the complete agent creation workflow"""
        
        # Validate files
        self.validate_files(files)
        
        # Save files to temporary directory
        temp_dir, file_metadata = await self.save_files_to_temp_directory(files)
        
        try:
            # Generate unique namespace using user input and user ID
            namespace = self.create_unique_namespace(user_namespace, user)
            
            # Determine settings for normal users
            if agent_provider is not None:  # Normal user
                chunking_method, embedding_model = self.determine_default_settings(agent_provider)
                logger.info(f"Normal user - using default settings: chunking={chunking_method}, embedding={embedding_model}")
            else:  # Super user
                if not chunking_method:
                    chunking_method = ChunkingMethod.TOKEN
                if not embedding_model:
                    embedding_model = EmbeddingModel.OPENAI_SMALL
                logger.info(f"Super user - using specified settings: chunking={chunking_method}, embedding={embedding_model}")
            
            # Initialize master pipeline with the specified settings
            if MasterPipeline is None:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Pipeline functionality not available due to missing dependencies"
                )
            
            master_pipeline = MasterPipeline(
                max_workers=4,
                rate_limit_delay=0.2,
                chunking_method=chunking_method.value,
                chunking_params={},
                user=user
            )
            # The document processor doesn't have a user field, but it operates on documents
            # We need to ensure it processes documents for this specific user
            
            logger.info(f"Processing {len(files)} files for user {user.user_name} with namespace '{namespace}'")
            
            # Run the complete workflow with embeddings
            results = await master_pipeline.process_directory_complete_with_embeddings(
                directory_path=temp_dir,
                namespace=namespace,
                user_id=str(user.id),
                embedding_model=embedding_model.value,
                use_parallel_upload=True,
                use_parallel_processing=True
            )
            
            # Close pipeline connections
            master_pipeline.close()
            
            # Process results
            success = results.get('complete_workflow_success', False)
            
            # If processing was successful, create ChatBot record
            if success:
                try:
                    #chatbot_name = self.generate_chatbot_name(agent_description)
                    chatbot = ChatBots(
                        name=user_namespace,
                        description=agent_description,
                        embedding_model=embedding_model.value,
                        chunking_method=chunking_method.value,
                        date_created=datetime.now(),
                        user_id=user,
                        namespace=namespace
                    )
                    chatbot.save()
                    logger.info(f"✅ ChatBot record created: {user_namespace} (namespace: {namespace})")
                except Exception as e:
                    logger.error(f"❌ Error creating ChatBot record: {e}")
                    # Don't fail the entire process if ChatBot creation fails
                    success = False
            
            response_data = {
                'success': success,
                'message': results.get('message', 'Processing completed'),
                'namespace': namespace,
                'file_metadata': file_metadata,
                'processing_results': None,
                'embedding_results': results.get('embedding_results'),
                'total_time': results.get('total_complete_workflow_time', 0)
            }
            
            # Add processing results if available
            if results.get('processing_results'):
                pr = results['processing_results']
                response_data['processing_results'] = {
                    'total_files': len(files),
                    'processed': pr.get('processed', 0),
                    'failed': pr.get('failed', 0),
                    'chunks_created': pr.get('chunks_created', 0),
                    'processing_time': pr.get('processing_time', 0)
                }
            
            if success:
                logger.info(f"Successfully processed agent for user {user.user_name}")
            else:
                logger.warning(f"Agent processing completed with issues for user {user.user_name}")
            
            return response_data
            
        except Exception as e:
            logger.error(f"Error processing agent creation: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error processing files: {str(e)}"
            )
        
        finally:
            # Clean up temporary directory
            import shutil
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
                logger.info(f"Cleaned up temporary directory: {temp_dir}")
            except Exception as e:
                logger.warning(f"Error cleaning up temp directory {temp_dir}: {e}")
    
    def get_user_chatbots(self, user_id: str) -> List[ChatbotDetailResponse]:
        """Get all chatbots for a user with detailed information including loaded files"""
        try:
            # Find user by ObjectId
            user = User_Auth_Table.objects(id=ObjectId(user_id)).first()
            if not user:
                logger.error(f"User not found: {user_id}")
                return []
            
            # Get all chatbots for this user
            chatbots = ChatBots.objects(user_id=user).order_by('-date_created')
            
            chatbot_details = []
            for chatbot in chatbots:
                # Get documents for this chatbot (by namespace) - case insensitive
                documents = Documents.objects(
                    user=user,
                    namespace__iexact=chatbot.namespace
                ).order_by('created_at')
                
                # Create loaded file info
                loaded_files = []
                total_chunks_across_files = 0
                
                for doc in documents:
                    # Count chunks for this document
                    chunk_count = Chunks.objects(document=doc).count()
                    total_chunks_across_files += chunk_count
                    
                    loaded_file = LoadedFileInfo(
                        file_name=doc.file_name,
                        file_type=doc.file_type,
                        status=doc.status,
                        upload_date=doc.created_at,
                        total_chunks=chunk_count
                    )
                    loaded_files.append(loaded_file)

                logger.info(f"Chatbot {chatbot.name} has {len(loaded_files)} loaded files and {total_chunks_across_files} total chunks")
                
                # Create detailed chatbot response
                chatbot_detail = ChatbotDetailResponse(
                    id=str(chatbot.id),
                    name=chatbot.name,
                    description=chatbot.description,
                    embedding_model=chatbot.embedding_model,
                    chunking_method=chatbot.chunking_method,
                    namespace=chatbot.namespace,
                    date_created=chatbot.date_created,
                    loaded_files=loaded_files,
                    total_files=len(loaded_files),
                    total_chunks=total_chunks_across_files
                )
                chatbot_details.append(chatbot_detail)
            
            logger.info(f"Retrieved {len(chatbot_details)} chatbots for user {user.user_name}")
            return chatbot_details
            
        except Exception as e:
            logger.error(f"Error retrieving user chatbots: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error retrieving chatbots: {str(e)}"
            )
    
    def get_chatbot_conversations(self, chatbot_id: str, user_id: str = None) -> List[Conversation]:
        """Get all conversations for a specific chatbot"""
        try:
            logger.info(f"Getting conversations for chatbot {chatbot_id} for user {user_id}")
            
            # Validate user and chatbot exist
            user = User_Auth_Table.objects(id=ObjectId(user_id)).first()
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            chatbot = ChatBots.objects(id=ObjectId(chatbot_id)).first()
            if not chatbot:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Chatbot not found"
                )
            
            # Validate the chatbot belongs to the user
            if chatbot.user_id.id != user.id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Chatbot doesn't belong to user"
                )
            
            # Get all conversations for the chatbot
            conversations = Conversation.objects(chatbot=chatbot).order_by('-created_at')
            conversation_summaries = []
            for conversation in conversations:
                conversation_summary = ConversationSummary(
                    conversation_id=str(conversation.id),
                    conversation_title=conversation.conversation_title,
                    created_at=conversation.created_at,
                    belonging_user_uid=str(user.id),
                    belonging_chatbot_id=str(chatbot.id)
                )
                conversation_summaries.append(conversation_summary)
            
            return conversation_summaries
        except Exception as e:
            logger.error(f"Error retrieving conversations for chatbot {chatbot_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error retrieving conversations: {str(e)}"
            )

    def create_new_conversation_with_session(self, user_id: str, chatbot_id: str) -> CreateSessionResponse:
        """Create a new conversation and session for a chatbot"""

        try: 
            # Validate user and chatbot exist
            user = User_Auth_Table.objects(id=ObjectId(user_id)).first()
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            
            # Validate the chatbot exists and belongs to the user
            chatbot = ChatBots.objects(id=ObjectId(chatbot_id), user_id=user).first()
            if not chatbot:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Chatbot not found or doesn't belong to user"
                )
            
            # Create new conversation
            conversation = Conversation(
                chatbot=chatbot,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            conversation.save()
            logger.info(f"Created new conversation {conversation.id} for chatbot {chatbot.name}")

            # Create new session
            response = self.create_conversation_session(user_id, chatbot_id, str(conversation.id))
            return response
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error creating new conversation with session: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error creating new conversation with session: {str(e)}"
            )

    
    def create_conversation_session(self, user_id: str, chatbot_id: str, conversation_id: str) -> CreateSessionResponse:
        """Create a new conversation session for a user and chatbot"""
        import uuid
        
        try:
            # Validate user and chatbot exist
            user = User_Auth_Table.objects(id=ObjectId(user_id)).first()
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            
            chatbot = ChatBots.objects(id=ObjectId(chatbot_id), user_id=user).first()
            if not chatbot:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Chatbot not found or doesn't belong to user"
                )

            # Validate the conversation exists and belongs to the chatbot
            conversation = Conversation.objects(
                id=ObjectId(conversation_id), 
                chatbot=chatbot
            ).first()
            if not conversation:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Conversation not found or doesn't belong to chatbot"
                )
            
            # Deactivate and delete any existing active sessions for this user
            existing_sessions = ConversationSession.objects(user_id=user, is_active=True)
            for session in existing_sessions:
                session.is_active = False
                session.save()
                session.delete()
                logger.info(f"Deactivated and deleted existing session {session.session_id} for user {user.user_name}")
            
            # Create new session
            session_id = str(uuid.uuid4())
            chat_session = ConversationSession(
                user_id=user,
                chatbot_id=chatbot,
                conversation_id=conversation,
                session_id=session_id,
                created_at=datetime.now(),
                last_activity=datetime.now(),
                is_active=True
            )
            chat_session.save()
            
            logger.info(f"Created conversation session {session_id} for user {user.user_name} with chatbot {chatbot.name} and conversation {conversation.id}")
            
            # Get conversation messages
            conversation_messages = self._get_conversation_messages_list(conversation)
            
            return CreateSessionResponse(
                session_id=session_id,
                chatbot_id=str(chatbot.id),
                chatbot_name=chatbot.name,
                conversation_id=str(conversation.id),
                messages=conversation_messages
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error creating conversation session: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error creating conversation session: {str(e)}"
            )
    
    def get_conversation_messages(self, conversation_id: str) -> ConversationMessagesResponse:
        """Get all messages for a specific conversation"""
        try:    
            try:
                conversation = Conversation.objects(id=ObjectId(conversation_id)).first()
                if not conversation:
                    logger.error(f"Conversation not found: {conversation_id}")
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Conversation not found"
                    )
            except HTTPException:
                # Re-raise HTTPExceptions as-is (404, 400, etc.)
                raise
            except Exception as e:
                if "invalid ObjectId" in str(e).lower():
                    logger.error(f"Invalid conversation ID format: {conversation_id}")
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid conversation ID format"
                    )
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Error retrieving conversation: {str(e)}"
                )
            
            messages = Messages.objects(conversation_id=conversation).order_by('created_at')
            message_responses = []
            for message in messages:
                message_response = Message(
                    message=message.message,
                    created_at=message.created_at,
                    role=message.role
                )
                message_responses.append(message_response)
            
            return ConversationMessagesResponse(
                conversation_id=str(conversation.id),
                messages=message_responses
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error retrieving messages for conversation {conversation_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error retrieving messages: {str(e)}"
                        )
    
    def _get_conversation_messages_list(self, conversation: Conversation) -> List[Message]:
        """Helper function to get formatted messages for a conversation"""
        messages = Messages.objects(conversation_id=conversation).order_by('created_at')
        message_responses = []
        for message in messages:
            message_response = Message(
                message=message.message,
                created_at=message.created_at,
                role=message.role
            )
            message_responses.append(message_response)
        return message_responses
    
    def get_conversation_session(self, session_id: str, user_id: str) -> ConversationSession:
        """Get an active conversation session"""
        try:
            user = User_Auth_Table.objects(id=ObjectId(user_id)).first()
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            
            session = ConversationSession.objects(
                session_id=session_id,
                user_id=user,
                is_active=True
            ).first()
            
            if not session:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Active session not found"
                )
            
            # Update last activity
            session.last_activity = datetime.now()
            session.save()
            
            return session
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error retrieving chat session: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error retrieving chat session: {str(e)}"
            )
    
    def save_message_to_session(self, session_id: str, message: str, role: str) -> Messages:
        """Save a message to the session's conversation"""
        try:
            session = ConversationSession.objects(session_id=session_id, is_active=True).first()
            if not session:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Active session not found"
                )
            
            # Create and save message
            msg = Messages(
                conversation_id=session.conversation_id,
                message=message,
                role=role,
                created_at=datetime.now()
            )
            msg.save()
            
            # Update conversation title with first user message
            conversation = session.conversation_id
            if role == "user" and (conversation.conversation_title == "New Conversation" or not conversation.conversation_title):
                # Check if this is the first user message in the conversation
                existing_user_messages = Messages.objects(
                    conversation_id=conversation,
                    role="user"
                ).count()
                
                if existing_user_messages == 1:  # This is the first user message (just saved)
                    # Truncate message if too long for title (limit to 50 characters)
                    title = message[:50] + "..." if len(message) > 50 else message
                    conversation.conversation_title = title
                    logger.info(f"Updated conversation {conversation.id} title to: {title}")
            
            # Update session and conversation activity
            session.last_activity = datetime.now()
            session.save()
            
            conversation.updated_at = datetime.now()
            conversation.save()
            
            return msg
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error saving message to session: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error saving message: {str(e)}"
            )
    
    def close_conversation_session(self, session_id: str, user_id: str):
        """Close/deactivate a conversation session"""
        try:
            user = User_Auth_Table.objects(id=ObjectId(user_id)).first()
            if not user:
                return  # User not found, nothing to close
            
            session = ConversationSession.objects(
                session_id=session_id,
                user_id=user,
                is_active=True
            ).first()
            
            if session:
                session.is_active = False
                session.save()
                logger.info(f"Closed conversation session {session_id} for user {user.user_name}")
                
        except Exception as e:
            logger.error(f"Error closing conversation session: {e}")
    
    def cleanup_inactive_sessions(self, hours: int = 24):
        """Cleanup sessions inactive for more than specified hours"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            inactive_sessions = ConversationSession.objects(
                last_activity__lt=cutoff_time,
                is_active=True
            )
            
            count = 0
            for session in inactive_sessions:
                session.is_active = False
                session.save()
                count += 1
            
            if count > 0:
                logger.info(f"Cleaned up {count} inactive sessions")
                
        except Exception as e:
            logger.error(f"Error cleaning up inactive sessions: {e}")
    
    def close(self):
        """Close database connections"""
        try:
            if self.client:
                self.client.close()
                logger.info("Database connections closed")
        except Exception as e:
            logger.error(f"Error closing database connections: {e}")