"""
Enhanced security utilities and base schemas.
"""
from pydantic import BaseModel, field_validator
from typing import Any, Dict, List, Optional
import re
import html
import logging

logger = logging.getLogger("app.security")

class SecurityMixin:
    """Mixin class for security validation."""
    
    @field_validator('*', mode='before')
    def strip_strings(cls, v):
        """Strip whitespace from all string fields."""
        if isinstance(v, str):
            return v.strip()
        return v
    
    @field_validator('*')
    def validate_no_scripts(cls, v):
        """Basic XSS protection for string fields."""
        if isinstance(v, str):
            dangerous_patterns = [
                r'<script.*?</script>',
                r'javascript:',
                r'on\w+\s*=',
                r'<iframe',
                r'<object',
                r'<embed',
                r'vbscript:',
                r'data:text/html'
            ]
            
            for pattern in dangerous_patterns:
                if re.search(pattern, v, re.IGNORECASE | re.DOTALL):
                    logger.warning(f"Potential XSS attempt detected: {pattern}")
                    raise ValueError("Invalid content detected")
        return v

class SecureBaseModel(BaseModel, SecurityMixin):
    """Base model with security validation."""
    pass

class PaginationParams(BaseModel):
    """Pagination parameters with validation."""
    page: int = 1
    limit: int = 10
    sort_by: Optional[str] = None
    sort_order: str = "desc"
    
    @field_validator('page')
    def validate_page(cls, v):
        if v < 1:
            raise ValueError("Page must be >= 1")
        return v
    
    @field_validator('limit')
    def validate_limit(cls, v):
        if v < 1 or v > 100:
            raise ValueError("Limit must be between 1 and 100")
        return v
    
    @field_validator('sort_order')
    def validate_sort_order(cls, v):
        if v.lower() not in ['asc', 'desc']:
            raise ValueError("Sort order must be 'asc' or 'desc'")
        return v.lower()

class PaginatedResponse(BaseModel):
    """Standardized paginated response."""
    items: List[Any]
    total: int
    page: int
    limit: int
    total_pages: int
    has_next: bool
    has_prev: bool
    
    @classmethod
    def create(cls, items: List[Any], total: int, page: int, limit: int):
        """Create paginated response from query results."""
        total_pages = (total + limit - 1) // limit  # Ceiling division
        return cls(
            items=items,
            total=total,
            page=page,
            limit=limit,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1
        )

def sanitize_html(text: str) -> str:
    """Sanitize HTML content."""
    return html.escape(text)

def validate_email(email: str) -> bool:
    """Validate email format."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None
