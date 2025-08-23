"""
Custom middleware for request logging, timing, and correlation tracking.
"""
import time
import uuid
import logging
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("app.middleware")

class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log all requests with timing and correlation ID."""
    
    async def dispatch(self, request: Request, call_next):
        # Generate correlation ID
        correlation_id = str(uuid.uuid4())[:8]
        start_time = time.time()
        
        # Add correlation ID to request state
        request.state.correlation_id = correlation_id
        
        # Log request start
        logger.info(
            f"[{correlation_id}] {request.method} {request.url.path} - Started "
            f"from {request.client.host if request.client else 'unknown'}"
        )
        
        # Process request
        try:
            response = await call_next(request)
        except Exception as e:
            process_time = time.time() - start_time
            logger.error(
                f"[{correlation_id}] {request.method} {request.url.path} - "
                f"Failed after {process_time:.3f}s with error: {str(e)}"
            )
            raise
        
        # Log response
        process_time = time.time() - start_time
        logger.info(
            f"[{correlation_id}] {request.method} {request.url.path} - "
            f"Completed in {process_time:.3f}s with status {response.status_code}"
        )
        
        # Add correlation ID to response headers
        response.headers["X-Correlation-ID"] = correlation_id
        response.headers["X-Process-Time"] = f"{process_time:.3f}"
        
        return response
