# Quickstart: validate integration health checks and alerts

## Prerequisites

- `gcloud` authenticated to project `trooth-prod`; backend deployed to dev with this branch
  (`/deploy-dev`).
- Local: `.venv` for the backend.

```bash
KEY=$(gcloud secrets versions access latest --secret=CRON_SECRET --project=trooth-prod)
API=https://trooth-discipleship-api-dev.onlyblv.com
```

## 1. Tests

```bash
.venv/bin/python -m pytest tests/test_integration_health.py -q
.venv/bin/python -m pytest -q
```

Expected: all pass.

## 2. Endpoint on dev

```bash
curl -s -o /dev/null -w '%{http_code}\n' $API/health/integrations                      # 403
curl -s -H "X-Cron-Secret: $KEY" $API/health/integrations | python3 -m json.tool       # report
for p in health/health/detailed health/health/llm health/health/metrics; do
  curl -s -o /dev/null -w "$p %{http_code}\n" $API/$p                                  # 403 each
done
curl -s -o /dev/null -w '%{http_code}\n' $API/health                                    # 200
```

Expected: report lists all eight integrations; `shopify` is `not_configured` on dev;
`llm_fallback` is `skipped` (suppressed by the `HEALTHCHECK_SKIP` default while OpenAI has no
credit). Shape matches
[contracts/health-integrations.md](contracts/health-integrations.md).

## 3. Monitoring setup

```bash
scripts/monitoring/setup.sh dev     # first run creates everything
scripts/monitoring/setup.sh dev     # second run: "updated"/"exists", no duplicates
```

Check in Cloud Console → Monitoring → Alerting: `[dev]` policies, uptime checks and the
admin@onlyblv.com channel; Cloud Scheduler: `integrations-health-dev` every 15 minutes.

## 4. Kill-switch test (SC-001, SC-003)

1. Trigger the scheduled job now: `gcloud scheduler jobs run integrations-health-dev --location us-east4`.
2. Temporarily break one integration on dev (e.g. redeploy dev with `LLM_MODEL=does-not-exist`)
   and run the job again: expect an `integration_down ... integration=llm_primary` log line within
   a minute and an alert email **"[dev] Integration down"** within ~10 minutes.
3. Restore with `/deploy-dev`, run the job, and confirm the alert closes (recovery email).

## 5. Uptime and 5xx

- Uptime checks report green for both API `/health` URLs and `https://onlyblv.com/`.
- Optional: point a temporary uptime check at a 404 URL to see the alert open and close.

## 6. Prod

After merge to `main`: `/deploy-prod`, then `scripts/monitoring/setup.sh prod` and repeat steps 2
(with the prod API URL) and 4.1–4.2.
