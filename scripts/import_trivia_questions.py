#!/usr/bin/env python3
"""Import approved trivia questions from a draft JSON file into the database.

Usage:
    python scripts/import_trivia_questions.py --file questions_draft_old_testament_beginner.json

    # Import all draft files in the current directory
    python scripts/import_trivia_questions.py --file questions_draft_*.json

    # Dry run — show what would be inserted without touching the DB
    python scripts/import_trivia_questions.py --file questions_draft_old_testament_beginner.json --dry-run

Only questions with "approved": true are imported. Questions already present in the
database (matched by question_text) are skipped to avoid duplicates.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv()


VALID_CATEGORIES = {"old_testament", "new_testament", "theology_doctrine", "discipleship_living", "random"}
VALID_DIFFICULTIES = {"beginner", "challenger", "expert"}
VALID_CORRECT_OPTIONS = {"a", "b", "c", "d"}
VALID_TYPES = {"multiple_choice", "true_false"}


def load_questions(file_path: Path) -> list[dict]:
    data = json.loads(file_path.read_text())
    if not isinstance(data, list):
        raise ValueError(f"{file_path}: expected a JSON array at top level")
    return data


def validate_for_import(q: dict, idx: int, file_name: str) -> list[str]:
    errors = []
    prefix = f"{file_name}[{idx}]"
    if not q.get("question"):
        errors.append(f"{prefix} Missing 'question'")
    opts = q.get("options", {})
    if not opts.get("a") or not opts.get("b"):
        errors.append(f"{prefix} options.a and options.b are required")
    if q.get("correct") not in VALID_CORRECT_OPTIONS:
        errors.append(f"{prefix} 'correct' must be a/b/c/d")
    if q.get("type") not in VALID_TYPES:
        errors.append(f"{prefix} 'type' must be multiple_choice or true_false")
    if q.get("category") not in VALID_CATEGORIES:
        errors.append(f"{prefix} unknown category: {q.get('category')!r}")
    if q.get("difficulty") not in VALID_DIFFICULTIES:
        errors.append(f"{prefix} unknown difficulty: {q.get('difficulty')!r}")
    return errors


def import_file(file_path: Path, db, dry_run: bool) -> dict:
    from app.models.trivia import TriviaQuestion, TriviaCategory, TriviaDifficulty, TriviaCorrectOption, TriviaQuestionType
    from app.models.device_token import DeviceToken  # noqa: F401 — needed so SQLAlchemy can resolve User.device_tokens relationship

    questions = load_questions(file_path)
    approved = [q for q in questions if q.get("approved") is True]
    skipped_not_approved = len(questions) - len(approved)

    all_errors = []
    valid = []
    for i, q in enumerate(approved):
        errs = validate_for_import(q, i, file_path.name)
        if errs:
            all_errors.extend(errs)
        else:
            valid.append(q)

    if all_errors:
        print(f"  {len(all_errors)} validation error(s) in {file_path.name}:")
        for e in all_errors[:20]:
            print(f"    {e}")
        if len(all_errors) > 20:
            print(f"    ...and {len(all_errors) - 20} more")
        print("  Skipping file due to validation errors. Fix them and re-run.")
        return {"file": file_path.name, "imported": 0, "skipped": 0, "errors": len(all_errors)}

    # Deduplicate against existing DB rows
    existing_texts = set()
    if not dry_run:
        rows = db.query(TriviaQuestion.question_text).all()
        existing_texts = {r[0] for r in rows}

    to_insert = []
    duplicates = 0
    for q in valid:
        if q["question"] in existing_texts:
            duplicates += 1
            continue
        to_insert.append(q)
        existing_texts.add(q["question"])  # avoid duplicate within this batch

    if dry_run:
        print(f"  [DRY RUN] {file_path.name}: {len(to_insert)} would be inserted "
              f"({skipped_not_approved} not approved, {duplicates} duplicates skipped)")
        return {"file": file_path.name, "would_import": len(to_insert), "errors": 0}

    inserted = 0
    for q in to_insert:
        opts = q.get("options", {})
        row = TriviaQuestion(
            category=TriviaCategory(q["category"]),
            difficulty=TriviaDifficulty(q["difficulty"]),
            question_text=q["question"],
            option_a=opts.get("a", ""),
            option_b=opts.get("b", ""),
            option_c=opts.get("c") or None,
            option_d=opts.get("d") or None,
            correct_option=TriviaCorrectOption(q["correct"]),
            question_type=TriviaQuestionType(q["type"]),
            is_approved=True,
        )
        db.add(row)
        inserted += 1

    db.commit()
    print(f"  {file_path.name}: inserted {inserted} "
          f"({skipped_not_approved} not approved, {duplicates} duplicates skipped)")
    return {"file": file_path.name, "imported": inserted, "skipped": duplicates, "errors": 0}


def main():
    parser = argparse.ArgumentParser(description="Import approved trivia questions into the DB")
    parser.add_argument("--file", nargs="+", required=True, help="One or more draft JSON files to import")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be imported without writing to DB")
    args = parser.parse_args()

    files = []
    for pattern in args.file:
        # Support shell glob expansion (argparse receives already-expanded list on most shells,
        # but handle single literal glob just in case)
        paths = list(Path(".").glob(pattern)) if "*" in pattern else [Path(pattern)]
        files.extend(paths)

    if not files:
        print("No matching files found.")
        sys.exit(1)

    files = sorted(set(files))

    if not args.dry_run:
        from app.db import SessionLocal
        db = SessionLocal()
    else:
        db = None

    total_imported = 0
    total_errors = 0

    try:
        for f in files:
            if not f.exists():
                print(f"File not found: {f}")
                total_errors += 1
                continue
            print(f"\nProcessing {f}")
            result = import_file(f, db, args.dry_run)
            total_imported += result.get("imported", result.get("would_import", 0))
            total_errors += result.get("errors", 0)
    finally:
        if db:
            db.close()

    print(f"\n{'[DRY RUN] ' if args.dry_run else ''}Done. Total inserted: {total_imported}, errors: {total_errors}")
    if total_errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
