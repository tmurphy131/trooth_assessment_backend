#!/usr/bin/env bash
set -euo pipefail

# Create & run Cloud Run Job to seed Spiritual Gift Definitions.
# Requires: gcloud auth, project set, artifact image built & pushed.
# The job reuses the existing backend image and overrides command to run the seed script.

usage() {
  cat <<EOF
Usage: $0 \
  --image gcr.io/PROJECT/trooth-backend:latest \
  --region us-east4 \
  --version 1 \
  --json-file scripts/spiritual_gift_definitions_v1.json \
  [--replace] [--publish] [--job-name seed-spiritual-gifts-v1]

Environment (required):
  DATABASE_URL   Postgres URL (can be secret-mounted using --set-secrets when running job)
Optional env:
  SENDGRID_API_KEY (ignored here but inherited if present)

Examples:
  DATABASE_URL=postgresql://user:pw@host:5432/db \\
    $0 --image gcr.io/myproj/trooth-backend:latest --region us-east4 --version 1 \
       --json-file scripts/spiritual_gift_definitions_v1.json --publish

Dry run (show commands only):
  DRY_RUN=1 $0 --image gcr.io/myproj/trooth-backend:latest --region us-east4 --version 1 --json-file scripts/spiritual_gift_definitions_v1.json
EOF
}

IMAGE=""
REGION="us-east4"
VERSION=""
JSON_FILE=""
REPLACE_FLAG=""
PUBLISH_FLAG=""
JOB_NAME=""
CLOUDSQL_INSTANCE=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --image) IMAGE="$2"; shift 2;;
    --region) REGION="$2"; shift 2;;
    --version) VERSION="$2"; shift 2;;
    --json-file) JSON_FILE="$2"; shift 2;;
    --replace) REPLACE_FLAG="--replace"; shift;;
    --publish) PUBLISH_FLAG="--publish"; shift;;
    --job-name) JOB_NAME="$2"; shift 2;;
  --cloudsql) CLOUDSQL_INSTANCE="$2"; shift 2;;
    -h|--help) usage; exit 0;;
    *) echo "Unknown arg: $1"; usage; exit 1;;
  esac
done

if [[ -z "$IMAGE" || -z "$VERSION" || -z "$JSON_FILE" ]]; then
  echo "ERROR: --image, --version, --json-file required" >&2
  usage; exit 2
fi

if [[ ! -f "$JSON_FILE" ]]; then
  echo "ERROR: JSON file not found: $JSON_FILE" >&2; exit 3
fi

if [[ -z "${JOB_NAME}" ]]; then
  JOB_NAME="seed-spiritual-gifts-v${VERSION}"
fi

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "WARNING: DATABASE_URL not set in environment. The job must receive it via --set-env-vars or secret." >&2
fi

CREATE_CMD=(gcloud run jobs create "$JOB_NAME" \
  --image "$IMAGE" \
  --region "$REGION" \
  --command python \
  --args "scripts/seed_spiritual_gifts.py","--version","${VERSION}","--file","${JSON_FILE}" \
  --max-retries=1 \
  --memory=512Mi)

if [[ -n "$CLOUDSQL_INSTANCE" ]]; then
  CREATE_CMD+=(--set-cloudsql-instances "$CLOUDSQL_INSTANCE")
fi

if [[ -n "$REPLACE_FLAG" ]]; then
  CREATE_CMD+=(--args "--replace")
fi
if [[ -n "$PUBLISH_FLAG" ]]; then
  CREATE_CMD+=(--args "--publish")
fi

# Provide DATABASE_URL env inline if present
if [[ -n "${DATABASE_URL:-}" ]]; then
  CREATE_CMD+=(--set-env-vars "DATABASE_URL=${DATABASE_URL}")
fi

RUN_CMD=(gcloud run jobs execute "$JOB_NAME" --region "$REGION")

if [[ -n "${DRY_RUN:-}" ]]; then
  echo "Create command: ${CREATE_CMD[*]}"; echo "Run command: ${RUN_CMD[*]}"; exit 0
fi

# If job exists, delete & recreate for idempotency
if gcloud run jobs describe "$JOB_NAME" --region "$REGION" >/dev/null 2>&1; then
  echo "Job exists. Deleting so we can recreate with updated args..."
  gcloud run jobs delete "$JOB_NAME" --quiet --region "$REGION"
fi

echo "Creating job: $JOB_NAME"
"${CREATE_CMD[@]}"

echo "Executing job: $JOB_NAME"
"${RUN_CMD[@]}"

echo "Done. View logs with: gcloud logs read --region $REGION run.googleapis.com/job.execution.job_name=$JOB_NAME --limit=100"
