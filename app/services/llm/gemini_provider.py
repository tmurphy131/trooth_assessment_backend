"""
Google Gemini LLM Provider

Implements the LLMProvider interface for Google Gemini models via Vertex AI.
Uses the new google-genai SDK (recommended by Google as of 2025+).
"""

import os
import logging
from typing import Dict, List, Optional

from .base import LLMProvider, LLMConfig

logger = logging.getLogger(__name__)


class GeminiProvider(LLMProvider):
    """Google Gemini model provider via Vertex AI."""
    
    PROVIDER_NAME = "gemini"
    DEFAULT_MODEL = "gemini-2.5-flash"  # Best price-performance, hybrid reasoning
    
    # Pricing per 1M tokens (as of Jan 2026)
    # gemini-2.5-flash: $0.30 input, $2.50 output
    INPUT_PRICE_PER_1M = 0.30
    OUTPUT_PRICE_PER_1M = 2.50
    
    # Model-specific pricing overrides
    MODEL_PRICING = {
        "gemini-2.5-flash": {"input": 0.30, "output": 2.50},
        "gemini-2.5-flash-lite": {"input": 0.10, "output": 0.40},
        "gemini-2.5-pro": {"input": 1.25, "output": 10.00},
        "gemini-2.0-flash": {"input": 0.10, "output": 0.40},  # Deprecated Mar 2026
        "gemini-3-flash-preview": {"input": 0.50, "output": 3.00},
        "gemini-3-pro-preview": {"input": 2.00, "output": 12.00},
    }
    
    def _init_client(
        self,
        project_id: Optional[str] = None,
        location: Optional[str] = None,
        **kwargs
    ) -> None:
        """Initialize Gemini client via google-genai SDK."""
        self._project_id = project_id or os.getenv("GOOGLE_CLOUD_PROJECT", "trooth-prod")
        self._location = location or os.getenv("GOOGLE_CLOUD_LOCATION", "us-east4")
        self._client = None
        
        # Update pricing based on model
        if self.model in self.MODEL_PRICING:
            self.INPUT_PRICE_PER_1M = self.MODEL_PRICING[self.model]["input"]
            self.OUTPUT_PRICE_PER_1M = self.MODEL_PRICING[self.model]["output"]
    
    def _get_client(self):
        """Lazy load Gemini client."""
        if self._client is None:
            try:
                from google import genai
                from google.genai import types
                
                # Initialize client with Vertex AI
                self._client = genai.Client(
                    vertexai=True,
                    project=self._project_id,
                    location=self._location
                )
                self._types = types
                
            except ImportError:
                raise ImportError(
                    "google-genai package not installed. "
                    "Install with: pip install google-genai"
                )
        
        return self._client
    
    def _call_api(
        self,
        messages: List[Dict[str, str]],
        config: LLMConfig
    ) -> tuple[str, int, int]:
        """Make Gemini API call."""
        client = self._get_client()
        
        # Convert messages to Gemini format
        # Gemini uses 'contents' with Parts
        # System instruction goes in system_instruction parameter
        system_content = ""
        user_content = ""
        
        for msg in messages:
            if msg["role"] == "system":
                system_content += msg["content"] + "\n"
            else:
                user_content += msg["content"] + "\n"
        
        # Build generation config
        gen_config = self._types.GenerateContentConfig(
            temperature=config.temperature,
            max_output_tokens=config.max_tokens,
            system_instruction=system_content.strip() if system_content else None,
        )
        
        # Add JSON response mode if requested
        if config.json_mode:
            gen_config.response_mime_type = "application/json"
        
        # Make the API call
        response = client.models.generate_content(
            model=self.model,
            contents=user_content.strip(),
            config=gen_config,
        )
        
        # Check for truncation via finish_reason
        if hasattr(response, 'candidates') and response.candidates:
            candidate = response.candidates[0]
            finish_reason = getattr(candidate, 'finish_reason', None)
            # Common finish reasons: STOP (normal), MAX_TOKENS (truncated), SAFETY, etc.
            # finish_reason values: 1=STOP, 2=MAX_TOKENS, 3=SAFETY, 4=RECITATION, 5=OTHER
            # For Gemini 2.x, finish_reason is an enum: FinishReason.STOP, FinishReason.MAX_TOKENS, etc.
            finish_reason_str = str(finish_reason).upper() if finish_reason else ""
            logger.debug(f"[gemini] finish_reason={finish_reason} (str={finish_reason_str})")
            
            # Check for various forms of "max tokens" / "truncated"
            if any(x in finish_reason_str for x in ('MAX_TOKENS', 'LENGTH', 'TRUNCAT')):
                logger.warning(f"[gemini] Response truncated due to max_tokens limit (finish_reason={finish_reason}). Consider increasing max_tokens.")
                raise ValueError(f"Response truncated due to max_tokens limit (finish_reason={finish_reason})")
            
            # Also check if finish_reason is integer 2 (MAX_TOKENS in older API)
            if finish_reason == 2:
                logger.warning(f"[gemini] Response truncated due to max_tokens limit (finish_reason=2)")
                raise ValueError("Response truncated due to max_tokens limit")
        
        # Extract response text
        raw_text = response.text or ""
        
        # Additional check: if JSON mode was requested but response doesn't look like valid JSON
        if config.json_mode and raw_text:
            raw_text_stripped = raw_text.strip()
            # Check if it starts with { or [ but doesn't end properly
            if raw_text_stripped.startswith(('{', '[')) and not raw_text_stripped.endswith(('}', ']')):
                logger.warning(f"[gemini] JSON response appears incomplete (doesn't end with }} or ]). Length={len(raw_text)}, ends with: {raw_text_stripped[-50:] if len(raw_text_stripped) > 50 else raw_text_stripped}")
                raise ValueError(f"JSON response appears truncated (length={len(raw_text)}, doesn't end with closing bracket)")
        
        # Extract token counts from usage metadata
        prompt_tokens = 0
        completion_tokens = 0
        
        if hasattr(response, 'usage_metadata') and response.usage_metadata:
            prompt_tokens = getattr(response.usage_metadata, 'prompt_token_count', 0) or 0
            completion_tokens = getattr(response.usage_metadata, 'candidates_token_count', 0) or 0
        
        return raw_text, prompt_tokens, completion_tokens
    
    def is_available(self) -> bool:
        """Check if Gemini/Vertex AI is properly configured."""
        try:
            # Check if we can initialize the client
            self._get_client()
            return True
        except Exception as e:
            logger.debug(f"Gemini not available: {e}")
            return False
