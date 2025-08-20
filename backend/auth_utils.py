"""
Authentication utilities for the FastAPI server
"""
import os
from datetime import datetime, timedelta
import random
import string
from typing import Optional
from passlib.context import CryptContext
from jose import JWTError, jwt
from fastapi import HTTPException, status
from db_service import User_Auth_Table


# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT settings
SECRET_KEY = os.getenv("JWT_SECRET_KEY", None)

if SECRET_KEY is None:
    SECRET_KEY = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(64))

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> dict:
    """Verify and decode a JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


def authenticate_user(username: str, password: str) -> Optional[User_Auth_Table]:
    """Authenticate a user by username and password"""
    try:
        user = User_Auth_Table.objects(user_name=username).first()
        if not user:
            return None
        
        if not verify_password(password, user.password):
            return None
        
        return user
    except Exception as e:
        print(f"Error authenticating user: {e}")
        return None


def get_user_by_username(username: str) -> Optional[User_Auth_Table]:
    """Get user by username"""
    try:
        return User_Auth_Table.objects(user_name=username).first()
    except Exception as e:
        print(f"Error getting user by username: {e}")
        return None


def create_user(user_data: dict) -> User_Auth_Table:
    """Create a new user"""
    try:
        # Hash the password
        hashed_password = get_password_hash(user_data["password"])
        
        # Create user object
        user = User_Auth_Table(
            user_name=user_data["user_name"],
            password=hashed_password,
            first_name=user_data["first_name"],
            last_name=user_data["last_name"],
            email=user_data["email"],
            created_at=datetime.now(),
            role=user_data.get("role", "User")  # Default to "User" if not specified
        )
        
        # Save to database
        user.save()
        return user
        
    except Exception as e:
        print(f"Error creating user: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error creating user: {str(e)}"
        )


def check_user_exists(username: str = None, email: str = None) -> bool:
    """Check if a user already exists by username or email"""
    try:
        if username:
            user = User_Auth_Table.objects(user_name=username).first()
            if user:
                return True
        
        if email:
            user = User_Auth_Table.objects(email=email).first()
            if user:
                return True
        
        return False
    except Exception as e:
        print(f"Error checking user existence: {e}")
        return False