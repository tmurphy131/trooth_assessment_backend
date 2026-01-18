#!/usr/bin/env python3
"""
Get Firebase ID token for load testing.
Usage: python get_test_token.py
"""
import requests
import sys

FIREBASE_API_KEY = "AIzaSyDTzy7Z-LaX4wC1EH3k-MR4sbH2hiIFmAE"

# Test user credentials - UPDATE THESE
TEST_EMAIL = "loadtest@test.com"
TEST_PASSWORD = "TestPassword123!"  # <-- Update this!

def get_firebase_token(email: str, password: str) -> str:
    """Sign in via Firebase REST API and return ID token."""
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
        print(f"❌ ERROR: Firebase sign-in failed: {error_message}")
        sys.exit(1)
    
    data = response.json()
    token = data.get("idToken")
    print(f"✅ Token obtained! (expires in 1 hour)")
    return token

if __name__ == "__main__":
    if TEST_PASSWORD == "YOUR_PASSWORD_HERE":
        print("❌ ERROR: Please update TEST_PASSWORD in this script!")
        print("   Edit load_tests/get_test_token.py and set your password.")
        sys.exit(1)
    
    token = get_firebase_token(TEST_EMAIL, TEST_PASSWORD)
    print("\n" + "="*60)
    print("FIREBASE ID TOKEN (copy this):")
    print("="*60)
    print(token)
    print("="*60)
    print("\nTo run the load test:")
    print(f'export AUTH_TOKEN="{token[:50]}..."')
    print('k6 run load_tests/infrastructure_test.js -e AUTH_TOKEN="$AUTH_TOKEN"')
