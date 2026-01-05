"""
Script to create the Prayer Life Assessment
Run as: python setup_prayer_assessment.py
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
ASSESSMENT_KEY = "prayer_v1"
ASSESSMENT_NAME = "Prayer Life"
ASSESSMENT_DESCRIPTION = """Explore the biblical foundation and practice of prayer — from access through Christ to the model of the Lord's Prayer, persistence, hindrances, praying in the Spirit, and the example of Jesus Himself. This assessment examines your prayer life through gospel-centered questions that help you grow in intimacy with God. 27 questions (16 multiple choice, 11 open-ended) across 7 categories."""

# Questions organized by category
# NOTE: Correct answers are distributed across positions A, B, C, D
QUESTIONS_DATA = [
    # ===========================================
    # CATEGORY: The Foundation of Prayer — Access Through Christ (4 questions: 2 MC, 2 OE)
    # ===========================================
    {
        "category": "The Foundation of Prayer — Access Through Christ",
        "text": "According to the New Testament, believers can approach God confidently in prayer because:",
        "type": "multiple_choice",
        "options": [
            {"text": "We have earned the right through righteous living", "is_correct": False},
            {"text": "Jesus' sacrifice opened the way — we have access to the Father through Him", "is_correct": True},  # B - CORRECT
            {"text": "God is obligated to hear everyone equally", "is_correct": False},
            {"text": "Prayer is a human right given to all people", "is_correct": False}
        ]
    },
    {
        "category": "The Foundation of Prayer — Access Through Christ",
        "text": "The writer of Hebrews encourages us to 'approach God's throne of grace with confidence' (Heb 4:16). This confidence is based on:",
        "type": "multiple_choice",
        "options": [
            {"text": "Our strong faith and spiritual maturity", "is_correct": False},
            {"text": "Our good track record of obedience", "is_correct": False},
            {"text": "Jesus our High Priest who sympathizes with our weaknesses", "is_correct": True},  # C - CORRECT
            {"text": "The number of times we've prayed before", "is_correct": False}
        ]
    },
    {
        "category": "The Foundation of Prayer — Access Through Christ",
        "text": "Before Christ, only the high priest could enter God's presence — and only once a year. Now, through Jesus, you can come boldly anytime. How does understanding that Jesus opened the way affect how you approach prayer? Do you come with confidence or hesitation? Why?",
        "type": "open_ended",
        "options": []
    },
    {
        "category": "The Foundation of Prayer — Access Through Christ",
        "text": "Jesus taught His disciples to pray 'Our Father' — prayer begins with relationship, not ritual. How would your prayer life change if you truly believed you were talking to a loving Father who delights in you, rather than a distant God you need to impress?",
        "type": "open_ended",
        "options": []
    },
    # ===========================================
    # CATEGORY: The Lord's Prayer — A Model for All Prayer (4 questions: 2 MC, 2 OE)
    # ===========================================
    {
        "category": "The Lord's Prayer — A Model for All Prayer",
        "text": "In the Lord's Prayer, Jesus taught us to pray 'Your kingdom come, Your will be done' before asking for personal needs. This order teaches us:",
        "type": "multiple_choice",
        "options": [
            {"text": "Prayer should begin with God's glory and purposes before our own requests", "is_correct": True},  # A - CORRECT
            {"text": "Personal needs are unimportant to God", "is_correct": False},
            {"text": "We shouldn't ask for anything for ourselves", "is_correct": False},
            {"text": "God's kingdom won't come unless we pray for it", "is_correct": False}
        ]
    },
    {
        "category": "The Lord's Prayer — A Model for All Prayer",
        "text": "'Give us today our daily bread' teaches us:",
        "type": "multiple_choice",
        "options": [
            {"text": "We should only pray for physical food", "is_correct": False},
            {"text": "Dependence on God for everyday needs — trusting Him one day at a time", "is_correct": True},  # B - CORRECT
            {"text": "God wants us to worry about tomorrow", "is_correct": False},
            {"text": "Material blessings are the main purpose of prayer", "is_correct": False}
        ]
    },
    {
        "category": "The Lord's Prayer — A Model for All Prayer",
        "text": "'Forgive us our debts, as we also have forgiven our debtors.' Jesus links receiving forgiveness with extending it. Is there anyone you're struggling to forgive? How might unforgiveness be affecting your relationship with God and your prayer life?",
        "type": "open_ended",
        "options": []
    },
    {
        "category": "The Lord's Prayer — A Model for All Prayer",
        "text": "'Lead us not into temptation, but deliver us from evil.' Jesus taught us to pray for protection and spiritual victory. What temptations or spiritual battles do you need to bring to God regularly? How honest are you with God about your struggles?",
        "type": "open_ended",
        "options": []
    },
    # ===========================================
    # CATEGORY: Persistence & Faith in Prayer (4 questions: 3 MC, 1 OE)
    # ===========================================
    {
        "category": "Persistence & Faith in Prayer",
        "text": "In the parable of the persistent widow (Luke 18), Jesus taught that:",
        "type": "multiple_choice",
        "options": [
            {"text": "God is reluctant and must be convinced to help us", "is_correct": False},
            {"text": "We should persist in prayer without giving up — God will bring justice", "is_correct": True},  # B - CORRECT
            {"text": "Only dramatic, public prayers get answered", "is_correct": False},
            {"text": "If prayer isn't answered quickly, we should stop asking", "is_correct": False}
        ]
    },
    {
        "category": "Persistence & Faith in Prayer",
        "text": "James wrote, 'You do not have because you do not ask God' (James 4:2). This teaches:",
        "type": "multiple_choice",
        "options": [
            {"text": "God automatically gives us everything we want", "is_correct": False},
            {"text": "Many needs go unmet simply because we fail to pray", "is_correct": True},  # B - CORRECT
            {"text": "Prayer is a magic formula for getting things", "is_correct": False},
            {"text": "We should demand things from God", "is_correct": False}
        ]
    },
    {
        "category": "Persistence & Faith in Prayer",
        "text": "Jesus said, 'If you believe, you will receive whatever you ask for in prayer' (Matt 21:22). This promise:",
        "type": "multiple_choice",
        "options": [
            {"text": "Guarantees we get anything we want if we believe hard enough", "is_correct": False},
            {"text": "Is connected to asking according to God's will and character", "is_correct": True},  # B - CORRECT
            {"text": "Means faith is measured by answered prayers", "is_correct": False},
            {"text": "Applies only to the apostles", "is_correct": False}
        ]
    },
    {
        "category": "Persistence & Faith in Prayer",
        "text": "Are there prayers you've given up on? Things you stopped asking for because you got tired or discouraged? What does Jesus' teaching on persistence say to you about those abandoned prayers? What might God be doing in the waiting?",
        "type": "open_ended",
        "options": []
    },
    # ===========================================
    # CATEGORY: Hindrances to Prayer (4 questions: 2 MC, 2 OE)
    # ===========================================
    {
        "category": "Hindrances to Prayer",
        "text": "James 4:3 says, 'When you ask, you do not receive, because you ask with wrong motives.' This indicates:",
        "type": "multiple_choice",
        "options": [
            {"text": "God is stingy and looks for reasons to say no", "is_correct": False},
            {"text": "The heart behind our prayers matters — selfish motives hinder prayer", "is_correct": True},  # B - CORRECT
            {"text": "We should never ask for anything for ourselves", "is_correct": False},
            {"text": "Only perfect prayers get answered", "is_correct": False}
        ]
    },
    {
        "category": "Hindrances to Prayer",
        "text": "Peter wrote that husbands should treat their wives with respect 'so that nothing will hinder your prayers' (1 Peter 3:7). This shows:",
        "type": "multiple_choice",
        "options": [
            {"text": "How we treat others affects our relationship with God in prayer", "is_correct": True},  # A - CORRECT
            {"text": "Only married people need to worry about hindered prayers", "is_correct": False},
            {"text": "Prayer is unrelated to daily life", "is_correct": False},
            {"text": "Wives don't need to treat husbands well", "is_correct": False}
        ]
    },
    {
        "category": "Hindrances to Prayer",
        "text": "Isaiah 59:2 says sin creates separation between us and God, hindering prayer. Is there unconfessed sin, bitterness, or disobedience in your life that might be creating distance? What would it look like to clear the air with God right now?",
        "type": "open_ended",
        "options": []
    },
    {
        "category": "Hindrances to Prayer",
        "text": "Jesus said if you're offering your gift at the altar and remember someone has something against you, leave and first be reconciled (Matt 5:23-24). Are there broken relationships affecting your prayer life? Who might you need to pursue reconciliation with?",
        "type": "open_ended",
        "options": []
    },
    # ===========================================
    # CATEGORY: Praying in the Spirit & in Jesus' Name (4 questions: 2 MC, 2 OE)
    # ===========================================
    {
        "category": "Praying in the Spirit & in Jesus' Name",
        "text": "When Jesus said, 'Whatever you ask in my name, I will do it' (John 14:13), praying 'in Jesus' name' means:",
        "type": "multiple_choice",
        "options": [
            {"text": "Adding 'in Jesus' name' at the end makes any prayer work", "is_correct": False},
            {"text": "Praying according to Jesus' character, will, and authority — as His representative", "is_correct": True},  # B - CORRECT
            {"text": "Jesus becomes obligated to give us whatever we want", "is_correct": False},
            {"text": "A magic phrase that guarantees results", "is_correct": False}
        ]
    },
    {
        "category": "Praying in the Spirit & in Jesus' Name",
        "text": "Paul wrote that 'the Spirit helps us in our weakness. We do not know what we ought to pray for, but the Spirit himself intercedes for us' (Rom 8:26). This means:",
        "type": "multiple_choice",
        "options": [
            {"text": "We don't need to pray because the Spirit does it for us", "is_correct": False},
            {"text": "Even when we don't know how to pray, the Spirit prays through and for us", "is_correct": True},  # B - CORRECT
            {"text": "Our prayers are useless without special spiritual gifts", "is_correct": False},
            {"text": "The Spirit only helps mature Christians", "is_correct": False}
        ]
    },
    {
        "category": "Praying in the Spirit & in Jesus' Name",
        "text": "'We do not know what we ought to pray for' — have you ever felt stuck, not knowing how to pray? How does it comfort you that the Spirit intercedes when words fail? How might you lean into the Spirit's help more in your prayer life?",
        "type": "open_ended",
        "options": []
    },
    {
        "category": "Praying in the Spirit & in Jesus' Name",
        "text": "Praying 'in Jesus' name' isn't a formula — it's praying as Jesus' representative, aligned with His heart. How might your prayers change if you asked, 'Would Jesus endorse this request? Does this align with His purposes?'",
        "type": "open_ended",
        "options": []
    },
    # ===========================================
    # CATEGORY: Types of Prayer — ACTS (4 questions: 3 MC, 1 OE)
    # ===========================================
    {
        "category": "Types of Prayer — ACTS",
        "text": "The Psalms model prayers of lament — bringing pain, anger, and confusion to God. This teaches:",
        "type": "multiple_choice",
        "options": [
            {"text": "We should hide negative emotions from God", "is_correct": False},
            {"text": "Honest, raw prayers are welcome — God can handle our complaints and questions", "is_correct": True},  # B - CORRECT
            {"text": "Complaining to God is always sinful", "is_correct": False},
            {"text": "We should only pray when we feel positive", "is_correct": False}
        ]
    },
    {
        "category": "Types of Prayer — ACTS",
        "text": "Paul commanded believers to 'pray without ceasing' (1 Thess 5:17). This means:",
        "type": "multiple_choice",
        "options": [
            {"text": "Spending every moment in formal prayer", "is_correct": False},
            {"text": "Never doing anything except praying", "is_correct": False},
            {"text": "Living in constant awareness of God's presence — ongoing conversation throughout the day", "is_correct": True},  # C - CORRECT
            {"text": "Repeating prayers continuously like a mantra", "is_correct": False}
        ]
    },
    {
        "category": "Types of Prayer — ACTS",
        "text": "'Do not be anxious about anything, but in every situation, by prayer and petition, with thanksgiving, present your requests to God' (Phil 4:6). Paul includes thanksgiving because:",
        "type": "multiple_choice",
        "options": [
            {"text": "Gratitude reorients our hearts and reminds us of God's faithfulness", "is_correct": True},  # A - CORRECT
            {"text": "God won't answer unless we thank Him first", "is_correct": False},
            {"text": "It's just polite religious etiquette", "is_correct": False},
            {"text": "Thanksgiving cancels out worry automatically", "is_correct": False}
        ]
    },
    {
        "category": "Types of Prayer — ACTS",
        "text": "The ACTS model covers Adoration, Confession, Thanksgiving, and Supplication (requests). Which of these is most natural for you? Which do you tend to neglect? How might a more balanced prayer life deepen your relationship with God?",
        "type": "open_ended",
        "options": []
    },
    # ===========================================
    # CATEGORY: The Example of Jesus & Transforming Power of Prayer (3 questions: 2 MC, 1 OE)
    # ===========================================
    {
        "category": "The Example of Jesus & Transforming Power of Prayer",
        "text": "Despite His divine nature, Jesus regularly withdrew to pray (Luke 5:16). This shows:",
        "type": "multiple_choice",
        "options": [
            {"text": "Even Jesus needed to earn God's favor", "is_correct": False},
            {"text": "Prayer was essential to Jesus' relationship with the Father and His mission", "is_correct": True},  # B - CORRECT
            {"text": "Jesus was setting a good example but didn't need to pray Himself", "is_correct": False},
            {"text": "Prayer is only for difficult times", "is_correct": False}
        ]
    },
    {
        "category": "The Example of Jesus & Transforming Power of Prayer",
        "text": "In Gethsemane, Jesus prayed, 'Not my will, but yours be done' (Luke 22:42). This teaches:",
        "type": "multiple_choice",
        "options": [
            {"text": "We should never express our desires to God", "is_correct": False},
            {"text": "Jesus was uncertain about God's plan", "is_correct": False},
            {"text": "Ultimate surrender — bringing honest desires while submitting to the Father's will", "is_correct": True},  # C - CORRECT
            {"text": "Prayer is about changing God's mind", "is_correct": False}
        ]
    },
    {
        "category": "The Example of Jesus & Transforming Power of Prayer",
        "text": "Jesus, in His darkest hour, prayed with raw honesty ('Take this cup from me') AND complete surrender ('Not my will, but yours'). How do you hold both together — bringing your honest desires to God while surrendering to His will? What are you holding tightly that you need to release into God's hands?",
        "type": "open_ended",
        "options": []
    },
]

def main():
    print("=" * 60)
    print("Prayer Life Assessment Setup")
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
                print(f"✅ Created Prayer Life Assessment template: {template_id}")
            
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
                question_code = f"PRAY_{question_order:03d}"
                
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
            print(f"✅ SUCCESS! Created Prayer Life Assessment")
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
