---

description: "Task list for invite codes"
---

# Tasks: Invite Codes

**Input**: Design documents from `/specs/006-invite-codes/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/invitations.md, quickstart.md

**Tests**: Per constitution Principle VIII, test tasks are REQUIRED for every new or changed endpoint: the success path plus applicable authorization failures, using conftest fixtures and mocking external services. Each story ends with `pytest` passing.

**Organization**: Tasks are grouped by user story so each can be implemented and tested independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: US1 = apprentice redeems a code, US2 = mentor gets a shareable code, US3 = accept-by-token can't be done for someone else

**Test fixture note**: `mock_apprentice` and `mock_mentor` (tests/conftest.py) return a `MockUser` that has no row in `users`. Redeem and accept tests need real rows. Use the `mentor_user` and `apprentice_user` fixtures, and set `app.dependency_overrides[get_current_user] = lambda: <that user>` in the test (clear it afterwards). Leave out the override, and send no `Authorization` header, to test 401.

---

## Phase 1: Setup

**Purpose**: Nothing new to install. Confirm the baseline is green.

- [X] T001 Run `ENV=test pytest -q` on `feature/invite-codes` and note any tests that already fail, so later runs can be compared against this baseline.

---

## Phase 2: Foundational (blocking all stories)

**Purpose**: The code column, the attempts table, the code helpers and the shared accept function. Every story needs them.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T002 [P] Create `app/services/invite_codes.py`, a pure helper module that **must not import any `app.models` or `app.db` module** (this avoids a circular import with T003). It contains:
  - Constants `CODE_ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"` and `CODE_LENGTH = 8`.
  - `generate_invite_code() -> str`: 8 characters chosen with `secrets.choice` from the alphabet.
  - `normalize_invite_code(raw: str) -> str | None`: remove **all** whitespace and `-`, uppercase. Return `None` unless the result is exactly 8 characters, all from the alphabet.
  - `format_invite_code(code: str) -> str`: return `XXXX-XXXX`. It MUST be **idempotent**: normalize the input first (so `K7QM3XPR`, `k7qm3xpr` and `K7QM-3XPR` all give `K7QM-3XPR`), and return the input unchanged if it doesn't normalize.
- [X] T003 Add `code` to `app/models/apprentice_invitation.py`: `Column(String(8), nullable=False, unique=True, index=True, default=generate_invite_code)`. Import the default from `app.services.invite_codes` (depends on T002). Canonical form is "uppercase, no dash".
- [X] T004 [P] Create `app/models/invite_code_attempt.py` with the `InviteCodeAttempt` model on table `invite_code_attempts`:
  - `id` String PK, default uuid4.
  - `user_id` String, `ForeignKey("users.id", ondelete="CASCADE")`, not null.
  - `invitation_id` String, nullable, **no FK**.
  - `succeeded` Boolean, not null.
  - `created_at` DateTime, default naive UTC now.
  - Composite `Index("ix_invite_code_attempts_user_created", "user_id", "created_at")`.

  Register the model in `app/models/__init__.py` and in the model import list in `alembic/env.py`.
- [X] T005 Create `alembic/versions/20261013_invite_codes.py` (`revision = '20261013_invite_codes'`, `down_revision = '20261012_email_prefs'`). In `upgrade()`:
  1. Add `apprentice_invitations.code` `String(8)` as nullable.
  2. Backfill every row with a unique code. Select the IDs, then update each with a code not already used in this run. The generator is **written out inside the migration** (its own copy of the alphabet constant and a `secrets.choice` loop). **Don't import from `app`**: no existing migration does, and a migration must not change when app code changes later.
  3. `alter_column(nullable=False)`.
  4. Create unique index `ix_apprentice_invitations_code`.
  5. Create `invite_code_attempts` with the composite index from T004.

  `downgrade()` drops the attempts table and index, then the code index and column. Depends on T003 and T004.
- [X] T006 Create `app/services/invitations.py` (database logic; it may import models) with `logger = logging.getLogger(__name__)`, the constants `MAX_FAILED_ATTEMPTS = 10` and `ATTEMPT_WINDOW = timedelta(hours=1)`, and `create_code_for(db) -> str`. That function generates a code with `generate_invite_code()` from `app.services.invite_codes`, re-rolls if `ApprenticeInvitation.code` already holds it, and raises `RuntimeError` after 5 tries (research R2). Depends on T002 and T003.
- [X] T007 Add `accept_invitation(db, invitation, apprentice) -> str` to `app/services/invitations.py`. It returns `"created" | "reactivated" | "already_active"`.
  1. Raise `ValidationException("This invitation has expired.")` if `expires_at` (naive-compared, as in `app/routes/invite.py:229-234`) is in the past.
  2. Run the conditional update `db.query(ApprenticeInvitation).filter(id == invitation.id, accepted == False).update({"accepted": True}, synchronize_session=False)`. If 0 rows changed, `db.rollback()` and raise `HTTPException(400, "Invitation has already been accepted")` (research R5).
  3. Create or reactivate the `MentorApprentice` row exactly as `app/routes/invite.py:246-259` does now. An existing row that is already active returns `"already_active"`.
  4. Leave the commit to the caller.

**Checkpoint**: `ENV=test pytest -q` matches the T001 baseline. The model has `code`, and every invite gets one at creation.

---

## Phase 3: User Story 1 - Apprentice joins a mentor with a code (Priority: P1) 🎯 MVP

**Goal**: `POST /invitations/redeem` pairs the signed-in apprentice with the mentor whose invite code they enter, whatever their email.

**Independent Test**: Insert an invite for `invitee@example.com`. As `apprentice_user` (a different email), redeem its code and get 200. A `MentorApprentice` row now exists.

### Tests for User Story 1 ⚠️

> Write these first and confirm they fail before implementing.

- [X] T008 [P] [US1] Create `tests/test_invite_codes.py` with redeem tests, following [quickstart.md §1](quickstart.md):
  - 200 with `relationship: created`, and `mentor_id` / `mentor_name` in the response;
  - the code is accepted as `k7qm3xpr` and `" K7QM-3XPR "`;
  - the apprentice's email differs from the invited email;
  - redeeming again returns 400 "Invitation has already been accepted";
  - an expired invite returns 400 "This invitation has expired.";
  - unknown and malformed (`"ABC"`, `"0OIL-0OIL"`) codes return 404 "Invite code not found";
  - a previously inactive pairing returns `relationship: reactivated` with no duplicate row;
  - an already-active pairing returns `already_active`;
  - a mentor or admin caller gets 403;
  - no auth gets 401;
  - a missing `code` gets 422, and a 33-character `code` gets 422;
  - race (simultaneous redemption): load an invite, mark it `accepted = True` directly in the database, then call `accept_invitation(db, <stale invite object>, apprentice)`. It raises 400 "Invitation has already been accepted" and creates no `MentorApprentice` row (this proves the conditional update from research R5);
  - logging (with `caplog`): one successful and one 404 redeem each log an `invite.redeem` record with the outcome (`ok` / `not_found`), and the raw code (in any form) appears nowhere in `caplog.text` (FR-012);
  - after 10 failed attempts, an 11th attempt with a *valid* code gets 429 with a `Retry-After` header;
  - after moving those attempts' `created_at` back more than an hour, the valid code succeeds;
  - attempts are recorded: one row per 200/400/404 response, none for 401/403/422/429.
- [X] T009 [P] [US1] Create `tests/test_invite_code_helpers.py` with unit tests for `app/services/invite_codes.py`:
  - `generate_invite_code`: length 8, only characters from the alphabet, no 0/O/1/I/L;
  - `normalize_invite_code`: case, dashes, and internal and surrounding whitespace are ignored; wrong length or characters return `None`;
  - `format_invite_code`: returns the `XXXX-XXXX` form, and is idempotent (`format_invite_code(format_invite_code(c)) == format_invite_code(c)`; an already-formatted value is never turned into `K7QM--3XPR`).

  Also assert that importing `app.services.invite_codes` imports no `app.models` module (guards against the circular import).

### Implementation for User Story 1

- [X] T010 [P] [US1] In `app/schemas/invite.py`, add:
  - `InviteRedeem(BaseModel)` with `code: str = Field(min_length=1, max_length=32)`;
  - `InviteRedeemOut(BaseModel)` with `message: str`, `mentor_id: str`, `mentor_name: str | None`, `relationship: Literal["created", "reactivated", "already_active"]`.
- [X] T011 [US1] Add `redeem_code(db, raw_code, apprentice) -> tuple[ApprenticeInvitation, str]` to `app/services/invitations.py`:
  1. Count the apprentice's `InviteCodeAttempt` rows with `succeeded == False` and `created_at > now - ATTEMPT_WINDOW`. If the count is `>= MAX_FAILED_ATTEMPTS`, raise `HTTPException(429, "Too many invalid codes. Try again later.", headers={"Retry-After": <seconds until the oldest counted failure is 1h old, minimum 1>})`. Record nothing for this request.
  2. Normalize the code with `normalize_invite_code` (from `app.services.invite_codes`). If it's `None` or no invite matches, record a failed attempt with `invitation_id=None`, **commit**, and raise `NotFoundException("Invite code not found")`.
  3. Call `accept_invitation`. If it raises 400 (expired or already used), roll back the acceptance, record a failed attempt with that `invitation_id`, commit, and re-raise.
  4. On success, record a succeeded attempt and commit.
  5. Log `invite.redeem` with `user_id`, `invitation_id` and the outcome (`ok`, `not_found`, `expired`, `used`, `rate_limited`). Never log the code.

  Depends on T004, T007.
- [X] T012 [US1] Add `POST /redeem` to `app/routes/invite.py`, with `response_model=InviteRedeemOut` and `current_user: User = Depends(require_apprentice)`. It calls `redeem_code`, looks up the mentor's name, and returns `message` (`"Invitation accepted, relationship created"`, `"...reactivated"` or `"...already active"`), `mentor_id`, `mentor_name` and `relationship`. Import `require_apprentice` from `app.services.auth`.
- [X] T013 [US1] Run `ENV=test pytest tests/test_invite_codes.py tests/test_invite_code_helpers.py -q` until T008 and T009 pass.

**Checkpoint**: Redeeming works end to end in tests. This is the MVP.

---

## Phase 4: User Story 2 - Mentor gets a code they can share anywhere (Priority: P1)

**Goal**: The code appears in the invite-creation response, both invite lists, the invitation email and the public landing page. The landing page stops showing the raw token.

**Independent Test**: A mentor creates an invite. The response, `pending-invites` and the rendered email HTML all show the same `XXXX-XXXX` code. The landing page HTML contains the code and not the token.

### Tests for User Story 2 ⚠️

- [X] T014 [P] [US2] Add tests to `tests/test_invite_codes.py`:
  - `POST /invitations/invite-apprentice` as a mentor returns 200 with `message == "Invitation sent"`, plus `id`, `code` matching `^[2-9A-HJKMNP-Z]{4}-[2-9A-HJKMNP-Z]{4}$`, and `expires_at`;
  - `GET /invitations/pending-invites` has the same `code`;
  - `GET /invitations/apprentice-invites?email=` includes `code`;
  - as an apprentice, `invite-apprentice` gets 403;
  - as an apprentice, `GET /invitations/pending-invites` gets 403 (Principle VIII, changed endpoint);
  - `GET /invitations/apprentice-invites?email=<someone else's email>` gets 403 "You can only view your own invitations" (Principle VIII, changed endpoint);
  - `GET /invitations/accept-invitation?token=` HTML contains the formatted code and does **not** contain the token;
  - `render_invitation_email(...)` HTML contains the formatted code;
  - the `mock_email_send` fixture captures a send whose content includes the code.

### Implementation for User Story 2

- [X] T015 [P] [US2] In `app/schemas/invite.py`:
  - add `code: str | None = None` to `InviteOut`, with a `field_validator`/serializer that turns a stored 8-character value into `XXXX-XXXX` (via `format_invite_code` from `app.services.invite_codes`);
  - add `InviteCreatedOut(BaseModel)` with `message: str`, `id: str`, `code: str`, `expires_at: datetime`.
- [X] T016 [P] [US2] In `app/services/email.py`:
  - `render_invitation_email` and `send_invitation_email` take a new **optional** `code: str | None = None` parameter and add it to the `email_catalog.render("invitation", ...)` context;
  - update the `invitation` preview context in `app/services/email_catalog.py` (around line 221) with `"code": "K7QM-3XPR"`.

  `code` is optional so existing callers (including `tests/test_email.py:38`) keep working. The template only shows the code block when `code` is set (T020).
- [X] T017 [US2] Update `invite_apprentice` in `app/routes/invite.py` (depends on T016):
  - set `code=create_code_for(db)` on the new `ApprenticeInvitation` (stored raw, no dash);
  - pass `code=format_invite_code(invitation.code)` to `send_invitation_email`;
  - return `InviteCreatedOut` (`response_model=InviteCreatedOut`) with `code=format_invite_code(invitation.code)`, so the response always uses the display form `XXXX-XXXX`;
  - replace both `print(...)` calls with `logger.warning`/`logger.exception`, logging `invitation.id` and **not** the apprentice email (Principle V);
  - add `logger = logging.getLogger(__name__)` at module top.
- [X] T018 [US2] In `get_apprentice_invites` in `app/routes/invite.py`, add the **raw** `"code": invitation.code` to each dict it builds. `get_pending_invites` returns ORM objects. In both cases the `InviteOut` serializer from T015 does the one and only formatting (it relies on the idempotent `format_invite_code` from T002).
- [X] T019 [US2] In `accept_invitation_page` in `app/routes/invite.py`, pass `"code": format_invite_code(invitation.code)` in the success-template context and remove `"token"` from it.
- [X] T020 [P] [US2] In `app/templates/email/account/invitation.html`, before `{{ m.button(accept_url, "Accept invitation") }}`, add `{% if code %}` … `{% endif %}` around a centered block. It has the label "Your invite code", `{{ code }}` in a large, letter-spaced monospace style, and the line "Open the T[root]H app and enter this code to join {{ mentor_name }}." Match the existing `highlight-box` styling.
- [X] T021 [P] [US2] In `app/templates/invitations/accept_invitation.html`, replace the "Invitation Token" `token-box` block (around lines 221-224) with an "Invite code" box that shows `{{ code }}` and the line "Open the T[root]H app and enter this code to join your mentor." Keep the existing `.token-*` CSS classes or rename them consistently.
- [X] T022 [US2] Run `ENV=test pytest tests/test_invite_codes.py tests/test_invitations.py tests/test_email.py -q` until T014 passes and `tests/test_email.py` (including `test_send_invitation_email_success`) still passes.

**Checkpoint**: Mentors can see and share codes. US1 and US2 together are the user-facing feature.

---

## Phase 5: User Story 3 - Invite acceptance can't be done on someone else's behalf (Priority: P2)

**Goal**: `POST /invitations/accept-invite` requires a signed-in apprentice and never pairs anyone except the caller.

**Independent Test**: No auth gets 401. Signed in as A with B's `apprentice_id` gets 403 and nothing changes. Signed in as A with A's ID, or no ID, gets 200.

### Tests for User Story 3 ⚠️

- [X] T023 [P] [US3] Add accept-invite tests to `tests/test_invite_codes.py`:
  - no auth gets 401;
  - A with `apprentice_id` = B gets 403 "You can only accept invitations for yourself", and the invite is still `accepted == False`;
  - A with their own `apprentice_id` gets 200 "Invitation accepted, relationship created";
  - A with no `apprentice_id` gets 200;
  - an unknown token gets 400 "Invitation is invalid or expired";
  - a mentor caller gets 403;
  - the reactivation path still returns "Invitation accepted, relationship reactivated".

### Implementation for User Story 3

- [X] T024 [P] [US3] In `app/schemas/invite.py`, make `InviteAccept.apprentice_id: str | None = None` and add `InviteAcceptOut(BaseModel)` with `message: str` (Principle VI, `response_model`).
- [X] T025 [US3] Rewrite `accept_invite` in `app/routes/invite.py`:
  - set `response_model=InviteAcceptOut` on the route;
  - add `current_user: User = Depends(require_apprentice)`;
  - if `data.apprentice_id` is set and `!= current_user.id`, raise `ForbiddenException("You can only accept invitations for yourself")`;
  - look up the token (unknown token gives 400 "Invitation is invalid or expired", as now);
  - call `accept_invitation(db, invitation, current_user)` and commit;
  - return the same messages as today (`"Invitation accepted, relationship created"` / `"Invitation accepted, relationship reactivated"`). Map `already_active` to the reactivated message so released apps see a known string.

  Delete the inline relationship code this replaces. Depends on T007.
- [X] T026 [US3] Run `ENV=test pytest tests/test_invite_codes.py -q` until T023 passes.

**Checkpoint**: All three stories pass on their own.

---

## Phase 6: Polish & Cross-Cutting

- [X] T027 [P] In `app/services/account_deletion.py`, add `_safe_delete(db, InviteCodeAttempt, InviteCodeAttempt.user_id == user_id, "invite_code_attempts")` to both `delete_apprentice_account` and `delete_mentor_account`. Add a test in `tests/test_invite_codes.py` that deleting an apprentice with attempts removes their rows.
- [X] T028 [P] Check that nothing logs a code or token. Grep `app/routes/invite.py`, `app/services/invitations.py` and `app/services/invite_codes.py` for `logger.` / `print(` and confirm only IDs and outcomes are logged (FR-012, Principle V).
- [X] T029 Run `ENV=test pytest -q`. Results must match the T001 baseline plus the new passing tests.
- [ ] T030 On the dev database (through the Cloud Run migrate job or a local connection to dev):
  - run `alembic upgrade head`, `alembic downgrade -1`, then `alembic upgrade head`;
  - confirm `SELECT count(*) FROM apprentice_invitations WHERE code IS NULL` returns 0 and the codes are unique.

  ([quickstart.md §2](quickstart.md))

  *Progress 2026-10-13:* verified on a throwaway local PostgreSQL 14 built from the full migration chain. Three seeded invites got three distinct codes with no nulls. The column is NOT NULL, and both indexes were created (one unique). Downgrade removed the column and the table and kept all invites, and the re-upgrade was clean. Dev: the `migrate-and-populate-dev` job (execution `migrate-and-populate-dev-hwt59`) ran `20261012_email_prefs -> 20261013_invite_codes` successfully. The NOT NULL step would have failed if any row were left without a code. The downgrade round-trip was not repeated on dev.
- [X] T031 Run the end-to-end checks on dev from [quickstart.md §3](quickstart.md), including accepting from an older store or TestFlight build (research R7). Also check the plan's performance goal (p95 under 300 ms). Create 5 invites, have 5 different apprentice accounts each redeem one (all 200s), and time each call. Then, as one more apprentice, time 9 redeems of an unknown code (404s). Keep each user **under 10 failures** so the rate limit doesn't skew the timings. **Requires the user**: deploys are done with `/deploy-dev`.
- [X] T032 Create the matching frontend spec in `trooth_assessment/specs/` with `/speckit-specify` there. It covers invite-code entry for apprentices, code display and Copy/Share for mentors, and social-first login. It MUST link `trooth_assessment_backend/specs/006-invite-codes/contracts/invitations.md` (Principle X). This is tracked here so the cross-repo step isn't forgotten; the work happens in the frontend repo.

---

## Dependencies & Execution Order

- **Phase 1 → Phase 2 → stories.** T002 and T004 together; then T003; then T005 and T006; then T007.
- **US1** (T008–T013) depends on Phase 2 (T004, T007).
- **US2** (T014–T022) depends on Phase 2 (T003, T006). It's independent of US1. Within US2, T016 (email service) must be done before T017, which passes `code=` to `send_invitation_email`.
- **US3** (T023–T026) depends on T007 only. It's independent of US1 and US2.
- **Polish** comes after the stories that are being shipped.
- Several story tasks edit the same files (`app/routes/invite.py`, `app/schemas/invite.py`, `tests/test_invite_codes.py`). Only tasks in different files are marked [P]. Run stories one after another unless you merge carefully.

## Parallel Examples

- **Phase 2**: T002 (code helpers) and T004 (attempt model) at the same time, then T003.
- **US1**: T008 (`tests/test_invite_codes.py`) and T009 (`tests/test_invite_code_helpers.py`) together with T010 (schemas), then T011 → T012.
- **US2**: T015 (schemas), T016 (email service), T020 (email template) and T021 (landing template) in parallel, then T017 → T018 → T019 in `invite.py` one at a time.
- **US3**: T023 (tests) and T024 (schema) together, then T025.

## Implementation Strategy

1. **MVP**: Phase 2 + US1. Apprentices can redeem codes, but mentors can only find codes in the database.
2. **Shippable**: add US2. Codes appear in the app response, email and landing page. **This is the smallest release the frontend can build against.**
3. **Hardening**: add US3 (security fix) in the same release. It's small and closes an existing hole.
4. Polish, then deploy to dev (migrate job **before** the image, Principle III), verify, then prod from `main`.
