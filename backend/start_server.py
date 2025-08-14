#!/usr/bin/env python3
"""
Startup script for the FastAPI RAG Pipeline Server
"""
import os
import sys
import subprocess
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


def check_requirements():
    """Check if all required packages are installed"""
    required_packages = [
        "fastapi", "uvicorn", "python-multipart", "pydantic",
        "python-jose", "passlib", "mongoengine", "pymongo"
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print("❌ Missing required packages:")
        for package in missing_packages:
            print(f"   - {package}")
        print("\n💡 Install missing packages with:")
        print(f"   pip install {' '.join(missing_packages)}")
        return False
    
    return True


def main():
    """Main startup function"""
    print("=" * 80)
    print("🚀 RAG CHATBOT PIPELINE API SERVER STARTUP")
    print("=" * 80)
    
    # Check if we're in the right directory
    if not Path("main.py").exists():
        print("❌ Error: main.py not found in current directory")
        print("💡 Please run this script from the backend directory")
        sys.exit(1)
    
    # Check requirements
    print("🔍 Checking requirements...")
    # if not check_requirements():
    #     sys.exit(1)
    # print("✅ All requirements satisfied")
    print("✅ Requirements checking skipped")
    
    # Check environment variables
    print("\n🔧 Checking environment...")
    env_vars = {
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
        "JWT_SECRET_KEY": os.getenv("JWT_SECRET_KEY")
    }
    
    missing_env = []
    for var, description in env_vars.items():
        if not os.getenv(var):
            missing_env.append((var, description))
    
    if missing_env:
        print("⚠️  Missing environment variables:")
        for var, desc in missing_env:
            print(f"   - {var}: {desc}")
        print("\n💡 Set environment variables in a .env file or your shell")
        if any(var == "OPENAI_API_KEY" for var, _ in missing_env):
            print("❌ OPENAI_API_KEY is required for document processing")
            sys.exit(1)
    else:
        print("✅ Environment configuration OK")
    
    # Get server configuration
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    reload = os.getenv("RELOAD", "true").lower() == "true"
    
    print(f"\n📡 Server Configuration:")
    print(f"   Host: {host}")
    print(f"   Port: {port}")
    print(f"   Reload: {reload}")
    
    # Check if port is available
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        if s.connect_ex((host, port)) == 0:
            print(f"⚠️  Port {port} is already in use")
            response = input("Continue anyway? (y/N): ").strip().lower()
            if response != 'y':
                print("❌ Startup cancelled")
                sys.exit(1)
    
    print("\n" + "=" * 80)
    print("🚀 STARTING SERVER...")
    print("=" * 80)
    print(f"📖 API Documentation: http://{host}:{port}/docs")
    print(f"🔗 ReDoc: http://{host}:{port}/redoc")
    print("=" * 80)
    
    # Start the server
    try:
        cmd = [
            sys.executable, "-m", "uvicorn", "main:app",
            "--host", host,
            "--port", str(port)
        ]
        
        if reload:
            cmd.append("--reload")
        
        subprocess.run(cmd)
        
    except KeyboardInterrupt:
        print("\n\n✅ Server stopped by user")
    except Exception as e:
        print(f"\n❌ Error starting server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()