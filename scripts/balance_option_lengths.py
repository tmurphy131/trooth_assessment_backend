#!/usr/bin/env python3
"""Rebalance trivia question options where the correct answer is significantly
longer than the distractors — a known LLM generation bias that makes the
correct answer guessable by length alone.

For each flagged question, rewrites the WRONG options to be similar in
length and style to the correct answer. The correct answer and all other
question fields are left untouched.

Usage:
    # Dry run — show what would be changed, don't write files
    python scripts/balance_option_lengths.py --dry-run

    # Fix all flagged questions across all 12 draft files
    python scripts/balance_option_lengths.py

    # Fix a single file only
    python scripts/balance_option_lengths.py --file questions_draft_old_testament_beginner.json

    # Adjust sensitivity (default: correct must be 30% longer than avg distractor)
    python scripts/balance_option_lengths.py --ratio 1.5
"""

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv
load_dotenv()

DRAFTS_DIR = Path(__file__).parent / "question_drafts"
BATCH_SIZE = 10  # questions per Gemini call

SYSTEM_PROMPT = (
    "You are editing Bible trivia questions. "
    "Return ONLY a valid JSON array — no markdown, no explanation, no extra text."
)

USER_PROMPT_TEMPLATE = """The following Bible trivia questions have a problem: the CORRECT answer is much longer than the wrong options, making it guessable by length alone.

For each question, rewrite ONLY the wrong options so that:
1. All options are similar in length and style to the correct answer
2. Every wrong option is plausible — a player who doesn't know the answer should be tempted
3. Wrong options use real Bible names, places, concepts, or numbers (never obviously made-up)
4. Do NOT change the correct answer text — copy it exactly as given
5. Do NOT change the question text or which key (a/b/c/d) is correct

Return a JSON array with one object per question in the same order:
[
  {{
    "index": <index as given>,
    "options": {{"a": "...", "b": "...", "c": "...", "d": "..."}}
  }}
]

For true/false questions (only options a and b), set c and d to null.

Questions to fix:
{questions_json}"""


def is_length_biased(q: dict, ratio_threshold: float) -> bool:
    """Return True if the correct answer is significantly longer than avg distractor."""
    if q.get("type") == "true_false":
        return False  # True/False can't be length-guessed
    opts = {k: v for k, v in q.get("options", {}).items() if v}
    correct = q.get("correct", "")
    if correct not in opts or len(opts) < 3:
        return False
    correct_len = len(opts[correct])
    others = [len(v) for k, v in opts.items() if k != correct]
    avg_other = sum(others) / len(others)
    return avg_other > 0 and (correct_len / avg_other) >= ratio_threshold


def call_gemini_batch(batch: list[dict]) -> list[dict]:
    """Send a batch of flagged questions to Gemini and return updated options."""
    from app.services.llm.gemini_provider import GeminiProvider
    from app.services.llm.base import LLMConfig

    payload = [
        {
            "index": item["index"],
            "question": item["q"]["question"],
            "correct_key": item["q"]["correct"],
            "correct_answer": item["q"]["options"][item["q"]["correct"]],
            "current_options": item["q"]["options"],
        }
        for item in batch
    ]

    provider = GeminiProvider(model="gemini-2.5-flash")
    config = LLMConfig(temperature=0.7, max_tokens=8192, json_mode=True)

    response = provider.generate(
        system_prompt=SYSTEM_PROMPT,
        user_content=USER_PROMPT_TEMPLATE.format(
            questions_json=json.dumps(payload, indent=2, ensure_ascii=False)
        ),
        config=config,
    )

    if not response.success:
        raise RuntimeError(f"Gemini call failed: {response.error}")

    raw = response.raw_response.strip()
    if raw.startswith("```"):
        lines = raw.splitlines()
        raw = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

    return json.loads(raw)


def process_file(fname: str, ratio_threshold: float, dry_run: bool) -> dict:
    path = DRAFTS_DIR / fname
    questions = json.loads(path.read_text())

    # Find approved, length-biased questions
    flagged = [
        {"index": i, "q": q}
        for i, q in enumerate(questions)
        if q.get("approved") and is_length_biased(q, ratio_threshold)
    ]

    if not flagged:
        return {"file": fname, "flagged": 0, "fixed": 0}

    print(f"\n  {fname}: {len(flagged)} flagged")

    if dry_run:
        for item in flagged[:3]:
            q = item["q"]
            correct = q["correct"]
            opts = q["options"]
            print(f"    [{item['index']}] {q['question'][:70]}")
            for k, v in opts.items():
                if v:
                    marker = " <-- correct" if k == correct else ""
                    print(f"      {k} [{len(v):3d}]: {v[:60]}{marker}")
        if len(flagged) > 3:
            print(f"    ... and {len(flagged) - 3} more")
        return {"file": fname, "flagged": len(flagged), "fixed": 0}

    # Process in batches
    fixed = 0
    for batch_start in range(0, len(flagged), BATCH_SIZE):
        batch = flagged[batch_start: batch_start + BATCH_SIZE]
        print(f"    Batch {batch_start // BATCH_SIZE + 1}: {len(batch)} questions → Gemini...", end=" ", flush=True)

        try:
            results = call_gemini_batch(batch)
        except Exception as e:
            print(f"FAILED ({e})")
            continue

        # Apply updates
        for result in results:
            idx = result.get("index")
            new_opts = result.get("options", {})
            if idx is None or not new_opts:
                continue

            original_q = questions[idx]
            correct_key = original_q["correct"]
            correct_val = original_q["options"][correct_key]

            # Safety: ensure the correct answer wasn't changed
            if new_opts.get(correct_key) != correct_val:
                new_opts[correct_key] = correct_val  # force it back

            # Preserve nulls for true/false
            for k in ["a", "b", "c", "d"]:
                if k not in new_opts:
                    new_opts[k] = original_q["options"].get(k)

            questions[idx]["options"] = new_opts
            fixed += 1

        print(f"done ({len(results)} updated)")
        time.sleep(0.5)  # brief pause between batches

    # Write back
    path.write_text(json.dumps(questions, indent=2, ensure_ascii=False))
    return {"file": fname, "flagged": len(flagged), "fixed": fixed}


def main():
    parser = argparse.ArgumentParser(description="Balance trivia option lengths using Gemini")
    parser.add_argument("--dry-run", action="store_true", help="Show what would change without writing")
    parser.add_argument("--file", help="Process only this filename (e.g. questions_draft_old_testament_beginner.json)")
    parser.add_argument("--ratio", type=float, default=1.3, help="Flag when correct is this many times longer than avg distractor (default: 1.3)")
    args = parser.parse_args()

    if args.dry_run:
        print("=== DRY RUN — no files will be written ===")

    # First pass: show counts
    files = (
        [args.file] if args.file
        else [f.name for f in sorted(DRAFTS_DIR.glob("questions_draft_*.json"))]
    )

    print(f"\nScanning {len(files)} file(s) with ratio threshold {args.ratio}x...\n")

    total_flagged = 0
    total_fixed = 0
    for fname in files:
        if not (DRAFTS_DIR / fname).exists():
            print(f"  ERROR: {fname} not found")
            continue
        result = process_file(fname, args.ratio, args.dry_run)
        total_flagged += result["flagged"]
        total_fixed += result["fixed"]

    print(f"\n=== Summary ===")
    print(f"  Questions flagged: {total_flagged}")
    if not args.dry_run:
        print(f"  Questions fixed:   {total_fixed}")
    else:
        print("  (dry run — run without --dry-run to apply fixes)")


if __name__ == "__main__":
    main()
