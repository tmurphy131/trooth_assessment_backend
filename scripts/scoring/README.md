# Durable assessment scoring

Spec: [specs/004-reliable-ai-reports](../../specs/004-reliable-ai-reports/spec.md).

```bash
scripts/scoring/setup_queue.sh dev     # or prod; safe to rerun
```

Creates or updates:
- Cloud Tasks queue `assessment-scoring-<env>` (us-east4): retries for 1 hour with backoff from 10 s to 10 min;
- IAM: `trooth-run-sa` can enqueue on the queue and act as itself (to mint the task's OIDC token);
- Cloud Scheduler `scoring-sweep-<env>`: every 15 minutes, POST `/scheduled/scoring-sweep`. The sweep fails assessments that outlived their retry window and re-queues ones that never ran, plus failed ones every 6 hours.

Re-queue by hand (admin or scheduler secret):

```bash
curl -X POST -H "X-Cron-Secret: $(gcloud secrets versions access latest --secret=CRON_SECRET --project=trooth-prod)" \
  -H 'Content-Type: application/json' -d '{"ids":["<assessment id>"]}' \
  https://trooth-discipleship-api.onlyblv.com/admin/assessments/requeue
```

Use `{"since": "...", "until": "...", "include_done_fallback": true}` to backfill reports emptied by an outage.

Watch the queue: `gcloud tasks list --queue assessment-scoring-dev --location us-east4`.
