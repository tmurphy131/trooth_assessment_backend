"""
Script to create the Free to Rejoice: Galatians & Philippians Assessment
Run as: python setup_galatians_philippians_assessment.py
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
ASSESSMENT_KEY = "galatians_philippians_v1"
ASSESSMENT_NAME = "Free to Rejoice: Galatians & Philippians"
ASSESSMENT_DESCRIPTION = """Explore Paul's passionate letters to the Galatians and Philippians — twin epistles of freedom and joy. This assessment covers the gospel of grace, freedom in Christ, walking by the Spirit, the mind of Christ, joy in all circumstances, pressing toward the goal, and gospel partnership. Gospel-centered open-ended questions help you embrace freedom from legalism and find joy in knowing Christ. 25 questions (15 multiple choice, 10 open-ended) across 7 categories."""

# Questions organized by category
# NOTE: Correct answers distributed across A, B, C, D positions (4 A's, 3 B's, 4 C's, 4 D's)
# NOTE: All options are balanced in length to avoid obvious patterns
QUESTIONS_DATA = [
    # ===========================================
    # CATEGORY: The Gospel of Grace — Justified by Faith (3 questions: 2 MC, 1 OE)
    # ===========================================
    {
        "category": "The Gospel of Grace — Justified by Faith",
        "text": "Paul begins Galatians expressing astonishment that the churches are 'so quickly deserting' the gospel. His primary concern was that they were:",
        "type": "multiple_choice",
        "options": [
            {"text": "Returning to pagan idol worship and temple sacrifices", "is_correct": False},
            {"text": "Rejecting Paul's authority as a legitimate apostle", "is_correct": False},
            {"text": "Refusing to support his missionary journeys financially", "is_correct": False},
            {"text": "Adding circumcision and law-keeping to faith in Christ", "is_correct": True}  # D - CORRECT
        ]
    },
    {
        "category": "The Gospel of Grace — Justified by Faith",
        "text": "In Galatians 2:20, Paul declares 'I have been crucified with Christ. It is no longer I who live, but Christ who lives in me.' This means:",
        "type": "multiple_choice",
        "options": [
            {"text": "Paul experienced a literal death and miraculous resurrection", "is_correct": False},
            {"text": "The old self-righteous Paul died; Christ now defines his identity", "is_correct": True},  # B - CORRECT
            {"text": "Physical death holds no fear because heaven is guaranteed", "is_correct": False},
            {"text": "Christians should seek martyrdom to prove their devotion", "is_correct": False}
        ]
    },
    {
        "category": "The Gospel of Grace — Justified by Faith",
        "text": "Paul opposed Peter 'to his face' when Peter withdrew from eating with Gentiles (Gal 2:11-14). Peter wasn't denying doctrine — he was just avoiding social awkwardness. Yet Paul called it 'not walking in step with the gospel.' How can our behavior — who we include, exclude, or treat differently — contradict the gospel even when our beliefs are technically correct? Where might you be doing this?",
        "type": "open_ended",
        "options": []
    },
    # ===========================================
    # CATEGORY: Freedom in Christ — No Longer Slaves (4 questions: 2 MC, 2 OE)
    # ===========================================
    {
        "category": "Freedom in Christ — No Longer Slaves",
        "text": "Paul uses Abraham to argue that righteousness comes by faith, not law. He points out that Abraham 'believed God, and it was counted to him as righteousness' (Gal 3:6). This happened:",
        "type": "multiple_choice",
        "options": [
            {"text": "After Abraham perfectly obeyed God's commands for many years", "is_correct": False},
            {"text": "When Abraham offered Isaac on the altar at Mount Moriah", "is_correct": False},
            {"text": "Before the law existed — 430 years before Moses received it", "is_correct": True},  # C - CORRECT
            {"text": "Once Abraham was circumcised as a sign of the covenant", "is_correct": False}
        ]
    },
    {
        "category": "Freedom in Christ — No Longer Slaves",
        "text": "Paul says the law was our 'guardian' (or schoolmaster) until Christ came (Gal 3:24-25). The purpose of this guardian was to:",
        "type": "multiple_choice",
        "options": [
            {"text": "Show our inability to save ourselves, leading us to Christ", "is_correct": True},  # A - CORRECT
            {"text": "Provide a permanent moral code for righteous living", "is_correct": False},
            {"text": "Separate Israel as morally superior to other nations", "is_correct": False},
            {"text": "Give detailed instructions for earning God's approval", "is_correct": False}
        ]
    },
    {
        "category": "Freedom in Christ — No Longer Slaves",
        "text": "'For freedom Christ has set us free; stand firm therefore, and do not submit again to a yoke of slavery' (Gal 5:1). Paul warns against returning to slavery — not just to the Mosaic law, but to any system of earning God's favor. What 'yokes of slavery' are you tempted to put back on? What rules, rituals, or performance metrics do you use to measure your standing with God instead of resting in Christ's finished work?",
        "type": "open_ended",
        "options": []
    },
    {
        "category": "Freedom in Christ — No Longer Slaves",
        "text": "Paul says, 'There is neither Jew nor Greek, slave nor free, male nor female, for you are all one in Christ Jesus' (Gal 3:28). This doesn't erase distinctions — it transforms their significance. We no longer use categories to determine worth or access to God. What categories (education, income, race, status) do you still use to rank people's value? How does the gospel challenge that?",
        "type": "open_ended",
        "options": []
    },
    # ===========================================
    # CATEGORY: Walking by the Spirit — Flesh vs. Spirit (3 questions: 2 MC, 1 OE)
    # ===========================================
    {
        "category": "Walking by the Spirit — Flesh vs. Spirit",
        "text": "Paul contrasts the 'works of the flesh' with the 'fruit of the Spirit' (Gal 5:19-23). The difference between 'works' and 'fruit' suggests:",
        "type": "multiple_choice",
        "options": [
            {"text": "Flesh produces effort-based results; Spirit produces organic growth", "is_correct": True},  # A - CORRECT
            {"text": "Works are visible to others while fruit remains internal", "is_correct": False},
            {"text": "Fleshly works are serious sins; Spirit fruit is minor virtues", "is_correct": False},
            {"text": "Works come naturally to us; fruit requires external motivation", "is_correct": False}
        ]
    },
    {
        "category": "Walking by the Spirit — Flesh vs. Spirit",
        "text": "'If we live by the Spirit, let us also keep in step with the Spirit' (Gal 5:25). 'Keep in step' implies:",
        "type": "multiple_choice",
        "options": [
            {"text": "Following strict rules to avoid grieving the Holy Spirit", "is_correct": False},
            {"text": "Achieving spiritual experiences through intense discipline", "is_correct": False},
            {"text": "Matching our daily conduct to the new life we've received", "is_correct": True},  # C - CORRECT
            {"text": "Waiting passively for the Spirit to override our choices", "is_correct": False}
        ]
    },
    {
        "category": "Walking by the Spirit — Flesh vs. Spirit",
        "text": "The fruit of the Spirit — love, joy, peace, patience, kindness, goodness, faithfulness, gentleness, self-control — is singular: 'fruit,' not 'fruits.' It's one integrated character that the Spirit produces. Which aspect of this fruit is most lacking in your life right now? What would it look like for the Spirit to grow that in you, and what might be blocking it?",
        "type": "open_ended",
        "options": []
    },
    # ===========================================
    # CATEGORY: The Mind of Christ — Humble Servanthood (4 questions: 2 MC, 2 OE)
    # ===========================================
    {
        "category": "The Mind of Christ — Humble Servanthood",
        "text": "The Christ-hymn in Philippians 2:6-11 describes Jesus as one who 'did not count equality with God a thing to be grasped.' This means Jesus:",
        "type": "multiple_choice",
        "options": [
            {"text": "Was uncertain whether He was truly equal with God", "is_correct": False},
            {"text": "Gradually achieved equality with God through obedience", "is_correct": False},
            {"text": "Temporarily lost His divinity during His time on earth", "is_correct": False},
            {"text": "Didn't exploit His divine status but emptied Himself to serve", "is_correct": True}  # D - CORRECT
        ]
    },
    {
        "category": "The Mind of Christ — Humble Servanthood",
        "text": "Paul says God 'highly exalted' Jesus and gave Him 'the name above every name' (Phil 2:9). This exaltation came:",
        "type": "multiple_choice",
        "options": [
            {"text": "Before creation as part of God's eternal plan", "is_correct": False},
            {"text": "At His baptism when the Spirit descended on Him", "is_correct": False},
            {"text": "As a result of His humble obedience even to death", "is_correct": True},  # C - CORRECT
            {"text": "When He performed miracles proving His divine power", "is_correct": False}
        ]
    },
    {
        "category": "The Mind of Christ — Humble Servanthood",
        "text": "'Do nothing from selfish ambition or conceit, but in humility count others more significant than yourselves' (Phil 2:3). This isn't about low self-esteem — it's about redirecting our focus from self-promotion to others' interests. Where does selfish ambition or conceit show up most in your life? What relationship or situation is God calling you to practice this 'others-first' humility?",
        "type": "open_ended",
        "options": []
    },
    {
        "category": "The Mind of Christ — Humble Servanthood",
        "text": "Jesus 'emptied himself, taking the form of a servant' (Phil 2:7). The eternal Son chose downward mobility — from heaven's throne to a feeding trough to a criminal's cross. How does our culture's obsession with status, promotion, and recognition conflict with this? What would it cost you to embrace downward mobility in some area of your life?",
        "type": "open_ended",
        "options": []
    },
    # ===========================================
    # CATEGORY: Joy in All Circumstances — Rejoicing Always (4 questions: 3 MC, 1 OE)
    # ===========================================
    {
        "category": "Joy in All Circumstances — Rejoicing Always",
        "text": "Paul wrote Philippians while imprisoned, yet uses the word 'joy' or 'rejoice' over a dozen times. His joy was possible because:",
        "type": "multiple_choice",
        "options": [
            {"text": "His joy was rooted in Christ, not external circumstances", "is_correct": True},  # A - CORRECT
            {"text": "His circumstances were actually quite comfortable in Rome", "is_correct": False},
            {"text": "He expected release and vindication very soon", "is_correct": False},
            {"text": "Roman guards had become friendly and supportive", "is_correct": False}
        ]
    },
    {
        "category": "Joy in All Circumstances — Rejoicing Always",
        "text": "'Rejoice in the Lord always; again I will say, rejoice' (Phil 4:4). Paul repeats this command because:",
        "type": "multiple_choice",
        "options": [
            {"text": "The Philippians were wealthy and had much to celebrate", "is_correct": False},
            {"text": "Joy is a choice anchored in who God is, not what's happening", "is_correct": True},  # B - CORRECT
            {"text": "Repetition was a common rhetorical style with no significance", "is_correct": False},
            {"text": "He wanted them to appear happy to attract converts", "is_correct": False}
        ]
    },
    {
        "category": "Joy in All Circumstances — Rejoicing Always",
        "text": "Paul's famous statement 'I can do all things through him who strengthens me' (Phil 4:13) is about:",
        "type": "multiple_choice",
        "options": [
            {"text": "Achieving success in any endeavor through positive faith", "is_correct": False},
            {"text": "Performing supernatural miracles through Christ's power", "is_correct": False},
            {"text": "Overcoming any opponent who opposes the gospel mission", "is_correct": False},
            {"text": "Being content in any circumstance — abundance or need", "is_correct": True}  # D - CORRECT
        ]
    },
    {
        "category": "Joy in All Circumstances — Rejoicing Always",
        "text": "'Do not be anxious about anything, but in everything by prayer and supplication with thanksgiving let your requests be made known to God' (Phil 4:6). Paul doesn't say 'don't have problems' — he says bring them to God with thanksgiving. What are you most anxious about right now? What would it look like to bring that specific thing to God with gratitude rather than just worry?",
        "type": "open_ended",
        "options": []
    },
    # ===========================================
    # CATEGORY: Pressing Toward the Goal — Knowing Christ (4 questions: 2 MC, 2 OE)
    # ===========================================
    {
        "category": "Pressing Toward the Goal — Knowing Christ",
        "text": "Paul had impressive religious credentials — circumcised, tribe of Benjamin, Pharisee, zealous. He says he now counts these as 'loss' and even 'rubbish' (Phil 3:7-8). Why?",
        "type": "multiple_choice",
        "options": [
            {"text": "He discovered those credentials were based on false records", "is_correct": False},
            {"text": "Nothing compares to the surpassing worth of knowing Christ", "is_correct": True},  # B - CORRECT
            {"text": "Jewish heritage became irrelevant after the temple's destruction", "is_correct": False},
            {"text": "His guilt over persecuting Christians made him reject his past", "is_correct": False}
        ]
    },
    {
        "category": "Pressing Toward the Goal — Knowing Christ",
        "text": "'Not that I have already obtained this or am already perfect, but I press on' (Phil 3:12). Paul describes the Christian life as:",
        "type": "multiple_choice",
        "options": [
            {"text": "Instant perfection received at the moment of conversion", "is_correct": False},
            {"text": "Passive waiting for God to complete all necessary work", "is_correct": False},
            {"text": "Ongoing pursuit of Christ while awaiting final transformation", "is_correct": True},  # C - CORRECT
            {"text": "Achieving moral perfection through disciplined effort", "is_correct": False}
        ]
    },
    {
        "category": "Pressing Toward the Goal — Knowing Christ",
        "text": "Paul's one ambition: 'that I may know him and the power of his resurrection, and may share his sufferings, becoming like him in his death' (Phil 3:10). Notice: knowing Christ includes sharing His sufferings. We want resurrection power without crucifixion pain. What suffering in your life might God be using to make you know Christ more deeply? How does that reframe the hardship?",
        "type": "open_ended",
        "options": []
    },
    {
        "category": "Pressing Toward the Goal — Knowing Christ",
        "text": "'Forgetting what lies behind and straining forward to what lies ahead, I press on toward the goal' (Phil 3:13-14). Paul — murderer of Christians — refused to let his past define his future. What past failure, sin, or regret do you keep dragging into your present? What would 'forgetting what lies behind' look like for you, practically?",
        "type": "open_ended",
        "options": []
    },
    # ===========================================
    # CATEGORY: Gospel Partnership — Standing Firm Together (3 questions: 2 MC, 1 OE)
    # ===========================================
    {
        "category": "Gospel Partnership — Standing Firm Together",
        "text": "Paul thanks the Philippians for their 'partnership in the gospel from the first day until now' (Phil 1:5). This partnership included:",
        "type": "multiple_choice",
        "options": [
            {"text": "Their financial support of Paul's missionary work", "is_correct": True},  # A - CORRECT
            {"text": "Only their prayers since they were too poor to give", "is_correct": False},
            {"text": "Sending multiple members to join his apostolic team", "is_correct": False},
            {"text": "Writing letters that Paul included in his epistles", "is_correct": False}
        ]
    },
    {
        "category": "Gospel Partnership — Standing Firm Together",
        "text": "'Only let your manner of life be worthy of the gospel of Christ... standing firm in one spirit, with one mind striving side by side for the faith' (Phil 1:27). Paul emphasizes:",
        "type": "multiple_choice",
        "options": [
            {"text": "Unified community effort, not isolated spiritual heroics", "is_correct": True},  # A - CORRECT
            {"text": "Individual spiritual disciplines practiced in private devotion", "is_correct": False},
            {"text": "Intellectual agreement on every theological detail", "is_correct": False},
            {"text": "Hierarchical structure with clear chains of command", "is_correct": False}
        ]
    },
    {
        "category": "Gospel Partnership — Standing Firm Together",
        "text": "Paul says he is 'sure of this, that he who began a good work in you will bring it to completion at the day of Jesus Christ' (Phil 1:6). God finishes what He starts. How does this promise encourage you when you feel spiritually stuck or see slow progress? Do you trust that God is still at work in you even when you can't see it?",
        "type": "open_ended",
        "options": []
    },
]

def main():
    print("=" * 60)
    print("Free to Rejoice: Galatians & Philippians Assessment Setup")
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
                print(f"✅ Created Free to Rejoice assessment template: {template_id}")
            
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
                question_code = f"GALPHIL_{question_order:03d}"
                
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
            print(f"✅ SUCCESS! Created Free to Rejoice: Galatians & Philippians Assessment")
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
