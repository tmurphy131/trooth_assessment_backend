"""
LLM Provider Base Interface

Abstract base class defining the contract for LLM providers.
All providers (OpenAI, Gemini, etc.) must implement this interface.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    """Standardized response from any LLM provider."""
    success: bool
    content: Dict[str, Any]  # Parsed JSON response
    raw_response: str  # Raw text from LLM
    
    # Metrics
    latency_ms: int
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost_usd: float
    
    # Provider info
    provider: str
    model: str
    
    # Error handling
    error: Optional[str] = None
    
    @property
    def json_valid(self) -> bool:
        return self.success and self.content is not None


@dataclass
class LLMConfig:
    """Configuration for LLM calls."""
    temperature: float = 0.2
    max_tokens: int = 4000  # Increased default to prevent Gemini truncation
    json_mode: bool = True  # Request JSON response format
    timeout_seconds: int = 60
    max_retries: int = 3


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    # Subclasses must define these
    PROVIDER_NAME: str = "base"
    DEFAULT_MODEL: str = "unknown"
    
    # Pricing per 1M tokens (subclasses override)
    INPUT_PRICE_PER_1M: float = 0.0
    OUTPUT_PRICE_PER_1M: float = 0.0
    
    def __init__(self, model: Optional[str] = None, **kwargs):
        """Initialize the provider.
        
        Args:
            model: Specific model to use (defaults to DEFAULT_MODEL)
            **kwargs: Provider-specific configuration
        """
        self.model = model or self.DEFAULT_MODEL
        self._init_client(**kwargs)
    
    @abstractmethod
    def _init_client(self, **kwargs) -> None:
        """Initialize the provider's client. Implemented by subclasses."""
        pass
    
    @abstractmethod
    def _call_api(
        self,
        messages: List[Dict[str, str]],
        config: LLMConfig
    ) -> tuple[str, int, int]:
        """Make the actual API call.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            config: LLM configuration
            
        Returns:
            Tuple of (raw_response_text, prompt_tokens, completion_tokens)
        """
        pass
    
    def generate(
        self,
        system_prompt: str,
        user_content: str,
        config: Optional[LLMConfig] = None
    ) -> LLMResponse:
        """Generate a response from the LLM.
        
        This is the main entry point. It handles:
        - Message formatting
        - Retries with backoff
        - JSON parsing
        - Error handling
        - Metrics logging
        
        Args:
            system_prompt: System message content
            user_content: User message content
            config: Optional LLM configuration
            
        Returns:
            LLMResponse with parsed content and metrics
        """
        import time
        import json
        
        config = config or LLMConfig()
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]
        
        start_time = time.time()
        
        try:
            # Call API with retry logic
            raw_response, prompt_tokens, completion_tokens = self._call_with_retry(
                messages, config
            )
            
            latency_ms = int((time.time() - start_time) * 1000)
            total_tokens = prompt_tokens + completion_tokens
            
            # Calculate cost
            cost_usd = self._calculate_cost(prompt_tokens, completion_tokens)
            
            # Parse JSON response
            content = self._parse_json(raw_response)
            
            # Log success
            logger.info(
                f"[llm] provider={self.PROVIDER_NAME} model={self.model} "
                f"latency_ms={latency_ms} tokens={total_tokens} "
                f"(prompt={prompt_tokens}, completion={completion_tokens}) "
                f"cost_usd={cost_usd:.6f}"
            )
            
            return LLMResponse(
                success=True,
                content=content,
                raw_response=raw_response,
                latency_ms=latency_ms,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                estimated_cost_usd=cost_usd,
                provider=self.PROVIDER_NAME,
                model=self.model,
            )
            
        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            logger.error(f"[llm] provider={self.PROVIDER_NAME} error={str(e)}")
            
            return LLMResponse(
                success=False,
                content={},
                raw_response="",
                latency_ms=latency_ms,
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
                estimated_cost_usd=0.0,
                provider=self.PROVIDER_NAME,
                model=self.model,
                error=str(e),
            )
    
    def _call_with_retry(
        self,
        messages: List[Dict[str, str]],
        config: LLMConfig
    ) -> tuple[str, int, int]:
        """Call API with exponential backoff retry."""
        import time
        
        last_error = None
        delay = 0.6
        
        for attempt in range(config.max_retries):
            try:
                if attempt > 0:
                    logger.info(f"[llm] retry attempt {attempt + 1}/{config.max_retries}")
                return self._call_api(messages, config)
            except Exception as e:
                last_error = e
                error_msg = str(e).lower()
                
                # Check if retryable
                retryable = any(x in error_msg for x in [
                    "rate limit", "429", "quota", "timeout", "503", "502"
                ])
                
                if not retryable and attempt < config.max_retries - 1:
                    # Non-retryable error, but try once more
                    pass
                
                if attempt < config.max_retries - 1:
                    time.sleep(delay)
                    delay *= 2  # Exponential backoff
        
        raise last_error or Exception("LLM call failed after retries")
    
    def _calculate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """Calculate estimated cost in USD."""
        return (
            prompt_tokens * self.INPUT_PRICE_PER_1M + 
            completion_tokens * self.OUTPUT_PRICE_PER_1M
        ) / 1_000_000
    
    def _parse_json(self, content: str) -> Dict[str, Any]:
        """Parse JSON from LLM response with fallback strategies."""
        import json
        import re
        
        if not content:
            raise ValueError("Empty response from LLM")
        
        text = content.strip()
        
        # Remove markdown code fences if present
        if text.startswith("```"):
            text = re.sub(r"^```[a-zA-Z0-9_-]*\n?", "", text)
            text = re.sub(r"\n?```\s*$", "", text)
            logger.debug("Removed markdown code fences from response")
        
        # Try direct parse
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            logger.debug(f"Direct JSON parse failed: {e}")
        
        # Try extracting JSON object
        try:
            start = text.find('{')
            end = text.rfind('}')
            if start != -1 and end != -1 and end > start:
                extracted = text[start:end + 1]
                result = json.loads(extracted)
                logger.info("JSON parse succeeded after extracting object")
                return result
        except json.JSONDecodeError as e:
            logger.debug(f"JSON object extraction failed: {e}")
        
        # Try fixing trailing commas
        try:
            fixed = re.sub(r",\s*([}\]])", r"\1", text)
            result = json.loads(fixed)
            logger.info("JSON parse succeeded after fixing trailing commas")
            return result
        except json.JSONDecodeError as e:
            logger.debug(f"Trailing comma fix failed: {e}")
        
        # Try fixing missing commas between properties (common LLM error)
        # Pattern: "value"\n"key" or "value"\s+"key" should have comma
        try:
            # Fix missing commas after string values before string keys
            fixed = re.sub(r'"\s*\n\s*"', '",\n"', text)
            # Fix missing commas after numbers/booleans before string keys  
            fixed = re.sub(r'(\d|true|false|null)\s*\n\s*"', r'\1,\n"', fixed)
            # Fix missing commas after } or ] before "
            fixed = re.sub(r'([}\]])\s*\n\s*"', r'\1,\n"', fixed)
            # Fix missing commas after } before {
            fixed = re.sub(r'}\s*\n\s*{', '},\n{', fixed)
            result = json.loads(fixed)
            logger.info("JSON parse succeeded after fixing missing commas (strategy 1)")
            return result
        except json.JSONDecodeError as e:
            logger.debug(f"Missing comma fix strategy 1 failed: {e}")
        
        # Try a more aggressive fix - add commas between any "value" and newline + "key":
        try:
            # This handles: "key": "value"\n  "next_key"
            fixed = re.sub(r'(["\d]|true|false|null|[}\]])\s*\n(\s*")', r'\1,\n\2', text)
            result = json.loads(fixed)
            logger.info("JSON parse succeeded after fixing missing commas (strategy 2)")
            return result
        except json.JSONDecodeError as e:
            # Log the problematic content for debugging (truncated)
            truncated = text[:500] + "..." if len(text) > 500 else text
            logger.error(f"All JSON parse strategies failed. Content preview: {truncated}")
            raise ValueError(f"Could not parse JSON from LLM response: {e}")
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the provider is properly configured and available."""
        pass
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(model={self.model})"
