"""
Script to create the 1st & 2nd Kings Assessment
Run as: python setup_kings_assessment.py
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
ASSESSMENT_KEY = "kings_v1"
ASSESSMENT_NAME = "1st & 2nd Kings"
ASSESSMENT_DESCRIPTION = """Explore the Books of 1st and 2nd Kings — from Solomon's glorious temple to the ashes of exile. This assessment traces the rise and fall of Israel's monarchy, the prophetic ministries of Elijah and Elisha, and the faithfulness of God even in judgment. Gospel-centered open-ended questions help you see how every failed king points to Jesus, the King who never fails. 27 questions (16 multiple choice, 11 open-ended) across 7 categories."""

# Questions organized by category
# NOTE: Correct answers are distributed across positions A, B, C, D
QUESTIONS_DATA = [
    # ===========================================
    # CATEGORY: Solomon's Wisdom & the Temple (4 questions: 2 MC, 2 OE)
    # ===========================================
    {
        "category": "Solomon's Wisdom & the Temple",
        "text": "When God appeared to Solomon and offered him anything he wanted, Solomon asked for:",
        "type": "multiple_choice",
        "options": [
            {"text": "Long life and victory over his enemies", "is_correct": False},
            {"text": "A discerning heart to govern God's people and distinguish right from wrong", "is_correct": True},  # B - CORRECT
            {"text": "Great wealth to build the temple", "is_correct": False},
            {"text": "The death of his father's enemies", "is_correct": False}
        ]
    },
    {
        "category": "Solomon's Wisdom & the Temple",
        "text": "The temple Solomon built was significant because:",
        "type": "multiple_choice",
        "options": [
            {"text": "It was the largest building in the ancient world", "is_correct": False},
            {"text": "It replaced the need for priests and sacrifices", "is_correct": False},
            {"text": "It represented God dwelling among His people — His presence in their midst", "is_correct": True},  # C - CORRECT
            {"text": "It gave Israel military protection from enemies", "is_correct": False}
        ]
    },
    {
        "category": "Solomon's Wisdom & the Temple",
        "text": "Solomon asked for wisdom rather than wealth, power, or long life — and God gave him all of those as well. What does this teach you about seeking God's priorities first? What would you ask for if God offered you anything?",
        "type": "open_ended",
        "options": []
    },
    {
        "category": "Solomon's Wisdom & the Temple",
        "text": "The temple was the place where heaven met earth — where God's glory dwelled among His people. Jesus said, 'Destroy this temple and I will raise it again in three days' (John 2:19), speaking of His body. How does Jesus fulfill what the temple represented? What does it mean that God now dwells in you through the Spirit?",
        "type": "open_ended",
        "options": []
    },
    # ===========================================
    # CATEGORY: Solomon's Fall & the Divided Kingdom (4 questions: 2 MC, 2 OE)
    # ===========================================
    {
        "category": "Solomon's Fall & the Divided Kingdom",
        "text": "Solomon's downfall came because:",
        "type": "multiple_choice",
        "options": [
            {"text": "His foreign wives turned his heart after other gods", "is_correct": True},  # A - CORRECT
            {"text": "He became lazy and neglected the kingdom", "is_correct": False},
            {"text": "He refused to listen to the prophets", "is_correct": False},
            {"text": "He was defeated in battle and lost confidence", "is_correct": False}
        ]
    },
    {
        "category": "Solomon's Fall & the Divided Kingdom",
        "text": "After Solomon's death, the kingdom divided because Rehoboam:",
        "type": "multiple_choice",
        "options": [
            {"text": "Was assassinated by his brother", "is_correct": False},
            {"text": "Rejected the wise counsel of elders and harshly oppressed the people", "is_correct": True},  # B - CORRECT
            {"text": "Converted to the worship of foreign gods", "is_correct": False},
            {"text": "Moved the capital away from Jerusalem", "is_correct": False}
        ]
    },
    {
        "category": "Solomon's Fall & the Divided Kingdom",
        "text": "Solomon started with incredible wisdom and devotion but ended with a divided heart, worshiping foreign gods. What warning does his story give you about guarding your heart over time? What relationships, influences, or compromises might slowly pull your heart away from wholehearted devotion to God?",
        "type": "open_ended",
        "options": []
    },
    {
        "category": "Solomon's Fall & the Divided Kingdom",
        "text": "The kingdom that was united under David and Solomon was torn apart by pride and foolishness. Division has plagued God's people ever since. How have you seen division harm the church or Christian community? What does it look like to pursue unity without compromising truth?",
        "type": "open_ended",
        "options": []
    },
    # ===========================================
    # CATEGORY: Elijah — Prophet of Fire (4 questions: 3 MC, 1 OE)
    # ===========================================
    {
        "category": "Elijah — Prophet of Fire",
        "text": "During the contest on Mount Carmel, Elijah challenged the prophets of Baal and then:",
        "type": "multiple_choice",
        "options": [
            {"text": "Called down fire from heaven that consumed the sacrifice, the wood, the stones, and the water", "is_correct": True},  # A - CORRECT
            {"text": "Defeated them in hand-to-hand combat", "is_correct": False},
            {"text": "Caused an earthquake that destroyed their altar", "is_correct": False},
            {"text": "Made the sun stand still until they surrendered", "is_correct": False}
        ]
    },
    {
        "category": "Elijah — Prophet of Fire",
        "text": "After his great victory on Mount Carmel, Elijah fled into the wilderness because:",
        "type": "multiple_choice",
        "options": [
            {"text": "God told him to hide from Ahab's army", "is_correct": False},
            {"text": "Queen Jezebel threatened to kill him, and he was afraid and exhausted", "is_correct": True},  # B - CORRECT
            {"text": "He wanted to return to his hometown", "is_correct": False},
            {"text": "The people rejected him despite the miracle", "is_correct": False}
        ]
    },
    {
        "category": "Elijah — Prophet of Fire",
        "text": "When God spoke to Elijah at Mount Horeb (Sinai), He was not in the wind, earthquake, or fire, but in:",
        "type": "multiple_choice",
        "options": [
            {"text": "A blinding light", "is_correct": False},
            {"text": "A thundering voice", "is_correct": False},
            {"text": "A gentle whisper (still small voice)", "is_correct": True},  # C - CORRECT
            {"text": "A vision during sleep", "is_correct": False}
        ]
    },
    {
        "category": "Elijah — Prophet of Fire",
        "text": "Elijah went from bold faith on Mount Carmel to fear and depression in the wilderness — in less than a day. Great victories don't make us immune to spiritual and emotional exhaustion. When have you experienced a 'crash' after a spiritual high? How does God's gentle care for Elijah (food, rest, His quiet presence) encourage you in your low seasons?",
        "type": "open_ended",
        "options": []
    },
    # ===========================================
    # CATEGORY: Elisha — Prophet of Grace (4 questions: 2 MC, 2 OE)
    # ===========================================
    {
        "category": "Elisha — Prophet of Grace",
        "text": "When Naaman the Syrian general came to be healed of leprosy, Elisha told him to:",
        "type": "multiple_choice",
        "options": [
            {"text": "Wash seven times in the Jordan River", "is_correct": True},  # A - CORRECT
            {"text": "Offer an expensive sacrifice at the temple", "is_correct": False},
            {"text": "Fast and pray for seven days", "is_correct": False},
            {"text": "Return to Syria and worship the God of Israel there", "is_correct": False}
        ]
    },
    {
        "category": "Elisha — Prophet of Grace",
        "text": "The story of Elisha and the widow's oil (2 Kings 4) demonstrates that:",
        "type": "multiple_choice",
        "options": [
            {"text": "Only wealthy people could receive God's blessing", "is_correct": False},
            {"text": "Miracles only happened for Israelites", "is_correct": False},
            {"text": "God provides abundantly for those in desperate need who come to Him in faith", "is_correct": True},  # C - CORRECT
            {"text": "Prophets were primarily focused on political matters", "is_correct": False}
        ]
    },
    {
        "category": "Elisha — Prophet of Grace",
        "text": "Naaman was a powerful, wealthy Gentile enemy — yet God healed him. Elisha's miracles often reached outsiders, the poor, and the marginalized. How does this foreshadow Jesus' ministry? Who are the 'outsiders' in your life that God might be calling you to reach with grace?",
        "type": "open_ended",
        "options": []
    },
    {
        "category": "Elisha — Prophet of Grace",
        "text": "Naaman almost missed his healing because Elisha's instructions seemed too simple and the Jordan seemed too dirty. He wanted something more impressive. How might pride or expectations prevent you from receiving what God offers? Where might you be overcomplicating obedience?",
        "type": "open_ended",
        "options": []
    },
    # ===========================================
    # CATEGORY: The Kings of Israel & Judah (4 questions: 3 MC, 1 OE)
    # ===========================================
    {
        "category": "The Kings of Israel & Judah",
        "text": "The repeated phrase used to evaluate the kings of Israel (northern kingdom) was:",
        "type": "multiple_choice",
        "options": [
            {"text": "'He did what was right in the eyes of the Lord'", "is_correct": False},
            {"text": "'He did evil in the eyes of the Lord, walking in the ways of Jeroboam'", "is_correct": True},  # B - CORRECT
            {"text": "'He sought the Lord with all his heart'", "is_correct": False},
            {"text": "'He restored the fortunes of Israel'", "is_correct": False}
        ]
    },
    {
        "category": "The Kings of Israel & Judah",
        "text": "King Hezekiah of Judah was commended because:",
        "type": "multiple_choice",
        "options": [
            {"text": "He expanded the kingdom's territory", "is_correct": False},
            {"text": "He formed alliances with powerful nations", "is_correct": False},
            {"text": "He trusted in the Lord, removed the high places, and held fast to God", "is_correct": True},  # C - CORRECT
            {"text": "He rebuilt Solomon's wealth and palace", "is_correct": False}
        ]
    },
    {
        "category": "The Kings of Israel & Judah",
        "text": "King Josiah's reforms began when:",
        "type": "multiple_choice",
        "options": [
            {"text": "He defeated the Assyrians in battle", "is_correct": False},
            {"text": "The Book of the Law was found in the temple during repairs", "is_correct": True},  # B - CORRECT
            {"text": "A prophet confronted him about his sin", "is_correct": False},
            {"text": "He had a dream about judgment", "is_correct": False}
        ]
    },
    {
        "category": "The Kings of Israel & Judah",
        "text": "Most kings in 1st & 2nd Kings failed — even the 'good' ones had serious flaws. The repeated cycle shows that Israel desperately needed a King who would not fail. How does this relentless record of failure prepare you to appreciate Jesus as the faithful King? What hope does Jesus' perfect reign give you?",
        "type": "open_ended",
        "options": []
    },
    # ===========================================
    # CATEGORY: Exile — The Consequences of Unfaithfulness (4 questions: 2 MC, 2 OE)
    # ===========================================
    {
        "category": "Exile — The Consequences of Unfaithfulness",
        "text": "The northern kingdom of Israel fell to Assyria (722 BC) because:",
        "type": "multiple_choice",
        "options": [
            {"text": "They were militarily weak and unprepared", "is_correct": False},
            {"text": "They had rejected God's covenant, worshiped idols, and ignored the prophets", "is_correct": True},  # B - CORRECT
            {"text": "They refused to pay tribute", "is_correct": False},
            {"text": "Their king surrendered without fighting", "is_correct": False}
        ]
    },
    {
        "category": "Exile — The Consequences of Unfaithfulness",
        "text": "When Jerusalem finally fell to Babylon (586 BC), the Babylonians:",
        "type": "multiple_choice",
        "options": [
            {"text": "Made Judah a self-governing province", "is_correct": False},
            {"text": "Left the temple standing as a sign of respect", "is_correct": False},
            {"text": "Destroyed the temple, burned the city, and deported the people", "is_correct": True},  # C - CORRECT
            {"text": "Converted to the worship of Yahweh", "is_correct": False}
        ]
    },
    {
        "category": "Exile — The Consequences of Unfaithfulness",
        "text": "The exile wasn't arbitrary punishment — it was the consequence of centuries of warnings ignored. God sent prophet after prophet, and generation after generation refused to listen. How does this patience before judgment reveal God's character? How does it motivate you to respond to His Word now rather than later?",
        "type": "open_ended",
        "options": []
    },
    {
        "category": "Exile — The Consequences of Unfaithfulness",
        "text": "The people lost everything — their land, their temple, their king, their identity. Yet even in judgment, God preserved a remnant. How do you see hope even in the darkest chapters of Kings? When have you experienced God's faithfulness in a season that felt like exile or loss?",
        "type": "open_ended",
        "options": []
    },
    # ===========================================
    # CATEGORY: Hope in the Midst of Judgment (3 questions: 2 MC, 1 OE)
    # ===========================================
    {
        "category": "Hope in the Midst of Judgment",
        "text": "Even during judgment, God remembered His covenant with David by:",
        "type": "multiple_choice",
        "options": [
            {"text": "Preserving a 'lamp' in Jerusalem — keeping David's line alive", "is_correct": True},  # A - CORRECT
            {"text": "Allowing the northern kingdom to reunite with Judah", "is_correct": False},
            {"text": "Sending angels to protect the temple", "is_correct": False},
            {"text": "Making Israel victorious in every battle", "is_correct": False}
        ]
    },
    {
        "category": "Hope in the Midst of Judgment",
        "text": "The Books of Kings point forward to a coming King because they show:",
        "type": "multiple_choice",
        "options": [
            {"text": "Every human king failed, proving Israel needed a King who would perfectly obey and reign forever", "is_correct": True},  # A - CORRECT
            {"text": "The monarchy was a mistake that should never have happened", "is_correct": False},
            {"text": "Kings were unnecessary if the people simply obeyed the law", "is_correct": False},
            {"text": "David's line ended with the exile", "is_correct": False}
        ]
    },
    {
        "category": "Hope in the Midst of Judgment",
        "text": "1st & 2nd Kings ends with the temple destroyed, the people in exile, and the Davidic king in Babylon — yet the final verses mention King Jehoiachin being released and given a seat at the king's table (2 Kings 25:27-30). It's a tiny glimmer of hope. How does the gospel complete this story? How does Jesus bring you out of exile, restore you to the Father's table, and fulfill every failed promise of the kings?",
        "type": "open_ended",
        "options": []
    },
]

def main():
    print("=" * 60)
    print("1st & 2nd Kings Assessment Setup")
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
                print(f"✅ Created 1st & 2nd Kings Assessment template: {template_id}")
            
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
                question_code = f"KING_{question_order:03d}"
                
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
            print(f"✅ SUCCESS! Created 1st & 2nd Kings Assessment")
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
