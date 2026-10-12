# Data Model: Email Redesign

## User (table `users`): new columns

| Column | Type | Default | Rules |
|---|---|---|---|
| `email_opt_out` | Boolean, not null | `false` (server default `false`) | true = no engagement emails |
| `email_pref_changed_at` | DateTime, nullable | null | set on every change |
| `email_pref_source` | String(16), nullable | null | `link` \| `one_click` \| `resubscribe` |

Migration: `alembic/versions/20261012_email_preferences.py`. It adds the three columns (existing rows
get `false`/null) and `downgrade()` drops them. The columns are deleted with the user row (no
separate table).

## EmailSendEvent (existing table): new value

- `delivery_status = 'skipped_opt_out'` for an engagement email not sent because of the opt-out.
  `campaign_type` and `context` are filled as for a real send, so campaign dedupe treats it as
  handled.

## EmailType (code registry, `app/services/email_catalog.py`)

| Field | Type | Notes |
|---|---|---|
| `key` | str | unique, e.g. `draft_reminder`, `mentor_report`, `gift_seat` |
| `template` | str | path under `app/templates/email/` |
| `category` | `engagement` \| `transactional` \| `internal` | engagement → unsubscribe link and headers, opt-out gate |
| `preheader` | str or callable(context) | inbox preview line, ≤ 110 chars |
| `reason` | str | footer "You're receiving this because…" |
| `sample_context` | callable() → dict | realistic data for the preview and tests |

Every email the system sends MUST have exactly one entry (enforced by a test that the catalog keys
cover every template under `app/templates/email/` except `_base.html` and `_macros.html`).

## RenderedEmail (value object, `app/services/email_render.py`)

`html` (CSS inlined), `text` (plain text), `preheader`, `size_bytes`, `headers` (dict; the
`List-Unsubscribe` pair for engagement emails).

## Unsubscribe token

`v1.<user_id>.<issued_at_epoch>.<base64url(hmac_sha256(EMAIL_LINK_SECRET, "v1.<user_id>.<issued_at_epoch>"))>`.
Valid if the signature matches, `issued_at` is no more than 400 days old and no more than 5 minutes
in the future (clock skew), and the user exists.

## Preference state

```text
opted in ──(confirm on page | one-click POST)──► opted out ──(resubscribe)──► opted in
(repeating either action is a no-op that returns the same success page)
```
