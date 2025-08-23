"""
Script to populate the database with spiritual assessment questions and templates.
Run this to create initial data for your assessment system.
"""

import requests
import json
from typing import List, Dict

# Configuration
API_BASE = "http://localhost:8000"
BEARER_TOKEN = "your-firebase-token-here"  # You'll need to replace this with actual token

def get_headers():
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {BEARER_TOKEN}"
    }

# Sample spiritual assessment questions
SPIRITUAL_QUESTIONS = [
    {
        "text": "How would you describe your current relationship with God?",
        "category": "Spiritual Foundation"
    },
    {
        "text": "What does daily prayer mean to you in your spiritual journey?",
        "category": "Prayer Life"
    },
    {
        "text": "How do you apply biblical teachings in your everyday decisions?",
        "category": "Biblical Application"
    },
    {
        "text": "Describe a time when your faith was challenged and how you responded.",
        "category": "Faith Challenges"
    },
    {
        "text": "How do you serve others in your community as an expression of your faith?",
        "category": "Service & Community"
    },
    {
        "text": "What role does Scripture reading play in your daily life?",
        "category": "Biblical Study"
    },
    {
        "text": "How do you see God working in your life circumstances?",
        "category": "Spiritual Awareness"
    },
    {
        "text": "Describe your understanding of forgiveness and how you practice it.",
        "category": "Christian Character"
    },
    {
        "text": "How do you balance spiritual growth with daily responsibilities?",
        "category": "Life Integration"
    },
    {
        "text": "What spiritual disciplines are most meaningful to you and why?",
        "category": "Spiritual Practices"
    }
]

def create_categories():
    """Create question categories first"""
    categories = [
        "Spiritual Foundation",
        "Prayer Life", 
        "Biblical Application",
        "Faith Challenges",
        "Service & Community",
        "Biblical Study",
        "Spiritual Awareness",
        "Christian Character",
        "Life Integration",
        "Spiritual Practices"
    ]
    
    created_categories = {}
    for category_name in categories:
        try:
            response = requests.post(
                f"{API_BASE}/categories",
                headers=get_headers(),
                json={"name": category_name, "description": f"Questions about {category_name.lower()}"}
            )
            if response.status_code == 200:
                category_data = response.json()
                created_categories[category_name] = category_data["id"]
                print(f"✅ Created category: {category_name}")
            else:
                print(f"❌ Failed to create category {category_name}: {response.text}")
        except Exception as e:
            print(f"❌ Error creating category {category_name}: {e}")
    
    return created_categories

def create_questions(categories: Dict[str, str]):
    """Create spiritual assessment questions"""
    created_questions = []
    
    for question_data in SPIRITUAL_QUESTIONS:
        category_id = categories.get(question_data["category"])
        if not category_id:
            print(f"⚠️ Skipping question - category '{question_data['category']}' not found")
            continue
            
        try:
            response = requests.post(
                f"{API_BASE}/questions",
                headers=get_headers(),
                json={
                    "text": question_data["text"],
                    "category_id": category_id
                }
            )
            if response.status_code == 200:
                question = response.json()
                created_questions.append(question)
                print(f"✅ Created question: {question_data['text'][:50]}...")
            else:
                print(f"❌ Failed to create question: {response.text}")
        except Exception as e:
            print(f"❌ Error creating question: {e}")
    
    return created_questions

def create_assessment_template(questions: List[Dict]):
    """Create a spiritual assessment template with all questions"""
    try:
        # Create the template
        template_response = requests.post(
            f"{API_BASE}/admin/templates",
            headers=get_headers(),
            json={
                "name": "Spiritual Growth Assessment",
                "description": "A comprehensive assessment of spiritual development and faith journey",
                "is_published": True
            }
        )
        
        if template_response.status_code != 200:
            print(f"❌ Failed to create template: {template_response.text}")
            return None
            
        template = template_response.json()
        template_id = template["id"]
        print(f"✅ Created template: {template['name']}")
        
        # Add questions to template
        for i, question in enumerate(questions):
            try:
                response = requests.post(
                    f"{API_BASE}/admin/templates/{template_id}/questions",
                    headers=get_headers(),
                    json={
                        "question_id": question["id"],
                        "order": i + 1
                    }
                )
                if response.status_code == 200:
                    print(f"✅ Added question {i+1} to template")
                else:
                    print(f"❌ Failed to add question {i+1}: {response.text}")
            except Exception as e:
                print(f"❌ Error adding question {i+1}: {e}")
        
        return template
        
    except Exception as e:
        print(f"❌ Error creating template: {e}")
        return None

def main():
    print("🚀 Setting up Spiritual Assessment Database...")
    print(f"📡 API Base: {API_BASE}")
    print("⚠️  Make sure your backend is running and you have a valid Firebase token")
    print()
    
    # Step 1: Create categories
    print("📂 Creating question categories...")
    categories = create_categories()
    print(f"Created {len(categories)} categories")
    print()
    
    # Step 2: Create questions
    print("❓ Creating spiritual assessment questions...")
    questions = create_questions(categories)
    print(f"Created {len(questions)} questions")
    print()
    
    # Step 3: Create template
    print("📋 Creating assessment template...")
    template = create_assessment_template(questions)
    if template:
        print(f"✅ Template created with ID: {template['id']}")
    print()
    
    print("🎉 Database setup complete!")
    print("📱 Your Flutter app can now use these assessment questions and templates.")

if __name__ == "__main__":
    print("⚠️  IMPORTANT: Update BEARER_TOKEN with your actual Firebase token before running!")
    print("To get a token:")
    print("1. Login to your Flutter app")
    print("2. Check the console logs for the token")
    print("3. Replace BEARER_TOKEN in this script")
    print()
    
    # Uncomment the line below after setting your token
    # main()
