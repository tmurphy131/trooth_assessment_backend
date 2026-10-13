# Implementation Plan: Invite Codes

**Branch**: `feature/invite-codes` | **Date**: 2026-10-13 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/006-invite-codes/spec.md`

## Summary

Every apprentice invitation gets a short, human-friendly code (`K7QM-3XPR`). A signed-in apprentice can redeem it with a new `POST /invitations/redeem`, whatever their account email is. That's what makes social sign-in with Apple's hidden email work. The accept logic moves into a shared service that both the code path and the token path use. Accept-by-token now requires sign-in and ignores apprentice IDs that aren't the caller's. Failed redemptions are rate-limited per user through a small attempts table, which also serves as the audit trail. The invitation email and landing page show the code instead of the raw token.

## Technical Context

**Language/Version**: Python 3.11

**Primary Dependencies**: FastAPI, SQLAlchemy, Alembic, Firebase Admin. No new packages; `secrets` is in the standard library.

**Storage**: PostgreSQL (Cloud SQL). New column `apprentice_invitations.code` (unique, backfilled). New table `invite_code_attempts`. Migration `20261013_invite_codes`.

**Testing**: pytest (`tests/`, SQLite in-memory via conftest fixtures); new `tests/test_invite_codes.py`

**Target Platform**: Google Cloud Run (dev and prod services)

**Project Type**: web-service (client: Flutter app in `trooth_assessment`)

**Performance Goals**: Redeem responds in under 300 ms p95. It does one indexed count, one indexed lookup and one conditional update.

**Constraints**: Additive API for released app versions (Principle VI). The rate limit must hold across Cloud Run instances. Codes and tokens are never logged.

**Scale/Scope**: Hundreds to low thousands of invites. Redemption volume is low (once per pairing).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **I. Auth** ✅ `redeem` and `accept-invite` use `require_apprentice`. Invite creation and listing keep `require_mentor`. The public landing page stays public and shows only that invite's own details. This closes an existing hole: accept-invite had no auth and trusted `apprentice_id`. No premium gating (the feature is free).
- [x] **II. Errors** ✅ `NotFoundException` / `ValidationException` / `ForbiddenException` from `app/exceptions.py`. 429 is an `HTTPException` with a `Retry-After` header. Existing `detail` strings are reused where the meaning matches.
- [x] **III. Migrations** ✅ `alembic/versions/20261013_invite_codes.py` adds the column, backfills, sets NOT NULL and the unique index, and creates the attempts table. Full `downgrade()`. Runs through the migrate job before deploy.
- [x] **IV. Config & secrets** ✅ No new config. The rate-limit numbers (10/hour) are module constants. Cloud Run env and secret lists are unchanged.
- [x] **V. Logging** ✅ `logging.getLogger(__name__)`. Logs user and invitation IDs and the outcome, never codes or tokens. The `print` calls in `invite_apprentice` that print the apprentice's email are replaced.
- [x] **VI. Compatibility** ✅ New endpoint and new fields. Accept-invite now requires sign-in, but released apps already send it (see research R7). The only status change is 404 → 403 for non-apprentice callers, an error path that apps treat the same way. New handlers declare `response_model`, and so does the changed `accept-invite` (`InviteAcceptOut`).
- [x] **VII. Layering** ✅ Logic lives in `app/services/invitations.py`, with pure code helpers in `app/services/invite_codes.py` (kept separate to avoid a model ↔ service circular import). Routes stay thin.
- [x] **VIII. Tests** ✅ Success and authz-failure tests for each new or changed endpoint, including the two list endpoints that gain `code` ([quickstart.md](quickstart.md) §1). SendGrid is mocked by the conftest autouse fixture.
- [x] **IX. Deploy** ✅ Dev first (migrate job, then image), verified with quickstart §3, then prod from `main`.
- [x] **X. Contract** ✅ [contracts/invitations.md](contracts/invitations.md). The frontend spec must link it; this is tracked as task T032.
- [x] **XI. Formatting** ✅ Edits are limited to the touched functions. No reformatting of whole files.

**Post-design re-check**: still passes. Neither the data model nor the contract adds anything that breaks a principle.

## Project Structure

### Documentation (this feature)

```text
specs/006-invite-codes/
├── spec.md
├── plan.md               # this file
├── research.md           # decisions R1–R8
├── data-model.md
├── quickstart.md
├── contracts/invitations.md
├── checklists/requirements.md
└── tasks.md              # /speckit-tasks
```

### Source Code (repository root)

```text
app/
├── routes/invite.py                       # add POST /redeem; accept-invite → require_apprentice + shared service;
│                                          #   invite-apprentice returns id/code/expires_at; landing page passes code
├── schemas/invite.py                      # InviteAccept.apprentice_id optional; InviteOut.code; InviteRedeem, InviteRedeemOut,
│                                          #   InviteCreatedOut, InviteAcceptOut
├── models/apprentice_invitation.py        # code column (default generator, unique)
├── models/invite_code_attempt.py          # NEW (import in alembic/env.py and models __init__ if used)
├── services/invite_codes.py               # NEW: pure helpers (generate/normalize/format, alphabet). No model imports.
├── services/invitations.py                # NEW: create_code_for(), accept_invitation(), redeem_code() + rate limit
├── services/email.py                      # render/send_invitation_email take code
├── services/email_catalog.py              # invitation preview context gains code
├── services/account_deletion.py           # delete invite_code_attempts for the user
├── templates/email/account/invitation.html       # show code
└── templates/invitations/accept_invitation.html  # token box → code box
alembic/versions/20261013_invite_codes.py  # NEW
tests/test_invite_codes.py                 # NEW (endpoint tests)
tests/test_invite_code_helpers.py          # NEW (pure helper unit tests)
```

**Structure Decision**: This follows the existing route → schema → model → service layout. Only one new module each in models and services. The `invitations` service name matches the route domain.

## Complexity Tracking

No constitution violations.
