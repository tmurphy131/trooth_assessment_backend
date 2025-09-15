"""Seed Spiritual Gift Definitions (idempotent, versioned).

Usage examples:
  python scripts/seed_spiritual_gifts.py --version 1 --file scripts/spiritual_gift_definitions_v1.json --publish
  DATABASE_URL=postgresql://... python scripts/seed_spiritual_gifts.py --version 1 --file scripts/spiritual_gift_definitions_v1.json --replace --publish

Behavior:
  - Validates JSON file entries (version, required fields).
  - Inserts rows into spiritual_gift_definitions if absent or replaces when --replace.
  - Optionally publishes an AssessmentTemplate record for the version.
  - Safe to re-run; use --replace to force refresh for that version.
"""
from __future__ import annotations
import argparse
import json
import os
import sys
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.append(str(Path(__file__).resolve().parents[1]))
from app.models.spiritual_gift_definition import SpiritualGiftDefinition  # noqa: E402
from app.models.assessment_template import AssessmentTemplate  # noqa: E402
from app.models.question import Question  # noqa: E402
from app.models.assessment_template_question import AssessmentTemplateQuestion  # noqa: E402
from app.core.spiritual_gifts_map import QUESTION_ITEMS, MAP  # noqa: E402


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--url", default=os.getenv("DATABASE_URL"), help="Database URL (env DATABASE_URL by default)")
    p.add_argument("--version", type=int, required=True, help="Definitions version to seed")
    p.add_argument("--file", required=True, help="Path to JSON definitions file")
    p.add_argument("--replace", action="store_true", help="Delete existing version definitions before inserting")
    p.add_argument("--publish", action="store_true", help="Publish template for this version if not already")
    p.add_argument("--seed-questions", action="store_true", help="Also seed the 72 spiritual gift questions & link to template")
    p.add_argument("--force-relink", action="store_true", help="Recreate template → question linkage (order) even if some exist")
    p.add_argument("--dry-run", action="store_true", help="Run without committing DB writes (except reads)")
    p.add_argument("--verify-only", action="store_true", help="Do not write; only verify that all codes & links exist")
    p.add_argument("--allow-text-update", action="store_true", help="Permit updating existing question text if it changed")
    return p.parse_args()


def load_definitions(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    args = parse_args()
    if not args.url:
        print("ERROR: Provide --url or set DATABASE_URL", file=sys.stderr)
        sys.exit(2)

    print(f"[seed_spiritual_gifts] Connecting to database: {args.url}")

    data = load_definitions(args.file)
    required = {"gift_slug", "display_name", "full_definition", "version", "locale"}
    for i, entry in enumerate(data):
        missing = required - entry.keys()
        if missing:
            print(f"ERROR: entry #{i} missing keys {missing}", file=sys.stderr)
            sys.exit(3)
        if entry["version"] != args.version:
            print(f"ERROR: entry #{i} version {entry['version']} != --version {args.version}", file=sys.stderr)
            sys.exit(3)

    try:
        engine = create_engine(args.url)
    except Exception as e:  # pragma: no cover - defensive logging
        print("ERROR: Failed to create engine for provided URL", file=sys.stderr)
        print(repr(e), file=sys.stderr)
        print("Hint: If the URL contains /cloudsql/... you must run the Cloud SQL Auth Proxy locally or supply a local postgres URL via --url", file=sys.stderr)
        sys.exit(4)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    # QUESTION_ITEMS and MAP now imported from app.core.spiritual_gifts_map

    def validate_map():
        all_codes = {c for c, _, _ in QUESTION_ITEMS}
        mapped_codes = {code for triplet in MAP.values() for code in triplet}
        if len(all_codes) != 72:
            raise ValueError(f"Expected 72 question codes, found {len(all_codes)}")
        if all_codes != mapped_codes:
            missing = all_codes - mapped_codes
            extra = mapped_codes - all_codes
            raise ValueError(f"MAP coverage mismatch. Missing={missing} Extra={extra}")
        for gift, triplet in MAP.items():
            if len(triplet) != 3:
                raise ValueError(f"Gift {gift} does not map to exactly 3 items")

    try:
        existing = session.query(SpiritualGiftDefinition).filter(SpiritualGiftDefinition.version == args.version).all()
        if existing and not args.replace:
            print(f"Definitions already present for version {args.version} (count={len(existing)}). Skipping (use --replace to overwrite).")
        else:
            if existing:
                for row in existing:
                    session.delete(row)
                session.flush()
                print(f"Deleted {len(existing)} existing definitions for version {args.version}")
            for entry in data:
                session.add(SpiritualGiftDefinition(
                    gift_slug=entry["gift_slug"],
                    display_name=entry["display_name"],
                    short_summary=entry.get("short_summary"),
                    full_definition=entry["full_definition"],
                    version=entry["version"],
                    locale=entry.get("locale", "en"),
                ))
            session.commit()
            print(f"Inserted {len(data)} gift definitions (version {args.version})")

        if args.seed_questions or args.verify_only:
            print("-- Spiritual Gifts question code validation & seeding --")
            validate_map()
            # Template fetch/create (unless verify-only and missing -> fail)
            template = (
                session.query(AssessmentTemplate)
                .filter(AssessmentTemplate.name == "Spiritual Gifts Assessment", AssessmentTemplate.version == args.version)
                .first()
            )
            if not template:
                if args.verify_only:
                    print("VERIFY FAIL: Template not found")
                    sys.exit(5)
                template = AssessmentTemplate(
                    name="Spiritual Gifts Assessment",
                    description=f"Spiritual gifts assessment (version {args.version})",
                    is_published=False,
                    is_master_assessment=False,
                    version=args.version,
                )
                session.add(template)
                session.flush()
                print(f"Created template draft id={template.id}")

            # Build lookup of existing questions by code
            all_codes = [code for code, _gift_slug, _text in QUESTION_ITEMS]
            existing_questions = (
                session.query(Question)
                .filter(Question.question_code.in_(all_codes))
                .all()
            )
            by_code = {q.question_code: q for q in existing_questions}
            inserted = 0
            updated = 0

            if not args.verify_only:
                for order_idx, (code, gift_slug, text) in enumerate(QUESTION_ITEMS, start=1):
                    existing_q = by_code.get(code)
                    if not existing_q:
                        q = Question(question_code=code, text=text)  # question_type defaults to open_ended
                        session.add(q)
                        session.flush()
                        by_code[code] = q
                        inserted += 1
                        print(f"Inserted question {code} (id={q.id})")
                    else:
                        if existing_q.text != text:
                            if args.allow_text_update:
                                print(f"Updating text for {code}")
                                existing_q.text = text
                                updated += 1
                            else:
                                print(f"WARNING: Text drift for {code}; run with --allow-text-update to apply change")

            # Verify coverage
            missing_codes = [c for c in all_codes if c not in by_code]
            if missing_codes:
                print(f"ERROR: Missing questions for codes: {missing_codes}")
                sys.exit(6)

            # Link questions in deterministic order
            if args.force_relink and not args.verify_only:
                existing_links = session.query(AssessmentTemplateQuestion).filter(AssessmentTemplateQuestion.template_id == template.id).all()
                for l in existing_links:
                    session.delete(l)
                session.flush()
                print(f"Removed {len(existing_links)} existing template question links (force-relink)")
            # Build current linkage map
            existing_link_ids = {
                (l.question_id) for l in session.query(AssessmentTemplateQuestion).filter(AssessmentTemplateQuestion.template_id == template.id).all()
            }
            link_inserts = 0
            for order_idx, (code, _gift_slug, _text) in enumerate(QUESTION_ITEMS, start=1):
                qid = by_code[code].id
                if qid not in existing_link_ids and not args.verify_only:
                    session.add(AssessmentTemplateQuestion(template_id=template.id, question_id=qid, order=order_idx))
                    link_inserts += 1
            if not args.verify_only:
                if link_inserts:
                    print(f"Linked {link_inserts} questions to template {template.id}")
                total_links = session.query(AssessmentTemplateQuestion).filter(AssessmentTemplateQuestion.template_id == template.id).count()
            else:
                total_links = session.query(AssessmentTemplateQuestion).filter(AssessmentTemplateQuestion.template_id == template.id).count()
            if total_links != 72:
                print(f"WARNING: Template currently has {total_links} linked questions (expected 72)")
            else:
                print("Template has all 72 questions linked ✅")

            if args.verify_only:
                print("VERIFY-ONLY: No changes applied.")
            elif args.dry_run:
                print("Dry run active: rolling back changes (inserted={}, updated={}, new_links={})".format(inserted, updated, link_inserts))
                session.rollback()
            else:
                session.commit()
                print(f"Commit complete (inserted={inserted}, updated={updated}, new_links={link_inserts})")

        if args.publish and not args.dry_run:
            tpl = (
                session.query(AssessmentTemplate)
                .filter(
                    AssessmentTemplate.name == "Spiritual Gifts Assessment",
                    AssessmentTemplate.version == args.version,
                    AssessmentTemplate.is_published == True,  # noqa: E712
                ).first()
            )
            if not tpl:
                # If created earlier (unpublished) fetch again
                draft = (
                    session.query(AssessmentTemplate)
                    .filter(AssessmentTemplate.name == "Spiritual Gifts Assessment", AssessmentTemplate.version == args.version)
                    .first()
                )
                if draft:
                    draft.is_published = True
                    session.commit()
                    print(f"Published existing template id={draft.id} version={args.version}")
                else:
                    new_tpl = AssessmentTemplate(
                        name="Spiritual Gifts Assessment",
                        description=f"Spiritual gifts assessment (version {args.version})",
                        is_published=True,
                        is_master_assessment=False,
                        version=args.version,
                    )
                    session.add(new_tpl)
                    session.commit()
                    print(f"Published new template id={new_tpl.id} version={args.version}")
            else:
                print(f"Template already published for version {args.version} (id={tpl.id})")
    finally:
        session.close()


if __name__ == "__main__":  # pragma: no cover
    main()
