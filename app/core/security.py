"""
Security utilities for JWT token management and password hashing.
Production-grade implementation with proper error handling.
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.core.config import settings

# bcrypt_sha256: SHA-256 then bcrypt — supports passwords >72 bytes safely.
# bcrypt: retained so existing $2b$ hashes keep verifying.
pwd_context = CryptContext(
    schemes=["bcrypt_sha256", "bcrypt"],
    deprecated="auto",
)


class SecurityService:
    """Centralized security service for authentication operations."""
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """
        Verify a plain password against a hashed password.
        
        Args:
            plain_password: The plain text password
            hashed_password: The hashed password from database
            
        Returns:
            True if password matches, False otherwise
        """
        return pwd_context.verify(plain_password, hashed_password)
    
    @staticmethod
    def get_password_hash(password: str) -> str:
        """
        Hash a password for secure storage.
        
        Args:
            password: Plain text password
            
        Returns:
            Hashed password string
        """
        return pwd_context.hash(password)
    
    @staticmethod
    def create_access_token(
        subject: str,
        additional_claims: Optional[Dict[str, Any]] = None,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create a JWT access token.
        
        Args:
            subject: The subject (usually user_id) for the token
            additional_claims: Additional claims to include in the token
            expires_delta: Custom expiration time
            
        Returns:
            Encoded JWT token string
        """
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(
                minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
            )
        
        to_encode = {
            "exp": expire,
            "sub": str(subject),
            "type": "access"
        }
        
        if additional_claims:
            to_encode.update(additional_claims)
        
        encoded_jwt = jwt.encode(
            to_encode,
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM
        )
        return encoded_jwt
    
    @staticmethod
    def create_refresh_token(subject: str) -> str:
        """
        Create a JWT refresh token with longer expiration.
        
        Args:
            subject: The subject (usually user_id) for the token
            
        Returns:
            Encoded JWT refresh token string
        """
        expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        
        to_encode = {
            "exp": expire,
            "sub": str(subject),
            "type": "refresh"
        }
        
        encoded_jwt = jwt.encode(
            to_encode,
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM
        )
        return encoded_jwt
    
    @staticmethod
    def decode_token(token: str) -> Optional[Dict[str, Any]]:
        """
        Decode and validate a JWT token.
        
        Args:
            token: The JWT token to decode
            
        Returns:
            Decoded token payload or None if invalid
        """
        try:
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=[settings.ALGORITHM]
            )
            return payload
        except JWTError:
            return None
    
    @staticmethod
    def verify_token_type(payload: Dict[str, Any], expected_type: str) -> bool:
        """
        Verify that the token is of the expected type (access/refresh).
        
        Args:
            payload: Decoded token payload
            expected_type: Expected token type ("access" or "refresh")
            
        Returns:
            True if token type matches, False otherwise
        """
        return payload.get("type") == expected_type

    @staticmethod
    def create_ws_session_token(session_id: str, user_id: str) -> str:
        """Short-lived token scoped to a single simulation session (WebSocket auth)."""
        expire = datetime.utcnow() + timedelta(minutes=settings.WS_SESSION_TOKEN_EXPIRE_MINUTES)
        to_encode = {
            "exp": expire,
            "sub": str(user_id),
            "session_id": str(session_id),
            "type": "ws_session",
        }
        return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    @staticmethod
    def decode_ws_session_token(token: str) -> Optional[Dict[str, Any]]:
        payload = SecurityService.decode_token(token)
        if not payload or payload.get("type") != "ws_session":
            return None
        return payload


# Create global instance
security_service = SecurityService()
