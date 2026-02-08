"""
LLM Service Module

Provides a unified interface for multiple LLM providers (OpenAI, Gemini).
Supports automatic fallback and configuration via environment variables.

Configuration:
- LLM_PROVIDER: Primary provider ('gemini' or 'openai', default: 'gemini')
- LLM_MODEL: Specific model to use (optional, uses provider default)
- LLM_FALLBACK_ENABLED: Enable fallback to secondary provider (default: 'true')

For Gemini (Vertex AI):
- GOOGLE_CLOUD_PROJECT: GCP project ID (default: 'trooth-prod')
- GOOGLE_CLOUD_LOCATION: GCP region (default: 'us-east4')

For OpenAI:
- OPENAI_API_KEY: OpenAI API key

Usage:
    from app.services.llm import get_llm_service, LLMConfig
    
    # Get singleton service (uses env config)
    service = get_llm_service()
    
    # Generate response
    response = service.generate(
        system_prompt="You are a helpful assistant.",
        user_content="Analyze this text...",
    )
    
    if response.success:
        print(response.content)  # Parsed JSON
        print(f"Latency: {response.latency_ms}ms")
        print(f"Cost: ${response.estimated_cost_usd:.6f}")
    else:
        print(f"Error: {response.error}")
    
    # Or create custom service with specific config
    from app.services.llm import LLMService
    
    service = LLMService(
        primary_provider="openai",
        primary_model="gpt-4o",
        fallback_enabled=False
    )

Available Models:
    OpenAI:
        - gpt-4o-mini (default, cheapest)
        - gpt-4o
        - gpt-4-turbo
    
    Gemini:
        - gemini-2.5-flash (default, best price-performance)
        - gemini-2.5-flash-lite (cheapest)
        - gemini-2.5-pro (best quality)
        - gemini-3-flash-preview (newest)
"""

from .base import LLMProvider, LLMResponse, LLMConfig
from .openai_provider import OpenAIProvider
from .gemini_provider import GeminiProvider
from .factory import (
    LLMService,
    LLMProviderType,
    get_llm_service,
    reset_llm_service,
    PROVIDER_REGISTRY,
)

__all__ = [
    # Base classes
    "LLMProvider",
    "LLMResponse", 
    "LLMConfig",
    
    # Providers
    "OpenAIProvider",
    "GeminiProvider",
    
    # Service
    "LLMService",
    "LLMProviderType",
    "get_llm_service",
    "reset_llm_service",
    "PROVIDER_REGISTRY",
]
