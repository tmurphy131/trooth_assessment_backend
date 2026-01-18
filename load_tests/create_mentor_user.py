#!/usr/bin/env python3
"""Create a mentor user for load testing."""

import requests

API_KEY = 'AIzaSyDTzy7Z-LaX4wC1EH3k-MR4sbH2hiIFmAE'
BACKEND_URL = 'https://trooth-backend-dev-ignpknnbva-uk.a.run.app'

email = 'loadtest-mentor@test.com'
password = 'TestPassword123!'

def main():
    # Try to sign up first
    signup_url = f'https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={API_KEY}'
    resp = requests.post(signup_url, json={
        'email': email,
        'password': password,
        'returnSecureToken': True
    })
    
    if resp.status_code == 200:
        data = resp.json()
        print(f'✅ Created Firebase user: {email}')
        print(f'   UID: {data["localId"]}')
        token = data['idToken']
    else:
        error = resp.json().get('error', {})
        if 'EMAIL_EXISTS' in str(error):
            print(f'User {email} already exists in Firebase, signing in...')
            signin_url = f'https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={API_KEY}'
            signin_resp = requests.post(signin_url, json={
                'email': email,
                'password': password,
                'returnSecureToken': True
            })
            if signin_resp.status_code == 200:
                data = signin_resp.json()
                token = data['idToken']
                print(f'✅ Signed in existing user')
            else:
                print(f'❌ Sign-in failed: {signin_resp.text}')
                return
        else:
            print(f'❌ Firebase signup failed: {error}')
            return
    
    # Register in backend as mentor
    backend_resp = requests.post(
        f'{BACKEND_URL}/users/',
        headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
        json={'role': 'mentor', 'name': 'Load Test Mentor', 'email': email}
    )
    
    if backend_resp.status_code in [200, 201]:
        print(f'✅ Registered in backend as MENTOR')
        print(backend_resp.json())
    elif backend_resp.status_code == 409:
        print(f'✅ User already exists in backend')
        # Verify they're a mentor
        verify_resp = requests.get(
            f'{BACKEND_URL}/mentor/my-apprentices',
            headers={'Authorization': f'Bearer {token}'}
        )
        if verify_resp.status_code == 200:
            print('✅ Confirmed: User is a mentor')
        else:
            print(f'⚠️  User may not be a mentor: {verify_resp.status_code}')
    else:
        print(f'❌ Backend registration failed: {backend_resp.status_code}')
        print(backend_resp.text)

if __name__ == '__main__':
    main()
