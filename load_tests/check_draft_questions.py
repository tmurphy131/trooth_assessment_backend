#!/usr/bin/env python3
"""Check draft questions to find the correct answer keys."""
import requests
from get_test_token import get_firebase_token

# Get token
token = get_firebase_token('loadtest@test.com', 'TestPassword123!')
headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
base_url = 'https://trooth-backend-dev-ignpknnbva-uk.a.run.app'

# Get existing drafts
drafts_list = requests.get(f'{base_url}/assessment-drafts/list', headers=headers).json()
print(f"Found {len(drafts_list)} drafts in list")

if drafts_list:
    draft_id = drafts_list[0]['id']
    print(f"Checking draft: {draft_id}")
    
    # Get full draft details
    draft_resp = requests.get(f'{base_url}/assessment-drafts/{draft_id}', headers=headers)
    if draft_resp.status_code == 200:
        draft_data = draft_resp.json()
        questions = draft_data.get('questions', [])
        print(f"\nDraft has {len(questions)} questions")
        
        if questions:
            print("\nSample questions (first 5):")
            for q in questions[:5]:
                print(f"  - id: {q.get('id')}")
                print(f"    code: {q.get('code')}")
                print(f"    text: {q.get('question_text', '')[:50]}...")
                print()
