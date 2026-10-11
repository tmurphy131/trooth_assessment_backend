"""Create (or reuse) the guide test accounts on DEV and leave a pending mentor invitation.

    python3 scripts/site/guide_capture/seed/create_accounts.py

Mentor "Marcus Johnson" (guide.mentor@example.com) and apprentice "Jordan Davis"
(guide.apprentice@example.com): Firebase Auth user (only-blv project, shared with prod auth),
dev backend user row, and the Firestore users/{uid} doc the app reads the role from.
Passwords are generated once and kept in ~/.config/onlyblv/test_accounts.env (chmod 600).
Safe to rerun.
"""
import os
import secrets
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import ACCOUNTS, ACCOUNTS_FILE, API, FIREBASE_PROJECT, call, firebase, read_passwords  # noqa: E402


def main():
    env = read_passwords()
    tokens = {}
    for role, acct in ACCOUNTS.items():
        password = env.get(f"{role}_PASSWORD") or ("Guide-" + secrets.token_urlsafe(12))
        s, d = firebase("signUp", acct["email"], password)
        if s != 200:
            s, d = firebase("signInWithPassword", acct["email"], password)
        if s != 200:
            sys.exit(f"{role}: Firebase sign-up/sign-in failed ({s}) {d}")
        token, uid = d["idToken"], d["localId"]
        tokens[role] = token
        env[f"{role}_EMAIL"], env[f"{role}_PASSWORD"] = acct["email"], password

        s, _ = call(f"{API}/users/", {"id": uid, "name": acct["name"], "email": acct["email"], "role": acct["role"]}, token)
        print(f"{role}: backend user {s}")

        first, last = acct["name"].split(" ", 1)
        fields = {k: {"stringValue": v} for k, v in
                  {"name": acct["name"], "first_name": first, "last_name": last,
                   "email": acct["email"], "role": acct["role"]}.items()}
        fields["onboarded"] = {"booleanValue": True}
        mask = "&".join(f"updateMask.fieldPaths={k}" for k in fields)  # leave other fields (created_at) alone
        s, _ = call(f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT}/databases/(default)/documents/users/{uid}?{mask}",
                    {"fields": fields}, token, method="PATCH")
        print(f"{role}: Firestore role doc {s}")

    fd = os.open(ACCOUNTS_FILE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write("".join(f"{k}={v}\n" for k, v in env.items()))

    apprentice = ACCOUNTS["APPRENTICE"]
    s, linked = call(f"{API}/mentor/my-apprentices", token=tokens["MENTOR"])
    if isinstance(linked, list) and any(a.get("email") == apprentice["email"] for a in linked):
        print("Mentor invite: skipped, the accounts are already linked")
        return
    s, _ = call(f"{API}/invitations/invite-apprentice",
                {"apprentice_email": apprentice["email"], "apprentice_name": apprentice["name"]}, tokens["MENTOR"])
    print(f"Mentor invite: {s} (a pending invite returns an error; that's fine)")


if __name__ == "__main__":
    main()
