#!/usr/bin/env bash
# Run the trivia question import as a Cloud Run Job against the dev database.
#
# Prerequisites:
#   1. Generate and review the draft JSON files locally:
#        python scripts/generate_trivia_questions.py --category old_testament --difficulty beginner --count 84
#        # ... repeat for all 12 buckets, then edit files and set "approved": true
#
#   2. Upload the approved draft files to GCS (the job reads them from a mounted bucket
#      or a baked-in path). The simplest approach is to embed the file as a Cloud Run
#      Job execution env-var pointing to GCS, but since our import script reads a local
#      file path, the easiest pattern is to upload the file to GCS and pass a
#      pre-signed URL — OR, more practically for one-off imports, run the import
#      script locally with Cloud SQL proxy (see below).
#
# ─── OPTION A: Run locally with Cloud SQL proxy (recommended for one-off imports) ──
#
#   1. Start the proxy:
#        ./scripts/start_cloud_sql_proxy.sh
#        # or: cloud-sql-proxy trooth-prod:us-east4:app-pg-dev --port 5433 &
#
#   2. Run the import pointing at the local proxy:
#        DATABASE_URL="postgresql://USER:PASSWORD@127.0.0.1:5433/DB_NAME" \
#          python scripts/import_trivia_questions.py \
#            --file questions_draft_*.json
#
# ─── OPTION B: Cloud Run Job (for repeatable / CI-triggered imports) ─────────────
#
# Usage:
#   ./scripts/run_import_trivia_questions_job.sh \
#     --file questions_draft_old_testament_beginner.json \
#     [--file questions_draft_new_testament_expert.json ...] \
#     [--job-name import-trivia-questions] \
#     [--dry-run]
#
# The script uploads the JSON file(s) to GCS, then creates and executes a Cloud Run
# Job that downloads the file(s) and runs import_trivia_questions.py.
#
# Requirements:
#   - gcloud auth login && gcloud config set project trooth-prod
#   - gsutil available (part of gcloud SDK)
#   - GCS bucket for staging files (set GCS_BUCKET env or use default below)
set -euo pipefail

PROJECT="trooth-prod"
REGION="us-east4"
IMAGE="gcr.io/${PROJECT}/trooth-backend-dev:latest"
CLOUDSQL_INSTANCE="${PROJECT}:${REGION}:app-pg-dev"
DB_SECRET="DB_URL_DEV"
GCS_BUCKET="${GCS_BUCKET:-${PROJECT}-job-staging}"
JOB_NAME="import-trivia-questions"
DRY_RUN=0
FILES=()

usage() {
  cat <<EOF
Usage: $0 --file DRAFT.json [--file DRAFT2.json ...] [--job-name NAME] [--dry-run]

Options:
  --file FILE       Draft JSON file to import (may be specified multiple times)
  --job-name NAME   Cloud Run Job name (default: import-trivia-questions)
  --dry-run         Print commands without executing
  -h, --help        Show this help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --file)     FILES+=("$2"); shift 2;;
    --job-name) JOB_NAME="$2"; shift 2;;
    --dry-run)  DRY_RUN=1; shift;;
    -h|--help)  usage; exit 0;;
    *)          echo "Unknown arg: $1"; usage; exit 1;;
  esac
done

if [[ ${#FILES[@]} -eq 0 ]]; then
  echo "ERROR: at least one --file is required" >&2
  usage; exit 2
fi

run() {
  if [[ $DRY_RUN -eq 1 ]]; then
    echo "[dry-run] $*"
  else
    "$@"
  fi
}

# ── 1. Upload draft files to GCS ────────────────────────────────────────────
GCS_PREFIX="gs://${GCS_BUCKET}/trivia-import/$(date +%Y%m%d-%H%M%S)"
ARGS_FOR_JOB=()

echo "Uploading draft files to GCS..."
for f in "${FILES[@]}"; do
  if [[ ! -f "$f" ]]; then
    echo "ERROR: file not found: $f" >&2; exit 3
  fi
  BASENAME=$(basename "$f")
  GCS_PATH="${GCS_PREFIX}/${BASENAME}"
  run gsutil cp "$f" "$GCS_PATH"
  # Job will download each file to /tmp/
  ARGS_FOR_JOB+=("/tmp/${BASENAME}")
  echo "  Uploaded $f → $GCS_PATH"
done

# Build the shell command that the job will run:
#   gsutil cp gs://... /tmp/file.json && ... && python scripts/import_trivia_questions.py --file /tmp/*.json
DOWNLOAD_CMDS=""
for f in "${FILES[@]}"; do
  BASENAME=$(basename "$f")
  GCS_PATH="${GCS_PREFIX}/${BASENAME}"
  DOWNLOAD_CMDS+="gsutil cp '${GCS_PATH}' '/tmp/${BASENAME}' && "
done

FILE_ARGS=$(printf "'/tmp/%s' " "${FILES[@]/#*\//}")
ENTRYPOINT_CMD="${DOWNLOAD_CMDS}python scripts/import_trivia_questions.py --file ${FILE_ARGS}"

echo ""
echo "Job entrypoint command:"
echo "  $ENTRYPOINT_CMD"
echo ""

# ── 2. Delete existing job if it exists ─────────────────────────────────────
if gcloud run jobs describe "$JOB_NAME" --region "$REGION" --project "$PROJECT" >/dev/null 2>&1; then
  echo "Deleting existing job '$JOB_NAME'..."
  run gcloud run jobs delete "$JOB_NAME" --region "$REGION" --project "$PROJECT" --quiet
fi

# ── 3. Create Cloud Run Job ──────────────────────────────────────────────────
echo "Creating Cloud Run Job: $JOB_NAME"
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

# ── 4. Execute ───────────────────────────────────────────────────────────────
echo "Executing job..."
run gcloud run jobs execute "$JOB_NAME" \
  --project "$PROJECT" \
  --region "$REGION" \
  --wait

echo ""
echo "Done. View logs:"
echo "  gcloud logging read 'resource.type=cloud_run_job AND resource.labels.job_name=${JOB_NAME}' --project=${PROJECT} --limit=200 --format='value(textPayload)'"
