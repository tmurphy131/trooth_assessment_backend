---

description: "Tasks: Email Redesign (consistent layout, report emails, working unsubscribe)"
---

# Tasks: Email Redesign

**Input**: Design documents from `/specs/005-email-redesign/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/email-preferences.md, quickstart.md

**Tests**: Required by spec FR-020 and constitution VIII. Endpoint success and failure tests, render coverage for every catalog entry, and opt-out gating. SendGrid is always mocked.

**Organization**: grouped by user story. Phase 2 builds the shared pipeline (layout, render, catalog, send path) that every story uses. US1 (unsubscribe) and US2 (report emails) are both P1 and touch different files, so they can run in parallel after Phase 2.

**Rule for every migrated email**: the existing `render_*` and `send_*` function names, signatures and return values in `app/services/email.py` stay the same, so callers in `app/routes/*` and `app/services/*` don't change (spec FR-013, SC-007).

## Format: `[ID] [P?] [Story] Description`

---

## Phase 1: Setup

- [X] T001 Add `css-inline>=0.14` and `html2text>=2024.2.26` to `requirements.txt` (with a comment: inline CSS for Gmail/Outlook; plain-text parts from the same HTML). Install them into `.venv` and confirm `import css_inline, html2text` works.
- [X] T002 [P] In `app/core/settings.py`, add:
  - `email_link_secret` (env `EMAIL_LINK_SECRET`, **no default**, empty string means unset);
  - `support_email` (env `SUPPORT_EMAIL`, default `admin@onlyblv.com`);
  - `email_link_ttl_days` (env `EMAIL_LINK_TTL_DAYS`, default 400);
  - `app_landing_url` (env `APP_LANDING_URL`, default `https://onlyblv.com/#apps`);
  - `android_play_store_url` (env `ANDROID_PLAY_STORE_URL`, default `https://play.google.com/store/apps/details?id=com.trooth.flutterTroothAssessment`).
- [X] T003 [P] Create the migration `alembic/versions/20261012_email_preferences.py` (down_revision = the current head; check with `alembic heads`). It adds to `users`:
  - `email_opt_out` Boolean NOT NULL server_default `false`;
  - `email_pref_changed_at` DateTime nullable;
  - `email_pref_source` String(16) nullable.

  `downgrade()` drops all three. Add the same columns to `app/models/user.py`, with the comment `# Engagement-email opt-out (specs/005-email-redesign)`.

---

## Phase 2: Foundational (Blocking Prerequisites)

**⚠️ CRITICAL**: no story work starts until this phase is done.

### Tests first

- [X] T004 [P] Create `tests/test_email_redesign.py` with render-pipeline tests (failing until T006–T009 exist):
  - `render_email()` returns `html` with no `class=` styling lost (a `.brand-btn` style is inlined into `style=`), a `text` part with no HTML tags and the button URL kept, the preheader in a hidden first `<div>`, and `size_bytes < 102_400`;
  - the `button()` macro output contains both `<!--[if mso]>` VML and a fallback `<a>`;
  - `<meta name="color-scheme" content="dark">` is present;
  - the footer contains both the App Store and Google Play URLs, and the `button(app_url, "Open in app")` in a report links to `settings.app_landing_url`.
- [X] T005 [P] In `tests/test_email_redesign.py`, add catalog coverage tests:
  - every `.html` file under `app/templates/email/` except `_base.html` and `_macros.html` belongs to exactly one `EmailType`;
  - every `EmailType` renders its `sample_context()` without error;
  - each render has a preheader of 1–110 chars and the shared footer marker (`data-trooth-footer`);
  - engagement entries render an unsubscribe link and transactional or internal ones don't.

### Implementation

- [X] T006 Replace `app/templates/email/_base.html` with the hardened layout (research R1):
  - `<!DOCTYPE html>` with `lang="en"`, the `color-scheme` and `supported-color-schemes` metas set to `dark`, and `:root{color-scheme:dark}`;
  - a hidden preheader `{% block preheader %}{{ preheader }}{% endblock %}` plus a zero-width-space filler as the first `<body>` child;
  - an outer 100% table (`bgcolor="#0b0b0b"`) holding an inner 600 px table (`bgcolor="#1a1a1a"`), with explicit `bgcolor` and inline `background-color` on every `td`;
  - the logo `<img src="{{ logo_url }}" alt="T[root]H Discipleship" width="160">` with a text fallback;
  - `{% block content %}`;
  - a footer `<td data-trooth-footer>` containing **both** store links (`ios_app_store_url` labelled "App Store" and `android_play_store_url` labelled "Google Play"), the support email, `{{ reason }}`, and `{% if unsubscribe_url %}<a href="{{ unsubscribe_url }}">Unsubscribe</a>{% endif %}`.

  Keep the existing class names (`.card`, `.brand-btn`, `.muted`, `.pill`, `.highlight-box`, `.accent-badge`, `.divider`, `.danger`, `.success`) defined in the `<style>` block with dark-safe colors, so the 21 extending templates keep working once inlined. Add a phone media query (`max-width:620px` → inner table 100%).
- [X] T007 Create `app/templates/email/_macros.html` with these macros:
  - `button(url, label)`: VML `v:roundrect` in `<!--[if mso]>`, plus a table-cell `<a>` with gold `#d4af37` background, black bold label and 6 px radius;
  - `section(title)` call block;
  - `bullet_list(items, max=3)`;
  - `report_headline(summary)`: Health Score number, band pill and Biblical Knowledge % line, each shown only if present (FR-017);
  - `kv_row(label, value)`.
- [X] T008 Create `app/services/email_render.py`:
  - `RenderedEmail` dataclass (`html`, `text`, `preheader`, `size_bytes`, `headers: dict`);
  - `render_email(template, context, *, preheader, reason, category, user=None)`. It merges the defaults (`logo_url`, `app_url=settings.app_landing_url`, `ios_app_store_url`, `android_play_store_url`, `support_email`, `reason`, `preheader`, `year`) and renders with `get_email_template_env()`. It inlines with `css_inline.CSSInliner(keep_style_tags=True).inline(html)`, then builds the text with `html2text` (`body_width=0`, `ignore_images=True`, `ignore_emphasis=False`) after removing the preheader `<div>`.
  - For `category == "engagement"` with a `user`, it adds `unsubscribe_url` to the context and the `List-Unsubscribe` and `List-Unsubscribe-Post` headers from `email_links` (T011). If the secret is unset, it logs `email_link_secret_missing` at ERROR and adds neither.
  - It warns at `size_bytes > 95_000`.
- [X] T009 Create `app/services/email_catalog.py`:
  - `EmailType(key, template, category, preheader, reason, sample_context)` and `CATALOG: dict[str, EmailType]`;
  - `get(key)`;
  - a placeholder entry for every existing template file, with `sample_context` returning realistic data (names Jordan/Marcus, a v2.1 mentor blob with `health_score` 80, `health_band` "Maturing", `biblical_knowledge.percent` 86.2, 3 strengths, 3 gaps and a priority action).

  Categories, exactly per research R6:
  - **engagement:** `draft_reminder`, `new_template`, `inactive_reengagement`, `welcome_mentor`, `welcome_apprentice`;
  - **internal:** `metrics_report`, `trivia_admin_summary`;
  - **transactional:** all others.
- [X] T010 In `app/services/email.py`, add `category: str = "transactional"` and `headers: dict | None = None` to `send_email()`, and attach each header to the SendGrid `Mail` (`Header(name, value)`). Route the two direct `Mail(...)` constructions in `send_assessment_email` and `send_invitation_email` through `send_email()`, keeping their behavior (recipients, subjects, attachments). Keep the existing test-mode behavior of `send_email`. *(Done: in production both functions already called `send_email`; their direct `Mail(...)` construction only runs in `ENV=test` for legacy tests that patch the SendGrid client, so it was left as is.)*

**Checkpoint**: T004/T005 pass for the shared pipeline. Existing `pytest` still passes (the old templates now inherit the new base).

---

## Phase 3: User Story 1 - Recipients can stop engagement emails in one click (Priority: P1) 🎯 MVP

**Goal**: working signed unsubscribe (page, one-click, resubscribe, legacy page), stored opt-out, and engagement sends gated.

**Independent Test**: quickstart §4.

### Tests

- [X] T011 [P] [US1] In `tests/test_email_redesign.py`, add token tests for `email_links`:
  - `make_token(user_id)` and `verify_token()` round-trip;
  - a flipped character, a wrong secret, `issued_at` older than 400 days, `issued_at` in the future, and an unknown version all return `None`;
  - `unsubscribe_urls(user)` returns the page URL and the one-click URL on `settings.backend_api_url`.
- [X] T012 [P] [US1] In `tests/test_email_redesign.py`, add endpoint tests per contracts/email-preferences.md:
  - `GET /email/unsubscribe?t=valid` → 200 with a form, and `email_opt_out` unchanged;
  - `POST /email/unsubscribe` → 200, opt-out true, source `link`; repeating it → 200;
  - `POST /email/unsubscribe/one-click?t=…` with body `List-Unsubscribe=One-Click` → 200 empty, source `one_click`;
  - `POST /email/resubscribe` → opt-out false, source `resubscribe`;
  - a tampered token on each endpoint → 400 and no change;
  - a token for a deleted user → 400;
  - `GET /settings/notifications` → 200 with the support email in the body.
- [X] T013 [P] [US1] In `tests/test_email_redesign.py`, add gating tests (SendGrid mocked):
  - `send_draft_reminder_email`, `send_new_template_email`, `send_inactive_reengagement_email` and `send_welcome_email` for an opted-out user send nothing, write an `EmailSendEvent` with `delivery_status='skipped_opt_out'`, and log `email_skipped_opt_out`;
  - for an opted-in user, the SendGrid `Mail` has `List-Unsubscribe` and `List-Unsubscribe-Post: List-Unsubscribe=One-Click` headers and the HTML contains the unsubscribe URL;
  - a transactional email (`send_gift_seat_email`, a report email) to an opted-out user is still sent.

### Implementation

- [X] T014 [P] [US1] Create `app/services/email_links.py` per research R4:
  - `make_token(user_id, now=None)` returns `v1.<user_id>.<issued_at>.<b64url hmac_sha256>`;
  - `verify_token(token, now=None) -> str | None` uses `hmac.compare_digest`, a TTL of `settings.email_link_ttl_days`, and rejects future timestamps (more than 5 minutes of skew);
  - `unsubscribe_urls(user) -> (page_url, one_click_url)`;
  - `list_unsubscribe_headers(user) -> dict`.

  All return `None` or `{}` when `settings.email_link_secret` is empty.
- [X] T015 [P] [US1] Create the public pages under `app/templates/pages/email_preferences/`: `confirm.html` (Unsubscribe form POST with hidden `t`), `already.html`, `done.html` (with a Resubscribe form), `resubscribed.html`, `invalid.html` and `legacy.html`. They use a standalone dark page layout (not an email), say what still arrives ("reports, invitations and account emails"), have `<meta name="robots" content="noindex">`, and contain no user email or name.
- [X] T016 [US1] Create `app/routes/email_preferences.py` and register it in `app/main.py`. The endpoints follow contracts/email-preferences.md exactly:
  - `GET /email/unsubscribe` has no side effects (FR-004);
  - `POST /email/unsubscribe` takes form `t`;
  - `POST /email/unsubscribe/one-click` takes query `t` and accepts the form body; it returns `Response(status_code=200)`, or 400;
  - `POST /email/resubscribe`;
  - `GET /settings/notifications` serves the legacy page.

  A preference change sets `email_opt_out`, `email_pref_source` (`link` | `one_click` | `resubscribe`) and `email_pref_changed_at`, and is logged as `email_pref_changed user=<id> opt_out=<bool> source=<src>` (no email address or token). Use `include_in_schema=False`. Add a comment that these routes are explicitly public and token-authorized (Principle I).
- [X] T017 [US1] In `app/services/email.py`, gate the engagement senders (`send_draft_reminder_email`, `send_new_template_email`, `send_inactive_reengagement_email`, `send_welcome_email`):
  - if `user.email_opt_out`, write the skip event (reuse `_log_campaign_email` with `delivery_status='skipped_opt_out'`), log `email_skipped_opt_out campaign=<type> user=<id>` and return `False`;
  - otherwise render through `render_email(..., category="engagement", user=user)` and pass `rendered.headers` to `send_email()`.

  Remove the hand-written `unsubscribe_link` context (`/settings/notifications`) and the template paragraphs that used it in `app/templates/email/campaigns/{draft_reminder,new_template,inactive_reengagement}.html`; the layout footer now provides the link. Make sure `_already_sent_campaign` counts `skipped_opt_out` rows as already handled.
- [X] T018 [US1] Add `email_link_secret`'s Secret Manager wiring to the deploy instructions: append `EMAIL_LINK_SECRET=EMAIL_LINK_SECRET:latest` to the `--set-secrets` lists in `/Users/tmoney/Developer/trooth_assessment/.claude/skills/deploy-dev/SKILL.md` and `deploy-prod/SKILL.md` (a separate commit and PR in the app repo). Document creating the secret (`openssl rand -base64 48 | gcloud secrets create EMAIL_LINK_SECRET --data-file=-`, and grant `trooth-run-sa` `secretAccessor`) in `specs/005-email-redesign/quickstart.md` prerequisites.

**Checkpoint**: T011–T013 pass. Unsubscribe works end to end.

---

## Phase 4: User Story 2 - Report emails lead with the same numbers as the app (Priority: P1)

**Goal**: every report email leads with the canonical headline from `report_summary`.

**Independent Test**: quickstart §5.

### Tests

- [X] T019 [P] [US2] In `tests/test_email_redesign.py`, add parity tests. For a v2.1 mentor blob (`health_score` 80, `health_band` "Maturing", `biblical_knowledge.percent` 86.2):
  - `render_mentor_report_v2_email`, `render_premium_report_email` (with a stored full report whose `executive_summary.health_score` is 99), `render_master_trooth_email` and `render_assessment_completion_email` all show "80", "Maturing" and "86.2%" (one decimal, as `summarize_mentor_blob` returns and the app shows) and never "99";
  - the Premium email contains the executive summary `one_liner` and 12-week plan phase goals;
  - a blob with no `priority_action` and no strengths renders with no empty "Priority Action" or "Strengths" headings;
  - the spiritual gifts email leads with the top 3 gifts.

### Implementation

- [X] T020 [P] [US2] Create `app/templates/email/reports/mentor_report.html`, extending `_base.html` and using `_macros`. In order:
  1. `report_headline(summary)`;
  2. Priority Action (title, description, up to 3 steps);
  3. top 3 strengths and top 3 growth areas;
  4. Biblical Knowledge % with weak topics;
  5. `button(app_url, "Open in app")`.

  `render_mentor_report_v2_email(context)` in `app/services/email.py` renders it through `render_email(..., category="transactional")`, with the context built from `master_trooth_report.build_report_context` plus `report_summary.summarize_mentor_blob(blob)`. Preheader: "<Apprentice>'s report is ready: Health Score <n> (<band>)".
- [X] T021 [P] [US2] Create `app/templates/email/reports/premium_report.html`: the same head as T020, then the executive summary (`one_liner`, trajectory note), the 12-week plan highlights (each gap's `phase_1/2/3` goals, up to 3 gaps), and 2 conversation-guide questions. `render_premium_report_email(context, full_report)` passes the report through `report_summary.public_full_report(full_report, blob)` before rendering, so its Health Score equals the blob's (FR-015).
- [X] T022 [P] [US2] Create `app/templates/email/reports/master_trooth.html`, `reports/generic_assessment.html` and `reports/assessment_complete.html` using `report_headline` where a mentor blob exists. The generic assessment shows the category scores when there's no Health Score. Rewrite `render_master_trooth_email` (removing its f-string HTML), `render_generic_assessment_email` and `render_assessment_completion_email` to use them through `render_email`, keeping their signatures.
- [X] T023 [P] [US2] Create `app/templates/email/reports/spiritual_gifts.html` (top 3 gifts with short definitions as the headline, then the full ranked list and the "Open in app" button). Rewrite `render_spiritual_gifts_report_email` to use it.
- [X] T024 [US2] Point the HTML preview and email path in `app/services/master_trooth_report.py` (`render_email_v2`) at `reports/mentor_report.html`. This also changes the mentor report **HTML preview route** (`GET /assessments/{id}/mentor-report-v2` in `app/routes/mentor_report_v2.py`), which previews the email and so is intended to show the new design. Add a test that this route returns 200 and contains the Health Score headline. Then and remove its inline f-string fallback (`master_trooth_report.py:419`) in favor of the template. Delete the superseded `mentor_report_email_template.html`, `mentor_report_premium_email_template.html`, `master_trooth_report.html`, `generic_assessment_report.html`, `spiritual_gifts_report.html` and `assessment_complete.html` once nothing references them (`grep` first). Update the catalog keys: `mentor_report`, `premium_report`, `master_trooth_report`, `generic_assessment_report`, `spiritual_gifts_report`, `assessment_complete`.

**Checkpoint**: T019 passes. Report emails match the app.

---

## Phase 5: User Story 3 - Every email looks right in every major mail app (Priority: P2)

**Goal**: all remaining emails are on the shared layout, each with a preheader and a text part.

**Independent Test**: quickstart §3.

- [X] T025 [P] [US3] Move the f-string account emails to templates:
  - `app/templates/email/account/notification.html` (subject and message, with message paragraphs escaped and newline-split);
  - `account/gift_seat.html`;
  - `account/gift_seat_revoked.html`.

  Rewrite `send_notification_email`, `send_gift_seat_email` and `send_gift_seat_revoked_email` in `app/services/email.py` to render through `render_email` (transactional), keeping their signatures, recipients and subjects.
- [X] T026 [P] [US3] Move the internal emails:
  - `app/services/metrics_reports.py`'s inline HTML (line ~80) and `metrics_report.html` become `app/templates/email/internal/metrics_report.html`;
  - `send_trivia_competition_admin_summary`'s `<pre>` HTML becomes `internal/trivia_admin_summary.html`.

  Both are category `internal` with recipients unchanged.
- [X] T027 [P] [US3] Agreement emails: make every `app/templates/email/agreements/*.html` extend the new `_base.html` with `button()` for their main link, and change `render_agreement_email` in `app/services/agreement_notifications.py` to use `render_email` (transactional). Add catalog entries with preheaders for `apprentice_invite`, `fully_signed`, `parent_invite`, `parent_resend`, `parent_resend_request`, `reschedule_request`, `reschedule_response` and `revoked`.
- [X] T028 [P] [US3] Remaining templated emails:
  - `invitation.html` → `account/invitation.html`;
  - `support_request_admin.html` → `internal/support_request_admin.html`;
  - `support_request_confirmation.html` → `account/support_request_confirmation.html`;
  - the campaign templates (`daily_trivia_reward`, `trivia_prize`, `welcome_*`, `draft_reminder`, `new_template`, `inactive_reengagement`) switch their buttons to `button()`.

  Update `app/routes/support.py` and the render functions to use `render_email`. Every catalog entry gets a written preheader (≤ 110 chars) and a footer `reason`.
- [X] T029 [US3] Remove the now-unused CSS classes from `_base.html`'s `<style>` once no template uses them (check with `grep` across `app/templates/email`). Confirm with the T005 coverage test that every catalog entry passes: preheader, text part, footer marker, size under 95 KB.

**Checkpoint**: every email renders on the shared layout. The full `pytest` suite passes.

---

## Phase 6: User Story 4 - The team can preview emails before release (Priority: P3)

**Goal**: render all emails locally and send test copies to one address.

**Independent Test**: quickstart §2.

- [X] T030 [P] [US4] In `tests/test_email_redesign.py`, add preview script tests:
  - `email_preview.render_all(out_dir)` writes `<key>.html` and `<key>.txt` for every catalog entry plus `index.html`, and returns zero failures;
  - `parse_args(["--send-to", "a@x.com,b@x.com"])` and `["--send-to", "a@x.com", "b@x.com"]` are rejected;
  - `send_previews(address, keys)` calls `send_email` only with that address and `[TEST]`-prefixed subjects (`send_email` mocked).
- [X] T031 [US4] Create `scripts/email_preview.py`:
  - render every `CATALOG` entry's `sample_context()` to `~/.cache/onlyblv/email-previews/` (override with `--out`), with an `index.html` gallery linking the HTML and text versions;
  - print and exit 1 on any render failure;
  - `--only key,key`;
  - `--send-to ADDRESS`: exactly one address, validated, refusing commas and spaces. It sends through `send_email` with `[TEST] ` subjects and engagement headers built for a fake user id, reading `SENDGRID_API_KEY` from the env or `gcloud secrets versions access latest --secret=SENDGRID_API_KEY` without printing it.

  Add a usage note to the script docstring and `specs/005-email-redesign/quickstart.md`.

---

## Phase 7: Polish & Cross-Cutting

- [X] T032 [P] Run `grep -rn "f\"\"\"" app/services/email.py app/services/metrics_reports.py app/services/master_trooth_report.py` and confirm no HTML email bodies are left as f-strings. *(Result: the only one left is `metrics_reports._fallback_html`, used only if the template fails to render.)* Confirm no template still extends a removed file.
- [X] T033 Run `.venv/bin/python -m pytest -q`; all pass (SC-007: existing email tests unchanged and passing). Also check how account deletion in `app/routes/user.py` removes the user (spec Edge Case "A user who deletes their account"). Record whether the opt-out columns are deleted with the row; if deletion anonymizes instead, confirm no email address is kept next to the opt-out, and note the result in the PR. *(Result: `account_deletion.delete_user_account` hard-deletes the `users` row, so the opt-out columns go with it.)*
- [X] T034 Run `scripts/email_preview.py` locally and review `index.html` at 375 px and 600 px widths. Fix any layout issues. Time `render_all()` over the catalog and record the per-email average in the PR (plan target: under 200 ms each). *(Result: 29 emails, 9–13 ms average, largest 12.5 KB. Checked at a true 375 px width in an iframe and at 600 px; the layout fits and wraps. The broken logo in local previews is the localhost `LOGO_URL` default; the prod logo URL returns `image/png`.)*
- [X] T035 Deploy to dev **after** creating `EMAIL_LINK_SECRET` (T018) and updating the deploy skills. Then run quickstart §3–§5: *(Done: dev revisions 00099–00102. The unsubscribe flow (confirm, one-click, already, resubscribe, invalid, legacy) was verified on a real dev account. Report parity 5/5 vs the app. `[TEST]` sends of all 29 emails to 3 owner inboxes, reviewed by the owner. Follow-ups #37–#39: white-and-gold Discipleship logo on a baked-in dark badge with a versioned filename, because Gmail caches images by URL. The owner accepted Gmail iOS showing the color-inverted, light view.)*
  - test sends to Gmail (web and iPhone), Apple Mail and Outlook, in light and dark mode;
  - unsubscribe by link and one-click, with the skip recorded and report emails unaffected;
  - 5-assessment report parity.

  Record the client × mode pass/fail table and the parity results in the PR.
- [X] T036 After merge: `/deploy-prod`, confirm `GET /settings/notifications` returns 200 on prod, and send one preview to the owner's inbox against the prod config (quickstart §6). *(Done: `/deploy-prod` revision trooth-backend-00221-z6v; `/settings/notifications` 200, invalid link 400, `email_logo_v2.png` 200, no `email_link_secret_missing` errors. One prod-config test email confirmed links use the prod host.)*

---

## Dependencies & Execution Order

- **Phase 1** (T001; T002 and T003 in parallel) → **Phase 2** (T004 and T005 tests; T006 → T007 → T008, T009 and T010).
- **US1** (T011–T018) and **US2** (T019–T024) both depend only on Phase 2 and touch different functions. They can run in parallel, except that T017 and T020–T023 all edit `app/services/email.py`, so those run one after another.
- **US3** (T025–T029) depends on Phase 2. T028's campaign button changes come after T017.
- **US4** (T030–T031) depends on the catalog (T009) and is best done after US3, so it covers every entry.
- **Polish** last. T035 needs T018's secret **and** T018's app-repo PR (deploy skills with `EMAIL_LINK_SECRET`) merged before `/deploy-dev`; otherwise the deploy drops the secret and engagement emails go out without unsubscribe links.

## Parallel Opportunities

- Phase 1: T002 and T003.
- Phase 2 tests: T004 and T005.
- US1: T011, T012, T013 (tests), T014 and T015 together.
- US2: T020–T023 templates in parallel (their `email.py` edits in sequence).
- US3: T025, T026, T027 and T028 touch different templates and services.

## Implementation Strategy

1. **MVP = Phase 1 + Phase 2 + US1**: shared layout everywhere (via the new `_base.html`) plus a working unsubscribe. This fixes the compliance gap first.
2. **US2**: report emails lead with the app's numbers.
3. **US3**: migrate the remaining standalone and f-string emails and give every email a preheader.
4. **US4**: preview tool, then dev test sends in real mail apps, then prod.
