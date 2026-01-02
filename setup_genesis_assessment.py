"""
Script to create the Book of Genesis Bible Knowledge Assessment
Run as: python setup_genesis_assessment.py
Or as Cloud Run job
"""
import os
import sys
from pathlib import Path

# Add the app directory to Python path
sys.path.append(str(Path(__file__).parent))

from sqlalchemy import text
from app.db import engine
import uuid

# Assessment metadata
ASSESSMENT_KEY = "genesis_bible_v1"
ASSESSMENT_NAME = "Book of Genesis Assessment"
ASSESSMENT_DESCRIPTION = """Test your knowledge of the Book of Genesis, the first book of the Bible. This comprehensive assessment covers Creation, the Patriarchs (Abraham, Isaac, Jacob, Joseph), key covenants, and foundational events that shape the rest of Scripture. 50 multiple choice questions across 5 categories."""

# Questions organized by category
QUESTIONS_DATA = [
    # ===========================================
    # CATEGORY: Creation & Early Humanity (10 questions)
    # ===========================================
    {
        "category": "Creation & Early Humanity",
        "text": "How many days did God take to create the heavens and earth before resting?",
        "type": "multiple_choice",
        "options": [
            {"text": "5 days", "is_correct": False},
            {"text": "6 days", "is_correct": True},
            {"text": "7 days", "is_correct": False},
            {"text": "40 days", "is_correct": False}
        ]
    },
    {
        "category": "Creation & Early Humanity",
        "text": "What was the first thing God created according to Genesis 1?",
        "type": "multiple_choice",
        "options": [
            {"text": "Water", "is_correct": False},
            {"text": "Light", "is_correct": True},
            {"text": "Land", "is_correct": False},
            {"text": "Animals", "is_correct": False}
        ]
    },
    {
        "category": "Creation & Early Humanity",
        "text": "From what did God create the first woman, Eve?",
        "type": "multiple_choice",
        "options": [
            {"text": "Dust of the ground", "is_correct": False},
            {"text": "Adam's rib", "is_correct": True},
            {"text": "Clay", "is_correct": False},
            {"text": "The tree of life", "is_correct": False}
        ]
    },
    {
        "category": "Creation & Early Humanity",
        "text": "What tree were Adam and Eve forbidden to eat from?",
        "type": "multiple_choice",
        "options": [
            {"text": "Tree of Life", "is_correct": False},
            {"text": "Tree of Knowledge of Good and Evil", "is_correct": True},
            {"text": "The fig tree", "is_correct": False},
            {"text": "The olive tree", "is_correct": False}
        ]
    },
    {
        "category": "Creation & Early Humanity",
        "text": "Who was the first person to commit murder in the Bible?",
        "type": "multiple_choice",
        "options": [
            {"text": "Lamech", "is_correct": False},
            {"text": "Cain", "is_correct": True},
            {"text": "Abel", "is_correct": False},
            {"text": "Seth", "is_correct": False}
        ]
    },
    {
        "category": "Creation & Early Humanity",
        "text": "What was Cain's occupation?",
        "type": "multiple_choice",
        "options": [
            {"text": "Shepherd", "is_correct": False},
            {"text": "Farmer/tiller of the ground", "is_correct": True},
            {"text": "Hunter", "is_correct": False},
            {"text": "Tent maker", "is_correct": False}
        ]
    },
    {
        "category": "Creation & Early Humanity",
        "text": "Why did God send the flood in Noah's time?",
        "type": "multiple_choice",
        "options": [
            {"text": "To water the earth", "is_correct": False},
            {"text": "To punish the serpent", "is_correct": False},
            {"text": "Because of widespread human wickedness", "is_correct": True},
            {"text": "To create the oceans", "is_correct": False}
        ]
    },
    {
        "category": "Creation & Early Humanity",
        "text": "How many of each clean animal did Noah bring on the ark?",
        "type": "multiple_choice",
        "options": [
            {"text": "2", "is_correct": False},
            {"text": "7 (or 7 pairs)", "is_correct": True},
            {"text": "12", "is_correct": False},
            {"text": "40", "is_correct": False}
        ]
    },
    {
        "category": "Creation & Early Humanity",
        "text": "What sign did God give as a covenant promise never to flood the earth again?",
        "type": "multiple_choice",
        "options": [
            {"text": "A dove", "is_correct": False},
            {"text": "An olive branch", "is_correct": False},
            {"text": "A rainbow", "is_correct": True},
            {"text": "A star", "is_correct": False}
        ]
    },
    {
        "category": "Creation & Early Humanity",
        "text": "Why did God confuse the languages of people at the Tower of Babel?",
        "type": "multiple_choice",
        "options": [
            {"text": "To punish them for idol worship", "is_correct": False},
            {"text": "To scatter them and stop them from building a tower to heaven", "is_correct": True},
            {"text": "To teach them humility", "is_correct": False},
            {"text": "To create different nations for war", "is_correct": False}
        ]
    },
    # ===========================================
    # CATEGORY: Abraham's Story (10 questions)
    # ===========================================
    {
        "category": "Abraham's Story",
        "text": "What was Abraham's original name before God changed it?",
        "type": "multiple_choice",
        "options": [
            {"text": "Abram", "is_correct": True},
            {"text": "Abner", "is_correct": False},
            {"text": "Abimelech", "is_correct": False},
            {"text": "Aram", "is_correct": False}
        ]
    },
    {
        "category": "Abraham's Story",
        "text": "From what city did God call Abraham to leave?",
        "type": "multiple_choice",
        "options": [
            {"text": "Babylon", "is_correct": False},
            {"text": "Ur of the Chaldeans", "is_correct": True},
            {"text": "Haran", "is_correct": False},
            {"text": "Canaan", "is_correct": False}
        ]
    },
    {
        "category": "Abraham's Story",
        "text": "What land did God promise to give Abraham and his descendants?",
        "type": "multiple_choice",
        "options": [
            {"text": "Egypt", "is_correct": False},
            {"text": "Babylon", "is_correct": False},
            {"text": "Canaan", "is_correct": True},
            {"text": "Mesopotamia", "is_correct": False}
        ]
    },
    {
        "category": "Abraham's Story",
        "text": "Who was Abraham's wife?",
        "type": "multiple_choice",
        "options": [
            {"text": "Rebekah", "is_correct": False},
            {"text": "Rachel", "is_correct": False},
            {"text": "Sarah", "is_correct": True},
            {"text": "Leah", "is_correct": False}
        ]
    },
    {
        "category": "Abraham's Story",
        "text": "Who was Abraham's nephew who traveled with him to Canaan?",
        "type": "multiple_choice",
        "options": [
            {"text": "Ishmael", "is_correct": False},
            {"text": "Lot", "is_correct": True},
            {"text": "Esau", "is_correct": False},
            {"text": "Laban", "is_correct": False}
        ]
    },
    {
        "category": "Abraham's Story",
        "text": "Who was the son born to Abraham through Hagar, Sarah's servant?",
        "type": "multiple_choice",
        "options": [
            {"text": "Isaac", "is_correct": False},
            {"text": "Ishmael", "is_correct": True},
            {"text": "Jacob", "is_correct": False},
            {"text": "Esau", "is_correct": False}
        ]
    },
    {
        "category": "Abraham's Story",
        "text": "At what age did Abraham have his son Isaac?",
        "type": "multiple_choice",
        "options": [
            {"text": "75 years old", "is_correct": False},
            {"text": "86 years old", "is_correct": False},
            {"text": "99 years old", "is_correct": False},
            {"text": "100 years old", "is_correct": True}
        ]
    },
    {
        "category": "Abraham's Story",
        "text": "What did God ask Abraham to sacrifice as a test of faith?",
        "type": "multiple_choice",
        "options": [
            {"text": "A lamb", "is_correct": False},
            {"text": "His son Isaac", "is_correct": True},
            {"text": "His wealth", "is_correct": False},
            {"text": "His land", "is_correct": False}
        ]
    },
    {
        "category": "Abraham's Story",
        "text": "What did God provide as a substitute sacrifice instead of Isaac?",
        "type": "multiple_choice",
        "options": [
            {"text": "A lamb", "is_correct": False},
            {"text": "A ram caught in a thicket", "is_correct": True},
            {"text": "A dove", "is_correct": False},
            {"text": "A bull", "is_correct": False}
        ]
    },
    {
        "category": "Abraham's Story",
        "text": "What two cities did God destroy with fire and brimstone because of their wickedness?",
        "type": "multiple_choice",
        "options": [
            {"text": "Babylon and Nineveh", "is_correct": False},
            {"text": "Sodom and Gomorrah", "is_correct": True},
            {"text": "Ur and Haran", "is_correct": False},
            {"text": "Jericho and Ai", "is_correct": False}
        ]
    },
    # ===========================================
    # CATEGORY: Isaac, Jacob & Esau (10 questions)
    # ===========================================
    {
        "category": "Isaac, Jacob & Esau",
        "text": "Who did Abraham's servant find as a wife for Isaac?",
        "type": "multiple_choice",
        "options": [
            {"text": "Rachel", "is_correct": False},
            {"text": "Leah", "is_correct": False},
            {"text": "Rebekah", "is_correct": True},
            {"text": "Zilpah", "is_correct": False}
        ]
    },
    {
        "category": "Isaac, Jacob & Esau",
        "text": "How did the servant know Rebekah was the right woman for Isaac?",
        "type": "multiple_choice",
        "options": [
            {"text": "She was the most beautiful", "is_correct": False},
            {"text": "She offered water to him and his camels", "is_correct": True},
            {"text": "An angel appeared to him", "is_correct": False},
            {"text": "She was Abraham's relative", "is_correct": False}
        ]
    },
    {
        "category": "Isaac, Jacob & Esau",
        "text": "Which of Isaac's twin sons was born first?",
        "type": "multiple_choice",
        "options": [
            {"text": "Jacob", "is_correct": False},
            {"text": "Esau", "is_correct": True},
            {"text": "They were born at the same time", "is_correct": False},
            {"text": "Joseph", "is_correct": False}
        ]
    },
    {
        "category": "Isaac, Jacob & Esau",
        "text": "What physical characteristic distinguished Esau at birth?",
        "type": "multiple_choice",
        "options": [
            {"text": "He was very tall", "is_correct": False},
            {"text": "He was red and hairy", "is_correct": True},
            {"text": "He had a birthmark", "is_correct": False},
            {"text": "He was blind", "is_correct": False}
        ]
    },
    {
        "category": "Isaac, Jacob & Esau",
        "text": "What did Esau sell to Jacob for a bowl of stew?",
        "type": "multiple_choice",
        "options": [
            {"text": "His inheritance", "is_correct": False},
            {"text": "His birthright", "is_correct": True},
            {"text": "His blessing", "is_correct": False},
            {"text": "His flocks", "is_correct": False}
        ]
    },
    {
        "category": "Isaac, Jacob & Esau",
        "text": "How did Jacob deceive his father Isaac to receive the blessing meant for Esau?",
        "type": "multiple_choice",
        "options": [
            {"text": "By lying about his age", "is_correct": False},
            {"text": "By wearing Esau's clothes and goat skins", "is_correct": True},
            {"text": "By bribing the servants", "is_correct": False},
            {"text": "By waiting until Isaac left", "is_correct": False}
        ]
    },
    {
        "category": "Isaac, Jacob & Esau",
        "text": "What did Jacob see in his dream at Bethel?",
        "type": "multiple_choice",
        "options": [
            {"text": "A burning bush", "is_correct": False},
            {"text": "A ladder reaching to heaven with angels", "is_correct": True},
            {"text": "A river of fire", "is_correct": False},
            {"text": "Seven stars", "is_correct": False}
        ]
    },
    {
        "category": "Isaac, Jacob & Esau",
        "text": "Who was Jacob's uncle that he worked for in Haran?",
        "type": "multiple_choice",
        "options": [
            {"text": "Esau", "is_correct": False},
            {"text": "Laban", "is_correct": True},
            {"text": "Lot", "is_correct": False},
            {"text": "Ishmael", "is_correct": False}
        ]
    },
    {
        "category": "Isaac, Jacob & Esau",
        "text": "How many years total did Jacob work for Laban to marry Rachel?",
        "type": "multiple_choice",
        "options": [
            {"text": "7 years", "is_correct": False},
            {"text": "14 years", "is_correct": True},
            {"text": "20 years", "is_correct": False},
            {"text": "3 years", "is_correct": False}
        ]
    },
    {
        "category": "Isaac, Jacob & Esau",
        "text": "What new name did God give Jacob after he wrestled with a divine being?",
        "type": "multiple_choice",
        "options": [
            {"text": "Abraham", "is_correct": False},
            {"text": "Israel", "is_correct": True},
            {"text": "Judah", "is_correct": False},
            {"text": "Benjamin", "is_correct": False}
        ]
    },
    # ===========================================
    # CATEGORY: Joseph's Story (12 questions)
    # ===========================================
    {
        "category": "Joseph's Story",
        "text": "What special gift did Jacob give Joseph that made his brothers jealous?",
        "type": "multiple_choice",
        "options": [
            {"text": "A gold ring", "is_correct": False},
            {"text": "A coat of many colors", "is_correct": True},
            {"text": "A flock of sheep", "is_correct": False},
            {"text": "The birthright", "is_correct": False}
        ]
    },
    {
        "category": "Joseph's Story",
        "text": "In Joseph's first dream, what did his brothers' sheaves do to his sheaf?",
        "type": "multiple_choice",
        "options": [
            {"text": "Burned it", "is_correct": False},
            {"text": "Bowed down to it", "is_correct": True},
            {"text": "Destroyed it", "is_correct": False},
            {"text": "Surrounded it", "is_correct": False}
        ]
    },
    {
        "category": "Joseph's Story",
        "text": "What did Joseph's brothers do to him out of jealousy?",
        "type": "multiple_choice",
        "options": [
            {"text": "Killed him", "is_correct": False},
            {"text": "Sold him into slavery", "is_correct": True},
            {"text": "Banished him to the wilderness", "is_correct": False},
            {"text": "Imprisoned him", "is_correct": False}
        ]
    },
    {
        "category": "Joseph's Story",
        "text": "For how many pieces of silver was Joseph sold?",
        "type": "multiple_choice",
        "options": [
            {"text": "10", "is_correct": False},
            {"text": "20", "is_correct": True},
            {"text": "30", "is_correct": False},
            {"text": "40", "is_correct": False}
        ]
    },
    {
        "category": "Joseph's Story",
        "text": "In whose house did Joseph serve as a slave in Egypt?",
        "type": "multiple_choice",
        "options": [
            {"text": "Pharaoh's palace", "is_correct": False},
            {"text": "Potiphar's house", "is_correct": True},
            {"text": "The prison warden's house", "is_correct": False},
            {"text": "The temple of Ra", "is_correct": False}
        ]
    },
    {
        "category": "Joseph's Story",
        "text": "Why was Joseph thrown into prison in Egypt?",
        "type": "multiple_choice",
        "options": [
            {"text": "For stealing", "is_correct": False},
            {"text": "For false accusations by Potiphar's wife", "is_correct": True},
            {"text": "For trying to escape", "is_correct": False},
            {"text": "For practicing magic", "is_correct": False}
        ]
    },
    {
        "category": "Joseph's Story",
        "text": "Whose dreams did Joseph interpret while in prison?",
        "type": "multiple_choice",
        "options": [
            {"text": "Pharaoh's servants", "is_correct": False},
            {"text": "The chief cupbearer and chief baker", "is_correct": True},
            {"text": "The prison guards", "is_correct": False},
            {"text": "Fellow prisoners", "is_correct": False}
        ]
    },
    {
        "category": "Joseph's Story",
        "text": "What ability did Joseph have that brought him before Pharaoh?",
        "type": "multiple_choice",
        "options": [
            {"text": "Ability to fight", "is_correct": False},
            {"text": "Ability to interpret dreams", "is_correct": True},
            {"text": "Ability to build", "is_correct": False},
            {"text": "Ability to heal", "is_correct": False}
        ]
    },
    {
        "category": "Joseph's Story",
        "text": "In Pharaoh's dream, what did the seven thin cows do to the seven fat cows?",
        "type": "multiple_choice",
        "options": [
            {"text": "Chased them away", "is_correct": False},
            {"text": "Ate them", "is_correct": True},
            {"text": "Followed them", "is_correct": False},
            {"text": "Ignored them", "is_correct": False}
        ]
    },
    {
        "category": "Joseph's Story",
        "text": "What position did Pharaoh give Joseph after he interpreted his dreams?",
        "type": "multiple_choice",
        "options": [
            {"text": "Chief baker", "is_correct": False},
            {"text": "Captain of the guard", "is_correct": False},
            {"text": "Second in command over all Egypt", "is_correct": True},
            {"text": "Royal scribe", "is_correct": False}
        ]
    },
    {
        "category": "Joseph's Story",
        "text": "How many years of famine did Joseph predict through Pharaoh's dreams?",
        "type": "multiple_choice",
        "options": [
            {"text": "3 years", "is_correct": False},
            {"text": "7 years", "is_correct": True},
            {"text": "10 years", "is_correct": False},
            {"text": "40 years", "is_correct": False}
        ]
    },
    {
        "category": "Joseph's Story",
        "text": "Which brother did Joseph keep as a hostage until the others brought Benjamin to Egypt?",
        "type": "multiple_choice",
        "options": [
            {"text": "Reuben", "is_correct": False},
            {"text": "Simeon", "is_correct": True},
            {"text": "Judah", "is_correct": False},
            {"text": "Levi", "is_correct": False}
        ]
    },
    # ===========================================
    # CATEGORY: Key Themes & Chapter Locations (8 questions)
    # ===========================================
    {
        "category": "Key Themes & Chapter Locations",
        "text": "In which chapter of Genesis do we find the account of Creation?",
        "type": "multiple_choice",
        "options": [
            {"text": "Genesis 1", "is_correct": True},
            {"text": "Genesis 3", "is_correct": False},
            {"text": "Genesis 6", "is_correct": False},
            {"text": "Genesis 12", "is_correct": False}
        ]
    },
    {
        "category": "Key Themes & Chapter Locations",
        "text": "In which chapter does the account of Noah and the flood begin?",
        "type": "multiple_choice",
        "options": [
            {"text": "Genesis 3", "is_correct": False},
            {"text": "Genesis 6", "is_correct": True},
            {"text": "Genesis 11", "is_correct": False},
            {"text": "Genesis 15", "is_correct": False}
        ]
    },
    {
        "category": "Key Themes & Chapter Locations",
        "text": "In which chapter does God make His covenant with Abraham, promising him descendants as numerous as the stars?",
        "type": "multiple_choice",
        "options": [
            {"text": "Genesis 1", "is_correct": False},
            {"text": "Genesis 12", "is_correct": False},
            {"text": "Genesis 15", "is_correct": True},
            {"text": "Genesis 22", "is_correct": False}
        ]
    },
    {
        "category": "Key Themes & Chapter Locations",
        "text": "How many sons did Jacob have who became the twelve tribes of Israel?",
        "type": "multiple_choice",
        "options": [
            {"text": "10", "is_correct": False},
            {"text": "12", "is_correct": True},
            {"text": "13", "is_correct": False},
            {"text": "7", "is_correct": False}
        ]
    },
    {
        "category": "Key Themes & Chapter Locations",
        "text": "What is the main theme of the Joseph narrative in Genesis?",
        "type": "multiple_choice",
        "options": [
            {"text": "Military conquest", "is_correct": False},
            {"text": "God's sovereignty and providence through suffering", "is_correct": True},
            {"text": "The importance of wealth", "is_correct": False},
            {"text": "The power of dreams alone", "is_correct": False}
        ]
    },
    {
        "category": "Key Themes & Chapter Locations",
        "text": "Which son of Jacob received the blessing of the 'scepter' that would lead to the line of kings (and ultimately the Messiah)?",
        "type": "multiple_choice",
        "options": [
            {"text": "Joseph", "is_correct": False},
            {"text": "Reuben", "is_correct": False},
            {"text": "Judah", "is_correct": True},
            {"text": "Benjamin", "is_correct": False}
        ]
    },
    {
        "category": "Key Themes & Chapter Locations",
        "text": "Who was the oldest of Jacob's twelve sons?",
        "type": "multiple_choice",
        "options": [
            {"text": "Judah", "is_correct": False},
            {"text": "Joseph", "is_correct": False},
            {"text": "Reuben", "is_correct": True},
            {"text": "Simeon", "is_correct": False}
        ]
    },
    {
        "category": "Key Themes & Chapter Locations",
        "text": "Where did Jacob and his family settle in Egypt?",
        "type": "multiple_choice",
        "options": [
            {"text": "Cairo", "is_correct": False},
            {"text": "Goshen", "is_correct": True},
            {"text": "Memphis", "is_correct": False},
            {"text": "Thebes", "is_correct": False}
        ]
    },
]

def main():
    print("=" * 60)
    print("Book of Genesis Assessment Setup")
    print("=" * 60)
    print(f"Assessment: {ASSESSMENT_NAME}")
    print(f"Key: {ASSESSMENT_KEY}")
    print(f"Total Questions: {len(QUESTIONS_DATA)}")
    print("=" * 60)
    
    with engine.connect() as conn:
        # Start transaction
        trans = conn.begin()
        
        try:
            # Check if assessment already exists
            result = conn.execute(text("""
                SELECT id FROM assessment_templates WHERE key = :key
            """), {"key": ASSESSMENT_KEY})
            existing = result.fetchone()
            
            if existing:
                template_id = existing[0]
                print(f"⚠️  Assessment already exists with ID: {template_id}")
                
                # Check if it has questions
                result = conn.execute(text("""
                    SELECT COUNT(*) FROM assessment_template_questions 
                    WHERE template_id = :template_id
                """), {"template_id": template_id})
                question_count = result.fetchone()[0]
                
                if question_count > 0:
                    print(f"   Assessment already has {question_count} questions. Skipping...")
                    trans.rollback()
                    return
                else:
                    print("   Assessment has no questions. Populating...")
            else:
                # Create the assessment template
                template_id = str(uuid.uuid4())
                conn.execute(text("""
                    INSERT INTO assessment_templates (
                        id, name, description, is_published, is_master_assessment, created_at,
                        key, version, scoring_strategy
                    )
                    VALUES (
                        :id, :name, :description, :is_published, :is_master_assessment, NOW(),
                        :key, :version, :scoring_strategy
                    )
                """), {
                    "id": template_id,
                    "name": ASSESSMENT_NAME,
                    "description": ASSESSMENT_DESCRIPTION,
                    "is_published": True,
                    "is_master_assessment": True,  # Make it globally visible to all users
                    "key": ASSESSMENT_KEY,
                    "version": 1,
                    "scoring_strategy": "percentage"  # Simple percentage scoring for MC-only
                })
                print(f"✅ Created Genesis Assessment template: {template_id}")
            
            # Get or create categories
            categories = {}
            category_names = list(set(q["category"] for q in QUESTIONS_DATA))
            
            for cat_name in category_names:
                result = conn.execute(text("""
                    SELECT id FROM categories WHERE name = :name
                """), {"name": cat_name})
                existing_cat = result.fetchone()
                
                if existing_cat:
                    categories[cat_name] = existing_cat[0]
                    print(f"   Found existing category: {cat_name}")
                else:
                    cat_id = str(uuid.uuid4())
                    conn.execute(text("""
                        INSERT INTO categories (id, name)
                        VALUES (:id, :name)
                    """), {
                        "id": cat_id,
                        "name": cat_name
                    })
                    categories[cat_name] = cat_id
                    print(f"✅ Created category: {cat_name}")
            
            # Create questions and link to template
            question_order = 0
            for q_data in QUESTIONS_DATA:
                question_order += 1
                question_id = str(uuid.uuid4())
                category_id = categories[q_data["category"]]
                
                # Generate question code
                question_code = f"GEN_{question_order:03d}"
                
                # Insert question
                conn.execute(text("""
                    INSERT INTO questions (
                        id, text, question_type, category_id, question_code
                    )
                    VALUES (
                        :id, :text, :question_type, :category_id, :question_code
                    )
                """), {
                    "id": question_id,
                    "text": q_data["text"],
                    "question_type": q_data["type"],
                    "category_id": category_id,
                    "question_code": question_code
                })
                
                # Insert options
                for idx, opt in enumerate(q_data["options"]):
                    option_id = str(uuid.uuid4())
                    conn.execute(text("""
                        INSERT INTO question_options (
                            id, question_id, option_text, is_correct, "order"
                        )
                        VALUES (
                            :id, :question_id, :option_text, :is_correct, :order
                        )
                    """), {
                        "id": option_id,
                        "question_id": question_id,
                        "option_text": opt["text"],
                        "is_correct": opt["is_correct"],
                        "order": idx
                    })
                
                # Link question to template
                link_id = str(uuid.uuid4())
                conn.execute(text("""
                    INSERT INTO assessment_template_questions (
                        id, template_id, question_id, "order"
                    )
                    VALUES (
                        :id, :template_id, :question_id, :order
                    )
                """), {
                    "id": link_id,
                    "template_id": template_id,
                    "question_id": question_id,
                    "order": question_order
                })
                
                if question_order % 10 == 0:
                    print(f"   Created {question_order} questions...")
            
            # Commit transaction
            trans.commit()
            
            print("=" * 60)
            print(f"✅ SUCCESS! Created Book of Genesis Assessment")
            print(f"   Template ID: {template_id}")
            print(f"   Total Questions: {question_order}")
            print(f"   Categories: {len(categories)}")
            print("=" * 60)
            
        except Exception as e:
            trans.rollback()
            print(f"❌ ERROR: {e}")
            raise

if __name__ == "__main__":
    main()
