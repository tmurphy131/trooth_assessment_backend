# Research: Link Agreements and Gift Seats to Apprentice Accounts

## R1. One check for "actively connected"

- **Decision**: Add `has_active_connection(db, mentor_id, apprentice_id) -> bool` in a new `app/services/mentorship.py`. It's true only for a `MentorApprentice` row with `active == True`. Agreement creation (FR-001) and the three gift-by-ID checks in `app/routes/subscriptions.py` (lines ~478, ~610, ~804; FR-006) all use it.
- **Rationale**: Today each seat path has its own query, and none of them checks `active`. That's how an ended mentorship passes. One helper keeps the rule identical everywhere (Principle VII: logic in services).
- **Alternatives**: Adding `active == True` inline three more times would work, but the next copy is just as easy to get wrong.

## R2. Creating an agreement by account ID

- **Decision**: `AgreementCreate` gains `apprentice_id: str | None = None`, and `apprentice_email` becomes `EmailStr | None = None`. A model validator requires at least one of them (otherwise 422). In `create_agreement`:
  - **With** `apprentice_id`: load the user; require role apprentice and `has_active_connection` (else 403 `"This apprentice is not connected to you"`). Then set `Agreement.apprentice_id`, set `apprentice_email` to the account email lowercased, and set `apprentice_name` to the payload name or the account name.
  - **Without** it: unchanged.
- **Rationale**: It's additive. Old clients send an email and get today's behavior. Storing the account email keeps every notification path, which sends to `ag.apprentice_email`, working. Apple relay addresses forward mail.
- **Alternatives**: A separate endpoint was rejected as needless duplication. Deriving the apprentice from the email was rejected because that's the bug.

## R3. Who may sign in the app

- **Decision**: In `apprentice_sign`, replace `if effective_email != ag.apprentice_email: 403` with a check that allows the signer if `ag.apprentice_id == user.id` **or** `effective_email == ag.apprentice_email`. Everything else is unchanged, including the `ENV=test` header shortcut and the later `ag.apprentice_id = header_uid or user.id`.
- **Edge**: If `ag.apprentice_id` is set to someone else, the email match is **not** enough. An agreement tied to account X can't be signed by account Y that happens to have the address. Rule: `allowed = (ag.apprentice_id == user.id) or (ag.apprentice_id is None and email matches)`.

## R4. Attaching agreements when an invite is accepted (FR-004)

- **Decision**: Inside `accept_invitation` (`app/services/invitations.py`), after the relationship is created, reactivated or already active, run:
  `UPDATE agreements SET apprentice_id = :apprentice WHERE mentor_id = :invitation.mentor_id AND apprentice_id IS NULL AND lower(apprentice_email) = lower(:invitation.apprentice_email)`.

  This goes through a helper `attach_pending_agreements(db, mentor_id, email, apprentice_id) -> int` in `app/services/mentorship.py`, and the count is logged. It runs in the same transaction, which the caller commits. Both `POST /invitations/redeem` and `POST /invitations/accept-invite` go through `accept_invitation`, so both get it.
- **Rationale**: The invitation email is exactly what the mentor typed for both the invite and the agreement. Requiring the same mentor **and** that email makes a wrong attach practically impossible. Already-tied agreements are skipped by `apprentice_id IS NULL`.
- **Signed-already case**: an agreement signed through the emailed link before the account existed has `apprentice_id` null, and `_activate_relationship` returned early. The invite acceptance itself creates or reactivates the relationship, so attaching the ID is enough. The status already reflects the signatures.
- **Alternatives**: Matching by email at sign-up or login was rejected because it's the same email mismatch the feature exists to avoid. A separate "claim agreement" code was rejected as more UI for a case the invite code already covers.

## R5. Reading agreements stays "ID or email"

- **Decision**: No change. Every apprentice-side read already uses `(apprentice_id == user.id) | (apprentice_email == user.email)`: `/agreements/my`, `GET /agreements/{id}`, `/apprentice/agreements/pending`, the request-resend and request-reschedule calls, the ending-mentorship check, and account deletion. Once R2 or R4 fills in `apprentice_id`, everything works. A regression test pins each of these for an agreement tied by ID whose email differs from the account (FR-005).

## R6. Gift-code redemption hardening

- **Decision**: In `redeem_gift_code` (`app/routes/subscriptions.py`):
  - change `user: User = Depends(get_current_user)` to `Depends(require_apprentice)` (403 for other roles, FR-007);
  - change the success log to `logger.info("Gift code redeemed: user_id=%s seat_id=%s mentor_id=%s", ...)` with no emails (FR-008).

  The body and response shape (`success` / `message`) are unchanged.
- **Compatibility**: The app has no gift-code entry screen yet, so no released client calls this with a mentor account.

## R7. Testing approach

- **Decision**: New `tests/test_connected_apprentice_linking.py`, using real `mentor_user` / `apprentice_user` rows and `app.dependency_overrides[get_current_user]` (the pattern from `tests/test_invite_codes.py`). Agreement templates are seeded directly in the database. Gift-seat tests create `MentorPremiumSeat` rows directly and patch `is_mentor_premium` where an endpoint requires it. No RevenueCat calls (Principle VIII).
