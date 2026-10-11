#!/bin/bash
# Create or update the durable scoring queue, its IAM and the sweep job (specs/004-reliable-ai-reports).
#   scripts/scoring/setup_queue.sh dev|prod
# Idempotent. Never prints CRON_SECRET.
set -euo pipefail
ENV_NAME="${1:-}"
PROJECT=trooth-prod
REGION=us-east4
SA=trooth-run-sa@trooth-prod.iam.gserviceaccount.com
case "$ENV_NAME" in
  dev)  QUEUE=assessment-scoring-dev;  API=https://trooth-discipleship-api-dev.onlyblv.com ;;
  prod) QUEUE=assessment-scoring-prod; API=https://trooth-discipleship-api.onlyblv.com ;;
  *) sed -n '2,4p' "$0" | sed 's/^# \{0,1\}//'; exit 2 ;;
esac

RETRY=(--max-attempts=-1 --max-retry-duration=3600s --min-backoff=10s --max-backoff=600s --max-doublings=5)
if gcloud tasks queues describe "$QUEUE" --location="$REGION" --project="$PROJECT" >/dev/null 2>&1; then
  gcloud tasks queues update "$QUEUE" --location="$REGION" --project="$PROJECT" "${RETRY[@]}" --quiet >/dev/null
  echo "  updated  queue: $QUEUE"
else
  gcloud tasks queues create "$QUEUE" --location="$REGION" --project="$PROJECT" "${RETRY[@]}" --quiet >/dev/null
  echo "  created  queue: $QUEUE"
fi

# The run service account enqueues tasks and mints the OIDC token the task carries
gcloud tasks queues add-iam-policy-binding "$QUEUE" --location="$REGION" --project="$PROJECT" \
  --member="serviceAccount:$SA" --role=roles/cloudtasks.enqueuer --quiet >/dev/null
echo "  ensured  iam: cloudtasks.enqueuer on $QUEUE"
gcloud iam service-accounts add-iam-policy-binding "$SA" --project="$PROJECT" \
  --member="serviceAccount:$SA" --role=roles/iam.serviceAccountUser --quiet >/dev/null
echo "  ensured  iam: iam.serviceAccountUser on $SA (self)"

JOB="scoring-sweep-$ENV_NAME"
SECRET=$(gcloud secrets versions access latest --secret=CRON_SECRET --project="$PROJECT")
COMMON=(--location="$REGION" --project="$PROJECT" --schedule="*/15 * * * *" --time-zone=UTC
        --uri="$API/scheduled/scoring-sweep" --http-method=POST --attempt-deadline=120s)
if gcloud scheduler jobs describe "$JOB" --location="$REGION" --project="$PROJECT" >/dev/null 2>&1; then
  gcloud scheduler jobs update http "$JOB" "${COMMON[@]}" --update-headers="X-Cron-Secret=$SECRET" --quiet >/dev/null
  echo "  updated  scheduler: $JOB"
else
  gcloud scheduler jobs create http "$JOB" "${COMMON[@]}" --headers="X-Cron-Secret=$SECRET" --quiet >/dev/null
  echo "  created  scheduler: $JOB"
fi
unset SECRET
echo "Done."
