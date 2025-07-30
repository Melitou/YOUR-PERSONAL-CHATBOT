from datetime import datetime
from mongoengine import connect, Document, StringField, DateTimeField, IntField, ReferenceField, ObjectIdField
from bson import ObjectId
from pymongo import MongoClient
from gridfs import GridFS
import hashlib


def initialize_db(db_url: str = "mongodb://localhost:27017/"):
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

    meta = {
        'collection': 'user_auth_table',
        'indexes': [
            {'fields': ['email'], 'unique': True},
            {'fields': ['user_name'], 'unique': True}
        ]
    }

    def __str__(self) -> str:
        return f"User_Auth_Table(user_name={self.user_name}, first_name={self.first_name}, last_name={self.last_name}, email={self.email})"


class Documents(Document):
    user = ReferenceField(User_Auth_Table, required=True)
    file_name = StringField(required=True)
    file_type = StringField(required=True)
    gridfs_file_id = ObjectIdField(
        required=True, unique=True)  # Link to GridFS ObjectId
    status = StringField(required=True, choices=[
                         'pending', 'processed', 'failed'])
    full_hash = StringField(required=True)  # SHA256 hash
    namespace = StringField(required=True)
    created_at = DateTimeField(required=True)

    meta = {
        'collection': 'documents',
        'indexes': [
            {'fields': ['user']},
            {'fields': ['gridfs_file_id'], 'unique': True},
            {'fields': ['full_hash']},
            {'fields': ['status']},
            # Composite unique index
            # Same user can't upload same file twice
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
        return f"Documents(user={self.user}, file_name={self.file_name}, file_type={self.file_type}, status={self.status}, namespace={self.namespace}, created_at={self.created_at})"


class Chunks(Document):
    """Chunks table for document text chunks with vector IDs"""
    document = ReferenceField(Documents, required=True)
    user = ReferenceField(User_Auth_Table, required=True)
    namespace = StringField(required=True)
    # The sequential order of the chunk within the document
    chunk_index = IntField(required=True)
    content = StringField(required=True)
    summary = StringField(required=True)
    # Pinecone vector ID, Initially null, populated after embedding
    vector_id = StringField(required=False)
    created_at = DateTimeField(required=True)

    meta = {
        'collection': 'chunks',
        'indexes': [
            {'fields': ['document']},
            {'fields': ['user']},
            {'fields': ['vector_id']},
            # query by both document and chunk_index
            {'fields': [('document', 1), ('chunk_index', 1)]}
        ]
    }

    def __str__(self) -> str:
        return f"Chunks(document={self.document}, user={self.user}, namespace={self.namespace}, chunk_index={self.chunk_index}, vector_id={self.vector_id}, created_at={self.created_at})"


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
            created_at=datetime.now()
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
