"""Email redesign (specs/005-email-redesign).

Shared layout, render pipeline and catalog coverage, unsubscribe links/endpoints/gating, report
parity and the preview tool. SendGrid is never called.
"""
import os
import re

import pytest

from app.core.settings import settings
from app.services import email_catalog
from app.services.email_render import render_email

EMAIL_DIR = os.path.join(os.path.dirname(__file__), "..", "app", "templates", "email")
SECRET = "test-email-link-secret"


@pytest.fixture
def link_secret(monkeypatch):
    monkeypatch.setattr(settings, "email_link_secret", SECRET)
    return SECRET


# ---------------------------------------------------------------------------
# Render pipeline (T004)
# ---------------------------------------------------------------------------

def test_render_inlines_css_builds_text_and_hides_preheader():
    r = render_email("campaigns/welcome_mentor.html", {"name": "Marcus"}, preheader="Welcome aboard",
                     reason="You created an account.")
    assert '<meta name="color-scheme" content="dark">' in r.html
    assert re.search(r'<div style="display:none;[^>]*>Welcome aboard', r.html)
    # <style> rules (.muted) are inlined onto elements so stripped <style> blocks don't matter
    assert re.search(r'class="muted"[^>]*style="[^"]*color: ?#a3a3a3', r.html)
    assert "<" not in r.text.replace("<https", "").replace("<mailto", "")
    assert "Welcome aboard" not in r.text  # preheader isn't repeated in the text part
    assert r.size_bytes < 102_400


def test_footer_has_both_store_links_and_reason():
    r = render_email("campaigns/welcome_mentor.html", {"name": "Marcus"}, reason="Because you signed up.")
    assert "data-trooth-footer" in r.html
    assert settings.ios_app_store_url in r.html and settings.android_play_store_url in r.html
    assert "Because you signed up." in r.html and settings.support_email in r.html


def test_button_macro_has_outlook_vml_and_fallback_link(tmp_path):
    from app.services.email import get_email_template_env

    env = get_email_template_env()
    html = env.from_string('{% import "_macros.html" as m %}{{ m.button("https://x.test/go", "Open in app") }}').render()
    assert "<!--[if mso]>" in html and "v:roundrect" in html and 'href="https://x.test/go"' in html
    assert html.count("Open in app") == 2  # VML label + fallback link


# ---------------------------------------------------------------------------
# Catalog coverage (T005)
# ---------------------------------------------------------------------------

def _template_files():
    files = set()
    for dirpath, _, names in os.walk(EMAIL_DIR):
        for name in names:
            if name.endswith(".html") and not name.startswith("_"):  # _partials are included, not sent
                files.add(os.path.relpath(os.path.join(dirpath, name), EMAIL_DIR))
    return files - {"_base.html", "_macros.html"}


def test_every_template_is_in_the_catalog_exactly_once():
    templates = [e.template for e in email_catalog.CATALOG.values()]
    assert len(templates) == len(set(templates))
    assert _template_files() == set(templates)


@pytest.mark.parametrize("key", sorted(email_catalog.CATALOG))
def test_every_catalog_email_renders_on_the_shared_layout(key, link_secret):
    entry = email_catalog.get(key)
    r = email_catalog.render(key, user_id="user-1")
    assert 1 <= len(r.preheader) <= 110
    assert "data-trooth-footer" in r.html and r.text.strip()
    assert r.size_bytes < 95_000
    has_unsub = "/email/unsubscribe?t=" in r.html
    if entry.category == email_catalog.ENGAGEMENT:
        assert has_unsub and r.headers.get("List-Unsubscribe-Post") == "List-Unsubscribe=One-Click"
    else:
        assert not has_unsub and not r.headers


# ---------------------------------------------------------------------------
# US1: unsubscribe links, endpoints and gating
# ---------------------------------------------------------------------------
import time
from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.models import User
from app.models.email_send_event import EmailSendEvent
from app.services import email as email_svc
from app.services import email_links

client = TestClient(app)


def test_tokens_round_trip_and_reject_tampering(link_secret, monkeypatch):
    token = email_links.make_token("user-1")
    assert email_links.verify_token(token) == "user-1"
    flipped = token[:-1] + ("A" if token[-1] != "A" else "B")
    assert email_links.verify_token(flipped) is None
    assert email_links.verify_token("v2" + token[2:]) is None
    assert email_links.verify_token(token.replace("user-1", "user-2")) is None
    old = email_links.make_token("user-1", now=time.time() - 401 * 86400)
    assert email_links.verify_token(old) is None
    future = email_links.make_token("user-1", now=time.time() + 3600)
    assert email_links.verify_token(future) is None
    monkeypatch.setattr(settings, "email_link_secret", "a-different-secret")
    assert email_links.verify_token(token) is None


def test_no_secret_means_no_links(monkeypatch):
    monkeypatch.setattr(settings, "email_link_secret", "")
    assert email_links.make_token("user-1") is None and email_links.list_unsubscribe_headers("user-1") == {}
    r = email_catalog.render("draft_reminder", user_id="user-1")
    assert "/email/unsubscribe" not in r.html and not r.headers


def test_unsubscribe_urls_use_the_api_host(link_secret, monkeypatch):
    monkeypatch.setattr(settings, "backend_api_url", "https://api.example.test/")
    page, one_click = email_links.unsubscribe_urls("user-1")
    assert page.startswith("https://api.example.test/email/unsubscribe?t=v1.user-1.")
    assert one_click.startswith("https://api.example.test/email/unsubscribe/one-click?t=")
    headers = email_links.list_unsubscribe_headers("user-1")
    assert headers["List-Unsubscribe-Post"] == "List-Unsubscribe=One-Click"
    assert one_click in headers["List-Unsubscribe"] and "mailto:" in headers["List-Unsubscribe"]


@pytest.fixture
def member(db_session):
    user = User(id=str(uuid4()), name="Jordan", email=f"j{uuid4().hex[:6]}@example.com", role="apprentice")
    db_session.add(user)
    db_session.commit()
    return user


def _reload(db_session, user):
    db_session.expire_all()
    return db_session.get(User, user.id)


def test_confirm_page_has_no_side_effects(link_secret, member, db_session):
    token = email_links.make_token(member.id)
    r = client.get(f"/email/unsubscribe?t={token}")
    assert r.status_code == 200 and 'action="/email/unsubscribe"' in r.text
    assert _reload(db_session, member).email_opt_out is False


def test_unsubscribe_resubscribe_and_repeat(link_secret, member, db_session):
    token = email_links.make_token(member.id)
    form = {"Content-Type": "application/x-www-form-urlencoded"}
    r = client.post("/email/unsubscribe", content=f"t={token}", headers=form)
    assert r.status_code == 200 and "unsubscribed" in r.text
    u = _reload(db_session, member)
    assert u.email_opt_out is True and u.email_pref_source == "link" and u.email_pref_changed_at
    assert client.post("/email/unsubscribe", content=f"t={token}", headers=form).status_code == 200
    assert "already unsubscribed" in client.get(f"/email/unsubscribe?t={token}").text

    r = client.post("/email/resubscribe", content=f"t={token}", headers=form)
    assert r.status_code == 200
    u = _reload(db_session, member)
    assert u.email_opt_out is False and u.email_pref_source == "resubscribe"


def test_one_click_unsubscribes_immediately(link_secret, member, db_session):
    token = email_links.make_token(member.id)
    r = client.post(f"/email/unsubscribe/one-click?t={token}", content="List-Unsubscribe=One-Click",
                    headers={"Content-Type": "application/x-www-form-urlencoded"})
    assert r.status_code == 200 and r.content == b""
    u = _reload(db_session, member)
    assert u.email_opt_out is True and u.email_pref_source == "one_click"


def test_invalid_tokens_change_nothing(link_secret, member, db_session):
    bad = email_links.make_token(member.id)[:-2] + "xx"
    form = {"Content-Type": "application/x-www-form-urlencoded"}
    assert client.get(f"/email/unsubscribe?t={bad}").status_code == 400
    assert client.post("/email/unsubscribe", content=f"t={bad}", headers=form).status_code == 400
    assert client.post(f"/email/unsubscribe/one-click?t={bad}").status_code == 400
    assert client.post("/email/resubscribe", content=f"t={bad}", headers=form).status_code == 400
    ghost = email_links.make_token("no-such-user")
    assert client.get(f"/email/unsubscribe?t={ghost}").status_code == 400
    assert _reload(db_session, member).email_opt_out is False
    assert member.email not in client.get(f"/email/unsubscribe?t={bad}").text


def test_legacy_settings_link_no_longer_404s():
    r = client.get("/settings/notifications")
    assert r.status_code == 200 and settings.support_email in r.text


@pytest.fixture
def sent(monkeypatch):
    calls = []
    monkeypatch.setattr(email_svc, "send_email",
                        lambda to, subject, html, text, **kw: calls.append(SimpleNamespace(
                            to=to, subject=subject, html=html, text=text, **kw)) or True)
    return calls


def _events(db_session, user):
    return db_session.query(EmailSendEvent).filter_by(target_user_id=user.id).all()


def _draft():
    return SimpleNamespace(id="draft-1", answers={"q1": "a"},
                           template=SimpleNamespace(name="Master T[root]H Assessment", questions=[1, 2, 3, 4]))


def test_engagement_email_carries_unsubscribe_and_headers(link_secret, member, db_session, sent):
    assert email_svc.send_draft_reminder_email(db_session, member, _draft(), "Marcus", 3) is True
    msg = sent[0]
    assert msg.category == "engagement"
    assert msg.headers["List-Unsubscribe-Post"] == "List-Unsubscribe=One-Click"
    assert "/email/unsubscribe?t=" in msg.html and "/settings/notifications" not in msg.html
    assert _events(db_session, member)[0].delivery_status == "sent"


def test_opted_out_users_get_no_engagement_email_but_still_get_transactional(
        link_secret, member, db_session, sent, caplog):
    member.email_opt_out = True
    db_session.commit()
    with caplog.at_level("INFO"):
        assert email_svc.send_draft_reminder_email(db_session, member, _draft(), "Marcus", 3) is False
        assert email_svc.send_new_template_email(db_session, member, SimpleNamespace(
            id="t1", name="New One", description=None, category=None, estimated_minutes=10)) is False
        assert email_svc.send_inactive_reengagement_email(db_session, member, 30) is False
        assert email_svc.send_welcome_email(db_session, member) is False
    assert sent == []
    statuses = {(e.campaign_type, e.delivery_status) for e in _events(db_session, member)}
    assert statuses == {("draft_reminder", "skipped_opt_out"), ("new_template", "skipped_opt_out"),
                        ("inactive_reengagement", "skipped_opt_out"), ("welcome", "skipped_opt_out")}
    assert "email_skipped_opt_out campaign=draft_reminder" in caplog.text
    # The skip counts as handled, so the reminder isn't retried every run
    assert email_svc._already_sent_campaign(db_session, member.id, "draft_reminder", "draft_id", "draft-1")

    # Transactional mail still goes out
    html, text = email_svc.render_mentor_report_v2_email(email_catalog.sample_report_context())
    assert email_svc.send_email(member.email, "Report", html, text) is True
    assert len(sent) == 1


# ---------------------------------------------------------------------------
# US2: report emails lead with the same numbers as the app
# ---------------------------------------------------------------------------
from app.models import Assessment
from app.services.auth import verify_token as _verify_token


def _blob(**overrides):
    blob = email_catalog.sample_blob()
    blob.update(overrides)
    return blob


def _ctx(blob):
    from app.services.master_trooth_report import build_report_context

    return build_report_context({"apprentice": {"id": "p1", "name": "Jordan Davis"}, "template_id": "t",
                                 "created_at": None}, {"overall_score": 8}, blob)


def _assert_headline(text):
    assert "80" in text and "Maturing" in text and "86.2%" in text


def test_mentor_and_premium_emails_match_the_canonical_numbers():
    ctx = _ctx(_blob())
    html, text = email_svc.render_mentor_report_v2_email(ctx)
    _assert_headline(text)
    assert "Establish an unhurried morning rhythm" in text and "Reads a Psalm every morning" in text
    assert settings.app_landing_url in html

    stale = email_catalog.sample_full_report()
    stale["executive_summary"] = dict(stale["executive_summary"], health_score=99, health_band="Flourishing")
    html, text = email_svc.render_premium_report_email(ctx, stale)
    _assert_headline(text)
    assert "99" not in text and "Flourishing" not in text
    assert "Strong devotional habits" in text  # executive summary
    assert "Weeks 1–4: Pray for five coworkers by name" in text  # 12-week plan highlights


def test_master_and_assessment_complete_emails_lead_with_the_health_score():
    scores = {"overall_score": 8, "mentor_blob_v2": _blob(), "top3": [{"category": "Bible Study", "score": 9}]}
    _, text = email_svc.render_master_trooth_email("Jordan Davis", scores, settings.app_url)
    _assert_headline(text)
    _, text = email_svc.render_assessment_completion_email("Marcus", "Jordan Davis", scores, {})
    _assert_headline(text)


def test_missing_sections_are_left_out():
    ctx = _ctx(_blob(priority_action=None, strengths=[], gaps=[]))
    _, text = email_svc.render_mentor_report_v2_email(ctx)
    assert "Priority Action" not in text and "Top strengths" not in text and "Growth areas" not in text
    _assert_headline(text)


def test_reports_without_a_blob_fall_back_to_their_own_scores():
    _, text = email_svc.render_generic_assessment_email("Disciplines", "Jordan", {
        "overall_score": 7, "category_scores": {"Prayer": 8}, "summary_recommendation": "Keep going"})
    assert "Health Score" not in text and "7/10" in text and "Prayer" in text


def test_spiritual_gifts_email_leads_with_top_gifts():
    defs = {"teaching": {"display_name": "Teaching", "short_summary": "Explaining God's Word clearly."}}
    _, text = email_svc.render_spiritual_gifts_report_email("Jordan", 1, {
        "top_gifts_truncated": [{"gift": "Teaching", "score": 18}, {"gift": "Mercy", "score": 15}],
        "all_scores": [{"gift": "Teaching", "score": 18}, {"gift": "Mercy", "score": 15}]}, defs, settings.app_url)
    assert text.index("1. Teaching") < text.index("All gifts")
    assert "Explaining God's Word clearly." in text


def test_mentor_report_preview_route_shows_the_new_email(db_session, member):
    a = Assessment(id=str(uuid4()), apprentice_id=member.id, template_id="t", answers={}, status="done",
                   scores={"overall_score": 8}, mentor_report_v2=_blob())
    db_session.add(a)
    db_session.commit()
    previous = app.dependency_overrides.get(_verify_token)  # other test modules set this at import
    app.dependency_overrides[_verify_token] = lambda: {"uid": member.id}
    try:
        r = client.get(f"/assessments/{a.id}/mentor-report-v2")
    finally:
        if previous is None:
            app.dependency_overrides.pop(_verify_token, None)
        else:
            app.dependency_overrides[_verify_token] = previous
    assert r.status_code == 200 and "Health Score" in r.text and "data-trooth-footer" in r.text


# ---------------------------------------------------------------------------
# US4: preview tool
# ---------------------------------------------------------------------------
import importlib.util

_spec = importlib.util.spec_from_file_location(
    "email_preview", os.path.join(os.path.dirname(__file__), "..", "scripts", "email_preview.py"))
email_preview = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(email_preview)


def test_preview_renders_every_email(tmp_path):
    assert email_preview.render_all(str(tmp_path)) == []
    for key in email_catalog.CATALOG:
        assert (tmp_path / f"{key}.html").exists() and (tmp_path / f"{key}.txt").exists()
    index = (tmp_path / "index.html").read_text()
    assert "0 failed" in index and all(k in index for k in email_catalog.CATALOG)


@pytest.mark.parametrize("argv", [["--send-to", "a@x.com,b@x.com"], ["--send-to", "a@x.com", "b@x.com"],
                                  ["--send-to", "not-an-email"]])
def test_preview_refuses_anything_but_one_address(argv):
    with pytest.raises(SystemExit):
        email_preview.parse_args(argv)


def test_preview_sends_only_to_the_test_address(sent):
    assert email_preview.send_previews("tester@example.com", ["mentor_report", "draft_reminder"]) == 2
    assert {m.to for m in sent} == {"tester@example.com"}
    assert all(m.subject.startswith("[TEST] ") for m in sent)
    with pytest.raises(ValueError):
        email_preview.send_previews("a@x.com, b@x.com", ["mentor_report"])
