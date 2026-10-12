# Implementation Plan: Email Redesign (consistent layout, report emails, working unsubscribe)

**Branch**: `feature/email-redesign` | **Date**: 2026-10-12 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/005-email-redesign/spec.md`

## Summary

All email goes through one render pipeline and one send path:

- **Templates:** a hardened, table-based dark layout replaces `_base.html`. Every email, including
  the standalone report templates and the ones currently built as f-strings, becomes a Jinja
  template that extends it.
- **Rendering:** at render time, CSS is inlined (`css-inline`) and a plain-text version is
  generated (`html2text`).
- **Email catalog:** a central catalog lists every email type with its category (engagement,
  transactional or internal), preheader and a sample-context builder. The preview script and the
  coverage tests both use it.
- **Unsubscribe:** engagement emails carry a signed unsubscribe link plus `List-Unsubscribe` and
  `List-Unsubscribe-Post` headers. New public pages confirm the unsubscribe (link scanners can't
  trigger it), handle the RFC 8058 one-click POST, and allow resubscribing. A new
  `users.email_opt_out` column gates engagement sends, and skips are logged.
- **Report emails:** they share one "report headline" partial fed by `report_summary`, so their
  numbers match the app.

## Technical Context

**Language/Version**: Python 3.11

**Primary Dependencies**: FastAPI, SQLAlchemy, Alembic, Jinja2 (existing), SendGrid (existing).
**New:**
- `css-inline` (inlines `<style>` rules into elements so Gmail and Outlook keep the design; Rust
  core, maintained, no system dependencies);
- `html2text` (plain-text versions generated from the same HTML, so text and HTML can't drift).

Both are pinned with a minimum version in `requirements.txt`.

**Storage**: PostgreSQL. New columns `users.email_opt_out` (bool, default false, server default
false), `users.email_pref_changed_at` and `users.email_pref_source` (String(16)), added by the
migration `alembic/versions/20261012_email_preferences.py` (with `downgrade()`).

**Testing**: pytest. Render tests for every catalog entry (shared layout, preheader, text part,
inlined styles, unsubscribe for engagement emails). Endpoint tests for unsubscribe, one-click,
resubscribe, an invalid token and the legacy path. Gating tests confirm engagement emails skip
opted-out users and transactional emails don't. SendGrid is mocked.

**Target Platform**: Google Cloud Run (dev and prod services)

**Project Type**: web-service (client: Flutter app in `trooth_assessment`; no app change)

**Performance Goals**: rendering plus inlining under 200 ms per email, so campaign batches stay
fast. Unsubscribe pages respond in under 500 ms.

**Links**: "Open in app" goes to `settings.app_landing_url` (onlyblv.com `#apps`, both store badges). The footer lists the App Store and Google Play links (research R8).

**Constraints**:
- emails stay under Gmail's 102 KB clipping limit;
- the layout is 600 px wide and fluid on phones;
- no web fonts are required (system font stack);
- the unsubscribe link must not expire for at least 1 year (old emails keep working).

**Scale/Scope**: every email type in the catalog: 26 template files (21 on `_base.html`, including
the 8 agreement and 7 campaign templates, plus 5 standalone report templates) and 5 emails built as f-strings, 4 public endpoints, 1 migration,
1 preview script.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **I. Auth** ✅: `/email/unsubscribe`, `/email/unsubscribe/one-click`, `/email/resubscribe`
  and the legacy `/settings/notifications` are **explicitly public** and authorized only by an
  HMAC-signed token bound to one user id (spec Access). The token can't be forged without
  `EMAIL_LINK_SECRET`. No test shortcuts.
- [x] **II. Errors** ✅: an invalid or tampered token gets a 400 HTML page (user-facing pages, not
  JSON). API-style errors use `HTTPException` with `detail`.
- [x] **III. Migrations** ✅: `20261012_email_preferences.py` with `downgrade()`, run by the migrate
  job before deploy.
- [x] **IV. Config & secrets** ✅: the new secret `EMAIL_LINK_SECRET` comes from Secret Manager
  through `settings.email_link_secret`, with no default. Without it, engagement emails go out
  without an unsubscribe link and an error is logged, rather than signing with a guessable key.
  The deploy skills' `--set-secrets` lists (in the app repo's `.claude/skills/deploy-*`) are
  updated in full.
- [x] **V. Logging** ✅: skips are logged as `email_skipped_opt_out campaign=<type> user=<id>`.
  Tokens and email addresses aren't logged.
- [x] **VI. Compatibility** ✅: additive. New columns have defaults, the endpoints are new, and the
  legacy path goes from 404 to a page. No app change.
- [x] **VII. Layering** ✅: rendering and sending live in `app/services/email.py` and the new
  `app/services/email_render.py` and `app/services/email_catalog.py`. Routes in
  `app/routes/email_preferences.py` only handle requests.
- [x] **VIII. Tests** ✅: endpoint success and failure paths (bad token, unknown user,
  repeats), render coverage for every catalog entry, and gating. No live SendGrid calls.
- [x] **IX. Deploy** ✅: dev first (with the test sends and dark-mode checks in quickstart), then
  prod from `main`.
- [x] **X. Contract** ✅: `contracts/email-preferences.md` documents the public endpoints and the
  email headers. There's no frontend spec (the spec says "Frontend: none").
- [x] **XI. Formatting** ✅: templates are rewritten wholesale (expected), with no unrelated
  reformatting of Python files.

## Project Structure

### Documentation (this feature)

```text
specs/005-email-redesign/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/email-preferences.md
└── tasks.md            # /speckit-tasks
```

### Source Code (repository root)

```text
app/
├── services/
│   ├── email_render.py          # NEW render_email(template, context) → RenderedEmail(html, text, preheader); css-inline + html2text; size guard
│   ├── email_catalog.py         # NEW EmailType registry: key, template, category, preheader, sample_context()
│   ├── email_links.py           # NEW sign/verify unsubscribe tokens (HMAC-SHA256, user id + issued-at)
│   ├── email.py                 # CHANGED: send_email(..., category, headers); campaign senders check opt-out; f-string emails → templates; all Mail() calls go through send_email
│   ├── agreement_notifications.py  # CHANGED: render through render_email
│   ├── metrics_reports.py       # CHANGED: inline HTML → templates/email/internal/metrics_report.html
│   └── master_trooth_report.py  # CHANGED: report email context uses the shared headline partial
├── routes/email_preferences.py  # NEW public unsubscribe / one-click / resubscribe / legacy pages
├── templates/
│   ├── email/
│   │   ├── _base.html           # REPLACED by the hardened table layout (all 21 extenders inherit it)
│   │   ├── _macros.html         # NEW button (VML for Outlook), report_headline, section, list
│   │   ├── reports/*.html       # MOVED/REWRITTEN: mentor_report, premium_report, assessment_complete, generic_assessment, spiritual_gifts, master_trooth
│   │   ├── account/*.html       # NEW from f-strings: notification, gift_seat, gift_seat_revoked
│   │   ├── internal/*.html      # NEW: metrics_report, trivia_competition_admin_summary
│   │   ├── campaigns/*.html     # CHANGED: unsubscribe block from the layout, not hand-written
│   │   └── agreements/*.html    # CHANGED: extend the new layout
│   └── pages/email_preferences/*.html   # NEW public pages: confirm, done, resubscribed, invalid, legacy
├── models/user.py               # CHANGED: email_opt_out, email_pref_changed_at, email_pref_source
└── core/settings.py             # CHANGED: email_link_secret, support_email
alembic/versions/20261012_email_preferences.py   # NEW
scripts/email_preview.py         # NEW render all to ~/.cache/onlyblv/email-previews; --send-to <one address>
tests/test_email_redesign.py     # NEW
requirements.txt                 # + css-inline, html2text
```

**Structure Decision**: rendering, catalog and link signing are separate small services, so the
preview script and tests can use them without the send path. The public pages are server-rendered
HTML from a new route module registered in `app/main.py`.

## Complexity Tracking

No constitution violations. The new secret follows Principle IV; it is not a deviation.
