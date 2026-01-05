"""
Script to create The Judges Assessment
Run as: python setup_judges_assessment.py
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
ASSESSMENT_KEY = "judges_v1"
ASSESSMENT_NAME = "The Judges"
ASSESSMENT_DESCRIPTION = """Explore the Book of Judges and the repeated cycle of sin, oppression, crying out, and deliverance. This assessment draws gospel truths from Israel's darkest period, covering the judges cycle, Deborah & Barak, Gideon, Jephthah, Samson, the downward spiral, and Israel's desperate need for a true King — pointing to Jesus as the final and perfect Deliverer. 27 questions (16 multiple choice, 11 open-ended) across 7 categories."""

# Questions organized by category
# NOTE: Correct answers are distributed across positions A, B, C, D
QUESTIONS_DATA = [
    # ===========================================
    # CATEGORY: The Cycle of Sin & Deliverance (4 questions: 2 MC, 2 OE)
    # ===========================================
    {
        "category": "The Cycle of Sin & Deliverance",
        "text": "The Book of Judges describes a repeated pattern in Israel's history. What is the correct order of this cycle?",
        "type": "multiple_choice",
        "options": [
            {"text": "Oppression → Sin → Crying out → Deliverance → Peace → Sin again", "is_correct": False},
            {"text": "Sin → Oppression → Crying out → God raises a judge → Deliverance → Peace → Sin again", "is_correct": True},  # B - CORRECT
            {"text": "Peace → Prosperity → Forgetting God → Judgment → Repentance", "is_correct": False},
            {"text": "Faithfulness → Testing → Failure → Restoration → Faithfulness again", "is_correct": False}
        ]
    },
    {
        "category": "The Cycle of Sin & Deliverance",
        "text": "After Joshua's death, God allowed enemy nations to remain in Canaan (Judges 2:20-23) because:",
        "type": "multiple_choice",
        "options": [
            {"text": "Israel's army was too small to defeat them", "is_correct": False},
            {"text": "God wanted to test Israel and see if they would keep His ways", "is_correct": True},  # B - CORRECT
            {"text": "The Canaanites had repented and deserved mercy", "is_correct": False},
            {"text": "Joshua had failed to complete the conquest", "is_correct": False}
        ]
    },
    {
        "category": "The Cycle of Sin & Deliverance",
        "text": "The Judges Cycle reveals that Israel couldn't break free from sin on their own — each generation repeated their parents' mistakes. How does this pattern reflect the human condition and our need for a Savior who can permanently break the power of sin?",
        "type": "open_ended",
        "options": []
    },
    {
        "category": "The Cycle of Sin & Deliverance",
        "text": "Despite Israel's repeated unfaithfulness, God kept raising up deliverers when they cried out. What does this reveal about God's character? How does His patience with Israel encourage you when you struggle with recurring sin?",
        "type": "open_ended",
        "options": []
    },
    # ===========================================
    # CATEGORY: Deborah & Barak — Faith in Action (4 questions: 2 MC, 2 OE)
    # ===========================================
    {
        "category": "Deborah & Barak — Faith in Action",
        "text": "Deborah was unique among the judges because she:",
        "type": "multiple_choice",
        "options": [
            {"text": "Was the only judge who never went to battle", "is_correct": False},
            {"text": "Served as both a prophetess and judge, leading Israel while holding court under a palm tree", "is_correct": True},  # B - CORRECT
            {"text": "Defeated more enemies than any other judge", "is_correct": False},
            {"text": "Was the only judge from the tribe of Judah", "is_correct": False}
        ]
    },
    {
        "category": "Deborah & Barak — Faith in Action",
        "text": "When Deborah told Barak that God commanded him to fight Sisera, Barak responded:",
        "type": "multiple_choice",
        "options": [
            {"text": "With immediate obedience and confidence in God's promise", "is_correct": False},
            {"text": "By asking for a sign to confirm God's word", "is_correct": False},
            {"text": "'If you go with me, I will go; but if you don't go with me, I won't go'", "is_correct": True},  # C - CORRECT
            {"text": "By gathering 10,000 men without hesitation", "is_correct": False}
        ]
    },
    {
        "category": "Deborah & Barak — Faith in Action",
        "text": "Deborah prophesied that because of Barak's hesitation, the glory of victory would go to a woman (Judges 4:9) — and indeed, Jael killed Sisera. God often works through unexpected people in unexpected ways. When have you seen God use 'unlikely' people to accomplish His purposes? What does this teach you about who God chooses to use?",
        "type": "open_ended",
        "options": []
    },
    {
        "category": "Deborah & Barak — Faith in Action",
        "text": "Deborah's song (Judges 5) praises God for the victory and calls out tribes who didn't join the battle. How do you balance personal celebration of God's faithfulness with the call for others to join in God's work? What 'battles' is God calling your community to engage in together?",
        "type": "open_ended",
        "options": []
    },
    # ===========================================
    # CATEGORY: Gideon — Strength in Weakness (4 questions: 3 MC, 1 OE)
    # ===========================================
    {
        "category": "Gideon — Strength in Weakness",
        "text": "When the angel of the Lord appeared to Gideon, he was:",
        "type": "multiple_choice",
        "options": [
            {"text": "Leading Israel's army in battle", "is_correct": False},
            {"text": "Praying at the tabernacle for deliverance", "is_correct": False},
            {"text": "Hiding in a winepress, threshing wheat to hide it from the Midianites", "is_correct": True},  # C - CORRECT
            {"text": "Serving as a priest in his father's household", "is_correct": False}
        ]
    },
    {
        "category": "Gideon — Strength in Weakness",
        "text": "God reduced Gideon's army from 32,000 to 300 men because:",
        "type": "multiple_choice",
        "options": [
            {"text": "The larger army was too difficult to feed and supply", "is_correct": False},
            {"text": "God wanted Israel to know the victory was His, not theirs — 'lest Israel boast'", "is_correct": True},  # B - CORRECT
            {"text": "Only 300 men had proper military training", "is_correct": False},
            {"text": "The rest of the men were from unfaithful tribes", "is_correct": False}
        ]
    },
    {
        "category": "Gideon — Strength in Weakness",
        "text": "Gideon's 300 men defeated the Midianite army using:",
        "type": "multiple_choice",
        "options": [
            {"text": "Superior weapons and military strategy", "is_correct": False},
            {"text": "A surprise night attack with swords and spears", "is_correct": False},
            {"text": "Trumpets, empty jars, and torches — creating confusion in the enemy camp", "is_correct": True},  # C - CORRECT
            {"text": "Poison in the Midianite water supply", "is_correct": False}
        ]
    },
    {
        "category": "Gideon — Strength in Weakness",
        "text": "God called Gideon a 'mighty warrior' while he was hiding in fear (Judges 6:12). God saw what Gideon could become, not just what he was. How does knowing that God sees your potential — not just your current struggles — change how you view yourself and your calling?",
        "type": "open_ended",
        "options": []
    },
    # ===========================================
    # CATEGORY: Jephthah & the Cost of Vows (3 questions: 2 MC, 1 OE)
    # ===========================================
    {
        "category": "Jephthah & the Cost of Vows",
        "text": "Jephthah was rejected by his family because:",
        "type": "multiple_choice",
        "options": [
            {"text": "He had committed a crime in his youth", "is_correct": False},
            {"text": "He was the son of a prostitute, and his half-brothers drove him out", "is_correct": True},  # B - CORRECT
            {"text": "He had abandoned the worship of the Lord", "is_correct": False},
            {"text": "He refused to fight for Israel when first called", "is_correct": False}
        ]
    },
    {
        "category": "Jephthah & the Cost of Vows",
        "text": "Before battle, Jephthah made a vow to the Lord that:",
        "type": "multiple_choice",
        "options": [
            {"text": "He would serve as priest if victorious", "is_correct": False},
            {"text": "He would give a tenth of all spoils to the tabernacle", "is_correct": False},
            {"text": "Whatever came out of his house first to greet him would be offered to the Lord", "is_correct": True},  # C - CORRECT
            {"text": "He would never cut his hair like the Nazirites", "is_correct": False}
        ]
    },
    {
        "category": "Jephthah & the Cost of Vows",
        "text": "Jephthah's rash vow led to tragedy with his daughter (Judges 11:34-40). This story warns about making promises to God carelessly. Jesus taught that our 'yes' should simply be 'yes' (Matthew 5:37). How do you approach commitments to God? Have you ever made a spiritual commitment you later regretted or couldn't keep?",
        "type": "open_ended",
        "options": []
    },
    # ===========================================
    # CATEGORY: Samson — Squandered Gifts & Redemption (4 questions: 3 MC, 1 OE)
    # ===========================================
    {
        "category": "Samson — Squandered Gifts & Redemption",
        "text": "Samson was set apart from birth as a Nazirite, which meant:",
        "type": "multiple_choice",
        "options": [
            {"text": "He was to be a priest serving in the tabernacle", "is_correct": False},
            {"text": "He was to marry only within his tribe", "is_correct": False},
            {"text": "No razor was to touch his head, and he was to abstain from wine and unclean things", "is_correct": True},  # C - CORRECT
            {"text": "He was forbidden from engaging in any form of combat", "is_correct": False}
        ]
    },
    {
        "category": "Samson — Squandered Gifts & Redemption",
        "text": "The source of Samson's supernatural strength was:",
        "type": "multiple_choice",
        "options": [
            {"text": "His physical training and diet from childhood", "is_correct": False},
            {"text": "His long hair, which was the sign of his covenant with God", "is_correct": True},  # B - CORRECT
            {"text": "A special blessing given only to firstborn sons", "is_correct": False},
            {"text": "His anger, which triggered divine power", "is_correct": False}
        ]
    },
    {
        "category": "Samson — Squandered Gifts & Redemption",
        "text": "After Samson was captured and blinded by the Philistines, his final act was:",
        "type": "multiple_choice",
        "options": [
            {"text": "Escaping from prison and returning to lead Israel", "is_correct": False},
            {"text": "Praying for strength one last time and collapsing the temple, killing more Philistines in his death than in his life", "is_correct": True},  # B - CORRECT
            {"text": "Prophesying about a future deliverer who would defeat the Philistines", "is_correct": False},
            {"text": "Repenting publicly and calling Israel to return to God", "is_correct": False}
        ]
    },
    {
        "category": "Samson — Squandered Gifts & Redemption",
        "text": "Samson had incredible God-given potential but repeatedly compromised through his choices with Delilah and others. Yet God still used his final prayer. How does Samson's story illustrate both the tragedy of squandered gifts AND the possibility of redemption? What does it teach you about finishing well despite past failures?",
        "type": "open_ended",
        "options": []
    },
    # ===========================================
    # CATEGORY: The Downward Spiral (4 questions: 2 MC, 2 OE)
    # ===========================================
    {
        "category": "The Downward Spiral",
        "text": "The story of Micah's idol (Judges 17-18) illustrates Israel's spiritual confusion because:",
        "type": "multiple_choice",
        "options": [
            {"text": "Micah hired a Levite as his personal priest for a household idol, blending true and false worship", "is_correct": True},  # A - CORRECT
            {"text": "Micah refused to worship at the tabernacle in Shiloh", "is_correct": False},
            {"text": "The tribe of Dan destroyed Micah's idol and returned to the Lord", "is_correct": False},
            {"text": "Micah's mother dedicated silver to the Lord but then made an idol", "is_correct": False}
        ]
    },
    {
        "category": "The Downward Spiral",
        "text": "The horrific account of the Levite's concubine and the near-destruction of the tribe of Benjamin (Judges 19-21) is compared in the text to:",
        "type": "multiple_choice",
        "options": [
            {"text": "The destruction of the golden calf worshipers", "is_correct": False},
            {"text": "The sins of Sodom and Gomorrah — showing how far Israel had fallen", "is_correct": True},  # B - CORRECT
            {"text": "The rebellion of Korah against Moses", "is_correct": False},
            {"text": "The worship of Baal at Mount Carmel", "is_correct": False}
        ]
    },
    {
        "category": "The Downward Spiral",
        "text": "The final chapters of Judges (17-21) contain some of the darkest stories in Scripture — idolatry, violence, and tribal warfare. These chapters show what happens when God's people abandon His ways. How do you see similar 'downward spirals' in culture today when people reject God's truth? What safeguards help you avoid spiritual drift?",
        "type": "open_ended",
        "options": []
    },
    {
        "category": "The Downward Spiral",
        "text": "In Judges 21:25, we read that 'everyone did what was right in their own eyes.' This phrase summarizes the chaos of the period. In what areas of your life are you tempted to define right and wrong by your own standards rather than God's Word? How can you guard against this?",
        "type": "open_ended",
        "options": []
    },
    # ===========================================
    # CATEGORY: The Need for a True King (4 questions: 2 MC, 2 OE)
    # ===========================================
    {
        "category": "The Need for a True King",
        "text": "The refrain 'In those days Israel had no king' (Judges 17:6, 18:1, 19:1, 21:25) appears multiple times in Judges. This phrase points to:",
        "type": "multiple_choice",
        "options": [
            {"text": "Israel's military weakness without centralized command", "is_correct": False},
            {"text": "Israel's need for godly leadership and ultimately the coming Messiah-King", "is_correct": True},  # B - CORRECT
            {"text": "The failure of the tribal system established by Moses", "is_correct": False},
            {"text": "God's anger at Israel for not appointing a king sooner", "is_correct": False}
        ]
    },
    {
        "category": "The Need for a True King",
        "text": "Unlike the judges who were temporary, flawed deliverers, Jesus as the true Judge and King:",
        "type": "multiple_choice",
        "options": [
            {"text": "Defeats sin permanently, rules with perfect justice, and never fails His people", "is_correct": True},  # A - CORRECT
            {"text": "Comes only to the tribe of Judah and rejects other nations", "is_correct": False},
            {"text": "Uses physical force to establish His kingdom on earth", "is_correct": False},
            {"text": "Requires Israel to earn deliverance through obedience first", "is_correct": False}
        ]
    },
    {
        "category": "The Need for a True King",
        "text": "The judges were deliverers, but none could save Israel permanently. Othniel brought 40 years of peace, then Israel sinned again. Gideon delivered them, then they returned to Baal. How does the repeated failure of the judges to bring lasting change increase your appreciation for Jesus as the final and perfect Deliverer?",
        "type": "open_ended",
        "options": []
    },
    {
        "category": "The Need for a True King",
        "text": "Judges ends in chaos — 'everyone did what was right in their own eyes.' But this points forward to the need for a King. How does Jesus fulfill the role that Israel desperately needed? What does it mean for Jesus to be King over your life today — not just Savior, but Lord who defines right and wrong?",
        "type": "open_ended",
        "options": []
    },
]

def main():
    print("=" * 60)
    print("The Judges Assessment Setup")
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
                print(f"✅ Created The Judges Assessment template: {template_id}")
            
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
                question_code = f"JUDG_{question_order:03d}"
                
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
            print(f"✅ SUCCESS! Created The Judges Assessment")
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
