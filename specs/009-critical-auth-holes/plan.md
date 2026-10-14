# Implementation Plan: Close Critical Authorization Holes

**Branch**: `fix/critical-auth-holes` | **Date**: 2026-10-14 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/009-critical-auth-holes/spec.md`

## Summary

Three small server-side changes, with no schema change:

1. **Signup (`POST /users/`, `app/routes/user.py:create_user`)**
   - Identity comes from the verified Firebase token only: `uid`, `email` and `email_verified`.
   - Look up the account by `uid`. If found, return it (only the display name may update). **Never** change `role` or `id`, and never re-set custom claims to a new role.
   - If not found by `uid` but an account has the token's email: re-link only when `email_verified` is true. Otherwise return 409.
   - Requests for `role=admin` get 403. The body's `email` is ignored for lookup and storage, but kept in the schema so released apps keep working.
2. **Legacy re-link in `get_current_user` (`app/services/auth.py`)**: the same verified-email rule for the email fallback.
3. **Delete two routes**:
   - `POST /agreements/{agreement_id}/sign/parent` (`app/routes/agreements.py:455`)
   - `POST /users/assign-apprentice` (`app/routes/user.py:24`)

   After removal they return 404 or 405 from FastAPI. `assign-apprentice` returns 405, because it still matches `GET /users/{user_id}`. Parents keep signing through `POST /agreements/public/{token}/sign`.

New tests cover every abuse case in the spec. A one-off read-only audit query finds unexpected admins after release.

## Technical Context

**Language/Version**: Python 3.11

**Primary Dependencies**: FastAPI, SQLAlchemy, Firebase Admin (existing). No new packages.

**Storage**: PostgreSQL. **No migration.** `users.email` is already `unique=True` (`app/models/user.py:41`).

**Testing**: pytest with the SQLite fixtures in `tests/conftest.py`. The signup tests monkeypatch `app.services.auth.auth.verify_id_token`, which `verify_token` uses. They also monkeypatch `app.routes.user.auth.set_custom_user_claims` so no Firebase call is made, plus the welcome-email task. There are no live external calls.

**Target Platform**: Google Cloud Run (dev and prod services)

**Project Type**: web-service (client: Flutter app in `trooth_assessment`; no app change required)

**Performance Goals**: no change. Signup does one or two indexed lookups.

**Constraints**:
- Released apps call `POST /users/` from `signup_screen.dart:100` and `role_selection_screen.dart:58`, sending `{uid, email, role, name}`. Both treat errors containing 409 or "exist" as harmless duplicates.
- The response stays `UserOut`, with 200 for new and repeat signups.
- The two deleted routes have no callers in released apps.

**Scale/Scope**: 3 files changed (`app/routes/user.py`, `app/services/auth.py`, `app/routes/agreements.py`), 1 new test file, 1 audit script.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **I. Auth**: ✅ This is the purpose of the change. Signup is bound to the token identity, the routes with no auth are removed, and no test shortcuts exist outside `ENV=test`.
- [x] **II. Errors**: ✅ `HTTPException` with 403/409 and a clear `detail`. Refusals don't reveal other accounts (FR-013): the 409 for an unverified email or a blocked re-link uses one generic message, "We couldn't finish setting up your account. Verify your email address, then try again.", so it never confirms that an account exists for an email.
- [x] **III. Migrations**: N/A. No schema change.
- [x] **IV. Config & secrets**: ✅ No new config.
- [x] **V. Logging**: ✅ Refusals are logged with the uid and a reason code only, never emails or tokens.
- [x] **VI. Compatibility**: ⚠️→✅ Two routes are removed. Principle VI allows removal when no released app version uses them; the frontend source confirms no callers (`parentSignAgreement` and `assignApprentice` are defined but never invoked). Recorded in [contracts/](contracts/auth-holes.md). `POST /users/` keeps its request and response shape.
- [x] **VII. Layering**: ✅ The auth logic stays in `app/services/auth.py` and the route.
- [x] **VIII. Tests**: ✅ Success-path and abuse tests for signup, re-link, parent signing (token path still works; the old route is gone) and direct linking.
- [x] **IX. Deploy**: ✅ Dev first (sign up as a new user through the app, then re-open the app), then prod. Run the admin audit query after the prod deploy.
- [x] **X. Contract**: ✅ [contracts/auth-holes.md](contracts/auth-holes.md). Frontend: no spec. Optional client cleanup is noted.
- [x] **XI. Formatting**: ✅ Only the touched functions change.

**Post-design re-check**: all ✅ / N/A.

## Project Structure

### Documentation (this feature)

```text
specs/009-critical-auth-holes/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/auth-holes.md
├── checklists/requirements.md
└── tasks.md            # /speckit-tasks
```

### Source Code (repository root)

```text
app/
├── routes/user.py          # create_user rewrite; delete assign_apprentice
├── routes/agreements.py    # delete parent_sign (POST /{agreement_id}/sign/parent)
└── services/auth.py        # get_current_user email re-link requires email_verified
scripts/audit_admin_accounts.py   # read-only: list admins + accounts whose claims/role look escalated
tests/test_critical_auth_holes.py # signup, re-link, removed routes, token parent-sign still works
```

**Structure Decision**: Fix the code in place where each hole lives. Shared signup and re-link logic goes in a small helper, `_find_account_for_token(db, decoded)` in `app/services/auth.py`. Both `create_user` and `get_current_user` call it, so the two paths can't drift apart again.

## Complexity Tracking

No constitution violations.
