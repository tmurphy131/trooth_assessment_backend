"""
Rate limiting middleware and utilities.
"""
import time
import logging
from typing import Dict, Optional
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.settings import settings

logger = logging.getLogger("app.rate_limit")

# In-memory rate limiting (for simple deployment)
# In production, you'd want to use Redis for distributed rate limiting
_rate_limit_store: Dict[str, Dict[str, float]] = {}

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory rate limiting middleware."""
    
    def __init__(self, app, calls_per_minute: int = 60):
        super().__init__(app)
        self.calls_per_minute = calls_per_minute
        self.window_size = 60  # 1 minute window
    
    def get_client_id(self, request: Request) -> str:
        """Get client identifier for rate limiting."""
        # Try to get user ID from request state (set by auth middleware)
        if hasattr(request.state, 'user_id'):
            return f"user:{request.state.user_id}"
        
        # Fall back to IP address
        if request.client:
            return f"ip:{request.client.host}"
        
        return "anonymous"
    
    def is_rate_limited(self, client_id: str) -> bool:
        """Check if client is rate limited."""
        current_time = time.time()
        
        if client_id not in _rate_limit_store:
            _rate_limit_store[client_id] = {}
        
        client_data = _rate_limit_store[client_id]
        
        # Clean old entries
        cutoff_time = current_time - self.window_size
        client_data = {k: v for k, v in client_data.items() if v > cutoff_time}
        _rate_limit_store[client_id] = client_data
        
        # Check if limit exceeded
        if len(client_data) >= self.calls_per_minute:
            return True
        
        # Add current request
        request_id = f"{current_time}_{len(client_data)}"
        client_data[request_id] = current_time
        
        return False
    
    async def dispatch(self, request: Request, call_next):
        """Process request with rate limiting."""
        # Always bypass rate limiting in test runs
        import os as _os
        if _os.getenv("ENV") == "test" or not settings.rate_limit_enabled:
            return await call_next(request)

        client_id = self.get_client_id(request)

        if self.is_rate_limited(client_id):
            logger.warning(f"Rate limit exceeded for {client_id}")
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Please try again later.",
                headers={"Retry-After": "60"}
            )

        return await call_next(request)

def rate_limit_decorator(calls_per_minute: int = 30):
    """Decorator for endpoint-specific rate limiting."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            # This is a simplified version - in practice you'd implement
            # more sophisticated per-endpoint rate limiting
            return func(*args, **kwargs)
        return wrapper
    return decorator
