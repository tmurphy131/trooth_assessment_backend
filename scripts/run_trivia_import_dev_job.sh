#!/usr/bin/env bash
# One-shot Cloud Run Job to import all approved trivia question drafts into the dev DB.
#
# Usage:
#   ./scripts/run_trivia_import_dev_job.sh [--dry-run]
#
# Prerequisites:
#   - gcloud auth login && gcloud config set project trooth-prod
#   - All question_drafts/*.json files have "approved": true on desired questions
#   - The trivia tables migration has already run against app-pg-dev
set -euo pipefail

PROJECT="trooth-prod"
REGION="us-east4"
IMAGE="gcr.io/${PROJECT}/trooth-backend-dev:latest"
CLOUDSQL_INSTANCE="${PROJECT}:${REGION}:app-pg-dev"
DB_SECRET="DB_URL_DEV"
JOB_NAME="import-trivia-questions-dev"
DRY_RUN=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) DRY_RUN=1; shift;;
    -h|--help)
      echo "Usage: $0 [--dry-run]"
      exit 0;;
    *) echo "Unknown arg: $1"; exit 1;;
  esac
done

run() {
  if [[ $DRY_RUN -eq 1 ]]; then
    echo "[dry-run] $*"
  else
    "$@"
  fi
}

# The question draft JSON files are baked into the image via COPY . .
# They live at /app/scripts/question_drafts/ inside the container.
# No GCS upload/download step needed.
ENTRYPOINT_CMD="/opt/venv/bin/python scripts/import_trivia_questions.py --file scripts/question_drafts/questions_draft_*.json"

echo "Job entrypoint:"
echo "  ${ENTRYPOINT_CMD}"
echo ""

# ── 1. Delete existing job if present ────────────────────────────────────────
if gcloud run jobs describe "$JOB_NAME" --region "$REGION" --project "$PROJECT" >/dev/null 2>&1; then
  echo "Deleting existing job '${JOB_NAME}'..."
  run gcloud run jobs delete "$JOB_NAME" --region "$REGION" --project "$PROJECT" --quiet
fi

# ── 2. Create the Cloud Run Job ───────────────────────────────────────────────
echo "Creating Cloud Run Job: ${JOB_NAME}"
run gcloud run jobs create "$JOB_NAME" \
  --project "$PROJECT" \
  --region "$REGION" \
  --image "$IMAGE" \
  --set-cloudsql-instances "$CLOUDSQL_INSTANCE" \
  --set-secrets "DATABASE_URL=${DB_SECRET}:latest" \
  --command "/bin/sh" \
  --args "-c","${ENTRYPOINT_CMD}" \
  --max-retries 0 \
  --memory 512Mi \
  --task-timeout 600

# ── 3. Execute ────────────────────────────────────────────────────────────────
echo "Executing job (this may take a minute)..."
run gcloud run jobs execute "$JOB_NAME" \
  --project "$PROJECT" \
  --region "$REGION" \
  --wait

echo ""
echo "Done. View logs:"
echo "  gcloud logging read 'resource.type=cloud_run_job AND resource.labels.job_name=${JOB_NAME}' --project=${PROJECT} --limit=200 --format='value(textPayload)'"
