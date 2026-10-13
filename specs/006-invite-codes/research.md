# Research: Invite Codes

## R1. Code format and generation

- **Decision**: 8 characters drawn with `secrets.choice` from `23456789ABCDEFGHJKMNPQRSTUVWXYZ` (31 symbols: no 0/O, 1/I/L). Stored as 8 uppercase characters with no dash. Every API response, email and page shows it as `XXXX-XXXX`.
- **Rationale**: 31^8 ≈ 8.5 × 10^11 possible codes. Pending invites number in the hundreds, so even without a rate limit a random guess has about a 1-in-a-billion chance of hitting one. With the FR-008 limit, guessing is not a realistic attack. Leaving out lookalike characters prevents typos when a code is read aloud or texted. Storing the code without the dash makes lookups exact matches. `format_invite_code` is idempotent (it normalizes before adding the dash), so formatting a value twice is harmless and the response serializer can always format.
- **Alternatives considered**: 6 characters (about 8.9 × 10^8, too close to guessable if the rate limit ever fails); digits only (shorter alphabet, so longer codes); reusing the UUID token (too long to type).

## R2. Uniqueness

- **Decision**: A unique index on `apprentice_invitations.code`. On insert, generate a code, check that no row has it, then insert. If the unique index still rejects it, retry up to 5 times.
- **Rationale**: Collisions are astronomically rare at this volume. The index guarantees uniqueness, so the code doesn't need to be clever.

## R3. Backfilling existing invites (FR-005)

- **Decision**: In one Alembic migration: add `code` as nullable, generate a code for every existing row in Python, then make the column NOT NULL and add the unique index. `downgrade()` drops the index and the column. The migration has its **own copy** of the alphabet and generator rather than importing from `app`. No existing migration imports app code, and a migration must not change when app code changes later.
- **Rationale**: Every invite then has a code, and the app never sees a null. Tests build the schema with `create_all` from the model, so the model declares `nullable=False, unique=True` with a default generator.

## R4. Rate limiting failed redemptions (FR-008)

- **Decision**: A new table `invite_code_attempts` (`id`, `user_id`, `invitation_id` nullable, `succeeded`, `created_at`). Before looking up a code, count the user's failed attempts in the last hour. At 10 or more, return 429 with a `Retry-After` header. Each attempt is recorded and committed before the response, including failures.
- **Rationale**: `RateLimitMiddleware` keeps its counts in memory on each Cloud Run instance. Counts reset on restart and aren't shared between instances, so it can't hold a per-user hourly limit. A small table holds the count reliably and also serves as the audit trail for FR-012. The middleware is turned off when `ENV=test`, so a table-based limit is also the only one that can be tested.
- **Alternatives considered**: Redis (new infrastructure); the existing middleware (not durable, and it limits all requests rather than failed redemptions); a counter column on `users` (mixes concerns, and hourly windows get awkward).
- **Housekeeping**: Rows are small. Pruning (for example, deleting rows older than 30 days) is optional and can happen in an existing cron later. It's out of scope here.

## R5. Two people redeeming the same code at once

- **Decision**: Mark the invite accepted with a conditional update: `UPDATE apprentice_invitations SET accepted = true WHERE id = :id AND accepted = false`. If no row changed, someone else redeemed it first, so return "already used" and roll back. Only the request that changed the row goes on to create the pairing.
- **Rationale**: This works the same on PostgreSQL and SQLite (which the tests use) and needs no row locks.

## R6. Sharing logic between accept-by-token and redeem

- **Decision**: Move the accept-by-token flow (check expiry and accepted, mark accepted, create or reactivate the `MentorApprentice` row) into `app/services/invitations.py` as `accept_invitation(db, invitation, apprentice) -> str`. Both routes call it. The pure code helpers (`generate_invite_code`, `normalize_invite_code`, `format_invite_code` and the alphabet constants) live in a separate `app/services/invite_codes.py` that imports no models.
- **Rationale**: Principle VII says business logic belongs in `app/services/`. With one function, the two acceptance paths can't drift apart. The helpers are split out because the `ApprenticeInvitation` model uses `generate_invite_code` as its column default, while `invitations.py` imports that model. Keeping both in one module would create a circular import.

## R7. Securing accept-by-token (FR-010)

- **Decision**: `POST /invitations/accept-invite` uses `require_apprentice`. `InviteAccept.apprentice_id` becomes optional. If it is present and doesn't match `current_user.id`, return 403. The apprentice is always `current_user`.
- **Compatibility**: The current app sends the sign-in token on every call through `_ApiClient` (`lib/services/api_service.dart:94`). It also sends `apprentice_id` set to the Firebase UID, which equals `users.id`. One status code changes: a signed-in caller who isn't an apprentice used to get 404 "Apprentice not found" and now gets 403. The app already treats both as failures, so this is acceptable. Before release, check one older store build to confirm it also sends auth here.

## R8. Logging

- **Decision**: Use `logging.getLogger(__name__)` in the service and routes. Log `invite.redeem` with `user_id`, `invitation_id` (when one was found) and the outcome (`ok`, `not_found`, `expired`, `used`, `rate_limited`). Never log the code or the token. While editing `invite_apprentice`, replace its two `print` calls that print the apprentice's email with logger calls that log the invitation ID instead.
