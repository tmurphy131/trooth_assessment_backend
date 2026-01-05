"""
Script to create the Exodus & Wilderness Assessment
Run as: python setup_exodus_wilderness_assessment.py
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
ASSESSMENT_KEY = "exodus_wilderness_v1"
ASSESSMENT_NAME = "Exodus & Wilderness Assessment"
ASSESSMENT_DESCRIPTION = """Explore the narrative of Moses leading Israel from bondage in Egypt through the wilderness toward the Promised Land. This assessment draws gospel truths from the story of redemption, covering Moses' calling, the Passover, deliverance at the Red Sea, wilderness provision, meeting God at Sinai, Israel's failures, and Moses' legacy pointing to Christ. 27 questions (16 multiple choice, 11 open-ended) across 7 categories."""

# Questions organized by category
# NOTE: Correct answers are distributed across positions A, B, C, D
QUESTIONS_DATA = [
    # ===========================================
    # CATEGORY: The Reluctant Deliverer (4 questions: 2 MC, 2 OE)
    # ===========================================
    {
        "category": "The Reluctant Deliverer",
        "text": "When God called Moses at the burning bush (Exodus 3), what was Moses' first response?",
        "type": "multiple_choice",
        "options": [
            {"text": "Immediate obedience and eagerness to deliver Israel", "is_correct": False},
            {"text": "A request for more time to prepare for the mission", "is_correct": False},
            {"text": "'Who am I that I should go to Pharaoh?' — doubt about his own adequacy", "is_correct": True},  # C - CORRECT
            {"text": "Fear of returning to Egypt where he was wanted for murder", "is_correct": False}
        ]
    },
    {
        "category": "The Reluctant Deliverer",
        "text": "God revealed His name to Moses as 'I AM WHO I AM' (Exodus 3:14). This name signifies:",
        "type": "multiple_choice",
        "options": [
            {"text": "God's mystery and unknowable nature", "is_correct": False},
            {"text": "God's eternal, self-existent nature — He is the source of all being", "is_correct": True},  # B - CORRECT
            {"text": "God's refusal to be defined by human categories", "is_correct": False},
            {"text": "God's anger at Moses' questioning", "is_correct": False}
        ]
    },
    {
        "category": "The Reluctant Deliverer",
        "text": "Moses made excuse after excuse for why he couldn't lead Israel (Exodus 3-4). God patiently answered each one. When you sense God calling you to something difficult, what excuses do you make? How does God's response to Moses encourage you?",
        "type": "open_ended",
        "options": []
    },
    {
        "category": "The Reluctant Deliverer",
        "text": "God chose a murderer and fugitive (Moses) to deliver His people. How does this foreshadow the gospel truth that God uses broken people and that our past doesn't disqualify us from His purposes?",
        "type": "open_ended",
        "options": []
    },
    # ===========================================
    # CATEGORY: Plagues, Passover & the Lamb (4 questions: 3 MC, 1 OE)
    # ===========================================
    {
        "category": "Plagues, Passover & the Lamb",
        "text": "The ten plagues demonstrated God's power over:",
        "type": "multiple_choice",
        "options": [
            {"text": "Pharaoh's army and military strength", "is_correct": False},
            {"text": "The Hebrew slaves who had lost faith", "is_correct": False},
            {"text": "The gods of Egypt — each plague targeted a specific Egyptian deity", "is_correct": True},  # C - CORRECT
            {"text": "Nature itself, showing He could destroy creation", "is_correct": False}
        ]
    },
    {
        "category": "Plagues, Passover & the Lamb",
        "text": "On the night of the Passover (Exodus 12), what protected the Israelite firstborn from death?",
        "type": "multiple_choice",
        "options": [
            {"text": "Their ethnic identity as children of Abraham", "is_correct": False},
            {"text": "Their obedience to Moses' leadership", "is_correct": False},
            {"text": "Their faith in God's promises", "is_correct": False},
            {"text": "The blood of the lamb applied to their doorposts", "is_correct": True}  # D - CORRECT
        ]
    },
    {
        "category": "Plagues, Passover & the Lamb",
        "text": "The Passover lamb had to be 'without defect' (Exodus 12:5) because:",
        "type": "multiple_choice",
        "options": [
            {"text": "It represented the costly, perfect sacrifice required for redemption", "is_correct": True},  # A - CORRECT
            {"text": "Blemished animals were considered unclean and worthless", "is_correct": False},
            {"text": "It demonstrated Israel's wealth and devotion to God", "is_correct": False},
            {"text": "Egyptian custom required perfect animals for sacrifice", "is_correct": False}
        ]
    },
    {
        "category": "Plagues, Passover & the Lamb",
        "text": "John the Baptist called Jesus 'the Lamb of God who takes away the sin of the world' (John 1:29), and Paul says 'Christ, our Passover lamb, has been sacrificed' (1 Cor 5:7). How does the Passover story deepen your understanding of what Jesus accomplished on the cross?",
        "type": "open_ended",
        "options": []
    },
    # ===========================================
    # CATEGORY: Deliverance at the Sea (4 questions: 2 MC, 2 OE)
    # ===========================================
    {
        "category": "Deliverance at the Sea",
        "text": "When the Israelites were trapped between the Red Sea and Pharaoh's army (Exodus 14), Moses told them:",
        "type": "multiple_choice",
        "options": [
            {"text": "'Prepare to fight — the Lord will give us victory'", "is_correct": False},
            {"text": "'Stand firm and you will see the deliverance the Lord will bring... The Lord will fight for you; you need only to be still'", "is_correct": True},  # B - CORRECT
            {"text": "'Cry out to the Lord and perhaps He will have mercy'", "is_correct": False},
            {"text": "'This is a test of faith — walk into the sea and trust God'", "is_correct": False}
        ]
    },
    {
        "category": "Deliverance at the Sea",
        "text": "After crossing the Red Sea, Moses and Miriam led the people in:",
        "type": "multiple_choice",
        "options": [
            {"text": "A solemn ceremony of covenant renewal", "is_correct": False},
            {"text": "Prayers of confession for their earlier doubt", "is_correct": False},
            {"text": "Songs of praise celebrating God's victory and deliverance", "is_correct": True},  # C - CORRECT
            {"text": "Planning for the journey ahead to Mount Sinai", "is_correct": False}
        ]
    },
    {
        "category": "Deliverance at the Sea",
        "text": "The Red Sea crossing is the defining salvation event of the Old Testament — Israel was helpless, trapped, and God alone delivered them. How does this parallel the gospel? In what ways were you 'trapped' before Christ rescued you?",
        "type": "open_ended",
        "options": []
    },
    {
        "category": "Deliverance at the Sea",
        "text": "Exodus 14:13 says 'Stand firm... you need only to be still.' When have you experienced a 'Red Sea moment' where you had to stop striving and trust God to fight for you? What happened?",
        "type": "open_ended",
        "options": []
    },
    # ===========================================
    # CATEGORY: Wilderness Provision (4 questions: 2 MC, 2 OE)
    # ===========================================
    {
        "category": "Wilderness Provision",
        "text": "When Israel complained about hunger in the wilderness, God provided manna with specific instructions (Exodus 16). What happened when people tried to hoard extra manna overnight?",
        "type": "multiple_choice",
        "options": [
            {"text": "It multiplied as a reward for their planning", "is_correct": False},
            {"text": "It remained fresh as long as they had faith", "is_correct": False},
            {"text": "It bred worms and became foul — they had to depend on God daily", "is_correct": True},  # C - CORRECT
            {"text": "Nothing happened; God understood their fear", "is_correct": False}
        ]
    },
    {
        "category": "Wilderness Provision",
        "text": "When the people had no water at Rephidim (Exodus 17), God told Moses to:",
        "type": "multiple_choice",
        "options": [
            {"text": "Pray and wait for rain from heaven", "is_correct": False},
            {"text": "Dig wells in the rock", "is_correct": False},
            {"text": "Lead the people to a nearby oasis", "is_correct": False},
            {"text": "Strike the rock, and water would flow from it", "is_correct": True}  # D - CORRECT
        ]
    },
    {
        "category": "Wilderness Provision",
        "text": "Jesus said, 'I am the bread of life' (John 6:35) and Paul wrote that the Israelites 'drank from the spiritual rock... and that rock was Christ' (1 Cor 10:4). How do manna and water from the rock point to Jesus as our daily sustenance?",
        "type": "open_ended",
        "options": []
    },
    {
        "category": "Wilderness Provision",
        "text": "The Israelites had to gather manna fresh each day — they couldn't stockpile it. What does this teach you about daily dependence on God? How does this connect to Jesus' prayer, 'Give us this day our daily bread'?",
        "type": "open_ended",
        "options": []
    },
    # ===========================================
    # CATEGORY: Meeting God at Sinai (4 questions: 2 MC, 2 OE)
    # ===========================================
    {
        "category": "Meeting God at Sinai",
        "text": "When God descended on Mount Sinai (Exodus 19), the people experienced:",
        "type": "multiple_choice",
        "options": [
            {"text": "Peaceful calm and a sense of God's gentle presence", "is_correct": False},
            {"text": "Thunder, lightning, thick cloud, trumpet blast, and trembling — overwhelming holiness", "is_correct": True},  # B - CORRECT
            {"text": "Visions and dreams revealing God's plan for Israel", "is_correct": False},
            {"text": "The ability to approach God freely on the mountain", "is_correct": False}
        ]
    },
    {
        "category": "Meeting God at Sinai",
        "text": "After the golden calf incident, Moses asked to see God's glory (Exodus 33:18). God responded by:",
        "type": "multiple_choice",
        "options": [
            {"text": "Showing Moses His face directly as a reward for faithfulness", "is_correct": False},
            {"text": "Refusing because no human could ever see God", "is_correct": False},
            {"text": "Hiding Moses in a rock and passing by, proclaiming His character: 'compassionate, gracious, slow to anger'", "is_correct": True},  # C - CORRECT
            {"text": "Sending an angel to represent His presence to Moses", "is_correct": False}
        ]
    },
    {
        "category": "Meeting God at Sinai",
        "text": "God's self-revelation in Exodus 34:6-7 — 'compassionate, gracious, slow to anger, abounding in love' — is quoted throughout Scripture. How does this description of God's character give you confidence to approach Him despite your failures?",
        "type": "open_ended",
        "options": []
    },
    {
        "category": "Meeting God at Sinai",
        "text": "The people were terrified at Sinai and begged Moses to speak to God for them (Exodus 20:19). Hebrews 12:18-24 contrasts Sinai with 'Mount Zion' — our access to God through Jesus. How has Christ changed your ability to approach God?",
        "type": "open_ended",
        "options": []
    },
    # ===========================================
    # CATEGORY: Grumbling, Failure & Grace (4 questions: 3 MC, 1 OE)
    # ===========================================
    {
        "category": "Grumbling, Failure & Grace",
        "text": "When the twelve spies returned from Canaan (Numbers 13-14), ten gave a fearful report. What was the key difference in Caleb and Joshua's perspective?",
        "type": "multiple_choice",
        "options": [
            {"text": "They had better military strategy for conquering the land", "is_correct": False},
            {"text": "They saw smaller enemies than the other spies saw", "is_correct": False},
            {"text": "They trusted God's promise and power despite the obstacles", "is_correct": True},  # C - CORRECT
            {"text": "They were younger and more courageous than the others", "is_correct": False}
        ]
    },
    {
        "category": "Grumbling, Failure & Grace",
        "text": "After years of grumbling, God sent venomous snakes among the Israelites (Numbers 21). What was God's remedy?",
        "type": "multiple_choice",
        "options": [
            {"text": "Moses prayed and the snakes immediately disappeared", "is_correct": False},
            {"text": "The people had to kill all the snakes to prove their repentance", "is_correct": False},
            {"text": "Anyone who confessed their sin was healed automatically", "is_correct": False},
            {"text": "Moses made a bronze snake on a pole; anyone who looked at it lived", "is_correct": True}  # D - CORRECT
        ]
    },
    {
        "category": "Grumbling, Failure & Grace",
        "text": "Despite Israel's constant rebellion in the wilderness, God:",
        "type": "multiple_choice",
        "options": [
            {"text": "Continued to provide food, water, and guidance — their clothes didn't even wear out", "is_correct": True},  # A - CORRECT
            {"text": "Eventually abandoned that generation and started over with their children", "is_correct": False},
            {"text": "Punished them harshly but provided no ongoing care", "is_correct": False},
            {"text": "Reduced His presence among them until they proved faithful", "is_correct": False}
        ]
    },
    {
        "category": "Grumbling, Failure & Grace",
        "text": "Jesus directly connected Himself to the bronze serpent: 'Just as Moses lifted up the snake in the wilderness, so the Son of Man must be lifted up' (John 3:14). What parallels do you see between looking at the bronze serpent for healing and looking to Christ on the cross?",
        "type": "open_ended",
        "options": []
    },
    # ===========================================
    # CATEGORY: Moses' Legacy & the Greater Prophet (3 questions: 2 MC, 1 OE)
    # ===========================================
    {
        "category": "Moses' Legacy & the Greater Prophet",
        "text": "Moses was not allowed to enter the Promised Land because:",
        "type": "multiple_choice",
        "options": [
            {"text": "He was too old and weak to lead the conquest", "is_correct": False},
            {"text": "He struck the rock in anger instead of speaking to it, failing to honor God as holy", "is_correct": True},  # B - CORRECT
            {"text": "He had committed murder in Egypt years earlier", "is_correct": False},
            {"text": "God needed Joshua's military leadership for the battles ahead", "is_correct": False}
        ]
    },
    {
        "category": "Moses' Legacy & the Greater Prophet",
        "text": "In Deuteronomy 18:15, Moses prophesied that God would raise up:",
        "type": "multiple_choice",
        "options": [
            {"text": "A king like David who would establish an eternal throne", "is_correct": False},
            {"text": "A prophet like Moses from among their own people, whom they must obey", "is_correct": True},  # B - CORRECT
            {"text": "A priest like Aaron who would make perfect atonement", "is_correct": False},
            {"text": "An angel who would lead them in Moses' place", "is_correct": False}
        ]
    },
    {
        "category": "Moses' Legacy & the Greater Prophet",
        "text": "Moses was a great deliverer, but he was flawed and couldn't bring the people into rest. How does Moses' story point you to Jesus as the greater Deliverer — the one who succeeds where Moses fell short and leads His people into true rest?",
        "type": "open_ended",
        "options": []
    },
]

def main():
    print("=" * 60)
    print("Exodus & Wilderness Assessment Setup")
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
                print(f"✅ Created Exodus & Wilderness Assessment template: {template_id}")
            
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
                question_code = f"EXOD_{question_order:03d}"
                
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
            print(f"✅ SUCCESS! Created Exodus & Wilderness Assessment")
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
