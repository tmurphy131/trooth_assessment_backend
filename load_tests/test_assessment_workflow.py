#!/usr/bin/env python3
"""Test the assessment workflow manually."""

import requests

API_KEY = 'AIzaSyDTzy7Z-LaX4wC1EH3k-MR4sbH2hiIFmAE'
BASE_URL = 'https://trooth-backend-dev-ignpknnbva-uk.a.run.app'

def main():
    # Get token
    r = requests.post(
        f'https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={API_KEY}',
        json={'email': 'loadtest@test.com', 'password': 'TestPassword123!', 'returnSecureToken': True}
    )
    token = r.json()['idToken']
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    print('✅ Got auth token')
    
    # Get templates
    templates = requests.get(f'{BASE_URL}/templates/published', headers=headers).json()
    print(f'✅ Found {len(templates)} templates')
    template_id = templates[0]['id']
    print(f'   Using template: {template_id}')
    
    # Start a draft (as query parameter)
    resp = requests.post(
        f'{BASE_URL}/assessment-drafts/start?template_id={template_id}',
        headers=headers
    )
    print(f'\n📝 Start draft response: {resp.status_code}')
    
    if resp.status_code == 200:
        draft = resp.json()
        print(f'✅ Draft created! ID: {draft["id"]}')
        
        # Try to save the draft
        save_resp = requests.patch(
            f'{BASE_URL}/assessment-drafts/{draft["id"]}',
            headers=headers,
            json={'answers': {'test_q1': 'Test answer from manual test'}}
        )
        print(f'\n💾 Save draft response: {save_resp.status_code}')
        if save_resp.status_code == 200:
            print('✅ Draft saved successfully!')
        else:
            print(f'❌ Save failed: {save_resp.text[:200]}')
            
    else:
        print(f'Response: {resp.json()}')

if __name__ == '__main__':
    main()
