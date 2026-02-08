"""
OpenAI LLM Provider

Implements the LLMProvider interface for OpenAI models.
"""

import os
import logging
from typing import Dict, List, Optional

from .base import LLMProvider, LLMConfig

logger = logging.getLogger(__name__)


class OpenAIProvider(LLMProvider):
    """OpenAI GPT model provider."""
    
    PROVIDER_NAME = "openai"
    DEFAULT_MODEL = "gpt-4o"
    
    # Pricing per 1M tokens (as of Jan 2026)
    # gpt-4o-mini: $0.15 input, $0.60 output
    INPUT_PRICE_PER_1M = 0.15
    OUTPUT_PRICE_PER_1M = 0.60
    
    # Model-specific pricing overrides
    MODEL_PRICING = {
        "gpt-4o-mini": {"input": 0.15, "output": 0.60},
        "gpt-4o": {"input": 2.50, "output": 10.00},
        "gpt-4-turbo": {"input": 10.00, "output": 30.00},
    }
    
    def _init_client(self, api_key: Optional[str] = None, **kwargs) -> None:
        """Initialize OpenAI client."""
        self._api_key = api_key or os.getenv("OPENAI_API_KEY")
        self._client = None
        
        # Update pricing based on model
        if self.model in self.MODEL_PRICING:
            self.INPUT_PRICE_PER_1M = self.MODEL_PRICING[self.model]["input"]
            self.OUTPUT_PRICE_PER_1M = self.MODEL_PRICING[self.model]["output"]
    
    def _get_client(self):
        """Lazy load OpenAI client."""
        if self._client is None:
            if not self._api_key or self._api_key.startswith("your_"):
                raise ValueError("OpenAI API key not configured")
            
            from openai import OpenAI
            self._client = OpenAI(api_key=self._api_key)
        
        return self._client
    
    def _call_api(
        self,
        messages: List[Dict[str, str]],
        config: LLMConfig
    ) -> tuple[str, int, int]:
        """Make OpenAI API call."""
        client = self._get_client()
        
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
        }
        
        # Add JSON mode if requested
        if config.json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        
        response = client.chat.completions.create(**kwargs)
        
        # Extract response
        raw_text = (response.choices[0].message.content or "").strip()
        
        # Extract token counts
        usage = response.usage
        prompt_tokens = usage.prompt_tokens if usage else 0
        completion_tokens = usage.completion_tokens if usage else 0
        
        return raw_text, prompt_tokens, completion_tokens
    
    def is_available(self) -> bool:
        """Check if OpenAI is properly configured."""
        if not self._api_key or self._api_key.startswith("your_"):
            return False
        
        # Optionally verify with a quick API check
        try:
            self._get_client()
            return True
        except Exception:
            return False
