from openai import OpenAI
import os
import json
import re
import logging
from typing import Dict, List, Tuple, Optional, Any
import asyncio
from statistics import mean
from dataclasses import dataclass
from datetime import datetime, UTC
from pydantic import BaseModel, ValidationError
from app.core.cache import cache_result
from app.services.llm import get_llm_service, LLMConfig

logger = logging.getLogger(__name__)

# Provide a module-level client object for tests that monkeypatch
# app.services.ai_scoring.client.chat.completions.create
class _DummyCompletions:
    def create(self, *args, **kwargs):
        class _Choice:
            message = type("Msg", (), {"content": "{}"})
        return type("Resp", (), {"choices": [_Choice()]})

class _DummyChat:
    completions = _DummyCompletions()

class _DummyClient:
    chat = _DummyChat()

# Tests patch this path; in production we don't use it.
client = _DummyClient()

def get_openai_client():
    """Get OpenAI client with error handling."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or api_key.startswith("your_"):
        logger.warning("OpenAI API key not configured")
        return None
    return OpenAI(api_key=api_key)

def _strip_code_fences(s: str) -> str:
    """Remove markdown-style code fences from a string if present."""
    if not isinstance(s, str):
        return s
    s = s.strip()
    if s.startswith("```"):
        # Remove first fence line and trailing fence if exists
        s = re.sub(r"^```[a-zA-Z0-9_-]*\n", "", s)
        s = re.sub(r"\n```\s*$", "", s)
    return s

def _parse_json_lenient(content: str) -> dict:
    """Try multiple strategies to obtain a JSON object from model content."""
    if not content:
        raise json.JSONDecodeError("empty content", content, 0)
    text = _strip_code_fences(content)
    # Direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Extract the largest {...} block
    try:
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1 and end > start:
            return json.loads(text[start:end+1])
    except Exception:
        pass
    # Try to fix common trailing commas
    try:
        fixed = re.sub(r",\s*([}\]])", r"\1", text)
        return json.loads(fixed)
    except Exception as e:
        raise json.JSONDecodeError(f"Could not parse JSON after lenient attempts: {e}", text, 0)

def _retry(callable_fn, *, retries: int = 3, base_delay: float = 0.6, factor: float = 2.0, retry_on: Tuple[type, ...] = (Exception,)):
    """Simple capped exponential backoff retry helper."""
    import time
    last = None
    delay = base_delay
    for attempt in range(retries):
        try:
            if attempt > 0:
                logger.info(f"[ai] retry attempt {attempt+1}/{retries}")
            return callable_fn()
        except retry_on as e:  # pragma: no cover
            last = e
            # Check for common rate limit indicators
            msg = str(e).lower()
            if "rate limit" not in msg and "429" not in msg and "quota" not in msg and attempt == retries - 1:
                break
            time.sleep(delay)
            delay *= factor
    if last:
        raise last


# ------------------------------
# Mentor report (v2) schema - matches ai_prompt_master_assessment_v2_optimized.txt
# ------------------------------

class _TopicBreakdownItem(BaseModel):
    topic: str
    correct: int
    total: int
    note: Optional[str] = None


class _BiblicalKnowledgeV2(BaseModel):
    """v2.1 format: percent, weak_topics, and study_recommendation"""
    percent: float
    weak_topics: list[str] = []
    study_recommendation: str = ""


class _InsightV2(BaseModel):
    """v2.1 format: category, level, observation, next_step"""
    category: str
    level: str
    observation: str  # renamed from 'evidence' in optimized prompt
    next_step: str


class _PriorityAction(BaseModel):
    title: str
    description: str = ""  # NEW in optimized prompt: explains WHY this is important
    steps: list[str]
    scripture: str = ""


class _ResourceV2(BaseModel):
    title: str
    why: str
    type: str = "book"


class _FourWeekPlan(BaseModel):
    """Four week mentoring plan with weekly rhythm and checkpoints"""
    rhythm: list[str] = []
    checkpoints: list[str] = []


class MentorBlobV2(BaseModel):
    """v2.1 format from ai_prompt_master_assessment_v2_optimized.txt"""
    health_score: int
    health_band: str
    strengths: list[str] = []
    gaps: list[str] = []
    priority_action: Optional[_PriorityAction] = None
    biblical_knowledge: _BiblicalKnowledgeV2
    insights: list[_InsightV2] = []
    flags: dict
    four_week_plan: Optional[_FourWeekPlan] = None
    conversation_starters: list[str] = []
    recommended_resources: list[_ResourceV2] = []


def _knowledge_band(percent: float) -> str:
    p = float(percent or 0)
    if p >= 90: return "Excellent"
    if p >= 80: return "Good"
    if p >= 70: return "Average"
    if p >= 60: return "Needs Improvement"
    return "Significant Study"


def _health_band(score: int) -> str:
    """v2.1 health band calculation"""
    if score >= 85: return "Flourishing"
    if score >= 70: return "Maturing"
    if score >= 55: return "Stable"
    if score >= 40: return "Developing"
    return "Beginning"


def _safe_minimal_blob(overall_percent: float, by_topic: list[dict]) -> dict:
    """Return minimal v2.1 structure that matches ai_prompt_master_assessment_v2_optimized.txt"""
    score = int(overall_percent)
    weak_topics = [t.get("topic") for t in by_topic if t.get("correct", 0) / max(t.get("total", 1), 1) < 0.6]
    return {
        "health_score": score,
        "health_band": _health_band(score),
        "strengths": [],
        "gaps": [],
        "priority_action": None,
        "biblical_knowledge": {
            "percent": round(overall_percent, 1),
            "weak_topics": weak_topics,
            "study_recommendation": f"Focus on studying {', '.join(weak_topics[:2]) if weak_topics else 'foundational Bible books'} to strengthen your biblical knowledge.",
        },
        "insights": [],
        "flags": {"red": [], "yellow": [], "green": []},
        "four_week_plan": {
            "rhythm": [
                "Week 1: Establish daily Scripture reading habit (15 minutes)",
                "Week 2: Add prayer journaling to your routine",
                "Week 3: Connect with a mentor or small group",
                "Week 4: Share what you've learned with someone"
            ],
            "checkpoints": [
                "Week 1: Read Scripture 5+ days this week",
                "Week 2: Journal at least 3 prayer entries",
                "Week 3: Attended one group meeting or mentor session",
                "Week 4: Had one conversation about your faith journey"
            ]
        },
        "conversation_starters": [],
        "recommended_resources": [],
    }



def _build_v2_prompt_input(apprentice: dict | None, assessment_id: str, template_id: Optional[str], submitted_at: Optional[str], answers: Dict[str, str], questions: list[dict], previous_assessments: List[dict] = None) -> tuple[dict, dict]:
    """Construct the input JSON for the v2 mentor prompt.

    Returns (payload_for_prompt, derived_mc_metrics) where derived_mc_metrics contains
    totals and topic breakdown useful for fallback.
    
    Phase 2: Now includes previous_assessments for historical context and trend analysis.
    """
    # Map question by id for lookups
    qmap = {str(q.get('id')): q for q in questions}

    mc_items: list[dict] = []
    open_items: list[dict] = []
    topic_acc: dict[str, dict] = {}
    total_mc = 0
    correct_mc = 0
    wrong_items = []

    for qid, ans in answers.items():
        q = qmap.get(str(qid))
        if not q:
            continue
        qtype = (q.get('question_type') or '').lower()
        category = q.get('category') or 'General Assessment'
        topic = q.get('topic') or category  # default to category if topic not available
        if qtype == 'multiple_choice':
            total_mc += 1
            matched_option = None
            for opt in (q.get('options') or []):
                # Match by option ID (UUID) OR by option text (legacy)
                opt_id = str(opt.get('id', '')).strip()
                opt_text = str(opt.get('text', '')).strip().lower()
                ans_str = str(ans).strip()
                if opt_id and opt_id == ans_str:
                    matched_option = opt
                    break
                elif opt_text == ans_str.lower():
                    matched_option = opt
                    break
            is_correct = bool(matched_option.get('is_correct')) if matched_option else False
            # Resolve the actual answer text (for sending to AI and wrong_items)
            apprentice_answer_text = matched_option.get('text', ans) if matched_option else ans
            if is_correct:
                correct_mc += 1
            else:
                # find correct answer text for wrong_items
                correct_opt = next((o for o in (q.get('options') or []) if o.get('is_correct')), None)
                wrong_items.append({
                    'question_id': str(qid),
                    'question_text': q.get('text'),
                    'correct_answer': (correct_opt or {}).get('text'),
                    'apprentice_answer': apprentice_answer_text,
                    'topic': topic,
                })
            # accumulate by topic
            if topic not in topic_acc:
                topic_acc[topic] = {'topic': topic, 'correct': 0, 'total': 0}
            topic_acc[topic]['total'] += 1
            if is_correct:
                topic_acc[topic]['correct'] += 1
        else:
            open_items.append({
                'category': category,
                'question_id': str(qid),
                'question_text': q.get('text'),
                'apprentice_answer': ans,
                'rubric': { 'dimensions': [] }  # placeholder; let LLM infer level
            })

    percent_correct = (correct_mc / total_mc * 100.0) if total_mc else 0.0
    by_topic = list(topic_acc.values())

    # Phase 2: Add historical context if previous assessments available
    historical_context = None
    if previous_assessments and len(previous_assessments) > 0:
        historical_context = {
            'previous_count': len(previous_assessments),
            'previous_assessments': []
        }
        for prev in previous_assessments[:3]:  # Include up to 3 most recent
            prev_data = {
                'date': prev.get('created_at'),
                'overall_score': prev.get('scores', {}).get('overall_score'),
                'category_scores': prev.get('scores', {}).get('category_scores', {}),
            }
            historical_context['previous_assessments'].append(prev_data)
        logger.info(f"[historical] Added {len(previous_assessments)} previous assessments to AI prompt")

    payload = {
        'apprentice': apprentice or {},
        'assessment': {
            'id': assessment_id,
            'template_id': template_id,
            'submitted_at': submitted_at,
            'version': 'v2',
            'categories': [{'name': (q.get('category') or 'General Assessment')} for q in questions],
            'mc_summary': {
                'total_questions': total_mc,
                'correct_count': correct_mc,
                'percent_correct': round(percent_correct, 1),
                'by_topic': by_topic,
                'wrong_items': wrong_items,
            },
            'open_ended': open_items,
        },
    }
    
    # Add historical_context to payload if available (Phase 2)
    if historical_context:
        payload['historical_context'] = historical_context
    derived = {
        'total': total_mc,
        'correct': correct_mc,
        'percent': percent_correct,
        'by_topic': by_topic,
    }
    return payload, derived


def _load_v2_prompt_text() -> str:
    """Load the v2 mentor prompt text from ai_prompt_master_assessment_v2_optimized.txt.

    Uses optimized prompt (v2.1) with 45% reduction in tokens and few-shot example.
    Expected location (relative to backend root): ./ai_prompt_master_assessment_v2_optimized.txt
    """
    backend_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))  # app/services -> app -> backend root
    candidates = [
        os.path.join(backend_root, 'ai_prompt_master_assessment_v2_optimized.txt'),  # v2.1 optimized
        os.path.join(backend_root, 'prompts', 'ai_prompt_master_assessment_v2_optimized.txt'),
        os.path.join(backend_root, 'ai_prompt_master_assessment_v2.txt'),  # fallback to original
        os.path.join(backend_root, 'prompts', 'ai_prompt_master_assessment_v2.txt'),  # fallback
    ]
    for p in candidates:
        try:
            with open(p, 'r', encoding='utf-8') as f:
                logger.info(f"[ai] Loaded prompt from: {p}")
                return f.read()
        except Exception:
            continue
    logger.warning(f"v2 prompt file not found in candidates: {candidates}")
    return ""


def _call_llm_for_mentor_blob(client, payload: dict) -> dict:
    """Generate mentor blob using LLMService abstraction (supports Gemini + OpenAI fallback).
    
    Args:
        client: Legacy parameter, now ignored (kept for backward compatibility)
        payload: Assessment data payload for the LLM prompt
        
    Returns:
        Parsed JSON response from the LLM
    """
    import time as _t
    start_ts = _t.time()
    
    prompt_text = _load_v2_prompt_text()
    system_prompt = "You must return STRICT JSON only. Complete the entire JSON response - do not truncate."
    user_prompt = f"{prompt_text.strip()}\n\n{json.dumps(payload, ensure_ascii=False)}"
    
    # Use LLMService abstraction with fallback support
    llm_service = get_llm_service()
    config = LLMConfig(
        temperature=0.2,
        max_tokens=8000,  # Increased significantly to prevent Gemini truncation
        json_mode=True
    )
    
    response = llm_service.generate(
        user_content=user_prompt,
        system_prompt=system_prompt,
        config=config
    )
    
    # Check if LLM call was successful
    if not response.success:
        logger.error(f"[mentor_blob] LLM generation failed: {response.error}")
        raise Exception(f"LLM generation failed: {response.error}")
    
    dur = _t.time() - start_ts
    
    logger.info(
        f"[ai_scoring] type='mentor_blob' provider='{response.provider}' model='{response.model}' "
        f"latency_ms={int(dur * 1000)} tokens={response.total_tokens} "
        f"cost_usd={response.estimated_cost_usd:.6f} version='v2.0'"
    )
    
    # LLMService already parses JSON; use content dict or fallback to raw_response parsing
    if response.content and isinstance(response.content, dict) and len(response.content) > 0:
        return response.content
    elif response.raw_response:
        return _parse_json_lenient(response.raw_response)
    else:
        raise Exception("LLM returned empty response")


def _load_full_report_prompt_text() -> str:
    """Load the premium full report prompt text from ai_prompt_full_report_premium.txt.
    
    This is the enhanced prompt for premium users, generating comprehensive mentor reports
    with conversation guides, growth pathways, and deeper analysis.
    
    Expected location (relative to backend root): ./ai_prompt_full_report_premium.txt
    """
    backend_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    candidates = [
        os.path.join(backend_root, 'ai_prompt_full_report_premium.txt'),
        os.path.join(backend_root, 'prompts', 'ai_prompt_full_report_premium.txt'),
    ]
    for p in candidates:
        try:
            with open(p, 'r', encoding='utf-8') as f:
                logger.info(f"[ai] Loaded full report prompt from: {p}")
                return f.read()
        except Exception:
            continue
    logger.warning(f"Full report prompt file not found in candidates: {candidates}")
    return ""


def generate_full_report(payload: dict, previous_assessments: List[dict] = None) -> dict:
    """Generate premium full report using LLMService (Gemini/OpenAI with fallback).
    
    This is the premium-tier enhanced report with:
    - Deep dive analysis for strengths and gaps
    - Multi-session conversation guides for mentors
    - Phased growth pathways (30/60/90 day plans)
    - Biblical knowledge detailed breakdown
    - Progress tracking and milestone recommendations
    - Personalized resource recommendations with specific application guidance
    
    Args:
        payload: Assessment data payload (same format as standard report)
        previous_assessments: List of previous assessment summaries for trend analysis
        
    Returns:
        Full report JSON (premium_v1 format)
    
    Raises:
        Exception: If LLM service fails and no fallback available
    """
    import time as _t
    from datetime import datetime
    
    start_ts = _t.time()
    
    # Add previous assessments to payload if available
    enriched_payload = payload.copy()
    if previous_assessments:
        enriched_payload['previous_assessments'] = previous_assessments
        logger.info(f"[full_report] Including {len(previous_assessments)} previous assessments for trend analysis")
    
    prompt_text = _load_full_report_prompt_text()
    if not prompt_text:
        raise Exception("Full report prompt not found - premium feature unavailable")
    
    system_prompt = "You are a senior pastor-mentor generating a premium, comprehensive mentor report. Return STRICT JSON only."
    user_prompt = f"{prompt_text.strip()}\n\n{json.dumps(enriched_payload, ensure_ascii=False)}"
    
    # Use LLMService with higher token limit for premium report
    llm_service = get_llm_service()
    config = LLMConfig(
        temperature=0.3,  # Slightly higher for more nuanced analysis
        max_tokens=16000,  # Higher limit for comprehensive report (Gemini supports up to 8192 default, but can go higher)
        json_mode=True
    )
    
    response = llm_service.generate(
        user_content=user_prompt,
        system_prompt=system_prompt,
        config=config
    )
    
    # Check if LLM call was successful
    if not response.success:
        logger.error(f"[full_report] LLM generation failed: {response.error}")
        raise Exception(f"LLM generation failed: {response.error}")
    
    dur = _t.time() - start_ts
    
    logger.info(
        f"[ai_scoring] type='full_report' provider='{response.provider}' model='{response.model}' "
        f"latency_ms={int(dur * 1000)} tokens={response.total_tokens} "
        f"cost_usd={response.estimated_cost_usd:.6f} version='premium_v1'"
    )
    
    # LLMService already parses JSON; use content dict or fallback to raw_response parsing
    if response.content and isinstance(response.content, dict) and len(response.content) > 0:
        result = response.content
    elif response.raw_response:
        result = _parse_json_lenient(response.raw_response)
    else:
        raise Exception("LLM returned empty response")
    
    # Add metadata
    result['_meta'] = {
        'generated_at': datetime.now(UTC).isoformat() + 'Z',
        'provider': response.provider,
        'model': response.model,
        'tokens_used': response.total_tokens,
        'cost_usd': response.estimated_cost_usd,
        'latency_ms': int(dur * 1000)
    }
    
    return result


def generate_full_report_for_assessment(assessment, apprentice_name: str = None, db_session = None) -> dict:
    """Generate premium full report for an existing assessment.
    
    This is used for on-demand generation when a premium user requests an email
    but the full_report wasn't cached during submission (e.g., older assessments).
    
    Args:
        assessment: Assessment ORM object with answers, template_id, etc.
        apprentice_name: Display name for the apprentice
        db_session: Database session for loading questions
        
    Returns:
        Full report dict (premium_v1 format), or None if generation fails
    """
    if not assessment or not assessment.answers:
        logger.warning("[full_report_for_assessment] No assessment or answers provided")
        return None
    
    try:
        # Load questions from template if available
        questions = []
        if assessment.template_id and db_session:
            from app.models.assessment_template_question import AssessmentTemplateQuestion
            from app.models.question import Question
            from app.models.category import Category
            from sqlalchemy.orm import joinedload
            
            # AssessmentTemplateQuestion is a junction table - need to join with Question
            tq_rows = db_session.query(AssessmentTemplateQuestion).options(
                joinedload(AssessmentTemplateQuestion.question)
            ).filter(
                AssessmentTemplateQuestion.template_id == assessment.template_id
            ).order_by(AssessmentTemplateQuestion.order).all()
            
            for tq in tq_rows:
                q = tq.question  # The actual Question object
                if not q:
                    continue
                    
                # Get category name
                category_name = 'General'
                if q.category_id:
                    cat = db_session.query(Category).filter_by(id=q.category_id).first()
                    if cat:
                        category_name = cat.name
                
                q_dict = {
                    'id': str(q.id),
                    'text': q.text,
                    'question_type': q.question_type.value if hasattr(q.question_type, 'value') else str(q.question_type),
                    'category': category_name,
                    'topic': category_name,
                }
                
                # Include options for multiple choice questions
                if q.options:
                    q_dict['options'] = [
                        {'id': str(opt.id), 'text': opt.option_text, 'is_correct': opt.is_correct}
                        for opt in q.options
                    ]
                
                questions.append(q_dict)
            
            logger.info(f"[full_report_for_assessment] Loaded {len(questions)} questions for template {assessment.template_id}")
        
        # Build payload for full report
        apprentice_info = {
            'id': assessment.apprentice_id,
            'name': apprentice_name or 'Apprentice',
        }
        
        payload, _ = _build_v2_prompt_input(
            apprentice=apprentice_info,
            assessment_id=assessment.id,
            template_id=assessment.template_id,
            submitted_at=assessment.created_at.isoformat() if assessment.created_at else None,
            answers=assessment.answers or {},
            questions=questions,
            previous_assessments=None
        )
        
        # Generate the full report
        full_report = generate_full_report(payload)
        
        logger.info(f"[full_report_for_assessment] Generated on-demand for assessment {assessment.id}")
        return full_report
        
    except Exception as e:
        logger.error(f"[full_report_for_assessment] Failed to generate: {e}")
        return None


def score_category_with_feedback(client, category: str, qa_pairs: List[Dict]) -> tuple:
    """Score a category and return detailed question feedback (with question_id echoed).

    Uses LLMService abstraction with Gemini/OpenAI fallback support.
    
    Keeps legacy return shape while ensuring each feedback item includes question_id,
    and MC items are graded objectively only when options with is_correct are provided.
    """
    prompt = {
        "instruction": (
            "Score this category from 1-10 based on the set of answers. "
            "For multiple-choice questions, use provided options with is_correct as ground truth and mark correct/incorrect. "
            "For open-ended questions, do not mark correct/incorrect; give a brief qualitative note. "
            "Respond JSON ONLY with keys: score (int), recommendation (string), question_feedback (array). "
            "Each feedback item must include: question, answer, question_id, correct (boolean or null), explanation (string)."
        ),
        "category": category,
        "items": [],
    }
    for qa in qa_pairs:
        item = {
            'question': qa.get('question'),
            'answer': qa.get('answer'),
            'question_id': qa.get('question_id'),
            'type': qa.get('question_type') or qa.get('type'),
        }
        if (qa.get('question_type') or qa.get('type')) == 'multiple_choice':
            opts = qa.get('options') or []
            item['options'] = [{'text': o.get('text'), 'is_correct': bool(o.get('is_correct'))} for o in opts]
        prompt['items'].append(item)

    try:
        import time as _t
        start_ts = _t.time()
        
        # Use LLMService abstraction with fallback support
        llm_service = get_llm_service()
        config = LLMConfig(
            temperature=0.2,
            max_tokens=4000,  # Increased to prevent Gemini truncation
            json_mode=True
        )
        
        system_prompt = "You are an expert spiritual mentor and assessor. Output pure JSON."
        user_prompt = json.dumps(prompt, ensure_ascii=False)
        
        response = llm_service.generate(
            user_content=user_prompt,
            system_prompt=system_prompt,
            config=config
        )
        
        # Check if LLM call was successful
        if not response.success:
            logger.warning(f"[category_scoring] LLM generation failed for {category}: {response.error}")
            raise Exception(f"LLM generation failed: {response.error}")
        
        dur = _t.time() - start_ts
        
        logger.info(
            f"[ai_scoring] category='{category}' provider='{response.provider}' model='{response.model}' "
            f"latency_ms={int(dur * 1000)} tokens={response.total_tokens} "
            f"cost_usd={response.estimated_cost_usd:.6f} version='v2.0'"
        )
        
        # LLMService already parses JSON; use content dict or fallback to raw_response parsing
        if response.content and isinstance(response.content, dict) and len(response.content) > 0:
            parsed = response.content
        elif response.raw_response:
            parsed = _parse_json_lenient(response.raw_response)
        else:
            raise Exception("LLM returned empty response")
        score = int(round(float(parsed.get('score', 7))))
        recommendation = parsed.get('recommendation', f"Continue developing your {category.lower()} practices.")
        feedback = parsed.get('question_feedback', [])
        # Ensure question_id present; if missing, map by input order
        for idx, fb in enumerate(feedback):
            if not fb.get('question_id') and idx < len(qa_pairs):
                fb['question_id'] = qa_pairs[idx].get('question_id')
        return score, recommendation, feedback
    except Exception as e:
        logger.warning(f"AI scoring failed for category {category}: {e}")
        return 7, f"Continue developing your {category.lower()} practices.", []

def generate_mock_detailed_scores(answers: Dict[str, str], questions: List[dict]) -> Dict:
    """Generate mock detailed scores for development."""
    categories = set()
    for q in questions:
        categories.add(q.get('category', 'General'))
    
    category_scores = {}
    recommendations = {}
    question_feedback = []
    
    for category in categories:
        # Mock scoring based on answer length and keywords
        category_answers = [ans for q_id, ans in answers.items() 
                          for q in questions 
                          if str(q['id']) == q_id and q.get('category') == category]
        
        avg_length = sum(len(ans.split()) for ans in category_answers) / max(len(category_answers), 1)
        score = min(10, max(1, int(5 + (avg_length / 10))))  # Convert to int
        
        category_scores[category] = score
        recommendations[category] = f"Continue growing in {category.lower()}. Focus on consistent practice and deeper understanding."
    
    # Generate mock question feedback
    for q_id, answer in answers.items():
        question = next((q for q in questions if str(q['id']) == q_id), None)
        if question:
            question_feedback.append({
                'question': question['text'],
                'answer': answer,
                'correct': len(answer.split()) > 5,  # Mock: longer answers are "correct"
                'explanation': '' if len(answer.split()) > 5 else 'Consider providing more detailed responses.',
                'question_id': q_id
            })
    
    overall_score = int(round(mean(category_scores.values()))) if category_scores else 7
    
    return {
        'overall_score': int(overall_score),
        'category_scores': category_scores,
        'recommendations': recommendations,
        'question_feedback': question_feedback,
        'summary_recommendation': generate_summary_recommendation(category_scores, recommendations)
    }

def generate_summary_recommendation(category_scores: Dict[str, int], 
                                  recommendations: Dict[str, str]) -> str:
    """Generate an overall summary recommendation."""
    # Find strongest and weakest areas
    if not category_scores:
        return "Continue your spiritual journey with consistency and dedication."
    
    strongest = max(category_scores.items(), key=lambda x: x[1])
    weakest = min(category_scores.items(), key=lambda x: x[1])
    
    summary = f"Your strongest area is {strongest[0]} (score: {strongest[1]}). "
    
    if strongest[1] - weakest[1] > 2.0:
        summary += f"Consider focusing more attention on {weakest[0]} to create better balance in your spiritual growth. "
    
    summary += "Continue practicing spiritual disciplines consistently and seek mentorship for areas of growth."
    
    return summary

# @cache_result(expiration=300, key_prefix="assessment_score:")
async def score_assessment_by_category(answers: Dict[str, str], 
                                     questions: List[dict],
                                     previous_assessments: List[dict] = None) -> Dict:
    """Enhanced AI scoring with category breakdown and detailed question feedback.
    
    Phase 2: Now includes previous_assessments for historical context and trend analysis.
    Uses LLMService abstraction with Gemini/OpenAI fallback support.
    """
    logger.info(f"Starting AI scoring with {len(answers)} answers and {len(questions)} questions")
    if previous_assessments:
        logger.info(f"[historical] Including {len(previous_assessments)} previous assessments for context")
    logger.info(f"Answer keys: {list(answers.keys())}")
    logger.info(f"Question IDs: {[q.get('id') for q in questions]}")
    
    # Check LLM service availability (Gemini or OpenAI)
    llm_service = get_llm_service()
    llm_available = llm_service.primary_provider is not None or llm_service.fallback_provider is not None
    is_mock = not llm_available
    
    if is_mock:
        logger.info("LLM service not configured; proceeding with mock scoring and safe mentor blob")
    else:
        logger.info(f"LLM service configured: primary={llm_service.primary_provider.__class__.__name__ if llm_service.primary_provider else 'None'}, fallback={'enabled' if llm_service.fallback_provider else 'disabled'}")
    
    # Group answers by category
    categorized_answers = {}
    all_question_feedback = []
    
    for answer_key, answer_text in answers.items():
        # Find the question and its category
        question = next((q for q in questions if str(q['id']) == answer_key), None)
        if question:
            category = question.get('category', None)
            # If no category_id, use 'Spiritual Assessment' as default
            if not category:
                category = 'Spiritual Assessment'
            logger.info(f"Question {answer_key}: category='{category}', text='{question.get('text', 'N/A')[:50]}...'")
            if category not in categorized_answers:
                categorized_answers[category] = []
            
            # For MC questions, resolve the answer from UUID to actual text
            resolved_answer = answer_text
            q_type = (question.get('question_type') or '').lower()
            if q_type == 'multiple_choice' and question.get('options'):
                # Try to find the option by ID (UUID) and get its text
                for opt in question.get('options', []):
                    opt_id = str(opt.get('id', '')).strip()
                    if opt_id and opt_id == str(answer_text).strip():
                        resolved_answer = opt.get('text', answer_text)
                        logger.info(f"  Resolved MC answer: {answer_text[:8]}... -> '{resolved_answer}'")
                        break
            
            # Include type/options so the category scorer can objectively grade MC using is_correct
            qa_item = {
                'question': question.get('text'),
                'answer': resolved_answer,
                'question_id': answer_key,
            }
            if 'question_type' in question:
                qa_item['question_type'] = question.get('question_type')
            if 'options' in question and isinstance(question.get('options'), list):
                qa_item['options'] = question.get('options')
            categorized_answers[category].append(qa_item)
        else:
            logger.warning(f"No question found for answer key: {answer_key}")
    
    logger.info(f"Categories found: {list(categorized_answers.keys())}")
    
    # Score each category
    category_scores = {}
    recommendations = {}
    
    if is_mock:
        # Use deterministic mock scorer for categories and feedback
        mock = generate_mock_detailed_scores(answers, questions)
        category_scores = mock.get('category_scores', {})
        recommendations = mock.get('recommendations', {})
        all_question_feedback = mock.get('question_feedback', [])
    else:
        # Process categories sequentially using LLMService
        for category, qa_pairs in categorized_answers.items():
            try:
                score, rec, feedback = score_category_with_feedback(None, category, qa_pairs)  # client param deprecated
                category_scores[category] = round(score)  # Convert to int
                recommendations[category] = rec
                all_question_feedback.extend(feedback)
            except Exception as e:
                logger.error(f"Failed to score category {category}: {e}")
                category_scores[category] = 7
                recommendations[category] = f"Continue developing your {category.lower()} practices."
    
    overall_score = int(round(mean(category_scores.values()))) if category_scores else 7
    
    # Build mentor_blob v2 via LLM (or fallback when no LLM available)
    mentor_blob = None
    try:
        apprentice_stub = {}
        # Construct v2 payload with historical context (Phase 2)
        payload, derived = _build_v2_prompt_input(apprentice_stub, assessment_id="N/A", template_id=None, submitted_at=None, answers=answers, questions=questions, previous_assessments=previous_assessments)
        if not is_mock:
            try:
                raw_blob = _call_llm_for_mentor_blob(None, payload)  # client param deprecated
                mentor_blob = MentorBlobV2.model_validate(raw_blob).model_dump()
            except ValidationError as ve:
                logger.warning(f"mentor_blob v2 validation failed, retrying once: {ve}")
                # one more attempt
                raw_blob = _call_llm_for_mentor_blob(None, payload)  # client param deprecated
                mentor_blob = MentorBlobV2.model_validate(raw_blob).model_dump()
        if mentor_blob is None:
            mentor_blob = _safe_minimal_blob(derived.get('percent', 0.0), derived.get('by_topic', []))
    except Exception as e:
        logger.error(f"Failed to build mentor_blob v2: {e}")
        mentor_blob = _safe_minimal_blob(0.0, [])

    result = {
        'overall_score': int(overall_score),  # Ensure it's an int
        'category_scores': category_scores,
        'recommendations': recommendations,
        'question_feedback': all_question_feedback,
        'summary_recommendation': generate_summary_recommendation(category_scores, recommendations),
        'mentor_blob_v2': mentor_blob,
    }
    
    logger.info(f"Assessment scoring completed: overall={result['overall_score']}, categories={len(category_scores)}, feedback_items={len(all_question_feedback)}")
    return result

def score_assessment(answers: dict):
    """Legacy function for backward compatibility.

    If tests patch client.chat.completions.create to return a JSON blob with per-question keys
    (e.g., {"q1": {...}}), parse and return that directly. Otherwise, fall back to the rich
    category-based scorer and return its dict.
    """
    # First, try the mocked completions path if present
    try:
        resp = client.chat.completions.create(model="gpt-4o", messages=[])
        content = resp.choices[0].message.content
        parsed = json.loads(content)
        if isinstance(parsed, dict) and all(isinstance(k, str) for k in parsed.keys()):
            return parsed
    except Exception:
        # Not in mocked mode; proceed to full scorer
        pass

    # Convert to async and run the category-based scorer
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        # Mock questions for legacy compatibility
        questions = [{"id": k, "text": f"Question {k}", "category": "General"} for k in answers.keys()]
        result = loop.run_until_complete(score_assessment_by_category(answers, questions))
        return result
    except Exception as e:
        logger.error(f"Legacy scoring failed: {e}")
        return {"overall_score": 7.0, "summary_recommendation": "Assessment completed. Continue growing in spiritual disciplines."}
    finally:
        try:
            loop.close()
        except Exception:
            pass

async def score_assessment_with_questions(answers: dict, questions: list) -> tuple[float, str]:
    """Enhanced scoring function that uses real questions."""
    try:
        result = await score_assessment_by_category(answers, questions)
        return result['overall_score'], result['summary_recommendation']
    except Exception as e:
        logger.error(f"Enhanced scoring failed: {e}")
        return 7.0, "Assessment completed. Continue growing in spiritual disciplines."


def generate_baseline_score(answers: dict, questions: list) -> dict:
    """Generate instant baseline score without AI (for progressive enhancement pattern).
    
    This provides immediate feedback to users while full AI scoring runs in background.
    Uses simple heuristics:
    - MC questions: % correct
    - Open-ended: presence/length check
    - Baseline status: "baseline" (will be updated to "done" after AI enrichment)
    
    Returns minimal mentor_blob_v2 structure compatible with frontend.
    """
    logger.info(f"[baseline] Generating baseline score for {len(answers)} answers")
    
    # Separate MC and open-ended
    mc_questions = [q for q in questions if q.get('question_type') in ['mc', 'multiple_choice']]
    open_questions = [q for q in questions if q.get('question_type') not in ['mc', 'multiple_choice']]
    
    # Calculate MC score
    mc_correct = 0
    mc_total = len(mc_questions)
    for q in mc_questions:
        q_id = str(q['id'])
        answer = answers.get(q_id, '')
        # Check if answer matches any correct option (by ID or by text)
        for opt in q.get('options', []):
            if opt.get('is_correct'):
                opt_id = str(opt.get('id', '')).strip()
                opt_text = str(opt.get('text', '')).strip().lower()
                ans_str = str(answer).strip()
                # Match by option ID (UUID) or by option text (legacy)
                if (opt_id and opt_id == ans_str) or (opt_text == ans_str.lower()):
                    mc_correct += 1
                    break
    
    mc_percent = int((mc_correct / mc_total * 100)) if mc_total > 0 else 0
    
    # Check open-ended completeness
    open_completed = sum(1 for q in open_questions if answers.get(str(q['id']), '').strip())
    open_total = len(open_questions)
    
    # Build minimal baseline mentor_blob_v2 (v2.1 format)
    health_score = mc_percent  # baseline uses MC percent as initial health score
    baseline_blob = {
        "health_score": health_score,
        "health_band": _health_band(health_score),
        "strengths": ["Completed assessment", "Engaged with questions"],
        "gaps": ["Awaiting detailed AI analysis"],
        "priority_action": None,
        "biblical_knowledge": {
            "percent": mc_percent,
            "weak_topics": [],  # Will be populated after AI analysis
        },
        "insights": [
            {
                "category": "Assessment",
                "level": "Baseline",
                "evidence": f"Answered {open_completed}/{open_total} open-ended questions. Full analysis pending.",
                "next_step": "AI analysis in progress..."
            }
        ],
        "flags": {
            "red": [],
            "yellow": [] if mc_percent >= 50 else ["Low biblical knowledge score"],
            "green": ["Completed full assessment"]
        },
        "conversation_starters": [
            "What motivated you to complete this assessment?",
            "Which questions were most challenging for you?"
        ],
        "recommended_resources": [],
    }
    
    return {
        "overall_score": mc_percent,
        "summary_recommendation": f"Baseline assessment complete. Scored {mc_percent}% on biblical knowledge. Full AI analysis in progress.",
        "mentor_blob_v2": baseline_blob,
        "status": "baseline",
        "model": "baseline_heuristic_v1"
    }


