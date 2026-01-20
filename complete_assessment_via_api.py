#!/usr/bin/env python3
"""
Script to complete assessments for the Apple reviewer apprentice account via API.
This authenticates like the frontend does and triggers full AI scoring.

Usage:
  python3 complete_assessment_via_api.py [assessment_number]
  
  1 = Master Trooth (70% accuracy)
  2 = Genesis (80% accuracy)
  3 = Matthew (50% accuracy)
  4 = Gospel Fluency (78% accuracy)
  
For OAuth users (signed up with Google/Apple), you need to provide Firebase UID instead:
  APPRENTICE_UID=<firebase_uid> python3 complete_assessment_via_api.py
"""
import os
import sys
import json
import random
import time
import requests
import firebase_admin
from firebase_admin import credentials, auth as firebase_auth

# Configuration
FIREBASE_API_KEY = "AIzaSyDTzy7Z-LaX4wC1EH3k-MR4sbH2hiIFmAE"  # Web API key
BACKEND_URL = "https://trooth-discipleship-api.onlyblv.com"

# Apple reviewer credentials
APPRENTICE_EMAIL = "tay.murphy88@yahoo.com"
APPRENTICE_PASSWORD = "Addison1"  # Won't work for OAuth users
APPRENTICE_UID = "OJkcNZ52RQMnSkzgb6ejmWvbNID2" #os.getenv("APPRENTICE_UID")  # For OAuth users, set this env var

# Assessment configurations: (template_key_pattern, target_accuracy, display_name)
ASSESSMENTS = [
    ("Master Trooth", 0.70, "Master Trooth Assessment"),
    ("Genesis", 0.80, "Genesis Assessment"),
    ("Matthew", 0.50, "Matthew Assessment"),
    ("Gospel Fluency", 0.78, "Gospel Fluency Assessment"),
]


def init_firebase_admin():
    """Initialize Firebase Admin SDK if not already initialized."""
    if not firebase_admin._apps:
        # Try to load Firebase credentials
        firebase_cert_path = os.getenv("FIREBASE_CERT_PATH", "firebase_key.json")
        firebase_cert_json = os.getenv("FIREBASE_CERT_JSON")
        
        if firebase_cert_json:
            import json as json_lib
            cred_dict = json_lib.loads(firebase_cert_json)
            cred = credentials.Certificate(cred_dict)
        elif os.path.exists(firebase_cert_path):
            cred = credentials.Certificate(firebase_cert_path)
        else:
            print(f"WARNING: No Firebase Admin credentials found. OAuth user authentication will fail.")
            print(f"Set FIREBASE_CERT_PATH or FIREBASE_CERT_JSON environment variable.")
            return False
        
        firebase_admin.initialize_app(cred)
    return True


def get_custom_token_for_uid(uid: str) -> str:
    """Generate a custom token for a Firebase UID using Admin SDK."""
    if not init_firebase_admin():
        print("ERROR: Cannot generate custom token without Firebase Admin credentials.")
        sys.exit(1)
    
    print(f"Generating custom token for UID: {uid}...")
    custom_token = firebase_auth.create_custom_token(uid)
    
    # Exchange custom token for ID token via Firebase REST API
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithCustomToken?key={FIREBASE_API_KEY}"
    payload = {
        "token": custom_token.decode('utf-8') if isinstance(custom_token, bytes) else custom_token,
        "returnSecureToken": True
    }
    
    response = requests.post(url, json=payload)
    if response.status_code != 200:
        print(f"ERROR: Failed to exchange custom token: {response.text}")
        sys.exit(1)
    
    data = response.json()
    return data.get("idToken")


def firebase_sign_in(email: str, password: str) -> str:
    """Sign in via Firebase REST API and return ID token."""
    # If APPRENTICE_UID is set, use Admin SDK instead (for OAuth users)
    if APPRENTICE_UID:
        print(f"Detected APPRENTICE_UID environment variable. Using Admin SDK authentication...")
        return get_custom_token_for_uid(APPRENTICE_UID)
    
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_API_KEY}"
    
    payload = {
        "email": email,
        "password": password,
        "returnSecureToken": True
    }
    
    print(f"Signing in as {email}...")
    response = requests.post(url, json=payload)
    
    if response.status_code != 200:
        error_data = response.json()
        error_message = error_data.get('error', {}).get('message', 'Unknown error')
        
        if 'INVALID_PASSWORD' in error_message or 'EMAIL_NOT_FOUND' in error_message:
            print(f"\n❌ ERROR: Firebase sign-in failed!")
            print(f"This user likely signed up with Google/Apple OAuth (not email/password).")
            print(f"\nTo authenticate OAuth users, you need to:")
            print(f"1. Get the user's Firebase UID from Firestore or Firebase Console")
            print(f"2. Run: APPRENTICE_UID=<their_firebase_uid> python3 complete_assessment_via_api.py")
            print(f"\nOriginal error: {error_message}")
        else:
            print(f"ERROR: Firebase sign-in failed: {response.text}")
        
        sys.exit(1)
    
    data = response.json()
    token = data.get("idToken")
    print(f"✅ Signed in successfully!")
    return token


def api_get(token: str, endpoint: str) -> dict:
    """Make authenticated GET request to backend API."""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BACKEND_URL}{endpoint}", headers=headers)
    
    if response.status_code != 200:
        print(f"ERROR: GET {endpoint} failed ({response.status_code}): {response.text}")
        return None
    
    return response.json()


def api_post(token: str, endpoint: str, data: dict = None) -> dict:
    """Make authenticated POST request to backend API."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    response = requests.post(f"{BACKEND_URL}{endpoint}", headers=headers, json=data or {})
    
    if response.status_code not in [200, 201]:
        print(f"ERROR: POST {endpoint} failed ({response.status_code}): {response.text}")
        return None
    
    return response.json()


def api_patch(token: str, endpoint: str, data: dict) -> dict:
    """Make authenticated PATCH request to backend API."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    response = requests.patch(f"{BACKEND_URL}{endpoint}", headers=headers, json=data)
    
    if response.status_code != 200:
        print(f"ERROR: PATCH {endpoint} failed ({response.status_code}): {response.text}")
        return None
    
    return response.json()


def get_published_templates(token: str) -> list:
    """Get all published assessment templates."""
    return api_get(token, "/templates/published") or []


def find_template(templates: list, key_pattern: str) -> dict:
    """Find a template by key or name pattern."""
    for t in templates:
        key = t.get('key', '') or t.get('template_key', '') or ''
        name = t.get('name', '') or t.get('display_name', '') or ''
        if key_pattern.lower() in key.lower() or key_pattern.lower() in name.lower():
            return t
    return None


def generate_answers(questions: list, target_accuracy: float) -> tuple:
    """Generate answers with target accuracy for MC questions.
    Returns (answers_dict, last_question_id)"""
    answers = {}
    
    mc_questions = []
    open_questions = []
    
    for q in questions:
        q_type = q.get('question_type') or q.get('type', '')
        if q_type == 'multiple_choice' and q.get('options'):
            mc_questions.append(q)
        elif q_type == 'open_ended':
            open_questions.append(q)
    
    # Calculate how many MC questions to answer correctly
    num_correct = int(len(mc_questions) * target_accuracy)
    correct_indices = set(random.sample(range(len(mc_questions)), min(num_correct, len(mc_questions))))
    
    print(f"\n📊 Question breakdown:")
    print(f"   Multiple choice: {len(mc_questions)} (targeting {num_correct} correct = {target_accuracy*100:.0f}%)")
    print(f"   Open-ended: {len(open_questions)}")
    
    last_question_id = None
    
    # Generate MC answers - use question ID as key
    for i, q in enumerate(mc_questions):
        q_id = q.get('id')  # Use question ID as the key
        options = q.get('options', [])
        
        correct_option = next((o for o in options if o.get('is_correct')), None)
        incorrect_options = [o for o in options if not o.get('is_correct')]
        
        if i in correct_indices and correct_option:
            # Answer correctly
            answer_text = correct_option.get('text', '')
            answers[q_id] = answer_text
        elif incorrect_options:
            # Answer incorrectly  
            wrong = random.choice(incorrect_options)
            answers[q_id] = wrong.get('text', '')
        elif correct_option:
            # No wrong options available
            answers[q_id] = correct_option.get('text', '')
        
        last_question_id = q_id
    
    # Generate thoughtful open-ended answers
    open_answer_templates = [
        "I believe this passage teaches us about God's faithfulness and love. It reminds me that even in difficult times, we can trust in His promises and find strength through prayer and community.",
        "This question makes me reflect on my own spiritual journey. I think the key lesson here is about obedience and trusting God even when we don't understand His plan.",
        "The principle I see here relates to how we treat others - with grace, compassion, and forgiveness, just as Christ has shown us.",
        "This challenges me to examine my heart and consider whether I'm truly living out my faith in practical ways each day.",
        "I see this as a call to deeper discipleship. It's not just about knowing Scripture but applying it to transform how I live and interact with others.",
        "This passage speaks to the importance of community and accountability in our walk with God. We weren't meant to journey alone.",
        "The theme of redemption stands out to me here. No matter what we've done, God's grace is sufficient and His mercies are new every morning.",
        "I think this is about surrendering control and acknowledging that God's ways are higher than our ways. It requires humility and faith.",
        "This reminds me of the importance of spiritual disciplines like prayer, fasting, and studying Scripture to grow closer to God.",
        "The call to be salt and light in the world resonates with me. We're meant to make a difference in our spheres of influence.",
    ]
    
    for i, q in enumerate(open_questions):
        q_id = q.get('id')  # Use question ID as the key
        base_answer = open_answer_templates[i % len(open_answer_templates)]
        answers[q_id] = f"{base_answer}"
        last_question_id = q_id
    
    return answers, last_question_id


def start_draft(token: str, template_id: str) -> dict:
    """Start a new assessment draft and get questions."""
    print(f"\n📝 Starting new draft for template {template_id}...")
    result = api_post(token, f"/assessment-drafts/start?template_id={template_id}", {})
    if result:
        draft_id = result.get('id') or result.get('draft_id')
        questions = result.get('questions', [])
        print(f"   Draft created: {draft_id}")
        print(f"   Questions loaded: {len(questions)}")
    return result


def update_draft(token: str, draft_id: str, answers: dict, last_question_id: str = None) -> dict:
    """Update draft with answers."""
    print(f"\n📝 Saving {len(answers)} answers to draft...")
    # Use the /{draft_id} endpoint to avoid issues with required fields
    result = api_patch(token, f"/assessment-drafts/{draft_id}", {
        "answers": answers,
        "last_question_id": last_question_id  # Can be None
    })
    if result:
        print(f"   Answers saved!")
    return result


def submit_draft(token: str, draft_id: str, template_id: str) -> dict:
    """Submit the draft for scoring."""
    print(f"\n🚀 Submitting draft for AI scoring...")
    result = api_post(token, "/assessment-drafts/submit", {
        "draft_id": draft_id,
        "template_id": template_id
    })
    if result:
        assessment_id = result.get('assessment_id') or result.get('id')
        print(f"   Submitted! Assessment ID: {assessment_id}")
    return result


def poll_for_completion(token: str, assessment_id: str, max_wait: int = 120) -> bool:
    """Poll until AI scoring is complete."""
    print(f"\n⏳ Waiting for AI scoring to complete...")
    
    start_time = time.time()
    while time.time() - start_time < max_wait:
        result = api_get(token, f"/assessments/{assessment_id}/status")
        if result:
            status = result.get('status', '')
            print(f"   Status: {status}")
            
            if status == 'done' or status == 'scored':
                print(f"   ✅ Scoring complete!")
                return True
            elif status == 'failed' or status == 'error':
                print(f"   ❌ Scoring failed")
                return False
        
        time.sleep(5)  # Wait 5 seconds between polls
    
    print(f"   ⚠️ Timed out waiting for scoring (waited {max_wait}s)")
    return False


def complete_assessment(token: str, templates: list, assessment_config: tuple):
    """Complete a single assessment end-to-end."""
    key_pattern, target_accuracy, display_name = assessment_config
    
    print(f"\n{'='*60}")
    print(f"🎯 {display_name}")
    print(f"   Target accuracy: {target_accuracy*100:.0f}%")
    print(f"{'='*60}")
    
    # Find the template
    template = find_template(templates, key_pattern)
    if not template:
        print(f"❌ ERROR: Could not find template matching '{key_pattern}'")
        print(f"   Available templates: {[t.get('key') or t.get('name') for t in templates]}")
        return False
    
    template_id = template.get('id') or template.get('template_id')
    template_name = template.get('name') or template.get('display_name')
    print(f"\n📋 Found template: {template_name}")
    print(f"   Template ID: {template_id}")
    
    # Start draft (this also fetches questions)
    draft_result = start_draft(token, template_id)
    if not draft_result:
        return False
    
    draft_id = draft_result.get('id') or draft_result.get('draft_id')
    questions = draft_result.get('questions', [])
    
    if not questions:
        print(f"❌ ERROR: No questions returned from draft start!")
        return False
    
    # Generate answers (returns tuple: answers_dict, last_question_id)
    answers, last_question_id = generate_answers(questions, target_accuracy)
    
    # Update draft with answers
    update_result = update_draft(token, draft_id, answers, last_question_id)
    if not update_result:
        return False
    
    # Submit draft
    submit_result = submit_draft(token, draft_id, template_id)
    if not submit_result:
        return False
    
    assessment_id = submit_result.get('assessment_id') or submit_result.get('id')
    
    # Poll for completion
    if assessment_id:
        poll_for_completion(token, assessment_id)
    
    print(f"\n✅ {display_name} completed!")
    return True


def main():
    print("="*60)
    print("📱 Assessment Completion Script (via API)")
    print("   For Apple Reviewer Apprentice Account")
    print("="*60)
    
    # Check for command line argument
    if len(sys.argv) > 1:
        try:
            choice = int(sys.argv[1])
        except ValueError:
            print("Invalid argument. Use a number 1-4.")
            sys.exit(1)
    else:
        print("\nWhich assessment do you want to complete?")
        for i, (_, accuracy, name) in enumerate(ASSESSMENTS, 1):
            print(f"  {i}. {name} ({accuracy*100:.0f}% accuracy)")
        print("  0. Exit")
        
        choice = input("\nEnter number: ").strip()
        try:
            choice = int(choice)
        except ValueError:
            print("Invalid input")
            sys.exit(1)
    
    if choice == 0:
        print("Exiting...")
        return
    
    if choice < 1 or choice > len(ASSESSMENTS):
        print(f"Invalid choice. Enter 1-{len(ASSESSMENTS)}")
        sys.exit(1)
    
    assessment_config = ASSESSMENTS[choice - 1]
    
    # Sign in
    token = firebase_sign_in(APPRENTICE_EMAIL, APPRENTICE_PASSWORD)
    
    # Get templates
    print("\n📚 Fetching published templates...")
    templates = get_published_templates(token)
    print(f"   Found {len(templates)} published templates")
    
    # Complete the assessment
    success = complete_assessment(token, templates, assessment_config)
    
    print("\n" + "="*60)
    if success:
        print("🎉 Done! The assessment should now appear in the app.")
    else:
        print("❌ Something went wrong. Check the errors above.")
    print("="*60)


if __name__ == "__main__":
    main()
