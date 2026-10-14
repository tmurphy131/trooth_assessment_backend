"""Read-only audit of admin accounts (specs/009-critical-auth-holes, SC-006).

Before spec 009, any signed-in user could make themselves admin by re-posting signup. Run this
after the fix ships to spot accounts that shouldn't be admins. It never writes.

Usage:
    DATABASE_URL=postgresql://... python scripts/audit_admin_accounts.py
    DATABASE_URL=postgresql://... python scripts/audit_admin_accounts.py --check-claims

--check-claims also compares each admin's Firebase custom-claim role with the database role.
It needs Firebase credentials (FIREBASE_CERT_JSON or application default credentials).
Emails are masked in the output (Principle V).
"""
from __future__ import annotations

import argparse
import os
import sys

from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import importlib  # noqa: E402
import pkgutil  # noqa: E402

import app.models as _models  # noqa: E402

# Register every model so relationship() targets (e.g. DeviceToken) resolve.
for _m in pkgutil.iter_modules(_models.__path__):
    importlib.import_module(f"app.models.{_m.name}")

from app.models.user import User, UserRole  # noqa: E402


def mask(email: str | None) -> str:
    if not email or "@" not in email:
        return "?"
    local, domain = email.split("@", 1)
    return f"{local[:1]}***@{domain}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check-claims", action="store_true", help="compare Firebase custom claims for admins")
    args = parser.parse_args()

    url = os.getenv("DATABASE_URL")
    if not url:
        print("DATABASE_URL is required", file=sys.stderr)
        return 2
    session = sessionmaker(bind=create_engine(url))()
    try:
        print("Users per role:")
        for role, count in session.query(User.role, func.count(User.id)).group_by(User.role).all():
            print(f"  {role.value if hasattr(role, 'value') else role}: {count}")

        admins = session.query(User).filter(User.role == UserRole.admin).order_by(User.created_at).all()
        print(f"\nAdmin accounts ({len(admins)}):")
        for u in admins:
            print(f"  {u.id}  created={u.created_at}  name={u.name!r}  email={mask(u.email)}")

        if args.check_claims and admins:
            from firebase_admin import auth

            from app.config import init_firebase

            init_firebase()
            print("\nFirebase claim check:")
            for u in admins:
                try:
                    claim = (auth.get_user(u.id).custom_claims or {}).get("role")
                except Exception as e:  # missing Firebase user, permissions
                    claim = f"<error: {type(e).__name__}>"
                flag = "" if claim == "admin" else "   <-- differs"
                print(f"  {u.id}  claim={claim}{flag}")
    finally:
        session.close()
    print("\nReview: every admin above should be a known operator account.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
