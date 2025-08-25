"""
Script to populate the Master Trooth Assessment with all 57 questions from assessment_info.md
"""
import os
import sys
from pathlib import Path

# Add the app directory to Python path
sys.path.append(str(Path(__file__).parent))

from sqlalchemy import text
from app.db import engine, SessionLocal
from app.models import *
# Import helper to create master assessment if missing
from setup_master_assessment import create_master_trooth_assessment
import uuid

def populate_trooth_assessment_questions():
    """Populate the Master Trooth Assessment with all questions"""
    
    # Question data from assessment_info.md
    questions_data = [
        # Category 1: Spiritual Growth
        {
            "category": "Spiritual Growth",
            "text": "When the disciples asked Jesus to increase their faith (Luke 17), what did Jesus compare faith to?",
            "type": "multiple_choice",
            "options": [
                {"text": "A mighty river", "is_correct": False},
                {"text": "A mustard seed", "is_correct": True},
                {"text": "A towering mountain", "is_correct": False},
                {"text": "A burning flame", "is_correct": False}
            ]
        },
        {
            "category": "Spiritual Growth",
            "text": "Jacob's spiritual growth is demonstrated when he wrestles with God at Peniel. What was the lasting sign of this encounter?",
            "type": "multiple_choice",
            "options": [
                {"text": "He received a new name (Israel)", "is_correct": True},
                {"text": "He became a prophet", "is_correct": False},
                {"text": "He was given supernatural strength", "is_correct": False},
                {"text": "He lost his ability to walk", "is_correct": False}
            ]
        },
        {
            "category": "Spiritual Growth",
            "text": "Peter's transformation from impulsive fisherman to church leader is shown throughout the Gospels. What event particularly marked his spiritual growth after denying Jesus?",
            "type": "multiple_choice",
            "options": [
                {"text": "Walking on water", "is_correct": False},
                {"text": "His restoration by Jesus after the resurrection", "is_correct": True},
                {"text": "Healing the lame man at the gate", "is_correct": False},
                {"text": "Speaking in tongues at Pentecost", "is_correct": False}
            ]
        },
        {
            "category": "Spiritual Growth",
            "text": "The parable of the soils (Matthew 13) teaches about spiritual growth. Which soil represents a person who receives the word with joy but falls away during trials?",
            "type": "multiple_choice",
            "options": [
                {"text": "The path", "is_correct": False},
                {"text": "Rocky ground", "is_correct": True},
                {"text": "Among thorns", "is_correct": False},
                {"text": "Good soil", "is_correct": False}
            ]
        },
        {
            "category": "Spiritual Growth",
            "text": "Describe a specific time in the past year when you experienced significant spiritual growth. What circumstances led to this growth, and how did you recognize it was happening?",
            "type": "open_ended"
        },
        {
            "category": "Spiritual Growth",
            "text": "What are the biggest obstacles you currently face in your spiritual development? How are you working to overcome them?",
            "type": "open_ended"
        },
        {
            "category": "Spiritual Growth",
            "text": "How do you measure your own spiritual maturity? What indicators do you look for to know you're growing closer to Christ?",
            "type": "open_ended"
        },
        
        # Category 2: Prayer Life
        {
            "category": "Prayer Life",
            "text": "When Hannah desperately wanted a child, where did she go to pour out her heart in prayer?",
            "type": "multiple_choice",
            "options": [
                {"text": "Her home altar", "is_correct": False},
                {"text": "The temple at Shiloh", "is_correct": True},
                {"text": "The synagogue", "is_correct": False},
                {"text": "A mountaintop", "is_correct": False}
            ]
        },
        {
            "category": "Prayer Life",
            "text": "What did Jesus do when He wanted to spend time in prayer, especially before major decisions?",
            "type": "multiple_choice",
            "options": [
                {"text": "He prayed in the temple courts", "is_correct": False},
                {"text": "He gathered the disciples to pray with Him", "is_correct": False},
                {"text": "He went to a solitary place, often early in the morning", "is_correct": True},
                {"text": "He fasted for exactly 40 days", "is_correct": False}
            ]
        },
        {
            "category": "Prayer Life",
            "text": "When Daniel faced the decree forbidding prayer to anyone but the king, what did he do?",
            "type": "multiple_choice",
            "options": [
                {"text": "He stopped praying until the decree was lifted", "is_correct": False},
                {"text": "He prayed secretly where no one could see", "is_correct": False},
                {"text": "He continued his regular practice of praying three times daily", "is_correct": True},
                {"text": "He only prayed in his heart without moving his lips", "is_correct": False}
            ]
        },
        {
            "category": "Prayer Life",
            "text": "In the parable of the Pharisee and the tax collector, which prayer did Jesus commend?",
            "type": "multiple_choice",
            "options": [
                {"text": "The Pharisee's prayer listing his good deeds", "is_correct": False},
                {"text": "The tax collector's prayer asking for God's mercy", "is_correct": True},
                {"text": "Both prayers equally", "is_correct": False},
                {"text": "Neither prayer was acceptable", "is_correct": False}
            ]
        },
        {
            "category": "Prayer Life",
            "text": "Describe your current prayer routine. How often do you pray, and what does a typical prayer time look like for you?",
            "type": "open_ended"
        },
        {
            "category": "Prayer Life",
            "text": "What has been your most meaningful prayer experience? How did it impact your relationship with God?",
            "type": "open_ended"
        },
        {
            "category": "Prayer Life",
            "text": "What challenges do you face in maintaining a consistent prayer life? How do you handle seasons when prayer feels difficult or dry?",
            "type": "open_ended"
        },
        {
            "category": "Prayer Life",
            "text": "How do you balance praise, confession, thanksgiving, and requests in your prayers? Which area comes most naturally to you, and which is most challenging?",
            "type": "open_ended"
        },
        
        # Category 3: Bible Study
        {
            "category": "Bible Study",
            "text": "When Ezra returned from exile, what was he particularly devoted to doing that blessed the people?",
            "type": "multiple_choice",
            "options": [
                {"text": "Building the temple walls", "is_correct": False},
                {"text": "Studying and teaching the Law of the Lord", "is_correct": True},
                {"text": "Leading worship services", "is_correct": False},
                {"text": "Organizing the priesthood", "is_correct": False}
            ]
        },
        {
            "category": "Bible Study",
            "text": "What did the Ethiopian eunuch need when Philip found him reading Isaiah?",
            "type": "multiple_choice",
            "options": [
                {"text": "A better translation of the text", "is_correct": False},
                {"text": "Someone to explain what he was reading", "is_correct": True},
                {"text": "A quieter place to study", "is_correct": False},
                {"text": "More scrolls to read", "is_correct": False}
            ]
        },
        {
            "category": "Bible Study",
            "text": "When the boy Samuel first heard God's voice, who helped him understand how to respond?",
            "type": "multiple_choice",
            "options": [
                {"text": "His mother Hannah", "is_correct": False},
                {"text": "The other temple workers", "is_correct": False},
                {"text": "Eli the priest", "is_correct": True},
                {"text": "He figured it out on his own", "is_correct": False}
            ]
        },
        {
            "category": "Bible Study",
            "text": "King Josiah found the Book of the Law in the temple and it had a powerful impact. What was his immediate response?",
            "type": "multiple_choice",
            "options": [
                {"text": "He celebrated with a great feast", "is_correct": False},
                {"text": "He tore his clothes in repentance", "is_correct": True},
                {"text": "He built a monument to commemorate it", "is_correct": False},
                {"text": "He immediately called for a census", "is_correct": False}
            ]
        },
        {
            "category": "Bible Study",
            "text": "When Jesus was tempted by Satan in the wilderness, how did He respond to each temptation?",
            "type": "multiple_choice",
            "options": [
                {"text": "He ignored Satan completely", "is_correct": False},
                {"text": "He used His divine power to resist", "is_correct": False},
                {"text": "He quoted Scripture to counter each temptation", "is_correct": True},
                {"text": "He called upon angels to help Him", "is_correct": False}
            ]
        },
        {
            "category": "Bible Study",
            "text": "How often do you currently read the Bible, and what method do you use (devotional plan, topical study, verse-by-verse, etc.)?",
            "type": "open_ended"
        },
        {
            "category": "Bible Study",
            "text": "What book or passage of Scripture has had the greatest impact on your life? Explain why and how it changed you.",
            "type": "open_ended"
        },
        {
            "category": "Bible Study",
            "text": "Describe your approach to studying difficult or confusing passages in Scripture. What resources do you use?",
            "type": "open_ended"
        },
        {
            "category": "Bible Study",
            "text": "How do you apply what you learn from Bible study to your daily life? Give a specific recent example.",
            "type": "open_ended"
        },
        
        # Category 4: Community & Fellowship
        {
            "category": "Community & Fellowship",
            "text": "When the early church in Acts faced persecution, what did they do to strengthen their fellowship?",
            "type": "multiple_choice",
            "options": [
                {"text": "They met in larger, more public gatherings", "is_correct": False},
                {"text": "They continued meeting in homes and sharing meals together", "is_correct": True},
                {"text": "They dispersed to avoid detection", "is_correct": False},
                {"text": "They appointed more formal leadership", "is_correct": False}
            ]
        },
        {
            "category": "Community & Fellowship",
            "text": "What characterized the friendship between David and Jonathan that made their bond so strong?",
            "type": "multiple_choice",
            "options": [
                {"text": "They were both from wealthy families", "is_correct": False},
                {"text": "Their souls were knit together in covenant friendship", "is_correct": True},
                {"text": "They shared the same political views", "is_correct": False},
                {"text": "They were both skilled warriors", "is_correct": False}
            ]
        },
        {
            "category": "Community & Fellowship",
            "text": "When the disciples argued about who was the greatest, what did Jesus do to teach them about true community?",
            "type": "multiple_choice",
            "options": [
                {"text": "He chose the most qualified leader", "is_correct": False},
                {"text": "He washed their feet and served them", "is_correct": True},
                {"text": "He gave them a written set of rules", "is_correct": False},
                {"text": "He told them to vote on their leader", "is_correct": False}
            ]
        },
        {
            "category": "Community & Fellowship",
            "text": "Ruth's commitment to Naomi demonstrates godly fellowship. What did Ruth say that shows her dedication to community?",
            "type": "multiple_choice",
            "options": [
                {"text": "\"Your people will be my people and your God my God\"", "is_correct": True},
                {"text": "\"I will serve you as long as it's convenient\"", "is_correct": False},
                {"text": "\"I will help you until you find other family\"", "is_correct": False},
                {"text": "\"Let's stay together until we reach Bethlehem\"", "is_correct": False}
            ]
        },
        {
            "category": "Community & Fellowship",
            "text": "Describe your current level of involvement in Christian community. What specific groups, ministries, or relationships provide fellowship in your life?",
            "type": "open_ended"
        },
        {
            "category": "Community & Fellowship",
            "text": "How comfortable are you with being vulnerable and sharing your struggles with other believers? What helps or hinders this openness?",
            "type": "open_ended"
        },
        {
            "category": "Community & Fellowship",
            "text": "Give an example of how you've recently encouraged or been encouraged by another believer. How did this impact your faith?",
            "type": "open_ended"
        },
        {
            "category": "Community & Fellowship",
            "text": "What role do you typically play in group settings (leader, encourager, listener, etc.)? How might God be calling you to grow in this area?",
            "type": "open_ended"
        },
        
        # Category 5: Service & Ministry
        {
            "category": "Service & Ministry",
            "text": "When Moses felt overwhelmed leading the Israelites, what solution did his father-in-law Jethro suggest?",
            "type": "multiple_choice",
            "options": [
                {"text": "Moses should pray more and trust God completely", "is_correct": False},
                {"text": "Moses should delegate responsibilities to capable men", "is_correct": True},
                {"text": "The people should solve their own problems", "is_correct": False},
                {"text": "Moses should appoint his sons as co-leaders", "is_correct": False}
            ]
        },
        {
            "category": "Service & Ministry",
            "text": "What motivated the widow to give her last two coins at the temple?",
            "type": "multiple_choice",
            "options": [
                {"text": "She expected God to make her wealthy", "is_correct": False},
                {"text": "She gave out of her heart's devotion despite her poverty", "is_correct": True},
                {"text": "She was required by law to give", "is_correct": False},
                {"text": "She wanted to impress the religious leaders", "is_correct": False}
            ]
        },
        {
            "category": "Service & Ministry",
            "text": "When Nehemiah saw the broken walls of Jerusalem, what was his response?",
            "type": "multiple_choice",
            "options": [
                {"text": "He complained about the problem to others", "is_correct": False},
                {"text": "He left the problem for someone else to solve", "is_correct": False},
                {"text": "He wept, prayed, and then took action to rebuild", "is_correct": True},
                {"text": "He decided the walls weren't really necessary", "is_correct": False}
            ]
        },
        {
            "category": "Service & Ministry",
            "text": "Dorcas (Tabitha) was known throughout her community for her service. What was she particularly remembered for?",
            "type": "multiple_choice",
            "options": [
                {"text": "Her powerful preaching", "is_correct": False},
                {"text": "Her acts of charity and making clothes for the needy", "is_correct": True},
                {"text": "Her large financial donations", "is_correct": False},
                {"text": "Her miraculous healing abilities", "is_correct": False}
            ]
        },
        {
            "category": "Service & Ministry",
            "text": "What spiritual gifts do you believe God has given you? How are you currently using these gifts to serve others?",
            "type": "open_ended"
        },
        {
            "category": "Service & Ministry",
            "text": "Describe your current involvement in ministry or service (within the church or in the community). What motivates you to serve?",
            "type": "open_ended"
        },
        {
            "category": "Service & Ministry",
            "text": "What barriers or fears have you faced when it comes to serving others? How have you worked to overcome them?",
            "type": "open_ended"
        },
        {
            "category": "Service & Ministry",
            "text": "Tell about a time when serving others significantly impacted your own spiritual growth. What did you learn from that experience?",
            "type": "open_ended"
        },
        
        # Category 6: Discipleship
        {
            "category": "Discipleship",
            "text": "When Jesus called His first disciples by the Sea of Galilee, what was their immediate response?",
            "type": "multiple_choice",
            "options": [
                {"text": "They asked for time to consider His invitation", "is_correct": False},
                {"text": "They left their nets and followed Him immediately", "is_correct": True},
                {"text": "They demanded to know more about His plans first", "is_correct": False},
                {"text": "They said they would follow Him after the fishing season", "is_correct": False}
            ]
        },
        {
            "category": "Discipleship",
            "text": "What did Jesus mean when He told the rich young ruler to \"come, follow me\" after selling his possessions?",
            "type": "multiple_choice",
            "options": [
                {"text": "Following Jesus requires complete surrender and sacrifice", "is_correct": True},
                {"text": "Only poor people can be His disciples", "is_correct": False},
                {"text": "Money is the root of all evil", "is_correct": False},
                {"text": "Everyone must sell everything to follow Jesus", "is_correct": False}
            ]
        },
        {
            "category": "Discipleship",
            "text": "When Paul discipled Timothy, what kind of relationship did they develop?",
            "type": "multiple_choice",
            "options": [
                {"text": "A formal teacher-student arrangement", "is_correct": False},
                {"text": "A father-son relationship in the faith", "is_correct": True},
                {"text": "A business partnership for ministry", "is_correct": False},
                {"text": "A casual friendship with occasional meetings", "is_correct": False}
            ]
        },
        {
            "category": "Discipleship",
            "text": "Barnabas demonstrated godly discipleship when he took a chance on which controversial new convert?",
            "type": "multiple_choice",
            "options": [
                {"text": "Timothy", "is_correct": False},
                {"text": "Titus", "is_correct": False},
                {"text": "Saul (later Paul)", "is_correct": True},
                {"text": "John Mark", "is_correct": False}
            ]
        },
        {
            "category": "Discipleship",
            "text": "Who has been most influential in discipling you in your faith? What specific things did they do that helped you grow?",
            "type": "open_ended"
        },
        {
            "category": "Discipleship",
            "text": "Are you currently discipling or mentoring anyone in their faith journey? If yes, describe that relationship. If no, what keeps you from taking this step?",
            "type": "open_ended"
        },
        {
            "category": "Discipleship",
            "text": "How do you share your faith with non-believers? What opportunities do you regularly have for evangelism?",
            "type": "open_ended"
        },
        {
            "category": "Discipleship",
            "text": "What does it mean to you personally to \"take up your cross daily\" and follow Jesus? Give specific examples from your life.",
            "type": "open_ended"
        },
        
        # Category 7: Faith Practice
        {
            "category": "Faith Practice",
            "text": "When Daniel was commanded to worship the king's statue, how did he demonstrate his faith practice?",
            "type": "multiple_choice",
            "options": [
                {"text": "He worshiped the statue publicly but prayed to God privately", "is_correct": False},
                {"text": "He refused to compromise his faith even facing the lion's den", "is_correct": True},
                {"text": "He found a way to honor both the king and God", "is_correct": False},
                {"text": "He temporarily stopped his religious practices to avoid conflict", "is_correct": False}
            ]
        },
        {
            "category": "Faith Practice",
            "text": "How did Joseph maintain his faith practice while serving in Potiphar's house and later in prison?",
            "type": "multiple_choice",
            "options": [
                {"text": "He kept his faith completely secret", "is_correct": False},
                {"text": "He lived with integrity and gave God credit for his success", "is_correct": True},
                {"text": "He only practiced his faith on the Sabbath", "is_correct": False},
                {"text": "He gradually adopted Egyptian religious practices", "is_correct": False}
            ]
        },
        {
            "category": "Faith Practice",
            "text": "When Shadrach, Meshach, and Abednego were thrown into the fiery furnace for their faith, what happened?",
            "type": "multiple_choice",
            "options": [
                {"text": "They were consumed by the flames as an example to others", "is_correct": False},
                {"text": "God delivered them without even the smell of smoke on their clothes", "is_correct": True},
                {"text": "They survived but were badly burned", "is_correct": False},
                {"text": "They escaped from the furnace when no one was looking", "is_correct": False}
            ]
        },
        {
            "category": "Faith Practice",
            "text": "How did Jesus demonstrate authentic faith practice during His earthly ministry?",
            "type": "multiple_choice",
            "options": [
                {"text": "He only associated with religious leaders", "is_correct": False},
                {"text": "He perfectly balanced teaching, prayer, service, and compassion for all people", "is_correct": True},
                {"text": "He focused exclusively on preaching in synagogues", "is_correct": False},
                {"text": "He avoided contact with sinners to maintain His purity", "is_correct": False}
            ]
        },
        {
            "category": "Faith Practice",
            "text": "How has your faith influenced your daily decisions and lifestyle choices in the past month? Give specific examples.",
            "type": "open_ended"
        },
        {
            "category": "Faith Practice",
            "text": "What spiritual disciplines (fasting, solitude, meditation, etc.) do you practice regularly? How have these impacted your relationship with God?",
            "type": "open_ended"
        },
        {
            "category": "Faith Practice",
            "text": "Describe how you handle conflict or difficult situations differently now than you did before becoming a Christian.",
            "type": "open_ended"
        },
        {
            "category": "Faith Practice",
            "text": "In what ways are you currently living out your faith in your workplace, family, or community? What opportunities do you see for growth in this area?",
            "type": "open_ended"
        },
        {
            "category": "Faith Practice",
            "text": "How do you maintain your Christian witness and values when faced with cultural pressures or opposition to your faith?",
            "type": "open_ended"
        }
    ]
    
    # Connect to database
    with engine.begin() as conn:
        # Get the master assessment ID
        result = conn.execute(text("""
            SELECT id FROM assessment_templates 
            WHERE is_master_assessment = TRUE
        """))
        assessment = result.fetchone()
        
        if not assessment:
            # Master assessment missing — create it idempotently
            print("🔄 Master Trooth Assessment not found, creating...")
            master_assessment_id = create_master_trooth_assessment()
        else:
            master_assessment_id = assessment[0]

        print(f"📋 Using Master Assessment: {master_assessment_id}")
        
        # Get category mappings
        categories = {}
        result = conn.execute(text("SELECT id, name FROM categories"))
        for row in result:
            categories[row[1]] = row[0]
        
        print(f"📁 Found {len(categories)} categories: {list(categories.keys())}")

        # Ensure all categories referenced by questions_data exist (idempotent)
        required_categories = {q["category"] for q in questions_data}
        missing_categories = required_categories - set(categories.keys())
        if missing_categories:
            print(f"🔍 Missing categories detected: {missing_categories}. Creating...")
            for cat in missing_categories:
                # Double-check if category exists (race-safe)
                existing = conn.execute(text("SELECT id FROM categories WHERE name = :name"), {"name": cat}).fetchone()
                if existing:
                    categories[cat] = existing[0]
                    continue
                cat_id = str(uuid.uuid4())
                conn.execute(text("INSERT INTO categories (id, name) VALUES (:id, :name)"), {"id": cat_id, "name": cat})
                categories[cat] = cat_id
                print(f"➕ Created missing category: {cat}")
        else:
            print("✅ All required categories present.")
        
        # Check if questions already exist
        result = conn.execute(text("""
            SELECT COUNT(*) FROM assessment_template_questions 
            WHERE template_id = :template_id
        """), {"template_id": master_assessment_id})
        
        existing_count = result.scalar()
        if existing_count > 0:
            print(f"⚠️  Assessment already has {existing_count} questions. Skipping population.")
            return
        
        # Insert all questions
        question_order = 1
        
        for q_data in questions_data:
            # Create the question
            question_id = str(uuid.uuid4())
            question_type = "multiple_choice" if q_data["type"] == "multiple_choice" else "open_ended"
            category_id = categories.get(q_data["category"])
            
            if not category_id:
                print(f"❌ Category '{q_data['category']}' not found!")
                continue
            
            # Insert question
            conn.execute(text("""
                INSERT INTO questions (id, text, question_type, category_id)
                VALUES (:id, :text, :question_type, :category_id)
            """), {
                "id": question_id,
                "text": q_data["text"],
                "question_type": question_type,
                "category_id": category_id
            })
            
            # Insert options for multiple choice questions
            if q_data["type"] == "multiple_choice" and "options" in q_data:
                for i, option in enumerate(q_data["options"]):
                    option_id = str(uuid.uuid4())
                    conn.execute(text("""
                        INSERT INTO question_options (id, question_id, option_text, is_correct, "order")
                        VALUES (:id, :question_id, :option_text, :is_correct, :order)
                    """), {
                        "id": option_id,
                        "question_id": question_id,
                        "option_text": option["text"],
                        "is_correct": option["is_correct"],
                        "order": i + 1
                    })
            
            # Link question to assessment template
            template_question_id = str(uuid.uuid4())
            conn.execute(text("""
                INSERT INTO assessment_template_questions (id, template_id, question_id, "order")
                VALUES (:id, :template_id, :question_id, :order)
            """), {
                "id": template_question_id,
                "template_id": master_assessment_id,
                "question_id": question_id,
                "order": question_order
            })
            
            print(f"✅ Added question {question_order}: {q_data['text'][:60]}...")
            question_order += 1
        
        print(f"🎉 Successfully populated Master Trooth Assessment with {len(questions_data)} questions!")

if __name__ == "__main__":
    populate_trooth_assessment_questions()
