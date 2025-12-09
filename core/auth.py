"""
JWT-based authentication for FuggerBot API.

Provides login endpoint and authentication dependency for protecting routes.
"""
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
import bcrypt
from fastapi import Depends, HTTPException, status, Cookie, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import os
from dotenv import load_dotenv

from core.logger import logger

load_dotenv()

# JWT Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "fuggerbot-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

# Security scheme
security = HTTPBearer(auto_error=False)


class LoginRequest(BaseModel):
    """Login request model."""
    username: str
    password: str


class TokenData(BaseModel):
    """Token data model."""
    username: Optional[str] = None


# Simple in-memory user store (in production, use a database)
# Default credentials: admin / admin (change in production!)
# Pre-computed bcrypt hash for "admin" password
# Generated with: python -c "import bcrypt; print(bcrypt.hashpw(b'admin', bcrypt.gensalt()).decode('utf-8'))"
ADMIN_PASSWORD_HASH = "$2b$12$5qRW4PDcobcG8CS9Rdf8Z.Kl/EcApOx6nYBGc.FKk87ic9vkXSPOe"

def _init_users_db():
    """Initialize users database with hashed passwords."""
    return {
        "admin": {
            "username": "admin",
            "hashed_password": ADMIN_PASSWORD_HASH,  # Pre-computed hash for "admin"
            "disabled": False
        }
    }

USERS_DB = None

def get_users_db():
    """Get users database, initializing if needed."""
    global USERS_DB
    if USERS_DB is None:
        USERS_DB = _init_users_db()
    return USERS_DB


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a bcrypt hash."""
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def get_user(username: str):
    """Get user from database."""
    return get_users_db().get(username)


def authenticate_user(username: str, password: str) -> Optional[dict]:
    """
    Authenticate a user.
    
    Args:
        username: Username
        password: Plain text password
    
    Returns:
        User dict if authenticated, None otherwise
    """
    user = get_user(username)
    if not user:
        return None
    if not verify_password(password, user["hashed_password"]):
        return None
    if user.get("disabled", False):
        return None
    return user


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.
    
    Args:
        data: Data to encode in token
        expires_delta: Optional expiration time delta
    
    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> Optional[TokenData]:
    """
    Verify and decode a JWT token.
    
    Args:
        token: JWT token string
    
    Returns:
        TokenData if valid, None otherwise
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
        token_data = TokenData(username=username)
        return token_data
    except JWTError:
        return None


async def get_current_user(
    access_token: Optional[str] = Cookie(None),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> dict:
    """
    Get current authenticated user from JWT token.
    
    Checks both cookie (access_token) and Authorization header.
    
    Args:
        access_token: JWT token from cookie
        credentials: HTTPBearer credentials from Authorization header
    
    Returns:
        User dict
    
    Raises:
        HTTPException: If authentication fails
    """
    token = None
    
    # Check cookie first
    if access_token:
        token = access_token
    # Check Authorization header
    elif credentials:
        token = credentials.credentials
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token_data = verify_token(token)
    if token_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = get_user(username=token_data.username)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if user.get("disabled", False):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User is disabled",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user


# Dependency for protected routes
async def require_auth(current_user: dict = Depends(get_current_user)) -> dict:
    """
    Dependency that requires authentication.
    
    Use this in route dependencies to protect endpoints.
    
    Example:
        @router.post("/protected")
        async def protected_route(user: dict = Depends(require_auth)):
            ...
    """
    return current_user

