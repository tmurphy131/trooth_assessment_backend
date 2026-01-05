"""
Script to create the Israel Under Joshua Assessment
Run as: python setup_joshua_assessment.py
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
ASSESSMENT_KEY = "joshua_v1"
ASSESSMENT_NAME = "Israel Under Joshua"
ASSESSMENT_DESCRIPTION = """Explore the narrative of Joshua leading Israel into the Promised Land. This assessment draws gospel truths from the conquest story, covering Joshua's commissioning, Rahab's faith, crossing the Jordan, the fall of Jericho, Israel's failures and restoration, the division of the land, and Joshua's legacy pointing to Christ as the one who gives true rest. 27 questions (16 multiple choice, 11 open-ended) across 7 categories."""

# Questions organized by category
# NOTE: Correct answers are distributed across positions A, B, C, D
QUESTIONS_DATA = [
    # ===========================================
    # CATEGORY: Joshua's Commissioning (4 questions: 2 MC, 2 OE)
    # ===========================================
    {
        "category": "Joshua's Commissioning",
        "text": "After Moses' death, God repeatedly told Joshua to 'be strong and courageous' (Joshua 1). What was the basis for Joshua's courage?",
        "type": "multiple_choice",
        "options": [
            {"text": "His military experience from leading Israel's army against Amalek", "is_correct": False},
            {"text": "The promise that God would be with him wherever he went", "is_correct": True},  # B - CORRECT
            {"text": "The knowledge that Israel's army was larger than any Canaanite force", "is_correct": False},
            {"text": "Moses' mentorship that had fully prepared him for leadership", "is_correct": False}
        ]
    },
    {
        "category": "Joshua's Commissioning",
        "text": "God told Joshua to meditate on the Book of the Law 'day and night' (Joshua 1:8) so that he would:",
        "type": "multiple_choice",
        "options": [
            {"text": "Become the greatest scholar in Israel", "is_correct": False},
            {"text": "Be able to teach the people perfectly", "is_correct": False},
            {"text": "Be prosperous and successful by walking in God's ways", "is_correct": True},  # C - CORRECT
            {"text": "Remember Moses' legacy and honor his mentor", "is_correct": False}
        ]
    },
    {
        "category": "Joshua's Commissioning",
        "text": "God told Joshua three times to 'be strong and courageous' (Joshua 1:6, 7, 9). Each time, the reason was God's presence and promises — not Joshua's abilities. When you face intimidating situations, where do you tend to look for courage? How does Joshua 1:9 redirect your focus?",
        "type": "open_ended",
        "options": []
    },
    {
        "category": "Joshua's Commissioning",
        "text": "Joshua had been Moses' assistant for 40 years, yet God didn't say 'You're ready — you've been trained well.' Instead, God said, 'I will be with you.' How does this shift from self-confidence to God-confidence apply to your own calling or ministry?",
        "type": "open_ended",
        "options": []
    },
    # ===========================================
    # CATEGORY: Rahab & the Scarlet Cord (4 questions: 2 MC, 2 OE)
    # ===========================================
    {
        "category": "Rahab & the Scarlet Cord",
        "text": "Rahab was a Canaanite prostitute who hid Israel's spies (Joshua 2). Her confession revealed:",
        "type": "multiple_choice",
        "options": [
            {"text": "She was hoping to negotiate a business deal with Israel", "is_correct": False},
            {"text": "She had heard about Israel's God and believed He was 'God in heaven above and on earth below'", "is_correct": True},  # B - CORRECT
            {"text": "She wanted revenge against the king of Jericho who had wronged her", "is_correct": False},
            {"text": "She was secretly an Israelite who had been living undercover", "is_correct": False}
        ]
    },
    {
        "category": "Rahab & the Scarlet Cord",
        "text": "Rahab asked the spies to show 'kindness' (Hebrew: chesed — covenant loyalty) to her family. Her family would be saved by:",
        "type": "multiple_choice",
        "options": [
            {"text": "Hiding in Rahab's house with the scarlet cord in the window", "is_correct": True},  # A - CORRECT
            {"text": "Fighting alongside Israel when they attacked the city", "is_correct": False},
            {"text": "Escaping through a secret tunnel before the battle", "is_correct": False},
            {"text": "Converting to the Israelite religion before the walls fell", "is_correct": False}
        ]
    },
    {
        "category": "Rahab & the Scarlet Cord",
        "text": "Rahab — a pagan, a Canaanite, a prostitute — is listed in Jesus' genealogy (Matthew 1:5) and in the 'Hall of Faith' (Hebrews 11:31). What does her inclusion tell you about God's grace? How does her story challenge any assumptions you have about who can be saved?",
        "type": "open_ended",
        "options": []
    },
    {
        "category": "Rahab & the Scarlet Cord",
        "text": "The scarlet cord in Rahab's window saved everyone inside her house, just as the Passover blood saved those inside Israelite homes. How do you see this 'scarlet thread' of redemption pointing to Christ's blood? What does it mean to be 'inside' His covering?",
        "type": "open_ended",
        "options": []
    },
    # ===========================================
    # CATEGORY: Crossing the Jordan (4 questions: 2 MC, 2 OE)
    # ===========================================
    {
        "category": "Crossing the Jordan",
        "text": "When Israel crossed the Jordan River (Joshua 3), the waters stopped flowing when:",
        "type": "multiple_choice",
        "options": [
            {"text": "Moses' staff was held over the water by Joshua", "is_correct": False},
            {"text": "The people prayed together on the riverbank", "is_correct": False},
            {"text": "The priests carrying the ark stepped into the river", "is_correct": True},  # C - CORRECT
            {"text": "Joshua commanded the waters to part in God's name", "is_correct": False}
        ]
    },
    {
        "category": "Crossing the Jordan",
        "text": "After crossing the Jordan, Joshua commanded twelve men to:",
        "type": "multiple_choice",
        "options": [
            {"text": "Build an altar for sacrifice on the west bank", "is_correct": False},
            {"text": "Return to the east side to guard against enemies", "is_correct": False},
            {"text": "Take twelve stones from the riverbed as a memorial", "is_correct": True},  # C - CORRECT
            {"text": "Circumcise all the males born in the wilderness", "is_correct": False}
        ]
    },
    {
        "category": "Crossing the Jordan",
        "text": "The priests had to step into the flooded Jordan before the waters parted — they couldn't wait until it was safe. When has God asked you to step out in faith before you could see the outcome? What did that experience teach you about trust?",
        "type": "open_ended",
        "options": []
    },
    {
        "category": "Crossing the Jordan",
        "text": "The twelve stones were set up so children would ask, 'What do these stones mean?' (Joshua 4:6). What 'memorial stones' has God given you — moments of His faithfulness you can point to? How do you pass these stories to the next generation?",
        "type": "open_ended",
        "options": []
    },
    # ===========================================
    # CATEGORY: The Fall of Jericho (4 questions: 3 MC, 1 OE)
    # ===========================================
    {
        "category": "The Fall of Jericho",
        "text": "Before the battle of Jericho, Joshua encountered a man with a drawn sword who identified himself as (Joshua 5:13-15):",
        "type": "multiple_choice",
        "options": [
            {"text": "An angel sent to protect Joshua from assassination", "is_correct": False},
            {"text": "A Canaanite warrior offering to defect to Israel", "is_correct": False},
            {"text": "The commander of the army of the Lord", "is_correct": True},  # C - CORRECT
            {"text": "The spirit of Moses returning to encourage Joshua", "is_correct": False}
        ]
    },
    {
        "category": "The Fall of Jericho",
        "text": "God's battle plan for Jericho (Joshua 6) required Israel to:",
        "type": "multiple_choice",
        "options": [
            {"text": "Build siege ramps and battering rams over seven days", "is_correct": False},
            {"text": "March silently around the city for six days, then shout on the seventh", "is_correct": True},  # B - CORRECT
            {"text": "Send in elite troops through Rahab's window at night", "is_correct": False},
            {"text": "Starve the city into surrender through a lengthy blockade", "is_correct": False}
        ]
    },
    {
        "category": "The Fall of Jericho",
        "text": "The command to destroy everything in Jericho (the 'ban' or cherem) meant:",
        "type": "multiple_choice",
        "options": [
            {"text": "Israel could keep nothing — the city belonged entirely to God as firstfruits", "is_correct": True},  # A - CORRECT
            {"text": "Israel should burn the city but keep the gold and silver for the tabernacle", "is_correct": False},
            {"text": "Only the warriors of the city should be destroyed; civilians could be spared", "is_correct": False},
            {"text": "The destruction was optional for those with moral objections", "is_correct": False}
        ]
    },
    {
        "category": "The Fall of Jericho",
        "text": "Jericho fell not by military might but by marching, trumpets, and a shout — a plan that made no earthly sense. God often works in ways that seem foolish to the world (1 Cor 1:27). When have you seen God work through 'foolish' or counterintuitive means? How does this shape how you approach problems?",
        "type": "open_ended",
        "options": []
    },
    # ===========================================
    # CATEGORY: Sin, Failure & Restoration (4 questions: 2 MC, 2 OE)
    # ===========================================
    {
        "category": "Sin, Failure & Restoration",
        "text": "After the stunning victory at Jericho, Israel was defeated at the small town of Ai because:",
        "type": "multiple_choice",
        "options": [
            {"text": "Joshua failed to consult God before attacking", "is_correct": False},
            {"text": "Achan had secretly taken devoted items from Jericho, bringing sin into the camp", "is_correct": True},  # B - CORRECT
            {"text": "The army was overconfident and sent too few soldiers", "is_correct": False},
            {"text": "The men of Ai had superior weapons and fortifications", "is_correct": False}
        ]
    },
    {
        "category": "Sin, Failure & Restoration",
        "text": "After Achan's sin was exposed and judged, God told Joshua:",
        "type": "multiple_choice",
        "options": [
            {"text": "'Depart from this land — you have defiled it'", "is_correct": False},
            {"text": "'Send the sinful tribes back across the Jordan'", "is_correct": False},
            {"text": "'Stand up! Why are you on your face? Go and attack Ai again'", "is_correct": True},  # C - CORRECT
            {"text": "'Wait one year before attempting any further conquest'", "is_correct": False}
        ]
    },
    {
        "category": "Sin, Failure & Restoration",
        "text": "Achan's 'private' sin brought defeat on the whole community — 36 men died at Ai (Joshua 7:5). How does this challenge the modern idea that 'my sin is my own business'? In what ways does hidden sin affect your community, family, or church?",
        "type": "open_ended",
        "options": []
    },
    {
        "category": "Sin, Failure & Restoration",
        "text": "After the disaster at Ai, Joshua fell facedown in despair (Joshua 7:6-9). But once sin was dealt with, God immediately said 'Do not be afraid' and gave victory. How does this pattern — confession, cleansing, restoration — encourage you when you've failed? How does it point to the gospel?",
        "type": "open_ended",
        "options": []
    },
    # ===========================================
    # CATEGORY: Conquest & Inheritance (4 questions: 3 MC, 1 OE)
    # ===========================================
    {
        "category": "Conquest & Inheritance",
        "text": "During the battle at Gibeon, Joshua prayed and God caused:",
        "type": "multiple_choice",
        "options": [
            {"text": "A plague to strike the enemy army", "is_correct": False},
            {"text": "An earthquake to swallow the Amorite kings", "is_correct": False},
            {"text": "The sun and moon to stand still, extending the day for Israel's victory", "is_correct": True},  # C - CORRECT
            {"text": "A flood to sweep away the enemy chariots", "is_correct": False}
        ]
    },
    {
        "category": "Conquest & Inheritance",
        "text": "When dividing the Promised Land among the tribes, 85-year-old Caleb asked Joshua for:",
        "type": "multiple_choice",
        "options": [
            {"text": "A peaceful valley suitable for his old age", "is_correct": False},
            {"text": "The hill country where the giants (Anakim) still lived — the very land that had terrified Israel 45 years earlier", "is_correct": True},  # B - CORRECT
            {"text": "A coastal region with fertile farmland", "is_correct": False},
            {"text": "A position of honor in Joshua's administration", "is_correct": False}
        ]
    },
    {
        "category": "Conquest & Inheritance",
        "text": "The Levites received no land inheritance because:",
        "type": "multiple_choice",
        "options": [
            {"text": "They had sinned during the golden calf incident", "is_correct": False},
            {"text": "God Himself was their inheritance — they would live among all the tribes and serve at the tabernacle", "is_correct": True},  # B - CORRECT
            {"text": "There wasn't enough land for all thirteen tribes", "is_correct": False},
            {"text": "They were meant to return to Egypt as missionaries", "is_correct": False}
        ]
    },
    {
        "category": "Conquest & Inheritance",
        "text": "Caleb at 85 said, 'I am still as strong today as I was when Moses sent me... Now give me this hill country' (Joshua 14:11-12). He wanted the hard assignment, not easy retirement. What does Caleb's faith-filled boldness in old age teach you about finishing well? What 'hill country' might God be calling you to take?",
        "type": "open_ended",
        "options": []
    },
    # ===========================================
    # CATEGORY: Joshua's Legacy & Choosing to Serve (3 questions: 2 MC, 1 OE)
    # ===========================================
    {
        "category": "Joshua's Legacy & Choosing to Serve",
        "text": "In his farewell address, Joshua reminded Israel that their victories came because (Joshua 23:3):",
        "type": "multiple_choice",
        "options": [
            {"text": "They were more numerous than the Canaanites", "is_correct": False},
            {"text": "Their military strategy was superior", "is_correct": False},
            {"text": "The Lord their God fought for them", "is_correct": True},  # C - CORRECT
            {"text": "They had trained harder than their enemies", "is_correct": False}
        ]
    },
    {
        "category": "Joshua's Legacy & Choosing to Serve",
        "text": "Joshua's famous declaration 'Choose this day whom you will serve... but as for me and my house, we will serve the Lord' (Joshua 24:15) came in the context of:",
        "type": "multiple_choice",
        "options": [
            {"text": "A warning that Israel's heart was prone to wander back to idols", "is_correct": True},  # A - CORRECT
            {"text": "A celebration of Israel's perfect faithfulness", "is_correct": False},
            {"text": "A prophecy that Israel would soon be exiled", "is_correct": False},
            {"text": "An announcement of Joshua's successor", "is_correct": False}
        ]
    },
    {
        "category": "Joshua's Legacy & Choosing to Serve",
        "text": "Joshua led Israel into the Promised Land and gave them rest from their enemies — yet Hebrews 4:8-9 says 'If Joshua had given them rest, God would not have spoken later about another day. There remains, then, a Sabbath-rest for the people of God.' How does Joshua point forward to Jesus as the one who gives true and eternal rest? What does it mean to you that Christ offers rest Joshua couldn't fully provide?",
        "type": "open_ended",
        "options": []
    },
]

def main():
    print("=" * 60)
    print("Israel Under Joshua Assessment Setup")
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
                print(f"✅ Created Israel Under Joshua Assessment template: {template_id}")
            
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
                question_code = f"JOSH_{question_order:03d}"
                
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
            print(f"✅ SUCCESS! Created Israel Under Joshua Assessment")
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
