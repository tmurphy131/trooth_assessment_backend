"""
Script to create the Romans Assessment
Run as: python setup_romans_assessment.py
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
ASSESSMENT_KEY = "romans_v1"
ASSESSMENT_NAME = "Romans Assessment"
ASSESSMENT_DESCRIPTION = """Explore the theological depths of Paul's letter to the Romans. This assessment covers key themes including sin, justification by faith, freedom from sin, the struggle with sin, life in the Spirit, living as a sacrifice, and love in relationships. 27 questions (16 multiple choice, 11 open-ended) across 7 categories."""

# Questions organized by category
QUESTIONS_DATA = [
    # ===========================================
    # CATEGORY: Sin & Human Condition (4 questions: 2 MC, 2 OE)
    # ===========================================
    {
        "category": "Sin & Human Condition",
        "text": "According to Romans 3:23, what is the universal condition of all humanity?",
        "type": "multiple_choice",
        "options": [
            {"text": "All have sinned and fall short of the glory of God", "is_correct": True},
            {"text": "All are born innocent until they choose to sin", "is_correct": False},
            {"text": "Only those who knowingly disobey are guilty of sin", "is_correct": False},
            {"text": "Some are righteous by nature", "is_correct": False}
        ]
    },
    {
        "category": "Sin & Human Condition",
        "text": "In Romans 1:18-32, Paul describes humanity's downward spiral. What does he identify as the root cause?",
        "type": "multiple_choice",
        "options": [
            {"text": "Lack of education about God", "is_correct": False},
            {"text": "Suppressing the truth and failing to honor God", "is_correct": True},
            {"text": "Being born into sinful environments", "is_correct": False},
            {"text": "Not having access to Scripture", "is_correct": False}
        ]
    },
    {
        "category": "Sin & Human Condition",
        "text": "Romans 1:20 says God's invisible qualities are 'clearly seen' through creation. How does this truth affect your view of people who have never heard the gospel?",
        "type": "open_ended",
        "options": []
    },
    {
        "category": "Sin & Human Condition",
        "text": "Reflect on Romans 3:10-18. How does this passage challenge the idea that people are 'basically good'? How should this shape our understanding of ourselves and others?",
        "type": "open_ended",
        "options": []
    },
    # ===========================================
    # CATEGORY: Justification by Faith (4 questions: 2 MC, 2 OE)
    # ===========================================
    {
        "category": "Justification by Faith",
        "text": "According to Romans 4, how was Abraham made righteous before God?",
        "type": "multiple_choice",
        "options": [
            {"text": "Through circumcision and keeping the law", "is_correct": False},
            {"text": "His faith was credited to him as righteousness", "is_correct": True},
            {"text": "By offering Isaac as a sacrifice", "is_correct": False},
            {"text": "Through his obedience in leaving Ur", "is_correct": False}
        ]
    },
    {
        "category": "Justification by Faith",
        "text": "Romans 5:1 says, 'Therefore, since we have been justified by faith, we have...'",
        "type": "multiple_choice",
        "options": [
            {"text": "Assurance of prosperity", "is_correct": False},
            {"text": "Freedom from all suffering", "is_correct": False},
            {"text": "Peace with God through our Lord Jesus Christ", "is_correct": True},
            {"text": "Complete sanctification", "is_correct": False}
        ]
    },
    {
        "category": "Justification by Faith",
        "text": "Romans 5:8 says Christ died for us 'while we were still sinners.' How does this truth impact the way you view your relationship with God when you fail?",
        "type": "open_ended",
        "options": []
    },
    {
        "category": "Justification by Faith",
        "text": "In Romans 3:28, Paul declares we are 'justified by faith apart from works of the law.' How would you explain this to someone who believes they must earn God's acceptance?",
        "type": "open_ended",
        "options": []
    },
    # ===========================================
    # CATEGORY: Freedom from Sin (4 questions: 2 MC, 2 OE)
    # ===========================================
    {
        "category": "Freedom from Sin",
        "text": "What rhetorical question does Paul ask in Romans 6:1?",
        "type": "multiple_choice",
        "options": [
            {"text": "Shall we stop sinning so grace may increase?", "is_correct": False},
            {"text": "Shall we go on sinning so that grace may increase?", "is_correct": True},
            {"text": "Shall we earn our salvation by good works?", "is_correct": False},
            {"text": "Shall we fear death since Christ has risen?", "is_correct": False}
        ]
    },
    {
        "category": "Freedom from Sin",
        "text": "According to Romans 6:6-7, what has happened to our 'old self'?",
        "type": "multiple_choice",
        "options": [
            {"text": "It has been improved and reformed", "is_correct": False},
            {"text": "It was crucified with Christ so we are no longer slaves to sin", "is_correct": True},
            {"text": "It remains but is gradually being sanctified", "is_correct": False},
            {"text": "It was hidden by Christ's righteousness", "is_correct": False}
        ]
    },
    {
        "category": "Freedom from Sin",
        "text": "Romans 6:11-14 calls us to 'consider ourselves dead to sin but alive to God.' What does this look like practically in your daily life?",
        "type": "open_ended",
        "options": []
    },
    {
        "category": "Freedom from Sin",
        "text": "Paul says in Romans 6:18 that we have been 'set free from sin and have become slaves to righteousness.' How do you reconcile this freedom with the ongoing struggle believers have with sin?",
        "type": "open_ended",
        "options": []
    },
    # ===========================================
    # CATEGORY: Struggle with Sin (4 questions: 3 MC, 1 OE)
    # ===========================================
    {
        "category": "Struggle with Sin",
        "text": "In Romans 7:15, Paul describes an internal conflict. What does he say?",
        "type": "multiple_choice",
        "options": [
            {"text": "I do the good I want to do and avoid all evil", "is_correct": False},
            {"text": "I do not do the good I want, but the evil I do not want is what I keep on doing", "is_correct": True},
            {"text": "I have completely overcome my sinful nature", "is_correct": False},
            {"text": "I no longer feel any desire to sin", "is_correct": False}
        ]
    },
    {
        "category": "Struggle with Sin",
        "text": "At the end of Romans 7, what is Paul's cry of anguish and hope?",
        "type": "multiple_choice",
        "options": [
            {"text": "Who will help me try harder? I will redouble my efforts!", "is_correct": False},
            {"text": "Who is righteous enough to stand before God? No one!", "is_correct": False},
            {"text": "Wretched man that I am! Who will deliver me? Thanks be to God through Jesus Christ!", "is_correct": True},
            {"text": "How long must I suffer? Until the day of the Lord!", "is_correct": False}
        ]
    },
    {
        "category": "Struggle with Sin",
        "text": "According to Romans 7:22-23, what two 'laws' are at war within the believer?",
        "type": "multiple_choice",
        "options": [
            {"text": "The law of Moses and the law of love", "is_correct": False},
            {"text": "The law of faith and the law of works", "is_correct": False},
            {"text": "The law of the mind (delighting in God's law) and the law of sin", "is_correct": True},
            {"text": "The law of grace and the law of judgment", "is_correct": False}
        ]
    },
    {
        "category": "Struggle with Sin",
        "text": "Romans 7 is often debated: Is Paul describing his experience before or after becoming a Christian? What is your view, and how does this passage encourage you in your own struggles with sin?",
        "type": "open_ended",
        "options": []
    },
    # ===========================================
    # CATEGORY: Life in the Spirit (4 questions: 3 MC, 1 OE)
    # ===========================================
    {
        "category": "Life in the Spirit",
        "text": "Romans 8:1 provides what assurance to those who are in Christ Jesus?",
        "type": "multiple_choice",
        "options": [
            {"text": "They will never experience trials", "is_correct": False},
            {"text": "They will always feel God's presence", "is_correct": False},
            {"text": "There is now no condemnation for them", "is_correct": True},
            {"text": "They will be rewarded with earthly prosperity", "is_correct": False}
        ]
    },
    {
        "category": "Life in the Spirit",
        "text": "According to Romans 8:28, what does God work for the good of those who love Him?",
        "type": "multiple_choice",
        "options": [
            {"text": "Only the good circumstances in life", "is_correct": False},
            {"text": "All things", "is_correct": True},
            {"text": "Only the things we pray about", "is_correct": False},
            {"text": "Only spiritual matters, not earthly ones", "is_correct": False}
        ]
    },
    {
        "category": "Life in the Spirit",
        "text": "In Romans 8:31-39, Paul asks, 'If God is for us, who can be against us?' What conclusion does he reach?",
        "type": "multiple_choice",
        "options": [
            {"text": "We might be separated from Christ by extreme persecution", "is_correct": False},
            {"text": "Only death can separate us from God's love", "is_correct": False},
            {"text": "Nothing in all creation can separate us from the love of God in Christ", "is_correct": True},
            {"text": "We must work hard to maintain our connection to Christ", "is_correct": False}
        ]
    },
    {
        "category": "Life in the Spirit",
        "text": "Romans 8:26-27 describes how the Spirit helps us in our weakness, especially in prayer. Describe a time when you sensed the Spirit interceding for you or helping you pray when you didn't have the words.",
        "type": "open_ended",
        "options": []
    },
    # ===========================================
    # CATEGORY: Living Sacrifice (4 questions: 2 MC, 2 OE)
    # ===========================================
    {
        "category": "Living Sacrifice",
        "text": "Romans 12:1 urges believers to present their bodies as what?",
        "type": "multiple_choice",
        "options": [
            {"text": "Temples of the Holy Spirit", "is_correct": False},
            {"text": "Living sacrifices, holy and pleasing to God", "is_correct": True},
            {"text": "Instruments of worship", "is_correct": False},
            {"text": "Vessels of mercy", "is_correct": False}
        ]
    },
    {
        "category": "Living Sacrifice",
        "text": "According to Romans 12:2, how are we transformed?",
        "type": "multiple_choice",
        "options": [
            {"text": "By conforming to the patterns of this world", "is_correct": False},
            {"text": "By the renewing of our minds", "is_correct": True},
            {"text": "By performing religious rituals", "is_correct": False},
            {"text": "By isolating from secular culture", "is_correct": False}
        ]
    },
    {
        "category": "Living Sacrifice",
        "text": "Romans 12:1 calls us to offer ourselves as 'living sacrifices' as our 'true and proper worship.' What does it look like for you to worship God with your everyday life, not just on Sunday?",
        "type": "open_ended",
        "options": []
    },
    {
        "category": "Living Sacrifice",
        "text": "In Romans 12:3-8, Paul discusses spiritual gifts within the body of Christ. How do you understand your role in the church community? What gifts has God given you, and how are you using them?",
        "type": "open_ended",
        "options": []
    },
    # ===========================================
    # CATEGORY: Love & Relationships (3 questions: 2 MC, 1 OE)
    # ===========================================
    {
        "category": "Love & Relationships",
        "text": "According to Romans 13:8-10, what fulfills the law?",
        "type": "multiple_choice",
        "options": [
            {"text": "Strict obedience to every commandment", "is_correct": False},
            {"text": "Love, because love does no harm to a neighbor", "is_correct": True},
            {"text": "Fear of God and His judgment", "is_correct": False},
            {"text": "Religious ceremonies and traditions", "is_correct": False}
        ]
    },
    {
        "category": "Love & Relationships",
        "text": "In Romans 14, Paul addresses disputes over 'disputable matters' (food, special days). What is his main instruction?",
        "type": "multiple_choice",
        "options": [
            {"text": "Everyone should follow the strictest interpretation", "is_correct": False},
            {"text": "Accept those whose faith is weak, without quarreling over disputable matters", "is_correct": True},
            {"text": "Avoid fellowship with those who disagree", "is_correct": False},
            {"text": "Leaders should decide for the entire community", "is_correct": False}
        ]
    },
    {
        "category": "Love & Relationships",
        "text": "Romans 14:13-19 warns against causing a brother or sister to stumble. Think of a current issue in your community where Christians disagree. How might you apply Paul's teaching to pursue peace and build others up?",
        "type": "open_ended",
        "options": []
    },
]

def main():
    print("=" * 60)
    print("Romans Assessment Setup")
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
                    "scoring_strategy": "ai_generic"  # AI scoring for open-ended questions
                })
                print(f"✅ Created Romans Assessment template: {template_id}")
            
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
                question_code = f"ROM_{question_order:03d}"
                
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
            print(f"✅ SUCCESS! Created Romans Assessment")
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
