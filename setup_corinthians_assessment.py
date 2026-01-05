"""
Script to create the 1st & 2nd Corinthians Assessment
Run as: python setup_corinthians_assessment.py
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
ASSESSMENT_KEY = "corinthians_v1"
ASSESSMENT_NAME = "1st & 2nd Corinthians"
ASSESSMENT_DESCRIPTION = """Explore Paul's letters to the Corinthian church — addressing division, immorality, spiritual gifts, the resurrection, and the paradox of power in weakness. This assessment draws gospel truths from the wisdom of the cross, the body of Christ, Christian freedom, new creation in Christ, and God's sufficient grace. 27 questions (16 multiple choice, 11 open-ended) across 7 categories."""

# Questions organized by category
# NOTE: Correct answers are distributed across positions A, B, C, D
QUESTIONS_DATA = [
    # ===========================================
    # CATEGORY: Unity in Christ & the Wisdom of the Cross (4 questions: 2 MC, 2 OE)
    # ===========================================
    {
        "category": "Unity in Christ & the Wisdom of the Cross",
        "text": "The Corinthian church was divided because members were saying:",
        "type": "multiple_choice",
        "options": [
            {"text": "'I follow Paul,' 'I follow Apollos,' 'I follow Cephas,' 'I follow Christ' — creating factions around leaders", "is_correct": True},  # A - CORRECT
            {"text": "They disagreed about which Old Testament books were authoritative", "is_correct": False},
            {"text": "Some wanted to return to Judaism while others embraced Greek philosophy", "is_correct": False},
            {"text": "They couldn't agree on a location for their meetings", "is_correct": False}
        ]
    },
    {
        "category": "Unity in Christ & the Wisdom of the Cross",
        "text": "Paul declared that 'the message of the cross is foolishness to those who are perishing, but to us who are being saved it is the power of God' (1 Cor 1:18). He preached Christ crucified because:",
        "type": "multiple_choice",
        "options": [
            {"text": "It was the simplest message for uneducated people", "is_correct": False},
            {"text": "The cross reveals God's power and wisdom, shaming human wisdom and strength", "is_correct": True},  # B - CORRECT
            {"text": "He didn't know enough philosophy to debate the Greeks", "is_correct": False},
            {"text": "The resurrection was too controversial to emphasize", "is_correct": False}
        ]
    },
    {
        "category": "Unity in Christ & the Wisdom of the Cross",
        "text": "Paul refused to build the church on impressive speech or human wisdom — only on 'Christ and him crucified' (1 Cor 2:2). How does the cross challenge our culture's definitions of success, power, and influence? In what ways are you tempted to trust in your own wisdom or abilities rather than the foolishness of the gospel?",
        "type": "open_ended",
        "options": []
    },
    {
        "category": "Unity in Christ & the Wisdom of the Cross",
        "text": "The Corinthians divided over personalities: 'I follow Paul... I follow Apollos.' We still divide over pastors, denominations, and theological tribes. What causes you to elevate human leaders or camps over Christ Himself? How does the gospel create unity across differences?",
        "type": "open_ended",
        "options": []
    },
    # ===========================================
    # CATEGORY: Holiness & the Body as Temple (4 questions: 2 MC, 2 OE)
    # ===========================================
    {
        "category": "Holiness & the Body as Temple",
        "text": "Paul commanded the Corinthians to remove an immoral man from their fellowship (1 Cor 5) because:",
        "type": "multiple_choice",
        "options": [
            {"text": "The church should judge everyone in society", "is_correct": False},
            {"text": "A little yeast works through the whole batch of dough — tolerating sin affects the whole community", "is_correct": True},  # B - CORRECT
            {"text": "The man had committed an unforgivable sin", "is_correct": False},
            {"text": "Paul wanted to demonstrate his authority over them", "is_correct": False}
        ]
    },
    {
        "category": "Holiness & the Body as Temple",
        "text": "Paul's argument against sexual immorality was based on the truth that:",
        "type": "multiple_choice",
        "options": [
            {"text": "Greek culture was too permissive", "is_correct": False},
            {"text": "The body is temporary and doesn't matter spiritually", "is_correct": False},
            {"text": "Your body is a temple of the Holy Spirit — you were bought at a price", "is_correct": True},  # C - CORRECT
            {"text": "Sexual sin is worse than all other sins", "is_correct": False}
        ]
    },
    {
        "category": "Holiness & the Body as Temple",
        "text": "Paul said, 'You are not your own; you were bought at a price. Therefore honor God with your bodies' (1 Cor 6:19-20). How does understanding that Jesus purchased you with His blood change how you view your body, your choices, and your sexuality? What areas of your life need to be surrendered to His ownership?",
        "type": "open_ended",
        "options": []
    },
    {
        "category": "Holiness & the Body as Temple",
        "text": "The Corinthians lived in a city famous for immorality — the culture said 'anything goes.' Yet Paul called them to radical holiness. How do you navigate being in the world but not of it? Where do you feel the most pressure to conform to cultural standards that contradict the gospel?",
        "type": "open_ended",
        "options": []
    },
    # ===========================================
    # CATEGORY: Christian Freedom & Love for Others (4 questions: 2 MC, 2 OE)
    # ===========================================
    {
        "category": "Christian Freedom & Love for Others",
        "text": "Regarding food offered to idols, Paul taught that:",
        "type": "multiple_choice",
        "options": [
            {"text": "Christians must never eat such food under any circumstances", "is_correct": False},
            {"text": "Knowledge puffs up, but love builds up — freedom should be limited by love for weaker believers", "is_correct": True},  # B - CORRECT
            {"text": "Stronger Christians should correct weaker ones until they understand their freedom", "is_correct": False},
            {"text": "The issue was unimportant and not worth discussing", "is_correct": False}
        ]
    },
    {
        "category": "Christian Freedom & Love for Others",
        "text": "Paul said, 'I have become all things to all people so that by all possible means I might save some' (1 Cor 9:22). This means:",
        "type": "multiple_choice",
        "options": [
            {"text": "He compromised the gospel to make it more appealing", "is_correct": False},
            {"text": "He adapted his approach and gave up personal rights to remove barriers to the gospel", "is_correct": True},  # B - CORRECT
            {"text": "He told people whatever they wanted to hear", "is_correct": False},
            {"text": "He blended Christianity with other religions", "is_correct": False}
        ]
    },
    {
        "category": "Christian Freedom & Love for Others",
        "text": "Paul had the 'right' to eat whatever he wanted, but he voluntarily limited his freedom for the sake of others' consciences. What freedoms might you need to set aside — not because they're sinful, but because love for others matters more? How does the gospel shape your view of personal rights?",
        "type": "open_ended",
        "options": []
    },
    {
        "category": "Christian Freedom & Love for Others",
        "text": "'Everything is permissible, but not everything is beneficial' (1 Cor 10:23). Christian freedom isn't about doing whatever you want — it's freedom to love and serve. Where in your life has 'freedom' become an excuse for selfishness? How can you use your freedom to build others up?",
        "type": "open_ended",
        "options": []
    },
    # ===========================================
    # CATEGORY: Spiritual Gifts & the Body of Christ (4 questions: 3 MC, 1 OE)
    # ===========================================
    {
        "category": "Spiritual Gifts & the Body of Christ",
        "text": "Paul compared the church to a human body to teach that:",
        "type": "multiple_choice",
        "options": [
            {"text": "Some members are more important than others", "is_correct": False},
            {"text": "Every part is needed, and there should be no division — each member belongs to the others", "is_correct": True},  # B - CORRECT
            {"text": "The head (pastor) controls everything the body does", "is_correct": False},
            {"text": "Weaker members should try to become stronger ones", "is_correct": False}
        ]
    },
    {
        "category": "Spiritual Gifts & the Body of Christ",
        "text": "In the famous 'love chapter' (1 Cor 13), Paul says that without love:",
        "type": "multiple_choice",
        "options": [
            {"text": "Spiritual gifts can still be effective for God's purposes", "is_correct": False},
            {"text": "We should focus on acquiring more gifts", "is_correct": False},
            {"text": "Even the most impressive gifts — prophecy, knowledge, faith, sacrifice — are nothing", "is_correct": True},  # C - CORRECT
            {"text": "We should avoid using our gifts until we mature", "is_correct": False}
        ]
    },
    {
        "category": "Spiritual Gifts & the Body of Christ",
        "text": "Regarding the gift of tongues in corporate worship, Paul instructed:",
        "type": "multiple_choice",
        "options": [
            {"text": "Everyone should speak in tongues as evidence of the Spirit", "is_correct": False},
            {"text": "Tongues should never be used in church gatherings", "is_correct": False},
            {"text": "Everything should be done for strengthening the church — in an orderly way", "is_correct": True},  # C - CORRECT
            {"text": "Tongues were only for the apostolic age", "is_correct": False}
        ]
    },
    {
        "category": "Spiritual Gifts & the Body of Christ",
        "text": "'The eye cannot say to the hand, \"I don't need you!\"' (1 Cor 12:21). We need each other — the body isn't complete without every member. How have you seen the diversity of gifts strengthen your church community? Where might you be tempted to think you don't need others, or that others don't need you?",
        "type": "open_ended",
        "options": []
    },
    # ===========================================
    # CATEGORY: The Resurrection — Our Living Hope (4 questions: 3 MC, 1 OE)
    # ===========================================
    {
        "category": "The Resurrection — Our Living Hope",
        "text": "Paul declared that if Christ has not been raised from the dead:",
        "type": "multiple_choice",
        "options": [
            {"text": "Christianity is still valuable for its moral teachings", "is_correct": False},
            {"text": "Our preaching is useless and our faith is futile — we are still in our sins", "is_correct": True},  # B - CORRECT
            {"text": "We should focus on the teachings of Jesus instead", "is_correct": False},
            {"text": "Heaven is still available through good works", "is_correct": False}
        ]
    },
    {
        "category": "The Resurrection — Our Living Hope",
        "text": "Paul described the resurrection body as:",
        "type": "multiple_choice",
        "options": [
            {"text": "Exactly the same as our current physical body", "is_correct": False},
            {"text": "A purely spiritual existence without any bodily form", "is_correct": False},
            {"text": "Imperishable, glorious, powerful, and spiritual — transformed like Christ's body", "is_correct": True},  # C - CORRECT
            {"text": "Something we cannot know anything about", "is_correct": False}
        ]
    },
    {
        "category": "The Resurrection — Our Living Hope",
        "text": "Paul's triumphant declaration 'Where, O death, is your victory? Where, O death, is your sting?' (1 Cor 15:55) is based on:",
        "type": "multiple_choice",
        "options": [
            {"text": "The hope that we will be remembered after we die", "is_correct": False},
            {"text": "Christ's victory over sin and death through His resurrection", "is_correct": True},  # B - CORRECT
            {"text": "The belief that death is merely an illusion", "is_correct": False},
            {"text": "The promise that we will never experience physical death", "is_correct": False}
        ]
    },
    {
        "category": "The Resurrection — Our Living Hope",
        "text": "Paul said, 'If only for this life we have hope in Christ, we are of all people most to be pitied' (1 Cor 15:19). The resurrection changes everything. How does the certainty of your future resurrection affect how you live today — your priorities, your suffering, your choices? What would change if you truly lived in light of eternity?",
        "type": "open_ended",
        "options": []
    },
    # ===========================================
    # CATEGORY: New Covenant Ministry & Transformation (4 questions: 2 MC, 2 OE)
    # ===========================================
    {
        "category": "New Covenant Ministry & Transformation",
        "text": "Paul described believers as 'letters from Christ... written not with ink but with the Spirit of the living God, not on tablets of stone but on tablets of human hearts' (2 Cor 3:3). This means:",
        "type": "multiple_choice",
        "options": [
            {"text": "Christians should avoid writing anything down", "is_correct": False},
            {"text": "Our transformed lives are the message — the Spirit writes Christ's character on our hearts", "is_correct": True},  # B - CORRECT
            {"text": "The Old Testament is no longer relevant", "is_correct": False},
            {"text": "Education is unnecessary for spiritual growth", "is_correct": False}
        ]
    },
    {
        "category": "New Covenant Ministry & Transformation",
        "text": "'We all, who with unveiled faces contemplate the Lord's glory, are being transformed into his image with ever-increasing glory' (2 Cor 3:18). This transformation happens:",
        "type": "multiple_choice",
        "options": [
            {"text": "Instantly at the moment of conversion", "is_correct": False},
            {"text": "Only after death when we reach heaven", "is_correct": False},
            {"text": "Progressively as we behold Christ — from glory to glory by the Spirit", "is_correct": True},  # C - CORRECT
            {"text": "Through strict obedience to religious rules", "is_correct": False}
        ]
    },
    {
        "category": "New Covenant Ministry & Transformation",
        "text": "Paul said we have this treasure (the gospel) in 'jars of clay' — fragile, ordinary vessels — so that the surpassing power belongs to God (2 Cor 4:7). How does your weakness showcase God's power? Where do you need to stop pretending to have it all together and let God's strength shine through your cracks?",
        "type": "open_ended",
        "options": []
    },
    {
        "category": "New Covenant Ministry & Transformation",
        "text": "'If anyone is in Christ, the new creation has come: The old has gone, the new is here!' (2 Cor 5:17). The gospel doesn't just forgive you — it recreates you. How have you experienced this 'new creation' reality? What 'old things' are you still holding onto that the gospel has already dealt with?",
        "type": "open_ended",
        "options": []
    },
    # ===========================================
    # CATEGORY: Strength in Weakness & God's Sufficient Grace (3 questions: 2 MC, 1 OE)
    # ===========================================
    {
        "category": "Strength in Weakness & God's Sufficient Grace",
        "text": "When Paul pleaded with God three times to remove his 'thorn in the flesh,' God responded:",
        "type": "multiple_choice",
        "options": [
            {"text": "By removing it immediately", "is_correct": False},
            {"text": "'My grace is sufficient for you, for my power is made perfect in weakness'", "is_correct": True},  # B - CORRECT
            {"text": "That Paul needed more faith for healing", "is_correct": False},
            {"text": "That the thorn was punishment for past sins", "is_correct": False}
        ]
    },
    {
        "category": "Strength in Weakness & God's Sufficient Grace",
        "text": "Paul boasted about his weaknesses because:",
        "type": "multiple_choice",
        "options": [
            {"text": "He wanted people to feel sorry for him", "is_correct": False},
            {"text": "When he was weak, Christ's power rested on him — strength comes through weakness", "is_correct": True},  # B - CORRECT
            {"text": "He was trying to lower expectations", "is_correct": False},
            {"text": "Humility was culturally valued in Corinth", "is_correct": False}
        ]
    },
    {
        "category": "Strength in Weakness & God's Sufficient Grace",
        "text": "'My grace is sufficient for you, for my power is made perfect in weakness' (2 Cor 12:9). Paul learned to boast in weakness so Christ's power could rest on him. What 'thorns' in your life have you begged God to remove? How might God be using your weakness to display His strength and deepen your dependence on His grace?",
        "type": "open_ended",
        "options": []
    },
]

def main():
    print("=" * 60)
    print("1st & 2nd Corinthians Assessment Setup")
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
                print(f"✅ Created 1st & 2nd Corinthians Assessment template: {template_id}")
            
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
                question_code = f"COR_{question_order:03d}"
                
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
            print(f"✅ SUCCESS! Created 1st & 2nd Corinthians Assessment")
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
