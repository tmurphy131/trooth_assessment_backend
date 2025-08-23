"""
Health check and monitoring endpoints.
"""
import os
import time
import logging
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Dict, Any
from app.db import get_db, check_database_health
from app.services.ai_scoring import get_openai_client
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
    
    # Check OpenAI API
    try:
        openai_client = get_openai_client()
        if openai_client:
            health_status["services"]["openai"] = {
                "status": "configured",
                "model": "gpt-4o-mini"
            }
        else:
            health_status["services"]["openai"] = {
                "status": "not_configured",
                "note": "Using mock scoring"
            }
    except Exception as e:
        health_status["services"]["openai"] = {
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
