# RAG Chatbot Pipeline API

A FastAPI server that provides endpoints for creating AI agents with document processing, chunking, summarization, and embedding generation capabilities.

## 🚀 Features

- **User Management**: Registration, authentication with JWT tokens
- **Agent Creation**: Complete workflow from document upload to vector embeddings
- **Document Processing**: Support for PDF, DOCX, TXT, and CSV files
- **Multiple Chunking Methods**: Token-based, semantic, line-based, and recursive chunking
- **AI Summarization**: Automatic chunk summarization using OpenAI GPT models
- **Vector Embeddings**: Support for OpenAI and Google Gemini embedding models
- **Database Integration**: MongoDB with GridFS for file storage
- **Vector Database**: Pinecone integration for similarity search

## 📋 Prerequisites

- Python 3.8+
- MongoDB running locally or remotely
- OpenAI API key (required)
- Pinecone API key (for embedding storage)
- Google API key (optional, for Gemini embeddings)

## 🛠️ Installation

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Environment Variables**
   Create a `.env` file with the following variables:
   ```bash
   # Required
   OPENAI_API_KEY=your_openai_api_key_here
   
   # Optional (will use defaults if not set)
   JWT_SECRET_KEY=your_jwt_secret_key_here
   MONGODB_URL=mongodb://localhost:50000/
   HOST=0.0.0.0
   PORT=8000
   RELOAD=true
   
   # For Pinecone (if using embeddings)
   PINECONE_API_KEY=your_pinecone_api_key_here
   PINECONE_ENVIRONMENT=your_pinecone_environment
   
   # For Google Gemini (if using Gemini embeddings)
   GOOGLE_API_KEY=your_google_api_key_here
   ```

3. **Start the Server**
   ```bash
   # Using the startup script (recommended)
   python start_server.py
   
   # Or directly with uvicorn
   uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```

## 📚 API Documentation

Once the server is running, visit:
- **Interactive API Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🔗 API Endpoints

### Authentication

#### POST `/signin`
Register a new user.

**Request Body:**
```json
{
  "user_name": "john_doe",
  "password": "secure_password",
  "first_name": "John",
  "last_name": "Doe",
  "email": "john@example.com",
  "role": "User"
}
```

#### POST `/login`
Authenticate user and get JWT token.

**Request Body:**
```json
{
  "username": "john_doe",
  "password": "secure_password"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": "user_id",
    "user_name": "john_doe",
    "first_name": "John",
    "last_name": "Doe",
    "email": "john@example.com",
    "created_at": "2024-01-01T12:00:00"
  }
}
```

### Agent Management

#### POST `/create_agent`
Create a new AI agent with document processing.

**Content-Type:** `multipart/form-data`

**Form Fields:**
- `agent_provider` (optional): "Gemini", "OpenAI", or null (null = super user)
- `chunking_method` (super users only): "token", "semantic", "line", "recursive"
- `embedding_model` (super users only): "text-embedding-3-small", "gemini-embedding-001"
- `user_name`: Username for the agent
- `password`: Password
- `first_name`: First name
- `last_name`: Last name
- `email`: Email address
- `agent_description`: Description of the agent's purpose
- `files`: Document files (PDF, DOCX, TXT, CSV)

**Response:**
```json
{
  "success": true,
  "message": "Agent created successfully",
  "user": { /* user object */ },
  "namespace": "john_doe_support_bot_20241201_120000",
  "processing_results": {
    "total_files": 3,
    "processed": 3,
    "failed": 0,
    "chunks_created": 45,
    "processing_time": 23.5
  },
  "embedding_results": {
    "total_chunks_embedded": 45,
    "total_chunks_updated": 45,
    "processing_time": 12.3
  },
  "total_time": 35.8
}
```

### User Information

#### GET `/me`
Get current user information (requires authentication).

**Headers:**
```
Authorization: Bearer your_jwt_token_here
```

## 👥 User Types

### Normal Users
- **agent_provider**: Must specify "Gemini" or "OpenAI"
- **chunking_method**: Automatically determined based on provider
- **embedding_model**: Automatically determined based on provider
- Limited to predefined configurations

### Super Users
- **agent_provider**: null
- **chunking_method**: Can specify any supported method
- **embedding_model**: Can specify any supported model
- Full control over processing parameters

## 🗂️ Supported File Types

| Extension | MIME Type | Description |
|-----------|-----------|-------------|
| `.pdf` | `application/pdf` | PDF documents |
| `.docx` | `application/vnd.openxmlformats-officedocument.wordprocessingml.document` | Word documents |
| `.txt` | `text/plain` | Plain text files |
| `.csv` | `text/csv`, `application/csv` | CSV data files |

## 🧩 Chunking Methods

1. **Token-based** (`token`): Split by token count, good for general use
2. **Semantic** (`semantic`): Split by meaning, requires OpenAI embeddings
3. **Line-based** (`line`): Split by line count, good for structured text
4. **Recursive** (`recursive`): Character-based recursive splitting

## 🤖 Embedding Models

1. **OpenAI**: `text-embedding-3-small` (high quality, requires OpenAI API key)
2. **Gemini**: `gemini-embedding-001` (Google's model, requires Google API key)

## 📊 Database Schema

The API uses MongoDB with the following collections:

- **user_auth_table**: User authentication and profile data
- **documents**: Document metadata and GridFS references
- **chunks**: Text chunks with summaries and vector IDs

Files are stored in MongoDB GridFS for efficient handling of large documents.

## 🔒 Security

- JWT-based authentication
- Password hashing with bcrypt
- Input validation with Pydantic models
- File type and size validation
- Database input sanitization

## 🐛 Error Handling

The API provides detailed error responses:

```json
{
  "detail": "Error description",
  "error_code": "400",
  "timestamp": "2024-01-01T12:00:00"
}
```

Common error codes:
- `400`: Bad Request (validation errors)
- `401`: Unauthorized (authentication required)
- `409`: Conflict (user already exists)
- `500`: Internal Server Error

## 📈 Performance

- Parallel document processing (configurable workers)
- Rate limiting for AI API calls
- Asynchronous processing for better throughput
- Efficient file handling with streaming uploads

## 🔧 Configuration

Environment variables for fine-tuning:

```bash
# Server settings
HOST=0.0.0.0
PORT=8000
RELOAD=true

# Database settings
MONGODB_URL=mongodb://localhost:27017/

# Processing settings
MAX_WORKERS=4
RATE_LIMIT_DELAY=0.2

# AI API settings
OPENAI_API_KEY=required
GOOGLE_API_KEY=optional
SUMMARY_MODEL=gpt-4.1-mini
SUMMARY_RPM=2000

# JWT settings
JWT_SECRET_KEY=your_secret_key
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

## 📝 Example Usage

### Using curl

1. **Register a user:**
```bash
curl -X POST "http://localhost:8000/signin" \
  -H "Content-Type: application/json" \
  -d '{
    "user_name": "john_doe",
    "password": "secure_password",
    "first_name": "John",
    "last_name": "Doe",
    "email": "john@example.com",
    "role": "User"
  }'
```

2. **Create an agent:**
```bash
curl -X POST "http://localhost:8000/create_agent" \
  -F "agent_provider=OpenAI" \
  -F "user_name=jane_doe" \
  -F "password=another_password" \
  -F "first_name=Jane" \
  -F "last_name=Doe" \
  -F "email=jane@example.com" \
  -F "agent_description=Customer support chatbot" \
  -F "files=@document1.pdf" \
  -F "files=@document2.docx"
```

### Using Python requests

```python
import requests

# Register user
response = requests.post("http://localhost:8000/signin", json={
    "user_name": "john_doe",
    "password": "secure_password",
    "first_name": "John",
    "last_name": "Doe",
    "email": "john@example.com",
    "role": "User"
})

# Create agent
files = [
    ('files', ('doc1.pdf', open('doc1.pdf', 'rb'), 'application/pdf')),
    ('files', ('doc2.txt', open('doc2.txt', 'rb'), 'text/plain')),
]

data = {
    'agent_provider': 'OpenAI',
    'user_name': 'jane_doe',
    'password': 'another_password',
    'first_name': 'Jane',
    'last_name': 'Doe',
    'email': 'jane@example.com',
    'agent_description': 'Customer support chatbot'
}

response = requests.post("http://localhost:8000/create_agent", files=files, data=data)
```

## 🚀 Deployment

For production deployment:

1. **Set secure environment variables**
2. **Use a proper WSGI server** (e.g., Gunicorn)
3. **Configure reverse proxy** (e.g., Nginx)
4. **Set up SSL/TLS certificates**
5. **Configure MongoDB with authentication**
6. **Set up monitoring and logging**

Example production command:
```bash
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

## 📞 Support

For issues and questions:
1. Check the API documentation at `/docs`
2. Review error messages and status codes
3. Ensure all environment variables are set correctly
4. Verify MongoDB and external API connections