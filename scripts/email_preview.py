"""Render every T[root]H email with sample data, and optionally send test copies (specs/005-email-redesign).

    .venv/bin/python scripts/email_preview.py                        # all → ~/.cache/onlyblv/email-previews/
    .venv/bin/python scripts/email_preview.py --only mentor_report,gift_seat
    .venv/bin/python scripts/email_preview.py --send-to you@example.com   # one address only; subjects start [TEST]

Open <out>/index.html to review each email's HTML and plain text. Test sends go through the normal
send path with the SendGrid key from SENDGRID_API_KEY or Secret Manager (never printed); nothing
is sent to anyone but the given address.
"""
from __future__ import annotations

import argparse
import html
import os
import re
import subprocess
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

DEFAULT_OUT = os.path.expanduser("~/.cache/onlyblv/email-previews")
_EMAIL_RE = re.compile(r"^[^@\s,;]+@[^@\s,;]+\.[^@\s,;]+$")


def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--out", default=DEFAULT_OUT)
    p.add_argument("--only", default="", help="comma-separated catalog keys")
    p.add_argument("--send-to", default=None, help="exactly one test address")
    args = p.parse_args(argv)
    if args.send_to is not None and not _EMAIL_RE.match(args.send_to.strip()):
        p.error("--send-to takes exactly one email address (no commas or spaces)")
    return args


def _keys(only: str) -> list[str]:
    from app.services import email_catalog

    keys = [k.strip() for k in only.split(",") if k.strip()] or sorted(email_catalog.CATALOG)
    unknown = [k for k in keys if k not in email_catalog.CATALOG]
    if unknown:
        raise SystemExit(f"Unknown email keys: {', '.join(unknown)}")
    return keys


def render_all(out_dir: str, keys: list[str] | None = None) -> list[str]:
    """Write <key>.html and <key>.txt for each email plus index.html. Returns the keys that failed."""
    from app.services import email_catalog

    os.makedirs(out_dir, exist_ok=True)
    rows, failures, timings = [], [], []
    for key in keys or sorted(email_catalog.CATALOG):
        entry = email_catalog.get(key)
        try:
            start = time.perf_counter()
            rendered = email_catalog.render(key, user_id="preview-user")
            timings.append(time.perf_counter() - start)
        except Exception as e:  # report and keep going
            failures.append(key)
            rows.append(f"<tr><td>{key}</td><td colspan=4 style='color:#f87171'>FAILED: {html.escape(str(e))}</td></tr>")
            continue
        with open(os.path.join(out_dir, f"{key}.html"), "w", encoding="utf-8") as f:
            f.write(rendered.html)
        with open(os.path.join(out_dir, f"{key}.txt"), "w", encoding="utf-8") as f:
            f.write(rendered.text)
        rows.append(f"<tr><td><a href='{key}.html'>{key}</a></td><td>{entry.category}</td>"
                    f"<td>{html.escape(rendered.preheader)}</td><td>{rendered.size_bytes // 1024} KB</td>"
                    f"<td><a href='{key}.txt'>text</a></td></tr>")
    avg_ms = (sum(timings) / len(timings) * 1000) if timings else 0
    with open(os.path.join(out_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write("<!doctype html><meta charset=utf-8><title>T[root]H email previews</title>"
                "<style>body{font-family:system-ui;background:#111;color:#eee;padding:24px}a{color:#e8c547}"
                "td,th{padding:6px 10px;border-bottom:1px solid #333;text-align:left}</style>"
                f"<h1>T[root]H email previews</h1><p>{len(rows)} emails · {len(failures)} failed · "
                f"avg render {avg_ms:.0f} ms</p><table><tr><th>Email</th><th>Category</th><th>Preheader</th>"
                f"<th>Size</th><th>Text</th></tr>{''.join(rows)}</table>")
    print(f"Rendered {len(rows) - len(failures)}/{len(rows)} emails to {out_dir} (avg {avg_ms:.0f} ms each)")
    return failures


def _ensure_sendgrid_key() -> None:
    if os.getenv("SENDGRID_API_KEY") and os.getenv("SENDGRID_API_KEY") != "your_sendgrid_api_key_here":
        return
    key = subprocess.run(["gcloud", "secrets", "versions", "access", "latest", "--secret=SENDGRID_API_KEY"],
                         capture_output=True, text=True, check=True).stdout.strip()
    os.environ["SENDGRID_API_KEY"] = key


def send_previews(address: str, keys: list[str]) -> int:
    """Send each email to ``address`` only, subject prefixed [TEST]. Returns the number sent."""
    from app.services import email as email_svc
    from app.services import email_catalog

    if not _EMAIL_RE.match(address.strip()):
        raise ValueError("send_previews takes exactly one email address")
    sent = 0
    for key in keys:
        entry = email_catalog.get(key)
        rendered = email_catalog.render(key, user_id="preview-user")
        subject = f"[TEST] {key}: {entry.preheader_for(entry.sample_context())}"[:150]
        if email_svc.send_email(address.strip(), subject, rendered.html, rendered.text,
                                category=entry.category, headers=rendered.headers):
            sent += 1
    print(f"Sent {sent}/{len(keys)} test emails to {address}")
    return sent


def main(argv=None) -> int:
    args = parse_args(argv)
    keys = _keys(args.only)
    failures = render_all(args.out, keys)
    if failures:
        print("Failed:", ", ".join(failures))
        return 1
    if args.send_to:
        os.environ.setdefault("ENV", "development")
        _ensure_sendgrid_key()
        send_previews(args.send_to, keys)
    return 0


if __name__ == "__main__":
    sys.exit(main())
