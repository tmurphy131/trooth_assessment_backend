#!/usr/bin/env python3
"""Check template questions to find the correct answer keys."""
import requests
from get_test_token import get_firebase_token

# Get token
token = get_firebase_token('loadtest@test.com', 'TestPassword123!')
headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
base_url = 'https://trooth-backend-dev-ignpknnbva-uk.a.run.app'

# Get published templates
templates = requests.get(f'{base_url}/templates/published', headers=headers).json()
print(f"Found {len(templates)} templates")

if templates:
    tpl_id = templates[0].get('id')
    print(f"Template ID: {tpl_id}")
    
    # Try admin endpoint for full template
    admin_resp = requests.get(f'{base_url}/admin/templates/{tpl_id}', headers=headers)
    print(f"Admin endpoint status: {admin_resp.status_code}")
    
    if admin_resp.status_code == 200:
        data = admin_resp.json()
        print(f"Has questions: {'questions' in data}")
        if 'questions' in data:
            print(f"Num questions: {len(data['questions'])}")
            for q in data['questions'][:5]:
                print(f"  - id: {q.get('id')}, code: {q.get('code')}")
    elif admin_resp.status_code == 403:
        print("Admin access denied for apprentice user")
        # Try getting draft questions
        print("\nChecking existing draft...")
        drafts = requests.get(f'{base_url}/assessment-drafts/list', headers=headers).json()
        if drafts:
            draft = drafts[0]
            print(f"Draft answers keys: {list(draft.get('answers', {}).keys())}")
            
            # Check the draft endpoint for more details
            draft_resp = requests.get(f'{base_url}/assessment-drafts/{draft["id"]}', headers=headers)
            print(f"Draft endpoint status: {draft_resp.status_code}")
            if draft_resp.status_code == 200:
                draft_data = draft_resp.json()
                print(f"Draft data keys: {list(draft_data.keys())}")
    else:
        print(f"Response: {admin_resp.text[:200]}")
