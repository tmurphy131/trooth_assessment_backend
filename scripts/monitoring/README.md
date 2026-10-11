# Monitoring and alerts

Monitoring for the Discipleship API is code. `setup.sh` creates or updates everything for one
environment and is safe to rerun: every resource is looked up by name and updated in place.
Spec: [specs/003-integration-health-alerts](../../specs/003-integration-health-alerts/spec.md).

```bash
scripts/monitoring/setup.sh dev --dry-run   # show what would change
scripts/monitoring/setup.sh dev
scripts/monitoring/setup.sh prod
```

Prerequisites: `gcloud` signed in with access to project `trooth-prod` (Monitoring, Logging,
Cloud Scheduler and Secret Manager), and the backend deployed with `GET /health/integrations`.
Alerts go to **admin@onlyblv.com**. After the first run, use the channel's "Send test
notification" in Cloud Console (Monitoring → Alerting → Edit notification channels) to confirm
delivery, and check the spam folder.

## What it creates (per environment)

| Resource | Name | What it does |
|---|---|---|
| Notification channel | `admin@onlyblv.com` (shared) | where every alert is sent |
| Cloud Scheduler job | `integrations-health-<env>` | calls `GET /health/integrations` every 15 minutes with `X-Cron-Secret` |
| Log metric | `integration_down_<env>` | counts `integration_down` lines, labeled by integration |
| Log metric | `llm_provider_error_<env>` | AI provider errors from real requests |
| Log metric | `scoring_fallback_<env>` | assessments scored with the empty fallback report |
| Log metric | `email_send_failed_<env>` | failed transactional email sends |
| Uptime check | `[<env>] API /health` (+ `onlyblv.com website` for prod) | outside availability checks every minute |
| Alert policy | `[<env>] Integration down` | any integration down at a scheduled check |
| Alert policy | `[<env>] API down` / `onlyblv.com down` | uptime failing from multiple regions for 5 minutes |
| Alert policy | `[<env>] AI generation failures`, `Scoring fallback`, `Email send failures` | real-traffic failures in a 10-minute window |
| Alert policy | `[<env>] Server errors` | more than 5 responses with status 5xx in 5 minutes |

Every policy re-notifies every 30 minutes while open and closes automatically 30 minutes after
recovery.

Filter check on 2026-10-10, against dev logs from the previous 7 days:
- `llm_provider_error`: 18 matches (the October 10 AI outage).
- `scoring_fallback`: 1 match.
- `email_send_failed`: 0 matches (no send failures that week).

## Day-to-day

- **What's down right now:** `curl -H "X-Cron-Secret: $(gcloud secrets versions access latest --secret=CRON_SECRET --project=trooth-prod)" https://trooth-discipleship-api.onlyblv.com/health/integrations`
- **Run the check now:** `gcloud scheduler jobs run integrations-health-prod --location us-east4`
- **Silence a policy:** Cloud Console → Monitoring → Alerting → policy → disable, or create a snooze.
- **Remove everything:** delete the policies, uptime checks and log metrics listed above, and the
  scheduler job.

## Rotating CRON_SECRET

1. Add a new version of the `CRON_SECRET` secret in Secret Manager.
2. Redeploy dev and prod. The deploy commands mount `CRON_SECRET:latest`.
3. Rerun `setup.sh dev` and `setup.sh prod` to refresh the scheduler header.
4. Update the other scheduler jobs that send `X-Cron-Secret`, such as daily trivia, campaigns and
   metrics reports, and re-enter the key on the status page.
