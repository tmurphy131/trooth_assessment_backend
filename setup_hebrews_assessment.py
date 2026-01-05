"""
Script to create the Hebrews Assessment
Run as: python setup_hebrews_assessment.py
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
ASSESSMENT_KEY = "hebrews_v1"
ASSESSMENT_NAME = "Hebrews Assessment"
ASSESSMENT_DESCRIPTION = """Explore the book of Hebrews - the supremacy of Christ over all things, His perfect high priesthood, the new covenant, and the call to persevere in faith. This assessment covers Christ's supremacy, His role as high priest, the new covenant, heroes of faith, perseverance, warnings against falling away, and living by faith. 27 questions (16 multiple choice, 11 open-ended) across 7 categories."""

# Questions organized by category
# NOTE: Correct answers are distributed across positions A, B, C, D
QUESTIONS_DATA = [
    # ===========================================
    # CATEGORY: The Supremacy of Christ (4 questions: 2 MC, 2 OE)
    # ===========================================
    {
        "category": "The Supremacy of Christ",
        "text": "According to Hebrews 1:1-3, how has God spoken to us in these last days?",
        "type": "multiple_choice",
        "options": [
            {"text": "Through His Son, who is the radiance of God's glory and exact representation of His being", "is_correct": True},  # A - CORRECT
            {"text": "Through prophets who received special visions and dreams", "is_correct": False},
            {"text": "Through the Holy Spirit who guides believers into all truth", "is_correct": False},
            {"text": "Through Scripture which is inspired and profitable for teaching", "is_correct": False}
        ]
    },
    {
        "category": "The Supremacy of Christ",
        "text": "Hebrews 1:4-14 argues that Jesus is superior to the angels because:",
        "type": "multiple_choice",
        "options": [
            {"text": "Angels are created beings while Jesus existed before all creation", "is_correct": False},
            {"text": "Angels serve God in heaven while Jesus serves God on earth", "is_correct": False},
            {"text": "Angels are spiritual beings while Jesus took on human flesh", "is_correct": False},
            {"text": "The Son is given the name, throne, and eternal kingdom that angels never receive", "is_correct": True}  # D - CORRECT
        ]
    },
    {
        "category": "The Supremacy of Christ",
        "text": "Hebrews 1:3 says Jesus 'sustains all things by his powerful word.' How does this truth about Christ's ongoing sovereignty affect how you view the circumstances of your life?",
        "type": "open_ended",
        "options": []
    },
    {
        "category": "The Supremacy of Christ",
        "text": "The author of Hebrews goes to great lengths to show Jesus is superior to angels, Moses, and the Levitical priests. Why do you think establishing Christ's supremacy matters for the Christian life?",
        "type": "open_ended",
        "options": []
    },
    # ===========================================
    # CATEGORY: Jesus Our High Priest (4 questions: 3 MC, 1 OE)
    # ===========================================
    {
        "category": "Jesus Our High Priest",
        "text": "According to Hebrews 4:15, what makes Jesus a sympathetic high priest?",
        "type": "multiple_choice",
        "options": [
            {"text": "He observed human suffering from heaven before coming to earth", "is_correct": False},
            {"text": "He was tempted in every way as we are, yet was without sin", "is_correct": True},  # B - CORRECT
            {"text": "He spent time with sinners and outcasts during His ministry", "is_correct": False},
            {"text": "He experienced God's wrath on the cross in our place", "is_correct": False}
        ]
    },
    {
        "category": "Jesus Our High Priest",
        "text": "Hebrews 7 explains that Jesus' priesthood is superior because it is in the order of:",
        "type": "multiple_choice",
        "options": [
            {"text": "Aaron, the first high priest appointed by God", "is_correct": False},
            {"text": "Moses, the mediator of the old covenant", "is_correct": False},
            {"text": "Melchizedek, a priest forever without beginning or end", "is_correct": True},  # C - CORRECT
            {"text": "David, the king who was also a prophet", "is_correct": False}
        ]
    },
    {
        "category": "Jesus Our High Priest",
        "text": "Unlike the Levitical priests who offered sacrifices repeatedly, Jesus:",
        "type": "multiple_choice",
        "options": [
            {"text": "Offered Himself once for all, accomplishing eternal redemption", "is_correct": True},  # A - CORRECT
            {"text": "Offered a more valuable sacrifice of gold and silver", "is_correct": False},
            {"text": "Offered sacrifices in a heavenly temple rather than an earthly one", "is_correct": False},
            {"text": "Offered prayers and intercession instead of animal sacrifices", "is_correct": False}
        ]
    },
    {
        "category": "Jesus Our High Priest",
        "text": "Hebrews 4:16 invites us to 'approach the throne of grace with confidence.' How does understanding Jesus as your high priest change the way you pray and come to God?",
        "type": "open_ended",
        "options": []
    },
    # ===========================================
    # CATEGORY: The New Covenant (4 questions: 2 MC, 2 OE)
    # ===========================================
    {
        "category": "The New Covenant",
        "text": "According to Hebrews 8:6-13, the new covenant is better than the old because:",
        "type": "multiple_choice",
        "options": [
            {"text": "It has simpler requirements and is easier to follow", "is_correct": False},
            {"text": "It is available to Gentiles, not just Jews", "is_correct": False},
            {"text": "It includes the gift of the Holy Spirit to all believers", "is_correct": False},
            {"text": "God writes His laws on hearts and minds, and sins are remembered no more", "is_correct": True}  # D - CORRECT
        ]
    },
    {
        "category": "The New Covenant",
        "text": "Hebrews 9:22 states a principle about forgiveness under the law:",
        "type": "multiple_choice",
        "options": [
            {"text": "Forgiveness comes through sincere repentance and restitution", "is_correct": False},
            {"text": "Without the shedding of blood there is no forgiveness", "is_correct": True},  # B - CORRECT
            {"text": "Forgiveness requires faith in God's promises", "is_correct": False},
            {"text": "Forgiveness is granted through the intercession of priests", "is_correct": False}
        ]
    },
    {
        "category": "The New Covenant",
        "text": "Hebrews 10:14 says by one sacrifice Jesus 'made perfect forever those who are being made holy.' How do you understand being already 'made perfect' while still 'being made holy'?",
        "type": "open_ended",
        "options": []
    },
    {
        "category": "The New Covenant",
        "text": "The old covenant required repeated sacrifices that could never fully cleanse the conscience (Heb 10:1-4). How does the finality of Christ's sacrifice ('It is finished') bring you peace when you struggle with guilt?",
        "type": "open_ended",
        "options": []
    },
    # ===========================================
    # CATEGORY: Faith & the Heroes of Faith (4 questions: 2 MC, 2 OE)
    # ===========================================
    {
        "category": "Faith & the Heroes of Faith",
        "text": "Hebrews 11:1 defines faith as:",
        "type": "multiple_choice",
        "options": [
            {"text": "Confidence in what we hope for and assurance about what we do not see", "is_correct": True},  # A - CORRECT
            {"text": "Trusting God's promises even when circumstances seem impossible", "is_correct": False},
            {"text": "Believing without any evidence or reason to doubt", "is_correct": False},
            {"text": "Complete surrender of our will to God's plan for our lives", "is_correct": False}
        ]
    },
    {
        "category": "Faith & the Heroes of Faith",
        "text": "What common thread unites all the heroes of faith in Hebrews 11?",
        "type": "multiple_choice",
        "options": [
            {"text": "They all received the fulfillment of God's promises in their lifetime", "is_correct": False},
            {"text": "They all performed great miracles that demonstrated God's power", "is_correct": False},
            {"text": "They all died in faith without receiving what was promised, looking forward to a heavenly city", "is_correct": True},  # C - CORRECT
            {"text": "They all suffered martyrdom for their refusal to deny God", "is_correct": False}
        ]
    },
    {
        "category": "Faith & the Heroes of Faith",
        "text": "Hebrews 11 recounts people who by faith conquered kingdoms, but also those who were tortured, imprisoned, and killed. What does this teach you about the nature of faith and God's purposes?",
        "type": "open_ended",
        "options": []
    },
    {
        "category": "Faith & the Heroes of Faith",
        "text": "Which person from Hebrews 11 do you most relate to right now in your faith journey? Why?",
        "type": "open_ended",
        "options": []
    },
    # ===========================================
    # CATEGORY: Perseverance & Endurance (4 questions: 3 MC, 1 OE)
    # ===========================================
    {
        "category": "Perseverance & Endurance",
        "text": "Hebrews 12:1-2 calls believers to run the race of faith by:",
        "type": "multiple_choice",
        "options": [
            {"text": "Comparing ourselves to the heroes of faith and striving to match their achievements", "is_correct": False},
            {"text": "Throwing off everything that hinders, fixing our eyes on Jesus who endured the cross", "is_correct": True},  # B - CORRECT
            {"text": "Relying on our own strength and determination to finish strong", "is_correct": False},
            {"text": "Focusing on the prize and reward that awaits us at the finish line", "is_correct": False}
        ]
    },
    {
        "category": "Perseverance & Endurance",
        "text": "According to Hebrews 12:5-11, God's discipline of His children is:",
        "type": "multiple_choice",
        "options": [
            {"text": "Punishment for specific sins we have committed", "is_correct": False},
            {"text": "A sign that we may not truly belong to God", "is_correct": False},
            {"text": "Temporary suffering that will be repaid with earthly blessing", "is_correct": False},
            {"text": "Proof of His love and produces a harvest of righteousness", "is_correct": True}  # D - CORRECT
        ]
    },
    {
        "category": "Perseverance & Endurance",
        "text": "Hebrews 10:24-25 exhorts believers to:",
        "type": "multiple_choice",
        "options": [
            {"text": "Spur one another on toward love and good deeds, not giving up meeting together", "is_correct": True},  # A - CORRECT
            {"text": "Focus on personal spiritual growth and individual Bible study", "is_correct": False},
            {"text": "Separate from unbelievers and form holy communities", "is_correct": False},
            {"text": "Submit to church leaders and follow their instructions carefully", "is_correct": False}
        ]
    },
    {
        "category": "Perseverance & Endurance",
        "text": "Hebrews 12:1 speaks of a 'great cloud of witnesses' surrounding us. How does remembering those who have gone before in faith encourage you in your current struggles?",
        "type": "open_ended",
        "options": []
    },
    # ===========================================
    # CATEGORY: Warnings Against Falling Away (4 questions: 2 MC, 2 OE)
    # ===========================================
    {
        "category": "Warnings Against Falling Away",
        "text": "The warning in Hebrews 2:1-3 urges readers to:",
        "type": "multiple_choice",
        "options": [
            {"text": "Beware of false teachers who distort the gospel message", "is_correct": False},
            {"text": "Guard against persecution that could cause them to deny Christ", "is_correct": False},
            {"text": "Pay careful attention to what they've heard so they don't drift away", "is_correct": True},  # C - CORRECT
            {"text": "Remain committed to the Jewish law while also following Christ", "is_correct": False}
        ]
    },
    {
        "category": "Warnings Against Falling Away",
        "text": "Hebrews 6:4-6 contains a sobering warning about those who:",
        "type": "multiple_choice",
        "options": [
            {"text": "Have shared in the Holy Spirit but fall away, crucifying the Son of God all over again", "is_correct": True},  # A - CORRECT
            {"text": "Commit the unforgivable sin of blasphemy against the Holy Spirit", "is_correct": False},
            {"text": "Reject the gospel after hearing it clearly explained", "is_correct": False},
            {"text": "Return to sinful lifestyles after making a public profession of faith", "is_correct": False}
        ]
    },
    {
        "category": "Warnings Against Falling Away",
        "text": "Hebrews contains serious warnings about apostasy alongside assurances of God's faithfulness. How do you hold these tensions together? Do the warnings make you fearful or watchful?",
        "type": "open_ended",
        "options": []
    },
    {
        "category": "Warnings Against Falling Away",
        "text": "Hebrews 3:12-13 warns against developing 'a sinful, unbelieving heart that turns away from the living God' and calls believers to encourage one another daily. What does this kind of daily encouragement look like practically?",
        "type": "open_ended",
        "options": []
    },
    # ===========================================
    # CATEGORY: Living by Faith (3 questions: 2 MC, 1 OE)
    # ===========================================
    {
        "category": "Living by Faith",
        "text": "According to Hebrews 13:5-6, believers can be content and free from the love of money because:",
        "type": "multiple_choice",
        "options": [
            {"text": "God promises material prosperity to those who are faithful", "is_correct": False},
            {"text": "God has said 'Never will I leave you; never will I forsake you'", "is_correct": True},  # B - CORRECT
            {"text": "Earthly wealth is meaningless compared to heavenly treasures", "is_correct": False},
            {"text": "Contentment is a spiritual discipline we must cultivate", "is_correct": False}
        ]
    },
    {
        "category": "Living by Faith",
        "text": "Hebrews 13:14-16 describes the sacrifices pleasing to God as:",
        "type": "multiple_choice",
        "options": [
            {"text": "Financial offerings given generously to the church and the poor", "is_correct": False},
            {"text": "Faithful attendance at worship and religious observances", "is_correct": False},
            {"text": "Surrendering our desires and ambitions to God's will", "is_correct": False},
            {"text": "Praise from lips that confess His name and doing good and sharing with others", "is_correct": True}  # D - CORRECT
        ]
    },
    {
        "category": "Living by Faith",
        "text": "Hebrews 13:8 declares 'Jesus Christ is the same yesterday and today and forever.' In a world of constant change and uncertainty, how does Christ's unchanging nature provide an anchor for your soul (6:19)?",
        "type": "open_ended",
        "options": []
    },
]

def main():
    print("=" * 60)
    print("Hebrews Assessment Setup")
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
                print(f"✅ Created Hebrews Assessment template: {template_id}")
            
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
                question_code = f"HEB_{question_order:03d}"
                
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
            print(f"✅ SUCCESS! Created Hebrews Assessment")
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
