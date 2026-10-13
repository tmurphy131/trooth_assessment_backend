"""Every email the system sends (specs/005-email-redesign, data-model EmailType).

Each entry names its template, category (engagement emails can be unsubscribed from; transactional
always send; internal go to staff), inbox preview line, footer reason and realistic sample data.
The preview script and tests/test_email_redesign.py iterate this catalog, so a new email type
must be registered here.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Union

ENGAGEMENT = "engagement"
TRANSACTIONAL = "transactional"
INTERNAL = "internal"

Preheader = Union[str, Callable[[dict], str]]


@dataclass(frozen=True)
class EmailType:
    key: str
    template: str
    category: str
    preheader: Preheader
    reason: str
    sample_context: Callable[[], dict[str, Any]]

    def preheader_for(self, context: dict) -> str:
        text = self.preheader(context) if callable(self.preheader) else self.preheader
        return text[:110]


# ---------------------------------------------------------------------------
# Sample data
# ---------------------------------------------------------------------------

def sample_blob() -> dict:
    return {
        "health_score": 80, "health_band": "Maturing",
        "strengths": ["Reads a Psalm every morning", "Honest in small group", "Growing patience at home"],
        "gaps": ["Sharing faith at work", "Rushed prayer on busy days", "Scripture memory"],
        "priority_action": {"title": "Establish an unhurried morning rhythm",
                            "description": "Ten unhurried minutes before work will deepen prayer and study.",
                            "steps": ["Set the alarm 15 minutes earlier", "Journal one worry and hand it to God",
                                      "Read one Psalm slowly twice"],
                            "scripture": "Psalm 5:3"},
        "biblical_knowledge": {"percent": 86.2, "weak_topics": ["Pentateuch"],
                               "study_recommendation": "Read Genesis 12-25 this month."},
        "insights": [{"category": "Prayer Life", "level": "Maturing", "observation": "Prays most mornings.",
                      "next_step": "Add five minutes of intercession."}],
        "flags": {"red": [], "yellow": ["Isolated at work"], "green": ["Hungry to grow"]},
        "four_week_plan": {"rhythm": ["Week 1: morning prayer"], "checkpoints": ["Prayed 5 mornings"]},
        "conversation_starters": ["Where did you see God this week?"],
        "recommended_resources": [{"title": "Praying the Bible", "why": "A simple way to pray Scripture.",
                                   "type": "book"}],
    }


def sample_report_context() -> dict:
    """Context shaped like master_trooth_report.build_report_context plus the canonical summary."""
    from app.services.master_trooth_report import build_report_context
    from app.services.report_summary import summarize_mentor_blob

    blob = sample_blob()
    ctx = build_report_context({"apprentice": {"id": "p1", "name": "Jordan Davis"}, "template_id": "master",
                                "created_at": None},
                               {"overall_score": 8, "category_scores": {"Prayer Life": 8, "Bible Study": 9}}, blob)
    ctx["summary"] = summarize_mentor_blob(blob)
    ctx["blob"] = blob
    ctx.setdefault("apprentice_name", "Jordan Davis")
    return ctx


def sample_full_report() -> dict:
    phase = {"goal": "Pray for five coworkers by name", "activities": ["List five names"], "success_metric": "Daily"}
    return {
        "executive_summary": {"health_score": 80, "health_band": "Maturing",
                              "one_liner": "Strong devotional habits; growing courage to share faith.",
                              "trajectory": "upward", "trajectory_note": "Steady growth in daily faithfulness."},
        "strengths_deep_dive": [{"area": "Prayer Life", "summary": "Consistent mornings", "evidence": ["Daily Psalm"],
                                 "spiritual_maturity_indicator": "Psalm 5:3", "how_to_leverage": "Lead prayer",
                                 "celebration_talking_point": "Ask about an answered prayer"}],
        "gaps_deep_dive": [{"area": "Evangelism", "summary": "Avoids faith talks at work", "severity": "moderate",
                            "root_cause_analysis": "Fear of rejection", "evidence": ["Hasn't shared in months"],
                            "biblical_perspective": "2 Timothy 1:7", "why_it_matters": "Faith grows when shared",
                            "growth_pathway": {"phase_1_weeks_1_4": phase,
                                               "phase_2_weeks_5_8": dict(phase, goal="Share your story with your mentor"),
                                               "phase_3_weeks_9_12": dict(phase, goal="One spiritual conversation")}}],
        "biblical_knowledge_analysis": {"overall_percent": 86.2, "mastery_level": "Advanced",
                                        "by_topic_breakdown": []},
        "conversation_guide": {"session_1_opening": {"theme": "Celebrate", "duration_minutes": 45,
                                                     "key_points_to_cover": [],
                                                     "questions_to_ask": ["What surprised you most?",
                                                                          "What would you like to change in 3 months?"]}},
        "personalized_resources": [],
        "_meta": {"generated_at": "2026-10-12T00:00:00Z"},
    }


def _report_sample() -> dict:
    """Same context the real report emails get (email._report_context), so previews match sends."""
    from app.services.email import _report_context

    ctx = _report_context(sample_report_context())
    ctx["top3"] = [{"category": "Bible Study", "score": 9}, {"category": "Prayer Life", "score": 8}]
    return ctx


def _premium_sample() -> dict:
    from app.services.report_summary import public_full_report

    ctx = _report_sample()
    ctx["full_report"] = public_full_report(sample_full_report(), ctx["blob"])
    return ctx


def _gifts_sample() -> dict:
    return {"apprentice_name": "Jordan Davis", "version": 1,
            "top_gifts": [{"gift": "Teaching", "score": 18, "summary": "Explaining God's Word clearly."},
                          {"gift": "Hospitality", "score": 17, "summary": "Making others feel welcome."},
                          {"gift": "Encouragement", "score": 16, "summary": "Strengthening others' faith."}],
            "all_scores": [{"gift": "Teaching", "score": 18}, {"gift": "Hospitality", "score": 17},
                           {"gift": "Encouragement", "score": 16}, {"gift": "Service", "score": 12}],
            "definitions": {"Teaching": "Explaining God's Word clearly.", "Hospitality": "Welcoming others.",
                            "Encouragement": "Strengthening others' faith."}}


def _agreement(extra: dict | None = None) -> Callable[[], dict]:
    def build() -> dict:
        ctx = {"action_url": "https://trooth-discipleship-api.onlyblv.com/agreements/sign/abc",
               "apprentice_name": "Jordan Davis", "mentor_name": "Marcus Lee", "apprentice_email": "jordan@example.com",
               "mentor_email": "marcus@example.com", "parent_email": "parent@example.com", "agreement_id": "agr_123"}
        ctx.update(extra or {})
        return ctx
    return build


def _metrics_sample() -> dict:
    return {"report_type": "Weekly", "period_label": "Oct 5 – Oct 11, 2026", "report_date": "2026-10-12",
            "generated_at": "2026-10-12 06:00 UTC",
            "users": {"total_users": 120, "mentors": 30, "apprentices": 90, "new_users_in_period": 8,
                      "new_mentors_in_period": 2, "new_apprentices_in_period": 6},
            "assessments": {"total_completed": 210, "completed_in_period": 13, "started_in_period": 16,
                            "active_drafts": 9, "completion_rate": 81.2, "errors": 0},
            "agreements": {"fully_signed": 25, "awaiting_apprentice": 2, "awaiting_parent": 1,
                           "completion_rate": 89.3},
            "invitations": {"total_invitations": 60, "accepted": 44, "pending": 10, "expired": 6,
                            "acceptance_rate": 73.3},
            "mentorship": {"active_relationships": 40, "mentors_with_apprentices": 22,
                           "avg_apprentices_per_mentor": 1.8, "mentor_utilization_percent": 73.3},
            "mentor_activity": {"active_mentors": 15, "notes_in_period": 31, "total_notes": 410}}


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

_ENTRIES = [
    # Engagement (can be unsubscribed from)
    EmailType("draft_reminder", "campaigns/draft_reminder.html", ENGAGEMENT,
              lambda c: f"You're {c.get('progress_percent', 0)}% through {c.get('assessment_name', 'your assessment')}. Finish in a few minutes.",
              "You're getting this because you started an assessment in T[root]H Discipleship.",
              lambda: {"apprentice_name": "Jordan", "assessment_name": "Master T[root]H Assessment", "days_ago": 3,
                       "progress_percent": 60, "answered_count": 34, "total_questions": 57, "mentor_name": "Marcus",
                       "resume_link": "https://onlyblv.com/#apps", "remaining_minutes": 10}),
    EmailType("new_template", "campaigns/new_template.html", ENGAGEMENT,
              lambda c: f"New assessment: {c.get('template_name', 'a new assessment')} is ready for you.",
              "You're getting this because you have a T[root]H Discipleship account.",
              lambda: {"name": "Jordan", "template_name": "Spiritual Disciplines Check-in", "category": "Growth",
                       "description": "A short look at your daily rhythms.", "estimated_minutes": 12}),
    EmailType("inactive_reengagement", "campaigns/inactive_reengagement.html", ENGAGEMENT,
              "Your discipleship journey is waiting. Pick up where you left off.",
              "You're getting this because you have a T[root]H Discipleship account.",
              lambda: {"name": "Jordan", "days_inactive": 30, "is_mentor": False, "assessment_count": 2,
                       "last_assessment_name": "Master T[root]H Assessment", "new_templates_count": 1,
                       "apprentice_names": []}),
    EmailType("welcome_mentor", "campaigns/welcome_mentor.html", ENGAGEMENT,
              "Welcome to T[root]H Discipleship. Here's how to invite your first apprentice.",
              "You're getting this because you created a T[root]H Discipleship mentor account.",
              lambda: {"name": "Marcus"}),
    EmailType("welcome_apprentice", "campaigns/welcome_apprentice.html", ENGAGEMENT,
              "Welcome to T[root]H Discipleship. Start with your first assessment.",
              "You're getting this because you created a T[root]H Discipleship account.",
              lambda: {"name": "Jordan", "mentor_name": "Marcus"}),

    # Transactional: reports
    EmailType("mentor_report", "reports/mentor_report.html", TRANSACTIONAL,
              lambda c: f"{c.get('apprentice_name', 'Your apprentice')}'s report is ready: Health Score {(c.get('summary') or {}).get('health_score', '')}",
              "You're getting this because you mentor this apprentice in T[root]H Discipleship.",
              _report_sample),
    EmailType("premium_report", "reports/premium_report.html", TRANSACTIONAL,
              lambda c: f"Premium report for {c.get('apprentice_name', 'your apprentice')}: executive summary and 12-week plan",
              "You're getting this because you mentor this apprentice in T[root]H Discipleship.",
              _premium_sample),
    EmailType("master_trooth_report", "reports/master_trooth.html", TRANSACTIONAL,
              "Your Master T[root]H Assessment report is ready.",
              "You're getting this because you requested this report in T[root]H Discipleship.",
              _report_sample),
    EmailType("generic_assessment_report", "reports/generic_assessment.html", TRANSACTIONAL,
              lambda c: f"{c.get('title', 'Assessment')} report is ready.",
              "You're getting this because you requested this report in T[root]H Discipleship.",
              lambda: {"title": "Spiritual Disciplines Check-in", "apprentice_name": "Jordan Davis", "summary": None,
                       "overall_score": 8, "category_rows": [("Prayer", 8), ("Scripture", 7)],
                       "summary_recommendation": "Keep a steady morning rhythm."}),
    EmailType("assessment_complete", "reports/assessment_complete.html", TRANSACTIONAL,
              lambda c: f"{c.get('apprentice_name', 'Your apprentice')} completed an assessment.",
              "You're getting this because you mentor this apprentice in T[root]H Discipleship.",
              lambda: dict(_report_sample(), mentor_name="Marcus Lee", assessment_title="Master T[root]H Assessment",
                           overall_score=8, category_rows=[("Prayer Life", 8), ("Bible Study", 9)],
                           strengths=sample_blob()["strengths"], gaps=sample_blob()["gaps"])),
    EmailType("spiritual_gifts_report", "reports/spiritual_gifts.html", TRANSACTIONAL,
              lambda c: f"Top gifts: {', '.join(g['gift'] for g in c.get('top_gifts', [])[:3])}",
              "You're getting this because you requested this report in T[root]H Discipleship.",
              _gifts_sample),

    # Transactional: account and mentorship
    EmailType("invitation", "account/invitation.html", TRANSACTIONAL,
              lambda c: f"{c.get('mentor_name', 'Your mentor')} invited you to T[root]H Discipleship.",
              "You're getting this because a mentor invited you to T[root]H Discipleship.",
              lambda: {"apprentice_name": "Jordan", "mentor_name": "Marcus Lee", "token": "inv_abc123", "code": "K7QM-3XPR",
                       "accept_url": "https://trooth-discipleship-api.onlyblv.com/invitations/accept-invitation?token=inv_abc123"}),
    EmailType("support_request_confirmation", "account/support_request_confirmation.html", TRANSACTIONAL,
              "We got your message and will reply soon.",
              "You're getting this because you contacted T[root]H support.",
              lambda: {"name": "Jordan", "topic": "Billing", "message": "My subscription didn't renew."}),

    EmailType("notification", "account/notification.html", TRANSACTIONAL,
              lambda c: (c.get("message") or c.get("subject") or "")[:110],
              "You're getting this because of activity on your T[root]H Discipleship account.",
              lambda: {"subject": "Your mentor left you a note", "message": "Marcus shared a note on your latest assessment.\n\nOpen the app to read it.",
                       "action_url": "https://onlyblv.com/#apps", "action_label": "Take action"}),
    EmailType("gift_seat", "account/gift_seat.html", TRANSACTIONAL,
              lambda c: f"{c.get('mentor_name', 'Your mentor')} gifted you Premium access to T[root]H Discipleship.",
              "You're getting this because your mentor gifted you Premium access.",
              lambda: {"apprentice_name": "Jordan", "mentor_name": "Marcus Lee", "redemption_code": "GIFT-7Q2X",
                       "auto_activated": False}),
    EmailType("gift_seat_revoked", "account/gift_seat_revoked.html", TRANSACTIONAL,
              "Your gifted Premium access has ended. You're back on the free plan.",
              "You're getting this because your gifted Premium access changed.",
              lambda: {"apprentice_name": "Jordan", "mentor_name": "Marcus Lee"}),

    # Transactional: rewards (deliver something the user earned)
    EmailType("daily_trivia_reward", "campaigns/daily_trivia_reward.html", TRANSACTIONAL,
              lambda c: f"You earned {c.get('percent', 0)}% off at the T[root]H shop.",
              "You're getting this because you earned a Daily Trivia reward.",
              lambda: {"name": "Jordan", "percent": 15, "tier": "7-day streak", "perfect": False,
                       "discount_code": "TROOTH15-ABCD", "expires": "Nov 12, 2026", "shop_url": "https://shop.onlyblv.com",
                       "replaced_percent": None}),
    EmailType("trivia_prize", "campaigns/trivia_prize.html", TRANSACTIONAL,
              lambda c: f"You placed {c.get('place_name', '')} in {c.get('competition_name', 'the trivia competition')}!",
              "You're getting this because you won a prize in a T[root]H trivia competition.",
              lambda: {"name": "Jordan", "competition_name": "October Challenge", "place_name": "1st", "medal": "🥇",
                       "score": 980, "prize_label": "25% off", "discount_code": "WIN25-ABCD", "expires": "Nov 30, 2026",
                       "shop_url": "https://shop.onlyblv.com"}),

    # Transactional: agreements
    EmailType("agreement_apprentice_invite", "agreements/apprentice_invite.html", TRANSACTIONAL,
              lambda c: f"{c.get('mentor_name', 'Your mentor')} sent you a mentorship agreement to review.",
              "You're getting this because you were invited to a mentorship agreement.", _agreement()),
    EmailType("agreement_fully_signed", "agreements/fully_signed.html", TRANSACTIONAL,
              "Your mentorship agreement is fully signed.",
              "You're getting this because you're part of this mentorship agreement.", _agreement()),
    EmailType("agreement_parent_invite", "agreements/parent_invite.html", TRANSACTIONAL,
              "Please review and sign your child's mentorship agreement.",
              "You're getting this because you were listed as a parent or guardian on a mentorship agreement.",
              _agreement()),
    EmailType("agreement_parent_resend", "agreements/parent_resend.html", TRANSACTIONAL,
              "Reminder: a mentorship agreement is waiting for your signature.",
              "You're getting this because you were listed as a parent or guardian on a mentorship agreement.",
              _agreement()),
    EmailType("agreement_parent_resend_request", "agreements/parent_resend_request.html", TRANSACTIONAL,
              "A new signing link was requested for a mentorship agreement.",
              "You're getting this because you're part of this mentorship agreement.", _agreement()),
    EmailType("agreement_reschedule_request", "agreements/reschedule_request.html", TRANSACTIONAL,
              "New meeting times were proposed for your mentorship.",
              "You're getting this because you're part of this mentorship agreement.",
              _agreement({"proposals": ["Tue 7:00 PM", "Thu 6:30 PM"]})),
    EmailType("agreement_reschedule_response", "agreements/reschedule_response.html", TRANSACTIONAL,
              "Your meeting time request has a response.",
              "You're getting this because you're part of this mentorship agreement.",
              _agreement({"decision": "accepted", "note": "See you then!", "selected_time": "Thu 6:30 PM"})),
    EmailType("agreement_revoked", "agreements/revoked.html", TRANSACTIONAL,
              "A mentorship agreement was revoked.",
              "You're getting this because you're part of this mentorship agreement.", _agreement()),

    # Internal (staff only)
    EmailType("metrics_report", "internal/metrics_report.html", INTERNAL,
              lambda c: f"T[root]H {c.get('report_type', '')} metrics: {c.get('period_label', '')}",
              "Internal report for the T[root]H team.", _metrics_sample),
    EmailType("support_request_admin", "internal/support_request_admin.html", INTERNAL,
              lambda c: f"Support request: {c.get('topic', '')} from {c.get('name', '')}",
              "Internal notice for the T[root]H support team.",
              lambda: {"name": "Jordan", "email": "jordan@example.com", "topic": "Billing", "message": "Renewal issue",
                       "user_id": "u1", "is_premium": True, "source": "app", "device_info": "iOS 26",
                       "submitted_at": "2026-10-12 10:00 UTC"}),
]

_ENTRIES.append(EmailType(
    "trivia_admin_summary", "internal/trivia_admin_summary.html", INTERNAL,
    lambda c: f"Trivia {c.get('competition_name', '')} winners",
    "Internal notice for the T[root]H team.",
    lambda: {"competition_name": "October Challenge", "competition_slug": "october-2026",
             "winners": [{"place": "1st", "name": "Jordan D.", "score": "980", "code": "WIN25-ABCD",
                          "emailed_at": "2026-11-01 09:00"}]}))

CATALOG: dict[str, EmailType] = {e.key: e for e in _ENTRIES}


def get(key: str) -> EmailType:
    return CATALOG[key]


def render(key: str, context: dict | None = None, *, user_id: str | None = None):
    """Render a catalog email with its preheader, reason and category."""
    from app.services.email_render import render_email

    entry = CATALOG[key]
    ctx = entry.sample_context() if context is None else context
    return render_email(entry.template, ctx, preheader=entry.preheader_for(ctx), reason=entry.reason,
                        category=entry.category, user_id=user_id)
