"""Application settings with environment validation."""

import os
from typing import List


class Settings:
    """Application settings with environment validation."""

    def __init__(self) -> None:
        # Database
        self.database_url = os.getenv(
            "DATABASE_URL", "postgres://trooth:trooth@localhost:5432/trooth_db"
        )

        # Authentication
        self.firebase_cert_path = os.getenv("FIREBASE_CERT_PATH", "firebase_key.json")

        # External APIs
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "your_openai_api_key_here")
        self.sendgrid_api_key = os.getenv(
            "SENDGRID_API_KEY", "your_sendgrid_api_key_here"
        )

        # Application / branding
        # Backend API URL for agreement signing pages and internal use
        self.backend_api_url = os.getenv("BACKEND_API_URL", os.getenv("APP_URL", "http://localhost:3000"))
        # iOS App Store URL for email "Return to App" buttons
        self.ios_app_store_url = os.getenv(
            "IOS_APP_STORE_URL",
            "https://apps.apple.com/app/t-root-h-discipleship/id6757311543"
        )
        # Backward compatibility: app_url falls back to backend_api_url
        self.app_url = self.backend_api_url
        self.logo_url = os.getenv(
            "LOGO_URL", f"{self.backend_api_url.rstrip('/')}/assets/logo.png"
        )
        self.email_from_address = os.getenv(
            "EMAIL_FROM_ADDRESS", "no-reply@trooth-app.com"
        )
        self.environment = os.getenv("ENV", "development")
        self.log_level = os.getenv("LOG_LEVEL", "INFO")

        # Security
        self.cors_origins = self._parse_cors_origins(os.getenv("CORS_ORIGINS", "*"))
        self.rate_limit_enabled = self._parse_bool(
            os.getenv("RATE_LIMIT_ENABLED", "true")
        )

        # Performance / diagnostics
        self.redis_url = os.getenv("REDIS_URL")
        self.cache_ttl = int(os.getenv("CACHE_TTL", "300"))
        self.sql_debug = self._parse_bool(os.getenv("SQL_DEBUG", "false"))

        # LLM Configuration
        # Provider: 'gemini' (default, faster/cheaper) or 'openai'
        self.llm_provider = os.getenv("LLM_PROVIDER", "gemini")
        # Model: optional, uses provider default if not set
        # Gemini models: gemini-2.5-flash (default), gemini-2.5-pro, gemini-2.5-flash-lite
        # OpenAI models: gpt-4o-mini (default), gpt-4o
        self.llm_model = os.getenv("LLM_MODEL", "")
        # Enable automatic fallback to secondary provider on failure
        self.llm_fallback_enabled = self._parse_bool(
            os.getenv("LLM_FALLBACK_ENABLED", "true")
        )
        # GCP settings for Vertex AI (Gemini)
        self.google_cloud_project = os.getenv("GOOGLE_CLOUD_PROJECT", "trooth-prod")
        self.google_cloud_location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-east4")

        # Feature flags / Premium tier (placeholder for RevenueCat integration)
        # When true, enables premium features for testing without subscription check
        self.premium_features_enabled = self._parse_bool(
            os.getenv("PREMIUM_FEATURES_ENABLED", "false")
        )

        # Printful API (for shop availability)
        self.printful_api_token = os.getenv("PRINTFUL_API_TOKEN", "")
        self.printful_store_id = os.getenv("PRINTFUL_STORE_ID", "17585424")
        
        # Shopify Storefront API (for fetching products)
        self.shopify_store_domain = os.getenv("SHOPIFY_STORE_DOMAIN", "0jpspx-qv.myshopify.com")
        self.shopify_storefront_token = os.getenv("SHOPIFY_STOREFRONT_TOKEN", "51d92ea63e7a18e8a8a01c2d080fe813")

    def _parse_cors_origins(self, v: str) -> List[str]:
        if v == "*":
            return ["*"]
        return [origin.strip() for origin in v.split(",")]

    def _parse_bool(self, v: str) -> bool:
        return v.lower() in ("true", "1", "yes", "on")

    @property
    def is_production(self) -> bool:  # convenience flag
        return self.environment.lower() == "production"

    @property
    def is_development(self) -> bool:  # convenience flag
        return self.environment.lower() == "development"


settings = Settings()
