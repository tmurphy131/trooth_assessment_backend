"""Application settings with environment validation."""

import logging
import os
from typing import List

logger = logging.getLogger(__name__)

# ENV values: "development" (local), "test" (pytest), "dev" (Cloud Run dev), "production".
# "dev" is deliberately neither development nor production: it is publicly reachable, so it
# must not return stack traces, but it is not prod either.
KNOWN_ENVIRONMENTS = {"development", "test", "dev", "production"}
_ENV_ALIASES = {"prod": "production"}


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
        raw_env = os.getenv("ENV", "development").strip().lower()
        self.environment = _ENV_ALIASES.get(raw_env, raw_env)
        if self.environment not in KNOWN_ENVIRONMENTS:
            logger.warning(
                "Unknown ENV %r; expected one of %s", raw_env, sorted(KNOWN_ENVIRONMENTS)
            )
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
        # Gemini models: gemini-3.5-flash (default), gemini-3.5-flash-lite, gemini-3.1-flash-lite
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
        
        # RevenueCat settings
        self.revenuecat_webhook_secret = os.getenv("REVENUECAT_WEBHOOK_SECRET", "")
        # Used to verify purchases server-side (GET /v1/subscribers). Prefer a
        # secret key; the public SDK key also works for that read-only call.
        self.revenuecat_secret_api_key = os.getenv("REVENUECAT_SECRET_API_KEY", "")
        self.revenuecat_api_key = os.getenv("REVENUECAT_API_KEY", "")

        # Printful API (for shop availability)
        self.printful_api_token = os.getenv("PRINTFUL_API_TOKEN", "")
        self.printful_store_id = os.getenv("PRINTFUL_STORE_ID", "17585424")
        
        # Shopify Storefront API (for fetching products)
        self.shopify_store_domain = os.getenv("SHOPIFY_STORE_DOMAIN", "0jpspx-qv.myshopify.com")
        self.shopify_storefront_token = os.getenv("SHOPIFY_STOREFRONT_TOKEN", "51d92ea63e7a18e8a8a01c2d080fe813")

        # Shopify Admin API (Dev Dashboard app, client credentials grant) — used to
        # create trivia competition prize codes. Leave unset outside prod: the
        # client then runs in dry-run mode and never touches the real store.
        self.shopify_client_id = os.getenv("SHOPIFY_CLIENT_ID", "")
        self.shopify_client_secret = os.getenv("SHOPIFY_CLIENT_SECRET", "")
        self.shopify_admin_api_version = os.getenv("SHOPIFY_ADMIN_API_VERSION", "2026-10")
        # Collection the prize codes apply to ("All Products – Trivia Prizes")
        self.shopify_prize_collection_id = os.getenv(
            "SHOPIFY_PRIZE_COLLECTION_ID", "gid://shopify/Collection/663277830328"
        )
        self.shop_url = os.getenv("SHOP_URL", "https://shop.onlyblv.com")

        # Trivia competition
        # Comma-separated emails or "@domain" entries that can't win prizes
        self.trivia_competition_excluded_emails = [
            e.strip().lower()
            for e in os.getenv("TRIVIA_COMPETITION_EXCLUDED_EMAILS", "").split(",")
            if e.strip()
        ]
        # Old /trivia/questions/draw and /single/submit; set false once app 2.2.0 is in both stores
        self.trivia_legacy_single_enabled = self._parse_bool(
            os.getenv("TRIVIA_LEGACY_SINGLE_ENABLED", "true")
        )
        # Who gets the winners/codes summary when a competition is finalized
        self.trivia_competition_admin_emails = [
            e.strip()
            for e in os.getenv("TRIVIA_COMPETITION_ADMIN_EMAILS", "taylor.murphy@onlyblv.com").split(",")
            if e.strip()
        ]

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
