from datetime import datetime
from mongoengine import connect, Document, StringField, DateTimeField, IntField, ReferenceField, ObjectIdField, ListField, DictField, BooleanField
from bson import ObjectId
from pymongo import MongoClient
from gridfs import GridFS
import hashlib


def initialize_db(db_url: str = "mongodb://localhost:50000/"):
    """Initialize MongoDB connection and create necessary indexes"""
    try:
        database_name = "your_personal_chatbot_db"

        # Connect to MongoDB with PyMongo
        client = MongoClient(db_url)
        db = client[database_name]

        # Connect MongoEngine to the same database
        connect(db=database_name, host=db_url)

        # Initialize GridFS
        fs = GridFS(db)

        print("Database initialized successfully!")
        return client, db, fs

    except Exception as e:
        print(f"Error initializing database: {e}")
        return None, None, None

class User_Auth_Table(Document):
    """User authentication table with user_id as main connector"""
    user_name = StringField(required=True, unique=True)
    password = StringField(required=True)
    first_name = StringField(required=True)
    last_name = StringField(required=True)
    email = StringField(required=True, unique=True)
    created_at = DateTimeField(required=True)
    role = StringField(required=True, choices=['User', 'Super User'])

    meta = {
        'collection': 'user_auth_table',
        'indexes': [
            {'fields': ['email'], 'unique': True},
            {'fields': ['user_name'], 'unique': True},
            {'fields': ['role']}
        ]
    }

    def __str__(self) -> str:
        return f"User_Auth_Table(user_name={self.user_name}, first_name={self.first_name}, last_name={self.last_name}, email={self.email}, role={self.role})"

class ChatBots(Document):
    """ChatBots table to store chatbot configurations"""
    name = StringField(required=True)
    description = StringField(required=True)
    embedding_model = StringField(required=True)
    chunking_method = StringField(required=True)
    date_created = DateTimeField(required=True)
    user_id = ReferenceField(User_Auth_Table, required=True)
    namespace = StringField(required=True, unique=True)

    meta = {
        'collection': 'chatbots',
        'indexes': [
            {'fields': ['user_id']},
            {'fields': ['namespace'], 'unique': True},
            {'fields': ['date_created']},
            {'fields': ['embedding_model']},
            {'fields': ['chunking_method']},
            {'fields': [('user_id', 1), ('date_created', -1)]}
        ]
    }

    def __str__(self) -> str:
        return f"ChatBots(name={self.name}, description={self.description}, embedding_model={self.embedding_model}, chunking_method={self.chunking_method}, date_created={self.date_created}, user_id={self.user_id}, namespace={self.namespace})"

class Conversation(Document):
    """A conversation made between a user and a chatbot, it belongs to the chatbot"""
    conversation_title = StringField(required=False, default="New Conversation")
    chatbot = ReferenceField(ChatBots, required=True)
    created_at = DateTimeField(required=True)
    updated_at = DateTimeField(required=True)
    meta = {
        'collection': 'conversations',
        'indexes': [
            {'fields': ['conversation_title']},
            {'fields': ['chatbot']},
            {'fields': ['created_at']},
            {'fields': ['updated_at']}
        ]
    }

    def __str__(self) -> str:
        return f"Conversation(conversation_title={self.conversation_title}, chatbot={self.chatbot}, created_at={self.created_at}, updated_at={self.updated_at})"

class Messages(Document):
    """A message made between a user and a chatbot, it belongs to the conversation"""
    conversation_id = ReferenceField(Conversation, required=True)
    message = StringField(required=True)
    role = StringField(required=True, choices=['user', 'agent'])
    created_at = DateTimeField(required=True)

    meta = {
        'collection': 'messages',
        'indexes': [
            {'fields': ['conversation_id']},
            {'fields': ['created_at']},
            {'fields': ['role']},
        ]
    }

    def __str__(self) -> str:
        return f"Messages(conversation_id={self.conversation_id}, message={self.message}, role={self.role}, created_at={self.created_at})"

class ConversationSession(Document):
    """Active conversation sessions for real-time conversations"""
    user_id = ReferenceField(User_Auth_Table, required=True)
    chatbot_id = ReferenceField(ChatBots, required=True) # The chatbot that the conversation belongs to
    conversation_id = ReferenceField(Conversation, required=True)
    session_id = StringField(required=True, unique=True)  # UUID for WebSocket connection
    created_at = DateTimeField(required=True)
    last_activity = DateTimeField(required=True)
    is_active = BooleanField(required=True, default=True)

    meta = {
        'collection': 'conversation_sessions',
        'indexes': [
            {'fields': ['user_id']},
            {'fields': ['chatbot_id']},
            {'fields': ['session_id'], 'unique': True},
            {'fields': ['created_at']},
            {'fields': ['last_activity']},
            {'fields': ['is_active']},
            {'fields': [('user_id', 1), ('is_active', 1)]},  # For finding active user sessions
        ]
    }

    def __str__(self) -> str:
        return f"ConversationSession(user_id={self.user_id}, chatbot_id={self.chatbot_id}, session_id={self.session_id}, is_active={self.is_active})"

class Documents(Document):
    user = ReferenceField(User_Auth_Table, required=True)
    file_name = StringField(required=True)
    file_type = StringField(required=True)
    gridfs_file_id = ObjectIdField(
        required=True, unique=True)  # Link to GridFS ObjectId
    status = StringField(required=True, choices=['pending', 'processed', 'failed'])
    full_hash = StringField(required=True) # SHA256 hash
    namespace = StringField(required=True)
    chunking_method = StringField(required=False, choices=['token', 'semantic', 'line', 'recursive'], default='token')
    created_at = DateTimeField(required=True)

    meta = {
        'collection': 'documents',
        'indexes': [
            {'fields': ['user']},
            {'fields': ['gridfs_file_id'], 'unique': True},
            {'fields': ['full_hash']},
            {'fields': ['status']},
            {'fields': ['chunking_method']},
            {'fields': ['namespace']},
            {'fields': [('user', 1), ('full_hash', 1)], 'unique': True}
        ]
    }

    def get_gridfs_file(self, fs: GridFS):
        """Get the GridFS file object"""
        try:
            return fs.get(self.gridfs_file_id)
        except Exception as e:
            print(f"Error retrieving GridFS file: {e}")
            return None

    def __str__(self) -> str:
        return f"Documents(user={self.user}, file_name={self.file_name}, file_type={self.file_type}, status={self.status}, namespace={self.namespace}, chunking_method={self.chunking_method}, created_at={self.created_at})"


class Chunks(Document):
    """Chunks table for document text chunks with vector IDs"""
    document = ReferenceField(Documents, required=True)
    user = ReferenceField(User_Auth_Table, required=True)
    namespace = StringField(required=True)
    # Denormalized from documents collection for performance
    file_name = StringField(required=True)
    # The sequential order of the chunk within the document
    chunk_index = IntField(required=True)
    content = StringField(required=True)
    summary = StringField(required=True)
    # Chunking method used to generate this chunk
    chunking_method = StringField(required=False, choices=[
        'token', 'semantic', 'line', 'recursive'], default='token')
    # Pinecone vector ID, Initially null, populated after embedding
    vector_id = StringField(required=False)
    created_at = DateTimeField(required=True)

    meta = {
        'collection': 'chunks',
        'indexes': [
            {'fields': ['document']},
            {'fields': ['user']},
            {'fields': ['vector_id']},
            {'fields': ['chunking_method']},
            # query by both document and chunk_index
            {'fields': [('document', 1), ('chunk_index', 1)]}
        ]
    }

    def __str__(self) -> str:
        return f"Chunks(document={self.document}, user={self.user}, namespace={self.namespace}, file_name={self.file_name}, chunk_index={self.chunk_index}, chunking_method={self.chunking_method}, vector_id={self.vector_id}, created_at={self.created_at})"

class ChatbotDocumentsMapper(Document):
    """Mapping table between ChatBots and Documents"""
    chatbot = ReferenceField(ChatBots, required=True)
    document = ReferenceField(Documents, required=True)
    user = ReferenceField(User_Auth_Table, required=True)
    assigned_at = DateTimeField(required=True)

    meta = {
        'collection': 'chatbot_documents_mapper',
        'indexes': [
            {'fields': ['chatbot']},
            {'fields': ['document']},
            {'fields': [('chatbot', 1), ('document', 1)], 'unique': True}
        ]
    }

    def __str__(self) -> str:
        return f"ChatbotDocumentsMapper(chatbot={self.chatbot}, document={self.document}, user={self.user}, assigned_at={self.assigned_at})"

def upload_file_to_gridfs(fs: GridFS, file_content: bytes, filename: str, content_type: str = "text/plain") -> ObjectId:
    """Upload a file to GridFS and return the file ObjectId"""
    try:
        file_id = fs.put(
            file_content,
            filename=filename,
            contentType=content_type,  # default is text/plain
            length=len(file_content),
            uploadDate=datetime.now()
        )
        return file_id
    except Exception as e:
        print(f"Error uploading file to GridFS: {e}")
        return None


def create_sample_data(client, db, fs):
    """Create sample data to test the database structure, THIS IS FOR TESTING ONLY"""
    if not client:
        return

    try:
        # Create a sample user
        user = User_Auth_Table(
            user_name="test_user",
            password="hashed_password_here",
            first_name="John",
            last_name="Doe",
            email="john.doe@example.com",
            created_at=datetime.now(),
            role="User"
        )
        user.save()
        print(f"Created user: {user}")

        # List of test files
        test_files = [  # Add your txt files for testing here
            "./test_files_for_local_db/alice_in_wonderland.txt",
            "./test_files_for_local_db/1. Eastern Philosophy Author J.S.R.L. Narayana Moorty.txt"
        ]

        for file_path in test_files:
            # Create a sample document
            with open(file_path, 'r') as file:
                file_content = file.read()

            file_hash = hashlib.sha256(
                file_content.encode('utf-8')).hexdigest()

            # Upload file to GridFS
            gridfs_file_id = upload_file_to_gridfs(
                fs, file_content.encode('utf-8'), file_path, "text/plain")

            document = Documents(
                user=user,  # Reference to the user object
                file_name=file_path,
                file_type="text/plain",
                gridfs_file_id=gridfs_file_id,  # ObjectId from GridFS
                status="processed",
                full_hash=file_hash,
                namespace="test_namespace",
                created_at=datetime.now()
            )
            document.save()
            print(f"Created document: {document}")

            # Create sample chunks
            sentences = file_content.split('. ')
            for i, sentence in enumerate(sentences):
                if sentence.strip():
                    chunk = Chunks(
                        document=document,  # Reference to the document object
                        user=user,  # Reference to the user object
                        namespace="test_namespace",
                        file_name=document.file_name,  # Denormalized for performance
                        chunk_index=i,
                        content=sentence.strip(),
                        summary=sentence.strip()[
                            # Simple summary
                            :100] + "..." if len(sentence.strip()) > 100 else sentence.strip(),
                        vector_id=None,  # Initially null, will be populated after embedding
                        created_at=datetime.now()
                    )
                    chunk.save()
                    print(f"Created chunk {i}: {chunk}")

            print(
                f"\n=== Sample Data Created Successfully for {file_path} ===")
            print(f"User ID: {user.id}")
            print(f"Document ID: {document.id}")
            print(f"GridFS File ID: {gridfs_file_id}")
            print(f"Number of chunks created: {len(sentences)}")

        return user.id, document.id, gridfs_file_id

    except Exception as e:
        print(f"Error creating sample data: {e}")
    finally:
        client.close()

##############################################################################################################################
##############################################################################################################################


if __name__ == "__main__":
    print("=== MongoDB Database Initialization Script ===")

    client, db, fs = initialize_db()  # call this to initialize the database
    # MongoDB will when data are added to it
    if client:
        print("Database connection established")

        print("\nCreating sample data...")
        create_sample_data(client, db, fs)

        client.close()
        print("\nDatabase initialization complete!")

    else:
        print("Failed to initialize database")
