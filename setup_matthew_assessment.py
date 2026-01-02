"""
Script to create the Book of Matthew Bible Knowledge Assessment
Run as: python setup_matthew_assessment.py
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
ASSESSMENT_KEY = "matthew_bible_v1"
ASSESSMENT_NAME = "Book of Matthew Assessment"
ASSESSMENT_DESCRIPTION = """Test your knowledge of the Gospel of Matthew. This assessment covers key events, teachings of Jesus, parables, and themes from Matthew's account of Jesus' life, death, and resurrection. 35 multiple choice questions across 5 categories: Narrative Events, Teachings of Jesus, Key Characters, Themes & Purpose, and Chapter Locations."""

# Questions organized by category
QUESTIONS_DATA = [
    # ===========================================
    # CATEGORY: Narrative Events (10 questions)
    # ===========================================
    {
        "category": "Narrative Events",
        "text": "Who visited Jesus after his birth, following a star?",
        "type": "multiple_choice",
        "options": [
            {"text": "Shepherds", "is_correct": False},
            {"text": "Wise men (Magi)", "is_correct": True},
            {"text": "Angels", "is_correct": False},
            {"text": "John the Baptist", "is_correct": False}
        ]
    },
    {
        "category": "Narrative Events",
        "text": "Where did Joseph take Mary and Jesus to escape King Herod?",
        "type": "multiple_choice",
        "options": [
            {"text": "Nazareth", "is_correct": False},
            {"text": "Bethlehem", "is_correct": False},
            {"text": "Egypt", "is_correct": True},
            {"text": "Jerusalem", "is_correct": False}
        ]
    },
    {
        "category": "Narrative Events",
        "text": "Who baptized Jesus in the Jordan River?",
        "type": "multiple_choice",
        "options": [
            {"text": "Peter", "is_correct": False},
            {"text": "John the Baptist", "is_correct": True},
            {"text": "Andrew", "is_correct": False},
            {"text": "James", "is_correct": False}
        ]
    },
    {
        "category": "Narrative Events",
        "text": "How many days did Jesus fast in the wilderness before being tempted by the devil?",
        "type": "multiple_choice",
        "options": [
            {"text": "7 days", "is_correct": False},
            {"text": "21 days", "is_correct": False},
            {"text": "40 days", "is_correct": True},
            {"text": "12 days", "is_correct": False}
        ]
    },
    {
        "category": "Narrative Events",
        "text": "When Jesus walked on water, which disciple also walked on water before sinking?",
        "type": "multiple_choice",
        "options": [
            {"text": "John", "is_correct": False},
            {"text": "James", "is_correct": False},
            {"text": "Peter", "is_correct": True},
            {"text": "Andrew", "is_correct": False}
        ]
    },
    {
        "category": "Narrative Events",
        "text": "At the Transfiguration, which two Old Testament figures appeared with Jesus?",
        "type": "multiple_choice",
        "options": [
            {"text": "Abraham and Isaac", "is_correct": False},
            {"text": "Moses and Elijah", "is_correct": True},
            {"text": "David and Solomon", "is_correct": False},
            {"text": "Isaiah and Jeremiah", "is_correct": False}
        ]
    },
    {
        "category": "Narrative Events",
        "text": "What did Judas receive for betraying Jesus?",
        "type": "multiple_choice",
        "options": [
            {"text": "20 pieces of silver", "is_correct": False},
            {"text": "30 pieces of silver", "is_correct": True},
            {"text": "50 pieces of gold", "is_correct": False},
            {"text": "A position of power", "is_correct": False}
        ]
    },
    {
        "category": "Narrative Events",
        "text": "Who asked Pilate for permission to bury Jesus' body?",
        "type": "multiple_choice",
        "options": [
            {"text": "Peter", "is_correct": False},
            {"text": "Nicodemus", "is_correct": False},
            {"text": "Joseph of Arimathea", "is_correct": True},
            {"text": "John", "is_correct": False}
        ]
    },
    {
        "category": "Narrative Events",
        "text": "What happened when Jesus died on the cross?",
        "type": "multiple_choice",
        "options": [
            {"text": "The sky turned red", "is_correct": False},
            {"text": "The temple curtain was torn in two", "is_correct": True},
            {"text": "Fire came down from heaven", "is_correct": False},
            {"text": "The Roman soldiers converted immediately", "is_correct": False}
        ]
    },
    {
        "category": "Narrative Events",
        "text": "Who were the first people to see the risen Jesus according to Matthew?",
        "type": "multiple_choice",
        "options": [
            {"text": "Peter and John", "is_correct": False},
            {"text": "The eleven disciples", "is_correct": False},
            {"text": "Mary Magdalene and the other Mary", "is_correct": True},
            {"text": "The Roman guards", "is_correct": False}
        ]
    },
    
    # ===========================================
    # CATEGORY: Teachings of Jesus (10 questions)
    # ===========================================
    {
        "category": "Teachings of Jesus",
        "text": "Where did Jesus deliver the Sermon on the Mount?",
        "type": "multiple_choice",
        "options": [
            {"text": "In the temple", "is_correct": False},
            {"text": "On a mountainside", "is_correct": True},
            {"text": "By the Sea of Galilee", "is_correct": False},
            {"text": "In a synagogue", "is_correct": False}
        ]
    },
    {
        "category": "Teachings of Jesus",
        "text": "In the Beatitudes, who does Jesus say will 'inherit the earth'?",
        "type": "multiple_choice",
        "options": [
            {"text": "The poor in spirit", "is_correct": False},
            {"text": "Those who mourn", "is_correct": False},
            {"text": "The meek", "is_correct": True},
            {"text": "The peacemakers", "is_correct": False}
        ]
    },
    {
        "category": "Teachings of Jesus",
        "text": "What did Jesus say are the two greatest commandments?",
        "type": "multiple_choice",
        "options": [
            {"text": "Do not murder; do not steal", "is_correct": False},
            {"text": "Love God; love your neighbor", "is_correct": True},
            {"text": "Honor your parents; keep the Sabbath", "is_correct": False},
            {"text": "Do not lie; do not covet", "is_correct": False}
        ]
    },
    {
        "category": "Teachings of Jesus",
        "text": "In the parable of the sower, what does the seed that falls among thorns represent?",
        "type": "multiple_choice",
        "options": [
            {"text": "Those who hear but don't understand", "is_correct": False},
            {"text": "Those who fall away when trouble comes", "is_correct": False},
            {"text": "Those choked by worries and wealth", "is_correct": True},
            {"text": "Those who produce a great harvest", "is_correct": False}
        ]
    },
    {
        "category": "Teachings of Jesus",
        "text": "What did Jesus say about those who practice their righteousness to be seen by others?",
        "type": "multiple_choice",
        "options": [
            {"text": "They will be rewarded twice", "is_correct": False},
            {"text": "They have already received their reward", "is_correct": True},
            {"text": "They will be forgiven", "is_correct": False},
            {"text": "They are greater in the kingdom", "is_correct": False}
        ]
    },
    {
        "category": "Teachings of Jesus",
        "text": "In the Lord's Prayer, what does Jesus teach us to ask for 'daily'?",
        "type": "multiple_choice",
        "options": [
            {"text": "Wisdom", "is_correct": False},
            {"text": "Bread", "is_correct": True},
            {"text": "Protection", "is_correct": False},
            {"text": "Forgiveness", "is_correct": False}
        ]
    },
    {
        "category": "Teachings of Jesus",
        "text": "In the parable of the talents, how many talents did the master give to the first servant?",
        "type": "multiple_choice",
        "options": [
            {"text": "1", "is_correct": False},
            {"text": "2", "is_correct": False},
            {"text": "5", "is_correct": True},
            {"text": "10", "is_correct": False}
        ]
    },
    {
        "category": "Teachings of Jesus",
        "text": "In the parable of the sheep and goats, what determines who enters the kingdom?",
        "type": "multiple_choice",
        "options": [
            {"text": "How much Scripture they memorized", "is_correct": False},
            {"text": "How they treated 'the least of these'", "is_correct": True},
            {"text": "How often they attended the temple", "is_correct": False},
            {"text": "Whether they were born Jewish", "is_correct": False}
        ]
    },
    {
        "category": "Teachings of Jesus",
        "text": "Jesus said, 'You are the salt of the earth.' What did He say happens if salt loses its saltiness?",
        "type": "multiple_choice",
        "options": [
            {"text": "It becomes sweet", "is_correct": False},
            {"text": "It is thrown out and trampled", "is_correct": True},
            {"text": "It can be restored by prayer", "is_correct": False},
            {"text": "It turns into water", "is_correct": False}
        ]
    },
    {
        "category": "Teachings of Jesus",
        "text": "What is the final command Jesus gives in Matthew (the Great Commission)?",
        "type": "multiple_choice",
        "options": [
            {"text": "Feed my sheep", "is_correct": False},
            {"text": "Wait in Jerusalem for the Holy Spirit", "is_correct": False},
            {"text": "Go and make disciples of all nations", "is_correct": True},
            {"text": "Sell all you have and give to the poor", "is_correct": False}
        ]
    },
    
    # ===========================================
    # CATEGORY: Key Characters (5 questions)
    # ===========================================
    {
        "category": "Key Characters",
        "text": "How many disciples did Jesus call?",
        "type": "multiple_choice",
        "options": [
            {"text": "7", "is_correct": False},
            {"text": "10", "is_correct": False},
            {"text": "12", "is_correct": True},
            {"text": "70", "is_correct": False}
        ]
    },
    {
        "category": "Key Characters",
        "text": "What reason did Herod give for wanting to know where the child Jesus was?",
        "type": "multiple_choice",
        "options": [
            {"text": "To warn Joseph of danger", "is_correct": False},
            {"text": "To worship him", "is_correct": True},
            {"text": "To register him for the census", "is_correct": False},
            {"text": "To present him at the temple", "is_correct": False}
        ]
    },
    {
        "category": "Key Characters",
        "text": "What was the reaction of the religious leaders when Jesus healed on the Sabbath?",
        "type": "multiple_choice",
        "options": [
            {"text": "They praised God", "is_correct": False},
            {"text": "They plotted to kill him", "is_correct": True},
            {"text": "They became his followers", "is_correct": False},
            {"text": "They ignored him", "is_correct": False}
        ]
    },
    {
        "category": "Key Characters",
        "text": "In Matthew 16, what had Peter just declared when Jesus said 'on this rock I will build my church'?",
        "type": "multiple_choice",
        "options": [
            {"text": "That he would never deny Jesus", "is_correct": False},
            {"text": "That Jesus is the Christ, the Son of the living God", "is_correct": True},
            {"text": "That he would follow Jesus anywhere", "is_correct": False},
            {"text": "That the disciples should go to Jerusalem", "is_correct": False}
        ]
    },
    {
        "category": "Key Characters",
        "text": "Who did Pilate release instead of Jesus at the crowd's request?",
        "type": "multiple_choice",
        "options": [
            {"text": "Judas Iscariot", "is_correct": False},
            {"text": "Barabbas", "is_correct": True},
            {"text": "Simon of Cyrene", "is_correct": False},
            {"text": "Joseph of Arimathea", "is_correct": False}
        ]
    },
    
    # ===========================================
    # CATEGORY: Themes & Purpose (5 questions)
    # ===========================================
    {
        "category": "Themes & Purpose",
        "text": "Why does Matthew repeatedly use the phrase 'This was to fulfill what was spoken by the prophet'?",
        "type": "multiple_choice",
        "options": [
            {"text": "To show Jesus came unexpectedly", "is_correct": False},
            {"text": "To prove Jesus is the promised Messiah", "is_correct": True},
            {"text": "To criticize the Old Testament prophets", "is_correct": False},
            {"text": "To explain why Jesus rejected Jewish customs", "is_correct": False}
        ]
    },
    {
        "category": "Themes & Purpose",
        "text": "In Matthew's genealogy, how many generations are listed from Abraham to David, from David to the exile, and from the exile to Christ?",
        "type": "multiple_choice",
        "options": [
            {"text": "14, 14, 14", "is_correct": True},
            {"text": "12, 12, 12", "is_correct": False},
            {"text": "10, 14, 14", "is_correct": False},
            {"text": "7, 7, 7", "is_correct": False}
        ]
    },
    {
        "category": "Themes & Purpose",
        "text": "What phrase does Matthew use more than any other Gospel to describe God's reign?",
        "type": "multiple_choice",
        "options": [
            {"text": "Kingdom of God", "is_correct": False},
            {"text": "Kingdom of Heaven", "is_correct": True},
            {"text": "Reign of Christ", "is_correct": False},
            {"text": "Eternal Kingdom", "is_correct": False}
        ]
    },
    {
        "category": "Themes & Purpose",
        "text": "Which of these events is NOT found in Matthew's Gospel?",
        "type": "multiple_choice",
        "options": [
            {"text": "The visit of the Magi", "is_correct": False},
            {"text": "The flight to Egypt", "is_correct": False},
            {"text": "The shepherds visiting the manger", "is_correct": True},
            {"text": "Herod killing the infants", "is_correct": False}
        ]
    },
    {
        "category": "Themes & Purpose",
        "text": "Matthew was written primarily for which audience?",
        "type": "multiple_choice",
        "options": [
            {"text": "Roman officials", "is_correct": False},
            {"text": "Jewish readers", "is_correct": True},
            {"text": "Greek philosophers", "is_correct": False},
            {"text": "Egyptian converts", "is_correct": False}
        ]
    },
    
    # ===========================================
    # CATEGORY: Chapter Locations (5 questions)
    # ===========================================
    {
        "category": "Chapter Locations",
        "text": "In which chapter of Matthew do we find the Beatitudes?",
        "type": "multiple_choice",
        "options": [
            {"text": "Matthew 3", "is_correct": False},
            {"text": "Matthew 5", "is_correct": True},
            {"text": "Matthew 10", "is_correct": False},
            {"text": "Matthew 13", "is_correct": False}
        ]
    },
    {
        "category": "Chapter Locations",
        "text": "The Lord's Prayer is found in which chapter?",
        "type": "multiple_choice",
        "options": [
            {"text": "Matthew 4", "is_correct": False},
            {"text": "Matthew 6", "is_correct": True},
            {"text": "Matthew 9", "is_correct": False},
            {"text": "Matthew 11", "is_correct": False}
        ]
    },
    {
        "category": "Chapter Locations",
        "text": "Matthew 13 is known for containing many of Jesus' what?",
        "type": "multiple_choice",
        "options": [
            {"text": "Miracles", "is_correct": False},
            {"text": "Parables", "is_correct": True},
            {"text": "Prophecies", "is_correct": False},
            {"text": "Prayers", "is_correct": False}
        ]
    },
    {
        "category": "Chapter Locations",
        "text": "The Great Commission is found in which chapter?",
        "type": "multiple_choice",
        "options": [
            {"text": "Matthew 24", "is_correct": False},
            {"text": "Matthew 26", "is_correct": False},
            {"text": "Matthew 27", "is_correct": False},
            {"text": "Matthew 28", "is_correct": True}
        ]
    },
    {
        "category": "Chapter Locations",
        "text": "Jesus' teaching about the sheep and the goats judgment is found in which chapter?",
        "type": "multiple_choice",
        "options": [
            {"text": "Matthew 20", "is_correct": False},
            {"text": "Matthew 23", "is_correct": False},
            {"text": "Matthew 25", "is_correct": True},
            {"text": "Matthew 27", "is_correct": False}
        ]
    },
]


def create_matthew_assessment():
    """Create the Book of Matthew Assessment template and populate with questions"""
    
    with engine.begin() as conn:
        # Check if assessment already exists
        result = conn.execute(text("""
            SELECT id FROM assessment_templates 
            WHERE key = :key
        """), {"key": ASSESSMENT_KEY})
        existing = result.fetchone()
        
        if existing:
            print(f"⚠️  Matthew Assessment already exists with ID: {existing[0]}")
            
            # Check if it has questions
            q_count = conn.execute(text("""
                SELECT COUNT(*) FROM assessment_template_questions 
                WHERE template_id = :template_id
            """), {"template_id": existing[0]}).scalar()
            
            if q_count > 0:
                print(f"   Assessment has {q_count} questions. Skipping.")
                return existing[0]
            else:
                print("   Assessment has no questions. Populating...")
                template_id = existing[0]
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
            print(f"✅ Created Matthew Assessment template: {template_id}")
        
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
            else:
                cat_id = str(uuid.uuid4())
                conn.execute(text("""
                    INSERT INTO categories (id, name) VALUES (:id, :name)
                """), {"id": cat_id, "name": cat_name})
                categories[cat_name] = cat_id
                print(f"➕ Created category: {cat_name}")
        
        # Insert questions
        question_order = 1
        for q_data in QUESTIONS_DATA:
            question_id = str(uuid.uuid4())
            category_id = categories[q_data["category"]]
            question_code = f"MATT_{question_order:03d}"
            
            # Insert question
            conn.execute(text("""
                INSERT INTO questions (id, text, question_type, category_id, question_code)
                VALUES (:id, :text, :question_type, :category_id, :question_code)
            """), {
                "id": question_id,
                "text": q_data["text"],
                "question_type": "multiple_choice",
                "category_id": category_id,
                "question_code": question_code
            })
            
            # Insert options
            for i, option in enumerate(q_data["options"]):
                option_id = str(uuid.uuid4())
                conn.execute(text("""
                    INSERT INTO question_options (id, question_id, option_text, is_correct, "order")
                    VALUES (:id, :question_id, :option_text, :is_correct, :order)
                """), {
                    "id": option_id,
                    "question_id": question_id,
                    "option_text": option["text"],
                    "is_correct": option["is_correct"],
                    "order": i + 1
                })
            
            # Link question to template
            tq_id = str(uuid.uuid4())
            conn.execute(text("""
                INSERT INTO assessment_template_questions (id, template_id, question_id, "order")
                VALUES (:id, :template_id, :question_id, :order)
            """), {
                "id": tq_id,
                "template_id": template_id,
                "question_id": question_id,
                "order": question_order
            })
            
            print(f"✅ [{question_order:02d}] {q_data['text'][:55]}...")
            question_order += 1
        
        print(f"\n🎉 Successfully created Matthew Assessment with {len(QUESTIONS_DATA)} questions!")
        print(f"   Template ID: {template_id}")
        print(f"   Key: {ASSESSMENT_KEY}")
        
        # Print category breakdown
        print("\n📊 Questions by Category:")
        for cat_name in category_names:
            count = sum(1 for q in QUESTIONS_DATA if q["category"] == cat_name)
            print(f"   • {cat_name}: {count} questions")
        
        return template_id


if __name__ == "__main__":
    result = create_matthew_assessment()
    print(f"\n✅ Done! Assessment ID: {result}")
