---
description: "Tasks for 009 Close Critical Authorization Holes"
---

# Tasks: Close Critical Authorization Holes

**Input**: Design documents from `/specs/009-critical-auth-holes/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/auth-holes.md, quickstart.md

**Tests**: REQUIRED by Principle VIII and FR-012. Every changed or removed endpoint gets a success test (the legitimate flow still works) and abuse tests (each acceptance scenario is refused). Tests mock Firebase; no live calls. Each story ends with `pytest` passing.

## Format: `[ID] [P?] [Story] Description`

---

## Phase 1: Setup

- [X] T001 Create `tests/test_critical_auth_holes.py` with shared fixtures:
  - `firebase_token(monkeypatch)`: a factory that monkeypatches `firebase_admin.auth.verify_id_token` (the module object that both the `auth` and `firebase_auth` aliases in `app/services/auth.py` point to) to return a dict for the next call, e.g. `{"uid": ..., "email": ..., "email_verified": bool}`. Tests send `Authorization: Bearer fake`.
  - `claims_spy(monkeypatch)`: records calls to `firebase_admin.auth.set_custom_user_claims`.
  - Stub the welcome-email background task by monkeypatching `app.services.email.send_welcome_email` to a no-op.
  - Make sure no `client.app.dependency_overrides[get_current_user]` leaks in from other fixtures: clear `dependency_overrides` in the fixture.

---

## Phase 2: Foundational

- [X] T002 Add `find_account_for_token(db, decoded) -> tuple[User | None, str]` to `app/services/auth.py`. It returns `(user, outcome)`, where `outcome` is one of `"by_uid"`, `"relinked"`, `"unverified_email"`, `"relink_blocked"` or `"none"`. Rules, per data-model.md:
  1. Look up by `User.id == decoded["uid"]` → `"by_uid"`.
  2. Else, if `decoded.get("email")`, look up by `User.email == decoded["email"]`:
     - `decoded.get("email_verified") is True` → set `user.id = uid`, commit → `"relinked"`. On `IntegrityError`, roll back → `(None, "relink_blocked")`.
     - not verified → `(None, "unverified_email")`.
  3. Else `(None, "none")`.

  Log the outcomes `relinked`, `relink_blocked` and `unverified_email` with the uid and the outcome only. **No emails** (Principle V).
- [X] T003 [P] Add unit tests for `find_account_for_token` in `tests/test_critical_auth_holes.py`: by uid; verified re-link; unverified email refused; no account. Use `db_session` and create users directly.

**Checkpoint**: The helper is tested and nothing calls it yet.

---

## Phase 3: User Story 1 - Nobody can change their own role or take over another account (P1) 🎯 MVP

**Goal**: `POST /users/` and `get_current_user` follow the decision table in data-model.md.

**Independent Test**: Re-post signup asking for admin or mentor as an existing apprentice. Post signup naming another person's email. Neither changes any account.

- [X] T004 [US1] Rewrite `create_user` in `app/routes/user.py`:
  - `uid = decoded_token["uid"]`, `email = decoded_token.get("email")`. If there's no email → 400 `"Your sign-in has no email address"`.
  - Call `find_account_for_token(db, decoded_token)`:
    - `by_uid` / `relinked`: if `user.name` differs, update `name` only. **Do not touch `role` or `id`.** Re-sync claims with `auth.set_custom_user_claims(uid, {"role": existing.role.value})` (stored role), ignoring claim errors as today. Return 200 with the account.
    - `unverified_email` / `relink_blocked`: 409 with the single generic message `"We couldn't finish setting up your account. Verify your email address, then try again."` (FR-013: it doesn't confirm an account exists). Define it once as a module constant.
    - `none`: if `user.role == UserRole.admin` → 403 `"This role can't be chosen at sign-up"`. Otherwise create `User(id=uid, email=email, name=user.name, role=user.role)`. The email comes **from the token**; ignore `user.email` and `user.uid` from the body. Set claims and queue the welcome email as today.

  Keep the `UserCreate` request schema and the `UserOut` response unchanged.
- [X] T005 [US1] In `get_current_user` (`app/services/auth.py:108-127`), replace the inline email re-link with `find_account_for_token`. Outcomes `by_uid` / `relinked` → continue. Any other outcome → the existing 404 `"User not found. Please complete registration first."`
- [X] T006 [P] [US1] Add signup tests to `tests/test_critical_auth_holes.py`, one per acceptance scenario:
  1. A new user registers as apprentice → 200. The stored email equals the **token** email even when the body sends a different email. Claims are set to apprentice.
  2. An existing apprentice re-posts with `role=mentor` and then `role=admin` → 200 each time, the role stays apprentice, and claims are re-synced to apprentice.
  3. A new user posts `role=admin` → 403, and no user row is created.
  4. Person B (token uid B, email b@…) posts with body email = A's email → A's row is unchanged (id, role, name). B gets their own new account, with email b@….
  5. A re-post with a new name → the name updates and the role is unchanged.
  6. Legacy re-link: an existing row with a different id and the token email, with `email_verified=True` → 200, id re-linked, role kept. With `email_verified=False` → 409 and the row is unchanged.
  7. A token with no email → 400.
  8. FR-013: the 409 response body in case 6 equals the generic message and contains neither the existing account's id, name or role nor the word "exists".
- [X] T007 [P] [US1] Add a test to `tests/test_critical_auth_holes.py`: `get_current_user` with an unverified email matching an existing row under another id → a signed-in route (e.g. `GET /users/me/deletion-summary`) returns 404, and the row's id is unchanged.

- [X] T008 [P] [US1] Add a Postgres-marked test to `tests/test_account_deletion_postgres.py`, or a new `tests/test_critical_auth_holes_postgres.py` that follows its fixtures and skip conditions. It covers `find_account_for_token` with a verified email whose existing row has a linked `Assessment` (a foreign key to `users.id`): the result is `(None, "relink_blocked")`, the transaction is rolled back, and the row's id is unchanged. Through `POST /users/`, the same case returns 409 with the generic message. (SQLite in the default suite doesn't enforce foreign keys, so this path can only be tested on Postgres.)

**Checkpoint**: The US1 tests pass. The existing suites that sign users in still pass (`tests/test_user*.py`, `tests/test_invite*`, `tests/test_connected_apprentice_linking.py`).

---

## Phase 4: User Story 2 - Only a real parent or guardian can give consent for a minor (P1)

**Goal**: A parent signature is only accepted through the emailed token.

**Independent Test**: Posting to the old id-based route is refused and changes nothing. The token flow still activates the agreement.

- [X] T009 [US2] Delete the `parent_sign` route (`@router.post("/{agreement_id}/sign/parent")`, `app/routes/agreements.py:455` to the end of that function) and any helper used only by it. Keep `public_sign` (`/public/{token}/sign`) and `_activate_relationship` unchanged.
- [X] T010 [P] [US2] Add tests to `tests/test_critical_auth_holes.py`:
  - Create an agreement in `awaiting_parent` (reuse the setup pattern from `tests/test_agreements.py` around lines 94–222).
  - `POST /agreements/{id}/sign/parent` with no auth, with mentor auth and with apprentice auth → status in (404, 405). The agreement is still `awaiting_parent`, `parent_signed_at` is None, and there's no active `MentorApprentice` row.
  - Then `POST /agreements/public/{parent_token}/sign` → 200 and `fully_signed`.

**Checkpoint**: The US2 tests and `tests/test_agreements.py` pass.

---

## Phase 5: User Story 3 - Mentor–apprentice links are only created through approved flows (P1)

**Goal**: There's no direct-link route.

**Independent Test**: Posting to `assign-apprentice` creates nothing. Invite-code redemption still links.

- [X] T011 [US3] Delete `assign_apprentice` (`@router.post("/assign-apprentice")`, `app/routes/user.py:24-37`). Remove imports used only by it, such as `NotFoundException`, if unused afterwards.
- [X] T012 [P] [US3] Add tests to `tests/test_critical_auth_holes.py`:
  - `POST /users/assign-apprentice?mentor_id=<m>&apprentice_id=<a>` with real user ids, signed out and as a mentor → 405 (the path still matches `GET /users/{user_id}`; assert `in (404, 405)` to stay robust), and no `MentorApprentice` row exists.
  - The approved flow stays covered by the existing `tests/test_invite_codes.py::test_redeem_creates_pairing_even_when_email_differs` (it uses the `act_as` / `make_invite` fixtures). Run it at the checkpoint instead of duplicating it.

**Checkpoint**: The US3 tests and the invite-code tests pass.

---

## Phase 6: Polish & Cross-Cutting

- [X] T013 [P] Create `scripts/audit_admin_accounts.py` (read-only):
  - Connects with `DATABASE_URL`.
  - Prints the id, created_at and name of every `role=admin` user, and the count of users per role. Never print emails, per Principle V; show a masked email such as `t***@domain` instead.
  - With `--check-claims` and Firebase credentials available, also lists users whose Firebase custom-claim `role` differs from the database role.
  - No writes. Add a module docstring with usage.
- [X] T014 Create `scripts/find_role_changes_in_logs.py` (read-only; Python rather than shell, because it joins with the database). It runs `gcloud logging read` for the prod `trooth-backend` service, filtering on `POST` requests to `/users/` with status 200, over `--freshness` (default 30d). Request logs carry no user id, so with `DATABASE_URL` set it matches each request against `users.created_at` within `--window` seconds. Requests with no matching new account are listed as repeat signups (possible role changes), with time, IP, user agent and trace. Document in quickstart.md §3 that this, plus `scripts/audit_admin_accounts.py`, satisfies SC-006.
- [X] T015 Run the full suite (`.venv/bin/python -m pytest -q`) and fix regressions. Grep `app/` for leftover references to `assign-apprentice` and `sign/parent`.
- [X] T016 [P] Update `docs/audit-2026-10-13.md`: mark findings 1–3 as "Fixed in spec 009 (pending deploy)".

---

## Dependencies & Execution Order

- T001 → T002 → T003. US1 (T004–T008) needs T002; T008 also needs T004.
- US2 (T009–T010) and US3 (T011–T012) only need T001, so they can run in parallel with US1. T004 and T011 both edit `app/routes/user.py`, so do them one after the other.
- Polish runs last. T013 and T014 are independent and can be done any time.

## Parallel Examples

- After T002: T003, T006, T007 (tests) together with T009 and T010.
- T013 (audit script) is fully independent.

## Implementation Strategy

- **MVP**: US1, because it closes the admin escalation, the most severe hole. All three stories are P1 and small, though, so ship them together in one PR.
- **Rollout**: `/deploy-dev`, then quickstart §2 (new signup and re-open in the app, curl probes), then `/deploy-prod`, then quickstart §3: `scripts/audit_admin_accounts.py` and `scripts/find_role_changes_in_logs.py` against prod.

---

## Phase 7: Convergence

- [X] T017 Log signup refusals in `app/routes/user.py:create_user` with the uid and a reason code only, no email: `logger.warning("signup refused uid=%s outcome=admin_requested", ...)` before the 403, and `outcome=no_email` before the 400. Add an assertion in `tests/test_critical_auth_holes.py::test_new_account_cannot_register_as_admin` (via `caplog`) that the admin attempt is logged and the log line contains no email, per plan: Constitution Check V (partial)
