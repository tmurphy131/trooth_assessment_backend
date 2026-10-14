# Data Model: Close Critical Authorization Holes

No schema changes. These are the existing entities and the rules that are now enforced.

## User (`users`)
| Field | Rule after this change |
|---|---|
| `id` | Firebase UID from the verified token. Set at creation. Changed **only** by a legacy re-link when `email_verified` is true (R4). Never from the request body |
| `email` | From the token at creation. Unique (existing constraint). Never taken from the request body |
| `role` | `apprentice` or `mentor` at self-signup. `admin` only by operator action. **Immutable through signup** after creation |
| `name` | May update on repeat signup (unchanged behavior) |

Signup decision table (token claims: `uid`, `email`, `email_verified`; body: `role`, `name`):

| Account by `uid` | Account by token `email` | Result |
|---|---|---|
| exists | n/a | 200, return it. Update `name` only. Re-sync claims to the **stored** role |
| none | none | `role=admin` → 403. Otherwise create with the token `email` → 200 |
| none | exists, `email_verified` | Re-link the id to `uid` → 200, role unchanged. If foreign keys block it (the account has linked data), 409 with the same generic message |
| none | exists, not verified | 409, generic "verify your email" message (FR-013) |
| token has no email | n/a | 400 "sign-in has no email" |

## MentorApprentice (`mentor_apprentice`)
Created only by invitations, invite codes and signed agreements. There's no direct-create route anymore.

## Agreement (`agreements`) / AgreementToken
`awaiting_parent` → `fully_signed` only through a valid, unused, unexpired parent `AgreementToken` (`POST /agreements/public/{token}/sign`).
