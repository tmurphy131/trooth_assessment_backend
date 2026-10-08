---

description: "Task list for 001-trivia-integrity"
---

# Tasks: Trivia Integrity & Premium-Only Challenge Creation

**Input**: Design documents from `/specs/001-trivia-integrity/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/trivia-api.md, quickstart.md

**Tests**: Principle VIII requires test tasks for every new or changed endpoint: the success path plus the authorization failures that apply (not the owner, non-premium). Tests use conftest fixtures (`db_session`, `client`, `app.dependency_overrides[get_current_user]`, as in `tests/test_trivia_competition.py`) and mock external services. Each story ends with `pytest` passing.

**Organization**: tasks are grouped by user story (spec.md):
- US1: server-run single player (P1)
- US2: the old flow is told to update (P1)
- US3: multiplayer answers must match the current question (P1)
- US4: premium-only challenge creation (P2)

## Format: `[ID] [P?] [Story] Description`

---

## Phase 1: Setup (Shared Infrastructure)

- [X] T001 Add `self.trivia_legacy_single_enabled = self._parse_bool(os.getenv("TRIVIA_LEGACY_SINGLE_ENABLED", "true"))` in the "Trivia competition" block of `app/core/settings.py`, with a one-line comment: old `/trivia/questions/draw` and `/single/submit`; set false once app 2.2.0 is in both stores.

---

## Phase 2: Foundational (Blocking Prerequisites)

**⚠️ CRITICAL**: US1 and US2 depend on the score columns. US1 depends on the session model.

- [X] T002 In `app/models/trivia.py`, add the `TriviaSessionStatus` enum (`active`, `awaiting_grace`, `finished`) and the `TriviaSingleSession` model (`__tablename__ = "trivia_single_sessions"`). Fields exactly as in data-model.md:
  - `id` String uuid4 PK
  - `user_id` String FK `users.id` indexed not null
  - `category` Enum(TriviaCategory)
  - `difficulty` Enum(TriviaDifficulty)
  - `question_ids` JSON not null (the whole approved pool, shuffled, with no fixed game length)
  - `current_index` Integer default 0
  - `current_question` JSON nullable (a snapshot of the question being served, `{id, question_text, question_type, options:{a,b,c?,d?}, correct}`)
  - `current_served_at` DateTime tz nullable
  - `answers` JSON default `[]`
  - `score`, `streak`, `max_streak`, `correct_count`, `grace_tokens`, `grace_tokens_used`: Integer default 0
  - `grace_deadline` DateTime tz nullable
  - `status` Enum(TriviaSessionStatus) default active, indexed
  - `result` JSON nullable
  - `created_at`, `last_activity_at` DateTime tz default now(UTC)
  - `finished_at` DateTime tz nullable
- [X] T003 In `app/models/trivia.py`, add two columns to `TriviaSingleScore`: `verified = Column(Boolean, nullable=False, default=False, server_default=sa.false())` and `session_id = Column(String, ForeignKey("trivia_single_sessions.id"), nullable=True)`.
- [X] T004 Create `alembic/versions/20261008_add_trivia_single_sessions.py` with `revision='20261008_trivia_single_sessions'` and `down_revision='20261003_trivia_competitions'`.
  - `upgrade()`:
    - create the `triviasessionstatus` enum and the `trivia_single_sessions` table matching T002, with indexes on `user_id` and `status`;
    - for the `category` and `difficulty` columns, **reuse the existing Postgres types** with `postgresql.ENUM(<values>, name='triviacategory', create_type=False)` and `postgresql.ENUM(<values>, name='triviadifficulty', create_type=False)`, exactly as `a1b2c3d4e5f6_add_trivia_tables.py:19-39` does. A plain `sa.Enum` runs `CREATE TYPE` again and fails on Cloud SQL;
    - add `trivia_single_scores.verified` (Boolean, not null, server_default false);
    - add `trivia_single_scores.session_id` (String, FK, nullable).
  - `downgrade()`: drop both columns, the table and **only** the `triviasessionstatus` enum (never `triviacategory` or `triviadifficulty`).
  - Hand-written, following the style of `20261003_add_trivia_competitions.py`.
- [X] T005 In `app/services/trivia.py`, extract `record_single_score(db, user_id, category, difficulty, score, streak_length, correct_count, grace_tokens_used, verified, session_id=None) -> SingleGameResult` from `submit_single_game`.
  - It covers persisting the score, previous best, leaderboard rank, badges and the commit.
  - Add an optional `created_at: Optional[datetime] = None` parameter. When it is given, it is set on the `TriviaSingleScore` row (session scores pass the session's start time, research R10). When it is omitted, the column default applies.
  - `submit_single_game` calls it with `verified=False`.
  - Its behaviour and response stay otherwise identical.

**Checkpoint**: `alembic upgrade head` works locally, and the existing `pytest` suite still passes.

---

## Phase 3: User Story 1 - Single-player scores can't be faked (Priority: P1) 🎯 MVP

**Goal**: games are run and graded only by the server. Competition standings count only verified scores.

**Independent Test**: play a full game through the four session endpoints. No `correct_option` is sent before answering, cheats are refused, and exactly one verified score is written.

### Tests for User Story 1 ⚠️

- [X] T006 [P] [US1] Create `tests/test_trivia_session.py`.
  - Fixtures: seed 55 approved questions for one category and difficulty, plus a few for another, and patch `trivia_session._now` for time control. Datetimes come back naive from SQLite, so the service's `_aware()` path is exercised.
  - Tests:
    - over a full 55-question game of correct answers, **no** start or answer response contains `correct_option` inside `question` (SC-001); `total_questions == 55`; after the 55th answer the status is `finished` (pool used up);
    - a correct answer advances and scores 100 × multiplier;
    - wrong `question_id` → 400, state unchanged;
    - retrying the last answer → 200, same state, not graded twice, including retrying the answer that **finished** the game and the one that triggered `awaiting_grace` (no 409);
    - answer more than 33 s after the question was served → `timed_out=true` and graded wrong;
    - wrong answer with no tokens → `finished`, one `TriviaSingleScore` with `verified=True` and `session_id` set;
    - 10 correct, then wrong → `awaiting_grace`; `grace use=true` → active with next question, streak kept, token spent;
    - grace after 13 s → finished;
    - `grace use=false` → finished;
    - answer while `awaiting_grace` → 409; answer or grace on a finished game → 409;
    - another user's session on any endpoint → 404;
    - `finish` twice → same result, one score row;
    - start while one is unfinished → the old one is finished and recorded;
    - no questions for the category → 400;
    - a verified score's `created_at` equals the session's `created_at` (game start), even when finished hours later;
    - `finish_stale` finishes sessions idle for over 1 h.
- [X] T007 [P] [US1] In `tests/test_trivia_competition.py`, add a test that a `TriviaSingleScore` with `verified=False` inside the window is excluded from `compute_standings`, and one with `verified=True` is included. Mark scores in the existing tests' helpers `verified=True` so they keep passing. Also add a test: a session started 10 minutes before `END` and left unfinished. Run the finalize path (call `trivia_session.finish_stale` then `finalize_competition`, as the route does) at `AFTER` with the session idle for over 1 h. Its score is included in the standings.

### Implementation for User Story 1

- [X] T008 [P] [US1] In `app/schemas/trivia.py`, add the following, matching contracts/trivia-api.md field for field:
  - `SingleStartIn {category: TriviaCategory, difficulty: TriviaDifficulty}`
  - `SessionAnswerIn {question_id: int, selected: Optional[str] = None}`
  - `GraceIn {use: bool}`
  - `SessionQuestion {index, id, question_text, question_type, option_a, option_b, option_c?, option_d?}`, with **no correct_option field**
  - `LastAnswer {question_id, selected?, correct, correct_option, timed_out}`
  - `SingleSessionState {session_id, status, score, streak, correct_count, grace_tokens, grace_tokens_used, question_number, total_questions, time_limit_ms, question?, last_answer?, grace_expires_in_ms?, result?: SingleGameResult}`
- [X] T009 [US1] Create `app/services/trivia_session.py` with `logger = logging.getLogger(__name__)`.
  - Constants: `TIME_LIMIT_MS=30000`, `GRACE_WINDOW_MS=10000`, `ALLOWANCE_MS=3000`, `IDLE_LIMIT=timedelta(hours=1)`. There is **no** question cap.
  - `_now()` returns `datetime.now(UTC)` and is patched in tests.
  - `_aware(dt)` returns `dt.replace(tzinfo=UTC)` when naive, as in `trivia_competition._aware`. Wrap **every** stored timestamp in it before comparing.
  - Implement the following:
    - `start(db, user, category, difficulty)`:
      - finish any unfinished session of the user;
      - query the IDs of **all** approved questions for the category and difficulty (all categories when `random`), shuffle them into `question_ids`, and raise 400 "No questions available" if empty;
      - serve index 0 via `_serve(session)`.
    - `_serve(session)`: load `question_ids[current_index]`, run it through `trivia._shuffle_options`, store `current_question = {id, question_text, question_type, options:{a,b,c,d}, correct}`, and set `current_served_at=_now()`. Skip IDs whose question has since been deleted or unapproved.
    - `answer(db, user, session_id, question_id, selected)`, applying in order:
      - lock the row (`with_for_update`); 404 if missing or not owned;
      - **retry rule first** (research R5): if `answers` is non-empty and `question_id == answers[-1].question_id`, return `to_state(session, last_answer=<from answers[-1]>)` unchanged, whatever the status;
      - lazily resolve an expired grace (finish);
      - 409 if not `active`; 400 "Answer is not for the current question" if `question_id != current_question.id`;
      - `timed_out` when elapsed > 33 000 ms;
      - grade against `current_question.correct`;
      - on correct: streak/max_streak/correct_count; earn a token when `correct_count % 10 == 0`;
      - on wrong: with a token → `awaiting_grace` and `grace_deadline = now + 13 s`; without → finish;
      - recompute `score` with `trivia.compute_score_for_answers` over non-graced answers;
      - advance and `_serve` the next question, or finish when `current_index` reaches `len(question_ids)` (pool used up).
    - `use_grace(db, user, session_id, use)`: 409 "No grace decision pending" unless `awaiting_grace`. A call past the deadline or `use=False` finishes. Otherwise spend the token, mark the last answer `graced=True`, recompute the score, and serve the next question.
    - `finish(db, user, session_id)`: idempotent; returns the stored `result`.
    - `_finish(db, session)`: calls `trivia.record_single_score(..., verified=True, session_id=session.id, created_at=session.created_at)`, stores `result`, sets `finished_at`, clears `current_question`, and treats a pending grace answer as wrong.
    - `finish_stale(db) -> int`: finishes sessions not `finished` whose `last_activity_at` is before now − 1 h.
    - `to_state(session, last_answer=None)`: builds `SingleSessionState`. `question` is built from `current_question` **without** `correct`. `total_questions = len(question_ids)`.
  - Every mutation updates `last_activity_at`.
- [X] T010 [US1] In `app/routes/trivia.py`, add `POST /single/start`, `POST /single/{session_id}/answer`, `POST /single/{session_id}/grace` and `POST /single/{session_id}/finish`. Each uses `get_current_user` and declares a `response_model` (`SingleSessionState`; `SingleGameResult` for finish) and calls `trivia_session`. Declare them **before** any route that could shadow `/single/{...}`.
- [X] T011 [US1] In `app/services/trivia_competition.py`, add `TriviaSingleScore.verified == True` to the `compute_standings` filter.
- [X] T012 [US1] In `app/routes/scheduled_tasks.py`:
  - make `trigger_trivia_expiry` also call `trivia_session.finish_stale(db)` and return `finished_sessions` in its response;
  - before recording winners, `finalize_competition` (`app/services/trivia_competition.py`) calls `trivia_session.games_in_progress_before(db, comp.ends_at, now)`. That closes stale games and returns `waiting_for_games` while a game started before the end is still live (FR-013). This is done in the service rather than the route, so every caller gets it.

**Checkpoint**: `pytest tests/test_trivia_session.py tests/test_trivia_competition.py` passes.

---

## Phase 4: User Story 2 - Old app versions are told to update (Priority: P1)

**Goal**: the old draw/submit keep working behind a setting, record unverified scores, and return 426 when turned off.

**Independent Test**: flag on → old flow works and scores are `verified=False`. Flag off → both return 426 and nothing is written.

### Tests for User Story 2 ⚠️

- [X] T013 [P] [US2] In `tests/test_trivia_session.py` (section "legacy"), add these tests:
  - With `monkeypatch.setattr(settings, "trivia_legacy_single_enabled", True)`, `GET /trivia/questions/draw` returns 200 and `POST /trivia/single/submit` returns 200, and the stored score has `verified=False`.
  - With it set False, both return 426 with `detail == "Please update the app to keep playing trivia."`, and no `TriviaSingleScore` row is added.

### Implementation for User Story 2

- [X] T014 [US2] In `app/routes/trivia.py`, add a dependency `_require_legacy_single()` that raises `HTTPException(status_code=426, detail="Please update the app to keep playing trivia.")` when `settings.trivia_legacy_single_enabled` is false. Attach it to `draw_questions` and `submit_single_game`. (The `verified=False` part is covered by T005.)

**Checkpoint**: the legacy tests pass.

---

## Phase 5: User Story 3 - Multiplayer answers must match the current question (Priority: P1)

**Goal**: a challenge answer is only accepted for the current question, and `time_used_ms` is clamped.

**Independent Test**: in an active challenge, an answer for the wrong question gets 400 and the right one is accepted.

### Tests for User Story 3 ⚠️

- [X] T015 [P] [US3] Create `tests/test_trivia_challenge_gate.py` (section "current question"). Build an active challenge with known `question_ids` directly in the DB, then:
  - answering `question_ids[1]` while on index 0 → 400 `"Answer is not for the current question"`, and the answers list is unchanged;
  - answering `question_ids[0]` → 200;
  - `time_used_ms=-5` is stored as 0, and `99999` is stored as 30000.

### Implementation for User Story 3

- [X] T016 [US3] In `app/services/trivia.py` `submit_challenge_answer`:
  - After the participant check, raise `HTTPException(400, "Answer is not for the current question")` when `challenge.current_question_index >= len(challenge.question_ids)` or `question_id != challenge.question_ids[challenge.current_question_index]`.
  - Clamp with `time_used_ms = max(0, min(time_used_ms, 30000))` before building `answer_entry`.

**Checkpoint**: the current-question tests pass.

---

## Phase 6: User Story 4 - Only premium users can create challenges (Priority: P2)

**Goal**: creating a challenge needs premium. Everything else in a challenge stays open to participants.

**Independent Test**: a free user gets 403 on create. A premium user challenges a free user, and the free user accepts and finishes.

### Tests for User Story 4 ⚠️

- [X] T017 [P] [US4] In `tests/test_trivia_challenge_gate.py` (section "premium"), stub the push notifications in `app.routes.trivia` with monkeypatch, then test:
  - a free user (`subscription_tier="free"`) `POST /trivia/challenges` → 403 with `detail["error"] == "premium_required"`, no `TriviaChallenge` row, no push;
  - a `mentor_premium` user → 200;
  - an `apprentice_premium` user → 200;
  - an expired premium user (`subscription_expires_at` in the past) → 403;
  - a free challenged user can accept, then answer every question to `complete`, and can nudge and forfeit.

### Implementation for User Story 4

- [X] T018 [US4] In `app/routes/trivia.py` `create_challenge`, as the first statement: `if not is_premium_user(current_user): raise HTTPException(status_code=403, detail={"error": "premium_required", "message": "Premium subscription required to create challenges", "upgrade_url": "/settings/subscription"})`. Import `is_premium_user` from `app.services.auth`. Do not touch the accept, decline, answer, forfeit, nudge, cancel or list routes.

**Checkpoint**: `pytest tests/test_trivia_challenge_gate.py` passes.

---

## Phase 6b: Clock keeps running while away (added after product review)

- [X] T026 [US1] In `app/services/trivia_session.py` `answer()`, for a wrong or late answer with a grace token, set `grace_deadline = min(now, served_at + 30 s) + GRACE_WINDOW + ALLOWANCE`. If `now` is already past it, finish the game (no grace offer).
- [X] T027 [US1] In `app/services/trivia_session.py` `_is_stale()`, also treat an `active` session as stale once `served_at + 30 s + 3 s` has passed (or `+ 10 s + 3 s` more if `grace_tokens > 0`), so `finish_stale` and the competition finalize close it without waiting 1 h.
- [X] T028 [P] [US1] In `tests/test_trivia_session.py`, add tests:
  - a late answer (35 s) with a token → `awaiting_grace` with about 8 s left;
  - away 44 s with a token → `finished`, no grace;
  - `finish_stale` closes an expired-question game after 34 s (no token) and 47 s (token), but not at 20 s.
  Update `test_finish_stale_closes_idle_games` and the competition "waiting for games" test to the new rule.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [X] T019 Fix the existing bug in `app/routes/scheduled_tasks.py` `trigger_trivia_expiry`: `expire_stale_challenges` returns an `int`, but the route calls `len(expired_ids)`, which raises TypeError after the commit. Change `expire_stale_challenges` in `app/services/trivia.py` to return the list of expired challenge IDs, so the route's `len()` and `expired_ids` fields work. Add a test in `tests/test_trivia_challenge_gate.py` that calls the function and checks the IDs returned.
- [X] T020 Remove the now-stale comment `# included for single player draw; omitted for multiplayer` on `TriviaQuestionOut.correct_option` in `app/schemas/trivia.py`. Replace it with `# legacy single-player draw only (removed at app 2.2.0)`.
- [X] T021 Run the full `pytest` suite; it must pass.
- [X] T022 Run `alembic upgrade head` then `alembic downgrade -1` then `alembic upgrade head` against a local Postgres (or confirm on the dev migrate job).
- [X] T023 Check that `contracts/trivia-api.md` matches the implemented status codes, `detail` strings and field names. Fix whichever side is wrong.
- [ ] T024 Deploy to dev (`/deploy-dev`, migrations first) and run quickstart.md "Manual on dev" steps 1–6.
- [ ] T025 After app 2.2.0 is live in both stores: add `TRIVIA_LEGACY_SINGLE_ENABLED=false` to the full `--set-env-vars` list in `trooth_assessment/.claude/skills/deploy-prod/SKILL.md` and redeploy prod **from `main`** (Principle IX) before 2026-11-01 (quickstart "Prod cutover").

---

## Dependencies & Execution Order

- **Setup (T001)** → used by US2 (T014).
- **Foundational (T002–T005)** blocks US1 and US2. US3 and US4 touch only challenge code and can start right after Setup.
- **US1 (T006–T012)**: T008 can run in parallel with tests. T009 depends on T002, T005 and T008. T010 depends on T009. T011 and T012 depend on T003 and T009.
- **US2 (T013–T014)**: depends on T001 and T005.
- **US3 (T015–T016)** and **US4 (T017–T018)**: independent of US1 and US2. Both edit `tests/test_trivia_challenge_gate.py`, so write those sections one after the other.
- **Polish (T019–T025)**: after the stories. T025 is gated on the app release.

## Parallel Example

```bash
# After Phase 2:
Task: "T006 tests/test_trivia_session.py"
Task: "T007 tests/test_trivia_competition.py verified filter test"
Task: "T008 schemas in app/schemas/trivia.py"
Task: "T016 challenge current-question check in app/services/trivia.py"   # US3, different function
```

## Implementation Strategy

1. **MVP**: Setup + Foundational + US1 + US2. That closes the competition hole with old clients still working.
2. Add US3 and US4. They are small and independent, and can ship in the same deploy.
3. Deploy dev → verify → deploy prod with old endpoints still on. The frontend spec 001 is built against the contract.
4. Once app 2.2.0 is in both stores → T025 cutover before Nov 1.

## Notes

- Don't commit until asked. When committing: `fix(trivia): ...` / `feat(trivia): ...`.
- `[P]` = different files, no dependency on unfinished tasks.
