"""
Script to create the Gospel of John Assessment
Run as: python setup_john_gospel_assessment.py
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
ASSESSMENT_KEY = "john_gospel_v1"
ASSESSMENT_NAME = "The Gospel of John"
ASSESSMENT_DESCRIPTION = """Explore the Gospel of John — the beloved disciple's testimony that Jesus is the Christ, the Son of God. This assessment covers the Word made flesh, the seven signs, the "I AM" statements, belief and unbelief, the cross as glory, the Holy Spirit, and abiding in Christ. Gospel-centered open-ended questions help you encounter Jesus and believe. 25 questions (15 multiple choice, 10 open-ended) across 7 categories."""

# Questions organized by category
# NOTE: Correct answers are distributed across positions A, B, C, D
QUESTIONS_DATA = [
    # ===========================================
    # CATEGORY: The Word Made Flesh — Who Jesus Is (4 questions: 2 MC, 2 OE)
    # ===========================================
    {
        "category": "The Word Made Flesh — Who Jesus Is",
        "text": "John's Gospel opens with 'In the beginning was the Word, and the Word was with God, and the Word was God' (John 1:1). This teaches that Jesus:",
        "type": "multiple_choice",
        "options": [
            {"text": "Was created by God as the first and greatest being", "is_correct": False},
            {"text": "Is eternal, distinct from the Father, yet fully God Himself", "is_correct": True},  # B - CORRECT
            {"text": "Became divine when He was baptized", "is_correct": False},
            {"text": "Is merely a symbol or idea, not a real person", "is_correct": False}
        ]
    },
    {
        "category": "The Word Made Flesh — Who Jesus Is",
        "text": "'The Word became flesh and made his dwelling among us' (John 1:14). The word 'dwelling' (Greek: tabernacled) connects Jesus to:",
        "type": "multiple_choice",
        "options": [
            {"text": "The permanent temple Solomon built", "is_correct": False},
            {"text": "The tabernacle where God's glory dwelt among Israel in the wilderness", "is_correct": True},  # B - CORRECT
            {"text": "The synagogues where Jews gathered to worship", "is_correct": False},
            {"text": "The homes of the disciples", "is_correct": False}
        ]
    },
    {
        "category": "The Word Made Flesh — Who Jesus Is",
        "text": "John says Jesus is the eternal Word who was with God and was God — and this Word 'became flesh' and moved into the neighborhood. How does the incarnation (God becoming human) change how you understand God's love for you? What does it mean that God didn't just send a message — He came Himself?",
        "type": "open_ended",
        "options": []
    },
    {
        "category": "The Word Made Flesh — Who Jesus Is",
        "text": "John 1:14 says we have 'seen his glory.' The disciples saw Jesus — ate with Him, walked with Him, watched Him die and rise. We haven't seen Him physically, yet Jesus said, 'Blessed are those who have not seen and yet have believed' (John 20:29). How do you 'see' Jesus' glory today? What has made Him real to you?",
        "type": "open_ended",
        "options": []
    },
    # ===========================================
    # CATEGORY: The Seven Signs — Revealing Glory (3 questions: 2 MC, 1 OE)
    # ===========================================
    {
        "category": "The Seven Signs — Revealing Glory",
        "text": "Jesus' first sign — turning water into wine at Cana — revealed His glory because:",
        "type": "multiple_choice",
        "options": [
            {"text": "It showed He could provide entertainment at parties", "is_correct": False},
            {"text": "It proved He was a skilled magician", "is_correct": False},
            {"text": "It demonstrated His divine power and pointed to the abundant joy of the coming Kingdom", "is_correct": True},  # C - CORRECT
            {"text": "It was meant to embarrass the host", "is_correct": False}
        ]
    },
    {
        "category": "The Seven Signs — Revealing Glory",
        "text": "The raising of Lazarus (John 11) was the climax of Jesus' signs. Before raising him, Jesus declared:",
        "type": "multiple_choice",
        "options": [
            {"text": "'I am the resurrection and the life. Whoever believes in me will live, even though they die'", "is_correct": True},  # A - CORRECT
            {"text": "'Lazarus was not really dead, only sleeping'", "is_correct": False},
            {"text": "'This miracle will prove I am greater than the prophets'", "is_correct": False},
            {"text": "'Death has no power because the body doesn't matter'", "is_correct": False}
        ]
    },
    {
        "category": "The Seven Signs — Revealing Glory",
        "text": "Jesus' signs weren't just miracles — they were windows into who He is. He turned water to wine (joy), healed the sick (restoration), fed thousands (provision), raised the dead (life). Which of Jesus' signs speaks most to your current situation? What is He revealing about Himself to you right now?",
        "type": "open_ended",
        "options": []
    },
    # ===========================================
    # CATEGORY: The "I AM" Statements — Jesus' Identity (4 questions: 3 MC, 1 OE)
    # ===========================================
    {
        "category": "The 'I AM' Statements — Jesus' Identity",
        "text": "When Jesus said 'I AM' (Greek: ego eimi), He was echoing:",
        "type": "multiple_choice",
        "options": [
            {"text": "A common greeting in first-century Judaism", "is_correct": False},
            {"text": "God's self-revelation to Moses at the burning bush: 'I AM WHO I AM'", "is_correct": True},  # B - CORRECT
            {"text": "A title used by Roman emperors", "is_correct": False},
            {"text": "The name of a famous rabbi", "is_correct": False}
        ]
    },
    {
        "category": "The 'I AM' Statements — Jesus' Identity",
        "text": "Jesus said, 'I am the way, the truth, and the life. No one comes to the Father except through me' (John 14:6). This claim:",
        "type": "multiple_choice",
        "options": [
            {"text": "Was just one option among many paths to God", "is_correct": False},
            {"text": "Applied only to Jewish believers", "is_correct": False},
            {"text": "Is an exclusive claim — Jesus is the only way to the Father", "is_correct": True},  # C - CORRECT
            {"text": "Was later changed by the apostles to be more inclusive", "is_correct": False}
        ]
    },
    {
        "category": "The 'I AM' Statements — Jesus' Identity",
        "text": "Jesus declared, 'I am the good shepherd. The good shepherd lays down his life for the sheep' (John 10:11). Unlike hired hands who run from danger:",
        "type": "multiple_choice",
        "options": [
            {"text": "Jesus fights wolves with supernatural power", "is_correct": False},
            {"text": "Jesus voluntarily dies to protect His sheep — He gives His life for them", "is_correct": True},  # B - CORRECT
            {"text": "Jesus teaches the sheep to defend themselves", "is_correct": False},
            {"text": "Jesus delegates protection to the disciples", "is_correct": False}
        ]
    },
    {
        "category": "The 'I AM' Statements — Jesus' Identity",
        "text": "Jesus made seven 'I AM' statements: Bread of Life, Light of the World, Gate, Good Shepherd, Resurrection and Life, Way/Truth/Life, True Vine. Which of these names for Jesus means the most to you in this season? Why? How does that aspect of who He is meet your deepest need right now?",
        "type": "open_ended",
        "options": []
    },
    # ===========================================
    # CATEGORY: Belief & Unbelief — The Great Divide (4 questions: 2 MC, 2 OE)
    # ===========================================
    {
        "category": "Belief & Unbelief — The Great Divide",
        "text": "John 3:16 says, 'For God so loved the world that he gave his one and only Son, that whoever believes in him shall not perish but have eternal life.' The word 'believes' means:",
        "type": "multiple_choice",
        "options": [
            {"text": "Intellectual agreement that Jesus existed", "is_correct": False},
            {"text": "Trusting, relying on, and committing oneself to Jesus", "is_correct": True},  # B - CORRECT
            {"text": "Following a set of religious rules", "is_correct": False},
            {"text": "Being born into a Christian family", "is_correct": False}
        ]
    },
    {
        "category": "Belief & Unbelief — The Great Divide",
        "text": "Jesus told Nicodemus, 'No one can see the kingdom of God unless they are born again' (John 3:3). Being 'born again' means:",
        "type": "multiple_choice",
        "options": [
            {"text": "Physical rebirth through reincarnation", "is_correct": False},
            {"text": "Starting over with a clean moral slate through personal effort", "is_correct": False},
            {"text": "Spiritual rebirth by the Holy Spirit — a new life from above", "is_correct": True},  # C - CORRECT
            {"text": "Being baptized as an infant", "is_correct": False}
        ]
    },
    {
        "category": "Belief & Unbelief — The Great Divide",
        "text": "John wrote his Gospel 'that you may believe that Jesus is the Messiah, the Son of God, and that by believing you may have life in his name' (John 20:31). What brought you to believe in Jesus? Or if you're still exploring, what draws you toward Him? What barriers or doubts have you wrestled with?",
        "type": "open_ended",
        "options": []
    },
    {
        "category": "Belief & Unbelief — The Great Divide",
        "text": "Throughout John's Gospel, people respond to Jesus in radically different ways — some believe, some walk away, some become hostile. What causes people today to reject Jesus? What might be holding someone you know back from faith? What held you back before you believed?",
        "type": "open_ended",
        "options": []
    },
    # ===========================================
    # CATEGORY: The Hour Has Come — The Cross & Glory (4 questions: 2 MC, 2 OE)
    # ===========================================
    {
        "category": "The Hour Has Come — The Cross & Glory",
        "text": "Throughout John's Gospel, Jesus said 'My hour has not yet come' — until finally, facing the cross, He declared, 'The hour has come for the Son of Man to be glorified' (John 12:23). This shows that Jesus' death was:",
        "type": "multiple_choice",
        "options": [
            {"text": "An accident that caught Him by surprise", "is_correct": False},
            {"text": "A tragic defeat that the resurrection reversed", "is_correct": False},
            {"text": "The purposeful climax of His mission — His glory revealed through sacrifice", "is_correct": True},  # C - CORRECT
            {"text": "Something He could have avoided if He tried harder", "is_correct": False}
        ]
    },
    {
        "category": "The Hour Has Come — The Cross & Glory",
        "text": "On the cross, Jesus cried out 'It is finished' (John 19:30). The Greek word (tetelestai) means:",
        "type": "multiple_choice",
        "options": [
            {"text": "'My life is over'", "is_correct": False},
            {"text": "'Paid in full' — the debt of sin completely satisfied", "is_correct": True},  # B - CORRECT
            {"text": "'I give up'", "is_correct": False},
            {"text": "'The disciples will continue my work'", "is_correct": False}
        ]
    },
    {
        "category": "The Hour Has Come — The Cross & Glory",
        "text": "John shows Jesus in complete control — knowing all that would happen, laying down His life voluntarily, declaring 'It is finished.' Yet He also shows Jesus troubled in soul, weeping, loving His disciples 'to the end.' How does seeing both Jesus' divine sovereignty AND His human emotion affect how you relate to Him in your own suffering?",
        "type": "open_ended",
        "options": []
    },
    {
        "category": "The Hour Has Come — The Cross & Glory",
        "text": "'It is finished' — the work of salvation is complete. You can't add to it or earn it. How does this finished work free you from trying to earn God's approval? Where do you still act like you need to perform for God rather than resting in what Jesus accomplished?",
        "type": "open_ended",
        "options": []
    },
    # ===========================================
    # CATEGORY: The Holy Spirit — Another Helper (3 questions: 2 MC, 1 OE)
    # ===========================================
    {
        "category": "The Holy Spirit — Another Helper",
        "text": "Jesus promised the disciples, 'I will ask the Father, and he will give you another Helper, to be with you forever' (John 14:16). The Spirit is 'another' Helper because:",
        "type": "multiple_choice",
        "options": [
            {"text": "He replaces Jesus with a completely different kind of presence", "is_correct": False},
            {"text": "He continues Jesus' work — same nature, same mission, now dwelling within believers", "is_correct": True},  # B - CORRECT
            {"text": "He is a created being sent to assist humanity", "is_correct": False},
            {"text": "He only helps those who achieve spiritual maturity", "is_correct": False}
        ]
    },
    {
        "category": "The Holy Spirit — Another Helper",
        "text": "Jesus said the Holy Spirit would 'convict the world concerning sin and righteousness and judgment' (John 16:8). This means the Spirit:",
        "type": "multiple_choice",
        "options": [
            {"text": "Makes people feel guilty to punish them", "is_correct": False},
            {"text": "Exposes the truth about sin, reveals Christ's righteousness, and shows that Satan is defeated", "is_correct": True},  # B - CORRECT
            {"text": "Forces people to believe against their will", "is_correct": False},
            {"text": "Only works in church settings", "is_correct": False}
        ]
    },
    {
        "category": "The Holy Spirit — Another Helper",
        "text": "Jesus said it was better for Him to go away so the Spirit could come (John 16:7). The disciples had Jesus physically present — yet Jesus said the Spirit's indwelling presence is better. Do you live like the Holy Spirit's presence is a gift? How aware are you of the Spirit's work in your daily life?",
        "type": "open_ended",
        "options": []
    },
    # ===========================================
    # CATEGORY: Abiding in Christ — The Fruitful Life (3 questions: 2 MC, 1 OE)
    # ===========================================
    {
        "category": "Abiding in Christ — The Fruitful Life",
        "text": "In the vine and branches metaphor (John 15), Jesus said, 'Apart from me you can do nothing.' This teaches:",
        "type": "multiple_choice",
        "options": [
            {"text": "Christians should avoid all non-religious activities", "is_correct": False},
            {"text": "Spiritual fruitfulness is impossible without ongoing dependence on Jesus", "is_correct": True},  # B - CORRECT
            {"text": "Trying hard is the key to spiritual growth", "is_correct": False},
            {"text": "Jesus only helps those who help themselves", "is_correct": False}
        ]
    },
    {
        "category": "Abiding in Christ — The Fruitful Life",
        "text": "Jesus commanded His disciples, 'As the Father has loved me, so have I loved you. Now remain in my love' (John 15:9). We 'remain' (abide) in His love by:",
        "type": "multiple_choice",
        "options": [
            {"text": "Earning it through perfect obedience", "is_correct": False},
            {"text": "Feeling emotionally connected at all times", "is_correct": False},
            {"text": "Keeping His commands and staying connected to Him — obedience flowing from relationship", "is_correct": True},  # C - CORRECT
            {"text": "Withdrawing from the world completely", "is_correct": False}
        ]
    },
    {
        "category": "Abiding in Christ — The Fruitful Life",
        "text": "'I am the vine; you are the branches. Whoever abides in me and I in him, he it is that bears much fruit' (John 15:5). Fruit comes from abiding, not striving. How would you describe your connection to Jesus right now — thriving, surviving, or dried up? What helps you stay connected to the Vine? What pulls you away?",
        "type": "open_ended",
        "options": []
    },
]

def main():
    print("=" * 60)
    print("Gospel of John Assessment Setup")
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
                    "is_master_assessment": True,
                    "key": ASSESSMENT_KEY,
                    "version": 1,
                    "scoring_strategy": "ai_generic"
                })
                print(f"✅ Created Gospel of John Assessment template: {template_id}")
            
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
            mc_count = 0
            oe_count = 0
            
            for q_data in QUESTIONS_DATA:
                question_order += 1
                question_id = str(uuid.uuid4())
                category_id = categories[q_data["category"]]
                
                # Generate question code
                question_code = f"JGOS_{question_order:03d}"
                
                # Track question types
                if q_data["type"] == "multiple_choice":
                    mc_count += 1
                else:
                    oe_count += 1
                
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
                
                # Insert options (only for multiple choice questions)
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
            print(f"✅ SUCCESS! Created Gospel of John Assessment")
            print(f"   Template ID: {template_id}")
            print(f"   Total Questions: {question_order}")
            print(f"   Categories: {len(categories)}")
            print(f"   Multiple Choice: {mc_count}")
            print(f"   Open-Ended: {oe_count}")
            print("=" * 60)
            
        except Exception as e:
            trans.rollback()
            print(f"❌ ERROR: {e}")
            raise

if __name__ == "__main__":
    main()
