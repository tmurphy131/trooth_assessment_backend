# Research: Reliable, Fast, Consistent AI Assessment Reports

## 1. Durable execution: Cloud Tasks over REST

- **Decision**: one Cloud Tasks HTTP queue per environment (`assessment-scoring-dev`,
  `assessment-scoring-prod`, us-east4). Tasks target `POST {BACKEND_API_URL}internal/score-assessment/{id}`
  with an OIDC token for `trooth-run-sa@trooth-prod.iam.gserviceaccount.com` (audience =
  `BACKEND_API_URL`).
- **Queue retry config**: `maxAttempts=-1` (unlimited within the duration), `maxRetryDuration=3600s`,
  `minBackoff=10s`, `maxBackoff=600s`, `maxDoublings=5`. Task dispatch deadline 300 s, which matches Cloud Run's default
  300 s request timeout. One structured AI call (~35 s) plus the Premium generation (~60 s) fits
  well inside it, so no service timeout change is needed.
- **Enqueue**: `google.auth.default()` credentials on Cloud Run → REST `tasks.create`. Task name
  `score-<assessment_id>` for the first enqueue (Cloud Tasks rejects duplicate names → natural
  dedupe); re-queues use `score-<id>-<unix_ts>`.
- **Rationale**: survives instance recycling (the request-scoped task keeps CPU allocated while
  it runs), built-in exponential retry, no new dependency, no new secret.
- **Alternatives**: in-process task plus a sweep (no durability between sweeps; double-scoring
  risk); Pub/Sub push (more config, no per-task naming/dedupe); Cloud Run Jobs per assessment
  (slow cold start, heavier).
- **IAM**: the run SA needs `roles/cloudtasks.enqueuer` on the queue and
  `roles/iam.serviceAccountUser` on itself (to mint the OIDC token). Scripted in
  `scripts/scoring/setup_queue.sh`.
- **Local/test**: when `ENV` is `development` or `test`, `enqueue()` runs the pipeline inline in a
  thread (same function), so the developer experience and tests need no queue.

## 2. Telling Cloud Tasks to retry vs. stop

- The handler returns **5xx** for retryable failures (AI error, malformed output, DB hiccup), so
  Cloud Tasks retries with backoff.
- It returns **200** when the assessment is already `done` (idempotent), is missing, or retries are
  exhausted.
- It returns **503** when another live lease holds a not-yet-`done` assessment. If the holder is
  healthy, a later retry sees `done`. If the holder crashed, the retry claims the expired lease.
  Returning 200 there would drop the task and strand the assessment until the sweep.
- **Exhaustion**: computed from `X-CloudTasks-TaskRetryCount` together with the time since
  `scoring_queued_at`, which is set on submit and on **every re-queue**, so re-queued and backfilled
  assessments get a full retry window too. If the next retry would fall outside the 1-hour window
  (elapsed ≥ 3540 s), the handler marks `failed` with the last error as `failure_reason`, logs
  `scoring_failed assessment=… reason=…` plus the existing `Failed to build mentor_blob` text,
  and returns 200.

## 3. Preventing double scoring: DB lease

- **Decision**: a conditional update claims the row:
  `UPDATE assessments SET scoring_lease_until = now()+15min, scoring_attempts = scoring_attempts+1
  WHERE id=:id AND status != 'done' AND (scoring_lease_until IS NULL OR scoring_lease_until < now())`.
  `rowcount == 1` → proceed; else, if not `done`, return 503 so Cloud Tasks retries after
  backoff (see §2). The lease is cleared on completion or failure.
- **Rationale**: works the same on Postgres and SQLite (tests), with no advisory locks. The
  15-minute lease exceeds the worst-case run.
- **Write guard**: the final persist uses `WHERE status != 'done'`, so a late duplicate can't
  overwrite a completed report.

## 4. Speed: one structured AI call

- **Today**: one AI call per category (~7), sequential, each including MC questions, plus one
  mentor-blob call (≈2–3 min end to end on 2026-10-10).
- **Decision**:
  - `scoring_facts.py` grades MC from `is_correct` and computes per-category and per-topic MC
    accuracy, Biblical Knowledge %, and the previous Health Score.
  - One Gemini call gets **only the open-ended answers** plus those facts, and returns the
    `MentorReportV3` schema: per-category `level`, `observation`, `next_step`; per-question
    open-ended feedback; strengths, gaps, priority action, flags, four-week plan, conversation
    starters, resources.
  - Code then derives `category_scores` (0–10): each category's MC accuracy × 10 and open-level
    score (Flourishing 9.5, Maturing 8, Stable 6.5, Developing 5, Beginning 3) are combined 60/40
    when both exist, else whichever exists.
  - `overall_score` is the mean of `category_scores`. `health_score` uses `report_summary`.
  - `question_feedback` is MC from code (correct/incorrect + correct answer) plus open-ended
    feedback from the AI.
- **Expected latency**: one ~6–8k-token structured generation on Gemini 3.5 Flash, roughly
  20–35 s. To be measured in the quickstart against the 45 s / 90% target.
- **Cost**: ~1 call instead of ~8, and the input drops the MC questions → lower cost (SC-007).

## 5. Structured output reliability

- **Decision**: `LLMConfig.response_schema` (optional), which the Gemini provider passes as
  `GenerateContentConfig.response_schema` with `response_mime_type="application/json"`. The
  output is validated with the pydantic model. On validation failure, the handler raises →
  Cloud Tasks retry (FR-009).
- **Premium report**: its schema is large and deeply nested; Gemini's response-schema size
  limits make a full schema risky. Keep JSON mode + pydantic-lite validation of required
  top-level keys + up to 2 immediate retries inside the generation step.
- **OpenAI fallback**: uses `response_format={"type": "json_object"}` + the same pydantic
  validation (no schema). Fallback stays suppressed in health checks until credit returns.

## 6. Consistency: facts in, interpretation out

- New prompt `ai_prompt_master_assessment_v3.txt`:
  - receives `computed_facts` (health score and band, Biblical Knowledge %, per-category and
    per-topic MC results, `previous_health_score` or null);
  - the instructions forbid stating numbers not present in the facts;
  - "if previous_health_score is null, do not describe change over time";
  - the schema has no numeric score fields for the AI to fill.
- The Premium prompt gets the same `computed_facts`; `public_full_report` (from #25) still
  overwrites the executive-summary numbers as a safety net.
- **Check**: a regex test scans generated narrative fields for percentages and "N-point" phrases
  and asserts each number appears in the facts (used in quickstart review and as a unit test
  with a fixture response).

## 7. Premium report: generate once

- **In the pipeline**: after the free report is persisted and `status='done'`, if the apprentice
  or any active mentor is premium, generate the Premium report and store it in
  `scores.full_report_v1` with `full_report_status='ready'`. A failure there sets
  `full_report_status='failed'` and does not change `status`.
- **On-demand fallback** (all three full-report endpoints share one helper):
  - claim with a conditional update `full_report_status IN (NULL,'failed')`, or `'generating'`
    whose claim is older than 5 min → `'generating'`;
  - the winner generates;
  - others poll the row every 2 s for up to 90 s, then return the report, or `200
    {"status":"generating"}` with no `report` key.
- The current app treats a missing report as "not available yet" (not a crash). The frontend spec
  will poll properly.
- Also fixes the stale-draft cache path: storage moves to the assessment row only, and drafts are
  no longer written.

## 8. Recovery: sweep and re-queue

- `POST /scheduled/scoring-sweep` (cron secret), every 15 minutes via Cloud Scheduler.
  - It re-enqueues `processing` assessments older than 75 min with an expired or empty lease.
  - It also re-enqueues `failed` ones whose `failure_reason` is retryable, at most once every 6 h.
- `POST /admin/assessments/requeue` (admin or cron): body `{ids?, since?, until?,
  include_done_fallback?}`. `include_done_fallback` also selects `done` assessments whose
  `mentor_report_v2` is the empty fallback (no insights, no strengths), to backfill the
  2026-10-10 outage.
- Status `failed` → `processing` on re-queue, with `failure_reason` cleared and `scoring_queued_at = now()`.
- The sweep's "stuck" test uses `scoring_queued_at` (> 75 min) with an expired lease.

## 9. Notifications

- The mentor email moves to after the free report is done and the Premium step has finished (or
  been skipped). It's sent once (guarded by `scores.mentor_email_sent_at`), and never on failure.
- Submission-time push and in-app notifications ("completed an assessment") are unchanged.

## 10. What stays as is

- Spiritual gifts scoring (deterministic) and generic templates (`ai_scoring_generic.py`) are
  untouched.
- `generate_baseline_score` still writes baseline scores at submit, so released apps that show
  `has_scores` immediately behave as today.
