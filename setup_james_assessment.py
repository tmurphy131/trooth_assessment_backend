"""
Script to create the James Assessment
Run as: python setup_james_assessment.py
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
ASSESSMENT_KEY = "james_v1"
ASSESSMENT_NAME = "James Assessment"
ASSESSMENT_DESCRIPTION = """Explore the book of James - practical wisdom for living out genuine faith. This assessment covers trials and perseverance, wisdom from above, hearing and doing the word, faith and works, taming the tongue, worldliness vs. humility, and patient prayer. 27 questions (16 multiple choice, 11 open-ended) across 7 categories."""

# Questions organized by category
QUESTIONS_DATA = [
    # ===========================================
    # CATEGORY: Trials & Perseverance (4 questions: 2 MC, 2 OE)
    # ===========================================
    {
        "category": "Trials & Perseverance",
        "text": "According to James 1:2-4, how should believers respond to trials?",
        "type": "multiple_choice",
        "options": [
            {"text": "Pray for immediate deliverance and claim victory over suffering", "is_correct": False},
            {"text": "Accept them as punishment for sin and seek to make amends", "is_correct": False},
            {"text": "Consider it pure joy because trials produce perseverance and maturity", "is_correct": True},
            {"text": "Endure patiently while asking God to reveal the purpose behind them", "is_correct": False}
        ]
    },
    {
        "category": "Trials & Perseverance",
        "text": "James 1:12 says the one who perseveres under trial will receive:",
        "type": "multiple_choice",
        "options": [
            {"text": "Prosperity and blessing in this life as a reward for faithfulness", "is_correct": False},
            {"text": "Wisdom and understanding to avoid future trials", "is_correct": False},
            {"text": "The crown of life that the Lord has promised to those who love Him", "is_correct": True},
            {"text": "A special place of honor in the kingdom of heaven", "is_correct": False}
        ]
    },
    {
        "category": "Trials & Perseverance",
        "text": "James says to consider trials 'pure joy' (1:2). What trial are you currently facing, and how does James' perspective challenge or encourage you?",
        "type": "open_ended",
        "options": []
    },
    {
        "category": "Trials & Perseverance",
        "text": "James 1:4 says perseverance must 'finish its work' so we may be 'mature and complete.' What do you think it means to let trials do their full work in your life rather than seeking a quick escape?",
        "type": "open_ended",
        "options": []
    },
    # ===========================================
    # CATEGORY: Wisdom from Above (4 questions: 2 MC, 2 OE)
    # ===========================================
    {
        "category": "Wisdom from Above",
        "text": "According to James 1:5-8, how should a person ask God for wisdom?",
        "type": "multiple_choice",
        "options": [
            {"text": "With fasting and prayer, demonstrating serious commitment to receiving it", "is_correct": False},
            {"text": "By proving they will use it wisely through their past track record", "is_correct": False},
            {"text": "In faith without doubting, for the doubter is unstable and should not expect to receive", "is_correct": True},
            {"text": "With humility, acknowledging they don't deserve God's guidance", "is_correct": False}
        ]
    },
    {
        "category": "Wisdom from Above",
        "text": "James 3:17 describes wisdom from above as:",
        "type": "multiple_choice",
        "options": [
            {"text": "Powerful, authoritative, bold, and commanding respect from others", "is_correct": False},
            {"text": "Intellectual, discerning, logical, and grounded in sound doctrine", "is_correct": False},
            {"text": "Pure, peace-loving, considerate, submissive, full of mercy and good fruit", "is_correct": True},
            {"text": "Patient, steadfast, uncompromising, and zealous for truth", "is_correct": False}
        ]
    },
    {
        "category": "Wisdom from Above",
        "text": "James contrasts earthly wisdom (which is 'unspiritual, demonic') with wisdom from above (3:15-17). How can you tell the difference in practical situations? Give an example.",
        "type": "open_ended",
        "options": []
    },
    {
        "category": "Wisdom from Above",
        "text": "James 1:5 promises God gives wisdom 'generously without finding fault.' How does this promise affect the way you approach God when you're confused or uncertain about a decision?",
        "type": "open_ended",
        "options": []
    },
    # ===========================================
    # CATEGORY: Hearing & Doing the Word (4 questions: 3 MC, 1 OE)
    # ===========================================
    {
        "category": "Hearing & Doing the Word",
        "text": "James 1:22-24 compares a hearer who does not do the word to:",
        "type": "multiple_choice",
        "options": [
            {"text": "A builder who constructs his house on sand instead of rock", "is_correct": False},
            {"text": "A farmer who plants seed but never waters or tends the crop", "is_correct": False},
            {"text": "A person who looks at their face in a mirror and immediately forgets what they look like", "is_correct": True},
            {"text": "A servant who knows the master's will but delays carrying it out", "is_correct": False}
        ]
    },
    {
        "category": "Hearing & Doing the Word",
        "text": "According to James 1:27, pure and faultless religion includes:",
        "type": "multiple_choice",
        "options": [
            {"text": "Faithful church attendance and consistent tithing", "is_correct": False},
            {"text": "Maintaining correct doctrine and defending truth against error", "is_correct": False},
            {"text": "Looking after orphans and widows and keeping oneself unstained by the world", "is_correct": True},
            {"text": "Evangelism and making disciples of all nations", "is_correct": False}
        ]
    },
    {
        "category": "Hearing & Doing the Word",
        "text": "James 2:1-4 warns against showing favoritism. The example he gives involves:",
        "type": "multiple_choice",
        "options": [
            {"text": "Giving positions of leadership only to the wealthy and educated", "is_correct": False},
            {"text": "Listening to some teachers while ignoring others based on their status", "is_correct": False},
            {"text": "Giving a well-dressed person a good seat while making a poor person stand or sit on the floor", "is_correct": True},
            {"text": "Inviting influential people to feasts while neglecting the hungry and poor", "is_correct": False}
        ]
    },
    {
        "category": "Hearing & Doing the Word",
        "text": "James warns against being 'hearers only' (1:22). What is one area where you know what Scripture teaches but struggle to actually live it out? What makes application so difficult?",
        "type": "open_ended",
        "options": []
    },
    # ===========================================
    # CATEGORY: Faith & Works (4 questions: 2 MC, 2 OE)
    # ===========================================
    {
        "category": "Faith & Works",
        "text": "James 2:17 states that faith without works is:",
        "type": "multiple_choice",
        "options": [
            {"text": "Incomplete and in need of maturing through spiritual disciplines", "is_correct": False},
            {"text": "Genuine but weak, requiring encouragement to grow", "is_correct": False},
            {"text": "Dead, being by itself without evidence of life", "is_correct": True},
            {"text": "Acceptable to God but missing out on earthly rewards", "is_correct": False}
        ]
    },
    {
        "category": "Faith & Works",
        "text": "James uses Abraham and Rahab as examples to show that:",
        "type": "multiple_choice",
        "options": [
            {"text": "Both Jews and Gentiles are saved by faith regardless of their background", "is_correct": False},
            {"text": "God rewards exceptional acts of courage and sacrifice", "is_correct": False},
            {"text": "Faith is demonstrated and made complete by what a person does", "is_correct": True},
            {"text": "Even great sinners can be justified if they perform righteous deeds", "is_correct": False}
        ]
    },
    {
        "category": "Faith & Works",
        "text": "James says 'faith without works is dead' (2:26) while Paul says we are 'justified by faith apart from works' (Romans 3:28). How do you understand the relationship between these two teachings?",
        "type": "open_ended",
        "options": []
    },
    {
        "category": "Faith & Works",
        "text": "Think about your own life: What 'works' or actions demonstrate that your faith is alive? What areas might indicate your faith needs to become more active?",
        "type": "open_ended",
        "options": []
    },
    # ===========================================
    # CATEGORY: Taming the Tongue (4 questions: 3 MC, 1 OE)
    # ===========================================
    {
        "category": "Taming the Tongue",
        "text": "James 3:5-6 compares the tongue to:",
        "type": "multiple_choice",
        "options": [
            {"text": "A sharp sword that can defend or destroy depending on how it's used", "is_correct": False},
            {"text": "A wild animal that can be trained with enough patience and discipline", "is_correct": False},
            {"text": "A small spark that sets a great forest ablaze, corrupting the whole person", "is_correct": True},
            {"text": "A rudder that guides a ship wherever the pilot wants it to go", "is_correct": False}
        ]
    },
    {
        "category": "Taming the Tongue",
        "text": "According to James 3:9-10, what inconsistency does James identify regarding the tongue?",
        "type": "multiple_choice",
        "options": [
            {"text": "We speak truth on Sunday but lie throughout the week", "is_correct": False},
            {"text": "We praise God publicly but complain about Him privately", "is_correct": False},
            {"text": "We praise God and curse people who are made in God's image", "is_correct": True},
            {"text": "We speak kindly to friends but harshly to strangers", "is_correct": False}
        ]
    },
    {
        "category": "Taming the Tongue",
        "text": "James 4:11 warns against what specific misuse of speech?",
        "type": "multiple_choice",
        "options": [
            {"text": "Lying and deceiving others for personal gain", "is_correct": False},
            {"text": "Using profanity and coarse language", "is_correct": False},
            {"text": "Slandering and speaking against one another, thereby judging the law", "is_correct": True},
            {"text": "Boasting and bragging about personal accomplishments", "is_correct": False}
        ]
    },
    {
        "category": "Taming the Tongue",
        "text": "James says no human being can tame the tongue (3:8). If that's true, how should believers approach the struggle to control their speech? What has helped you in this area?",
        "type": "open_ended",
        "options": []
    },
    # ===========================================
    # CATEGORY: Worldliness vs. Humility (4 questions: 2 MC, 2 OE)
    # ===========================================
    {
        "category": "Worldliness vs. Humility",
        "text": "James 4:4 says that friendship with the world is:",
        "type": "multiple_choice",
        "options": [
            {"text": "Dangerous but sometimes necessary for the sake of evangelism", "is_correct": False},
            {"text": "A sign of spiritual immaturity that needs correction", "is_correct": False},
            {"text": "Enmity with God; whoever chooses to be a friend of the world becomes an enemy of God", "is_correct": True},
            {"text": "Understandable given the pressures believers face in society", "is_correct": False}
        ]
    },
    {
        "category": "Worldliness vs. Humility",
        "text": "According to James 4:6-10, what is the pathway to receiving God's grace?",
        "type": "multiple_choice",
        "options": [
            {"text": "Faithful obedience, consistent prayer, and generous giving", "is_correct": False},
            {"text": "Confessing sin, making restitution, and committing to change", "is_correct": False},
            {"text": "Humbling yourself before God, resisting the devil, and drawing near to God", "is_correct": True},
            {"text": "Acknowledging weakness, depending on the Spirit, and trusting His promises", "is_correct": False}
        ]
    },
    {
        "category": "Worldliness vs. Humility",
        "text": "James 4:13-16 rebukes those who make plans without acknowledging God's sovereignty, calling it 'arrogance.' How do you balance making wise plans with humbly submitting to God's will?",
        "type": "open_ended",
        "options": []
    },
    {
        "category": "Worldliness vs. Humility",
        "text": "James 4:4 presents a stark choice: friendship with the world or friendship with God. What does 'friendship with the world' look like in your context, and how do you guard against it?",
        "type": "open_ended",
        "options": []
    },
    # ===========================================
    # CATEGORY: Patience & Prayer (3 questions: 2 MC, 1 OE)
    # ===========================================
    {
        "category": "Patience & Prayer",
        "text": "James 5:7-8 calls believers to be patient like:",
        "type": "multiple_choice",
        "options": [
            {"text": "A soldier waiting for orders from his commanding officer", "is_correct": False},
            {"text": "A watchman who stays alert through the night for signs of dawn", "is_correct": False},
            {"text": "A farmer who waits for the valuable harvest after the autumn and spring rains", "is_correct": True},
            {"text": "A servant who waits at the door until the master returns from a journey", "is_correct": False}
        ]
    },
    {
        "category": "Patience & Prayer",
        "text": "According to James 5:13-16, what should believers do when they are sick?",
        "type": "multiple_choice",
        "options": [
            {"text": "Trust in God alone and refuse medical treatment as an act of faith", "is_correct": False},
            {"text": "Examine their lives for unconfessed sin that may have caused the illness", "is_correct": False},
            {"text": "Call the elders to pray and anoint with oil, confessing sins to one another", "is_correct": True},
            {"text": "Pray privately and wait for God to heal in His own time and way", "is_correct": False}
        ]
    },
    {
        "category": "Patience & Prayer",
        "text": "James ends his letter emphasizing prayer (5:13-18), citing Elijah as an example of powerful, effective prayer. What makes prayer 'powerful and effective'? How would you describe your own prayer life right now?",
        "type": "open_ended",
        "options": []
    },
]

def main():
    print("=" * 60)
    print("James Assessment Setup")
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
                print(f"✅ Created James Assessment template: {template_id}")
            
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
                question_code = f"JAS_{question_order:03d}"
                
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
            print(f"✅ SUCCESS! Created James Assessment")
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
