"""
Script to add 2 open-ended questions per category to the Matthew and Genesis assessments.
Appends to existing templates without modifying existing questions.

Run as: python add_open_ended_questions.py
"""
import os
import sys
from pathlib import Path

# Add the app directory to Python path
sys.path.append(str(Path(__file__).parent))

from sqlalchemy import text
from app.db import engine
import uuid

# ── Matthew: 2 open-ended questions per category (5 categories × 2 = 10) ──

MATTHEW_KEY = "matthew_bible_v1"
MATTHEW_OPEN_QUESTIONS = [
    # Narrative Events
    {
        "category": "Narrative Events",
        "text": "Describe the events surrounding Jesus' baptism by John the Baptist in the Jordan River. What significance do you see in what happened immediately after He was baptized?",
        "question_type": "open_ended",
    },
    {
        "category": "Narrative Events",
        "text": "In your own words, retell the account of Jesus' triumphal entry into Jerusalem. Why do you think this event was important for both Jesus and the people who witnessed it?",
        "question_type": "open_ended",
    },
    # Teachings of Jesus
    {
        "category": "Teachings of Jesus",
        "text": "Choose one of the Beatitudes from the Sermon on the Mount (Matthew 5:3-12) and explain what you think Jesus meant by it. How could this teaching apply to your daily life?",
        "question_type": "open_ended",
    },
    {
        "category": "Teachings of Jesus",
        "text": "Jesus often taught using parables. Pick one parable from the Book of Matthew and explain the lesson you believe Jesus was communicating through it.",
        "question_type": "open_ended",
    },
    # Key Characters
    {
        "category": "Key Characters",
        "text": "Peter is one of the most prominent disciples in the Book of Matthew. Describe a moment where Peter showed great faith and a moment where he struggled. What can we learn from his example?",
        "question_type": "open_ended",
    },
    {
        "category": "Key Characters",
        "text": "What role did Joseph (Jesus' earthly father) play in the early chapters of Matthew? How did his actions demonstrate obedience and trust in God?",
        "question_type": "open_ended",
    },
    # Themes & Purpose
    {
        "category": "Themes & Purpose",
        "text": "Matthew's Gospel emphasizes that Jesus is the fulfillment of Old Testament prophecy. Give an example from Matthew where this theme appears and explain why it matters.",
        "question_type": "open_ended",
    },
    {
        "category": "Themes & Purpose",
        "text": "The concept of the 'Kingdom of Heaven' is central to Matthew's Gospel. In your own words, explain what you think Jesus meant by the Kingdom of Heaven and how believers are called to participate in it.",
        "question_type": "open_ended",
    },
    # Chapter Locations
    {
        "category": "Chapter Locations",
        "text": "The Great Commission is found at the end of Matthew's Gospel. Write out what Jesus commanded His disciples to do and explain why this passage is considered so important for Christians today.",
        "question_type": "open_ended",
    },
    {
        "category": "Chapter Locations",
        "text": "Matthew chapters 24-25 contain Jesus' teachings about the end times and His return. Summarize one key lesson from these chapters and explain what it teaches about being spiritually prepared.",
        "question_type": "open_ended",
    },
]

# ── Genesis: 2 open-ended questions per category (5 categories × 2 = 10) ──

GENESIS_KEY = "genesis_bible_v1"
GENESIS_OPEN_QUESTIONS = [
    # Creation & Early Humanity
    {
        "category": "Creation & Early Humanity",
        "text": "Describe the sequence of events during the Creation week as recorded in Genesis 1-2. What stands out to you most about how God created the world and humanity?",
        "question_type": "open_ended",
    },
    {
        "category": "Creation & Early Humanity",
        "text": "Explain the story of the Fall in Genesis 3. What were the consequences of Adam and Eve's disobedience, and what do you think this teaches us about the nature of sin?",
        "question_type": "open_ended",
    },
    # Abraham's Story
    {
        "category": "Abraham's Story",
        "text": "God made a covenant with Abraham that included several promises. Describe those promises and explain what Abraham's willingness to sacrifice Isaac reveals about his faith.",
        "question_type": "open_ended",
    },
    {
        "category": "Abraham's Story",
        "text": "Abraham and Sarah waited many years for the child God promised them. What challenges did they face during that waiting period, and what can we learn from their experience about trusting God's timing?",
        "question_type": "open_ended",
    },
    # Isaac, Jacob & Esau
    {
        "category": "Isaac, Jacob & Esau",
        "text": "Describe the conflict between Jacob and Esau over the birthright and blessing. What were the long-term consequences of this rivalry for both brothers and their descendants?",
        "question_type": "open_ended",
    },
    {
        "category": "Isaac, Jacob & Esau",
        "text": "Jacob wrestled with God at Peniel and was given a new name (Israel). What do you think this event symbolized in Jacob's spiritual journey, and how did it change him?",
        "question_type": "open_ended",
    },
    # Joseph's Story
    {
        "category": "Joseph's Story",
        "text": "Trace Joseph's journey from being sold into slavery by his brothers to becoming a ruler in Egypt. What character qualities helped Joseph endure his hardships and ultimately succeed?",
        "question_type": "open_ended",
    },
    {
        "category": "Joseph's Story",
        "text": "When Joseph finally revealed himself to his brothers, he told them that what they meant for evil, God meant for good. Explain this statement and what it teaches about God's sovereignty over difficult circumstances.",
        "question_type": "open_ended",
    },
    # Key Themes & Chapter Locations
    {
        "category": "Key Themes & Chapter Locations",
        "text": "The theme of covenant appears throughout Genesis. Choose one covenant God made (with Noah, Abraham, etc.) and explain its terms, its significance, and how it points to God's larger plan for humanity.",
        "question_type": "open_ended",
    },
    {
        "category": "Key Themes & Chapter Locations",
        "text": "Genesis is sometimes called the 'book of beginnings.' Identify at least three major 'beginnings' found in Genesis and explain why each one is foundational to the rest of the Bible.",
        "question_type": "open_ended",
    },
]


def add_open_ended_questions():
    """Add open-ended questions to existing Matthew and Genesis assessment templates."""
    with engine.begin() as conn:
        for assessment_key, questions_data, code_prefix in [
            (MATTHEW_KEY, MATTHEW_OPEN_QUESTIONS, "MATT_OE"),
            (GENESIS_KEY, GENESIS_OPEN_QUESTIONS, "GEN_OE"),
        ]:
            print(f"\n{'='*60}")
            print(f"Processing: {assessment_key}")
            print(f"{'='*60}")

            # Find the template
            result = conn.execute(
                text("SELECT id FROM assessment_templates WHERE key = :key"),
                {"key": assessment_key},
            )
            row = result.fetchone()
            if not row:
                print(f"❌ Template with key '{assessment_key}' not found! Skipping.")
                continue
            template_id = row[0]
            print(f"✅ Found template: {template_id}")

            # Get current max order
            result = conn.execute(
                text(
                    "SELECT COALESCE(MAX(\"order\"), 0) FROM assessment_template_questions WHERE template_id = :tid"
                ),
                {"tid": template_id},
            )
            max_order = result.scalar()
            print(f"   Current max question order: {max_order}")

            # Get or create categories (reuse existing)
            categories = {}
            category_names = list(set(q["category"] for q in questions_data))
            for cat_name in category_names:
                result = conn.execute(
                    text("SELECT id FROM categories WHERE name = :name"),
                    {"name": cat_name},
                )
                existing_cat = result.fetchone()
                if existing_cat:
                    categories[cat_name] = existing_cat[0]
                    print(f"   Found category: {cat_name}")
                else:
                    cat_id = str(uuid.uuid4())
                    conn.execute(
                        text("INSERT INTO categories (id, name) VALUES (:id, :name)"),
                        {"id": cat_id, "name": cat_name},
                    )
                    categories[cat_name] = cat_id
                    print(f"   ➕ Created category: {cat_name}")

            # Check for duplicates (don't re-add if script is run twice)
            result = conn.execute(
                text(
                    """
                    SELECT q.question_code FROM questions q
                    JOIN assessment_template_questions atq ON atq.question_id = q.id
                    WHERE atq.template_id = :tid AND q.question_type = 'open_ended'
                    """
                ),
                {"tid": template_id},
            )
            existing_oe = {r[0] for r in result.fetchall()}
            if existing_oe:
                print(f"   ⚠️  Found {len(existing_oe)} existing open-ended questions. Skipping duplicates.")

            # Insert questions
            added = 0
            question_order = max_order
            for idx, q_data in enumerate(questions_data, start=1):
                question_code = f"{code_prefix}_{idx:03d}"
                if question_code in existing_oe:
                    print(f"   ⏭️  [{question_code}] Already exists, skipping.")
                    continue

                question_order += 1
                question_id = str(uuid.uuid4())
                category_id = categories[q_data["category"]]

                # Insert question
                conn.execute(
                    text(
                        """
                        INSERT INTO questions (id, text, question_type, category_id, question_code)
                        VALUES (:id, :text, :question_type, :category_id, :question_code)
                        """
                    ),
                    {
                        "id": question_id,
                        "text": q_data["text"],
                        "question_type": "open_ended",
                        "category_id": category_id,
                        "question_code": question_code,
                    },
                )

                # Link question to template
                tq_id = str(uuid.uuid4())
                conn.execute(
                    text(
                        """
                        INSERT INTO assessment_template_questions (id, template_id, question_id, "order")
                        VALUES (:id, :template_id, :question_id, :order)
                        """
                    ),
                    {
                        "id": tq_id,
                        "template_id": template_id,
                        "question_id": question_id,
                        "order": question_order,
                    },
                )

                print(f"   ✅ [{question_code}] {q_data['text'][:60]}...")
                added += 1

            print(f"\n🎉 Added {added} open-ended questions to {assessment_key}")

        # Also update scoring_strategy to 'ai' since we now have open-ended questions
        for key in [MATTHEW_KEY, GENESIS_KEY]:
            conn.execute(
                text(
                    "UPDATE assessment_templates SET scoring_strategy = 'ai' WHERE key = :key"
                ),
                {"key": key},
            )
            print(f"📝 Updated {key} scoring_strategy → 'ai' (mixed question types)")


if __name__ == "__main__":
    add_open_ended_questions()
    print("\n✅ Done!")
