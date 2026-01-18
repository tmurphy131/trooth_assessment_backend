#!/usr/bin/env python3
"""Test the full assessment workflow with real question IDs."""
import requests
from get_test_token import get_firebase_token

# Get token
token = get_firebase_token('loadtest@test.com', 'TestPassword123!')
headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
base_url = 'https://trooth-backend-dev-ignpknnbva-uk.a.run.app'

print("=" * 60)
print("Testing Full Assessment Workflow")
print("=" * 60)

# Step 1: Get published templates
print("\n1. Getting published templates...")
templates = requests.get(f'{base_url}/templates/published', headers=headers).json()
print(f"   Found {len(templates)} templates")

if not templates:
    print("ERROR: No templates found!")
    exit(1)

template = templates[0]
print(f"   Using template: {template.get('name')}")

# Step 2: Start a new draft
print("\n2. Starting new draft...")
start_resp = requests.post(
    f'{base_url}/assessment-drafts/start?template_id={template["id"]}',
    headers=headers
)
print(f"   Status: {start_resp.status_code}")

if start_resp.status_code not in [200, 201]:
    print(f"   ERROR: {start_resp.text[:200]}")
    exit(1)

draft = start_resp.json()
print(f"   Draft ID: {draft.get('id')}")
questions = draft.get('questions', [])
print(f"   Questions in draft: {len(questions)}")

if not questions:
    print("ERROR: Draft has no questions!")
    exit(1)

# Step 3: Generate answers with REAL question IDs
print("\n3. Generating answers with real question IDs...")
answers = {}
for i, q in enumerate(questions):
    q_id = q.get('id')
    if not q_id:
        continue
    if q.get('question_type') == 'multiple_choice' and q.get('options'):
        opts = q['options']
        answers[q_id] = opts[0].get('option_text', f'Option {i}')
    else:
        answers[q_id] = f"Test answer for question {i+1}. This is a thoughtful response."

print(f"   Generated {len(answers)} answers")
print(f"   Sample answer key: {list(answers.keys())[0]}")

# Step 4: Save the draft
print("\n4. Saving draft...")
save_resp = requests.patch(
    f'{base_url}/assessment-drafts/{draft["id"]}',
    headers=headers,
    json={'answers': answers}
)
print(f"   Status: {save_resp.status_code}")
if save_resp.status_code >= 400:
    print(f"   ERROR: {save_resp.text[:200]}")
    exit(1)

# Step 5: Submit the assessment
print("\n5. Submitting assessment...")
submit_resp = requests.post(
    f'{base_url}/assessment-drafts/submit?draft_id={draft["id"]}',
    headers=headers
)
print(f"   Status: {submit_resp.status_code}")
if submit_resp.status_code >= 400:
    print(f"   Response: {submit_resp.text[:300]}")
else:
    result = submit_resp.json()
    print(f"   Assessment ID: {result.get('id', 'unknown')}")
    print(f"   Status: {result.get('status', 'unknown')}")

print("\n" + "=" * 60)
if submit_resp.status_code < 400:
    print("SUCCESS! Full workflow completed.")
else:
    print("FAILED - check the error above")
print("=" * 60)
