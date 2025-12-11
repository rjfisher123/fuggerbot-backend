"""
Authentication API endpoints.

Provides login/logout functionality.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel
from datetime import timedelta

from core.auth import (
    authenticate_user,
    create_access_token,
    get_current_user,
    LoginRequest,
    ACCESS_TOKEN_EXPIRE_MINUTES
)
from core.logger import logger

router = APIRouter(prefix="/api/auth", tags=["auth"])
dashboard_router = APIRouter(tags=["dashboard"])


@router.post("/login")
async def login(
    login_data: LoginRequest,
    response: Response
) -> dict:
    """
    Login endpoint.
    
    Authenticates user and sets JWT token in HTTP-only cookie.
    
    Args:
        login_data: Login credentials
        response: FastAPI response object
    
    Returns:
        Success message with user info
    
    Raises:
        HTTPException: If authentication fails
    """
    user = authenticate_user(login_data.username, login_data.password)
    if not user:
        logger.warning(f"Failed login attempt for username: {login_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["username"]},
        expires_delta=access_token_expires
    )
    
    # Set HTTP-only cookie
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=False,  # Set to True in production with HTTPS
        samesite="lax",
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )
    
    logger.info(f"User {user['username']} logged in successfully")
    
    return {
        "message": "Login successful",
        "username": user["username"],
        "access_token": access_token,  # Also return in response for API clients
        "token_type": "bearer"
    }


@router.post("/logout")
async def logout(response: Response) -> dict:
    """
    Logout endpoint.
    
    Clears the authentication cookie.
    
    Args:
        response: FastAPI response object
    
    Returns:
        Success message
    """
    response.delete_cookie(key="access_token")
    logger.info("User logged out")
    return {"message": "Logout successful"}


@router.get("/me")
async def get_current_user_info(
    current_user: dict = Depends(get_current_user)
) -> dict:
    """
    Get current user information.
    
    Args:
        current_user: Current authenticated user (from dependency)
    
    Returns:
        User information
    """
    return {
        "username": current_user["username"],
        "disabled": current_user.get("disabled", False)
    }


# Dashboard login page
@dashboard_router.get("/login", response_class=JSONResponse)
async def login_page():
    """Login page endpoint (for dashboard)."""
    return {"message": "Please POST to /api/auth/login with username and password"}





