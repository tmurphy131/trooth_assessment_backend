"""Find past repeat signups in Cloud Run request logs (specs/009-critical-auth-holes, SC-006).

Before spec 009, re-posting signup (POST /users/) on an existing account could change its role.
Role history isn't stored, and request logs don't carry user ids. So this lists every
POST /users/ that returned 200 in the log window and pairs it with accounts created at that
moment. A 200 with no account created within --window seconds was a repeat signup, which may
have changed a role. Review those by time, IP and user agent. Read-only.

Usage:
    python scripts/find_role_changes_in_logs.py --freshness 30d
    DATABASE_URL=postgresql://... python scripts/find_role_changes_in_logs.py --freshness 30d

Without DATABASE_URL it only lists the requests. Needs `gcloud` signed in with log read access.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta

FILTER = (
    'resource.type="cloud_run_revision" '
    'AND resource.labels.service_name="{service}" '
    'AND httpRequest.requestMethod="POST" '
    'AND httpRequest.status=200 '
    'AND httpRequest.requestUrl=~"/users/?(\\?.*)?$"'
)


def read_logs(service: str, project: str, freshness: str) -> list[dict]:
    cmd = [
        "gcloud", "logging", "read", FILTER.format(service=service),
        f"--project={project}", f"--freshness={freshness}", "--format=json", "--limit=10000",
    ]
    out = subprocess.run(cmd, check=True, capture_output=True, text=True).stdout
    rows = []
    for e in json.loads(out or "[]"):
        req = e.get("httpRequest", {})
        rows.append({
            "ts": datetime.fromisoformat(e["timestamp"].replace("Z", "+00:00")).replace(tzinfo=None),
            "ip": req.get("remoteIp", "?"),
            "agent": (req.get("userAgent") or "?")[:40],
            "trace": (e.get("trace") or "").rsplit("/", 1)[-1][:16],
        })
    return sorted(rows, key=lambda r: r["ts"])


def created_times(url: str, since: datetime) -> list[datetime]:
    from sqlalchemy import create_engine, text

    with create_engine(url).connect() as conn:
        rs = conn.execute(text("SELECT created_at FROM users WHERE created_at >= :since"), {"since": since})
        return [r[0].replace(tzinfo=None) for r in rs if r[0]]


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--service", default="trooth-backend")
    p.add_argument("--project", default="trooth-prod")
    p.add_argument("--freshness", default="30d", help="gcloud --freshness, e.g. 30d")
    p.add_argument("--window", type=int, default=15, help="seconds to match a request to a new account")
    args = p.parse_args()

    rows = read_logs(args.service, args.project, args.freshness)
    print(f"POST /users/ -> 200 in the last {args.freshness}: {len(rows)}")
    url = os.getenv("DATABASE_URL")
    if not url or not rows:
        for r in rows:
            print(f"  {r['ts']:%Y-%m-%d %H:%M:%S}  ip={r['ip']}  agent={r['agent']}  trace={r['trace']}")
        if rows and not url:
            print("\nSet DATABASE_URL to separate new signups from repeat signups.")
        return 0

    created = created_times(url, rows[0]["ts"] - timedelta(minutes=5))
    window = timedelta(seconds=args.window)
    repeats = [r for r in rows if not any(abs(c - r["ts"]) <= window for c in created)]
    print(f"New signups: {len(rows) - len(repeats)}   Repeat signups (possible role change): {len(repeats)}")
    for r in repeats:
        print(f"  {r['ts']:%Y-%m-%d %H:%M:%S}  ip={r['ip']}  agent={r['agent']}  trace={r['trace']}")
    print("\nA few repeats are normal (role-selection retries). Look for bursts, unknown IPs or")
    print("non-app user agents, and compare with scripts/audit_admin_accounts.py output.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
