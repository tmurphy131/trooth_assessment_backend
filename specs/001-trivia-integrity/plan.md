# Implementation Plan: Trivia Integrity & Premium-Only Challenge Creation

**Branch**: `fix/trivia-integrity` | **Date**: 2026-10-08 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/001-trivia-integrity/spec.md`

## Summary

Single-player trivia moves to a server-run game session. The server:
- draws and shuffles the questions;
- sends one question at a time without the answer;
- grades each answer against the current question using its own clock (30 s + 3 s allowance);
- runs sudden death and grace tokens;
- writes one verified score when the game ends.

Competition standings count only verified scores. The old draw/submit endpoints stay on behind `TRIVIA_LEGACY_SINGLE_ENABLED` until app 2.2.0 is in both stores, then return 426.

Two changes to multiplayer:
- challenge answers must be for the current question;
- creating a challenge needs premium (403 using the existing object-style `premium_required` detail).

## Technical Context

**Language/Version**: Python 3.11

**Primary Dependencies**: FastAPI, SQLAlchemy, Alembic, Firebase Admin. No new packages.

**Storage**: PostgreSQL (Cloud SQL).
- New table `trivia_single_sessions`.
- New columns `trivia_single_scores.verified` and `.session_id`.
- Migration `20261008_add_trivia_single_sessions.py`.

**Testing**: pytest (`tests/`, SQLite in-memory via conftest fixtures). Server time is patched through a `_now()` helper, following the pattern in `trivia_competition.py`.

**Target Platform**: Google Cloud Run (dev and prod services)

**Project Type**: web-service (client: Flutter app in `trooth_assessment`)

**Performance Goals**: answering a question should add no noticeable delay. Each answer is one indexed row read and update under a row lock, well within the existing handler latency.

**Constraints**:
- The old flow must stay on until app 2.2.0 ships.
- Prod cutover is before 2026-11-01 (competition start).
- Sessions store the shuffled ID list of the whole pool (a few KB) plus one ~300-byte snapshot of the current question. There is no fixed game length; a game runs until the pool is used up, as today.
- The migration must reuse the existing `triviacategory` and `triviadifficulty` Postgres enum types (`create_type=False`).

**Scale/Scope**: low thousands of users and a handful of concurrent games. One session row per game.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Source: `.specify/memory/constitution.md`. Mark each ✅ / ❌ / N/A; every ❌ needs a row in Complexity Tracking.

- [x] ✅ **I. Auth**:
  - All new endpoints use `get_current_user` and check session ownership (404 otherwise).
  - Challenge creation is gated with `is_premium_user` and returns 403.
  - No new test shortcuts.
- [x] ✅ **II. Errors**: `HTTPException` everywhere and `detail` kept. The 403 reuses the existing object shape and adds no new shape (known debt not increased).
- [x] ✅ **III. Migrations**: `20261008_add_trivia_single_sessions.py` has a `downgrade()` and runs through the migrate job before deploy. No seed data.
- [x] ✅ **IV. Config & secrets**:
  - `trivia_legacy_single_enabled` lives in `app/core/settings.py`. It is not a secret and defaults to the safe value `true`.
  - At cutover, `TRIVIA_LEGACY_SINGLE_ENABLED=false` is added to the **full** `--set-env-vars` list in the deploy-prod skill (and deploy-dev if wanted).
- [x] ✅ **V. Logging**: `logger = logging.getLogger(__name__)` in the new session service. It logs the session id and user id only, never answers or tokens.
- [x] ✅ **VI. Compatibility**:
  - New endpoints are additive.
  - Removing the old draw/submit is specified, with minimum app version **2.2.0** (spec, Access & Compatibility).
  - New 403/400 responses on existing endpoints are documented in the contract.
  - New handlers declare a `response_model`.
- [x] ✅ **VII. Layering**: game logic goes in a new `app/services/trivia_session.py`. Routes stay thin. No LLM.
- [x] ✅ **VIII. Tests**: tests for success, not owner (404), non-premium (403), each cheat path, and old flag on/off. There are no external calls; push notifications are already stubbed via monkeypatch.
- [x] ✅ **IX. Deploy**: `/deploy-dev` and verify (quickstart) before `/deploy-prod` from `main`.
- [x] ✅ **X. Contract**: [contracts/trivia-api.md](contracts/trivia-api.md). The frontend spec 001 must link it.
- [x] ✅ **XI. Formatting**: existing files are edited in place without reformatting.

**Post-design re-check**: all ✅. No Complexity Tracking entries.

## Project Structure

### Documentation (this feature)

```text
specs/001-trivia-integrity/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/trivia-api.md
├── checklists/requirements.md
└── tasks.md             # /speckit-tasks
```

### Source Code (repository root)

```text
app/
├── core/settings.py                 # + trivia_legacy_single_enabled
├── models/trivia.py                 # + TriviaSessionStatus, TriviaSingleSession; TriviaSingleScore.verified/session_id
├── schemas/trivia.py                # + SingleStartIn, SessionAnswerIn, GraceIn, SessionQuestion, LastAnswer, SingleSessionState
├── services/trivia.py               # extract record_single_score() from submit_single_game (shared by old + session paths);
│                                    #   submit_single_game writes verified=False; challenge answer question check + time clamp
├── services/trivia_session.py       # NEW: start / answer / grace / finish / finish_stale; _now() for tests
├── services/trivia_competition.py   # compute_standings filters verified == True
└── routes/
    ├── trivia.py                    # + 4 session routes; old-flow 426 gate; premium 403 on create_challenge
    └── scheduled_tasks.py           # daily /trivia-expiry and hourly /trivia-competition-finalize both call trivia_session.finish_stale() first; fix len(int) bug
alembic/versions/20261008_add_trivia_single_sessions.py
tests/test_trivia_session.py         # NEW
tests/test_trivia_challenge_gate.py  # NEW (premium gate + current-question check)
tests/test_trivia_competition.py     # + unverified scores excluded
```

Outside this repo, at cutover only: `trooth_assessment/.claude/skills/deploy-prod/SKILL.md` gets `TRIVIA_LEGACY_SINGLE_ENABLED=false`.

**Structure Decision**: follow the existing trivia layout (one model, schema and route module per domain). The new session logic gets its own service module so `services/trivia.py` doesn't grow further and tests can patch `_now()` in one place.

## Complexity Tracking

No violations.
