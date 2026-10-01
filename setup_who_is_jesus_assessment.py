"""
Script to create the "Who is Jesus?" Assessment
Run as: python setup_who_is_jesus_assessment.py
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
ASSESSMENT_KEY = "who_is_jesus_v1"
ASSESSMENT_NAME = "Who is Jesus?"
ASSESSMENT_DESCRIPTION = """Explore who Jesus truly is — His identity, His miracles, His teachings, His sacrificial death and resurrection, His role as Savior and Redeemer, and what it means to follow Him today. This assessment covers both knowledge of what Jesus has done and understanding of how His words apply to your life. 40 questions (25 multiple choice, 15 open-ended) across 6 categories."""

# Questions organized by category
# NOTE: Correct answers are distributed across positions A, B, C, D
QUESTIONS_DATA = [
    # ===========================================
    # CATEGORY: The Identity of Jesus (7 questions: 5 MC, 2 OE)
    # ===========================================
    {
        "category": "The Identity of Jesus",
        "text": "According to John 1:1-3, what is true about the 'Word'?",
        "type": "multiple_choice",
        "options": [
            {"text": "The Word was with God and was sent by God to reveal His will to humanity", "is_correct": False},
            {"text": "The Word was the first of God's creation, through whom everything else was made", "is_correct": False},
            {"text": "The Word was with God, was God, and through Him all things were made", "is_correct": True},  # C - CORRECT
            {"text": "The Word was God's spoken promise that became flesh to establish a new covenant", "is_correct": False}
        ]
    },
    {
        "category": "The Identity of Jesus",
        "text": "In Matthew 16:15-16, when Jesus asked 'Who do you say I am?', Peter answered:",
        "type": "multiple_choice",
        "options": [
            {"text": "You are the Lamb of God who takes away the sin of the world", "is_correct": False},
            {"text": "You are the Christ, the Son of the living God", "is_correct": True},  # B - CORRECT
            {"text": "You are the Prophet Moses told us would come", "is_correct": False},
            {"text": "You are the Son of Man spoken of by Daniel", "is_correct": False}
        ]
    },
    {
        "category": "The Identity of Jesus",
        "text": "In John 20:28, after seeing the risen Jesus, what did Thomas declare?",
        "type": "multiple_choice",
        "options": [
            {"text": "Now I believe that you are the Prophet who was to come into the world", "is_correct": False},
            {"text": "My Lord and my God!", "is_correct": True},  # B - CORRECT
            {"text": "You are truly the Son of God, just as you said", "is_correct": False},
            {"text": "Lord, I am not worthy to be in your presence", "is_correct": False}
        ]
    },
    {
        "category": "The Identity of Jesus",
        "text": "In John 8:58, when Jesus said 'Before Abraham was born, I am,' why did the crowd react with hostility?",
        "type": "multiple_choice",
        "options": [
            {"text": "They believed He was dishonoring Abraham by claiming to be older than their patriarch", "is_correct": False},
            {"text": "They thought He was speaking blasphemy by using a divine title reserved for angels", "is_correct": False},
            {"text": "He used God's covenant name for Himself, and they understood He was claiming to be God", "is_correct": True},  # C - CORRECT
            {"text": "They were offended that a Galilean carpenter would claim to have existed before Abraham", "is_correct": False}
        ]
    },
    {
        "category": "The Identity of Jesus",
        "text": "According to Philippians 2:6-8, what did Jesus do despite being in very nature God?",
        "type": "multiple_choice",
        "options": [
            {"text": "He veiled His glory but retained His divine authority throughout His earthly ministry", "is_correct": False},
            {"text": "He emptied Himself of His heavenly position and took on human limitations, though He remained fully God", "is_correct": False},
            {"text": "He made Himself nothing, taking the very nature of a servant, being made in human likeness, and humbled Himself by becoming obedient to death", "is_correct": True},  # C - CORRECT
            {"text": "He set aside His divine privileges and lived among us to show the Father's character and will", "is_correct": False}
        ]
    },
    {
        "category": "The Identity of Jesus",
        "text": "Jesus is called by many names and titles in Scripture — Immanuel, Prince of Peace, Lamb of God, the Good Shepherd. Which name or title of Jesus speaks most deeply to you right now, and why?",
        "type": "open_ended",
        "options": []
    },
    {
        "category": "The Identity of Jesus",
        "text": "In John 14:9, Jesus told Philip, 'Anyone who has seen me has seen the Father.' What does it mean to you personally that Jesus is the visible image of the invisible God? How does that shape the way you think about God?",
        "type": "open_ended",
        "options": []
    },
    # ===========================================
    # CATEGORY: The Miracles of Jesus (6 questions: 4 MC, 2 OE)
    # ===========================================
    {
        "category": "The Miracles of Jesus",
        "text": "What was the first miracle Jesus performed, as recorded in John 2:1-11?",
        "type": "multiple_choice",
        "options": [
            {"text": "Healing a nobleman's son who was sick in Capernaum", "is_correct": False},
            {"text": "Turning water into wine at the wedding in Cana", "is_correct": True},  # B - CORRECT
            {"text": "Casting out an unclean spirit in the synagogue at Capernaum", "is_correct": False},
            {"text": "Calling the first disciples and giving them power to heal", "is_correct": False}
        ]
    },
    {
        "category": "The Miracles of Jesus",
        "text": "In Mark 4:35-41, after Jesus calmed the storm, what was the disciples' response?",
        "type": "multiple_choice",
        "options": [
            {"text": "They worshiped Him and said, 'Truly you are the Son of God'", "is_correct": False},
            {"text": "They were amazed and said, 'He even commands unclean spirits and they obey'", "is_correct": False},
            {"text": "They fell at His feet and said, 'Depart from us, Lord, for we are sinful men'", "is_correct": False},
            {"text": "They were terrified and asked each other, 'Who is this? Even the wind and the waves obey him!'", "is_correct": True}  # D - CORRECT
        ]
    },
    {
        "category": "The Miracles of Jesus",
        "text": "In John 11, what did Jesus say to Martha before raising Lazarus from the dead?",
        "type": "multiple_choice",
        "options": [
            {"text": "Did I not tell you that if you believe, you will see the glory of God?", "is_correct": False},
            {"text": "I am the resurrection and the life. The one who believes in me will live, even though they die", "is_correct": True},  # B - CORRECT
            {"text": "Your brother will rise again in the resurrection at the last day", "is_correct": False},
            {"text": "If you had faith as small as a mustard seed, nothing would be impossible for you", "is_correct": False}
        ]
    },
    {
        "category": "The Miracles of Jesus",
        "text": "In Matthew 14:28-31, when Peter walked on the water and began to sink, what did Jesus say to him?",
        "type": "multiple_choice",
        "options": [
            {"text": "Do not be afraid; it is I", "is_correct": False},
            {"text": "Why were you afraid? Did I not call you to come?", "is_correct": False},
            {"text": "Peace, be still — your faith has saved you", "is_correct": False},
            {"text": "You of little faith, why did you doubt?", "is_correct": True}  # D - CORRECT
        ]
    },
    {
        "category": "The Miracles of Jesus",
        "text": "The miracles of Jesus were not just displays of power — they were signs pointing to who He is. Which miracle of Jesus stands out most to you, and what does it reveal about His character or authority?",
        "type": "open_ended",
        "options": []
    },
    {
        "category": "The Miracles of Jesus",
        "text": "In Mark 5:25-34, the woman with the bleeding issue pressed through the crowd just to touch Jesus' garment. Is there an area of your life where you need to press through obstacles to reach Jesus? What is holding you back?",
        "type": "open_ended",
        "options": []
    },
    # ===========================================
    # CATEGORY: The Teachings of Jesus (7 questions: 4 MC, 3 OE)
    # ===========================================
    {
        "category": "The Teachings of Jesus",
        "text": "In John 14:6, Jesus said, 'I am the way, the truth, and the life.' What did He say next?",
        "type": "multiple_choice",
        "options": [
            {"text": "Whoever follows me will not walk in darkness but will have the light of life", "is_correct": False},
            {"text": "No one comes to the Father except through me", "is_correct": True},  # B - CORRECT
            {"text": "If you love me, keep my commandments", "is_correct": False},
            {"text": "And the truth shall set you free", "is_correct": False}
        ]
    },
    {
        "category": "The Teachings of Jesus",
        "text": "In the Sermon on the Mount (Matthew 5:44), what specifically did Jesus say about how to treat enemies?",
        "type": "multiple_choice",
        "options": [
            {"text": "Do not resist an evil person; if anyone slaps you on the right cheek, turn the other also", "is_correct": False},
            {"text": "Forgive and you will be forgiven; give and it will be given to you", "is_correct": False},
            {"text": "Love your enemies and pray for those who persecute you", "is_correct": True},  # C - CORRECT
            {"text": "Overcome evil with good, and repay no one evil for evil", "is_correct": False}
        ]
    },
    {
        "category": "The Teachings of Jesus",
        "text": "According to Matthew 6:33, what did Jesus say we should seek first?",
        "type": "multiple_choice",
        "options": [
            {"text": "Wisdom from above, which is pure, peaceable, and full of mercy", "is_correct": False},
            {"text": "The peace of God that surpasses all understanding", "is_correct": False},
            {"text": "The kingdom of God and His righteousness, and all these things will be added to you", "is_correct": True},  # C - CORRECT
            {"text": "Treasure in heaven, where moth and rust do not destroy", "is_correct": False}
        ]
    },
    {
        "category": "The Teachings of Jesus",
        "text": "In the Parable of the Sower (Matthew 13), what happens to the seed that falls among thorns?",
        "type": "multiple_choice",
        "options": [
            {"text": "It springs up quickly but withers because it has no root", "is_correct": False},
            {"text": "The birds come and eat it before it can take root", "is_correct": False},
            {"text": "The worries of life and the deceitfulness of wealth choke it, making it unfruitful", "is_correct": True},  # C - CORRECT
            {"text": "It produces a crop — thirty, sixty, or a hundred times what was sown", "is_correct": False}
        ]
    },
    {
        "category": "The Teachings of Jesus",
        "text": "In Matthew 7:24-27, Jesus compared those who hear and obey His words to a wise man who built his house on the rock. In what area of your life are you actively building on the rock of Jesus' teaching? Where might you be building on sand?",
        "type": "open_ended",
        "options": []
    },
    {
        "category": "The Teachings of Jesus",
        "text": "Jesus said 'Blessed are the poor in spirit, for theirs is the kingdom of heaven' (Matthew 5:3). What does it mean to be 'poor in spirit,' and how does that challenge the way the world measures success and strength?",
        "type": "open_ended",
        "options": []
    },
    {
        "category": "The Teachings of Jesus",
        "text": "In John 13:34-35, Jesus gave a 'new commandment' to love one another as He loved us, saying this is how the world would know we are His disciples. How are you practically demonstrating this kind of love in your relationships right now?",
        "type": "open_ended",
        "options": []
    },
    # ===========================================
    # CATEGORY: The Death & Resurrection (6 questions: 4 MC, 2 OE)
    # ===========================================
    {
        "category": "The Death & Resurrection",
        "text": "According to Isaiah 53:5, why was the Messiah pierced and crushed?",
        "type": "multiple_choice",
        "options": [
            {"text": "He bore the punishment that Israel's enemies deserved as an act of divine justice", "is_correct": False},
            {"text": "He was pierced for our transgressions and crushed for our iniquities; by His wounds we are healed", "is_correct": True},  # B - CORRECT
            {"text": "He suffered so that we would understand the seriousness of sin and turn back to God", "is_correct": False},
            {"text": "He was afflicted to fulfill the covenant God made with Abraham and his descendants", "is_correct": False}
        ]
    },
    {
        "category": "The Death & Resurrection",
        "text": "What were Jesus' final words on the cross, as recorded in John 19:30?",
        "type": "multiple_choice",
        "options": [
            {"text": "Father, into your hands I commit my spirit", "is_correct": False},
            {"text": "My God, my God, why have you forsaken me?", "is_correct": False},
            {"text": "Father, forgive them, for they do not know what they are doing", "is_correct": False},
            {"text": "It is finished", "is_correct": True}  # D - CORRECT
        ]
    },
    {
        "category": "The Death & Resurrection",
        "text": "According to Romans 4:25, why was Jesus delivered over to death and raised to life?",
        "type": "multiple_choice",
        "options": [
            {"text": "To prove that He was truly the Son of God and had power over death", "is_correct": False},
            {"text": "To send the Holy Spirit and empower the church for mission", "is_correct": False},
            {"text": "To fulfill the promise God made to David that his throne would endure forever", "is_correct": False},
            {"text": "He was delivered over to death for our sins and was raised to life for our justification", "is_correct": True}  # D - CORRECT
        ]
    },
    {
        "category": "The Death & Resurrection",
        "text": "In Luke 24:36-43, how did the risen Jesus prove to the frightened disciples that He was physically alive and not a ghost?",
        "type": "multiple_choice",
        "options": [
            {"text": "He performed a miracle by making bread appear for them to share", "is_correct": False},
            {"text": "He called them by name and reminded them of conversations only He would know", "is_correct": False},
            {"text": "He showed them His hands and feet and ate a piece of broiled fish in their presence", "is_correct": True},  # C - CORRECT
            {"text": "He opened the Scriptures and explained how everything written about Him had been fulfilled", "is_correct": False}
        ]
    },
    {
        "category": "The Death & Resurrection",
        "text": "In Luke 23:34, Jesus prayed from the cross, 'Father, forgive them, for they do not know what they are doing.' How does Jesus' willingness to forgive even while suffering challenge the way you handle being wronged or hurt by others?",
        "type": "open_ended",
        "options": []
    },
    {
        "category": "The Death & Resurrection",
        "text": "The resurrection is the foundation of the Christian faith (1 Corinthians 15:17). How does believing that Jesus truly rose from the dead change the way you face fear, grief, or hopeless situations in your own life?",
        "type": "open_ended",
        "options": []
    },
    # ===========================================
    # CATEGORY: Jesus as Savior & Redeemer (7 questions: 4 MC, 3 OE)
    # ===========================================
    {
        "category": "Jesus as Savior & Redeemer",
        "text": "According to John 3:16-17, what was God's purpose in sending His Son into the world?",
        "type": "multiple_choice",
        "options": [
            {"text": "To reveal the truth and call all nations to repentance and obedience", "is_correct": False},
            {"text": "Not to condemn the world, but that the world through Him might be saved", "is_correct": True},  # B - CORRECT
            {"text": "To defeat the powers of darkness and establish His eternal kingdom on earth", "is_correct": False},
            {"text": "To fulfill every promise made to Abraham, Moses, and the prophets", "is_correct": False}
        ]
    },
    {
        "category": "Jesus as Savior & Redeemer",
        "text": "In Romans 5:8, what makes God's love for us remarkable?",
        "type": "multiple_choice",
        "options": [
            {"text": "He loved us before we existed or could do anything to earn it", "is_correct": False},
            {"text": "He continued to pursue us even when we repeatedly turned away from Him", "is_correct": False},
            {"text": "While we were still sinners — not after we repented — Christ died for us", "is_correct": True},  # C - CORRECT
            {"text": "He loved the whole world without partiality, offering salvation to every nation", "is_correct": False}
        ]
    },
    {
        "category": "Jesus as Savior & Redeemer",
        "text": "According to Ephesians 2:8-9, what is specifically said about how we are saved?",
        "type": "multiple_choice",
        "options": [
            {"text": "We are saved by grace through faith, and this is not from ourselves — it is the gift of God, not by works", "is_correct": True},  # A - CORRECT
            {"text": "We are saved by faith that expresses itself through love and obedience to God", "is_correct": False},
            {"text": "We are saved by confessing with our mouth and believing in our heart that God raised Jesus from the dead", "is_correct": False},
            {"text": "We are saved by the washing of rebirth and renewal by the Holy Spirit poured out on us", "is_correct": False}
        ]
    },
    {
        "category": "Jesus as Savior & Redeemer",
        "text": "According to Acts 4:12, what did Peter declare about salvation through Jesus?",
        "type": "multiple_choice",
        "options": [
            {"text": "Everyone who calls on the name of the Lord will be saved", "is_correct": False},
            {"text": "Salvation is found in no one else, for there is no other name under heaven given to mankind by which we must be saved", "is_correct": True},  # B - CORRECT
            {"text": "God exalted Him to His own right hand as Prince and Savior to bring repentance and forgiveness of sins", "is_correct": False},
            {"text": "Through Him everyone who believes is set free from every sin from which the law of Moses could not set you free", "is_correct": False}
        ]
    },
    {
        "category": "Jesus as Savior & Redeemer",
        "text": "Romans 6:23 says 'the wages of sin is death, but the gift of God is eternal life in Christ Jesus our Lord.' In your own words, what does it mean that salvation is a gift and not a wage? How does that affect the way you relate to God?",
        "type": "open_ended",
        "options": []
    },
    {
        "category": "Jesus as Savior & Redeemer",
        "text": "In 2 Corinthians 5:17, Paul writes, 'If anyone is in Christ, the new creation has come: The old has gone, the new is here!' In what specific ways have you experienced (or do you long to experience) being made new in Christ?",
        "type": "open_ended",
        "options": []
    },
    {
        "category": "Jesus as Savior & Redeemer",
        "text": "Jesus said in John 10:10, 'I have come that they may have life, and have it to the full.' What does 'life to the full' look like for you? How is that different from what the world promises?",
        "type": "open_ended",
        "options": []
    },
    # ===========================================
    # CATEGORY: Following Jesus Today (7 questions: 4 MC, 3 OE)
    # ===========================================
    {
        "category": "Following Jesus Today",
        "text": "In Luke 9:23, what did Jesus say is required to follow Him?",
        "type": "multiple_choice",
        "options": [
            {"text": "Believe in me, be baptized, and you will be saved — you and your household", "is_correct": False},
            {"text": "Deny yourself, take up your cross daily, and follow me", "is_correct": True},  # B - CORRECT
            {"text": "Leave everything behind and come, follow me", "is_correct": False},
            {"text": "Love the Lord your God with all your heart, soul, mind, and strength", "is_correct": False}
        ]
    },
    {
        "category": "Following Jesus Today",
        "text": "In John 15:4-5, what did Jesus say about the relationship between Himself and His followers?",
        "type": "multiple_choice",
        "options": [
            {"text": "Where two or three gather in my name, there I am with them", "is_correct": False},
            {"text": "If you love me, keep my commands, and I will ask the Father to give you the Holy Spirit", "is_correct": False},
            {"text": "I am the vine, you are the branches — whoever abides in me bears much fruit, for apart from me you can do nothing", "is_correct": True},  # C - CORRECT
            {"text": "I will never leave you nor forsake you; I am with you always to the end of the age", "is_correct": False}
        ]
    },
    {
        "category": "Following Jesus Today",
        "text": "In Matthew 28:19-20, what specifically did Jesus commission His disciples to do?",
        "type": "multiple_choice",
        "options": [
            {"text": "Be my witnesses in Jerusalem, Judea, Samaria, and to the ends of the earth", "is_correct": False},
            {"text": "Preach the gospel to all creation; whoever believes and is baptized will be saved", "is_correct": False},
            {"text": "Feed my sheep, tend my lambs, and take care of my flock", "is_correct": False},
            {"text": "Go and make disciples of all nations, baptizing them and teaching them to obey everything I have commanded you", "is_correct": True}  # D - CORRECT
        ]
    },
    {
        "category": "Following Jesus Today",
        "text": "In Galatians 2:20, how did Paul describe his new life in Christ?",
        "type": "multiple_choice",
        "options": [
            {"text": "For me to live is Christ, and to die is gain", "is_correct": False},
            {"text": "I have been crucified with Christ and I no longer live, but Christ lives in me", "is_correct": True},  # B - CORRECT
            {"text": "I count everything as loss because of the surpassing worth of knowing Christ Jesus my Lord", "is_correct": False},
            {"text": "I press on toward the goal for the prize of the upward call of God in Christ Jesus", "is_correct": False}
        ]
    },
    {
        "category": "Following Jesus Today",
        "text": "Jesus said in John 13:35, 'By this everyone will know that you are my disciples, if you love one another.' If someone observed your daily life for a week, what evidence would they see that you are a follower of Jesus?",
        "type": "open_ended",
        "options": []
    },
    {
        "category": "Following Jesus Today",
        "text": "In Matthew 11:28-30, Jesus said, 'Come to me, all you who are weary and burdened, and I will give you rest.' What burdens are you currently carrying? What would it look like to truly bring them to Jesus and experience His rest?",
        "type": "open_ended",
        "options": []
    },
    {
        "category": "Following Jesus Today",
        "text": "Jesus told His disciples in Acts 1:8, 'You will be my witnesses.' How are you currently being a witness for Jesus in your everyday life — at home, school, work, or in your community? What is one step you could take to be more intentional about it?",
        "type": "open_ended",
        "options": []
    },
]

def main():
    print("=" * 60)
    print("Who is Jesus? Assessment Setup")
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
                print(f"✅ Created Who is Jesus? Assessment template: {template_id}")

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
                question_code = f"JESUS_{question_order:03d}"

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
            print(f"✅ SUCCESS! Created Who is Jesus? Assessment")
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
