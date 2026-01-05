"""
Script to create the Gospel of Luke Assessment
Run as: python setup_luke_gospel_assessment.py
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
ASSESSMENT_KEY = "luke_gospel_v1"
ASSESSMENT_NAME = "The Gospel of Luke"
ASSESSMENT_DESCRIPTION = """Explore the Gospel of Luke — the most detailed account of Jesus' life, written for all people. This assessment covers the birth narrative, Jesus' heart for the marginalized, parables of grace, the cost of discipleship, prayer, Jesus' determined journey to Jerusalem, and the cross and resurrection. Gospel-centered open-ended questions help you encounter the Savior of the world. 25 questions (15 multiple choice, 10 open-ended) across 7 categories."""

# Questions organized by category
# NOTE: Correct answers are distributed across positions A, B, C, D
# NOTE: All options are balanced in length to avoid obvious patterns
QUESTIONS_DATA = [
    # ===========================================
    # CATEGORY: The Savior Is Born — Good News for All (4 questions: 2 MC, 2 OE)
    # ===========================================
    {
        "category": "The Savior Is Born — Good News for All",
        "text": "When the angel announced Jesus' birth to the shepherds (Luke 2), the message was significant because shepherds were:",
        "type": "multiple_choice",
        "options": [
            {"text": "Wealthy landowners who could support Jesus' ministry financially", "is_correct": False},
            {"text": "Lowly outcasts — God announced the Savior first to the marginalized", "is_correct": True},  # B - CORRECT
            {"text": "Religious leaders responsible for spreading news in the temple", "is_correct": False},
            {"text": "Roman officials with the authority to protect the newborn king", "is_correct": False}
        ]
    },
    {
        "category": "The Savior Is Born — Good News for All",
        "text": "Mary's song (the Magnificat) proclaimed that God:",
        "type": "multiple_choice",
        "options": [
            {"text": "Would establish Israel as the dominant military power on earth", "is_correct": False},
            {"text": "Would make Mary famous and honored throughout all nations", "is_correct": False},
            {"text": "Brings down the proud and mighty, and lifts up the humble", "is_correct": True},  # C - CORRECT
            {"text": "Would immediately destroy all of Israel's Gentile enemies", "is_correct": False}
        ]
    },
    {
        "category": "The Savior Is Born — Good News for All",
        "text": "The angels announced 'good news of great joy for all people' — shepherds, outsiders, the overlooked. God didn't announce the Savior to kings first, but to nobodies in a field. How does this shape your understanding of who the gospel is for? Do you ever feel too insignificant for God's attention?",
        "type": "open_ended",
        "options": []
    },
    {
        "category": "The Savior Is Born — Good News for All",
        "text": "Mary sang, 'He has brought down the mighty from their thrones and exalted those of humble estate' (Luke 1:52). Luke's Gospel consistently shows God reversing the world's values. Where do you see the world's values and the Kingdom's values in conflict? How does the gospel challenge your own assumptions about status and success?",
        "type": "open_ended",
        "options": []
    },
    # ===========================================
    # CATEGORY: Jesus & the Marginalized — Savior of the Lost (3 questions: 2 MC, 1 OE)
    # ===========================================
    {
        "category": "Jesus & the Marginalized — Savior of the Lost",
        "text": "In the Nazareth synagogue (Luke 4), the crowd turned violent when Jesus:",
        "type": "multiple_choice",
        "options": [
            {"text": "Claimed to be greater than Moses and all the prophets combined", "is_correct": False},
            {"text": "Refused to perform any miracles for His own hometown crowd", "is_correct": False},
            {"text": "Harshly condemned their beloved religious traditions and leaders", "is_correct": False},
            {"text": "Said God sent Elijah and Elisha to Gentiles, not Israelites", "is_correct": True}  # D - CORRECT
        ]
    },
    {
        "category": "Jesus & the Marginalized — Savior of the Lost",
        "text": "When the Pharisees grumbled about Jesus eating with sinners, He responded:",
        "type": "multiple_choice",
        "options": [
            {"text": "By apologizing and promising to avoid such people going forward", "is_correct": False},
            {"text": "'The healthy don't need a doctor — I came to call sinners'", "is_correct": True},  # B - CORRECT
            {"text": "By explaining that these tax collectors were actually good people", "is_correct": False},
            {"text": "By condemning the tax collectors along with the complaining Pharisees", "is_correct": False}
        ]
    },
    {
        "category": "Jesus & the Marginalized — Savior of the Lost",
        "text": "Jesus intentionally sought out the people everyone else avoided — lepers, tax collectors, prostitutes, Samaritans, the poor. Who are the 'untouchables' in your world — the people others avoid or look down on? How is Jesus calling you to see them differently? What would it look like to follow His example?",
        "type": "open_ended",
        "options": []
    },
    # ===========================================
    # CATEGORY: Parables of Grace — The Father's Heart (4 questions: 2 MC, 2 OE)
    # ===========================================
    {
        "category": "Parables of Grace — The Father's Heart",
        "text": "In the Parable of the Prodigal Son (Luke 15), when the son returned, the father:",
        "type": "multiple_choice",
        "options": [
            {"text": "Made him work as a servant first to prove his sincerity", "is_correct": False},
            {"text": "Lectured him about his foolishness before offering forgiveness", "is_correct": False},
            {"text": "Ran to embrace him and threw a feast, fully restoring him", "is_correct": True},  # C - CORRECT
            {"text": "Forgave him but permanently reduced his share of inheritance", "is_correct": False}
        ]
    },
    {
        "category": "Parables of Grace — The Father's Heart",
        "text": "In the Parable of the Pharisee and Tax Collector (Luke 18), the tax collector was justified because:",
        "type": "multiple_choice",
        "options": [
            {"text": "He carefully listed all his charitable deeds before God in prayer", "is_correct": False},
            {"text": "He was secretly more righteous than the self-righteous Pharisee", "is_correct": False},
            {"text": "He made a detailed promise to change his sinful ways completely", "is_correct": False},
            {"text": "He simply confessed, 'God, have mercy on me, a sinner'", "is_correct": True}  # D - CORRECT
        ]
    },
    {
        "category": "Parables of Grace — The Father's Heart",
        "text": "The father in the Prodigal Son story ran to his son, embraced him while still filthy, and restored him completely — before the son could finish his apology. How does this picture of the Father challenge your view of God? Do you approach God expecting embrace or expecting to earn your way back?",
        "type": "open_ended",
        "options": []
    },
    {
        "category": "Parables of Grace — The Father's Heart",
        "text": "The older brother in the parable refused to celebrate his brother's return. He had stayed home, obeyed the rules, and resented the grace shown to the rebel. Which son do you relate to more? In what ways might you be an 'older brother' — obeying outwardly while harboring resentment or self-righteousness?",
        "type": "open_ended",
        "options": []
    },
    # ===========================================
    # CATEGORY: The Cost of Discipleship — Following Jesus (3 questions: 2 MC, 1 OE)
    # ===========================================
    {
        "category": "The Cost of Discipleship — Following Jesus",
        "text": "Jesus said, 'Take up your cross daily and follow me' (Luke 9:23). 'Taking up your cross' means:",
        "type": "multiple_choice",
        "options": [
            {"text": "Wearing a cross necklace as a visible symbol of your faith", "is_correct": False},
            {"text": "Patiently enduring life's minor inconveniences and frustrations", "is_correct": False},
            {"text": "Dying to self-will and being willing to suffer for Jesus", "is_correct": True},  # C - CORRECT
            {"text": "Carrying an actual wooden cross on religious pilgrimages", "is_correct": False}
        ]
    },
    {
        "category": "The Cost of Discipleship — Following Jesus",
        "text": "When a man said he would follow Jesus after burying his father, Jesus' response taught that:",
        "type": "multiple_choice",
        "options": [
            {"text": "Funerals are unimportant rituals that believers should skip", "is_correct": False},
            {"text": "Following Jesus demands ultimate allegiance above all else", "is_correct": True},  # B - CORRECT
            {"text": "Family relationships have no value in God's kingdom plan", "is_correct": False},
            {"text": "The man was lying and his father wasn't actually dead yet", "is_correct": False}
        ]
    },
    {
        "category": "The Cost of Discipleship — Following Jesus",
        "text": "Jesus said, 'Whoever does not carry their own cross and follow me cannot be my disciple' (Luke 14:27). He warned people to count the cost before following Him. Have you counted the cost? What has following Jesus cost you — or what might it cost you? Are there areas where you're holding back from full surrender?",
        "type": "open_ended",
        "options": []
    },
    # ===========================================
    # CATEGORY: Prayer & the Holy Spirit (4 questions: 2 MC, 2 OE)
    # ===========================================
    {
        "category": "Prayer & the Holy Spirit",
        "text": "Luke's Gospel emphasizes that Jesus prayed:",
        "type": "multiple_choice",
        "options": [
            {"text": "Only when facing major decisions or serious crises in ministry", "is_correct": False},
            {"text": "Only in the temple or synagogue where prayer was appropriate", "is_correct": False},
            {"text": "Constantly — before key events, alone, and all night at times", "is_correct": True},  # C - CORRECT
            {"text": "Silently and privately without the disciples ever knowing about it", "is_correct": False}
        ]
    },
    {
        "category": "Prayer & the Holy Spirit",
        "text": "In the parable of the persistent widow (Luke 18), Jesus taught that:",
        "type": "multiple_choice",
        "options": [
            {"text": "God is reluctant like the judge and must be worn down over time", "is_correct": False},
            {"text": "We should pray about each matter only once and then let it go", "is_correct": False},
            {"text": "Prayer is ineffective unless it is done publicly with witnesses", "is_correct": False},
            {"text": "If an unjust judge responds, how much more will our good Father", "is_correct": True}  # D - CORRECT
        ]
    },
    {
        "category": "Prayer & the Holy Spirit",
        "text": "Luke shows Jesus praying more than any other Gospel — at His baptism, before choosing the Twelve, at the Transfiguration, in Gethsemane. If Jesus needed constant communion with the Father, how much more do we? How does Jesus' prayer life challenge or inspire your own? What would change if you prayed like Jesus did?",
        "type": "open_ended",
        "options": []
    },
    {
        "category": "Prayer & the Holy Spirit",
        "text": "Jesus told the parable of the friend at midnight (Luke 11) and the persistent widow (Luke 18) to teach bold, shameless persistence in prayer. Yet many of us give up quickly. What prayers have you stopped praying? What would it look like to bring them to God with renewed persistence and faith?",
        "type": "open_ended",
        "options": []
    },
    # ===========================================
    # CATEGORY: The Journey to Jerusalem — The Determined Savior (3 questions: 2 MC, 1 OE)
    # ===========================================
    {
        "category": "The Journey to Jerusalem — The Determined Savior",
        "text": "Luke 9:51 says Jesus 'set his face to go to Jerusalem.' This phrase emphasizes:",
        "type": "multiple_choice",
        "options": [
            {"text": "Jesus' anger and frustration toward the religious leaders there", "is_correct": False},
            {"text": "Jesus' determined resolve — He knew what awaited and went willingly", "is_correct": True},  # B - CORRECT
            {"text": "Jesus' uncertainty about His mission and need for clarity", "is_correct": False},
            {"text": "Jerusalem was simply the logical next destination on His route", "is_correct": False}
        ]
    },
    {
        "category": "The Journey to Jerusalem — The Determined Savior",
        "text": "On the Emmaus road after the resurrection, Jesus explained that:",
        "type": "multiple_choice",
        "options": [
            {"text": "His death was an unfortunate detour from the original plan", "is_correct": False},
            {"text": "The disciples should have fought harder to stop His crucifixion", "is_correct": False},
            {"text": "The resurrection made the Old Testament unnecessary going forward", "is_correct": False},
            {"text": "All the Scriptures — Moses and Prophets — pointed to Him", "is_correct": True}  # D - CORRECT
        ]
    },
    {
        "category": "The Journey to Jerusalem — The Determined Savior",
        "text": "Jesus 'set his face' toward Jerusalem, knowing betrayal, mockery, torture, and death awaited Him — yet He went willingly for you. How does His determined love affect you? What fears or hardships are you facing that feel overwhelming? How does Jesus' resolve to save you give you courage?",
        "type": "open_ended",
        "options": []
    },
    # ===========================================
    # CATEGORY: The Cross & Resurrection — Salvation Accomplished (4 questions: 3 MC, 1 OE)
    # ===========================================
    {
        "category": "The Cross & Resurrection — Salvation Accomplished",
        "text": "On the cross, Jesus prayed, 'Father, forgive them, for they know not what they do' (Luke 23:34). This shows:",
        "type": "multiple_choice",
        "options": [
            {"text": "The Roman soldiers were completely innocent of wrongdoing", "is_correct": False},
            {"text": "Jesus extending grace even to those actively killing Him", "is_correct": True},  # B - CORRECT
            {"text": "That ignorance of the law automatically removes all guilt", "is_correct": False},
            {"text": "Jesus was confused and delirious from the intense pain", "is_correct": False}
        ]
    },
    {
        "category": "The Cross & Resurrection — Salvation Accomplished",
        "text": "When the criminal on the cross asked Jesus to remember him, Jesus promised:",
        "type": "multiple_choice",
        "options": [
            {"text": "'You must wait until the final judgment to know your fate'", "is_correct": False},
            {"text": "'If you somehow survive, live a better life from now on'", "is_correct": False},
            {"text": "'Today you will be with me in paradise'", "is_correct": True},  # C - CORRECT
            {"text": "'Your crimes are too severe to receive full forgiveness'", "is_correct": False}
        ]
    },
    {
        "category": "The Cross & Resurrection — Salvation Accomplished",
        "text": "Jesus' final commission (Luke 24:47) that repentance and forgiveness be preached 'to all nations' emphasizes:",
        "type": "multiple_choice",
        "options": [
            {"text": "The gospel was primarily intended for Jews in Jerusalem only", "is_correct": False},
            {"text": "Forgiveness requires significant good works following repentance", "is_correct": False},
            {"text": "Luke's theme: salvation is for all peoples, not just Israel", "is_correct": True},  # C - CORRECT
            {"text": "The disciples were commanded to stay in Jerusalem permanently", "is_correct": False}
        ]
    },
    {
        "category": "The Cross & Resurrection — Salvation Accomplished",
        "text": "The thief on the cross had no time for good works, no baptism, no church membership — just a desperate plea to Jesus in his final moments, and Jesus promised him paradise that very day. What does this tell you about salvation? How does this story confront the idea that we must earn our way to God? Who in your life needs to hear that it's never too late?",
        "type": "open_ended",
        "options": []
    },
]

def main():
    print("=" * 60)
    print("Gospel of Luke Assessment Setup")
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
                print(f"✅ Created Gospel of Luke Assessment template: {template_id}")
            
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
                question_code = f"LUKE_{question_order:03d}"
                
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
            print(f"✅ SUCCESS! Created Gospel of Luke Assessment")
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
