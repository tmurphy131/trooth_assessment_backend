import os
import json
import firebase_admin
from firebase_admin import credentials


def init_firebase():
    """Initialize Firebase admin SDK.

    Behavior:
    - If FIREBASE_CERT_JSON env var is present, parse it as JSON and use it.
    - Else if FIREBASE_CERT_PATH env var is set or file 'firebase_key.json' exists, use that path.
    - Else, do nothing (avoid raising at import time).
    """
    fb_json = os.environ.get("FIREBASE_CERT_JSON")
    if fb_json:
        try:
            cred_dict = json.loads(fb_json)
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred)
            return
        except Exception as e:
            # Fall through to file-based loading which may still work
            print(f"Failed to init Firebase from FIREBASE_CERT_JSON: {e}")

    fb_path = os.environ.get("FIREBASE_CERT_PATH", "firebase_key.json")
    if fb_path and os.path.exists(fb_path):
        try:
            cred = credentials.Certificate(fb_path)
            firebase_admin.initialize_app(cred)
            return
        except Exception as e:
            print(f"Failed to init Firebase from path {fb_path}: {e}")

    # No credential available; skip initialization to avoid crashing the process.
    print("No Firebase credentials found; skipping Firebase initialization.")