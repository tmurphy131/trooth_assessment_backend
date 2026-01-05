"""
Script to create the Acts Assessment
Run as: python setup_acts_assessment.py
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
ASSESSMENT_KEY = "acts_v1"
ASSESSMENT_NAME = "Acts Assessment"
ASSESSMENT_DESCRIPTION = """Explore the book of Acts - the birth of the church, the Holy Spirit's power, and the spread of the gospel to the ends of the earth. This assessment covers the early church community, bold witness under persecution, Paul's conversion and missionary journeys, and the gospel crossing cultural barriers. 27 questions (16 multiple choice, 11 open-ended) across 7 categories."""

# Questions organized by category
QUESTIONS_DATA = [
    # ===========================================
    # CATEGORY: The Holy Spirit's Coming (4 questions: 2 MC, 2 OE)
    # ===========================================
    {
        "category": "The Holy Spirit's Coming",
        "text": "What happened on the day of Pentecost in Acts 2?",
        "type": "multiple_choice",
        "options": [
            {"text": "The disciples received power to perform miracles and appointed the first deacons", "is_correct": False},
            {"text": "Believers from every nation gathered and Peter delivered the Sermon on the Mount", "is_correct": False},
            {"text": "The Holy Spirit came upon the believers with the sound of wind and tongues of fire", "is_correct": True},
            {"text": "Jesus appeared to five hundred believers and commissioned them as apostles", "is_correct": False}
        ]
    },
    {
        "category": "The Holy Spirit's Coming",
        "text": "What did Jesus tell His disciples to wait for before beginning their mission (Acts 1:4-8)?",
        "type": "multiple_choice",
        "options": [
            {"text": "The destruction of the temple as a sign to begin preaching", "is_correct": False},
            {"text": "Confirmation from the apostles in Jerusalem to authorize their ministry", "is_correct": False},
            {"text": "The gift of the Holy Spirit who would give them power to be witnesses", "is_correct": True},
            {"text": "The conversion of the Jewish leaders to open doors for the gospel", "is_correct": False}
        ]
    },
    {
        "category": "The Holy Spirit's Coming",
        "text": "In Acts 1:8, Jesus says, 'You will be my witnesses in Jerusalem, Judea, Samaria, and to the ends of the earth.' How does this pattern apply to your own life and witness today?",
        "type": "open_ended",
        "options": []
    },
    {
        "category": "The Holy Spirit's Coming",
        "text": "The coming of the Holy Spirit at Pentecost transformed fearful disciples into bold witnesses. How have you experienced the Holy Spirit's empowerment in your own life?",
        "type": "open_ended",
        "options": []
    },
    # ===========================================
    # CATEGORY: The Early Church Community (4 questions: 2 MC, 2 OE)
    # ===========================================
    {
        "category": "The Early Church Community",
        "text": "According to Acts 2:42-47, the early church devoted themselves to:",
        "type": "multiple_choice",
        "options": [
            {"text": "Evangelistic preaching, miraculous signs, caring for widows, and temple worship", "is_correct": False},
            {"text": "The apostles' teaching, fellowship, breaking of bread, and prayer", "is_correct": True},
            {"text": "Scripture study, fasting, financial giving, and spreading the gospel", "is_correct": False},
            {"text": "Community meals, healing the sick, prophetic ministry, and baptism", "is_correct": False}
        ]
    },
    {
        "category": "The Early Church Community",
        "text": "How did the early believers handle their possessions according to Acts 4:32-35?",
        "type": "multiple_choice",
        "options": [
            {"text": "They gave a required portion to the apostles who distributed to those in need", "is_correct": False},
            {"text": "They voluntarily shared everything and there were no needy persons among them", "is_correct": True},
            {"text": "They sold their possessions and pooled resources into a common treasury", "is_correct": False},
            {"text": "They tithed to the church while maintaining private ownership of property", "is_correct": False}
        ]
    },
    {
        "category": "The Early Church Community",
        "text": "The early church in Acts was marked by radical generosity and community. What aspects of their example challenge you? What would it look like for your church to live this way?",
        "type": "open_ended",
        "options": []
    },
    {
        "category": "The Early Church Community",
        "text": "Acts 2:46-47 describes believers meeting daily with 'glad and sincere hearts.' What do you think made their community so attractive that 'the Lord added to their number daily'?",
        "type": "open_ended",
        "options": []
    },
    # ===========================================
    # CATEGORY: Bold Witness & Persecution (4 questions: 3 MC, 1 OE)
    # ===========================================
    {
        "category": "Bold Witness & Persecution",
        "text": "When Peter and John were commanded by the Jewish leaders to stop speaking about Jesus (Acts 4:18-20), how did they respond?",
        "type": "multiple_choice",
        "options": [
            {"text": "They appealed to Roman law protecting their right to religious freedom", "is_correct": False},
            {"text": "They agreed publicly but continued preaching privately in homes", "is_correct": False},
            {"text": "They declared they must obey God rather than men and could not stop speaking", "is_correct": True},
            {"text": "They requested time to pray and later returned with a compromise", "is_correct": False}
        ]
    },
    {
        "category": "Bold Witness & Persecution",
        "text": "Stephen, the first Christian martyr (Acts 7), was killed primarily because:",
        "type": "multiple_choice",
        "options": [
            {"text": "He performed miracles that threatened the authority of the Sanhedrin", "is_correct": False},
            {"text": "He encouraged Jews to stop following the law of Moses", "is_correct": False},
            {"text": "He accused the Jewish leaders of resisting the Holy Spirit and killing the Messiah", "is_correct": True},
            {"text": "He proclaimed that Gentiles could be saved without circumcision", "is_correct": False}
        ]
    },
    {
        "category": "Bold Witness & Persecution",
        "text": "After Stephen's death and the persecution that followed (Acts 8:1-4), what happened?",
        "type": "multiple_choice",
        "options": [
            {"text": "The apostles fled Jerusalem and established new headquarters in Antioch", "is_correct": False},
            {"text": "The church grew stronger in Jerusalem as persecution drew believers together", "is_correct": False},
            {"text": "Scattered believers preached the word wherever they went, spreading the gospel", "is_correct": True},
            {"text": "The persecution ended quickly when Gamaliel intervened on behalf of the church", "is_correct": False}
        ]
    },
    {
        "category": "Bold Witness & Persecution",
        "text": "The early church faced intense persecution yet continued to grow. What do you think gave them such boldness? How does their example speak to believers facing opposition today?",
        "type": "open_ended",
        "options": []
    },
    # ===========================================
    # CATEGORY: Paul's Conversion & Ministry (4 questions: 2 MC, 2 OE)
    # ===========================================
    {
        "category": "Paul's Conversion & Ministry",
        "text": "Before his conversion, Saul's persecution of the church involved:",
        "type": "multiple_choice",
        "options": [
            {"text": "Debating believers in synagogues and writing letters against them", "is_correct": False},
            {"text": "Entering homes to drag off men and women to prison, approving their deaths", "is_correct": True},
            {"text": "Reporting Christian activity to Roman authorities for prosecution", "is_correct": False},
            {"text": "Excommunicating Jewish believers from synagogue worship", "is_correct": False}
        ]
    },
    {
        "category": "Paul's Conversion & Ministry",
        "text": "On the road to Damascus, Jesus appeared to Saul and said:",
        "type": "multiple_choice",
        "options": [
            {"text": "You will be my apostle to the Gentiles and kings and the people of Israel", "is_correct": False},
            {"text": "Rise and go to Jerusalem where you will be told what to do", "is_correct": False},
            {"text": "Saul, Saul, why are you persecuting me?", "is_correct": True},
            {"text": "Your sins are forgiven; go and preach repentance to the nations", "is_correct": False}
        ]
    },
    {
        "category": "Paul's Conversion & Ministry",
        "text": "Paul's conversion shows that no one is beyond God's reach. He went from persecutor to apostle. How does Paul's story give you hope for people in your life who seem far from God?",
        "type": "open_ended",
        "options": []
    },
    {
        "category": "Paul's Conversion & Ministry",
        "text": "In Acts 20:24, Paul says, 'I consider my life worth nothing to me; my only aim is to finish the race and complete the task the Lord Jesus has given me.' What does this level of commitment look like, and how does it challenge you?",
        "type": "open_ended",
        "options": []
    },
    # ===========================================
    # CATEGORY: The Gospel Crossing Barriers (4 questions: 3 MC, 1 OE)
    # ===========================================
    {
        "category": "The Gospel Crossing Barriers",
        "text": "In Peter's vision in Acts 10, God declared all foods clean. What was the primary lesson?",
        "type": "multiple_choice",
        "options": [
            {"text": "That the old covenant dietary laws were now abolished for all believers", "is_correct": False},
            {"text": "That Jewish and Gentile believers should share meals together freely", "is_correct": False},
            {"text": "That God shows no favoritism and no person should be called impure or unclean", "is_correct": True},
            {"text": "That the gospel transforms cultural practices rather than eliminating them", "is_correct": False}
        ]
    },
    {
        "category": "The Gospel Crossing Barriers",
        "text": "Cornelius, the centurion in Acts 10, was described before his conversion as:",
        "type": "multiple_choice",
        "options": [
            {"text": "A God-fearing man who had already been baptized by John the Baptist", "is_correct": False},
            {"text": "A devout, God-fearing man who gave generously and prayed regularly", "is_correct": True},
            {"text": "A Roman officer who secretly believed Jesus was the Messiah", "is_correct": False},
            {"text": "A seeker who had studied the Hebrew Scriptures with Jewish teachers", "is_correct": False}
        ]
    },
    {
        "category": "The Gospel Crossing Barriers",
        "text": "The Jerusalem Council in Acts 15 concluded that Gentile believers:",
        "type": "multiple_choice",
        "options": [
            {"text": "Must be circumcised but are free from other requirements of the law", "is_correct": False},
            {"text": "Should follow Jewish customs when worshiping with Jewish believers", "is_correct": False},
            {"text": "Should not be burdened beyond abstaining from certain practices like food sacrificed to idols", "is_correct": True},
            {"text": "Are equal to Jewish believers and have no special requirements whatsoever", "is_correct": False}
        ]
    },
    {
        "category": "The Gospel Crossing Barriers",
        "text": "Acts shows the gospel breaking through cultural, ethnic, and social barriers. What barriers exist in your context that the gospel needs to cross? How can you be part of that work?",
        "type": "open_ended",
        "options": []
    },
    # ===========================================
    # CATEGORY: Missionary Journeys (4 questions: 2 MC, 2 OE)
    # ===========================================
    {
        "category": "Missionary Journeys",
        "text": "Paul and Barnabas separated before the second missionary journey because:",
        "type": "multiple_choice",
        "options": [
            {"text": "They disagreed over whether to preach to Jews or Gentiles first", "is_correct": False},
            {"text": "They had a sharp disagreement over whether to take John Mark with them", "is_correct": True},
            {"text": "Barnabas was called to lead the church in Antioch while Paul traveled", "is_correct": False},
            {"text": "Paul wanted to revisit churches while Barnabas wanted to plant new ones", "is_correct": False}
        ]
    },
    {
        "category": "Missionary Journeys",
        "text": "When Paul and Silas were imprisoned in Philippi, what happened after the earthquake?",
        "type": "multiple_choice",
        "options": [
            {"text": "They escaped and continued their journey to Thessalonica", "is_correct": False},
            {"text": "They remained and converted many prisoners before being released", "is_correct": False},
            {"text": "They stayed, and the jailer and his household believed and were baptized", "is_correct": True},
            {"text": "They were brought before the magistrates who apologized and released them", "is_correct": False}
        ]
    },
    {
        "category": "Missionary Journeys",
        "text": "In Acts 16:6-10, the Holy Spirit redirected Paul's travel plans, eventually leading him to Macedonia (Europe). Describe a time when God redirected your plans. How did you respond, and what was the result?",
        "type": "open_ended",
        "options": []
    },
    {
        "category": "Missionary Journeys",
        "text": "Paul's strategy included going to synagogues, marketplaces, and anywhere people gathered. How do you think about bringing the gospel to the places where you live, work, and spend time?",
        "type": "open_ended",
        "options": []
    },
    # ===========================================
    # CATEGORY: Faithfulness to the End (3 questions: 2 MC, 1 OE)
    # ===========================================
    {
        "category": "Faithfulness to the End",
        "text": "In Paul's farewell to the Ephesian elders (Acts 20), he warned them that:",
        "type": "multiple_choice",
        "options": [
            {"text": "Political persecution from Rome would intensify against the church", "is_correct": False},
            {"text": "Financial troubles would test the faithfulness of believers", "is_correct": False},
            {"text": "Savage wolves will arise from among your own number, distorting the truth", "is_correct": True},
            {"text": "Disagreements about worship styles would divide the congregation", "is_correct": False}
        ]
    },
    {
        "category": "Faithfulness to the End",
        "text": "The book of Acts ends with Paul in Rome:",
        "type": "multiple_choice",
        "options": [
            {"text": "Writing his final letters and preparing Timothy to continue his ministry", "is_correct": False},
            {"text": "Appearing before Caesar and being acquitted of all charges", "is_correct": False},
            {"text": "Under house arrest but freely preaching the kingdom of God to all visitors", "is_correct": True},
            {"text": "Planning a fourth missionary journey to Spain and the western regions", "is_correct": False}
        ]
    },
    {
        "category": "Faithfulness to the End",
        "text": "Acts doesn't have a neat ending - it closes with the gospel still spreading. How do you see yourself as part of the continuing story of God's mission in the world?",
        "type": "open_ended",
        "options": []
    },
]

def main():
    print("=" * 60)
    print("Acts Assessment Setup")
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
                print(f"✅ Created Acts Assessment template: {template_id}")
            
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
                question_code = f"ACTS_{question_order:03d}"
                
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
            print(f"✅ SUCCESS! Created Acts Assessment")
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
