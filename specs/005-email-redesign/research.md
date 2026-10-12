# Research: Email Redesign

## R1. Layout technique for a dark brand that survives mail apps

- **Decision**: a table-based 600 px layout (outer full-width table, inner fixed table) with
  `bgcolor` attributes *and* inline `background-color` on every table and cell. Text colors are set
  inline on each element. `<meta name="color-scheme" content="dark">` and
  `<meta name="supported-color-schemes" content="dark">`, plus `:root { color-scheme: dark }`,
  tell Apple Mail and iOS not to invert. Surfaces use near-black (`#0b0b0b`) and dark gray
  (`#1a1a1a`), not pure black, so the Gmail app's partial inversion leaves them alone. Text is
  off-white (`#f2f2f2`) and the accent is gold `#d4af37`. Accent text and button labels go only on
  dark backgrounds or a solid gold fill, never transparent, so inverted or forced-light renders
  stay readable. A hidden preheader `<div>` with a zero-width-space filler comes first in `<body>`.
- **Rationale**: Gmail strips some `<head>` styles and doesn't support all of CSS. Outlook
  (Windows) renders with Word and needs tables, `bgcolor` and VML. Gmail apps auto-adjust light
  colors in dark mode, but leave already-dark backgrounds mostly as they are. Setting both the
  attribute and the inline style covers both rendering paths. Owner decision: "dark brand,
  hardened."
- **Alternatives**: a light design with dark-mode media queries (rejected: changes the brand, and
  Gmail ignores `prefers-color-scheme`); MJML (rejected: adds a Node toolchain to a Python service
  for about 35 templates).

## R2. Buttons in Outlook

- **Decision**: a `button(url, label)` Jinja macro that outputs a VML `v:roundrect` inside
  `<!--[if mso]>` for Outlook (Windows), and a padded `<a>` in a table cell (`bgcolor` gold, black
  label, 6 px radius) for everything else. The visible label is real text, not an image.
- **Rationale**: Outlook (Windows) ignores padding and border-radius on `<a>`. The VML "bulletproof
  button" is the standard fix.

## R3. CSS inlining and plain text

- **Decision**: render the Jinja template, run it through `css_inline.CSSInliner(keep_style_tags=True)`
  (so media queries for phones stay in `<style>` for clients that support them), then build the
  plain-text version with `html2text` (`body_width=0`, links kept as `text (url)`, images ignored,
  the preheader block removed first). An email over 95 KB logs a warning, before Gmail's 102 KB
  clipping.
- **Rationale**: one source (the HTML template) gives both parts, so they can't drift. css-inline
  is fast, maintained and dependency-free. html2text gives readable Markdown-like text.
- **Alternatives**: premailer (slower, less maintained); hand-written `.txt` templates (about 35
  more files that would drift).

## R4. Unsubscribe token

- **Decision**: an HMAC-SHA256 over `v1.<user_id>.<issued_at_epoch>` with `EMAIL_LINK_SECRET`,
  base64url, in the form `v1.<user_id>.<issued_at>.<sig>`. It's verified with `hmac.compare_digest`
  and is valid for 400 days. One token per user per email (not per campaign): unsubscribing turns
  off all engagement email.
- **Rationale**: no sign-in (spec FR-003), can't be forged, and needs no database lookup to verify.
  400 days keeps links in old emails working for over a year. A dedicated secret means rotating the
  cron secret doesn't break links.
- **Alternatives**: `itsdangerous` (an extra dependency for about 20 lines); a random token
  stored per user (needs a table and lookups); reusing `CRON_SECRET` (rotation coupling, and it
  mixes trust domains).

## R5. One-click unsubscribe (RFC 8058) and link scanners

- **Decision**: engagement emails send these headers:
  - `List-Unsubscribe: <https://<api>/email/unsubscribe/one-click?t=<token>>, <mailto:<support>?subject=unsubscribe>`
  - `List-Unsubscribe-Post: List-Unsubscribe=One-Click`

  The visible link goes to `GET /email/unsubscribe?t=…`, which only shows a confirm page with a
  form. The form POSTs to `/email/unsubscribe`. Mail apps POST `List-Unsubscribe=One-Click` to the
  one-click URL, which unsubscribes immediately and returns 200.
- **Rationale**: Gmail and Yahoo bulk-sender rules require RFC 8058 one-click. Corporate link
  scanners prefetch GET links, so GET must have no side effects (spec FR-004).

## R6. Which emails are engagement vs transactional

- **Decision**: categories live in `email_catalog.py`, and campaign senders gate on them:
  - **engagement:** `draft_reminder`, `new_template`, `inactive_reengagement`, `welcome_mentor`,
    `welcome_apprentice`;
  - **transactional:** everything user-facing, including trivia prize and reward emails;
  - **internal:** metrics report, trivia admin summary.

  A skip writes an `EmailSendEvent` with `delivery_status='skipped_opt_out'` and the campaign type.
  That keeps the existing campaign dedupe working: a skipped send counts as handled, so the
  reminder isn't retried every run.
- **Rationale**: matches the spec assumptions. Recording skips in the existing table keeps
  reporting in one place.

## R7. Report headline numbers

- **Decision**: a `report_headline(summary, priority_action, strengths, gaps)` macro is fed from
  `report_summary.summarize_mentor_blob()` (the same function the app endpoints use) and
  `build_report_context`. The Premium email uses `public_full_report()` for its executive summary,
  so the Health Score equals the blob's. The spiritual gifts email uses its own headline (top 3
  gifts) in the same partial style.
- **Rationale**: spec FR-014 and FR-015 require exact parity with the app, and spec 004 already
  made `report_summary` the single source.

## R8. "Open in app" and footer links

- **Decision**: the app ships on iOS **and** Android, so no single store link works for everyone.
  - **"Open in app" button:** goes to `settings.app_landing_url` (default
    `https://onlyblv.com/#apps`, the homepage section with both the App Store and Google Play badges
    for T[root]H Discipleship).
  - **Footer:** shows both store links, `settings.ios_app_store_url` and the new
    `settings.android_play_store_url` (default
    `https://play.google.com/store/apps/details?id=com.trooth.flutterTroothAssessment`, the listing
    linked from onlyblv.com), plus the support email (`settings.support_email`, default
    `admin@onlyblv.com`), "You're receiving this because…" text from the catalog entry, and an
    unsubscribe link only on engagement emails.
- **Rationale**: Gmail and Outlook don't open custom `trooth://` schemes, and the app has no
  universal links yet. A landing page with both badges works on any device. Switching to universal
  links later is a one-setting change, with no template edits.
- **Alternatives**: iOS App Store link only (rejected: sends Android users to the wrong store);
  sniffing the device in the email (not possible in email).

## R9. Preview tool

- **Decision**: `scripts/email_preview.py` loads the catalog and renders every entry's
  `sample_context()` to `~/.cache/onlyblv/email-previews/<key>.html` and `.txt`, with an
  `index.html` gallery, and prints failures (exit 1 if any). `--send-to <address>` (exactly one
  address; refuses lists and commas) sends the chosen or all emails with subjects prefixed
  `[TEST]`, through the normal send path, using the SendGrid key from Secret Manager. `--only key,key`
  limits the set.
- **Rationale**: spec FR-018 and FR-019. Using the same catalog as the tests means a new email type
  can't skip either.
