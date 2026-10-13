---

description: "Task list for linking agreements and gift seats to apprentice accounts"
---

# Tasks: Link Agreements and Gift Seats to Apprentice Accounts

**Input**: Design documents from `/specs/007-connected-apprentice-linking/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api.md, quickstart.md

**Tests**: Per constitution Principle VIII, test tasks are REQUIRED for every new or changed endpoint: the success path plus applicable authorization failures, using conftest fixtures and mocking external services. Each story ends with `pytest` passing.

**Organization**: Tasks are grouped by user story so each can be implemented and tested independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: US1 = agreements to connected apprentices, US2 = attach on invite acceptance, US3 = gift-seat hardening

**Test conventions** (every test task):
- File: `tests/test_connected_apprentice_linking.py`.
- Use real `User` rows (the `mentor_user` / `apprentice_user` fixtures, plus a local `make_user(role, email=...)` helper like the one in `tests/test_invite_codes.py`).
- Sign in with an `act_as(user)` fixture that sets `app.dependency_overrides[get_current_user]` and clears it on teardown.
- Seed an `AgreementTemplate(version=1, markdown_source='Agreement {{meeting_location}}', is_active=True)` directly with `db_session`, and seed connections as `MentorApprentice(mentor_id, apprentice_id, active=...)`.
- Run tests with the pinned stack. The repo `.venv` must have `fastapi==0.143.0` / `starlette==1.8.0`; run `pip install -r requirements.txt` first if it doesn't.

---

## Phase 1: Setup

- [X] T001 Make sure the repo `.venv` matches `requirements.txt` (`.venv/bin/pip install -r requirements.txt`; check `starlette.__version__ == '1.8.0'`). Then run `ENV=test .venv/bin/python -m pytest -q` on `feature/connected-apprentice-linking` and note the pass/skip counts as the baseline.

---

## Phase 2: Foundational (blocks all stories)

- [X] T002 Create `app/services/mentorship.py` with `logger = logging.getLogger(__name__)` and:
  - `has_active_connection(db: Session, mentor_id: str, apprentice_id: str) -> bool`, which is true only when a `MentorApprentice` row with that `mentor_id`, that `apprentice_id` **and `active == True`** exists;
  - `attach_pending_agreements(db: Session, mentor_id: str, email: str, apprentice_id: str) -> int`, which runs a bulk `db.query(Agreement).filter(Agreement.mentor_id == mentor_id, Agreement.apprentice_id.is_(None), func.lower(Agreement.apprentice_email) == email.strip().lower()).update({"apprentice_id": apprentice_id}, synchronize_session=False)`. It returns the row count and logs `"Attached %d agreement(s) mentor_id=%s apprentice_id=%s"` (IDs only, no emails) when the count is above 0. It does **not** commit; the caller does.
- [X] T003 [P] Add unit tests for both helpers to `tests/test_connected_apprentice_linking.py`:
  - `has_active_connection`: true for active, false for inactive, false for no row;
  - `attach_pending_agreements`: ties only same-mentor, untied, same-email rows (case-insensitive); leaves other mentors' rows and already-tied rows alone; returns the count.

**Checkpoint**: `ENV=test pytest tests/test_connected_apprentice_linking.py -q` passes.

---

## Phase 3: User Story 1 - Mentor sends an agreement to a connected apprentice (Priority: P1) 🎯 MVP

**Goal**: Agreements can be created for a connected apprentice by account ID. The apprentice then sees and signs them in the app whatever their email.

**Independent Test**: Mentor M and apprentice A (account email `a-relay@privaterelay.appleid.com`) are actively connected. M creates an agreement with `apprentice_id = A.id` and submits it. A sees it in `/agreements/my` and signs it in the app (200).

### Tests for User Story 1 ⚠️

- [X] T004 [P] [US1] Add tests to `tests/test_connected_apprentice_linking.py`:
  - **Create by ID:** 200; `apprentice_id == A.id`; `apprentice_email == A.email.lower()`; `apprentice_name` is the account name when none is sent.
  - **Create by ID with `apprentice_email` also sent:** the account email wins.
  - **Ended connection** (`active=False`): 403 `"This apprentice is not connected to you"`, and no row is created.
  - **No connection:** 403.
  - **ID of a mentor-role user:** 403.
  - **Wrong role:** an apprentice calling `POST /agreements` gets 403 (Principle VIII; the existing `require_mentor` must stay in place).
  - **Neither ID nor email:** 422.
  - **Email only (old path):** 200 with `apprentice_id` empty.
  - **Reads**, for an agreement tied by ID whose email isn't A's login email (set it to something else directly): `GET /agreements/my` includes it; `GET /agreements/{id}` returns 200; `GET /apprentice/agreements/pending` includes it once it's submitted (`awaiting_apprentice`).
  - **Other apprentice actions (FR-005):** for that tied agreement, `POST /agreements/{id}/request-resend-parent` (on an agreement with `parent_required=True`, `status='awaiting_parent'`) and `POST /agreements/{id}/request-reschedule` as A are **not** 403. Patch out any email or notification send, as the existing agreement tests do.
  - **In-app sign:** after submit, `POST /agreements/{id}/sign/apprentice` as A with `{"typed_name": "A"}` returns 200.
  - **Tied to X, signed by Y with the same email:** 403 `"Not authorized to sign"`.
  - **Untied with matching email:** today's behavior, 200.
  - **Ending the mentorship while a tied agreement is pending:** `POST /apprentice/mentor/revoke` returns 409.

### Implementation for User Story 1

- [X] T005 [P] [US1] In `app/schemas/agreement.py`, `AgreementCreate`:
  - add `apprentice_id: Optional[str] = None`;
  - change `apprentice_email: EmailStr` to `apprentice_email: Optional[EmailStr] = None`;
  - add a `@model_validator(mode="after")` (import `model_validator` from pydantic) that raises `ValueError("apprentice_id or apprentice_email is required")` when both are missing (gives 422).

  Keep the existing `parent_email` validator.
- [X] T006 [US1] In `app/routes/agreements.py`, `create_agreement`:
  - **If `payload.apprentice_id`:** load `User` by ID. If it's missing, not role apprentice, or `not has_active_connection(db, mentor.id, payload.apprentice_id)`, raise `HTTPException(403, "This apprentice is not connected to you")`. Otherwise set `apprentice_email = (user.email or '').lower().strip()` and `apprentice_name = payload.apprentice_name or user.name`, and pass `apprentice_id=user.id` into `Agreement(...)`.
  - **Else:** today's code (`payload.apprentice_email.lower().strip()`).
  - Use these resolved values for `_render_content(...)` and for the transient `apprentice_name` at the end. Replace `payload.apprentice_email.split('@')[0]` with `apprentice_email.split('@')[0]`, since the payload email may now be `None`.

  Import `has_active_connection` from `app.services.mentorship`. Depends on T002 and T005.
- [X] T007 [US1] In `app/routes/agreements.py`, `apprentice_sign`: replace `if effective_email != ag.apprentice_email: raise 403` with
  `allowed = (ag.apprentice_id is not None and ag.apprentice_id == (header_uid or user.id)) or (ag.apprentice_id is None and effective_email == ag.apprentice_email)`, raising the same 403 `"Not authorized to sign"` when it's false. Leave the rest of the function, including the `ENV=test` header shortcut, unchanged.
- [X] T008 [US1] Run `ENV=test .venv/bin/python -m pytest tests/test_connected_apprentice_linking.py tests/test_agreements.py -q` until both pass. Existing agreement tests must not regress.

**Checkpoint**: Agreements by account work end to end. This is the MVP.

---

## Phase 4: User Story 2 - Agreement sent by email attaches once the apprentice joins (Priority: P2)

**Goal**: Accepting a mentor's invite (by code or token) ties that mentor's untied agreements to the invited email onto the apprentice.

**Independent Test**: M invites `jordan@example.com` and creates an email-only agreement for `jordan@example.com`. Apprentice J (with a different email) redeems the invite code. `GET /agreements/my` as J includes the agreement, now with `apprentice_id == J.id`.

### Tests for User Story 2 ⚠️

- [X] T009 [P] [US2] Add tests to `tests/test_connected_apprentice_linking.py`, creating `ApprenticeInvitation` rows directly with an explicit `code`, like `tests/test_invite_codes.py`:
  - **Redeem attaches:** `POST /invitations/redeem` attaches M's untied agreement for the invite email (`Jordan@Example.com` vs `jordan@example.com`, so case doesn't matter), and `/agreements/my` as J includes it.
  - **Accept by token attaches:** `POST /invitations/accept-invite` with the token attaches the same way.
  - **Other mentors untouched:** another mentor's untied agreement for the same email isn't attached.
  - **Tied agreements untouched:** an agreement already tied to another account is unchanged.
  - **Already-signed agreement:** an agreement whose apprentice signature was recorded through the emailed link (set `apprentice_signed_at` and `status='active'` directly, with `apprentice_id` null) attaches, and J sees it as signed.
  - **Already connected:** attaching still runs when the invite redeem returns `relationship: already_active` or `reactivated`.

### Implementation for User Story 2

- [X] T010 [US2] In `app/services/invitations.py`, `accept_invitation`: right after the conditional `update(...)` that marks the invite accepted succeeds, and **before** the existing-relationship branches (which return early), call `attach_pending_agreements(db, invitation.mentor_id, invitation.apprentice_email, apprentice.id)`. The caller still commits. Import it from `app.services.mentorship`. Depends on T002.
- [X] T011 [US2] Run `ENV=test .venv/bin/python -m pytest tests/test_connected_apprentice_linking.py tests/test_invite_codes.py -q` until both pass.

**Checkpoint**: The invite-plus-agreement flow works for hidden-email apprentices.

---

## Phase 5: User Story 3 - Gift seats only go to current apprentices; only apprentices redeem codes (Priority: P3)

**Goal**: Gifting by ID requires an active connection, gift codes are redeemable only by apprentices, and redeem logs have no emails.

**Independent Test**: Assigning a seat by ID to an apprentice whose connection has ended returns 403. A mentor redeeming a gift code gets 403. An apprentice's redeem succeeds and logs no email.

### Tests for User Story 3 ⚠️

- [X] T012 [P] [US3] Add tests to `tests/test_connected_apprentice_linking.py`. Create `MentorPremiumSeat(mentor_id=M.id)` rows directly, patching `app.routes.subscriptions.is_mentor_premium` to return `True` wherever an endpoint checks it.
  - **Assign, ended connection:** `POST /mentor/seats/{id}/assign` with `{"apprentice_id": B.id}` where B's connection is `active=False` returns 403 `"This apprentice is not linked to you"`, and the seat stays unassigned.
  - **Assign, active connection:** 200 and the seat is assigned.
  - **Redeem as a mentor:** `POST /apprentice/redeem-code` with a valid seat code returns 403, and the seat stays `is_redeemed == False`.
  - **Redeem as an apprentice:** 200 with `success: true`. Using `caplog` at INFO for `app.routes.subscriptions`, no record contains the apprentice's or mentor's email.

  - **Purchase (required; Principle VIII):** use the `_fake_customer(monkeypatch, revenuecat.VerifiedCustomer(premium=None, gift_seat_purchases=1))` pattern from `tests/test_subscription_security.py` (copy the helper or import it).
    - `POST /mentor/seats/purchase` with `{"subscription_id": "sub_1", "product_id": "mentor_gift_seat_monthly", "apprentice_id": B.id}`, where B's connection is ended and **no** `apprentice_email` is sent, returns 200, and the created seat has `apprentice_id` empty.
    - The same call for an apprentice with an **active** connection assigns them (`apprentice_id == C.id`, `is_redeemed == True`).

### Implementation for User Story 3

- [X] T013 [US3] In `app/routes/subscriptions.py`, replace each of the three "is linked" queries with `has_active_connection(db, user.id, data.apprentice_id)`. Each is `db.query(MentorApprentice).filter(MentorApprentice.mentor_id == user.id, MentorApprentice.apprentice_id == data.apprentice_id).first()`, and they are:
  - **two** in `confirm_seat_purchase`: the "existing seat not yet assigned" branch and the new-seat branch;
  - **one** in `assign_gift_seat`.

  Find them by function name, not line number. Do this before T014, which edits the same file. Keep each site's existing reaction: set `apprentice = None`, or raise 403 `"This apprentice is not linked to you"` in assign. Import from `app.services.mentorship`. Depends on T002.
- [X] T014 [US3] In `app/routes/subscriptions.py`, `redeem_gift_code`:
  - change `user: User = Depends(get_current_user)` to `Depends(require_apprentice)`, adding the import from `app.services.auth` if it's missing;
  - change the success log to `logger.info("Gift code redeemed: user_id=%s seat_id=%s mentor_id=%s", user.id, seat.id, seat.mentor_id)`;
  - check the function's other log lines for emails and replace them with IDs.
- [X] T015 [US3] Run `ENV=test .venv/bin/python -m pytest tests/test_connected_apprentice_linking.py tests/test_subscription_security.py -q` until both pass.

**Checkpoint**: All three stories pass on their own.

---

## Phase 6: Polish & Cross-Cutting

- [X] T016 [P] Grep `app/services/mentorship.py`, `app/routes/agreements.py` (changed functions only), `app/routes/subscriptions.py` (`redeem_gift_code` and the three changed sites) and `app/services/invitations.py` for log calls containing `email`. New code must log IDs only (Principle V).
- [X] T017 Run `ENV=test .venv/bin/python -m pytest -q` on the pinned stack. Results must match the T001 baseline plus the new tests.
- [ ] T018 Run [quickstart.md §2](quickstart.md) on dev after `/deploy-dev`. **Requires the user**: deploy, and app accounts with different emails.
- [ ] T019 Create the matching frontend spec in `trooth_assessment/specs/` with `/speckit-specify` there:
  - the mentor agreement screen picks a connected apprentice and sends `apprentice_id`, with email entry kept for apprentices not connected yet;
  - an apprentice "Redeem gift code" screen using `POST /apprentice/redeem-code`.

  It MUST link `trooth_assessment_backend/specs/007-connected-apprentice-linking/contracts/api.md` (Principle X).

---

## Dependencies & Execution Order

- T001 → T002 → (T003 ∥ stories).
- **US1** (T004–T008) needs T002. T006 needs T005.
- **US2** (T009–T011) needs T002 only. It's independent of US1, but its tests reuse the US1 fixtures in the same file.
- **US3** (T012–T015) needs T002 only.
- Same-file sequencing:
  - `app/routes/agreements.py`: T006 → T007.
  - `app/routes/subscriptions.py`: T013 → T014.
  - `tests/test_connected_apprentice_linking.py`: T003, T004, T009 and T012 append to it, so run them one after another (marked [P] only against implementation tasks in other files).

## Parallel Examples

- **Phase 2**: T002, then T003 alongside the start of story work.
- **US1**: T004 (tests) and T005 (schema) together, then T006 → T007.
- **US2 and US3** can each start as soon as T002 is done, since they edit different files (`invitations.py` vs `subscriptions.py`).

## Implementation Strategy

1. **MVP**: Phase 2 + US1. That fixes every new agreement a mentor sends to a connected hidden-email apprentice.
2. Add US2 (the invite-plus-agreement flow for new apprentices).
3. Add US3 (gift hardening). It's small and can ship with the others.
4. Polish, deploy to dev and check, then the frontend spec (T019) and prod.
