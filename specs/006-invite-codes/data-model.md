# Data Model: Invite Codes

Migration: `alembic/versions/20261013_invite_codes.py` (revision `20261013_invite_codes`, down_revision `20261012_email_prefs`).

## ApprenticeInvitation (existing table `apprentice_invitations`, changed)

| Field | Change | Notes |
|-------|--------|-------|
| `code` | **new** `String(8)`, NOT NULL, unique index `ix_apprentice_invitations_code` | Canonical form: uppercase, no dash. Model default is `generate_invite_code()` from `app/services/invite_codes.py`, a pure module with no model imports. Existing rows are backfilled by the migration, which has its own copy of the generator. |
| `token`, `apprentice_email`, `apprentice_name`, `mentor_id`, `expires_at`, `accepted` | unchanged | `token` stays for email links and accept-by-token. |

**State transitions** (unchanged; the code is just another way in):

```
pending (accepted=false, expires_at > now)
   ├─ accept-by-token / redeem-code ─► accepted (accepted=true)   [conditional update, once only]
   ├─ time passes ─────────────────► expired (expires_at <= now)  [derived, not stored]
   └─ mentor revokes ──────────────► deleted                      [row removed]
```

**Validation**
- Input is normalized: remove all whitespace (internal and surrounding) and `-`, uppercase. Anything that isn't then 8 characters from the alphabet is answered with 404 (not found) without a database lookup, and still counts as a failed attempt.

## InviteCodeAttempt (new table `invite_code_attempts`)

| Field | Type | Notes |
|-------|------|-------|
| `id` | String (uuid4) PK | |
| `user_id` | String, FK `users.id` ON DELETE CASCADE, indexed | Who tried to redeem |
| `invitation_id` | String, nullable, no FK | Set when the code matched an invite. No FK, so deleting a revoked invite doesn't cascade into the audit rows. |
| `succeeded` | Boolean, NOT NULL | |
| `created_at` | DateTime (naive UTC), indexed with `user_id` | Composite index `(user_id, created_at)` for the hourly count |

**Rule**: if `count(succeeded = false AND created_at > now - 1h) >= 10` for this user, the redemption returns 429 before any lookup. Rate-limited attempts are not recorded. The window is rolling, so the user can try again one hour after the **oldest** of the counted failures. That allows one more attempt, and each further attempt opens up as the next-oldest failure ages out. `Retry-After` is the number of seconds until the oldest counted failure is one hour old (minimum 1).

**Account deletion**: `app/services/account_deletion.py` deletes related rows table by table with `_safe_delete` and doesn't rely on cascades. It MUST add `_safe_delete(db, InviteCodeAttempt, InviteCodeAttempt.user_id == user_id, "invite_code_attempts")` for every role. The FK cascade is a backstop.

## MentorApprentice (existing, unchanged)

Created, or reactivated (`active = true`), by the shared `accept_invitation` service. This is the same behavior as `accept_invite` today.
