"""Shared helpers for the guide test-account seed scripts (DEV only)."""
import json
import os
import ssl
import urllib.error
import urllib.request

# Public Firebase web API key for the only-blv project (same value ships in the app's firebase_options.dart).
FIREBASE_KEY = "AIzaSyDTzy7Z-LaX4wC1EH3k-MR4sbH2hiIFmAE"
FIREBASE_PROJECT = "only-blv"
API = os.environ.get("GUIDE_API", "https://trooth-discipleship-api-dev.onlyblv.com")
ACCOUNTS_FILE = os.path.expanduser("~/.config/onlyblv/test_accounts.env")
MASTER_TEMPLATE_KEY = "master_trooth_v1"

ACCOUNTS = {
    "MENTOR": {"email": "guide.mentor@example.com", "name": "Marcus Johnson", "role": "mentor"},
    "APPRENTICE": {"email": "guide.apprentice@example.com", "name": "Jordan Davis", "role": "apprentice"},
}

# python.org builds of Python ship without CA certificates; fall back to the macOS bundle.
_ctx = ssl.create_default_context(cafile="/etc/ssl/cert.pem") if os.path.exists("/etc/ssl/cert.pem") else None

if "trooth-discipleship-api.onlyblv.com" in API or "trooth-backend-ignpknnbva" in API:
    raise SystemExit("Refusing to seed guide data against PROD")


def call(url, body=None, token=None, method=None, timeout=180):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method or ("POST" if data is not None else "GET"))
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_ctx) as r:
            text = r.read().decode()
            return r.status, (json.loads(text) if text else None)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:600]


def read_passwords():
    env = {}
    if os.path.exists(ACCOUNTS_FILE):
        with open(ACCOUNTS_FILE) as f:
            for line in f:
                if "=" in line:
                    k, v = line.strip().split("=", 1)
                    env[k] = v
    return env


def firebase(kind, email, password):
    return call(f"https://identitytoolkit.googleapis.com/v1/accounts:{kind}?key={FIREBASE_KEY}",
                {"email": email, "password": password, "returnSecureToken": True})


def login(role):
    """Returns (id_token, uid) for MENTOR or APPRENTICE."""
    env = read_passwords()
    s, d = firebase("signInWithPassword", env[f"{role}_EMAIL"], env[f"{role}_PASSWORD"])
    if s != 200:
        raise SystemExit(f"{role} sign-in failed ({s}); run create_accounts.py first")
    return d["idToken"], d["localId"]


def master_template_id(token):
    s, templates = call(f"{API}/templates/published", token=token)
    for t in templates if isinstance(templates, list) else []:
        if t.get("key") == MASTER_TEMPLATE_KEY:
            return t["id"]
    raise SystemExit(f"Published template {MASTER_TEMPLATE_KEY} not found ({s})")
