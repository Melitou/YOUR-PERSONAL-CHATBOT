# FastAPI RAG Pipeline Setup Guide

This guide will help you set up and run the FastAPI server for the RAG Chatbot Pipeline.

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Set Up Environment Variables
Create a `.env` file in the backend directory:
```bash
# Required
OPENAI_API_KEY=your_openai_api_key_here

# Optional (defaults will be used if not set)
JWT_SECRET_KEY=your_secure_jwt_secret_key
MONGODB_URL=mongodb://localhost:50000/
HOST=0.0.0.0
PORT=8000
RELOAD=true

# For Pinecone vector storage
PINECONE_API_KEY=your_pinecone_api_key
PINECONE_ENVIRONMENT=your_pinecone_environment

# For Google Gemini embeddings (optional)
GOOGLE_API_KEY=your_google_api_key
```

### 3. Start MongoDB
Make sure MongoDB is running:
```bash
# Using Docker (port 50000 to avoid conflicts)
docker run -d -p 50000:27017 --name mongodb-rag mongo:latest

# Or if installed locally on different port
mongod --port 50000
```

### 4. Test the Setup
```bash
python test_api.py
```

### 5. Start the Server
```bash
python start_server.py
```

### 6. Access the API
- **Interactive Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/

## 📋 System Requirements

- **Python**: 3.8 or higher
- **MongoDB**: 4.4 or higher
- **Memory**: At least 4GB RAM (8GB recommended for processing large documents)
- **Storage**: Sufficient space for uploaded documents and vector embeddings

## 🔧 Configuration Options

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | ✅ | - | OpenAI API key for document processing |
| `JWT_SECRET_KEY` | ❌ | Auto-generated | Secret key for JWT tokens |
| `MONGODB_URL` | ❌ | `mongodb://localhost:50000/` | MongoDB connection string |
| `HOST` | ❌ | `0.0.0.0` | Server host address |
| `PORT` | ❌ | `8000` | Server port |
| `RELOAD` | ❌ | `true` | Auto-reload on code changes |
| `PINECONE_API_KEY` | ❌ | - | Pinecone API key for vector storage |
| `PINECONE_ENVIRONMENT` | ❌ | - | Pinecone environment |
| `GOOGLE_API_KEY` | ❌ | - | Google API key for Gemini embeddings |

### Processing Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `MAX_WORKERS` | `4` | Maximum parallel processing workers |
| `RATE_LIMIT_DELAY` | `0.2` | Delay between database operations (seconds) |
| `SUMMARY_MODEL` | `gpt-4.1-mini` | OpenAI model for chunk summarization |
| `SUMMARY_RPM` | `2000` | Summary requests per minute limit |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | JWT token expiration time |

## 🗂️ File Structure

After setup, your backend directory should contain:

```
backend/
├── main.py                  # FastAPI application
├── api_models.py           # Pydantic models for validation
├── auth_utils.py           # Authentication utilities
├── pipeline_handler.py     # Pipeline integration handler
├── start_server.py         # Server startup script
├── test_api.py            # Test script
├── requirements.txt        # Python dependencies
├── README_API.md          # API documentation
├── SETUP_GUIDE.md         # This file
├── master_pipeline.py      # Existing pipeline code
├── db_service.py          # Database models
├── [other existing files...] # Other pipeline components
└── test_uploads/          # Example files (created by test script)
    ├── example.txt
    └── example.csv
```

## 🧪 Testing the Setup

### 1. Run Component Tests
```bash
python test_api.py
```

This will test:
- API model imports and validation
- Authentication utilities
- Database model structure
- Pipeline handler imports
- Create example files for testing

### 2. Test API Endpoints

Once the server is running, you can test endpoints using:

#### Using curl:
```bash
# Health check
curl http://localhost:8000/

# Register user
curl -X POST "http://localhost:8000/signin" \
  -H "Content-Type: application/json" \
  -d '{
    "user_name": "test_user",
    "password": "test_password123",
    "first_name": "Test",
    "last_name": "User",
    "email": "test@example.com",
    "role": "User"
  }'

# Login
curl -X POST "http://localhost:8000/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "test_user",
    "password": "test_password123"
  }'
```

#### Using the Interactive Docs:
1. Go to http://localhost:8000/docs
2. Try the endpoints interactively
3. Use the "Try it out" button for each endpoint

### 3. Test Agent Creation

```bash
# Create agent with example files
curl -X POST "http://localhost:8000/create_agent" \
  -F "agent_provider=OpenAI" \
  -F "user_name=agent_user" \
  -F "password=agent_password123" \
  -F "first_name=Agent" \
  -F "last_name=User" \
  -F "email=agent@example.com" \
  -F "agent_description=Test chatbot for documentation" \
  -F "files=@test_uploads/example.txt" \
  -F "files=@test_uploads/example.csv"
```

## 🔍 Troubleshooting

### Common Issues

1. **Import Errors**
   ```
   Solution: pip install -r requirements.txt
   ```

2. **MongoDB Connection Failed**
   ```
   Error: Failed to initialize database
   Solution: 
   - Start MongoDB service
   - Check MONGODB_URL in .env file
   - Verify MongoDB is accessible
   ```

3. **OpenAI API Errors**
   ```
   Error: OPENAI_API_KEY environment variable not set
   Solution: Add valid OpenAI API key to .env file
   ```

4. **Port Already in Use**
   ```
   Error: Address already in use
   Solution: 
   - Change PORT in .env file
   - Or stop the service using the port
   ```

5. **File Upload Errors**
   ```
   Error: Unsupported file type
   Solution: Use only PDF, DOCX, TXT, or CSV files
   ```

### Debug Mode

To run with debug information:

```bash
# Set log level to debug
export LOG_LEVEL=DEBUG
python start_server.py
```

### Check Logs

The server logs will show:
- Startup information
- Request processing
- Error details
- Database operations

## 🚀 Production Deployment

For production deployment:

1. **Security**
   - Use strong JWT secret key
   - Set up MongoDB authentication
   - Configure SSL/TLS certificates
   - Use environment variables for secrets

2. **Performance**
   - Use Gunicorn or similar WSGI server
   - Configure reverse proxy (Nginx)
   - Set up load balancing
   - Monitor resource usage

3. **Monitoring**
   - Set up application logging
   - Monitor API response times
   - Track database performance
   - Set up alerts for errors

Example production command:
```bash
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

## 📞 Getting Help

1. **Check the logs** for detailed error messages
2. **Verify environment variables** are set correctly
3. **Test individual components** using test_api.py
4. **Review the API documentation** at /docs
5. **Check database connectivity** with MongoDB client

For detailed API usage, see `README_API.md`.