#!/usr/bin/env python3
"""
Helper script to get Firebase UID for a user by email.
This is useful for OAuth users who don't have email/password credentials.

Usage:
  python3 get_firebase_uid.py <email>
"""
import os
import sys
import firebase_admin
from firebase_admin import credentials, auth as firebase_auth


def init_firebase_admin():
    """Initialize Firebase Admin SDK if not already initialized."""
    if not firebase_admin._apps:
        # Try to load Firebase credentials
        firebase_cert_path = os.getenv("FIREBASE_CERT_PATH", "firebase_key.json")
        firebase_cert_json = os.getenv("FIREBASE_CERT_JSON")
        
        if firebase_cert_json:
            import json
            cred_dict = json.loads(firebase_cert_json)
            cred = credentials.Certificate(cred_dict)
        elif os.path.exists(firebase_cert_path):
            cred = credentials.Certificate(firebase_cert_path)
        else:
            print(f"ERROR: No Firebase Admin credentials found.")
            print(f"Set FIREBASE_CERT_PATH or FIREBASE_CERT_JSON environment variable.")
            print(f"Default path tried: {firebase_cert_path}")
            sys.exit(1)
        
        firebase_admin.initialize_app(cred)
    return True


def get_user_by_email(email: str):
    """Get Firebase user by email."""
    if not init_firebase_admin():
        sys.exit(1)
    
    try:
        user = firebase_auth.get_user_by_email(email)
        return user
    except firebase_auth.UserNotFoundError:
        print(f"ERROR: No Firebase user found with email: {email}")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Failed to get user: {e}")
        sys.exit(1)


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 get_firebase_uid.py <email>")
        print("Example: python3 get_firebase_uid.py ch0senpriest@gmail.com")
        sys.exit(1)
    
    email = sys.argv[1]
    user = get_user_by_email(email)
    
    print(f"\n✅ Found user: {user.email}")
    print(f"UID: {user.uid}")
    print(f"Display Name: {user.display_name}")
    print(f"Email Verified: {user.email_verified}")
    print(f"Disabled: {user.disabled}")
    print(f"Provider Data:")
    for provider in user.provider_data:
        print(f"  - Provider: {provider.provider_id}")
        print(f"    UID: {provider.uid}")
    
    print(f"\n📋 To use with complete_assessment_via_api.py:")
    print(f"   APPRENTICE_UID={user.uid} python3 complete_assessment_via_api.py")


if __name__ == "__main__":
    main()
