# Contract: email preferences (public) and email headers

All endpoints below are **public** (no Firebase token) and authorized only by the signed token `t`
([data-model.md](../data-model.md#unsubscribe-token)). They return HTML pages with the T[root]H
dark design, except the one-click endpoint, which returns an empty 200.

## `GET /email/unsubscribe?t=<token>`

Confirm page. **No side effects** (safe for link scanners).

| Case | Status | Page |
|---|---|---|
| valid token, opted in | 200 | "Stop reminder and announcement emails?" + **Unsubscribe** button (form POST) |
| valid token, already opted out | 200 | "You're already unsubscribed" + **Resubscribe** button |
| invalid, tampered, expired or unknown user | 400 | "This link isn't valid. Use the link in a recent email, or contact support." No account details. |

## `POST /email/unsubscribe`

Form body: `t=<token>`. Sets `email_opt_out=true`, `email_pref_source='link'`,
`email_pref_changed_at=now`.

| Case | Status | Page |
|---|---|---|
| valid | 200 | "You're unsubscribed. You'll still get reports, invitations and account emails." + **Resubscribe** |
| already opted out | 200 | same page (idempotent) |
| invalid | 400 | invalid-link page |

## `POST /email/unsubscribe/one-click?t=<token>`

RFC 8058. Body `List-Unsubscribe=One-Click` (form-encoded). Sets `email_opt_out=true`,
`email_pref_source='one_click'`.

| Case | Status | Body |
|---|---|---|
| valid (or already opted out) | 200 | empty |
| invalid | 400 | empty |

## `POST /email/resubscribe`

Form body: `t=<token>`. Sets `email_opt_out=false`, `email_pref_source='resubscribe'`.

| Case | Status | Page |
|---|---|---|
| valid | 200 | "You're subscribed again." |
| invalid | 400 | invalid-link page |

## `GET /settings/notifications` (legacy link in emails sent before this feature)

| Case | Status | Page |
|---|---|---|
| any | 200 | "To unsubscribe, use the Unsubscribe link at the bottom of any newer T[root]H email, or reply to it and we'll take care of it." Includes the support email. (No token, so the user can't be identified.) |

## Email headers (engagement emails only)

```text
List-Unsubscribe: <https://<API>/email/unsubscribe/one-click?t=<token>>, <mailto:<support_email>?subject=unsubscribe>
List-Unsubscribe-Post: List-Unsubscribe=One-Click
```

The visible footer link points to `GET https://<API>/email/unsubscribe?t=<token>`. Transactional
and internal emails carry neither header nor link.

## Send behavior

- Engagement email to an opted-out user: not sent. An `EmailSendEvent` is written with
  `delivery_status='skipped_opt_out'`, and `email_skipped_opt_out campaign=<type> user=<id>` is
  logged.
- Missing `EMAIL_LINK_SECRET`: the engagement email is sent **without** an unsubscribe link or
  headers, and `email_link_secret_missing` is logged at ERROR. This never signs with a default key.
