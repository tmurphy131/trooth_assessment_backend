"""
Health check and monitoring endpoints.
"""
import os
import time
import logging
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Dict, Any
from app.db import get_db, check_database_health
from app.services.llm import get_llm_service
from app.services.email import get_sendgrid_client
from app.core.settings import settings

logger = logging.getLogger("app.health")
router = APIRouter()

@router.get("/health")
async def health_check():
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "environment": settings.environment,
        "version": "1.0.0"
    }

@router.get("/health/detailed")
async def detailed_health_check(db: Session = Depends(get_db)):
    """Detailed health check with service status."""
    start_time = time.time()
    
    health_status = {
        "status": "healthy",
        "timestamp": time.time(),
        "environment": settings.environment,
        "services": {}
    }
    
    # Check database
    try:
        db_health = await check_database_health()
        health_status["services"]["database"] = db_health
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        health_status["services"]["database"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "degraded"
    
    # Check LLM Service (Gemini/OpenAI)
    try:
        llm_service = get_llm_service()
        primary = llm_service.primary_provider
        fallback = llm_service.fallback_provider
        if primary or fallback:
            health_status["services"]["llm"] = {
                "status": "configured",
                "primary_provider": primary.__class__.__name__ if primary else "None",
                "primary_model": primary.model if primary else None,
                "fallback_provider": fallback.__class__.__name__ if fallback else "None",
                "fallback_model": fallback.model if fallback else None,
                "fallback_enabled": settings.llm_fallback_enabled
            }
        else:
            health_status["services"]["llm"] = {
                "status": "not_configured",
                "note": "Using mock scoring"
            }
    except Exception as e:
        health_status["services"]["llm"] = {
            "status": "error",
            "error": str(e)
        }
    
    # Check SendGrid
    try:
        sendgrid_client = get_sendgrid_client()
        if sendgrid_client:
            health_status["services"]["email"] = {
                "status": "configured",
                "provider": "sendgrid"
            }
        else:
            health_status["services"]["email"] = {
                "status": "not_configured",
                "note": "Email sending disabled"
            }
    except Exception as e:
        health_status["services"]["email"] = {
            "status": "error",
            "error": str(e)
        }
    
    # Check Redis (if configured)
    if settings.redis_url:
        try:
            # This would require redis package
            health_status["services"]["redis"] = {
                "status": "not_implemented",
                "note": "Redis health check not implemented"
            }
        except Exception as e:
            health_status["services"]["redis"] = {
                "status": "error",
                "error": str(e)
            }
    
    # Calculate response time
    response_time = (time.time() - start_time) * 1000
    health_status["response_time_ms"] = round(response_time, 2)
    
    return health_status

@router.get("/health/metrics")
async def get_metrics():
    """Application metrics endpoint."""
    return {
        "uptime_seconds": time.time(),  # This would be actual uptime in production
        "memory_usage": "N/A",  # Would implement actual memory monitoring
        "cpu_usage": "N/A",     # Would implement actual CPU monitoring
        "active_connections": "N/A",  # Would track DB connections
        "cache_hit_rate": "N/A",      # Would track cache performance
        "request_count": "N/A",       # Would track total requests
        "error_rate": "N/A"           # Would track error percentage
    }

@router.get("/ready")
async def readiness_check(db: Session = Depends(get_db)):
    """Kubernetes-style readiness probe."""
    try:
        # Check if database is accessible
        db_health = await check_database_health()
        if db_health["status"] != "healthy":
            return {"status": "not_ready", "reason": "database_unavailable"}
        
        return {"status": "ready"}
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return {"status": "not_ready", "reason": str(e)}

@router.get("/live")
async def liveness_check():
    """Kubernetes-style liveness probe."""
    return {"status": "alive", "timestamp": time.time()}


@router.get("/health/llm")
async def llm_health_check(
    test_generation: bool = Query(False, description="Run a test generation (costs tokens)")
):
    """
    LLM Service health check.
    
    Returns availability status of configured LLM providers (OpenAI, Gemini).
    Set test_generation=true to run an actual API call (will cost tokens).
    """
    from app.services.llm import get_llm_service, LLMConfig
    
    start_time = time.time()
    
    try:
        service = get_llm_service()
        
        result = {
            "status": "healthy",
            "timestamp": time.time(),
            "configuration": {
                "primary_provider": service.primary_provider.PROVIDER_NAME,
                "primary_model": service.primary_provider.model,
                "fallback_enabled": service._fallback_enabled,
            },
            "providers": service.get_available_providers(),
        }
        
        # Optionally run a test generation
        if test_generation:
            config = LLMConfig(temperature=0.1, max_tokens=100, json_mode=True)
            
            response = service.generate(
                system_prompt="Return JSON only.",
                user_content='Return exactly: {"test": "ok", "provider": "<your_name>"}',
                config=config
            )
            
            result["test_generation"] = {
                "success": response.success,
                "provider_used": response.provider,
                "model_used": response.model,
                "latency_ms": response.latency_ms,
                "tokens_used": response.total_tokens,
                "cost_usd": response.estimated_cost_usd,
                "content": response.content if response.success else None,
                "error": response.error if not response.success else None,
            }
            
            if not response.success:
                result["status"] = "degraded"
        
        result["response_time_ms"] = round((time.time() - start_time) * 1000, 2)
        return result
        
    except Exception as e:
        logger.error(f"LLM health check failed: {e}")
        return {
            "status": "unhealthy",
            "timestamp": time.time(),
            "error": str(e),
            "response_time_ms": round((time.time() - start_time) * 1000, 2)
        }

