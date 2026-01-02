"""
Script to create the Gospel Fluency Assessment
Run as: python setup_gospel_fluency_assessment.py
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
ASSESSMENT_KEY = "gospel_fluency_v1"
ASSESSMENT_NAME = "Gospel Fluency Assessment"
ASSESSMENT_DESCRIPTION = """Assess your ability to understand and apply the gospel to all areas of life. This comprehensive assessment includes both knowledge-based multiple choice questions and reflective open-ended questions that explore how you apply gospel truths to real-life situations. 40 questions across 7 categories."""

# Questions organized by category
QUESTIONS_DATA = [
    # ===========================================
    # CATEGORY: Core Gospel Knowledge (8 MC questions)
    # ===========================================
    {
        "category": "Core Gospel Knowledge",
        "text": "What is the primary problem that the gospel addresses?",
        "type": "multiple_choice",
        "options": [
            {"text": "Broken relationships and lack of community", "is_correct": False},
            {"text": "Humanity's rebellion against God and resulting separation from Him", "is_correct": True},
            {"text": "Ignorance of God's laws and expectations", "is_correct": False},
            {"text": "The corruption of religious institutions", "is_correct": False}
        ]
    },
    {
        "category": "Core Gospel Knowledge",
        "text": "According to the gospel, how are humans made right with God?",
        "type": "multiple_choice",
        "options": [
            {"text": "Through sincere repentance and changed behavior", "is_correct": False},
            {"text": "By faith in Christ, whose righteousness is credited to us", "is_correct": True},
            {"text": "Through faith plus ongoing obedience to God's commands", "is_correct": False},
            {"text": "By God's mercy accepting our best efforts", "is_correct": False}
        ]
    },
    {
        "category": "Core Gospel Knowledge",
        "text": "What does 'justification' mean in gospel terms?",
        "type": "multiple_choice",
        "options": [
            {"text": "God overlooking our sins because of His love", "is_correct": False},
            {"text": "Being declared righteous through Christ's work, not our own", "is_correct": True},
            {"text": "The process of gradually becoming more holy", "is_correct": False},
            {"text": "God recognizing the good intentions of our heart", "is_correct": False}
        ]
    },
    {
        "category": "Core Gospel Knowledge",
        "text": "Jesus fulfills the role of prophet, priest, and king. What does His role as priest specifically accomplish?",
        "type": "multiple_choice",
        "options": [
            {"text": "He teaches us how to live righteously", "is_correct": False},
            {"text": "He rules over all creation with authority", "is_correct": False},
            {"text": "He mediates between God and man, offering Himself as the sacrifice", "is_correct": True},
            {"text": "He demonstrates God's power over evil", "is_correct": False}
        ]
    },
    {
        "category": "Core Gospel Knowledge",
        "text": "What is the primary significance of Jesus' resurrection for believers?",
        "type": "multiple_choice",
        "options": [
            {"text": "It validates Jesus' moral teachings as authoritative", "is_correct": False},
            {"text": "It demonstrates God's power to overcome any obstacle", "is_correct": False},
            {"text": "It secures our justification and guarantees our future resurrection", "is_correct": True},
            {"text": "It provides hope that good ultimately triumphs over evil", "is_correct": False}
        ]
    },
    {
        "category": "Core Gospel Knowledge",
        "text": "Which statement best describes the relationship between grace and faith in salvation?",
        "type": "multiple_choice",
        "options": [
            {"text": "Grace makes salvation possible; our faith makes it actual", "is_correct": False},
            {"text": "Grace is God's part; faith is our contribution to salvation", "is_correct": False},
            {"text": "Both grace and faith are gifts from God that accomplish our salvation", "is_correct": True},
            {"text": "Grace provides forgiveness; faith provides transformation", "is_correct": False}
        ]
    },
    {
        "category": "Core Gospel Knowledge",
        "text": "According to the gospel, a believer's identity is:",
        "type": "multiple_choice",
        "options": [
            {"text": "Shaped by their spiritual disciplines and growth", "is_correct": False},
            {"text": "Found in their calling and purpose in God's kingdom", "is_correct": False},
            {"text": "Rooted in their union with Christ and His finished work", "is_correct": True},
            {"text": "Defined by their transformation from who they were before", "is_correct": False}
        ]
    },
    {
        "category": "Core Gospel Knowledge",
        "text": "What does sanctification refer to?",
        "type": "multiple_choice",
        "options": [
            {"text": "The moment when God sets us apart as His own", "is_correct": False},
            {"text": "Our cooperation with the Spirit to grow in Christlikeness", "is_correct": True},
            {"text": "The final perfection we receive in heaven", "is_correct": False},
            {"text": "The cleansing from sin that happens at baptism", "is_correct": False}
        ]
    },
    # ===========================================
    # CATEGORY: Gospel Application Scenarios (6 MC questions)
    # ===========================================
    {
        "category": "Gospel Application Scenarios",
        "text": "A friend says, 'I've messed up too badly for God to forgive me.' The most gospel-centered response is:",
        "type": "multiple_choice",
        "options": [
            {"text": "God forgives those who are truly sorry and committed to change", "is_correct": False},
            {"text": "The depth of your sin reveals the greater depth of God's grace in Christ", "is_correct": True},
            {"text": "God sees your heart and knows you didn't mean it", "is_correct": False},
            {"text": "Everyone struggles with sin; God understands our weakness", "is_correct": False}
        ]
    },
    {
        "category": "Gospel Application Scenarios",
        "text": "A successful professional bases their entire worth on career achievements. The gospel speaks to this by saying:",
        "type": "multiple_choice",
        "options": [
            {"text": "Use your success to glorify God and serve others", "is_correct": False},
            {"text": "Success is fine, but remember that family and faith matter more", "is_correct": False},
            {"text": "Your value was settled at the cross, not in your accomplishments", "is_correct": True},
            {"text": "Be grateful for your gifts and stay humble about your success", "is_correct": False}
        ]
    },
    {
        "category": "Gospel Application Scenarios",
        "text": "A coworker is consumed with anxiety about an uncertain future. A gospel-fluent response would emphasize:",
        "type": "multiple_choice",
        "options": [
            {"text": "God's promise to work all things for the good of those who love Him", "is_correct": False},
            {"text": "The peace that comes from trusting God's sovereign plan", "is_correct": False},
            {"text": "That Christ has secured our ultimate future, freeing us from fear's power", "is_correct": True},
            {"text": "God's faithfulness in providing for our daily needs", "is_correct": False}
        ]
    },
    {
        "category": "Gospel Application Scenarios",
        "text": "When you experience significant personal failure, gospel fluency means:",
        "type": "multiple_choice",
        "options": [
            {"text": "Remembering that failure helps you grow and become stronger", "is_correct": False},
            {"text": "Trusting that God will use even your failures for good", "is_correct": False},
            {"text": "Resting in Christ's perfect record that is now counted as yours", "is_correct": True},
            {"text": "Knowing that God's love doesn't depend on your success", "is_correct": False}
        ]
    },
    {
        "category": "Gospel Application Scenarios",
        "text": "Someone struggling with persistent pride should understand that the gospel:",
        "type": "multiple_choice",
        "options": [
            {"text": "Calls us to focus on others rather than ourselves", "is_correct": False},
            {"text": "Reminds us of our unworthiness before a holy God", "is_correct": False},
            {"text": "Simultaneously humbles and affirms us through Christ", "is_correct": True},
            {"text": "Teaches that all our gifts come from God", "is_correct": False}
        ]
    },
    {
        "category": "Gospel Application Scenarios",
        "text": "A believer feels spiritually distant from God despite consistent devotional practices. Gospel fluency reminds them:",
        "type": "multiple_choice",
        "options": [
            {"text": "To persist in spiritual disciplines until feelings return", "is_correct": False},
            {"text": "That their standing with God depends on Christ, not their spiritual performance", "is_correct": True},
            {"text": "To examine their life for unconfessed sin creating the distance", "is_correct": False},
            {"text": "That feelings of closeness naturally ebb and flow", "is_correct": False}
        ]
    },
    # ===========================================
    # CATEGORY: Theological Understanding (6 MC questions)
    # ===========================================
    {
        "category": "Theological Understanding",
        "text": "Someone asks, 'If we're saved by grace, why does obedience matter?' The gospel answer is:",
        "type": "multiple_choice",
        "options": [
            {"text": "Obedience is how we show gratitude and maintain our relationship with God", "is_correct": False},
            {"text": "Obedience doesn't earn salvation but it does earn greater rewards", "is_correct": False},
            {"text": "Obedience is the fruit of a transformed heart, not the root of our acceptance", "is_correct": True},
            {"text": "Obedience is optional but leads to a more blessed and fulfilled life", "is_correct": False}
        ]
    },
    {
        "category": "Theological Understanding",
        "text": "The doctrine of union with Christ means:",
        "type": "multiple_choice",
        "options": [
            {"text": "Christ lives in our hearts through faith", "is_correct": False},
            {"text": "We are spiritually connected to Christ and share in all His benefits", "is_correct": True},
            {"text": "We become more like Christ as we follow Him", "is_correct": False},
            {"text": "We have access to God through Christ's mediation", "is_correct": False}
        ]
    },
    {
        "category": "Theological Understanding",
        "text": "What is the relationship between the law and the gospel?",
        "type": "multiple_choice",
        "options": [
            {"text": "The law shows us how to live; the gospel forgives us when we fail", "is_correct": False},
            {"text": "The gospel replaces the law, which is no longer relevant for believers", "is_correct": False},
            {"text": "The law reveals our need; the gospel provides what the law demanded", "is_correct": True},
            {"text": "The law is for unbelievers; the gospel is for believers", "is_correct": False}
        ]
    },
    {
        "category": "Theological Understanding",
        "text": "True repentance in light of the gospel is best understood as:",
        "type": "multiple_choice",
        "options": [
            {"text": "Feeling deep remorse for sin and committing to change", "is_correct": False},
            {"text": "Confessing specific sins and making restitution where possible", "is_correct": False},
            {"text": "Turning from self-reliance to reliance on Christ for righteousness", "is_correct": True},
            {"text": "Acknowledging sin and accepting God's discipline", "is_correct": False}
        ]
    },
    {
        "category": "Theological Understanding",
        "text": "A mature believer needs the gospel:",
        "type": "multiple_choice",
        "options": [
            {"text": "Primarily when sharing faith with unbelievers", "is_correct": False},
            {"text": "Mainly during seasons of failure or spiritual struggle", "is_correct": False},
            {"text": "As the daily foundation for all of life and growth", "is_correct": True},
            {"text": "To remember where they came from and stay humble", "is_correct": False}
        ]
    },
    {
        "category": "Theological Understanding",
        "text": "The Holy Spirit's primary role in the Christian life is:",
        "type": "multiple_choice",
        "options": [
            {"text": "Guiding us to make wise decisions", "is_correct": False},
            {"text": "Empowering us to live obediently", "is_correct": False},
            {"text": "Applying Christ's work to us and conforming us to Him", "is_correct": True},
            {"text": "Giving us spiritual gifts for ministry", "is_correct": False}
        ]
    },
    # ===========================================
    # CATEGORY: Personal Reflection (5 open-ended questions)
    # ===========================================
    {
        "category": "Personal Reflection",
        "text": "In your own words, explain the gospel message in 2-3 sentences as if sharing with someone who has never heard it.",
        "type": "open_ended",
        "options": []
    },
    {
        "category": "Personal Reflection",
        "text": "Describe a recent situation where you struggled to apply the gospel to your own heart. What gospel truth did you need to remember?",
        "type": "open_ended",
        "options": []
    },
    {
        "category": "Personal Reflection",
        "text": "How has understanding the gospel changed the way you view your own failures and shortcomings?",
        "type": "open_ended",
        "options": []
    },
    {
        "category": "Personal Reflection",
        "text": "What does it mean to you personally that your identity is 'in Christ'? How does this affect your daily life?",
        "type": "open_ended",
        "options": []
    },
    {
        "category": "Personal Reflection",
        "text": "Describe a time when you applied the gospel to a specific emotion you were experiencing (fear, anger, shame, etc.). What happened?",
        "type": "open_ended",
        "options": []
    },
    # ===========================================
    # CATEGORY: Everyday Application (5 open-ended questions)
    # ===========================================
    {
        "category": "Everyday Application",
        "text": "A friend confides they feel worthless because of a recent divorce. How would you speak the gospel into this situation?",
        "type": "open_ended",
        "options": []
    },
    {
        "category": "Everyday Application",
        "text": "A young person you mentor is devastated after being cut from a sports team. How would you apply the gospel to their disappointment?",
        "type": "open_ended",
        "options": []
    },
    {
        "category": "Everyday Application",
        "text": "Someone at work takes credit for your idea. How does the gospel shape your response to this injustice?",
        "type": "open_ended",
        "options": []
    },
    {
        "category": "Everyday Application",
        "text": "A neighbor going through cancer treatment asks, 'Why would God let this happen?' How would you respond with gospel truth while showing compassion?",
        "type": "open_ended",
        "options": []
    },
    {
        "category": "Everyday Application",
        "text": "You're having dinner with a non-believing friend who says, 'I'm basically a good person, so I think I'll be fine with God.' How do you graciously share the gospel?",
        "type": "open_ended",
        "options": []
    },
    # ===========================================
    # CATEGORY: Deeper Theological Application (5 open-ended questions)
    # ===========================================
    {
        "category": "Deeper Theological Application",
        "text": "Explain how the gospel speaks to someone trapped in legalism (trying to earn God's favor through rule-keeping).",
        "type": "open_ended",
        "options": []
    },
    {
        "category": "Deeper Theological Application",
        "text": "How does the gospel address the person who uses grace as an excuse to continue in sin?",
        "type": "open_ended",
        "options": []
    },
    {
        "category": "Deeper Theological Application",
        "text": "A believer confesses they intellectually know the gospel but don't 'feel' forgiven. How would you counsel them using gospel truths?",
        "type": "open_ended",
        "options": []
    },
    {
        "category": "Deeper Theological Application",
        "text": "Describe how the gospel should shape the way a Christian handles conflict in relationships.",
        "type": "open_ended",
        "options": []
    },
    {
        "category": "Deeper Theological Application",
        "text": "How does understanding Jesus as Prophet, Priest, and King help you apply the gospel to different life situations?",
        "type": "open_ended",
        "options": []
    },
    # ===========================================
    # CATEGORY: Community & Mission (5 open-ended questions)
    # ===========================================
    {
        "category": "Community & Mission",
        "text": "How does the gospel shape the way you view and treat people who are different from you (culturally, socially, economically)?",
        "type": "open_ended",
        "options": []
    },
    {
        "category": "Community & Mission",
        "text": "Describe what it looks like to create a gospel-centered community in your home or small group.",
        "type": "open_ended",
        "options": []
    },
    {
        "category": "Community & Mission",
        "text": "How should the gospel motivate and shape our approach to serving the poor and marginalized?",
        "type": "open_ended",
        "options": []
    },
    {
        "category": "Community & Mission",
        "text": "What are practical ways to weave gospel conversations into everyday interactions (at work, with neighbors, etc.)?",
        "type": "open_ended",
        "options": []
    },
    {
        "category": "Community & Mission",
        "text": "Reflect on an area of your life where you are NOT currently applying the gospel. What would change if you did?",
        "type": "open_ended",
        "options": []
    },
]

def main():
    print("=" * 60)
    print("Gospel Fluency Assessment Setup")
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
                # Columns: id, name, description, is_published, is_master_assessment, created_at,
                #          key, version, scoring_strategy, rubric_json, report_template, pdf_renderer, created_by
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
                print(f"✅ Created Gospel Fluency Assessment template: {template_id}")
            
            # Get or create categories
            # Categories table only has: id, name
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
                question_code = f"GOSP_{question_order:03d}"
                
                # Insert question
                # Questions table: id, question_code, text, question_type, category_id
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
                # Question_options table: id, question_id, option_text, is_correct, "order"
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
                # Assessment_template_questions table: id, template_id, question_id, "order"
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
            print(f"✅ SUCCESS! Created Gospel Fluency Assessment")
            print(f"   Template ID: {template_id}")
            print(f"   Total Questions: {question_order}")
            print(f"   Categories: {len(categories)}")
            print(f"   Multiple Choice: 20")
            print(f"   Open-Ended: 20")
            print("=" * 60)
            
        except Exception as e:
            trans.rollback()
            print(f"❌ ERROR: {e}")
            raise

if __name__ == "__main__":
    main()
