# Implementation Plan: Reliable, Fast, Consistent AI Assessment Reports

**Branch**: `feature/ai-scoring-pipeline` | **Date**: 2026-10-10 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/004-reliable-ai-reports/spec.md`

## Summary

Move Master-assessment scoring from an in-process `asyncio.create_task` to a **Cloud Tasks**
queue per environment that calls an internal, OIDC-authenticated endpoint; Cloud Tasks retries
with backoff for 1 hour. A database lease on the assessment stops concurrent double-scoring.
Scoring becomes **one structured AI call**, using Gemini's `response_schema` from a pydantic
model, for the open-ended interpretation only. Multiple-choice grading, category scores, the
Health Score and Biblical Knowledge are computed in code and passed to the AI as facts. A run
that can't produce real AI content is never marked `done`: it retries, then ends `failed`
with a reason. The Premium report is generated in the same task right after the free report
is saved. On-demand generation stays as a fallback behind a DB claim, so it runs at most once.
A sweep plus an admin re-queue endpoint recover stuck, failed or outage-emptied assessments.
The status endpoint gains `failed` and `reason` (additive). The app follow-up is a separate
frontend spec.

## Technical Context

**Language/Version**: Python 3.11

**Primary Dependencies**: FastAPI, SQLAlchemy, Alembic, `google-genai` (Vertex Gemini, already
used), `google-auth` (already installed via firebase-admin; used for Cloud Tasks REST calls and
OIDC token verification), httpx. **No new packages.**

**Storage**: PostgreSQL. New columns on `assessments` (migration
`alembic/versions/20261011_assessment_scoring_state.py`): `scoring_attempts`, `scoring_queued_at`,
`scoring_lease_until`, `scoring_completed_at`, `failure_reason`, `full_report_status`,
`full_report_claimed_at`. `status` gains the value `failed` (it's a `String` column, so no
enum change).

**Testing**: pytest (`tests/`, SQLite in-memory). The LLM, Cloud Tasks and OIDC verification
are mocked.

**Target Platform**: Cloud Run (`trooth-backend`, `trooth-backend-dev`), Cloud Tasks queues
`assessment-scoring-{dev,prod}` in us-east4, Cloud Scheduler for the sweep.

**Project Type**: web-service (client: Flutter app; follow-up spec in `trooth_assessment`)

**Performance Goals**: free report ready ≤ 45 s for 90% of Master submissions (today 2–3 min);
the submit request itself returns as today (< 2 s).

**Constraints**: AI cost per assessment must not rise (one call instead of ~8). Retry window of
at least 1 hour, measured from `scoring_queued_at`. Released apps must keep working. Spiritual
gifts, generic templates and the unused legacy `POST /assessments/master-trooth/submit` (sync)
keep their current scoring paths, so `score_assessment_by_category` stays.

**Scale/Scope**: tens of submissions per day; queue throughput isn't a concern. The design
priority is correctness under failure.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **I. Auth** ✅
  - The internal task endpoint verifies a Google-signed OIDC token for the run service account,
    with audience = API base URL.
  - The re-queue endpoint uses `require_admin` or `require_cron_secret`; the sweep uses
    `require_cron_secret`.
  - The status and full-report endpoints keep their current owner and active-mentor checks and
    premium 403s.
- [x] **II. Errors** ✅ — `HTTPException` only. The status endpoint stops wrapping 403/404 in a
  500 (it does today). "Being prepared" is a normal 200 body after a bounded wait, not an error.
- [x] **III. Migrations** ✅ — `20261011_assessment_scoring_state.py` adds nullable or defaulted
  columns, with `downgrade()` dropping them. Run via the migrate job before deploy.
- [x] **IV. Config & secrets** ✅
  - Queue name, location and service account are settings derived from `ENV`, with defaults:
    `assessment-scoring-dev` or `assessment-scoring-prod`, `us-east4`,
    `trooth-run-sa@trooth-prod.iam.gserviceaccount.com`.
  - The OIDC audience comes from `BACKEND_API_URL`, which is already deployed.
  - No new secrets and no deploy env/secret list changes.
  - Local and test runs score inline, with no queue.
- [x] **V. Logging** ✅ — named loggers. Scoring failures keep the `Failed to build mentor_blob` /
  `[llm] … error` text that feature 003's alerts match, and add `scoring_failed assessment=…
  reason=…`. No answer text or PII in logs.
- [x] **VI. Compatibility** ✅
  - Status gets the additive value `failed` and an optional `reason`.
  - `scores` keeps `category_scores`, `recommendations`, `question_feedback`, `overall_score`,
    `summary_recommendation` and `mentor_blob_v2`, which the app reads.
  - Full-report responses are unchanged in shape.
- [x] **VII. Layering** ✅ — the pipeline lives in `app/services/scoring_pipeline.py` and the queue
  client in `app/services/scoring_queue.py`. All AI calls go through `app/services/llm/`
  (`LLMConfig` gains an optional `response_schema`).
- [x] **VIII. Tests** ✅ — the task endpoint (valid, invalid and missing token), re-queue and sweep
  (admin or cron OK, others 403), status (`failed` and `reason`), lease/idempotency, retry →
  failed transition, no-`done`-on-fallback, the Premium claim under concurrency, and computed
  facts in prompts. All external calls are mocked.
- [x] **IX. Deploy** ✅ — `/deploy-dev` → `scripts/scoring/setup_queue.sh dev` → quickstart
  (including the outage simulation) → prod from `main`.
- [x] **X. Contract** ✅ — [contracts/scoring-api.md](contracts/scoring-api.md). The frontend spec
  for User Story 5 will link it.
- [x] **XI. Formatting** ✅ — no reformatting of touched files.

## Project Structure

### Documentation (this feature)

```text
specs/004-reliable-ai-reports/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/scoring-api.md
└── tasks.md            # /speckit-tasks
```

### Source Code (repository root)

```text
app/
├── services/scoring_pipeline.py      # NEW: score_assessment(id) — lease, facts, one AI call, persist, premium, notify
├── services/scoring_queue.py         # NEW: enqueue(id, reason) via Cloud Tasks REST; inline in dev/test
├── services/scoring_facts.py         # NEW: deterministic MC grading, per-category/topic stats, category scores, health
├── services/ai_scoring.py            # one structured call (v3 prompt + MentorReportV3 schema); old per-category path kept only for generic templates if used
├── services/llm/base.py              # LLMConfig.response_schema (optional)
├── services/llm/gemini_provider.py   # pass response_schema → GenerateContentConfig.response_schema
├── services/report_summary.py        # reuse canonical health (from #25)
├── routes/internal_scoring.py        # NEW: POST /internal/score-assessment/{id} (OIDC)
├── routes/assessment_draft.py        # submit: enqueue instead of asyncio.create_task; remove _process_assessment_background body
├── routes/assessment.py              # status: failed + reason; full-report claim/wait fallback
├── routes/apprentice.py, mentor.py   # full-report fallback uses the shared claim helper
├── routes/scheduled_tasks.py         # POST /scheduled/scoring-sweep (cron)
├── routes/admin_scoring.py           # NEW: POST /admin/assessments/requeue (admin or cron)
├── models/assessment.py              # new columns
├── core/settings.py                  # scoring queue settings derived from ENV
└── main.py                           # include new routers
ai_prompt_master_assessment_v3.txt    # NEW prompt: facts in, interpretation out
alembic/versions/20261011_assessment_scoring_state.py
scripts/scoring/setup_queue.sh        # NEW: queue + IAM + sweep scheduler job (idempotent)
tests/test_scoring_pipeline.py        # NEW
```

**Structure Decision**: the existing service/route layering, with the queue and OIDC in
services. GCP resources are scripted, as in feature 003.

## Complexity Tracking

No constitution violations.
