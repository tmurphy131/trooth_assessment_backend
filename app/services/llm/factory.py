"""
LLM Provider Factory

Creates and manages LLM provider instances based on configuration.
Supports automatic fallback from primary to secondary provider.
"""

import os
import logging
from typing import Optional, Dict, Any, Type
from enum import Enum

from .base import LLMProvider, LLMResponse, LLMConfig
from .openai_provider import OpenAIProvider
from .gemini_provider import GeminiProvider

logger = logging.getLogger(__name__)


class LLMProviderType(str, Enum):
    """Supported LLM providers."""
    OPENAI = "openai"
    GEMINI = "gemini"


# Registry of available providers
PROVIDER_REGISTRY: Dict[str, Type[LLMProvider]] = {
    LLMProviderType.OPENAI: OpenAIProvider,
    LLMProviderType.GEMINI: GeminiProvider,
}


class LLMService:
    """
    LLM Service with automatic provider selection and fallback.
    
    Configuration via environment variables:
    - LLM_PROVIDER: Primary provider ('gemini' or 'openai', default: 'gemini')
    - LLM_MODEL: Model name (optional, uses provider default)
    - LLM_FALLBACK_ENABLED: Enable fallback to secondary provider (default: true)
    
    Usage:
        service = LLMService()
        response = service.generate(
            system_prompt="You are a helpful assistant.",
            user_content="Analyze this text...",
        )
        if response.success:
            print(response.content)
    """
    
    def __init__(
        self,
        primary_provider: Optional[str] = None,
        primary_model: Optional[str] = None,
        fallback_enabled: Optional[bool] = None,
        **kwargs
    ):
        """Initialize LLM service.
        
        Args:
            primary_provider: Primary provider type ('gemini' or 'openai')
            primary_model: Specific model to use
            fallback_enabled: Whether to fallback to secondary provider on failure
            **kwargs: Additional provider configuration
        """
        # Load config from env or params
        self._primary_type = LLMProviderType(
            primary_provider or os.getenv("LLM_PROVIDER", "gemini")
        )
        self._model = primary_model or os.getenv("LLM_MODEL")
        self._fallback_enabled = fallback_enabled if fallback_enabled is not None else (
            os.getenv("LLM_FALLBACK_ENABLED", "true").lower() in ("true", "1", "yes")
        )
        self._kwargs = kwargs
        
        # Lazy-loaded providers
        self._primary: Optional[LLMProvider] = None
        self._fallback: Optional[LLMProvider] = None
        
        logger.info(
            f"[llm_service] initialized: primary={self._primary_type.value} "
            f"model={self._model or 'default'} fallback={self._fallback_enabled}"
        )
    
    @property
    def primary_provider(self) -> LLMProvider:
        """Get or create primary provider instance."""
        if self._primary is None:
            provider_class = PROVIDER_REGISTRY[self._primary_type]
            self._primary = provider_class(model=self._model, **self._kwargs)
        return self._primary
    
    @property
    def fallback_provider(self) -> Optional[LLMProvider]:
        """Get or create fallback provider instance."""
        if not self._fallback_enabled:
            return None
        
        if self._fallback is None:
            # Use the opposite provider as fallback
            fallback_type = (
                LLMProviderType.OPENAI 
                if self._primary_type == LLMProviderType.GEMINI 
                else LLMProviderType.GEMINI
            )
            provider_class = PROVIDER_REGISTRY[fallback_type]
            self._fallback = provider_class()  # Use default model for fallback
        
        return self._fallback
    
    def generate(
        self,
        system_prompt: str,
        user_content: str,
        config: Optional[LLMConfig] = None,
        use_fallback: bool = True
    ) -> LLMResponse:
        """Generate response using primary provider with optional fallback.
        
        Args:
            system_prompt: System message content
            user_content: User message content
            config: Optional LLM configuration
            use_fallback: Whether to attempt fallback on primary failure
            
        Returns:
            LLMResponse from successful provider
        """
        # Try primary provider
        try:
            response = self.primary_provider.generate(
                system_prompt=system_prompt,
                user_content=user_content,
                config=config
            )
            
            if response.success:
                return response
            
            logger.warning(
                f"[llm_service] primary provider failed: {response.error}"
            )
            
        except Exception as e:
            logger.warning(f"[llm_service] primary provider exception: {e}")
            response = None
        
        # Try fallback if enabled
        if use_fallback and self._fallback_enabled and self.fallback_provider:
            logger.info(
                f"[llm_service] attempting fallback to {self.fallback_provider.PROVIDER_NAME}"
            )
            
            try:
                fallback_response = self.fallback_provider.generate(
                    system_prompt=system_prompt,
                    user_content=user_content,
                    config=config
                )
                
                if fallback_response.success:
                    logger.info(
                        f"[llm_service] fallback succeeded via {fallback_response.provider}"
                    )
                    return fallback_response
                    
            except Exception as e:
                logger.error(f"[llm_service] fallback also failed: {e}")
        
        # Return the failed response from primary
        if response:
            return response
        
        # Create error response if we have nothing
        return LLMResponse(
            success=False,
            content={},
            raw_response="",
            latency_ms=0,
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            estimated_cost_usd=0.0,
            provider=self._primary_type.value,
            model=self._model or "unknown",
            error="All LLM providers failed"
        )
    
    def is_available(self) -> bool:
        """Check if at least one provider is available."""
        try:
            if self.primary_provider.is_available():
                return True
        except Exception:
            pass
        
        if self._fallback_enabled:
            try:
                if self.fallback_provider and self.fallback_provider.is_available():
                    return True
            except Exception:
                pass
        
        return False
    
    def get_available_providers(self) -> Dict[str, bool]:
        """Get availability status of all providers."""
        status = {}
        for provider_type, provider_class in PROVIDER_REGISTRY.items():
            try:
                provider = provider_class()
                status[provider_type] = provider.is_available()
            except Exception:
                status[provider_type] = False
        return status


# Module-level singleton for convenience
_service_instance: Optional[LLMService] = None


def get_llm_service(**kwargs) -> LLMService:
    """Get or create the default LLM service instance.
    
    This provides a singleton pattern for easy use across the application.
    Pass kwargs to override default configuration.
    
    Usage:
        from app.services.llm import get_llm_service
        
        service = get_llm_service()
        response = service.generate(system_prompt, user_content)
    """
    global _service_instance
    
    if _service_instance is None or kwargs:
        _service_instance = LLMService(**kwargs)
    
    return _service_instance


def reset_llm_service() -> None:
    """Reset the singleton instance (useful for testing)."""
    global _service_instance
    _service_instance = None
