"""
Application settings with environment validation.
"""
import os
from typing import Optional, List

class Settings:
    """Application settings with environment validation."""
    
    def __init__(self):
        # Database
        self.database_url = os.getenv("DATABASE_URL", "postgres://trooth:trooth@localhost:5432/trooth_db")
        
        # Authentication
        self.firebase_cert_path = os.getenv("FIREBASE_CERT_PATH", "firebase_key.json")
        
        # External APIs
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "your_openai_api_key_here")
        self.sendgrid_api_key = os.getenv("SENDGRID_API_KEY", "your_sendgrid_api_key_here")
        
        # Application
        self.app_url = os.getenv("APP_URL", "http://localhost:3000")
        self.email_from_address = os.getenv("EMAIL_FROM_ADDRESS", "no-reply@trooth-app.com")
        self.environment = os.getenv("ENV", "development")
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        
        # Security
        self.cors_origins = self._parse_cors_origins(os.getenv("CORS_ORIGINS", "*"))
        self.rate_limit_enabled = self._parse_bool(os.getenv("RATE_LIMIT_ENABLED", "true"))
        
        # Performance
        self.redis_url = os.getenv("REDIS_URL")
        self.cache_ttl = int(os.getenv("CACHE_TTL", "300"))
        self.sql_debug = self._parse_bool(os.getenv("SQL_DEBUG", "false"))
    
    def _parse_cors_origins(self, v: str) -> List[str]:
        """Parse CORS origins from string."""
        if v == "*":
            return ["*"]
        return [origin.strip() for origin in v.split(',')]
    
    def _parse_bool(self, v: str) -> bool:
        """Parse boolean from environment variable string."""
        return v.lower() in ('true', '1', 'yes', 'on')
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment.lower() == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment.lower() == "development"

# Global settings instance
settings = Settings()
