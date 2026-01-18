#!/usr/bin/env python3
"""Clean up existing drafts with invalid answer keys."""
import requests
from get_test_token import get_firebase_token

# Get token
token = get_firebase_token('loadtest@test.com', 'TestPassword123!')
headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
base_url = 'https://trooth-backend-dev-ignpknnbva-uk.a.run.app'

# Get existing drafts
drafts = requests.get(f'{base_url}/assessment-drafts/list', headers=headers).json()
print(f"Found {len(drafts)} drafts")

for draft in drafts:
    draft_id = draft['id']
    print(f"Deleting draft {draft_id}...")
    
    # Try to delete the draft
    del_resp = requests.delete(f'{base_url}/assessment-drafts/{draft_id}', headers=headers)
    print(f"  Status: {del_resp.status_code}")
    if del_resp.status_code != 200 and del_resp.status_code != 204:
        print(f"  Response: {del_resp.text[:100]}")

print("\nVerifying cleanup...")
remaining = requests.get(f'{base_url}/assessment-drafts/list', headers=headers).json()
print(f"Remaining drafts: {len(remaining)}")
