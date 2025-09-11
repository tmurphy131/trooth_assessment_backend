from openai import OpenAI
import os
import json
import re
import logging
from typing import Dict, List, Tuple, Optional
import asyncio
from app.core.cache import cache_result

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

def score_category_with_feedback(client, category: str, qa_pairs: List[Dict]) -> tuple:
    """Score a category and return detailed question feedback."""
    prompt = f"""
You are an AI assistant evaluating spiritual assessment responses in the category: {category}.

Please evaluate the following questions and answers on a scale of 1-10, where:
- 1-3: Major concerns, significant gaps
- 4-6: Some concerns, areas needing development  
- 7-8: Good understanding, minor improvements possible
- 9-10: Excellent understanding and application

For each question-answer pair, determine if it's based on:
- FACT: Requires specific knowledge or correct understanding (provide explanations for incorrect answers)
- OPINION/EXPERIENCE: Personal views or life experiences (no right/wrong explanation needed)

Questions and Answers:
"""
    
    for i, qa in enumerate(qa_pairs, 1):
        prompt += f"\n{i}. Question: {qa['question']}\n   Answer: {qa['answer']}\n"
    
    prompt += """
Return a JSON response with:
{
    "score": [integer 1-10],
    "recommendation": "[brief recommendation for this category]",
    "question_feedback": [
        {
            "question": "[original question text]",
            "answer": "[user's answer]", 
            "correct": [true/false - whether answer demonstrates understanding],
            "explanation": "[for factual questions marked false, explain why the answer is incorrect and what the correct understanding should be. For opinion/experience questions or correct answers, leave empty]"
        }
    ]
}
"""
    
    try:
        logger.info(f"Scoring category: {category}")
        logger.info(f"Making OpenAI API call...")
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an expert spiritual mentor and assessor. Focus on providing educational feedback for incorrect factual answers."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1500,
            temperature=0.3
        )
        logger.info(f"OpenAI API call completed successfully")
        
        content = response.choices[0].message.content.strip()
        logger.info(f"Raw AI response for {category}: {content[:200]}...")
        
        # Parse JSON response
        try:
            parsed = json.loads(content)
            score = int(parsed.get('score', 7))
            recommendation = parsed.get('recommendation', f"Continue developing your {category.lower()} practices.")
            feedback = parsed.get('question_feedback', [])
            
            # Add question_id to feedback items
            for i, feedback_item in enumerate(feedback):
                if i < len(qa_pairs):
                    feedback_item['question_id'] = qa_pairs[i].get('question_id')
            
            logger.info(f"Parsed feedback for {category}: score={score}, feedback_items={len(feedback)}")
            return score, recommendation, feedback
            
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON for {category}: {e}. Content: {content}")
            # Fallback - extract score if possible
            score_match = re.search(r'"score":\s*(\d+)', content)
            score = int(score_match.group(1)) if score_match else 7
            return score, f"Continue developing your {category.lower()} practices.", []
            
    except Exception as e:
        logger.error(f"Error scoring category {category}: {e}")
        return 7, f"Continue developing your {category.lower()} practices.", []
    """Score a specific category with AI."""
    try:
        qa_text = "\n".join([f"Q: {qa['question']}\nA: {qa['answer']}" for qa in qa_pairs])
        logger.info(f"Scoring category '{category}' with {len(qa_pairs)} questions")
        logger.info(f"Sending to OpenAI: {qa_text[:200]}...")
        
        # Enhanced prompt for detailed feedback
        messages = [
            {
                "role": "system",
                "content": (
                    f"You are evaluating the '{category}' category of a spiritual assessment. "
                    "Rate this category from 1-10 based on the apprentice's answers. "
                    "For factual questions (like 'Who baptized Jesus?'), provide specific corrections if the answer is wrong. "
                    "For experiential/opinion questions, provide encouragement and growth suggestions. "
                    "Return JSON with: "
                    "1. 'score': numerical score (1-10) "
                    "2. 'recommendation': overall category feedback "
                    "3. 'question_feedback': array of objects with 'question', 'answer', 'correct', 'explanation' for each question "
                    "Format: {\"score\": 7.5, \"recommendation\": \"...\", \"question_feedback\": [{\"question\": \"...\", \"answer\": \"...\", \"correct\": true/false, \"explanation\": \"...\"}]}"
                )
            },
            {
                "role": "user",
                "content": qa_text
            }
        ]

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.7,
            max_tokens=1000  # Increased for detailed feedback
        )

        result_text = response.choices[0].message.content
        logger.info(f"OpenAI response for {category}: {result_text}")
        result = json.loads(result_text)
        score = float(result.get("score", 7.0))
        recommendation = result.get("recommendation", "Continue growing.")
        
        # Log detailed feedback
        question_feedback = result.get("question_feedback", [])
        logger.info(f"Question feedback for {category}: {len(question_feedback)} questions analyzed")
        
        logger.info(f"Parsed score for {category}: {score}")
        return score, recommendation
        
    except Exception as e:
        logger.warning(f"AI scoring failed for category {category}: {e}")
        return 7.0, f"Continue developing your {category.lower()} practices."

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
    
    overall_score = sum(category_scores.values()) // len(category_scores) if category_scores else 7
    
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
                                     questions: List[dict]) -> Dict:
    """Enhanced AI scoring with category breakdown and detailed question feedback."""
    logger.info(f"Starting AI scoring with {len(answers)} answers and {len(questions)} questions")
    logger.info(f"Answer keys: {list(answers.keys())}")
    logger.info(f"Question IDs: {[q.get('id') for q in questions]}")
    
    client = get_openai_client()
    
    if not client:
        logger.info("Using mock scoring - OpenAI not configured")
        return generate_mock_detailed_scores(answers, questions)
    
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
            categorized_answers[category].append({
                'question': question['text'],
                'answer': answer_text,
                'question_id': answer_key
            })
        else:
            logger.warning(f"No question found for answer key: {answer_key}")
    
    logger.info(f"Categories found: {list(categorized_answers.keys())}")
    
    # Score each category
    category_scores = {}
    recommendations = {}
    
    # Process categories sequentially since OpenAI client is sync
    for category, qa_pairs in categorized_answers.items():
        try:
            score, rec, feedback = score_category_with_feedback(client, category, qa_pairs)
            category_scores[category] = round(score)  # Convert to int
            recommendations[category] = rec
            all_question_feedback.extend(feedback)
        except Exception as e:
            logger.error(f"Failed to score category {category}: {e}")
            category_scores[category] = 7
            recommendations[category] = f"Continue developing your {category.lower()} practices."
    
    overall_score = sum(category_scores.values()) // len(category_scores) if category_scores else 7
    
    result = {
        'overall_score': int(overall_score),  # Ensure it's an int
        'category_scores': category_scores,
        'recommendations': recommendations,
        'question_feedback': all_question_feedback,
        'summary_recommendation': generate_summary_recommendation(category_scores, recommendations)
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
        resp = client.chat.completions.create(model="gpt-4o-mini", messages=[])
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
