"""
Seed a small Master Trooth assessment template with 2 questions per category.
- Creates or reuses categories (Spiritual Growth, Prayer Life, Bible Study, Community & Fellowship, Service & Ministry, Discipleship, Faith Practice)
- Creates a template "Master Trooth Assessment (Mini 2-per-category)" with key "master_trooth_mini_v1"
- Adds 2 open-ended questions per category and links them to the template in order
- Idempotent: if the template exists, its question links are replaced to match this script's set

Usage:
  python scripts/seed_master_mini.py

Optional flags:
  --reset-questions  # Deletes and recreates question links even if the template exists

Environment:
  Uses the database configured by app.core.settings / app.db
"""
from __future__ import annotations
import sys
import uuid
from typing import List, Tuple

from app.db import SessionLocal
from app.models.assessment_template import AssessmentTemplate
from app.models.assessment_template_question import AssessmentTemplateQuestion
from app.models.category import Category
from app.models.question import Question, QuestionType

TEMPLATE_KEY = "master_trooth_mini_v1"
TEMPLATE_NAME = "Mini Trooth Assessment"

CATEGORIES: List[Tuple[str, str]] = [
    ("spiritual_growth", "Spiritual Growth"),
    ("prayer_life", "Prayer Life"),
    ("bible_study", "Bible Study"),
    ("community_fellowship", "Community & Fellowship"),
    ("service_ministry", "Service & Ministry"),
    ("discipleship", "Discipleship"),
    ("faith_practice", "Faith Practice"),
]

# Two concise open-ended questions per category for faster testing
QUESTION_TEXTS: List[Tuple[str, List[str]]] = [
    (
        "Spiritual Growth",
        [
            "Describe one way you've grown spiritually in the last month.",
            "What is one area of growth you want to focus on next?",
        ],
    ),
    (
        "Prayer Life",
        [
            "Briefly describe your current prayer rhythm (when/where/how).",
            "Share one recent answer to prayer or a challenge in prayer.",
        ],
    ),
    (
        "Bible Study",
        [
            "What passage has influenced you most recently and why?",
            "How do you decide what to study or read next?",
        ],
    ),
    (
        "Community & Fellowship",
        [
            "How are you currently engaged in Christian community?",
            "Share one recent experience of encouragement or accountability.",
        ],
    ),
    (
        "Service & Ministry",
        [
            "Where do you feel most effective serving right now?",
            "What opportunity to serve are you considering in the next month?",
        ],
    ),
    (
        "Discipleship",
        [
            "Who is investing in you, and who are you investing in?",
            "Name one practical next step in discipleship you plan to take.",
        ],
    ),
    (
        "Faith Practice",
        [
            "Which spiritual discipline has been most meaningful lately?",
            "What practice would you like to build more consistency in?",
        ],
    ),
]


def _upsert_category(db, name: str) -> Category:
    cat = db.query(Category).filter(Category.name == name).first()
    if not cat:
        cat = Category(name=name)
        db.add(cat)
        db.flush()
    return cat


def _upsert_question(
    db,
    code: str,
    text: str,
    category_id: str,
    qtype: QuestionType = QuestionType.open_ended,
) -> Question:
    q = db.query(Question).filter(Question.question_code == code).first()
    if not q:
        q = Question(question_code=code, text=text, question_type=qtype, category_id=category_id)
        db.add(q)
        db.flush()
    else:
        # Keep question text in sync (safe for test seeds)
        q.text = text
        q.question_type = qtype
        q.category_id = category_id
        db.add(q)
        db.flush()
    return q


def _upsert_template(db) -> AssessmentTemplate:
    tpl = db.query(AssessmentTemplate).filter(AssessmentTemplate.key == TEMPLATE_KEY).first()
    if not tpl:
        tpl = AssessmentTemplate(
            name=TEMPLATE_NAME,
            description="Mini master assessment for testing (2 questions per category).",
            is_published=True,
            is_master_assessment=False,  # avoid clashing with the real master template
            key=TEMPLATE_KEY,
            version=1,
            scoring_strategy="ai_master",
            report_template="master_trooth_report.html",
            pdf_renderer="master_trooth",
        )
        db.add(tpl)
        db.flush()
    return tpl


def _clear_template_links(db, template_id: str) -> None:
    db.query(AssessmentTemplateQuestion).filter(
        AssessmentTemplateQuestion.template_id == template_id
    ).delete(synchronize_session=False)
    db.flush()


def _link_questions_in_order(db, template_id: str, question_ids: List[str]) -> None:
    for idx, qid in enumerate(question_ids, start=1):
        link = AssessmentTemplateQuestion(
            template_id=template_id,
            question_id=qid,
            order=idx,
        )
        db.add(link)
    db.flush()


def seed(reset_questions: bool = True) -> str:
    db = SessionLocal()
    try:
        tpl = _upsert_template(db)
        # Build lookup for category ids
        cat_id_by_name = {}
        for slug, display in CATEGORIES:
            cat = _upsert_category(db, display)
            cat_id_by_name[display] = cat.id

        # Create questions and collect IDs in order
        question_ids: List[str] = []
        for cat_name, texts in QUESTION_TEXTS:
            cat_id = cat_id_by_name[cat_name]
            for i, text in enumerate(texts, start=1):
                code = f"MTM-{cat_name.replace(' ', '_').replace('&', 'and').lower()}-q{i}"
                q = _upsert_question(db, code, text, category_id=cat_id, qtype=QuestionType.open_ended)
                question_ids.append(q.id)

        if reset_questions:
            _clear_template_links(db, tpl.id)
        else:
            # If not resetting, still ensure we don't duplicate links by clearing existing links to these questions
            db.query(AssessmentTemplateQuestion).filter(
                AssessmentTemplateQuestion.template_id == tpl.id
            ).delete(synchronize_session=False)
            db.flush()
        _link_questions_in_order(db, tpl.id, question_ids)
        db.commit()
        print(f"✅ Seeded template '{TEMPLATE_NAME}' (key={TEMPLATE_KEY}) with {len(question_ids)} questions.")
        return tpl.id
    except Exception as e:
        db.rollback()
        print(f"❌ Failed to seed template: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    reset = True
    if "--no-reset" in sys.argv:
        reset = False
    seed(reset_questions=reset)
