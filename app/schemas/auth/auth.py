"""
Pydantic schemas for authentication.
Handles login, token management, and registration flows.
"""
from pydantic import BaseModel, EmailStr, ConfigDict


class Token(BaseModel):
    """JWT token response schema."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer"
            }
        }
    )


class TokenPayload(BaseModel):
    """JWT token payload schema."""
    sub: str  # Subject (user_id)
    exp: int  # Expiration timestamp
    type: str  # Token type (access/refresh)


class LoginRequest(BaseModel):
    """Login request schema."""
    email: EmailStr
    password: str
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "user@example.com",
                "password": "strongpassword123"
            }
        }
    )


class RefreshTokenRequest(BaseModel):
    """Refresh token request schema."""
    refresh_token: str
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            }
        }
    )
