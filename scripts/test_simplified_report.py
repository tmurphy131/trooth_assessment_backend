#!/usr/bin/env python3
"""
Test script to submit a Master Trooth Assessment via API and test the simplified report.

This script:
1. Gets a Firebase ID token for the test user (ch0senpriest@gmail.com's apprentice)
2. Fetches published templates to get the Master Trooth Assessment ID
3. Starts a new draft
4. Populates all 57 questions with realistic answers
5. Submits the assessment for AI scoring
6. Polls for completion
7. Fetches the simplified report

Usage:
    python scripts/test_simplified_report.py [--base-url URL]

Environment variables needed:
    FIREBASE_API_KEY - Firebase Web API key for authentication
    TEST_USER_EMAIL - Email of the apprentice user (must be registered under ch0senpriest@gmail.com)
    TEST_USER_PASSWORD - Password for the test user
    
Or provide a Firebase ID token directly:
    FIREBASE_ID_TOKEN - Pre-obtained Firebase ID token
"""

import os
import sys
import json
import time
import argparse
import requests
from typing import Optional

# Configuration
DEFAULT_BASE_URL = "https://trooth-assessment-dev.onlyblv.com"
# DEFAULT_BASE_URL = "http://localhost:8000"

# Test user credentials (ch0senpriest@gmail.com is the apprentice, tay.murphy88@gmail.com is mentor)
TEST_USER_EMAIL = os.getenv("TEST_USER_EMAIL", "ch0senpriest@gmail.com")
TEST_USER_PASSWORD = os.getenv("TEST_USER_PASSWORD", "W3@re1T3am")
FIREBASE_API_KEY = os.getenv("FIREBASE_API_KEY", "AIzaSyDTzy7Z-LaX4wC1EH3k-MR4sbH2hiIFmAE")
FIREBASE_ID_TOKEN = os.getenv("FIREBASE_ID_TOKEN", "")


def get_firebase_token(email: str, password: str, api_key: str) -> str:
    """Get Firebase ID token using email/password authentication."""
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={api_key}"
    
    payload = {
        "email": email,
        "password": password,
        "returnSecureToken": True
    }
    
    response = requests.post(url, json=payload)
    
    if response.status_code != 200:
        print(f"❌ Firebase auth failed: {response.text}")
        sys.exit(1)
    
    data = response.json()
    return data["idToken"]


def api_request(method: str, endpoint: str, base_url: str, token: str, json_data: dict = None, params: dict = None) -> dict:
    """Make an authenticated API request."""
    url = f"{base_url.rstrip('/')}{endpoint}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    response = requests.request(
        method=method,
        url=url,
        headers=headers,
        json=json_data,
        params=params
    )
    
    print(f"  {method} {endpoint} -> {response.status_code}")
    
    if response.status_code >= 400:
        print(f"    Error: {response.text[:500]}")
        return None
    
    try:
        return response.json()
    except:
        return {"status_code": response.status_code}


# ============================================================================
# REALISTIC ANSWERS FOR ALL 57 QUESTIONS
# ============================================================================
# Answers keyed by question ID (will be mapped dynamically based on question text)

MULTIPLE_CHOICE_ANSWERS = {
    # Category 1: Spiritual Growth (Questions 1-4)
    "When the disciples asked Jesus to increase their faith": "b",  # mustard seed
    "Jacob's spiritual growth is demonstrated": "a",  # new name Israel
    "Peter's transformation from impulsive fisherman": "b",  # restoration by Jesus
    "parable of the soils": "b",  # rocky ground
    
    # Category 2: Prayer Life (Questions 8-11)
    "Hannah desperately wanted a child": "b",  # temple at Shiloh
    "What did Jesus do when He wanted to spend time in prayer": "c",  # solitary place
    "Daniel faced the decree forbidding prayer": "c",  # three times daily
    "parable of the Pharisee and the tax collector": "b",  # tax collector's prayer
    
    # Category 3: Bible Study (Questions 16-20)
    "Ezra returned from exile": "b",  # studying and teaching the Law
    "Ethiopian eunuch need when Philip found him": "b",  # someone to explain
    "boy Samuel first heard God's voice": "c",  # Eli the priest
    "King Josiah found the Book of the Law": "b",  # tore his clothes
    "Jesus was tempted by Satan in the wilderness": "c",  # quoted Scripture
    
    # Category 4: Community & Fellowship (Questions 25-28)
    "early church in Acts faced persecution": "b",  # met in homes
    "friendship between David and Jonathan": "b",  # souls knit together
    "disciples argued about who was the greatest": "b",  # washed their feet
    "Ruth's commitment to Naomi": "a",  # your people will be my people
    
    # Category 5: Service & Ministry (Questions 33-36)
    "Moses felt overwhelmed leading the Israelites": "b",  # delegate responsibilities
    "widow to give her last two coins": "b",  # heart's devotion
    "Nehemiah saw the broken walls of Jerusalem": "c",  # wept, prayed, took action
    "Dorcas (Tabitha) was known": "b",  # acts of charity and making clothes
    
    # Category 6: Discipleship (Questions 41-44)
    "Jesus called His first disciples by the Sea of Galilee": "b",  # left nets immediately
    "Jesus mean when He told the rich young ruler": "a",  # complete surrender
    "Paul discipled Timothy": "b",  # father-son relationship
    "Barnabas demonstrated godly discipleship": "c",  # Saul/Paul
    
    # Category 7: Faith Practice (Questions 49-52)
    "Daniel was commanded to worship the king's statue": "b",  # refused, lion's den
    "Joseph maintain his faith practice while serving in Potiphar's house": "b",  # integrity, gave God credit
    "Shadrach, Meshach, and Abednego were thrown into the fiery furnace": "b",  # delivered, no smoke
    "Jesus demonstrate authentic faith practice": "b",  # balanced teaching, prayer, service
}

OPEN_ENDED_ANSWERS = {
    # Category 1: Spiritual Growth (Questions 5-7)
    "Describe a specific time in the past year when you experienced significant spiritual growth": 
        """I guess the only time I can think of was when I started going back to church after not attending for a while. I'm not sure if that really counts as growth though. Honestly, I still struggle to see how my faith connects to my daily life. I read my Bible sometimes but I don't always understand what I'm reading or how to apply it. My mentor has been encouraging me to be more intentional, but I find myself getting distracted by other things. I want to grow but I'm not sure what that even looks like practically.""",
    
    "What are the biggest obstacles you currently face in your spiritual development":
        """There are so many obstacles I don't even know where to start. I'm constantly busy with work and by the time I get home I'm too tired to pray or read the Bible. Social media is a huge time waster for me - I'll pick up my phone to read a devotional and end up scrolling for an hour. I also struggle with doubt sometimes. When bad things happen, I wonder if God is really there or if He cares. I don't have anyone I can really talk to about this stuff. My church friends seem to have it all together and I don't want them to think I'm a bad Christian.""",
    
    "How do you measure your own spiritual maturity":
        """Honestly, I'm not really sure how to measure it. I guess I compare myself to others? Like if I'm at church more than someone else or if I know more Bible verses, I figure I must be doing okay. But deep down I know that's probably not the right way to think about it. My mentor talks about 'fruit of the Spirit' but I don't really see a lot of that in my life - I still get angry, I'm impatient, and I can be pretty selfish. Maybe spiritual maturity just takes more time? I'm only a few years into this faith journey.""",
    
    # Category 2: Prayer Life (Questions 12-15)
    "Describe your current prayer routine":
        """I don't really have a set routine. I try to pray before meals but I forget a lot. Sometimes I'll pray before bed but I usually fall asleep partway through. When something bad happens or I need something, I definitely pray more. I know I should have a more consistent prayer life but it feels weird talking to someone I can't see. I've tried journaling my prayers like my mentor suggested but it feels awkward writing to God. I wish prayer came more naturally to me.""",
    
    "What has been your most meaningful prayer experience":
        """I'm struggling to think of one honestly. Most of my prayers feel pretty routine - just going through the motions. There was one time at a retreat where everyone was crying during the worship and prayer time. I felt something but I'm not sure if it was God or just the emotional atmosphere. I keep hearing other people talk about 'hearing from God' but I've never experienced that. It makes me wonder if I'm doing something wrong or if God just doesn't speak to me the same way.""",
    
    "What challenges do you face in maintaining a consistent prayer life":
        """Pretty much everything is a challenge. I don't know what to say, I get bored or distracted, and I'm not sure if it even makes a difference. Sometimes I wonder why I need to pray if God already knows everything and has a plan anyway. My mind wanders constantly - I'll start praying about one thing and suddenly I'm thinking about my grocery list. I've tried prayer apps and prayer lists but nothing seems to stick. I feel guilty about how weak my prayer life is.""",
    
    "How do you balance praise, confession, thanksgiving, and requests":
        """Balance? I mostly just do requests. If I'm being honest, my prayers are probably 90% asking God for things I need or want. I know I should praise Him and thank Him more, but when I try it feels forced, like I'm just saying what I think He wants to hear. Confession is hard too - I know I sin but sitting there listing all my sins feels depressing. I usually just say a quick 'forgive me for my sins' and move on. I clearly need help in this area.""",
    
    # Category 3: Bible Study (Questions 21-24)
    "How often do you currently read the Bible":
        """Not as often as I should. Maybe a few times a week if I'm being generous with myself. I'll have good stretches where I read every day for a week, then I'll go two weeks without opening it. I have a Bible app on my phone but I usually end up checking other apps instead. When I do read, it's usually just a verse or two - I find it hard to understand the longer passages, especially the Old Testament stuff. I feel bad admitting this because I know the Bible is supposed to be important.""",
    
    "What book or passage of Scripture has had the greatest impact on your life":
        """I like Psalm 23 because it's familiar and comforting. 'The Lord is my shepherd' is nice to think about. I also like Jeremiah 29:11 about God having plans to prosper me. But honestly, I haven't done a deep dive into any particular book. I kind of just read whatever the devotional tells me to or what comes up in church. I feel like I'm missing out on something deeper but I don't know how to find it. Bible study feels overwhelming - there's so much there.""",
    
    "Describe your approach to studying difficult or confusing passages":
        """Usually I just skip them and move on to something easier to understand. If a passage is confusing, I figure there are plenty of other verses that make sense, so why get stuck on the hard ones? Sometimes I'll Google it or ask my mentor, but then I get multiple different interpretations and I don't know which one is right. I don't have any commentaries or study tools - I wouldn't even know where to start. I wish the Bible was just easier to understand.""",
    
    "How do you apply what you learn from Bible study to your daily life":
        """This is where I really struggle. I can read something that sounds good, but then I walk out the door and it's like I forgot everything. There's a disconnect between what I read and how I actually live. I know Jesus said to love my neighbor, but then I get cut off in traffic and I'm cursing the other driver. I read about forgiveness but I'm still holding grudges. Maybe I'm not studying the right way? I wish there was a more direct line between reading and doing.""",
    
    # Category 4: Community & Fellowship (Questions 29-32)
    "Describe your current level of involvement in Christian community":
        """I go to church most Sundays, but I usually slip in late and leave right after. I tried a small group once but it felt awkward - everyone seemed to know each other already and I felt like an outsider. I have a mentor which is great, but besides that I don't really have close Christian friends. I know I should be more involved but I'm an introvert and all the social stuff drains me. I tell myself I'll join something eventually but it hasn't happened yet.""",
    
    "How comfortable are you with being vulnerable":
        """Not comfortable at all. I have a hard time sharing my struggles because I don't want people to judge me or think less of me. Everyone at church seems so put together with their perfect families and their confident prayers. If they knew the thoughts I have or the things I struggle with, they'd probably be shocked. I keep most things surface level. Even with my mentor, there are things I haven't shared because I'm embarrassed. I know this isn't healthy but I don't know how to change it.""",
    
    "Give an example of how you've recently encouraged or been encouraged by another believer":
        """I'm trying to think of something recent but nothing really stands out. I guess people say 'good to see you' at church, which is nice? My mentor encourages me a lot but I don't feel like I do much encouraging myself. I'm not good at knowing what to say to people. I always worry I'll say the wrong thing or that it will come across as fake. This question is making me realize I probably need to work on this - I'm pretty focused on my own problems and not very aware of others.""",
    
    "What role do you typically play in group settings":
        """I'm usually the quiet one in the corner hoping no one calls on me. I observe more than participate. If someone asks me a direct question I'll answer, but I don't volunteer much. I'm not a leader and I'm not particularly good at serving - I don't have obvious skills to contribute. I feel like I'm always on the receiving end rather than giving. My mentor keeps telling me everyone has something to offer but I haven't figured out what my thing is yet.""",
    
    # Category 5: Service & Ministry (Questions 37-40)
    "What spiritual gifts do you believe God has given you":
        """I took a spiritual gifts assessment once but the results were pretty flat - nothing really stood out. I don't think I have the obvious gifts like teaching or leadership or music. Maybe helps? I'm okay at behind-the-scenes stuff but even that doesn't feel like a 'gift' - more like just doing basic tasks. I see other people using their gifts and I wonder why God didn't give me something more useful. I'm still trying to figure out where I fit.""",
    
    "Describe your current involvement in ministry or service":
        """Pretty minimal honestly. I helped set up chairs once at church. I gave money to a food drive. But I'm not actively involved in any ongoing ministry. I've thought about volunteering somewhere but I never follow through - I'm worried I won't have time or that I won't know what I'm doing. The few times I've tried serving, I felt out of place and uncertain. I know serving is important but it feels like another thing to add to an already overwhelming list.""",
    
    "What barriers or fears have you faced when it comes to serving":
        """Fear of failure is huge. What if I mess up? What if I don't know enough? What if people realize I'm not as spiritual as they thought? I also worry about overcommitting - what if I say yes to something and then can't follow through? That would be worse than not helping at all. I tell myself I'll serve more when I'm more mature in my faith, when I have more time, when I feel more confident. But those conditions never seem to be met.""",
    
    "Tell about a time when serving others significantly impacted your own spiritual growth":
        """I don't have a strong example here. The times I have served felt more like checking a box than a meaningful experience. I helped with a church cleanup day and mostly felt tired afterward, not spiritually filled. Maybe I'm serving with the wrong attitude? Or maybe I just haven't found the right opportunity yet. I hear others talk about how serving changed their life and I wonder what I'm missing. I want that experience but I don't know how to get there.""",
    
    # Category 6: Discipleship (Questions 45-48)
    "Who has been most influential in discipling you in your faith":
        """My current mentor is probably the only person who's really discipled me intentionally. Before that, I kind of just picked things up on my own from sermons and books. I grew up going to church but no one really explained what it meant to follow Jesus - it was more about just showing up. I'm grateful for my mentor but our relationship is still pretty new. I'm learning a lot but I also feel like I'm way behind where I should be for my age.""",
    
    "Are you currently discipling or mentoring anyone":
        """No, definitely not. I don't feel qualified to disciple anyone - I can barely figure out my own faith. Who would want to learn from me? I'm still a mess. Maybe someday when I have more experience and know more Bible verses and have my life more together. Right now I feel like I'm the one who needs discipling, not the other way around. The idea of being responsible for someone else's spiritual growth is scary.""",
    
    "How do you share your faith with non-believers":
        """I mostly don't. I'm afraid of saying the wrong thing or being seen as pushy or judgmental. Most of my friends aren't Christians and I don't want to weird them out or damage those relationships. If someone asks me directly about my faith, I'll answer, but that rarely happens. I feel guilty about not evangelizing more but I don't even know what I would say. 'Hey, want to come to church sometime?' feels so awkward. This is definitely an area of weakness.""",
    
    "What does it mean to you personally to 'take up your cross daily'":
        """Honestly, I'm not entirely sure what this means in practical terms. I know it's something Jesus said about following Him, but the 'daily cross' part is confusing. Does it mean being willing to die for my faith? I'm not in a situation where that's a real possibility. Does it mean suffering? My life is pretty comfortable. I probably need to study this more. I hear people use this phrase but I've never really understood how to apply it to modern suburban life.""",
    
    # Category 7: Faith Practice (Questions 53-57)
    "How has your faith influenced your daily decisions and lifestyle choices":
        """I want to say it influences everything but that would be a lie. Sunday me and weekday me are kind of different people. At church I'm thinking about God and being good, but by Monday I'm back to my usual patterns - gossip, complaining, worrying about money, getting frustrated with people. There are some things I've changed - I don't party like I used to - but a lot of my daily decisions are made without really considering what God wants. I compartmentalize my faith more than I should.""",
    
    "What spiritual disciplines do you practice regularly":
        """I don't have a lot of consistent disciplines. I've tried different things - fasting, journaling, memorization - but nothing has really stuck beyond a few weeks. I tell myself I'm too busy or too tired. The only thing that's somewhat consistent is church attendance, and even that isn't every week. I know spiritual disciplines are supposed to help you grow but they feel like another set of obligations in an already packed life. I need someone to help me build better habits.""",
    
    "Describe how you handle conflict or difficult situations differently now":
        """I wish I could say I handle things better as a Christian, but honestly I still react the same ways I always have. I avoid conflict, then get resentful, then eventually blow up. Or I replay conversations in my head obsessing over what I should have said. I know I'm supposed to forgive and turn the other cheek but that's really hard when someone has actually hurt you. I've tried praying for people I'm in conflict with but my prayers feel fake. This is one area where my faith hasn't seemed to change me much yet.""",
    
    "In what ways are you currently living out your faith in your workplace, family, or community":
        """At work, no one even knows I'm a Christian. I don't hide it exactly, but I don't bring it up. I try to be honest and work hard, but so do lots of non-Christians. At home, my family knows I go to church but we don't really talk about faith - it feels awkward with relatives who aren't believers. In my community, I don't really do anything faith-related. I feel like I'm living two separate lives and I don't know how to integrate them. My faith is more private than public.""",
    
    "How do you maintain your Christian witness and values when faced with cultural pressures":
        """I struggle with this a lot. At work there's pressure to participate in things I'm not comfortable with - drinking events, gossip, cutting corners. I usually just stay quiet rather than speak up. Online, I see Christians getting attacked for their beliefs and I stay out of those conversations to avoid conflict. I know I should be bolder but I'm scared of being rejected or labeled as intolerant. I often feel like I'm blending in rather than standing out. My witness is pretty weak to be honest."""
}


def build_answers_dict(questions: list) -> dict:
    """Map question IDs to answers based on question text matching.
    
    For MC questions: ~70% correct, ~30% incorrect to simulate a struggling apprentice.
    For open-ended: Uses the revised answers that show areas of struggle.
    """
    import random
    random.seed(42)  # For reproducibility
    
    # Question indices to answer INCORRECTLY (roughly 30% of MC questions)
    # We'll pick the wrong answer for these questions
    INCORRECT_MC_INDICES = {2, 5, 8, 11, 14, 17, 20, 23, 26}  # ~30% wrong
    
    answers = {}
    mc_index = 0
    
    for q in questions:
        q_id = q["id"]
        q_text = q["text"]
        q_type = q.get("question_type", "open_ended")
        
        # For multiple choice questions
        if q_type == "multiple_choice" and q.get("options"):
            mc_index += 1
            
            # Decide if this should be correct or incorrect
            should_be_incorrect = mc_index in INCORRECT_MC_INDICES
            
            if should_be_incorrect:
                # Pick a WRONG answer (first option that is NOT correct)
                wrong_opt = None
                for opt in q["options"]:
                    if not opt.get("is_correct"):
                        wrong_opt = opt
                        break
                
                if wrong_opt:
                    answers[q_id] = wrong_opt["id"]
                else:
                    # Fallback if no is_correct flag - just pick first option
                    answers[q_id] = q["options"][0]["id"]
            else:
                # Pick the CORRECT answer
                correct_opt = None
                for opt in q["options"]:
                    if opt.get("is_correct"):
                        correct_opt = opt
                        break
                
                if correct_opt:
                    answers[q_id] = correct_opt["id"]
                else:
                    # Fallback: use our answer key by order
                    matched = False
                    for key_phrase, answer_letter in MULTIPLE_CHOICE_ANSWERS.items():
                        if key_phrase.lower() in q_text.lower():
                            order_map = {"a": 1, "b": 2, "c": 3, "d": 4}
                            target_order = order_map.get(answer_letter, 1)
                            for opt in q["options"]:
                                if opt.get("order") == target_order:
                                    answers[q_id] = opt["id"]
                                    matched = True
                                    break
                            break
                    
                    # If still no match, pick first option
                    if not matched and q.get("options"):
                        answers[q_id] = q["options"][0]["id"]
        
        # For open-ended questions
        else:
            matched = False
            for key_phrase, answer_text in OPEN_ENDED_ANSWERS.items():
                if key_phrase.lower() in q_text.lower():
                    answers[q_id] = answer_text
                    matched = True
                    break
            
            # If no match found, provide a generic thoughtful answer
            if not matched:
                answers[q_id] = f"""This is an area I'm actively growing in. I've been learning through 
Scripture study and conversations with my mentor that spiritual growth is a lifelong journey. 
I'm committed to deepening my walk with Christ through daily practices of prayer, Bible reading, 
and service to others. While I have room to grow, I'm grateful for the progress God has made in my life 
and look forward to continued transformation through His Spirit."""
    
    return answers


def main():
    parser = argparse.ArgumentParser(description="Test the simplified report API")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="API base URL")
    parser.add_argument("--token", help="Firebase ID token (optional)")
    args = parser.parse_args()
    
    base_url = args.base_url
    print(f"\n🔧 Testing Simplified Report API")
    print(f"   Base URL: {base_url}\n")
    
    # Step 1: Get Firebase token
    print("1️⃣  Authenticating...")
    token = args.token or FIREBASE_ID_TOKEN
    
    if not token:
        if TEST_USER_EMAIL and TEST_USER_PASSWORD and FIREBASE_API_KEY:
            token = get_firebase_token(TEST_USER_EMAIL, TEST_USER_PASSWORD, FIREBASE_API_KEY)
            print(f"   ✅ Got Firebase token for {TEST_USER_EMAIL}")
        else:
            print("   ❌ No authentication credentials provided!")
            print("      Set FIREBASE_ID_TOKEN or (TEST_USER_EMAIL, TEST_USER_PASSWORD, FIREBASE_API_KEY)")
            print("\n   You can get a token from the mobile app or Firebase console.")
            print("   Then run: python scripts/test_simplified_report.py --token YOUR_TOKEN")
            sys.exit(1)
    else:
        print("   ✅ Using provided token")
    
    # Step 2: Get published templates
    print("\n2️⃣  Fetching published templates...")
    templates = api_request("GET", "/templates/published", base_url, token)
    
    if not templates:
        print("   ❌ Failed to fetch templates")
        sys.exit(1)
    
    # Find Master Trooth Assessment
    master_template = None
    for t in templates:
        if "master" in t.get("name", "").lower() or "trooth" in t.get("name", "").lower():
            master_template = t
            break
    
    if not master_template:
        print("   ❌ Master Trooth Assessment template not found")
        print(f"   Available templates: {[t.get('name') for t in templates]}")
        sys.exit(1)
    
    template_id = master_template["id"]
    print(f"   ✅ Found template: {master_template.get('name')} (ID: {template_id})")
    
    # Step 3: Start a draft
    print("\n3️⃣  Starting assessment draft...")
    draft = api_request("POST", f"/assessment-drafts/start?template_id={template_id}", base_url, token)
    
    if not draft:
        print("   ❌ Failed to start draft")
        sys.exit(1)
    
    draft_id = draft["id"]
    questions = draft.get("questions", [])
    print(f"   ✅ Draft created: {draft_id}")
    print(f"   📝 {len(questions)} questions loaded")
    
    # Step 4: Build and save answers
    print("\n4️⃣  Building answers for all questions...")
    answers = build_answers_dict(questions)
    print(f"   ✅ Generated answers for {len(answers)} questions")
    
    # Save draft with answers
    print("\n5️⃣  Saving draft with answers...")
    save_data = {
        "answers": answers,
        "last_question_id": questions[-1]["id"] if questions else None,
        "template_id": template_id
    }
    
    saved = api_request("POST", "/assessment-drafts", base_url, token, json_data=save_data)
    if not saved:
        print("   ❌ Failed to save draft")
        sys.exit(1)
    print("   ✅ Draft saved")
    
    # Step 5: Submit assessment
    print("\n6️⃣  Submitting assessment for AI scoring...")
    submitted = api_request("POST", f"/assessment-drafts/submit?draft_id={draft_id}", base_url, token)
    
    if not submitted:
        print("   ❌ Failed to submit assessment")
        sys.exit(1)
    
    assessment_id = submitted.get("id")
    print(f"   ✅ Submitted! Assessment ID: {assessment_id}")
    print(f"   📊 Status: {submitted.get('status', 'unknown')}")
    
    if submitted.get("scores"):
        print(f"   📈 Baseline score: {submitted['scores'].get('overall_score', 'N/A')}")
    
    # Step 6: Poll for completion
    print("\n7️⃣  Waiting for AI scoring to complete...")
    max_attempts = 60  # 5 minutes max
    attempt = 0
    
    while attempt < max_attempts:
        status_resp = api_request("GET", f"/assessments/{assessment_id}/status", base_url, token)
        if status_resp:
            status = status_resp.get("status", "unknown")
            print(f"   ... Status: {status} (attempt {attempt + 1})")
            
            if status == "done":
                print("   ✅ Scoring complete!")
                break
            elif status == "error":
                print("   ❌ Scoring failed!")
                break
        
        time.sleep(5)
        attempt += 1
    
    if attempt >= max_attempts:
        print("   ⚠️  Timeout waiting for scoring - continuing anyway")
    
    # Step 7: Fetch simplified report AS MENTOR
    print("\n8️⃣  Fetching simplified report (as mentor)...")
    
    # Get mentor token
    mentor_token = None
    try:
        mentor_auth = requests.post(
            f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_API_KEY}",
            json={"email": "tay.murphy88@gmail.com", "password": TEST_USER_PASSWORD, "returnSecureToken": True}
        )
        if mentor_auth.status_code == 200:
            mentor_token = mentor_auth.json().get("idToken")
            print("   ✅ Got mentor token")
    except Exception as e:
        print(f"   ⚠️ Could not get mentor token: {e}")
    
    if mentor_token:
        simplified = api_request("GET", f"/mentor/reports/{assessment_id}/simplified", base_url, mentor_token)
        
        if simplified:
            print("\n" + "="*60)
            print("📋 SIMPLIFIED REPORT (Mentor View)")
            print("="*60)
            print(json.dumps(simplified, indent=2))
        else:
            print("   ⚠️  Could not fetch simplified report")
    
    # Also fetch full assessment data
    print("\n9️⃣  Fetching full assessment data...")
    full_assessment = api_request("GET", f"/assessments/{assessment_id}", base_url, token)
    if full_assessment:
        print("\n" + "="*60)
        print("📋 FULL ASSESSMENT SCORES")
        print("="*60)
        scores = full_assessment.get("scores", {})
        # Show key metrics
        print(f"Overall Score: {scores.get('overall_score', 'N/A')}")
        print(f"Category Scores: {json.dumps(scores.get('category_scores', {}), indent=2)}")
        
        # Check for v2.1 format first (mentor_blob_v2 at top level of scores)
        mentor_blob = scores.get('mentor_blob_v2', {})
        
        # v2.1 format has mc_percent and health_score at top level of mentor_blob
        if 'health_score' in mentor_blob:
            print(f"\nMC Percent: {mentor_blob.get('biblical_knowledge', {}).get('percent', 'N/A')}%")
            print(f"Health Score: {mentor_blob.get('health_score', 'N/A')}")
            print(f"Health Band: {mentor_blob.get('health_band', 'N/A')}")
            print(f"Strengths: {mentor_blob.get('strengths', [])}")
            print(f"Gaps: {mentor_blob.get('gaps', [])}")
        else:
            # Legacy v2.0 format
            snapshot = mentor_blob.get('snapshot', {})
            print(f"\nMC Percent: {snapshot.get('overall_mc_percent', 'N/A')}%")
            print(f"Knowledge Band: {snapshot.get('knowledge_band', 'N/A')}")
            print(f"Strengths: {snapshot.get('top_strengths', [])}")
            print(f"Gaps: {snapshot.get('top_gaps', [])}")
    
    print("\n✅ Test complete!")
    print(f"   Assessment ID: {assessment_id}")
    print(f"   Template ID: {template_id}")
    

if __name__ == "__main__":
    main()
