"""
Script to create the In Christ: Ephesians & Colossians Assessment
Run as: python setup_ephesians_colossians_assessment.py
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
ASSESSMENT_KEY = "ephesians_colossians_v1"
ASSESSMENT_NAME = "In Christ: Ephesians & Colossians"
ASSESSMENT_DESCRIPTION = """Explore Paul's twin letters to the Ephesians and Colossians — rich with theology about who we are "in Christ." This assessment covers our spiritual inheritance, salvation by grace, unity in Christ, the supremacy and sufficiency of Jesus, the mystery revealed, walking worthy, and spiritual warfare. Gospel-centered open-ended questions help you understand and live out your identity in Christ. 25 questions (15 multiple choice, 10 open-ended) across 7 categories."""

# Questions organized by category
# NOTE: Correct answers distributed across A, B, C, D positions
# NOTE: All options are balanced in length to avoid obvious patterns
QUESTIONS_DATA = [
    # ===========================================
    # CATEGORY: Blessed in Christ — Our Spiritual Inheritance (4 questions: 2 MC, 2 OE)
    # ===========================================
    {
        "category": "Blessed in Christ — Our Spiritual Inheritance",
        "text": "Paul begins Ephesians by saying God 'has blessed us in Christ with every spiritual blessing in the heavenly places' (Eph 1:3). This means believers:",
        "type": "multiple_choice",
        "options": [
            {"text": "Already possess every spiritual blessing as their inheritance now", "is_correct": True},  # A - CORRECT
            {"text": "Will receive blessings in heaven after they die if they obey", "is_correct": False},
            {"text": "Must pray to unlock blessings that are currently withheld", "is_correct": False},
            {"text": "Earn additional blessings through faithful service over time", "is_correct": False}
        ]
    },
    {
        "category": "Blessed in Christ — Our Spiritual Inheritance",
        "text": "According to Ephesians 1, God chose us in Christ 'before the foundation of the world' so that we would be:",
        "type": "multiple_choice",
        "options": [
            {"text": "Free from all suffering and hardship in this present life", "is_correct": False},
            {"text": "Wealthy and successful as proof of His favor on earth", "is_correct": False},
            {"text": "Superior to those who have not yet believed in Christ", "is_correct": False},
            {"text": "Holy and blameless before Him — adopted as His children", "is_correct": True}  # D - CORRECT
        ]
    },
    {
        "category": "Blessed in Christ — Our Spiritual Inheritance",
        "text": "Paul says you were chosen, predestined, adopted, redeemed, forgiven, and sealed — all 'in Christ.' These aren't things you earned; they're gifts given before you existed. How does knowing your identity is rooted in God's choice (not your performance) change how you see yourself? Which of these truths do you most need to believe today?",
        "type": "open_ended",
        "options": []
    },
    {
        "category": "Blessed in Christ — Our Spiritual Inheritance",
        "text": "Ephesians 1:18 prays that you would know 'the riches of his glorious inheritance in the saints.' God doesn't just give you an inheritance — He considers YOU His inheritance. How does it affect you to know that God treasures you? Do you live like someone who is that valued?",
        "type": "open_ended",
        "options": []
    },
    # ===========================================
    # CATEGORY: Grace & Salvation — Dead Made Alive (3 questions: 2 MC, 1 OE)
    # ===========================================
    {
        "category": "Grace & Salvation — Dead Made Alive",
        "text": "Ephesians 2:1-3 describes humanity's condition before Christ as:",
        "type": "multiple_choice",
        "options": [
            {"text": "Spiritually sick and in need of moral improvement and guidance", "is_correct": False},
            {"text": "Ignorant of God but actively seeking truth and meaning", "is_correct": False},
            {"text": "Dead in sins, following the world, flesh, and the devil", "is_correct": True},  # C - CORRECT
            {"text": "Basically good people who occasionally made poor choices", "is_correct": False}
        ]
    },
    {
        "category": "Grace & Salvation — Dead Made Alive",
        "text": "'For by grace you have been saved through faith. And this is not your own doing; it is the gift of God' (Eph 2:8). Paul emphasizes it's 'not your own doing' because:",
        "type": "multiple_choice",
        "options": [
            {"text": "Only certain predestined people are capable of having faith", "is_correct": False},
            {"text": "Salvation is entirely God's work so no one can boast", "is_correct": True},  # B - CORRECT
            {"text": "Works become important after the initial moment of faith", "is_correct": False},
            {"text": "Human effort plays a significant but secondary role in salvation", "is_correct": False}
        ]
    },
    {
        "category": "Grace & Salvation — Dead Made Alive",
        "text": "Paul says you were 'dead' — not sick, not struggling, but dead in sin. Dead people can't help themselves. Then God, 'rich in mercy,' made you alive. How does understanding that you were spiritually dead — and that God initiated your rescue — shape your gratitude and humility? Where do you still try to take credit for what God has done?",
        "type": "open_ended",
        "options": []
    },
    # ===========================================
    # CATEGORY: One New Humanity — Unity in Christ (4 questions: 2 MC, 2 OE)
    # ===========================================
    {
        "category": "One New Humanity — Unity in Christ",
        "text": "In Ephesians 2:14, Paul says Christ 'has made us both one and has broken down the dividing wall of hostility.' The 'dividing wall' refers to:",
        "type": "multiple_choice",
        "options": [
            {"text": "The literal wall Herod built around the temple courts", "is_correct": False},
            {"text": "The distance between heaven and earth before the incarnation", "is_correct": False},
            {"text": "The separation between rich and poor in Roman society", "is_correct": False},
            {"text": "The barrier between Jews and Gentiles — now removed in Christ", "is_correct": True}  # D - CORRECT
        ]
    },
    {
        "category": "One New Humanity — Unity in Christ",
        "text": "Paul describes the church as God's 'household' built on the foundation of apostles and prophets, with Christ Jesus as:",
        "type": "multiple_choice",
        "options": [
            {"text": "The cornerstone — the essential reference for the whole structure", "is_correct": True},  # A - CORRECT
            {"text": "The architect who designed the building's blueprints", "is_correct": False},
            {"text": "The owner who will inspect the finished construction", "is_correct": False},
            {"text": "The roof that protects the building from outside threats", "is_correct": False}
        ]
    },
    {
        "category": "One New Humanity — Unity in Christ",
        "text": "Jew and Gentile — groups that hated each other — are made 'one new humanity' in Christ. The cross doesn't just reconcile us to God vertically; it reconciles us to each other horizontally. What divisions exist in your community or church? How does the gospel demand that we pursue unity across barriers that the world considers permanent?",
        "type": "open_ended",
        "options": []
    },
    {
        "category": "One New Humanity — Unity in Christ",
        "text": "Paul says we are 'members of the household of God' (Eph 2:19). The church isn't an organization you join — it's a family you belong to. How well do you live out that reality? Are there believers you've written off or kept at arm's length? What would it look like to treat the church as your actual family?",
        "type": "open_ended",
        "options": []
    },
    # ===========================================
    # CATEGORY: The Supremacy of Christ — Fullness in Him (3 questions: 2 MC, 1 OE)
    # ===========================================
    {
        "category": "The Supremacy of Christ — Fullness in Him",
        "text": "Colossians 1:15-17 declares that Christ is 'the image of the invisible God, the firstborn over all creation.' 'Firstborn' here means:",
        "type": "multiple_choice",
        "options": [
            {"text": "Jesus was the first being God ever created in eternity past", "is_correct": False},
            {"text": "Jesus was born before all other humans in history", "is_correct": False},
            {"text": "Jesus holds the rank of supreme heir and ruler over all", "is_correct": True},  # C - CORRECT
            {"text": "Jesus earned His position through perfect obedience to God", "is_correct": False}
        ]
    },
    {
        "category": "The Supremacy of Christ — Fullness in Him",
        "text": "Paul warns the Colossians not to be taken 'captive by philosophy and empty deceit' (Col 2:8). His concern was that they would:",
        "type": "multiple_choice",
        "options": [
            {"text": "Reject all forms of wisdom and knowledge as worldly", "is_correct": False},
            {"text": "Engage in debates that distract from practical ministry", "is_correct": False},
            {"text": "Stop studying and become intellectually lazy in their faith", "is_correct": False},
            {"text": "Add human traditions and rules to the sufficiency of Christ", "is_correct": True}  # D - CORRECT
        ]
    },
    {
        "category": "The Supremacy of Christ — Fullness in Him",
        "text": "'In him the whole fullness of deity dwells bodily, and you have been filled in him' (Col 2:9-10). Christ lacks nothing — and in Him, neither do you. Where are you tempted to look for fullness, satisfaction, or identity outside of Christ? What are you adding to Jesus as if He weren't enough?",
        "type": "open_ended",
        "options": []
    },
    # ===========================================
    # CATEGORY: The Mystery Revealed — Christ in You (3 questions: 2 MC, 1 OE)
    # ===========================================
    {
        "category": "The Mystery Revealed — Christ in You",
        "text": "Paul says the 'mystery hidden for ages' but now revealed is:",
        "type": "multiple_choice",
        "options": [
            {"text": "The secret knowledge available only to spiritually elite believers", "is_correct": False},
            {"text": "A coded message about the end times and Christ's return", "is_correct": False},
            {"text": "Christ in you, the hope of glory — Gentiles included in God's plan", "is_correct": True},  # C - CORRECT
            {"text": "The identity of the Antichrist and the timing of judgment", "is_correct": False}
        ]
    },
    {
        "category": "The Mystery Revealed — Christ in You",
        "text": "In Ephesians 3, Paul describes himself as 'the very least of all the saints' yet given grace to:",
        "type": "multiple_choice",
        "options": [
            {"text": "Preach to the Gentiles the unsearchable riches of Christ", "is_correct": True},  # A - CORRECT
            {"text": "Rule over the other apostles as their designated leader", "is_correct": False},
            {"text": "Perform greater miracles than any prophet before him", "is_correct": False},
            {"text": "Write more books of the Bible than any other author", "is_correct": False}
        ]
    },
    {
        "category": "The Mystery Revealed — Christ in You",
        "text": "'Christ in you, the hope of glory' (Col 1:27). The mystery isn't just that Christ exists — it's that He lives IN you. The God of the universe has taken up residence in your life. How aware are you of Christ's presence in you daily? How would you live differently if you constantly remembered that Christ is IN you?",
        "type": "open_ended",
        "options": []
    },
    # ===========================================
    # CATEGORY: Walking Worthy — The New Self (5 questions: 3 MC, 2 OE)
    # ===========================================
    {
        "category": "Walking Worthy — The New Self",
        "text": "Paul urges believers to 'walk in a manner worthy of the calling to which you have been called' (Eph 4:1). This 'worthy walk' is motivated by:",
        "type": "multiple_choice",
        "options": [
            {"text": "Fear of losing salvation if we fail to live up to standards", "is_correct": False},
            {"text": "The desire to earn rewards and higher status in heaven", "is_correct": False},
            {"text": "Obligation to repay God for what He has done for us", "is_correct": False},
            {"text": "Gratitude for grace already received — identity producing behavior", "is_correct": True}  # D - CORRECT
        ]
    },
    {
        "category": "Walking Worthy — The New Self",
        "text": "In Colossians 3, Paul instructs believers to 'put to death' earthly things and 'put on' the new self. This language suggests:",
        "type": "multiple_choice",
        "options": [
            {"text": "Salvation eliminates the struggle with sin immediately", "is_correct": False},
            {"text": "Active, intentional effort is required — but empowered by grace", "is_correct": True},  # B - CORRECT
            {"text": "Christians must rely entirely on willpower to defeat sin", "is_correct": False},
            {"text": "Only serious sins need to be addressed; minor ones are tolerable", "is_correct": False}
        ]
    },
    {
        "category": "Walking Worthy — The New Self",
        "text": "'Be filled with the Spirit' (Eph 5:18) is contrasted with being drunk with wine. Being 'filled' with the Spirit means:",
        "type": "multiple_choice",
        "options": [
            {"text": "A one-time experience that never needs to be repeated", "is_correct": False},
            {"text": "Losing control of yourself in an ecstatic, emotional state", "is_correct": False},
            {"text": "Speaking in tongues as the required evidence of filling", "is_correct": False},
            {"text": "Being continually controlled and empowered by the Spirit", "is_correct": True}  # D - CORRECT
        ]
    },
    {
        "category": "Walking Worthy — The New Self",
        "text": "'Put off the old self... put on the new self' (Eph 4:22-24). Paul uses the imagery of changing clothes. What 'old clothes' — habits, attitudes, patterns — are you still wearing that don't fit who you are in Christ? What would it look like to 'put on' the new self in that specific area?",
        "type": "open_ended",
        "options": []
    },
    {
        "category": "Walking Worthy — The New Self",
        "text": "Colossians 3:12 says, 'Put on then, as God's chosen people, holy and beloved, compassionate hearts, kindness, humility...' Notice: you put on virtue BECAUSE you're already chosen, holy, and beloved — not to become those things. How does acting FROM your identity (rather than FOR your identity) change your approach to obedience and growth?",
        "type": "open_ended",
        "options": []
    },
    # ===========================================
    # CATEGORY: Spiritual Warfare — Standing Firm (3 questions: 2 MC, 1 OE)
    # ===========================================
    {
        "category": "Spiritual Warfare — Standing Firm",
        "text": "Paul says 'we do not wrestle against flesh and blood, but against... spiritual forces of evil' (Eph 6:12). This means believers should:",
        "type": "multiple_choice",
        "options": [
            {"text": "Ignore human conflict since only spiritual battles matter", "is_correct": False},
            {"text": "Blame every difficulty on direct demonic attack or possession", "is_correct": False},
            {"text": "Recognize the real enemy and fight with spiritual weapons", "is_correct": True},  # C - CORRECT
            {"text": "Avoid all engagement with culture and withdraw from society", "is_correct": False}
        ]
    },
    {
        "category": "Spiritual Warfare — Standing Firm",
        "text": "The 'armor of God' in Ephesians 6 includes the belt of truth, breastplate of righteousness, shoes of the gospel, shield of faith, helmet of salvation, and sword of the Spirit. The only offensive weapon listed is:",
        "type": "multiple_choice",
        "options": [
            {"text": "The sword of the Spirit, which is the Word of God", "is_correct": True},  # A - CORRECT
            {"text": "The breastplate of righteousness for attacking the enemy", "is_correct": False},
            {"text": "The shield of faith for advancing against opposition", "is_correct": False},
            {"text": "The helmet of salvation for charging into battle boldly", "is_correct": False}
        ]
    },
    {
        "category": "Spiritual Warfare — Standing Firm",
        "text": "Paul ends Ephesians not with comfort but with battle language — armor, standing firm, struggling against evil. The Christian life is warfare. Where are you currently under attack — spiritually, mentally, relationally? Which piece of the armor do you most need to 'put on' right now? How do you practically do that?",
        "type": "open_ended",
        "options": []
    },
]

def main():
    print("=" * 60)
    print("In Christ: Ephesians & Colossians Assessment Setup")
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
                print(f"✅ Created In Christ: Ephesians & Colossians Assessment template: {template_id}")
            
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
                question_code = f"EPHCOL_{question_order:03d}"
                
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
            print(f"✅ SUCCESS! Created In Christ: Ephesians & Colossians Assessment")
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
