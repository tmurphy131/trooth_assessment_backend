#!/usr/bin/env python3
"""Generate trivia questions using the app's existing Gemini/Vertex AI integration.

Uses the same GeminiProvider that powers assessment reports — no API key needed.
Authentication is via Application Default Credentials (ADC):
  - Locally: run `gcloud auth application-default login` once
  - On Cloud Run: uses the service account automatically

Usage:
    python scripts/generate_trivia_questions.py \
        --category old_testament \
        --difficulty beginner \
        --count 50

    # Generate all 12 buckets in one pass
    python scripts/generate_trivia_questions.py --all --count 84

Output: questions_draft_{category}_{difficulty}.json in --output-dir (default: current dir)
Set "approved": true on the questions you want to keep, then run import_trivia_questions.py.
"""

import argparse
import json
import random
import sys
import time
from pathlib import Path

# Allow running from repo root without installing the package
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv()

CATEGORIES = ["old_testament", "new_testament", "theology_doctrine", "discipleship_living"]
DIFFICULTIES = ["beginner", "challenger", "expert"]

DIFFICULTY_GUIDANCE = {
    "beginner": (
        "Well-known Bible facts, core stories, major figures, and central teachings. "
        "The correct answer should be clear to anyone who has attended church regularly, "
        "but wrong options must still be plausible — no obviously absurd distractors."
    ),
    "challenger": (
        "Less common details: secondary characters, specific numerical facts (days, ages, counts), "
        "the names of lesser-known places or people, and questions that require knowing more than "
        "just the main storyline. A casual reader may guess; a regular Bible student should know. "
        "WRONG ANSWER CRAFT: Wrong options must be genuinely deceptive — use real Bible names, "
        "places, or numbers that are close but incorrect (e.g. a different disciple's name, the "
        "adjacent chapter, a number off by one). Someone who half-knows the story should be "
        "tempted by at least two options. Never use obviously wrong names or made-up details."
    ),
    "expert": (
        "Obscure details, cross-referencing multiple books, nuanced theological distinctions, "
        "specific chapter/verse context, uncommon proper nouns, and questions that would stump "
        "even an experienced churchgoer without focused study. "
        "WRONG ANSWER CRAFT: Wrong options must be nearly indistinguishable from the correct "
        "answer to anyone without precise knowledge — use the actual names, terms, or numbers "
        "from related passages that are commonly confused with the answer (e.g. the right event "
        "but wrong book, the right person but wrong role, a real theological term with a subtly "
        "different meaning). At least two wrong options should be plausible enough to fool a "
        "seminary student on a bad day. Avoid any option a player could eliminate by basic "
        "process of elimination."
    ),
}

CATEGORY_GUIDANCE = {
    "old_testament": "Questions drawn exclusively from Genesis through Malachi.",
    "new_testament": "Questions drawn exclusively from Matthew through Revelation.",
    "theology_doctrine": (
        "Christian theology and doctrine: the Trinity, soteriology (salvation, justification, "
        "sanctification), ecclesiology, eschatology, the nature of Scripture, key creeds and "
        "confessions, and major theological figures (Augustine, Luther, Calvin, Barth, etc.)."
    ),
    "discipleship_living": (
        "Practical Christian living: spiritual disciplines (prayer, fasting, Scripture reading, "
        "giving, service), the fruit of the Spirit, Christian ethics, discipleship relationships, "
        "evangelism, and applying faith to everyday decisions."
    ),
}

SYSTEM_PROMPT = (
    "You are generating trivia questions for a Christian discipleship mobile app. "
    "Return ONLY a valid JSON array — no markdown, no explanation, no extra text."
)

USER_PROMPT_TEMPLATE = """Category: {category_label}
{category_guidance}

Difficulty: {difficulty}
{difficulty_guidance}

Rules:
- Wrong options must be plausible — no obviously absurd distractors.
- True/False questions: exactly two options, a = "True", b = "False", option_c and option_d must be null.
- Multiple choice questions: exactly four non-null options (a, b, c, d).
- Aim for roughly 85% multiple choice and 15% true/false.
- Answers must require actual knowledge — not googleable in under 5 seconds.
- Do not repeat questions.

Return exactly {count} questions as a JSON array with this structure:
[
  {{
    "question": "...",
    "options": {{"a": "...", "b": "...", "c": "..." or null, "d": "..." or null}},
    "correct": "a" | "b" | "c" | "d",
    "type": "multiple_choice" | "true_false",
    "difficulty": "{difficulty}",
    "category": "{category}",
    "approved": false
  }}
]"""


def build_prompt(category: str, difficulty: str, count: int) -> str:
    return USER_PROMPT_TEMPLATE.format(
        category=category,
        category_label=category.replace("_", " ").title(),
        category_guidance=CATEGORY_GUIDANCE[category],
        difficulty=difficulty,
        difficulty_guidance=DIFFICULTY_GUIDANCE[difficulty],
        count=count,
    )


def call_gemini(category: str, difficulty: str, count: int) -> list[dict]:
    from app.services.llm.gemini_provider import GeminiProvider
    from app.services.llm.base import LLMConfig

    provider = GeminiProvider(model="gemini-2.5-flash")
    config = LLMConfig(
        temperature=0.9,
        max_tokens=65536,  # gemini-2.5-flash max output tokens
        json_mode=True,
    )

    print(f"  Calling Gemini (gemini-2.5-flash via Vertex AI)...")
    response = provider.generate(
        system_prompt=SYSTEM_PROMPT,
        user_content=build_prompt(category, difficulty, count),
        config=config,
    )

    if not response.success:
        raise RuntimeError(f"Gemini call failed: {response.error}\nRaw: {response.raw_response[:500]}")

    # The provider returns raw_response as a string; parse it
    raw = response.raw_response.strip()
    if raw.startswith("```"):
        lines = raw.splitlines()
        raw = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

    questions = json.loads(raw)
    if not isinstance(questions, list):
        raise ValueError(f"Expected a JSON array, got {type(questions)}")
    return questions


def shuffle_options(q: dict) -> dict:
    """Randomly redistribute answer options so the correct answer isn't always 'a'."""
    opts = q.get("options", {})
    correct_key = q.get("correct")
    if not correct_key or correct_key not in opts:
        return q

    # Collect only non-null options
    filled = [(k, v) for k, v in opts.items() if v]
    if len(filled) < 2:
        return q

    correct_value = opts[correct_key]
    slot_keys = [k for k, _ in filled]

    # Shuffle the values into the same slots
    values = [v for _, v in filled]
    random.shuffle(values)
    new_opts = dict(zip(slot_keys, values))

    # Pad back any null slots (c/d for true_false)
    for k in opts:
        if k not in new_opts:
            new_opts[k] = None

    # Find which key now holds the correct value
    new_correct = next(k for k, v in new_opts.items() if v == correct_value)

    return {**q, "options": new_opts, "correct": new_correct}


def validate_question(q: dict, idx: int) -> list[str]:
    errors = []
    if not q.get("question"):
        errors.append(f"[{idx}] Missing 'question'")
    opts = q.get("options", {})
    if not isinstance(opts, dict) or not opts.get("a") or not opts.get("b"):
        errors.append(f"[{idx}] options.a and options.b are required")
    elif q.get("type") == "multiple_choice" and (not opts.get("c") or not opts.get("d")):
        errors.append(f"[{idx}] Multiple choice must have all four options")
    if q.get("correct") not in ("a", "b", "c", "d"):
        errors.append(f"[{idx}] 'correct' must be a/b/c/d")
    if q.get("type") not in ("multiple_choice", "true_false"):
        errors.append(f"[{idx}] 'type' must be multiple_choice or true_false")
    return errors


def generate_bucket(category: str, difficulty: str, count: int, output_dir: Path) -> Path:
    output_file = output_dir / f"questions_draft_{category}_{difficulty}.json"

    existing = []
    if output_file.exists():
        try:
            existing = json.loads(output_file.read_text())
            print(f"  Found existing draft with {len(existing)} questions — appending")
        except Exception:
            pass

    questions = [shuffle_options(q) for q in call_gemini(category, difficulty, count)]

    all_errors = []
    for i, q in enumerate(questions):
        all_errors.extend(validate_question(q, i))

    if all_errors:
        print(f"  WARNING: {len(all_errors)} validation issue(s):")
        for e in all_errors[:10]:
            print(f"    {e}")
        if len(all_errors) > 10:
            print(f"    ...and {len(all_errors) - 10} more")

    combined = existing + questions
    output_file.write_text(json.dumps(combined, indent=2, ensure_ascii=False))
    print(f"  Wrote {len(questions)} questions → {output_file} ({len(combined)} total)")
    return output_file


def main():
    parser = argparse.ArgumentParser(description="Generate trivia questions via Gemini/Vertex AI")
    parser.add_argument("--category", choices=CATEGORIES, help="Single category to generate")
    parser.add_argument("--difficulty", choices=DIFFICULTIES, help="Single difficulty level")
    parser.add_argument("--count", type=int, default=50, help="Number of questions (default: 50)")
    parser.add_argument("--all", action="store_true", help="Generate all 12 buckets")
    parser.add_argument("--output-dir", default=".", help="Directory for draft JSON files")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.all:
        buckets = [(c, d) for c in CATEGORIES for d in DIFFICULTIES]
        print(f"Generating {len(buckets)} buckets × {args.count} questions each\n")
        for category, difficulty in buckets:
            print(f"[{category} / {difficulty}]")
            try:
                generate_bucket(category, difficulty, args.count, output_dir)
            except Exception as e:
                print(f"  ERROR: {e}")
            time.sleep(1)
    elif args.category and args.difficulty:
        print(f"[{args.category} / {args.difficulty}]")
        generate_bucket(args.category, args.difficulty, args.count, output_dir)
    else:
        parser.error("Provide --category and --difficulty, or use --all")


if __name__ == "__main__":
    main()
