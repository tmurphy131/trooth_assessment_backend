# Quickstart: validate reliable AI reports

## Prerequisites

- Backend branch deployed to dev (`/deploy-dev`), migration applied by the migrate job.
- Queue, IAM and sweep set up: `scripts/scoring/setup_queue.sh dev` (idempotent).
- Guide test accounts (Premium) from `scripts/site/guide_capture/seed/`.

```bash
KEY=$(gcloud secrets versions access latest --secret=CRON_SECRET --project=trooth-prod)
API=https://trooth-discipleship-api-dev.onlyblv.com
```

## 1. Tests

```bash
.venv/bin/python -m pytest tests/test_scoring_pipeline.py -q && .venv/bin/python -m pytest -q
```

## 2. Speed (SC-001)

Submit 10 Master assessments with `seed_data.py complete` (or a loop calling its submit step).
Record submit → `status=done` times from `/assessments/{id}/status` polling or
`scoring_completed_at - created_at`.
Expected: ≥ 9 of 10 under 45 s; `scores.scoring_version == "master_v3"`.

## 3. Consistency (SC-006)

For the 10 reports, check:
- apprentice, mentor and Premium all show the same Health Score, band and Biblical Knowledge %;
- every number in narrative fields appears in `scores.computed_facts`;
- the first assessment for a fresh account has no change-over-time language.

## 4. Premium instant (US4)

Immediately after `done`, `GET /assessments/{id}/my-full-report` returns `cached: true` in < 2 s.
For a non-premium assessment, switch the account to Premium (`seed/set_plan.sh premium`) and fire
two requests at once: one generation in the logs, both get the report (or one gets
`status: generating`), no 500.

## 5. Outage and retry (US1, SC-004)

1. `gcloud run services update trooth-backend-dev --region us-east4 --update-env-vars LLM_MODEL=gemini-does-not-exist`
2. Submit an assessment: status stays `processing`; Cloud Tasks shows retries
   (`gcloud tasks list --queue assessment-scoring-dev --location us-east4`).
3. Within 30 min, restore: `--remove-env-vars LLM_MODEL`. The next retry completes → `done` with
   full content, no user action.
4. Exhaustion: repeat step 1 and wait > 1 h (or temporarily lower `maxRetryDuration` on the dev
   queue to 120 s with `gcloud tasks queues update`): status `failed` with `reason`; the
   "Scoring fallback" or "AI generation failures" alert fires; no mentor email sent.
5. Re-queue: `curl -X POST -H "X-Cron-Secret: $KEY" -H 'Content-Type: application/json' -d '{"ids":["<id>"]}' $API/admin/assessments/requeue`
   → `done`. Restore the queue settings with `setup_queue.sh dev`.

## 6. Restart mid-scoring (SC-004)

Submit, then immediately deploy a new dev revision (or `gcloud run services update … --update-labels bump=$(date +%s)`).
The in-flight task fails or loses its instance; Cloud Tasks retries; status ends `done`.

## 7. Backfill (FR-006)

`POST /admin/assessments/requeue` with `{"since":"2026-10-09T00:00:00Z","until":"2026-10-11T00:00:00Z","include_done_fallback":true}`
on dev re-scores outage-emptied reports.

## 8. Released app

The current store/TestFlight app shows reports for `done` and doesn't crash on `failed`.

## 9. Prod

After merge: `/deploy-prod`, `scripts/scoring/setup_queue.sh prod`, steps 2 (3 submissions) and 8,
then run the backfill for prod's 2026-10-10 window if any empty reports exist.

## 10. Invariant checks (SC-002, SC-003)

Run against the dev database (read-only), and later prod:

```sql
-- SC-002: no "done" Master report with empty AI content (expect 0 rows)
SELECT id FROM assessments
 WHERE status = 'done' AND category = 'master_trooth'
   AND COALESCE(json_array_length(mentor_report_v2::json -> 'insights'), 0) = 0
   AND scores::jsonb ->> 'scoring_version' = 'master_v3';
-- SC-003: nothing processing for more than 2 hours (expect 0 rows)
SELECT id, scoring_queued_at FROM assessments
 WHERE status = 'processing' AND scoring_queued_at < now() - interval '2 hours';
```
