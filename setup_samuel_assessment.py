"""
Script to create the 1st & 2nd Samuel Assessment
Run as: python setup_samuel_assessment.py
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
ASSESSMENT_KEY = "samuel_v1"
ASSESSMENT_NAME = "1st & 2nd Samuel"
ASSESSMENT_DESCRIPTION = """Explore the Books of 1st and 2nd Samuel — from the last judge to Israel's first kings, culminating in David and the covenant that points directly to Jesus. This assessment draws gospel truths from Samuel's calling, Saul's failure, David's rise and reign, the Davidic covenant, David's sin and repentance, and the promise of an eternal King. 27 questions (16 multiple choice, 11 open-ended) across 7 categories."""

# Questions organized by category
# NOTE: Correct answers are distributed across positions A, B, C, D
QUESTIONS_DATA = [
    # ===========================================
    # CATEGORY: Samuel's Calling & Israel's Demand (4 questions: 2 MC, 2 OE)
    # ===========================================
    {
        "category": "Samuel's Calling & Israel's Demand",
        "text": "When the boy Samuel heard God calling him in the night (1 Samuel 3), he initially thought:",
        "type": "multiple_choice",
        "options": [
            {"text": "It was a dream and went back to sleep", "is_correct": False},
            {"text": "It was the priest Eli calling him", "is_correct": True},  # B - CORRECT
            {"text": "It was an angel appearing to him", "is_correct": False},
            {"text": "It was his own imagination", "is_correct": False}
        ]
    },
    {
        "category": "Samuel's Calling & Israel's Demand",
        "text": "When the elders of Israel demanded a king 'like all the other nations' (1 Samuel 8), God told Samuel:",
        "type": "multiple_choice",
        "options": [
            {"text": "To refuse their request because Israel must remain different", "is_correct": False},
            {"text": "That they had rejected God Himself as their king, not just Samuel", "is_correct": True},  # B - CORRECT
            {"text": "To appoint the strongest warrior as king", "is_correct": False},
            {"text": "That Israel was not yet ready for a monarchy", "is_correct": False}
        ]
    },
    {
        "category": "Samuel's Calling & Israel's Demand",
        "text": "God called Samuel as a young boy, speaking to him personally before Samuel even knew how to recognize His voice. How did you first begin to recognize God speaking to you? What helps you discern His voice today?",
        "type": "open_ended",
        "options": []
    },
    {
        "category": "Samuel's Calling & Israel's Demand",
        "text": "Israel wanted a king 'like all the other nations' — they wanted to fit in rather than be set apart. In what ways are you tempted to look like the world rather than trusting God's unique plan for your life? How does the gospel free you from that pressure?",
        "type": "open_ended",
        "options": []
    },
    # ===========================================
    # CATEGORY: Saul — The People's Choice (4 questions: 2 MC, 2 OE)
    # ===========================================
    {
        "category": "Saul — The People's Choice",
        "text": "Saul was initially chosen as king partly because he:",
        "type": "multiple_choice",
        "options": [
            {"text": "Was from the most prominent tribe and had proven military leadership", "is_correct": False},
            {"text": "Was head and shoulders taller than anyone else — impressive in appearance", "is_correct": True},  # B - CORRECT
            {"text": "Had demonstrated exceptional wisdom and godliness", "is_correct": False},
            {"text": "Was a direct descendant of the judges", "is_correct": False}
        ]
    },
    {
        "category": "Saul — The People's Choice",
        "text": "Saul's disobedience in sparing King Agag and the best livestock (1 Samuel 15) led Samuel to declare:",
        "type": "multiple_choice",
        "options": [
            {"text": "'The Lord has rejected you as king over Israel'", "is_correct": True},  # A - CORRECT
            {"text": "'You will be forgiven if you sacrifice the animals now'", "is_correct": False},
            {"text": "'Your son will inherit your sin but also your throne'", "is_correct": False},
            {"text": "'God will give you another chance to obey'", "is_correct": False}
        ]
    },
    {
        "category": "Saul — The People's Choice",
        "text": "Samuel told Saul, 'To obey is better than sacrifice' (1 Samuel 15:22). Saul tried to cover disobedience with religious activity. In what ways might you be tempted to substitute religious actions for actual obedience? What areas of obedience is God highlighting in your life right now?",
        "type": "open_ended",
        "options": []
    },
    {
        "category": "Saul — The People's Choice",
        "text": "Saul started humble ('Am I not a Benjaminite, from the smallest tribe?' — 1 Samuel 9:21) but ended consumed by pride and jealousy. What warning does Saul's trajectory give you about guarding your heart over time? How can you stay humble as God gives you influence or success?",
        "type": "open_ended",
        "options": []
    },
    # ===========================================
    # CATEGORY: David's Anointing & Rise (4 questions: 3 MC, 1 OE)
    # ===========================================
    {
        "category": "David's Anointing & Rise",
        "text": "When Samuel came to Jesse's house to anoint a new king, God rejected David's older brothers because:",
        "type": "multiple_choice",
        "options": [
            {"text": "They had disqualified themselves through sin", "is_correct": False},
            {"text": "They were not interested in being king", "is_correct": False},
            {"text": "'The Lord looks at the heart,' not outward appearance", "is_correct": True},  # C - CORRECT
            {"text": "They were too old to begin a new dynasty", "is_correct": False}
        ]
    },
    {
        "category": "David's Anointing & Rise",
        "text": "When David was anointed by Samuel, what happened to him?",
        "type": "multiple_choice",
        "options": [
            {"text": "He immediately became king and moved to the palace", "is_correct": False},
            {"text": "The Spirit of the Lord came powerfully upon him from that day forward", "is_correct": True},  # B - CORRECT
            {"text": "He received a vision of his future reign", "is_correct": False},
            {"text": "Nothing visible changed; he returned to his sheep", "is_correct": False}
        ]
    },
    {
        "category": "David's Anointing & Rise",
        "text": "David first entered Saul's service as:",
        "type": "multiple_choice",
        "options": [
            {"text": "A military commander leading troops against the Philistines", "is_correct": False},
            {"text": "A musician who played the harp to soothe Saul's troubled spirit", "is_correct": True},  # B - CORRECT
            {"text": "A personal attendant to the royal family", "is_correct": False},
            {"text": "A prophet delivering messages from God to the king", "is_correct": False}
        ]
    },
    {
        "category": "David's Anointing & Rise",
        "text": "David was anointed king as a teenager but didn't take the throne until his thirties — years of waiting, running, and hiding. How do you handle the gap between God's promises and their fulfillment? What is God teaching you in your own 'waiting seasons'?",
        "type": "open_ended",
        "options": []
    },
    # ===========================================
    # CATEGORY: David & Goliath — Faith Over Fear (4 questions: 2 MC, 2 OE)
    # ===========================================
    {
        "category": "David & Goliath — Faith Over Fear",
        "text": "When David volunteered to fight Goliath, he refused Saul's armor because:",
        "type": "multiple_choice",
        "options": [
            {"text": "It was too heavy and he wasn't trained to use it", "is_correct": True},  # A - CORRECT
            {"text": "He wanted to demonstrate that God alone would give victory", "is_correct": False},
            {"text": "Saul's armor was cursed due to his disobedience", "is_correct": False},
            {"text": "He preferred to fight with speed and agility", "is_correct": False}
        ]
    },
    {
        "category": "David & Goliath — Faith Over Fear",
        "text": "David declared to Goliath, 'You come against me with sword and spear, but I come against you in the name of the Lord Almighty... and the whole world will know that there is a God in Israel' (1 Samuel 17:45-46). David's primary concern was:",
        "type": "multiple_choice",
        "options": [
            {"text": "Protecting Israel's army from defeat", "is_correct": False},
            {"text": "Proving his own courage and skill", "is_correct": False},
            {"text": "God's glory and reputation among the nations", "is_correct": True},  # C - CORRECT
            {"text": "Earning the reward Saul had promised", "is_correct": False}
        ]
    },
    {
        "category": "David & Goliath — Faith Over Fear",
        "text": "David said, 'The Lord who rescued me from the paw of the lion and the paw of the bear will rescue me from this Philistine' (1 Samuel 17:37). He built confidence from past faithfulness. What 'lions and bears' has God already delivered you from? How do those memories equip you for current giants?",
        "type": "open_ended",
        "options": []
    },
    {
        "category": "David & Goliath — Faith Over Fear",
        "text": "Israel's army saw Goliath and thought, 'He's too big to fight.' David saw Goliath and thought, 'He's too big to miss — God will defeat him.' How does faith change the way you see your obstacles? What 'giant' are you facing that you need to see through eyes of faith?",
        "type": "open_ended",
        "options": []
    },
    # ===========================================
    # CATEGORY: David's Reign & the Covenant (4 questions: 3 MC, 1 OE)
    # ===========================================
    {
        "category": "David's Reign & the Covenant",
        "text": "After David became king and wanted to build a temple for God, the Lord responded through Nathan by:",
        "type": "multiple_choice",
        "options": [
            {"text": "Giving David detailed plans for construction", "is_correct": False},
            {"text": "Promising instead that God would build David a 'house' — an eternal dynasty", "is_correct": True},  # B - CORRECT
            {"text": "Telling David to wait until he had conquered all enemies", "is_correct": False},
            {"text": "Rejecting the idea because the tabernacle was sufficient", "is_correct": False}
        ]
    },
    {
        "category": "David's Reign & the Covenant",
        "text": "In the Davidic covenant (2 Samuel 7), God promised David that:",
        "type": "multiple_choice",
        "options": [
            {"text": "His kingdom would last as long as his descendants obeyed", "is_correct": False},
            {"text": "His throne would be established forever — an eternal kingdom", "is_correct": True},  # B - CORRECT
            {"text": "One of his sons would become high priest as well as king", "is_correct": False},
            {"text": "Israel would never again face military defeat", "is_correct": False}
        ]
    },
    {
        "category": "David's Reign & the Covenant",
        "text": "David's response to God's covenant promise was:",
        "type": "multiple_choice",
        "options": [
            {"text": "Confident pride that he deserved such honor", "is_correct": False},
            {"text": "Humble amazement: 'Who am I, Sovereign Lord... that you have brought me this far?'", "is_correct": True},  # B - CORRECT
            {"text": "Immediate plans to expand his kingdom", "is_correct": False},
            {"text": "A request for even greater blessings", "is_correct": False}
        ]
    },
    {
        "category": "David's Reign & the Covenant",
        "text": "God promised David an eternal throne (2 Samuel 7:16), fulfilled ultimately in Jesus — 'son of David' who reigns forever. How does knowing that Jesus fulfills the Davidic covenant deepen your trust in God's faithfulness to His promises? What promises are you holding onto today?",
        "type": "open_ended",
        "options": []
    },
    # ===========================================
    # CATEGORY: Sin, Consequences & Repentance (4 questions: 2 MC, 2 OE)
    # ===========================================
    {
        "category": "Sin, Consequences & Repentance",
        "text": "David's sin with Bathsheba began when:",
        "type": "multiple_choice",
        "options": [
            {"text": "Bathsheba seduced him at the palace", "is_correct": False},
            {"text": "He stayed home from war 'at the time when kings go out to battle' and saw her bathing", "is_correct": True},  # B - CORRECT
            {"text": "His advisors suggested he take another wife", "is_correct": False},
            {"text": "He was depressed and seeking comfort after military losses", "is_correct": False}
        ]
    },
    {
        "category": "Sin, Consequences & Repentance",
        "text": "When the prophet Nathan confronted David about his sin, David's response was:",
        "type": "multiple_choice",
        "options": [
            {"text": "Denial and anger toward Nathan", "is_correct": False},
            {"text": "Excuses blaming Bathsheba and circumstances", "is_correct": False},
            {"text": "'I have sinned against the Lord' — immediate confession", "is_correct": True},  # C - CORRECT
            {"text": "A promise to make restitution through sacrifice", "is_correct": False}
        ]
    },
    {
        "category": "Sin, Consequences & Repentance",
        "text": "Psalm 51, David's prayer after his sin was exposed, says 'Against you, you only, have I sinned' (Psalm 51:4). David had sinned against Bathsheba, Uriah, and Israel — yet he saw his sin primarily as against God. How does understanding sin as an offense against God change how you approach confession and repentance?",
        "type": "open_ended",
        "options": []
    },
    {
        "category": "Sin, Consequences & Repentance",
        "text": "David was forgiven, but he still faced consequences — the child died, and his family was torn apart by violence and rebellion. Grace doesn't always remove consequences. How do you reconcile God's forgiveness with the ongoing effects of sin? How does this reality motivate you toward obedience?",
        "type": "open_ended",
        "options": []
    },
    # ===========================================
    # CATEGORY: The Promised King to Come (3 questions: 2 MC, 1 OE)
    # ===========================================
    {
        "category": "The Promised King to Come",
        "text": "David, despite being called 'a man after God's own heart' (1 Samuel 13:14), was still:",
        "type": "multiple_choice",
        "options": [
            {"text": "Perfect in his obedience after becoming king", "is_correct": False},
            {"text": "A flawed sinner who failed morally and as a father", "is_correct": True},  # B - CORRECT
            {"text": "Unable to receive forgiveness for his sins", "is_correct": False},
            {"text": "Rejected by God after his sin with Bathsheba", "is_correct": False}
        ]
    },
    {
        "category": "The Promised King to Come",
        "text": "The Books of Samuel point forward to Jesus as the ultimate King because Jesus:",
        "type": "multiple_choice",
        "options": [
            {"text": "Was a literal descendant of David who fulfills the eternal throne promise", "is_correct": True},  # A - CORRECT
            {"text": "Rejected the idea of kingship in favor of being a servant only", "is_correct": False},
            {"text": "Established His kingdom through military conquest like David", "is_correct": False},
            {"text": "Replaced the Davidic covenant with a new promise", "is_correct": False}
        ]
    },
    {
        "category": "The Promised King to Come",
        "text": "David was a shepherd who became king, a man after God's heart who still failed terribly, and a recipient of an eternal promise he never saw fulfilled. How does David's story — his faith, failures, and the covenant — prepare you to understand and appreciate who Jesus is as the true and better King? What does it mean to you that Jesus succeeds where David fell short?",
        "type": "open_ended",
        "options": []
    },
]

def main():
    print("=" * 60)
    print("1st & 2nd Samuel Assessment Setup")
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
                print(f"✅ Created 1st & 2nd Samuel Assessment template: {template_id}")
            
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
                question_code = f"SAM_{question_order:03d}"
                
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
            print(f"✅ SUCCESS! Created 1st & 2nd Samuel Assessment")
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
