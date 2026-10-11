---

description: "Task list for Reliable, Fast, Consistent AI Assessment Reports"
---

# Tasks: Reliable, Fast, Consistent AI Assessment Reports

**Input**: Design documents from `/specs/004-reliable-ai-reports/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/scoring-api.md, quickstart.md

**Tests**: Per constitution Principle VIII, every new or changed endpoint gets tests for the success path and the authorization failures that apply. The AI, Cloud Tasks and OIDC verification are mocked. Each story ends with `pytest` passing.

**Organization**: by user story. US1 wraps the **existing** scorer, so durability and honest status can ship before US2 swaps in the single-call v3 scorer.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: US1–US5 from spec.md

---

## Phase 1: Setup

- [X] T001 Add scoring settings to `app/core/settings.py`, derived from `ENV` with defaults:
  - `scoring_queue_name` (`assessment-scoring-dev` for dev, `assessment-scoring-prod` for production);
  - `scoring_queue_location` (`us-east4`);
  - `scoring_service_account` (`trooth-run-sa@trooth-prod.iam.gserviceaccount.com`);
  - `scoring_inline` (true when `ENV` is `development` or `test`);
  - `scoring_retry_window_s` (3600).
- [X] T002 [P] Create `scripts/scoring/setup_queue.sh dev|prod`, idempotent:
  - create or update queue `assessment-scoring-<env>` in us-east4 with `--max-attempts=-1 --max-retry-duration=3600s --min-backoff=10s --max-backoff=600s --max-doublings=5`;
  - grant `roles/cloudtasks.enqueuer` on the queue and `roles/iam.serviceAccountUser` on itself to `trooth-run-sa`;
  - create or update the Cloud Scheduler job `scoring-sweep-<env>` (`*/15 * * * *`, POST `<api>/scheduled/scoring-sweep`, `X-Cron-Secret` from Secret Manager, never printed);
  - add `scripts/scoring/README.md`.

---

## Phase 2: Foundational (blocks all stories)

- [X] T003 Add columns to `app/models/assessment.py`:
  - `scoring_attempts` Integer default 0;
  - `scoring_queued_at` DateTime nullable ("set on submit and every re-queue; the 1-hour retry window and the sweep's stuck test are measured from it");
  - `scoring_lease_until` DateTime nullable;
  - `scoring_completed_at` DateTime nullable;
  - `failure_reason` String(300) nullable ("short, user-safe reason when `failed`");
  - `full_report_status` String(16) nullable ("null | `generating` | `ready` | `failed`");
  - `full_report_claimed_at` DateTime nullable.

  Document `status` values `processing | done | failed`.
- [X] T004 Create migration `alembic/versions/20261011_assessment_scoring_state.py`:
  - add the T003 columns, with server default `0` for `scoring_attempts`;
  - backfill `scoring_queued_at` from `created_at`;
  - backfill `full_report_status='ready'` where `scores` contains `full_report_v1` (portable JSON check: Postgres `scores::jsonb ? 'full_report_v1'`, guarded for the dialect);
  - `downgrade()` drops the columns. Verify locally with `alembic upgrade head` against SQLite or Postgres.
- [X] T005 [P] Add optional `response_schema` to `LLMConfig` in `app/services/llm/base.py`, then:
  - in `app/services/llm/gemini_provider.py`, set `gen_config.response_schema = config.response_schema` and `response_mime_type="application/json"` when provided;
  - in `app/services/llm/openai_provider.py`, ignore it (keep `json_object`).
- [X] T006 Create `app/services/scoring_queue.py` with `enqueue(assessment_id: str, reason: str, unique: bool = False) -> str`:
  - when `settings.scoring_inline`, run `scoring_pipeline.score_assessment(id, attempt_info=None)` in a daemon thread and return `"inline"`;
  - else POST `https://cloudtasks.googleapis.com/v2/projects/trooth-prod/locations/{loc}/queues/{queue}/tasks` with `google.auth.default()` credentials (refreshed token), body `{"task": {"name": ".../tasks/score-<id>"` (or `score-<id>-<unix_ts>` when `unique`) `, "httpRequest": {"httpMethod": "POST", "url": f"{settings.backend_api_url}internal/score-assessment/{id}", "oidcToken": {"serviceAccountEmail": settings.scoring_service_account, "audience": settings.backend_api_url}}, "dispatchDeadline": "300s"}}`;
  - treat HTTP 409 (task already exists) as success.

**Checkpoint**: migration applies; existing tests pass.

---

## Phase 3: User Story 1 - Reports are never lost or silently empty (P1) 🎯 MVP

**Goal**: queued, retried, leased scoring; never `done` with fallback content; `failed` with a reason; sweep and re-queue.

**Independent Test**: quickstart §5–6 (bad `LLM_MODEL` → retries → restore → `done`; exhaust → `failed`; re-queue → `done`; restart mid-scoring → `done`).

### Tests for User Story 1

- [X] T007 [P] [US1] `tests/test_scoring_pipeline.py`, OIDC on `POST /internal/score-assessment/{id}`: valid token (mock `google.oauth2.id_token.verify_oauth2_token` returning `email=trooth-run-sa@…`, `email_verified=True`) → 200; missing, invalid, wrong email or wrong audience → 403
- [X] T008 [P] [US1] `tests/test_scoring_pipeline.py`:
  - a successful run sets `status='done'`, `scoring_completed_at`, clears the lease and returns `{"result":"done"}`;
  - a second call returns `already_done` and doesn't call the scorer;
  - a live lease held by another worker on a not-`done` assessment → **503** `retry: leased` (so Cloud Tasks retries rather than dropping the task);
  - after the lease expires, the next call claims it and completes.
- [X] T009 [P] [US1] `tests/test_scoring_pipeline.py`:
  - scorer raises, or returns the safe/empty blob while open-ended answers exist → response 503 and status stays `processing`;
  - with `X-CloudTasks-TaskRetryCount` and elapsed ≥ 3540 s since `scoring_queued_at` → `status='failed'`, `failure_reason` set, `scoring_failed assessment=… reason=…` logged, and 200 `{"result":"failed"}`;
  - an assessment created > 1 h ago but **re-queued** (fresh `scoring_queued_at`) gets retries (503) rather than failing at once;
  - no mentor email sent on failure.
- [X] T010 [P] [US1] `tests/test_scoring_pipeline.py`:
  - `POST /scheduled/scoring-sweep` re-queues `processing` with `scoring_queued_at` > 75 min ago and an expired lease and retryable `failed` ≥ 6 h (mock `enqueue`); 403 without the cron secret;
  - `POST /admin/assessments/requeue` by admin and by cron secret → 200 with ids and skipped; non-admin user → 403; empty body → 422; `include_done_fallback` selects `done` assessments whose `mentor_report_v2` has no insights and no strengths.
- [X] T011 [P] [US1] `tests/test_scoring_pipeline.py`: `GET /assessments/{id}/status` returns `reason` when failed and `health_score` when done; a stranger gets 403 (not 500); unknown → 404 (not 500)
- [X] T012 [P] [US1] `tests/test_scoring_pipeline.py`: submitting a draft calls `scoring_queue.enqueue(id, "submit")` (mocked) and no longer starts `asyncio.create_task`

### Implementation for User Story 1

- [X] T013 [US1] Create `app/services/scoring_pipeline.py` with `score_assessment(assessment_id, attempt_info) -> str`:
  - lease claim (conditional UPDATE per research §3);
  - build questions (move from `routes/assessment_draft.py:_process_assessment_background`);
  - call the **current** scorer `ai_scoring.score_assessment_by_category`;
  - **reject fallback**: if open-ended answers exist and the blob has no insights, or `category_scores` came from defaults, raise `ScoringRetryable`;
  - persist with `WHERE status != 'done'` (scores, `mentor_report_v2`, recommendation, `status='done'`, `scoring_completed_at`, lease cleared);
  - then notify mentors once (guard `scores.mentor_email_sent_at`; move the email code from the old worker);
  - return a result string.
- [X] T014 [US1] Exhaustion logic in `app/services/scoring_pipeline.py`: exhausted when elapsed since `scoring_queued_at` ≥ `settings.scoring_retry_window_s - 60`; `mark_failed(id, reason)` sets `status='failed'`, `failure_reason` (≤ 300 chars, user-safe mapping such as "AI provider unavailable"), clears the lease, and logs `scoring_failed assessment=<id> reason=<code>` plus `Failed to build mentor_blob (final)` so feature 003's alert fires
- [X] T015 [US1] Create `app/routes/internal_scoring.py` with `POST /internal/score-assessment/{assessment_id}`:
  - verify the Google OIDC token (`google.oauth2.id_token.verify_oauth2_token(token, google.auth.transport.requests.Request(), audience=settings.backend_api_url)`; require `email == settings.scoring_service_account` and `email_verified`);
  - read `X-CloudTasks-TaskRetryCount`;
  - map outcomes to the responses in contracts/scoring-api.md (503 for retryable **and for a live lease on a not-`done` assessment**; 200 for done, already-done, missing, failed);
  - register it, the `admin_scoring` router (T018) and the sweep route in `app/main.py`.
- [X] T016 [US1] In `app/routes/assessment_draft.py` `submit_draft`, set `assessment.scoring_queued_at = now()` and replace `asyncio.create_task(_process_assessment_background(...))` with `scoring_queue.enqueue(assessment.id, "submit")`:
  - on enqueue error, log and continue (the sweep recovers it);
  - delete `_process_assessment_background` (logic moved to the pipeline);
  - keep the baseline scores and submission notifications as they are.
- [X] T017 [P] [US1] Add `POST /scheduled/scoring-sweep` (`require_cron_secret`) to `app/routes/scheduled_tasks.py` per contracts (stuck = `processing` with `scoring_queued_at` > 75 min ago and an expired lease; retryable `failed` ≥ 6 h), setting `scoring_queued_at = now()` before `scoring_queue.enqueue(id, "sweep", unique=True)`
- [X] T018 [US1] Create `app/routes/admin_scoring.py` with `POST /admin/assessments/requeue`:
  - accept `require_admin` OR `require_cron_secret` (try the header first);
  - body `ids | since | until | include_done_fallback` per contracts;
  - set `status='processing'`, clear `failure_reason` and set `scoring_queued_at = now()` before enqueue (`unique=True`);
  - router registration happens in T015.
- [X] T019 [US1] Update `GET /assessments/{assessment_id}/status` in `app/routes/assessment.py`:
  - add `reason` (only when failed) and `health_score` (via `report_summary.summarize_mentor_blob` when done);
  - stop catching `HTTPException` in the broad `except`, so 403 and 404 surface correctly.

**Checkpoint**: US1 tests pass; quickstart §5–6 pass on dev.

---

## Phase 4: User Story 2 - Reports arrive in seconds (P1)

**Goal**: one structured AI call on open-ended answers only; MC and numbers computed in code.

**Independent Test**: quickstart §2 (≥ 9/10 under 45 s; `scoring_version == "master_v3"`).

### Tests for User Story 2

- [ ] T020 [P] [US2] `tests/test_scoring_pipeline.py`: `scoring_facts.compute(answers, questions, previous)` grades MC exactly from `is_correct`, gives per-category and per-topic percentages, Biblical Knowledge % and `weak_topics` (< 65%), and ignores unknown answer ids
- [ ] T021 [P] [US2] `tests/test_scoring_pipeline.py`, v3 scorer with a fixture `MentorReportV3` response (LLM mocked, asserting exactly **one** `generate` call with `response_schema` set and **no MC question text** in the prompt):
  - `category_scores` combine MC × 10 and the level map 60/40;
  - `question_feedback` includes MC (code) and open-ended (AI) entries;
  - `mentor_report_v2` has v2.1 keys (`health_score`, `health_band`, `biblical_knowledge.percent`, `insights`);
  - `scores.scoring_version == "master_v3"`.
- [ ] T022 [P] [US2] `tests/test_scoring_pipeline.py`: an assessment with no open-ended answers → no AI call, `done` with computed facts; an AI response failing schema validation → `ScoringRetryable`

### Implementation for User Story 2

- [ ] T023 [P] [US2] Create `app/services/scoring_facts.py` returning `compute(...) -> ComputedFacts` with:
  - `health_score` placeholder (computed after levels);
  - `biblical_knowledge_percent` one decimal;
  - `mc_by_category`, `mc_by_topic`, `weak_topics` (topics < 65%);
  - `previous_health_score` (from the previous assessment's `mentor_report_v2` via `summarize_mentor_blob`, else null);
  - `open_ended_count`.

  Also add `category_scores(facts, levels)` using the level map (Flourishing 9.5, Maturing 8, Stable 6.5, Developing 5, Beginning 3), 60/40 MC/open when both exist.
- [ ] T024 [P] [US2] Write prompt `ai_prompt_master_assessment_v3.txt` (repo root, next to v2):
  - interpretation-only instructions;
  - input: open-ended Q&A, plus `computed_facts` without `health_score`;
  - output must match the schema, with no numbers except those in `computed_facts`;
  - "Health Score is computed by the system; do not state it";
  - "if previous_health_score is null, do not describe change over time".
- [ ] T025 [US2] In `app/services/ai_scoring.py`, add the pydantic `MentorReportV3` (fields from data-model.md: `categories[{category, level ∈ {Flourishing, Maturing, Stable, Developing, Beginning}, observation, next_step}]`, `open_feedback[{question_id, feedback}]`, `strengths` (≤ 5), `gaps` (≤ 5), `priority_action{title, steps, scripture}`, `flags{red,yellow,green}`, `four_week_plan{rhythm,checkpoints}`, `conversation_starters`, `recommended_resources[{title,why,type}]`) and `score_master_v3(answers, questions, previous) -> dict`:
  - compute facts;
  - if open-ended answers exist, make **one** `get_llm_service().generate(system_prompt=<v3 prompt>, user_content=json(payload), config=LLMConfig(response_schema=MentorReportV3, temperature=0.2, max_tokens=8000))` and validate;
  - compute `category_scores`, `overall_score`, `question_feedback` and the health score via `report_summary.compute_health_score`;
  - map to `mentor_report_v2` (v2.1 shape) and the `scores` dict (keys kept per data-model.md, plus `computed_facts`, `scoring_version`).
- [ ] T026 [US2] Switch `app/services/scoring_pipeline.py` to `score_master_v3` for Master assessments (category `master_trooth` or template `is_master_assessment`); other categories keep their current scorer

**Checkpoint**: US2 tests pass; quickstart §2 meets 45 s / 90%.

---

## Phase 5: User Story 3 - Report content matches the numbers (P2)

**Goal**: narratives never invent numbers; free and Premium agree.

**Independent Test**: quickstart §3.

- [ ] T027 [P] [US3] `tests/test_scoring_pipeline.py`: `narrative_numbers_ok(report_text, facts)` flags percentages or "N-point" phrases not present in the facts, and change-over-time phrases ("improve", "increase", "decline", "up from", "down from") when `previous_health_score` is null; applied to a fixture v3 response
- [ ] T028 [US3] Implement `narrative_numbers_ok` in `app/services/scoring_facts.py` and call it in `score_master_v3`: on violation, retry the generation once with an added corrective instruction, then accept and log `report_number_mismatch assessment=…` (don't fail the report)
- [ ] T029 [US3] Pass the same `computed_facts` (now including the final `health_score` and `health_band`) into the Premium generation payload in `app/services/ai_scoring.generate_full_report` and `generate_full_report_for_assessment`, with the same no-invented-numbers instruction appended to the system prompt; keep `public_full_report` as the safety net

---

## Phase 6: User Story 4 - Premium report opens instantly and never errors (P2)

**Goal**: Premium generated in the scoring task; on-demand fallback claimed once; no 500s.

**Independent Test**: quickstart §4.

### Tests for User Story 4

- [ ] T030 [P] [US4] `tests/test_scoring_pipeline.py`:
  - after `done`, when the apprentice or an active mentor is premium, the pipeline generates and stores `full_report_v1` with `full_report_status='ready'`;
  - a Premium failure leaves `status='done'` and sets `full_report_status='failed'`;
  - the mentor email is sent once after the Premium step.
- [ ] T031 [P] [US4] `tests/test_scoring_pipeline.py`, on-demand helper:
  - `ready` → returned without generating;
  - two concurrent claims (simulate by pre-setting `generating` with a fresh `full_report_claimed_at`) → the second caller waits and gets the report when the first stores it, or `{"status":"generating"}` after the wait;
  - a stale claim (> 5 min) is re-claimed;
  - generation that raises twice → 503 "Report is temporarily unavailable" (never 500).

  Covers all three endpoints, with premium 403s unchanged.

### Implementation for User Story 4

- [ ] T032 [US4] Create `get_or_generate_full_report(db, assessment, requester, wait_s=90) -> dict` in a new `app/services/full_report.py`:
  - claim via a conditional UPDATE on `full_report_status`/`full_report_claimed_at`;
  - the winner generates (≤ 2 retries on malformed output), stores it in `assessment.scores['full_report_v1']` with `full_report_status='ready'`, and stops writing the draft copy;
  - waiters poll every 2 s;
  - returns `{"report": public_full_report(...), "cached": bool}` or `{"status": "generating", "cached": false}`;
  - raises a 503 `HTTPException` on final failure.
- [ ] T033 [US4] Replace the generate/cache code in `app/routes/assessment.py` (`get_own_full_report`), `app/routes/apprentice.py` (`get_my_full_report`) and `app/routes/mentor.py` (`get_full_report`) with `get_or_generate_full_report`, keeping their auth, premium and lookup logic and response keys
- [ ] T034 [US4] In `app/services/scoring_pipeline.py`, after the free report is persisted, determine premium (apprentice or any active mentor, via `is_premium_user`), call the generation path of `full_report.py` (claim then generate), and catch failures (`full_report_status='failed'`); then send the mentor email (Premium template when the report is ready, else the free template)

---

## Phase 7: User Story 5 - App shows a clear status (P3)

**Goal**: an updated app shows preparing and delayed states (implemented in `trooth_assessment`).

- [ ] T035 [US5] Create the frontend spec in `/Users/tmoney/Developer/trooth_assessment/specs/` via `/speckit-specify` in that repo, linking `specs/004-reliable-ai-reports/contracts/scoring-api.md`:
  - apprentice and mentor report screens show "Preparing your report…" while `status=processing` (auto-poll);
  - they show "Taking longer than usual — we're on it" when `failed`;
  - when the Premium report returns `status: generating`, poll and show a loading state. Today released apps mark the user premium and show an empty Premium section without polling.
- [ ] T036 [US5] Confirm backward compatibility with the current store app on dev (quickstart §8) and record the result in the PR

---

## Phase 8: Polish & Cross-Cutting

- [ ] T037 Keep `score_assessment_by_category` in `app/services/ai_scoring.py`: it's still used by `ai_scoring_master.score_master_assessment` (the unused legacy `POST /assessments/master-trooth/submit`) and by `tests/test_master_v2_reporting.py`. Remove only helpers that `grep` shows nothing references, and note the legacy route in the PR.
- [ ] T038 [P] Update `scripts/monitoring/setup.py` docs/README if alert text changes (the `scoring_failed` line already matches "Scoring fallback" via the "Failed to build mentor_blob (final)" log); no new policy expected
- [ ] T039 Run `.venv/bin/python -m pytest -q`; all pass
- [ ] T040 `/deploy-dev` (migrate job runs the new migration), `scripts/scoring/setup_queue.sh dev`, then quickstart §2–8, recording in the PR:
  - timings;
  - **AI tokens and cost per assessment** for the 10 runs (from the `[ai_scoring] … tokens= cost=` log lines) against pre-change runs (SC-007);
  - the SC-002 / SC-003 SQL checks from quickstart §10.
- [ ] T041 After merge: `/deploy-prod`, `scripts/scoring/setup_queue.sh prod`, quickstart §9 including a prod backfill for the 2026-10-10 window if empty reports exist

---

## Dependencies & Execution Order

- Phase 1 → Phase 2 (T003 → T004; T005 and T006 can run in parallel after T001) → US1.
- **US1** (T007–T019) uses the current scorer and is shippable on its own (MVP).
- **US2** depends on US1's pipeline (T013) and T005.
- **US3** depends on US2 (T025).
- **US4** depends on US1 (pipeline) and can run in parallel with US2/US3, except T034, which touches `scoring_pipeline.py` after T026.
- **US5** depends on the contract only (frontend repo).
- Polish last.

## Parallel Opportunities

- T002 with T003–T006.
- US1 tests T007–T012 together; T017 in parallel with T015 and T016 (T018 follows T015, which registers its router).
- US2: T020–T022 together; T023 and T024 in parallel.
- US4 tests T030 and T031 together; T032 in parallel with US2 work.

## Implementation Strategy

1. **MVP = Setup + Foundational + US1**: no lost or empty reports, honest `failed`, recovery tools. Deployable on its own.
2. **US2** next (the biggest user-visible win: about 3 min → under 45 s), then **US4** (Premium never errors), then **US3** (consistency checks).
3. **US5** in the app repo after the backend is on dev.
4. Ship as one PR per milestone or a single PR with the quickstart results recorded, per the owner's preference.
