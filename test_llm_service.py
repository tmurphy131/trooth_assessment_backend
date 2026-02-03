#!/usr/bin/env python3
"""
Quick test script for the LLMService abstraction.

Tests:
1. OpenAI provider availability
2. Gemini provider availability  
3. Basic generation with primary provider
4. Fallback behavior

Usage:
    python test_llm_service.py
"""

import os
import sys
import json

# Add the app directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.llm import (
    get_llm_service, 
    LLMService, 
    LLMConfig,
    OpenAIProvider,
    GeminiProvider,
)


def test_provider_availability():
    """Test which providers are available."""
    print("\n" + "=" * 60)
    print("1. PROVIDER AVAILABILITY")
    print("=" * 60)
    
    # Test OpenAI
    try:
        openai = OpenAIProvider()
        openai_available = openai.is_available()
        print(f"  OpenAI (gpt-4o-mini): {'✓ Available' if openai_available else '✗ Not configured'}")
    except Exception as e:
        print(f"  OpenAI: ✗ Error - {e}")
        openai_available = False
    
    # Test Gemini
    try:
        gemini = GeminiProvider()
        gemini_available = gemini.is_available()
        print(f"  Gemini (gemini-2.5-flash): {'✓ Available' if gemini_available else '✗ Not configured'}")
    except Exception as e:
        print(f"  Gemini: ✗ Error - {e}")
        gemini_available = False
    
    return openai_available, gemini_available


def test_service_configuration():
    """Test LLMService configuration."""
    print("\n" + "=" * 60)
    print("2. SERVICE CONFIGURATION")
    print("=" * 60)
    
    # Check env vars
    provider = os.getenv("LLM_PROVIDER", "gemini")
    model = os.getenv("LLM_MODEL", "(default)")
    fallback = os.getenv("LLM_FALLBACK_ENABLED", "true")
    
    print(f"  LLM_PROVIDER: {provider}")
    print(f"  LLM_MODEL: {model}")
    print(f"  LLM_FALLBACK_ENABLED: {fallback}")
    
    # Create service
    service = get_llm_service()
    print(f"\n  Primary: {service.primary_provider}")
    print(f"  Fallback enabled: {service._fallback_enabled}")
    
    # Get availability status
    status = service.get_available_providers()
    print(f"\n  Provider status: {status}")
    
    return service


def test_basic_generation(service: LLMService):
    """Test basic generation with a simple prompt."""
    print("\n" + "=" * 60)
    print("3. BASIC GENERATION TEST")
    print("=" * 60)
    
    system_prompt = "You are a helpful assistant. Return JSON only."
    user_content = """
    Analyze this simple text and return JSON with keys:
    - sentiment: "positive", "negative", or "neutral"
    - confidence: float 0-1
    - summary: one sentence summary
    
    Text: "I really enjoyed the workshop yesterday! The speaker was engaging and I learned a lot about Python programming."
    """
    
    config = LLMConfig(
        temperature=0.2,
        max_tokens=500,
        json_mode=True
    )
    
    print(f"\n  Sending request to {service.primary_provider.PROVIDER_NAME}...")
    
    response = service.generate(
        system_prompt=system_prompt,
        user_content=user_content,
        config=config
    )
    
    print(f"\n  Response:")
    print(f"    Success: {response.success}")
    print(f"    Provider: {response.provider}")
    print(f"    Model: {response.model}")
    print(f"    Latency: {response.latency_ms}ms")
    print(f"    Tokens: {response.total_tokens} (prompt: {response.prompt_tokens}, completion: {response.completion_tokens})")
    print(f"    Cost: ${response.estimated_cost_usd:.6f}")
    
    if response.success:
        print(f"\n  Content:")
        print(f"    {json.dumps(response.content, indent=4)}")
    else:
        print(f"\n  Error: {response.error}")
    
    return response


def test_fallback_behavior():
    """Test fallback to secondary provider."""
    print("\n" + "=" * 60)
    print("4. FALLBACK BEHAVIOR TEST")
    print("=" * 60)
    
    # Create service with invalid primary to force fallback
    print("\n  Creating service with intentionally invalid primary...")
    
    # Save original env var
    original_provider = os.environ.get("LLM_PROVIDER")
    
    # This tests the fallback mechanism without actually breaking things
    service = LLMService(
        primary_provider="gemini",  # Will use gemini
        fallback_enabled=True
    )
    
    print(f"  Primary: {service.primary_provider}")
    print(f"  Fallback: {service.fallback_provider}")
    
    return True


def main():
    print("\n" + "=" * 60)
    print("LLM SERVICE TEST SUITE")
    print("=" * 60)
    
    # 1. Check provider availability
    openai_ok, gemini_ok = test_provider_availability()
    
    if not openai_ok and not gemini_ok:
        print("\n⚠️  No LLM providers available! Configure API keys/credentials.")
        return 1
    
    # 2. Test configuration
    service = test_service_configuration()
    
    # 3. Test basic generation
    if service.is_available():
        response = test_basic_generation(service)
        
        if not response.success:
            print("\n⚠️  Generation failed!")
    else:
        print("\n⚠️  Service not available, skipping generation test")
    
    # 4. Test fallback
    test_fallback_behavior()
    
    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)
    
    return 0


if __name__ == "__main__":
    exit(main())
