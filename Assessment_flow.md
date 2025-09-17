# Master Trooth Assessment vs Mentor-Created Templates — Scoring, Reporting, Email

Goals
- Give the Master Trooth Assessment (MTA) its own first-class flow (scoring + reporting + email) suitable for a holistic spiritual snapshot.
- Provide a flexible, safe, and lighter-weight flow for mentor-created templates (MCT) that can scale across custom assessments.
- Preserve existing entry points: “New Assessment” continues to launch the MTA for apprentices; results/history are accessible from the apprentice “View Progress” screen and the mentor “Assessment Results” screen for both MTA and generic templates.

Architecture Overview
- Template-driven: assessment_templates carries strategy flags per template.
- Two scoring pipelines:
  - MTA: dedicated prompts, rubric, aggregation, and report design.
  - MCT: generic scoring using per-template rubric metadata (or deterministic/no-AI).
- Two reporting pipelines:
  - MTA: branded Jinja email + PDF with growth plan sections.
  - MCT: generic Jinja email + optional PDF derived from rubric.
- Shared infra: rate limiting, audit logging, history/latest endpoints, authorization.

Data Model (additions/flags)
- assessment_templates
  - key (e.g., master_trooth_v1), version (int)
  - is_master (bool, default false)
  - scoring_strategy (enum: ai_master, ai_generic, deterministic, none)
  - rubric_json (JSON; categories, weights, output schema for ai_generic)
  - report_template (string id; e.g., email/master_trooth_report.html)
  - pdf_renderer (string id; e.g., master_trooth)
- assessments (existing)
  - template_key, template_version
  - scores (JSON; schema varies by strategy; include scoring_version, model)
- Optional: email_send_events already exists

Backend Endpoints

Master Trooth Assessment (dedicated)
- POST /assessments/master-trooth/submit
  - Validates answers → loads MTA questions → ai_master scoring → persist → return result
- GET /assessments/master-trooth/latest
- GET /assessments/master-trooth/history?cursor=&limit=
- GET /assessments/master-trooth/submission/{assessment_id} (optional deep-link)
- Mentor scope:
  - GET /assessments/master-trooth/{apprentice_id}/latest
  - GET /assessments/master-trooth/{apprentice_id}/history
- Email/Report:
  - POST /assessments/master-trooth/email-report
  - POST /assessments/master-trooth/{apprentice_id}/email-report (mentor/admin)

Mentor-Created Templates (generic)
- POST /assessments/{template_id}/submit
  - Resolves template → strategy switch:
    - ai_generic: use rubric_json to build prompts and parse
    - deterministic: template-provided rules
    - none: store answers only
- GET /assessments/{template_id}/latest
- GET /assessments/{template_id}/history
- GET /assessments/{template_id}/submission/{assessment_id} (optional)
- POST /assessments/{template_id}/email-report

Scoring Pipelines

ai_master (Master Trooth)
- Service: app/services/ai_scoring_master.py
- Input: questions with categories (Prayer, Scripture, Community, Service, Worship, Mission, etc.), optional weights.
- Prompting:
  - Calibrated system prompt; explicit JSON schema (per-category {score 1–10, strengths, growth_opportunities, practices, scriptures}), plus overall summary and 90-day plan suggestions.
  - Model: gpt-4o/gpt-4.1 (configurable).
- Aggregation:
  - Weighted composite score, rank categories, derive strengths/weaknesses, produce tailored growth plan.
- Output JSON (persisted):
  {
    "overall_score": 0–100,
    "categories": [{ "name", "score", "strengths":[], "growth":[] }],
    "recommendations": { "90_day_plan": [...], "scripture_reading_plan": [...] },
    "scoring_version": "mta_v1",
    "model": "gpt-4o"
  }
- Fallback: mock scoring if no key; safe defaults.

ai_generic (Mentor Templates)
- Service: app/services/ai_scoring_generic.py
- Uses rubric_json from template to:
  - Define category groups, score scale, and output fields.
  - Emit normalized, template-specific JSON, e.g. { overall, categories[], feedback[] }.
- Safer default prompts; smaller surface area; includes mock fallback.

deterministic
- Optional if a template encodes scoring rules (like Spiritual Gifts).

Reporting & Email

Master Trooth
- Email HTML: app/templates/email/master_trooth_report.html (Jinja)
  - Header, apprentice greeting, category tiles, strengths/growth, 90-day plan, scriptures, CTA back to app
  - Uses app brand colors
- PDF: app/services/master_trooth_report.py (ReportLab or WeasyPrint)
  - Visual parity with email; printable layout
- Routes call render_master_trooth_email(...) and generate_master_trooth_pdf(...).
- Rate limit + audit like Spiritual Gifts.

Mentor Templates
- Email HTML: app/templates/email/generic_assessment_report.html
  - Driven by rubric_json (headings, table of category scores, brief notes)
- Optional PDF: app/services/generic_assessment_report.py

Authorization & History
- Self routes limited to the authenticated apprentice.
- Mentor routes check assignment/relationship (mentor-of-apprentice).
- audit.log_assessment_submit/view/email on actions.
- Cursor-based history for both flows; latest for quick access.

Frontend Integration

Navigation guarantees (unchanged access)
- Apprentices still access the Master Trooth Assessment via the “New Assessment” button. This continues to launch the MTA flow without change.
- Results and history are visible from:
  - Apprentice Dashboard → View Progress screen (shows MTA and generic assessments).
  - Mentor Dashboard → Assessment Results screen (shows MTA and generic assessments per apprentice).

Apprentice
- Entry points
  - New Assessment button: launches Master Trooth Assessment (MTA) as before.
  - View Progress screen:
    - Shows Latest Results and History for MTA.
    - Also lists generic mentor-created assessments in the same screen, with template badges/titles to distinguish them.
- Screens
  - MTA Results screen: strengths, growth plan, category list, email.
  - MTA History: paginated list; detail view; email per submission.
  - Generic template results: use the generic renderer; appear alongside MTA in View Progress.

Mentor
- Assessment Results screen (single hub)
  - Select apprentice → shows:
    - Master Trooth latest + history.
    - Generic template results and history (same screen; selectable by template filter or sectioned list).
  - Actions: open full report view, email PDF/HTML, view history item details.

Notes
- No new dashboard cards are required to access MTA; the existing New Assessment button remains the canonical entry.
- Spiritual Gifts remains a separate dedicated experience; this section focuses on MTA and mentor-created templates.

Migration & Rollout Plan
- DB: add columns (is_master, scoring_strategy, rubric_json, report_template, pdf_renderer).
- Seed: mark master trooth template (key master_trooth_v1) with is_master=true, scoring_strategy=ai_master.
- Services:
  - Add ai_scoring_master.py, ai_scoring_generic.py
  - Add master_trooth_report.py, generic_assessment_report.py
  - Add email renderers + templates
- Routes:
  - New MTA routes (submit/latest/history/email)
  - Generic template routes (submit/latest/history/email) if not present
- Frontend:
  - Keep New Assessment button routing to MTA (unchanged).
  - Ensure View Progress screen aggregates MTA + generic templates (latest + history).
  - Mentor Assessment Results screen displays MTA + generic templates for selected apprentice.
- Tests:
  - Unit tests per service (prompt build, JSON parse, fallback)
  - Route tests (authz, rate limit)
  - Email render snapshot tests
  - PDF smoke tests

Open Questions / Decisions
- Exact MTA categories and weights? Provide finalized rubric.
- Target JSON schema for 90-day plan and scripture plan?
- Whether mentor-created templates can opt in to email/PDF by default or require an admin flag.

Implementation Checklist (backend)
- [ ] Migration: add template flags/columns
- [ ] Seed master_trooth_v1 template record
- [ ] app/services/ai_scoring_master.py
- [ ] app/templates/email/master_trooth_report.html
- [ ] app/services/master_trooth_report.py
- [ ] Routes: /assessments/master-trooth/* (self + mentor)
- [ ] app/services/ai_scoring_generic.py
- [ ] app/templates/email/generic_assessment_report.html
- [ ] app/services/generic_assessment_report.py
- [ ] Routes: /assessments/{template_id}/* (self + mentor)
- [ ] Tests: scoring, routes, emails, pdfs

Implementation Checklist (frontend)
- [ ] New Assessment button → MTA (unchanged)
- [ ] View Progress: show MTA + generic assessments (latest + history), with template badges
- [ ] Apprentice MTA Results screen (strengths, growth plan, scriptures, email)
- [ ] Apprentice MTA History screen + detail
- [ ] Mentor Assessment Results: MTA + generic templates per apprentice
- [ ] Generic results renderer + email actions and cooldowns

Summary
- MTA retains its primary entry via the existing New Assessment button.
- Results and history for both MTA and mentor-created templates are available in the same places:
  - Apprentice: View Progress screen.
  - Mentor: Assessment Results screen.
- MTA gets a specialized AI scoring and reporting pipeline; mentor-created templates use a generic, rubric-driven pipeline. Both share infra (auth, history, email).