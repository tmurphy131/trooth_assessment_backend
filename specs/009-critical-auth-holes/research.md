# Research: Close Critical Authorization Holes

## R1. Which identity fields to trust
- **Decision**: Trust only the verified Firebase ID token's `uid`, `email` and `email_verified`. Ignore `uid` and `email` from the request body for lookup and storage.
- **Rationale**: The token is signed by Firebase and checked with `verify_id_token`, while the body is attacker-controlled. Today `create_user` matches `User.email == body.email`, which is the takeover vector.
- **Alternatives**: Validating that `body.email == token.email` and rejecting a mismatch. That's possible, but mismatches can happen legitimately (casing, Apple private relay versus typed email). Ignoring the body is simpler and never breaks the app.

## R2. What happens to `role` on an existing account
- **Decision**: Never change it at signup. A repeat signup returns the stored account with 200, whatever `role` the body sends, and custom claims are re-synced to the **stored** role.
- **Rationale**: FR-003. The app's Firestore rules already fix the role once (`firestore.rules:18-26`). The original reason for updating the role ("old auto-create code") is gone, because `get_current_user` no longer auto-creates (`auth.py:121-127`).
- **Alternatives**:
  - Return 409 on a role mismatch. Rejected: released apps only swallow errors containing "409/exist", and a 409 here could confuse the role-selection retry. A quiet 200 is safer.
  - Allow changing the role while the account has no activity. Rejected as unnecessary complexity.

## R3. Admin at signup
- **Decision**: Return 403 for `role=admin` on a **new** account. For an existing account the role is ignored anyway (R2), so an existing admin re-posting stays admin and a non-admin can't become one. Admins are granted by an operator (database update + `set_custom_user_claims`) outside the app.
- **Rationale**: FR-005. The app's UI only offers mentor and apprentice.
- **Alternatives**: Remove `admin` from `UserCreate`'s enum. Rejected because it gives a 422, a less clear error, and the schema enum is shared.

## R4. Legacy email re-link
- **Decision**: In both `create_user` and `get_current_user`, when no account matches the token `uid` but one matches the token `email`:
  - if `email_verified` is true, re-link (set `id` to the token uid), as today
  - if not, refuse: 409 at signup, 404 "complete registration" from `get_current_user`.

  The re-link is wrapped so a foreign-key failure (an account that has linked data) returns 409 instead of 500.
- **Rationale**: FR-007, the same takeover class. Google and Apple tokens carry `email_verified: true`. Email/password accounts are unverified until verified, but they get one Firebase account per email, so a legitimate re-link for them is rare.
- **FK behavior**: 19 foreign keys reference `users.id` without `ON UPDATE CASCADE`. On Postgres, re-linking an account that has rows pointing at it fails. That's existing behavior, now surfaced as 409. Making re-link work for accounts with data is out of scope.
- **Alternatives**: Remove re-link entirely. Rejected: it's how accounts that predate the current sign-in identity keep working.

## R5. Removing routes rather than securing them
- **Decision**: Delete both routes outright.
- **Rationale**:
  - **Parent sign:** the token flow (`/public/{token}/sign`) is the real mechanism. There's no legitimate caller for an id-based parent signature: a parent has no account.
  - **Assign-apprentice:** links come from `invitations.py`, invite codes (spec 006) and `agreements._activate_relationship`. The client function is broken (it sends a JSON body to a query-param route) and is never invoked.
- **Alternatives**: Add admin auth to `assign-apprentice` for support use. Rejected for now, because nobody uses it. If support needs it later, it should be a spec'd admin tool.

## R6. Testing signup without Firebase
- **Decision**: Monkeypatch `app.services.auth.auth.verify_id_token` to return crafted claims per test, and `app.routes.user.auth.set_custom_user_claims` to record calls. Stub the welcome-email background task (`send_welcome_email`).
- **Rationale**: `verify_token` calls `firebase_admin.auth.verify_id_token`, with no existing test seam, and Principle VIII forbids live calls.

## R7. Post-release audit
- **Decision**: Add `scripts/audit_admin_accounts.py`. It's read-only, takes a `DATABASE_URL`, and prints the id, created_at and role for every `role=admin` user. It also prints users whose Firebase custom-claim role differs from the database role, through `firebase_admin.auth.get_user` when credentials are available. It never writes.
- **Rationale**: SC-006. The hole may already have been used.
- **Limit**: users have no role-change history, and the old signup also re-set Firebase claims to the new role, so the claim check can't reveal an apprentice-to-mentor escalation. That's covered by R8.

## R8. Finding past role changes in request logs
- **Decision**: After the prod deploy, run a Cloud Logging query for `POST /users/` requests that returned 200, within the log retention window (30 days by default). Cross-check each caller uid against the account's `created_at`. A 200 for an account created well before that request is a repeat signup that may have changed its role. List them for manual review.
- **Rationale**: This is the only record of past role changes. It's read-only.
- **Alternatives**: Adding a role-history column now. Rejected: it can't recover the past, and it's not needed going forward because signup can no longer change roles.
