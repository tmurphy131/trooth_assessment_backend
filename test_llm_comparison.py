#!/usr/bin/env python3
"""
LLM Comparison Test: OpenAI vs Vertex AI (Gemini)

This script tests both providers with your actual assessment prompt format
and compares: latency, JSON validity, output quality, and cost.

Usage:
  python test_llm_comparison.py
"""

import os
import json
import time
from typing import Dict, Any, Optional
from dataclasses import dataclass

# ============================================================================
# SAMPLE ASSESSMENT DATA (mimics your real format)
# ============================================================================

SAMPLE_PAYLOAD = {
    "apprentice": {
        "id": "test-user-123",
        "name": "Jordan",
        "age_range": "18-25",
        "church": "Grace Community Church"
    },
    "assessment": {
        "id": "test-assessment-001",
        "template_id": "master_v1",
        "submitted_at": "2026-01-31T15:00:00Z",
        "version": "v2",
        "categories": [
            {"name": "Prayer Life"},
            {"name": "Scripture Engagement"},
            {"name": "Community & Fellowship"},
            {"name": "Biblical Knowledge"}
        ],
        "mc_summary": {
            "total_questions": 25,
            "correct_count": 18,
            "percent_correct": 72.0,
            "by_topic": [
                {"topic": "Gospels", "correct": 8, "total": 10},
                {"topic": "Pentateuch", "correct": 4, "total": 8},
                {"topic": "Pauline Epistles", "correct": 6, "total": 7}
            ],
            "wrong_items": [
                {
                    "question_id": "q1",
                    "question_text": "Who wrote the book of Romans?",
                    "correct_answer": "Paul",
                    "apprentice_answer": "Peter",
                    "topic": "Pauline Epistles"
                },
                {
                    "question_id": "q2",
                    "question_text": "How many days did God take to create the world according to Genesis?",
                    "correct_answer": "6 days",
                    "apprentice_answer": "7 days",
                    "topic": "Pentateuch"
                },
                {
                    "question_id": "q3",
                    "question_text": "What was the first miracle Jesus performed?",
                    "correct_answer": "Turning water into wine at Cana",
                    "apprentice_answer": "Healing the blind man",
                    "topic": "Gospels"
                }
            ]
        },
        "open_ended": [
            {
                "category": "Prayer Life",
                "question_id": "oe1",
                "question_text": "Describe your current prayer routine and how consistent you are with it.",
                "apprentice_answer": "I try to pray every morning for about 10-15 minutes. I usually thank God for the day and ask for help with work and family. Sometimes I forget when I'm busy or rushing. I've been trying to add more time for listening but it's hard to quiet my mind. I use a prayer journal about twice a week which helps me stay focused.",
                "rubric": {"dimensions": []}
            },
            {
                "category": "Scripture Engagement",
                "question_id": "oe2",
                "question_text": "How do you currently engage with the Bible and what methods have you found most helpful?",
                "apprentice_answer": "I read my Bible most days, usually a chapter or two from whatever book I'm going through. Right now I'm in John. I sometimes use a devotional app that gives me a short passage and explanation. I haven't really tried deep study methods yet but I want to learn. Memorizing verses is really hard for me.",
                "rubric": {"dimensions": []}
            },
            {
                "category": "Community & Fellowship",
                "question_id": "oe3",
                "question_text": "Describe your involvement in Christian community and how you experience fellowship with other believers.",
                "apprentice_answer": "I go to church most Sundays, maybe 2-3 times a month. I'm in a small group that meets every other Wednesday but I miss it sometimes because of work. I have a few Christian friends I text with but we don't really talk about deep spiritual stuff much. I want to be more connected but it's hard to find time.",
                "rubric": {"dimensions": []}
            }
        ]
    }
}

# ============================================================================
# PROMPT (simplified version of your v2.1 prompt)
# ============================================================================

SYSTEM_PROMPT = "You must return STRICT JSON only. No markdown, no explanations outside JSON."

USER_PROMPT = """
# T[root]H Master Assessment — Mentor Report v2.1

## ROLE
Pastor-mentor and assessment analyst. Turn assessment data into concise, pastoral mentor reports.

## OUTPUT (STRICT JSON)
Return a JSON object with these exact keys:
{
  "health_score": <int 0-100>,
  "health_band": "<Flourishing|Maturing|Stable|Developing|Beginning>",
  "strengths": ["<strength 1>", "<strength 2>", "<strength 3>"],
  "gaps": ["<gap 1>", "<gap 2>", "<gap 3>"],
  "priority_action": {
    "title": "<action title>",
    "description": "<2-3 sentences explaining why>",
    "steps": ["<step 1>", "<step 2>", "<step 3>"],
    "scripture": "<Book chapter:verse - brief explanation>"
  },
  "biblical_knowledge": {
    "percent": <float>,
    "weak_topics": ["<topic 1>", "<topic 2>"],
    "study_recommendation": "<1-2 sentences>"
  },
  "insights": [
    {
      "category": "<category name>",
      "level": "<Flourishing|Maturing|Stable|Developing|Beginning>",
      "observation": "<2-3 sentences based on their answers>",
      "next_step": "<specific actionable advice>"
    }
  ],
  "flags": {
    "red": [],
    "yellow": ["<watch item if any>"],
    "green": ["<encouragement>"]
  },
  "conversation_starters": ["<question 1>", "<question 2>"],
  "recommended_resources": [
    {"title": "<book/resource>", "why": "<1 sentence>", "type": "book"}
  ]
}

## RULES
1. MC = Objective (use correct/incorrect). Open = Descriptive (assess maturity, don't grade).
2. Health score: Weighted (MC 60%, open 40%).
3. Health bands: 85+ Flourishing, 70-84 Maturing, 55-69 Stable, 40-54 Developing, <40 Beginning.
4. Be pastorally honest; avoid false praise.
5. Return valid JSON only.

## INPUT DATA
"""


@dataclass
class LLMResult:
    provider: str
    model: str
    latency_ms: int
    success: bool
    json_valid: bool
    output: Optional[Dict[str, Any]]
    raw_response: str
    error: Optional[str]
    tokens_used: int
    estimated_cost_usd: float


def test_openai(payload: dict) -> LLMResult:
    """Test OpenAI gpt-4o-mini"""
    from openai import OpenAI
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return LLMResult(
            provider="OpenAI",
            model="gpt-4o-mini",
            latency_ms=0,
            success=False,
            json_valid=False,
            output=None,
            raw_response="",
            error="OPENAI_API_KEY not set",
            tokens_used=0,
            estimated_cost_usd=0
        )
    
    client = OpenAI(api_key=api_key)
    
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": USER_PROMPT + json.dumps(payload, indent=2)},
    ]
    
    start = time.time()
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.2,
            max_tokens=2000,
            response_format={"type": "json_object"}
        )
        latency_ms = int((time.time() - start) * 1000)
        
        raw = response.choices[0].message.content or ""
        tokens = response.usage.total_tokens if response.usage else 0
        prompt_tokens = response.usage.prompt_tokens if response.usage else 0
        completion_tokens = response.usage.completion_tokens if response.usage else 0
        
        # gpt-4o-mini: $0.150/1M input, $0.600/1M output
        cost = (prompt_tokens * 0.150 + completion_tokens * 0.600) / 1_000_000
        
        try:
            parsed = json.loads(raw)
            return LLMResult(
                provider="OpenAI",
                model="gpt-4o-mini",
                latency_ms=latency_ms,
                success=True,
                json_valid=True,
                output=parsed,
                raw_response=raw,
                error=None,
                tokens_used=tokens,
                estimated_cost_usd=cost
            )
        except json.JSONDecodeError as e:
            return LLMResult(
                provider="OpenAI",
                model="gpt-4o-mini",
                latency_ms=latency_ms,
                success=True,
                json_valid=False,
                output=None,
                raw_response=raw,
                error=f"JSON parse error: {e}",
                tokens_used=tokens,
                estimated_cost_usd=cost
            )
    except Exception as e:
        return LLMResult(
            provider="OpenAI",
            model="gpt-4o-mini",
            latency_ms=int((time.time() - start) * 1000),
            success=False,
            json_valid=False,
            output=None,
            raw_response="",
            error=str(e),
            tokens_used=0,
            estimated_cost_usd=0
        )


def test_vertex_gemini(payload: dict) -> LLMResult:
    """Test Vertex AI Gemini using google-genai SDK (new recommended approach)"""
    try:
        from google import genai
        from google.genai import types
    except ImportError:
        return LLMResult(
            provider="Vertex AI",
            model="gemini-2.0-flash",
            latency_ms=0,
            success=False,
            json_valid=False,
            output=None,
            raw_response="",
            error="google-genai not installed (pip install google-genai)",
            tokens_used=0,
            estimated_cost_usd=0
        )
    
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "trooth-prod")
    location = "us-central1"
    
    # Initialize client for Vertex AI
    client = genai.Client(
        vertexai=True,
        project=project_id,
        location=location
    )
    
    prompt = SYSTEM_PROMPT + "\n\n" + USER_PROMPT + json.dumps(payload, indent=2)
    
    start = time.time()
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash-001",
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.2,
                max_output_tokens=2000,
                response_mime_type="application/json"
            )
        )
        latency_ms = int((time.time() - start) * 1000)
        
        raw = response.text if response.text else ""
        
        # Get actual token usage from response
        tokens = 0
        if hasattr(response, 'usage_metadata'):
            tokens = getattr(response.usage_metadata, 'total_token_count', 0)
        if not tokens:
            tokens = len(prompt.split()) + len(raw.split())  # fallback estimate
        
        # gemini-2.0-flash pricing: ~$0.075/1M input, ~$0.30/1M output (rough)
        cost = tokens * 0.0001 / 1000  # Very rough estimate
        
        try:
            parsed = json.loads(raw)
            return LLMResult(
                provider="Vertex AI",
                model="gemini-2.0-flash",
                latency_ms=latency_ms,
                success=True,
                json_valid=True,
                output=parsed,
                raw_response=raw,
                error=None,
                tokens_used=tokens,
                estimated_cost_usd=cost
            )
        except json.JSONDecodeError as e:
            return LLMResult(
                provider="Vertex AI",
                model="gemini-2.0-flash",
                latency_ms=latency_ms,
                success=True,
                json_valid=False,
                output=None,
                raw_response=raw,
                error=f"JSON parse error: {e}",
                tokens_used=tokens,
                estimated_cost_usd=cost
            )
    except Exception as e:
        return LLMResult(
            provider="Vertex AI",
            model="gemini-2.0-flash",
            latency_ms=int((time.time() - start) * 1000),
            success=False,
            json_valid=False,
            output=None,
            raw_response="",
            error=str(e),
            tokens_used=0,
            estimated_cost_usd=0
        )


def validate_output_schema(output: Dict[str, Any]) -> Dict[str, bool]:
    """Check if output has all required fields"""
    required_keys = [
        "health_score", "health_band", "strengths", "gaps",
        "priority_action", "biblical_knowledge", "insights",
        "flags", "conversation_starters", "recommended_resources"
    ]
    
    results = {}
    for key in required_keys:
        results[key] = key in output
    
    # Check nested structure
    if output.get("priority_action"):
        pa = output["priority_action"]
        results["priority_action.title"] = "title" in pa
        results["priority_action.steps"] = "steps" in pa and isinstance(pa.get("steps"), list)
    
    if output.get("biblical_knowledge"):
        bk = output["biblical_knowledge"]
        results["biblical_knowledge.percent"] = "percent" in bk
        results["biblical_knowledge.weak_topics"] = "weak_topics" in bk
    
    return results


def print_result(result: LLMResult):
    """Pretty print a single result"""
    status = "✅" if result.success and result.json_valid else "❌"
    print(f"\n{'='*60}")
    print(f"{status} {result.provider} ({result.model})")
    print(f"{'='*60}")
    print(f"  Latency:     {result.latency_ms:,} ms")
    print(f"  Success:     {result.success}")
    print(f"  JSON Valid:  {result.json_valid}")
    print(f"  Tokens:      ~{result.tokens_used:,}")
    print(f"  Est. Cost:   ${result.estimated_cost_usd:.6f}")
    
    if result.error:
        print(f"  Error:       {result.error}")
    
    if result.output:
        print(f"\n  Output Preview:")
        print(f"    health_score: {result.output.get('health_score')}")
        print(f"    health_band:  {result.output.get('health_band')}")
        print(f"    strengths:    {len(result.output.get('strengths', []))} items")
        print(f"    gaps:         {len(result.output.get('gaps', []))} items")
        print(f"    insights:     {len(result.output.get('insights', []))} items")
        
        # Schema validation
        schema_check = validate_output_schema(result.output)
        missing = [k for k, v in schema_check.items() if not v]
        if missing:
            print(f"\n  ⚠️ Missing fields: {missing}")
        else:
            print(f"\n  ✅ All required fields present")


def main():
    print("\n" + "="*60)
    print("  LLM COMPARISON TEST: OpenAI vs Vertex AI (Gemini)")
    print("="*60)
    print("\nTesting with sample assessment data...")
    print(f"  - MC Questions: {SAMPLE_PAYLOAD['assessment']['mc_summary']['total_questions']}")
    print(f"  - MC Correct:   {SAMPLE_PAYLOAD['assessment']['mc_summary']['correct_count']}")
    print(f"  - Open-ended:   {len(SAMPLE_PAYLOAD['assessment']['open_ended'])}")
    
    results = []
    
    # Test OpenAI
    print("\n\n🔄 Testing OpenAI gpt-4o-mini...")
    openai_result = test_openai(SAMPLE_PAYLOAD)
    results.append(openai_result)
    print_result(openai_result)
    
    # Test Vertex AI Gemini
    print("\n\n🔄 Testing Vertex AI gemini-2.0-flash...")
    gemini_result = test_vertex_gemini(SAMPLE_PAYLOAD)
    results.append(gemini_result)
    print_result(gemini_result)
    
    # Summary comparison
    print("\n\n" + "="*60)
    print("  COMPARISON SUMMARY")
    print("="*60)
    
    successful = [r for r in results if r.success and r.json_valid]
    if len(successful) >= 2:
        fastest = min(successful, key=lambda r: r.latency_ms)
        print(f"\n  🏆 Fastest:     {fastest.provider} ({fastest.latency_ms:,} ms)")
        
        latency_diff = abs(results[0].latency_ms - results[1].latency_ms)
        print(f"  📊 Latency Δ:   {latency_diff:,} ms")
        
        if results[0].latency_ms > 0 and results[1].latency_ms > 0:
            if results[1].latency_ms < results[0].latency_ms:
                pct = ((results[0].latency_ms - results[1].latency_ms) / results[0].latency_ms) * 100
                print(f"  📈 Gemini is {pct:.1f}% faster than OpenAI")
            else:
                pct = ((results[1].latency_ms - results[0].latency_ms) / results[1].latency_ms) * 100
                print(f"  📈 OpenAI is {pct:.1f}% faster than Gemini")
    
    # Save full results to file
    output_file = "llm_comparison_results.json"
    with open(output_file, "w") as f:
        json.dump({
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "results": [
                {
                    "provider": r.provider,
                    "model": r.model,
                    "latency_ms": r.latency_ms,
                    "success": r.success,
                    "json_valid": r.json_valid,
                    "error": r.error,
                    "tokens_used": r.tokens_used,
                    "estimated_cost_usd": r.estimated_cost_usd,
                    "output": r.output
                }
                for r in results
            ]
        }, f, indent=2)
    
    print(f"\n  📁 Full results saved to: {output_file}")
    print("\n")


if __name__ == "__main__":
    main()
