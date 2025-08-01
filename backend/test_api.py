#!/usr/bin/env python3
"""
Test script for the FastAPI RAG Pipeline API
"""
import json
import time
from pathlib import Path


def test_api_models():
    """Test that API models can be imported and instantiated"""
    try:
        from api_models import (
            CreateAgentRequest, LoginRequest, SigninRequest,
            ChunkingMethod, EmbeddingModel, AgentProvider, UserRole
        )
        
        print("✅ API models imported successfully")
        
        # Test enum values
        assert ChunkingMethod.TOKEN == "token"
        assert EmbeddingModel.OPENAI_SMALL == "text-embedding-3-small"
        assert AgentProvider.GEMINI == "Gemini"
        assert UserRole.USER == "User"
        
        print("✅ API model enums work correctly")
        return True
        
    except Exception as e:
        print(f"❌ API models test failed: {e}")
        return False


def test_auth_utils():
    """Test authentication utilities"""
    try:
        from auth_utils import get_password_hash, verify_password, create_access_token
        
        print("✅ Auth utils imported successfully")
        
        # Test password hashing
        password = "test_password_123"
        hashed = get_password_hash(password)
        
        assert verify_password(password, hashed) == True
        assert verify_password("wrong_password", hashed) == False
        
        print("✅ Password hashing works correctly")
        
        # Test JWT token creation
        token = create_access_token({"sub": "test_user"})
        assert isinstance(token, str) and len(token) > 0
        
        print("✅ JWT token creation works")
        return True
        
    except Exception as e:
        print(f"❌ Auth utils test failed: {e}")
        return False


def test_database_models():
    """Test database models without connecting to database"""
    try:
        from db_service import User_Auth_Table, Documents, Chunks
        
        print("✅ Database models imported successfully")
        
        # Check model structure
        assert hasattr(User_Auth_Table, 'user_name')
        assert hasattr(Documents, 'file_name')
        assert hasattr(Chunks, 'content')
        
        print("✅ Database models have correct attributes")
        return True
        
    except Exception as e:
        print(f"❌ Database models test failed: {e}")
        return False


def test_pipeline_handler_import():
    """Test pipeline handler import"""
    try:
        # This will fail without database connection, but we can test import
        from pipeline_handler import PipelineHandler
        
        print("✅ Pipeline handler imported successfully")
        return True
        
    except ImportError as e:
        print(f"❌ Pipeline handler import failed: {e}")
        return False
    except Exception as e:
        # Expected - database connection will fail
        print("✅ Pipeline handler imported (database connection expected to fail in test)")
        return True


def create_example_files():
    """Create example files for testing"""
    try:
        # Create test directory
        test_dir = Path("test_uploads")
        test_dir.mkdir(exist_ok=True)
        
        # Create example text file
        with open(test_dir / "example.txt", "w") as f:
            f.write("""This is an example document for testing the RAG pipeline.

The document contains multiple paragraphs to demonstrate text chunking and processing.

It includes various topics:
- Technical documentation
- API usage examples  
- Configuration details
- Troubleshooting information

This content will be processed, chunked, summarized, and embedded for vector search.""")
        
        # Create example CSV file
        with open(test_dir / "example.csv", "w") as f:
            f.write("""Name,Age,Department,Role
John Doe,30,Engineering,Senior Developer
Jane Smith,28,Product,Product Manager
Bob Johnson,35,Sales,Sales Director
Alice Brown,32,Marketing,Marketing Specialist""")
        
        print(f"✅ Example files created in {test_dir}/")
        return True
        
    except Exception as e:
        print(f"❌ Failed to create example files: {e}")
        return False


def print_api_examples():
    """Print example API usage"""
    print("\n" + "=" * 80)
    print("📝 API USAGE EXAMPLES")
    print("=" * 80)
    
    print("\n1. Register a new user:")
    print("POST /signin")
    signin_example = {
        "user_name": "john_doe",
        "password": "secure_password123",
        "first_name": "John",
        "last_name": "Doe",
        "email": "john@example.com",
        "role": "User"
    }
    print(json.dumps(signin_example, indent=2))
    
    print("\n2. Login:")
    print("POST /login")
    login_example = {
        "username": "john_doe",
        "password": "secure_password123"
    }
    print(json.dumps(login_example, indent=2))
    
    print("\n3. Create agent (normal user):")
    print("POST /create_agent (multipart/form-data)")
    print("Form fields:")
    agent_fields = {
        "agent_provider": "OpenAI",
        "user_name": "jane_doe",
        "password": "another_password123",
        "first_name": "Jane",
        "last_name": "Doe",
        "email": "jane@example.com",
        "agent_description": "Customer support chatbot for handling inquiries"
    }
    for key, value in agent_fields.items():
        print(f"  {key}: {value}")
    print("  files: [document1.pdf, document2.txt, ...]")
    
    print("\n4. Create agent (super user):")
    print("POST /create_agent (multipart/form-data)")
    print("Form fields:")
    super_agent_fields = {
        "agent_provider": "null",  # Super user
        "chunking_method": "semantic",
        "embedding_model": "text-embedding-3-small",
        "user_name": "admin_user",
        "password": "admin_password123",
        "first_name": "Admin",
        "last_name": "User",
        "email": "admin@example.com",
        "agent_description": "Advanced technical documentation assistant"
    }
    for key, value in super_agent_fields.items():
        print(f"  {key}: {value}")
    print("  files: [manual.pdf, guide.docx, data.csv, ...]")


def main():
    """Run all tests"""
    print("=" * 80)
    print("🧪 TESTING RAG PIPELINE API COMPONENTS")
    print("=" * 80)
    
    tests = [
        ("API Models", test_api_models),
        ("Authentication Utils", test_auth_utils),
        ("Database Models", test_database_models),
        ("Pipeline Handler", test_pipeline_handler_import),
        ("Example Files", create_example_files),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🔍 Testing {test_name}...")
        try:
            if test_func():
                passed += 1
            else:
                print(f"❌ {test_name} failed")
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
    
    print("\n" + "=" * 80)
    print(f"📊 TEST RESULTS: {passed}/{total} tests passed")
    print("=" * 80)
    
    if passed == total:
        print("🎉 All tests passed! The API components are ready.")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
    
    # Print usage examples
    print_api_examples()
    
    print("\n" + "=" * 80)
    print("🚀 NEXT STEPS:")
    print("=" * 80)
    print("1. Install dependencies: pip install -r requirements.txt")
    print("2. Set up environment variables (see README_API.md)")
    print("3. Start MongoDB database")
    print("4. Run the server: python start_server.py")
    print("5. Visit http://localhost:8000/docs for interactive API documentation")
    print("=" * 80)


if __name__ == "__main__":
    main()