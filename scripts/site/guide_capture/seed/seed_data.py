"""Seed the guide test accounts with realistic data on DEV.

    python3 scripts/site/guide_capture/seed/seed_data.py draft      # before capture stage a
    python3 scripts/site/guide_capture/seed/seed_data.py complete   # before capture stage b

draft:    starts a Master T[root]H Assessment draft with the first 6 answers filled in
          (for the "Draft Assessments" and "taking an assessment" shots).
complete: accepts the pending mentor invite, finishes and submits the draft (or a new one),
          waits for AI scoring, submits Spiritual Gifts, adds prayer journal entries (two shared
          with the mentor, one answered), deletes older Master reports so only the newest shows,
          and pre-generates the Premium full reports when the accounts are premium.
"""
import os
import random
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import API, call, login, master_template_id  # noqa: E402

OPEN_ANSWERS = [
    "I'm learning to bring my worries to God in prayer each morning before work, but I still rush it on busy days.",
    "Reading a Psalm with my coffee has become a habit. I want to go deeper than just reading and actually study.",
    "My small group helps me stay honest. I still struggle to share my faith with coworkers because I fear what they'll think.",
    "I notice I'm more patient with my family and quicker to ask for forgiveness than I was a year ago.",
    "Serving on the welcome team has shown me how much I enjoy helping people feel at home at church.",
    "When I'm stressed I tend to try to fix things myself first and pray later. I want prayer to be my first response.",
]
STRONG_GIFTS = {"Q02", "Q42", "Q62", "Q22", "Q55", "Q07", "Q40", "Q66", "Q10", "Q48", "Q30", "Q06", "Q17", "Q50"}
PRAYERS = [
    {"title": "Peace about the new job", "body": "Lord, help me trust you with this transition and do my work as unto you.",
     "category": "request", "scripture_ref": "Philippians 4:6-7", "shared_with_mentor": True},
    {"title": "Mom's recovery", "body": "Thank you for a successful surgery. Please give her strength as she heals.",
     "category": "intercession", "praying_for": "Mom", "scripture_ref": "James 5:15", "shared_with_mentor": True,
     "answered": "Surgery went well and she is home resting."},
    {"title": "Grateful for my small group", "body": "Thank you for people who encourage me and keep me honest.",
     "category": "thanksgiving", "scripture_ref": "Hebrews 10:24-25", "shared_with_mentor": False},
    {"title": "Patience at home", "body": "Forgive me for being short with my family this week. Make me quick to listen.",
     "category": "confession", "scripture_ref": "James 1:19", "shared_with_mentor": False},
]


def answers_for(questions, count=None, accuracy=0.78):
    rng = random.Random(11)
    out = {}
    for n, q in enumerate(questions[:count] if count else questions):
        if q["question_type"] == "multiple_choice":
            correct = next(o["id"] for o in q["options"] if o["is_correct"])
            out[q["id"]] = correct if rng.random() < accuracy else rng.choice(q["options"])["id"]
        else:
            out[q["id"]] = OPEN_ANSWERS[n % len(OPEN_ANSWERS)]
    return out


def start_draft(token):
    s, d = call(f"{API}/assessment-drafts/start?template_id={master_template_id(token)}", {}, token)
    if s != 200:
        sys.exit(f"Could not start draft ({s}) {d}")
    return d


def seed_draft():
    token, _ = login("APPRENTICE")
    d = start_draft(token)
    qs = d["questions"]
    s, _ = call(f"{API}/assessment-drafts/{d['id']}", {"answers": answers_for(qs, 6), "last_question_id": qs[6]["id"]},
                token, method="PATCH")
    print(f"Draft {d['id']}: 6 of {len(qs)} answered ({s})")


def seed_complete():
    token, uid = login("APPRENTICE")
    mentor_token, _ = login("MENTOR")

    s, invites = call(f"{API}/invitations/apprentice-invites?email=guide.apprentice@example.com", token=token)
    for inv in invites if isinstance(invites, list) else []:
        print("Accept invite:", call(f"{API}/invitations/accept-invite", {"token": inv["token"], "apprentice_id": uid}, token)[0])

    d = start_draft(token)  # returns the existing draft if there is one
    qs = d["questions"]
    call(f"{API}/assessment-drafts/{d['id']}", {"answers": answers_for(qs), "last_question_id": qs[-1]["id"]}, token, method="PATCH")
    s, r = call(f"{API}/assessment-drafts/submit?draft_id={d['id']}", {}, token)
    if s != 200:
        sys.exit(f"Submit failed ({s}) {r}")
    aid = r["id"]
    print(f"Submitted {aid}; waiting for AI scoring...")
    for _ in range(60):
        time.sleep(10)
        s, st = call(f"{API}/assessments/{aid}/status", token=token)
        if isinstance(st, dict) and st.get("status") != "processing":
            break
    s, rep = call(f"{API}/progress/reports/{aid}/simplified", token=token)
    print(f"  status={st.get('status')} health={rep.get('health_score')} priority={(rep.get('priority_action') or {}).get('title')!r}")
    if not rep.get("health_score"):
        print("  WARNING: empty report; check the dev backend's LLM provider logs before capturing")

    # Only the newest Master report should appear in Progress and the mentor's list.
    s, reports = call(f"{API}/progress/reports?limit=50", token=token)
    for item in reports.get("items", []) if isinstance(reports, dict) else []:
        rid = item.get("id")
        if rid and rid != aid and item.get("assessment_type") == "master":
            print("  Deleted older report", rid, call(f"{API}/progress/reports/{rid}", token=token, method="DELETE")[0])

    s, g = call(f"{API}/assessments/spiritual-gifts/questions", token=token)
    rng = random.Random(7)
    gift_answers = {it["code"]: (4 if it["code"] in STRONG_GIFTS else rng.choice([1, 2, 2, 3])) for it in g["items"]}
    print("Spiritual gifts:", call(f"{API}/assessments/spiritual-gifts/submit",
                                   {"template_key": "spiritual_gifts_v1", "answers": gift_answers}, token)[0])

    s, existing = call(f"{API}/prayer-journal/entries", token=token)
    have = {e.get("title") for e in existing} if isinstance(existing, list) else set()
    for p in PRAYERS:
        if p["title"] in have:
            continue
        body = {k: v for k, v in p.items() if k != "answered"}
        s, e = call(f"{API}/prayer-journal/entries", body, token)
        print("Prayer:", p["title"], s)
        if p.get("answered") and isinstance(e, dict):
            call(f"{API}/prayer-journal/entries/{e['id']}/answered", {"answer_note": p["answered"]}, token)

    # Premium full reports are generated on first open; warm them so the screens load instantly.
    for label, url, tok in [("apprentice", f"{API}/assessments/{aid}/my-full-report", token),
                            ("mentor", f"{API}/mentor/submitted-drafts/{aid}/full-report", mentor_token)]:
        s, _ = call(url, token=tok, timeout=300)
        print(f"Full report ({label}): {s}" + (" (accounts are not premium)" if s in (402, 403) else ""))


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in ("draft", "complete"):
        sys.exit(__doc__)
    seed_draft() if sys.argv[1] == "draft" else seed_complete()
