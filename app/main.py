from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import os
from dotenv import load_dotenv

# Import core components
from app.core.logging_config import setup_logging
from app.core.settings import settings
from app.middleware.logging import LoggingMiddleware
from app.middleware.rate_limit import RateLimitMiddleware

# Import configuration
from app.config import init_firebase

# Import route modules
from app.routes import (
    user, assessment, mentor, invite, question, 
    templates, assessment_draft, admin_template, health, categories
)
from app.routes import mentor_notes, assessment_score_history, agreements
from app.routes import mentor_profile
from app.routes import apprentice
from app.routes import mentor_resources, apprentice_resources
from app.routes import spiritual_gifts
from app.exceptions import (
    UnauthorizedException, ForbiddenException, 
    NotFoundException, ValidationException
)

# Load environment variables
load_dotenv()

# Set up logging first
logger = setup_logging()

# Create FastAPI app
import os as _os

# Allow exposing the interactive docs in development or when explicitly enabled
# via the SHOW_DOCS environment variable (useful for temporary access on Cloud Run).
_docs_enabled = settings.is_development or _os.getenv("SHOW_DOCS", "").lower() in ("1", "true", "yes")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    logger.info("=" * 50)
    logger.info(f"🚀 T[root]H Assessment API starting up")
    logger.info(f"📁 Environment: {settings.environment}")
    logger.info(f"🌐 CORS origins: {settings.cors_origins}")
    logger.info(f"⚡ Rate limiting: {'enabled' if settings.rate_limit_enabled else 'disabled'}")
    logger.info(f"📊 SQL Debug: {'enabled' if settings.sql_debug else 'disabled'}")

    from app.services.ai_scoring import get_openai_client
    from app.services.email import get_sendgrid_client
    openai_status = "✅ configured" if get_openai_client() else "❌ not configured (using mocks)"
    email_status = "✅ configured" if get_sendgrid_client() else "❌ not configured (logging only)"
    logger.info(f"🤖 OpenAI API: {openai_status}")
    logger.info(f"📧 SendGrid Email: {email_status}")
    logger.info("=" * 50)

    # Seed agreement template (same logic moved from startup_event)
    try:
        from sqlalchemy.orm import Session
        from app.db import SessionLocal
        from app.models.agreement import AgreementTemplate
        import uuid
        session: Session = SessionLocal()
        count = session.query(AgreementTemplate).count()
        if count == 0:
            logger.info("📝 Seeding initial agreement template (version 1)")
            template_path = os.path.join(os.path.dirname(__file__), '..', 'MENTOR_AGREEMENT.md')
            markdown_source = "Rooted Commitment Agreement"
            try:
                with open(template_path, 'r', encoding='utf-8') as f:
                    markdown_source = f.read()[:20000]
            except Exception as e:
                logger.warning(f"Could not read MENTOR_AGREEMENT.md: {e}")
            tpl = AgreementTemplate(
                id=str(uuid.uuid4()),
                version=1,
                markdown_source=markdown_source,
                is_active=True,
                notes="Initial seeded version"
            )
            session.add(tpl)
            session.commit()
            logger.info("✅ Agreement template v1 seeded")
        session.close()
    except Exception as seed_err:
        logger.error(f"Failed seeding agreement template: {seed_err}")

    yield
    # Shutdown logic
    logger.info("🛑 T[root]H Assessment API shutting down gracefully")

app = FastAPI(
    title="T[root]H Assessment API",
    description="Comprehensive spiritual assessment and mentoring platform",
    version="1.0.0",
    docs_url="/docs" if _docs_enabled else None,
    redoc_url="/redoc" if _docs_enabled else None,
    lifespan=lifespan,
)

# Jinja templates (avoid clashing with routes.templates module)
jinja_templates = Jinja2Templates(directory="app/templates")

# Add middleware in correct order (last added = first executed)
app.add_middleware(LoggingMiddleware)

if settings.rate_limit_enabled:
    app.add_middleware(RateLimitMiddleware, calls_per_minute=60)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000", 
        "http://localhost:3001",
        "http://127.0.0.1:3001",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "http://localhost:8081",
        "http://127.0.0.1:8081",
        "http://localhost:8082",
        "http://127.0.0.1:8082",
        "http://localhost:5000",
        "http://127.0.0.1:5000"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
)

# Initialize Firebase (skip in test environment)
if os.getenv("ENV") != "test":
    init_firebase()

# Include routers
app.include_router(health.router, prefix="/health", tags=["Health"])
app.include_router(user.router, prefix="/users", tags=["Users"])
app.include_router(assessment.router, prefix="/assessments", tags=["Assessments"])
app.include_router(assessment_score_history.router)
app.include_router(mentor.router, prefix="/mentor", tags=["Mentor"])
app.include_router(invite.router, prefix="/invitations", tags=["Invitations"])
app.include_router(question.router, prefix="/question", tags=["Questions"])
app.include_router(templates.router, tags=["Templates"])
app.include_router(assessment_draft.router, prefix="/assessment-drafts", tags=["Assessment Drafts"])
app.include_router(admin_template.router, prefix="/admin", tags=["Admin"])
# Include compatibility admin routes for legacy path expectations in tests
try:
    from app.routes.admin_template import compat_router as admin_templates_compat_router
    app.include_router(admin_templates_compat_router, prefix="/admin", tags=["Admin"])
except Exception as _e:
    logger.warning(f"Could not include admin templates compat router: {_e}")
app.include_router(categories.router, tags=["Categories"])
app.include_router(mentor_notes.router)
app.include_router(agreements.router, tags=["Agreements"]) 
app.include_router(mentor_profile.router)
app.include_router(mentor_resources.router)
app.include_router(apprentice_resources.router)
app.include_router(apprentice.router)
app.include_router(spiritual_gifts.router)

# Static assets (logo etc.) – map /assets to ./assets if present
_assets_dir = os.path.join(os.path.dirname(__file__), '..', 'assets')
try:
    if os.path.isdir(os.path.abspath(_assets_dir)):
        app.mount("/assets", StaticFiles(directory=os.path.abspath(_assets_dir)), name="assets")
        logger.info(f"📎 Static assets mounted at /assets from {_assets_dir}")
    else:
        logger.warning(f"/assets directory not found at {_assets_dir}; logo references may 404 (settings.logo_url={settings.logo_url})")
except Exception as e:
    logger.error(f"Failed to mount /assets static directory: {e}")

# Public static for HTML signing page (CSS)
_static_dir = os.path.join(os.path.dirname(__file__), '..', 'static')
try:
    if os.path.isdir(os.path.abspath(_static_dir)):
        app.mount("/static", StaticFiles(directory=os.path.abspath(_static_dir)), name="static")
        logger.info(f"🎨 Public static mounted at /static from {_static_dir}")
except Exception as e:
    logger.error(f"Failed to mount /static directory: {e}")

# Exception handlers
@app.exception_handler(UnauthorizedException)
async def unauthorized_exception_handler(request: Request, exc: UnauthorizedException):
    correlation_id = getattr(request.state, 'correlation_id', 'unknown')
    logger.warning(f"[{correlation_id}] Unauthorized access attempt on {request.url.path}")
    return JSONResponse(
        status_code=401,
        content={"detail": exc.detail, "correlation_id": correlation_id}
    )

@app.exception_handler(ForbiddenException)
async def forbidden_exception_handler(request: Request, exc: ForbiddenException):
    correlation_id = getattr(request.state, 'correlation_id', 'unknown')
    logger.warning(f"[{correlation_id}] Forbidden access attempt on {request.url.path}")
    return JSONResponse(
        status_code=403,
        content={"detail": exc.detail, "correlation_id": correlation_id}
    )

@app.exception_handler(ValidationException)
async def validation_exception_handler(request: Request, exc: ValidationException):
    correlation_id = getattr(request.state, 'correlation_id', 'unknown')
    logger.warning(f"[{correlation_id}] Validation error on {request.url.path}: {exc.detail}")
    return JSONResponse(
        status_code=400,
        content={"detail": exc.detail, "correlation_id": correlation_id}
    )

@app.exception_handler(NotFoundException)
async def not_found_exception_handler(request: Request, exc: NotFoundException):
    correlation_id = getattr(request.state, 'correlation_id', 'unknown')
    logger.warning(f"[{correlation_id}] Not found error on {request.url.path}: {exc.detail}")
    return JSONResponse(
        status_code=404,
        content={"detail": exc.detail, "correlation_id": correlation_id}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    correlation_id = getattr(request.state, 'correlation_id', 'unknown')
    logger.error(f"[{correlation_id}] Unhandled exception on {request.url.path}: {str(exc)}", exc_info=True)
    
    if settings.is_development:
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Internal server error",
                "error": str(exc),
                "correlation_id": correlation_id,
                "type": type(exc).__name__
            }
        )
    else:
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Internal server error",
                "correlation_id": correlation_id
            }
        )

# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information."""
    return {
        "message": "T[root]H Assessment API",
        "version": "1.0.0",
        "environment": settings.environment,
        "docs_url": "/docs" if settings.is_development else None,
        "health_check": "/health",
        "status": "running"
    }

# Legacy health endpoint (keep for backward compatibility)
@app.get("/health", tags=["Health"])
async def legacy_health_check():
    """Legacy health check endpoint."""
    return {"status": "healthy", "service": "trooth-assessment-api"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
        log_level="info" if settings.is_development else "warning"
    )