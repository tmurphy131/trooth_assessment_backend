"""
Script to create the 1st, 2nd & 3rd John Assessment
Run as: python setup_john_epistles_assessment.py
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
ASSESSMENT_KEY = "john_epistles_v1"
ASSESSMENT_NAME = "1st, 2nd & 3rd John Assessment"
ASSESSMENT_DESCRIPTION = """Explore the letters of John - walking in the light, love for one another, assurance of salvation, discerning truth from error, and faithful hospitality. This assessment covers themes from all three epistles including fellowship with God, loving one another, overcoming the world, testing the spirits, abiding in Christ, and faithful hospitality. 27 questions (16 multiple choice, 11 open-ended) across 7 categories."""

# Questions organized by category
# NOTE: Correct answers are distributed across positions A, B, C, D
QUESTIONS_DATA = [
    # ===========================================
    # CATEGORY: Walking in the Light (4 questions: 2 MC, 2 OE)
    # ===========================================
    {
        "category": "Walking in the Light",
        "text": "According to 1 John 1:5-7, what does it mean that 'God is light'?",
        "type": "multiple_choice",
        "options": [
            {"text": "God reveals Himself clearly through creation and conscience", "is_correct": False},
            {"text": "In God there is no darkness at all; walking in the light means fellowship with Him and cleansing from sin", "is_correct": True},  # B - CORRECT
            {"text": "God illuminates our path so we can make wise decisions", "is_correct": False},
            {"text": "God's truth exposes and judges all hidden things", "is_correct": False}
        ]
    },
    {
        "category": "Walking in the Light",
        "text": "1 John 1:8-10 says if we claim to be without sin:",
        "type": "multiple_choice",
        "options": [
            {"text": "We demonstrate mature faith and victory over temptation", "is_correct": False},
            {"text": "We show that Christ's work in us is complete", "is_correct": False},
            {"text": "We honor God by trusting His sanctifying power", "is_correct": False},
            {"text": "We deceive ourselves, the truth is not in us, and we make God out to be a liar", "is_correct": True}  # D - CORRECT
        ]
    },
    {
        "category": "Walking in the Light",
        "text": "1 John 1:9 promises that 'if we confess our sins, He is faithful and just to forgive us.' How does knowing God is both 'faithful' and 'just' in forgiving affect how you approach confession?",
        "type": "open_ended",
        "options": []
    },
    {
        "category": "Walking in the Light",
        "text": "John contrasts walking in the light versus walking in darkness (1 John 1:6-7). What areas of your life tend to stay 'in the dark'? What would it look like to bring them into the light?",
        "type": "open_ended",
        "options": []
    },
    # ===========================================
    # CATEGORY: Love One Another (4 questions: 3 MC, 1 OE)
    # ===========================================
    {
        "category": "Love One Another",
        "text": "According to 1 John 3:16-18, how do we know what love is?",
        "type": "multiple_choice",
        "options": [
            {"text": "Love is a feeling of deep affection and care for others", "is_correct": False},
            {"text": "Love is patient, kind, and keeps no record of wrongs", "is_correct": False},
            {"text": "Jesus laid down His life for us, and we ought to lay down our lives for one another", "is_correct": True},  # C - CORRECT
            {"text": "Love is the fulfillment of God's law and the greatest commandment", "is_correct": False}
        ]
    },
    {
        "category": "Love One Another",
        "text": "1 John 4:20 confronts those who claim to love God but hate their brother:",
        "type": "multiple_choice",
        "options": [
            {"text": "They are liars, for anyone who does not love their brother whom they have seen cannot love God whom they have not seen", "is_correct": True},  # A - CORRECT
            {"text": "They are immature and need to grow in their understanding of love", "is_correct": False},
            {"text": "They are deceived by the world's definition of love", "is_correct": False},
            {"text": "They are struggling with sin but can still have genuine faith", "is_correct": False}
        ]
    },
    {
        "category": "Love One Another",
        "text": "What does 1 John 3:14 say is evidence that we have passed from death to life?",
        "type": "multiple_choice",
        "options": [
            {"text": "We have been baptized and participate in communion", "is_correct": False},
            {"text": "We believe that Jesus is the Christ, the Son of God", "is_correct": False},
            {"text": "We keep God's commandments and do what pleases Him", "is_correct": False},
            {"text": "We love our brothers and sisters in Christ", "is_correct": True}  # D - CORRECT
        ]
    },
    {
        "category": "Love One Another",
        "text": "1 John 3:18 says we should love 'not with words or speech but with actions and in truth.' Think of someone in your life who needs tangible love. What specific action could you take this week?",
        "type": "open_ended",
        "options": []
    },
    # ===========================================
    # CATEGORY: Assurance of Salvation (4 questions: 2 MC, 2 OE)
    # ===========================================
    {
        "category": "Assurance of Salvation",
        "text": "According to 1 John 5:13, why did John write his letter?",
        "type": "multiple_choice",
        "options": [
            {"text": "To warn believers about false teachers infiltrating the church", "is_correct": False},
            {"text": "To encourage believers to persevere through persecution", "is_correct": False},
            {"text": "So that those who believe may know that they have eternal life", "is_correct": True},  # C - CORRECT
            {"text": "To teach believers how to walk in love and truth", "is_correct": False}
        ]
    },
    {
        "category": "Assurance of Salvation",
        "text": "1 John 2:3-6 says we can know that we have come to know Christ if:",
        "type": "multiple_choice",
        "options": [
            {"text": "We have a personal experience of His presence and power", "is_correct": False},
            {"text": "We keep His commands and walk as Jesus walked", "is_correct": True},  # B - CORRECT
            {"text": "We have correct doctrine and defend the faith against error", "is_correct": False},
            {"text": "We feel assured and at peace about our salvation", "is_correct": False}
        ]
    },
    {
        "category": "Assurance of Salvation",
        "text": "1 John gives several 'tests' of genuine faith: believing right doctrine, obeying God's commands, and loving others. Which of these do you find most challenging? Why?",
        "type": "open_ended",
        "options": []
    },
    {
        "category": "Assurance of Salvation",
        "text": "1 John 5:13 says John wrote so believers may 'know' they have eternal life. Do you have this assurance? What gives you confidence (or what causes doubt) about your standing with God?",
        "type": "open_ended",
        "options": []
    },
    # ===========================================
    # CATEGORY: Overcoming the World (4 questions: 2 MC, 2 OE)
    # ===========================================
    {
        "category": "Overcoming the World",
        "text": "According to 1 John 2:15-17, what does 'the world' consist of that believers should not love?",
        "type": "multiple_choice",
        "options": [
            {"text": "Material possessions, entertainment, and secular education", "is_correct": False},
            {"text": "Non-Christians, secular culture, and worldly philosophies", "is_correct": False},
            {"text": "The lust of the flesh, the lust of the eyes, and the pride of life", "is_correct": True},  # C - CORRECT
            {"text": "Political systems, economic structures, and social institutions", "is_correct": False}
        ]
    },
    {
        "category": "Overcoming the World",
        "text": "1 John 5:4-5 declares that our victory that overcomes the world is:",
        "type": "multiple_choice",
        "options": [
            {"text": "Our obedience to God's commands", "is_correct": False},
            {"text": "Our love for one another", "is_correct": False},
            {"text": "Our perseverance through trials", "is_correct": False},
            {"text": "Our faith - everyone born of God overcomes the world", "is_correct": True}  # D - CORRECT
        ]
    },
    {
        "category": "Overcoming the World",
        "text": "1 John 2:15 says 'Do not love the world or anything in the world.' How do you distinguish between appreciating God's good creation and sinfully loving 'the world'?",
        "type": "open_ended",
        "options": []
    },
    {
        "category": "Overcoming the World",
        "text": "John says 'the one who is in you is greater than the one who is in the world' (1 John 4:4). How does this truth encourage you when you feel overwhelmed by worldly pressures or temptations?",
        "type": "open_ended",
        "options": []
    },
    # ===========================================
    # CATEGORY: Discerning Truth & Error (4 questions: 3 MC, 1 OE)
    # ===========================================
    {
        "category": "Discerning Truth & Error",
        "text": "According to 1 John 4:1-3, how can believers test whether a spirit is from God?",
        "type": "multiple_choice",
        "options": [
            {"text": "By examining the fruits and character of the teacher", "is_correct": False},
            {"text": "By whether they acknowledge that Jesus Christ has come in the flesh", "is_correct": True},  # B - CORRECT
            {"text": "By whether their teaching aligns with the Old Testament prophets", "is_correct": False},
            {"text": "By whether they perform signs and wonders", "is_correct": False}
        ]
    },
    {
        "category": "Discerning Truth & Error",
        "text": "1 John 2:22-23 identifies the antichrist as anyone who:",
        "type": "multiple_choice",
        "options": [
            {"text": "Persecutes believers and opposes the church", "is_correct": False},
            {"text": "Claims to be Christ or performs false miracles", "is_correct": False},
            {"text": "Denies that Jesus is the Christ and denies the Father and the Son", "is_correct": True},  # C - CORRECT
            {"text": "Teaches that salvation comes through works rather than faith", "is_correct": False}
        ]
    },
    {
        "category": "Discerning Truth & Error",
        "text": "2 John 9-11 instructs believers regarding false teachers who do not continue in the teaching of Christ:",
        "type": "multiple_choice",
        "options": [
            {"text": "Engage them in dialogue to understand their perspective", "is_correct": False},
            {"text": "Pray for them and show them kindness to win them back", "is_correct": False},
            {"text": "Report them to church leadership for discipline", "is_correct": False},
            {"text": "Do not welcome them into your house or give them any greeting", "is_correct": True}  # D - CORRECT
        ]
    },
    {
        "category": "Discerning Truth & Error",
        "text": "John warns about 'many antichrists' and 'false prophets' (1 John 2:18, 4:1). What false teachings do you see today that deny essential truths about Christ? How can believers guard against deception?",
        "type": "open_ended",
        "options": []
    },
    # ===========================================
    # CATEGORY: The Anointing & Abiding (4 questions: 2 MC, 2 OE)
    # ===========================================
    {
        "category": "The Anointing & Abiding",
        "text": "According to 1 John 2:27, what does the 'anointing' from the Holy One do for believers?",
        "type": "multiple_choice",
        "options": [
            {"text": "Teaches them about all things so they do not need human teachers to lead them astray", "is_correct": True},  # A - CORRECT
            {"text": "Gives them spiritual gifts for ministry and service", "is_correct": False},
            {"text": "Empowers them to perform miracles and cast out demons", "is_correct": False},
            {"text": "Seals them for the day of redemption and guarantees their inheritance", "is_correct": False}
        ]
    },
    {
        "category": "The Anointing & Abiding",
        "text": "1 John 2:28 urges believers to 'continue in Him' so that when Christ appears:",
        "type": "multiple_choice",
        "options": [
            {"text": "They will receive their full reward in heaven", "is_correct": False},
            {"text": "They may be confident and unashamed before Him at His coming", "is_correct": True},  # B - CORRECT
            {"text": "They will be recognized as His faithful servants", "is_correct": False},
            {"text": "They will be spared from the tribulation to come", "is_correct": False}
        ]
    },
    {
        "category": "The Anointing & Abiding",
        "text": "John speaks of 'abiding' or 'remaining' in Christ throughout his letter. What practices or habits help you abide in Christ daily? What pulls you away?",
        "type": "open_ended",
        "options": []
    },
    {
        "category": "The Anointing & Abiding",
        "text": "1 John 2:27 mentions the 'anointing' that teaches believers. How do you understand the relationship between the Spirit's teaching and learning from human teachers and Scripture?",
        "type": "open_ended",
        "options": []
    },
    # ===========================================
    # CATEGORY: Faithful Hospitality (3 John) (3 questions: 2 MC, 1 OE)
    # ===========================================
    {
        "category": "Faithful Hospitality (3 John)",
        "text": "In 3 John, the elder (John) commends Gaius for:",
        "type": "multiple_choice",
        "options": [
            {"text": "Showing hospitality to traveling teachers, even though they were strangers to him", "is_correct": True},  # A - CORRECT
            {"text": "Defending sound doctrine against the false teachers in the church", "is_correct": False},
            {"text": "Leading the church faithfully despite opposition from Diotrephes", "is_correct": False},
            {"text": "Giving generously to the poor and supporting widows and orphans", "is_correct": False}
        ]
    },
    {
        "category": "Faithful Hospitality (3 John)",
        "text": "In 3 John 9-10, Diotrephes is criticized because he:",
        "type": "multiple_choice",
        "options": [
            {"text": "Taught false doctrine and led people away from the truth", "is_correct": False},
            {"text": "Loved money and used the church for personal gain", "is_correct": False},
            {"text": "Loved to be first, refused to welcome the brothers, and put people out of the church", "is_correct": True},  # C - CORRECT
            {"text": "Persecuted believers and reported them to the authorities", "is_correct": False}
        ]
    },
    {
        "category": "Faithful Hospitality (3 John)",
        "text": "3 John contrasts Gaius (faithful hospitality) with Diotrephes (selfish ambition). Which character do you more naturally resemble? How can the church cultivate a culture of generous hospitality today?",
        "type": "open_ended",
        "options": []
    },
]

def main():
    print("=" * 60)
    print("1st, 2nd & 3rd John Assessment Setup")
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
                print(f"✅ Created 1st, 2nd & 3rd John Assessment template: {template_id}")
            
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
                question_code = f"JOHN_{question_order:03d}"
                
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
            print(f"✅ SUCCESS! Created 1st, 2nd & 3rd John Assessment")
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
