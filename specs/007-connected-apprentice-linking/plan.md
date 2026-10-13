# Implementation Plan: Link Agreements and Gift Seats to Apprentice Accounts

**Branch**: `feature/connected-apprentice-linking` | **Date**: 2026-10-13 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/007-connected-apprentice-linking/spec.md`

## Summary

Agreements become account-based without changing the database.
- **Creating:** mentors can create an agreement for an actively connected apprentice by account ID, so it's tied to that account from the start.
- **Signing in the app:** allowed when the agreement is tied to the signer, or, as today, when it's untied and the emails match.
- **Joining:** when an apprentice accepts a mentor's invite, that mentor's untied agreements to the invited email attach to the apprentice.

Gift seats get small hardening:
- gifting by ID requires an **active** connection;
- only apprentices can redeem gift codes;
- the redeem log stops recording emails.

A new `app/services/mentorship.py` holds the shared "active connection" check and the attach step.

## Technical Context

**Language/Version**: Python 3.11

**Primary Dependencies**: FastAPI (0.143.0, pinned), SQLAlchemy, Alembic, Firebase Admin. No new packages.

**Storage**: PostgreSQL (Cloud SQL). **No schema change and no migration**; it uses the existing `agreements.apprentice_id`.

**Testing**: pytest (`tests/`, SQLite in-memory via conftest fixtures). New `tests/test_connected_apprentice_linking.py`.

**Target Platform**: Google Cloud Run (dev and prod)

**Project Type**: web-service (client: Flutter app in `trooth_assessment`)

**Performance Goals**: Attaching on invite acceptance is one indexed `UPDATE` (by mentor and email). Agreement creation adds one primary-key lookup and one connection lookup. Both are negligible.

**Constraints**: Additive for released app versions (Principle VI). Never re-tie an agreement that's already tied. No emails in logs.

**Scale/Scope**: 4 route files touched (agreements, subscriptions, plus the invitations service hook), 1 schema, 1 new service module, about 17 tests.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **I. Auth** ✅ Agreement-by-ID requires `require_mentor` **plus** an active `MentorApprentice` link (Principle I's mentor→apprentice rule). Gift redeem moves to `require_apprentice`. The signing check gets *more* precise: an agreement tied to account X can't be signed by Y. No new test shortcuts; the existing `ENV=test` one in `apprentice_sign` is untouched. Creating an agreement **by email** and the gift-seat **email** fallback still don't need a connection. That's deliberate, unchanged from today: they're how a mentor reaches someone who isn't an apprentice of theirs yet. They address a new person by email rather than touching an existing apprentice's data, which is what Principle I's connection rule protects. Anything done **by account ID** requires an active connection.
- [x] **II. Errors** ✅ `HTTPException` / `ForbiddenException` with clear `detail`. Existing messages are reused where the meaning is the same (`Not authorized to sign`, `This apprentice is not linked to you`).
- [x] **III. Migrations** ✅ N/A: no model change.
- [x] **IV. Config & secrets** ✅ N/A.
- [x] **V. Logging** ✅ `logging.getLogger(__name__)`. Attach counts log mentor and apprentice IDs only. Removes an existing email from the gift-redeem log.
- [x] **VI. Compatibility** ✅ A new optional field, email made optional (old payloads still valid), wider reads and signing. The stricter checks only refuse requests that shouldn't have worked (an ended connection; a mentor redeeming a gift code). No minimum app version.
- [x] **VII. Layering** ✅ The connection and attach logic lives in `app/services/mentorship.py`. Routes stay thin.
- [x] **VIII. Tests** ✅ Success plus authz failures for each changed endpoint (quickstart §1). No live RevenueCat or SendGrid.
- [x] **IX. Deploy** ✅ Dev first, then prod from `main`. No migration step needed.
- [x] **X. Contract** ✅ [contracts/api.md](contracts/api.md). The frontend spec must link it.
- [x] **XI. Formatting** ✅ Edits are limited to the touched functions.

**Post-design re-check**: passes.

## Project Structure

### Documentation (this feature)

```text
specs/007-connected-apprentice-linking/
├── spec.md
├── plan.md                 # this file
├── research.md             # R1–R7
├── data-model.md
├── quickstart.md
├── contracts/api.md
├── checklists/requirements.md
└── tasks.md                # /speckit-tasks
```

### Source Code (repository root)

```text
app/
├── services/mentorship.py        # NEW: has_active_connection(), attach_pending_agreements()
├── services/invitations.py       # accept_invitation(): call attach_pending_agreements (FR-004)
├── schemas/agreement.py          # AgreementCreate: apprentice_id optional; apprentice_email optional; one required
├── routes/agreements.py          # create_agreement by ID (FR-001/002); apprentice_sign access rule (FR-003)
└── routes/subscriptions.py       # 3 gift-by-ID checks → has_active_connection (FR-006);
                                  #   redeem_gift_code → require_apprentice + ID-only log (FR-007/008)
tests/test_connected_apprentice_linking.py   # NEW
```

**Structure Decision**: Existing route → schema → service layout. One new service module, named for what it checks (mentorship connections).

## Complexity Tracking

No constitution violations.
