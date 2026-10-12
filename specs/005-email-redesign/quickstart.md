# Quickstart: validate Email Redesign

## Prerequisites

- `.venv` with the new requirements (`css-inline`, `html2text`).
- Secret `EMAIL_LINK_SECRET` created once in Secret Manager. It's shared by dev and prod. Never paste
  or print it. The run service account needs `secretAccessor`:
  ```bash
  openssl rand -base64 48 | tr -d '\n' | gcloud secrets create EMAIL_LINK_SECRET --data-file=- --project=trooth-prod
  gcloud secrets add-iam-policy-binding EMAIL_LINK_SECRET --project=trooth-prod \
    --member=serviceAccount:trooth-run-sa@trooth-prod.iam.gserviceaccount.com --role=roles/secretmanager.secretAccessor
  ```
- The app repo's deploy skills (`.claude/skills/deploy-dev` and `deploy-prod`) include
  `EMAIL_LINK_SECRET=EMAIL_LINK_SECRET:latest` in `--set-secrets` (branch `chore/email-link-secret`),
  merged before `/deploy-dev`.
- Test inboxes the team controls: one Gmail (checked on web and the iPhone app), one Apple Mail
  (iCloud or another account in Mail.app), one Outlook (outlook.com and, if available, Outlook
  for Windows).
- Guide test accounts on dev (`~/.config/onlyblv/test_accounts.env`).

## 1. Automated

```bash
.venv/bin/python -m pytest tests/test_email_redesign.py -q
.venv/bin/python -m pytest -q
```

Expected: every catalog entry renders on the shared layout, with a preheader, a text part and
inlined styles. Engagement emails carry the unsubscribe link and headers. The endpoint tests cover
valid, repeated, invalid and legacy tokens, and gating skips opted-out users only for engagement
emails.

## 2. Preview (US4, SC-006)

```bash
.venv/bin/python scripts/email_preview.py            # renders all → ~/.cache/onlyblv/email-previews/index.html
open ~/.cache/onlyblv/email-previews/index.html
```

Expected: every email type is listed with its HTML and text versions, and "0 failed". Check each
in a browser at 375 px and 600 px widths.

## 3. Test sends to real mail apps (US3, SC-003, SC-004)

```bash
.venv/bin/python scripts/email_preview.py --send-to <gmail-test-address>
.venv/bin/python scripts/email_preview.py --send-to <apple-test-address>
.venv/bin/python scripts/email_preview.py --send-to <outlook-test-address>
```

Expected, in each app in **light and dark mode**:

- readable text, the logo, a working gold button and the same footer;
- the inbox preview line is the catalog preheader;
- no Gmail "[Message clipped]";
- subjects start with `[TEST]`, and nothing goes to any other address.

Record a pass or fail table (email type × client × mode) in the PR.

## 4. Unsubscribe on dev (US1, SC-001, SC-002)

1. Deploy to dev. Trigger a draft reminder for the guide apprentice (a stale draft and the campaign
   cron, or the campaign test hook) so it arrives in a test inbox.
2. Gmail shows "Unsubscribe" next to the sender; use it. Expected: the account's `email_opt_out`
   becomes true with `email_pref_source='one_click'`.
3. Resubscribe from the page. Then open the email's footer link: the confirm page appears and
   nothing has changed yet. Tap Unsubscribe and you're unsubscribed (`email_pref_source='link'`).
4. Trigger the reminder again. It isn't sent, and an `EmailSendEvent` with
   `delivery_status='skipped_opt_out'` is written. Submit an assessment: the report email still
   arrives.
5. Edit one character of the token: the invalid-link page appears (400) and no account changes.
   `GET /settings/notifications` shows the legacy page (200, not 404).

## 5. Report parity (US2, SC-005)

Submit 5 Master assessments on dev for the guide apprentice, with the premium guide mentor linked.
For each, compare the mentor email's Health Score, band, Biblical Knowledge % and priority action
with the app's report. The Premium email's executive-summary Health Score equals the free one.

## 6. Prod

After merge: `/deploy-prod` (the migrate job adds the columns). Confirm `GET /settings/notifications`
returns 200 on prod. Send one preview `--send-to` your own inbox against prod config to confirm the
links use the prod API host.
