#!/usr/bin/env bash
set -euo pipefail

# Config
SECRETS_DIR="/secrets"
FIREBASE_FILE="$SECRETS_DIR/firebase_key.json"
SECRET_NAME="FIREBASE_CERT_JSON"   # secret name in Secret Manager
# Respect the runtime provided PORT (Cloud Run sets PORT=8080). Default to 8000 for local/dev.
PORT="${PORT:-8000}"
UVICORN_CMD="uvicorn app.main:app --host 0.0.0.0 --port $PORT"

mkdir -p "$SECRETS_DIR"

# Try to get project id and access token from metadata server (works on Cloud Run / GCE / GKE)
PROJECT_ID=""
ACCESS_TOKEN=""
if curl -s -H "Metadata-Flavor: Google" "http://metadata.google.internal/computeMetadata/v1/project/project-id" >/dev/null 2>&1; then
  PROJECT_ID=$(curl -s -H "Metadata-Flavor: Google" "http://metadata.google.internal/computeMetadata/v1/project/project-id")
  ACCESS_TOKEN=$(curl -s -H "Metadata-Flavor: Google" "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token" \
    | python -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))")
fi

if [ -z "$PROJECT_ID" ] || [ -z "$ACCESS_TOKEN" ]; then
  echo "Unable to get project id or access token from metadata server."
  echo "If you're running locally, set FIREBASE_CERT_PATH or provide ACCESS_TOKEN for testing."
else
  # Fetch latest version of the secret, decode base64 payload and write to file.
  # Use a small tempfile + heredoc Python script to avoid quoting/newline issues
  TMP_JSON="$(mktemp)"
  curl -s -H "Authorization: Bearer $ACCESS_TOKEN" \
    "https://secretmanager.googleapis.com/v1/projects/${PROJECT_ID}/secrets/${SECRET_NAME}/versions/latest:access" \
    -o "$TMP_JSON"

  python - "$TMP_JSON" > "$FIREBASE_FILE" <<'PY'
import sys, json, base64
with open(sys.argv[1], 'r') as fh:
    obj = json.load(fh)
data = obj.get('payload', {}).get('data')
if not data:
    raise SystemExit('no secret payload')
print(base64.b64decode(data).decode('utf-8'), end='')
PY

  rm -f "$TMP_JSON"
  chmod 600 "$FIREBASE_FILE"
  export FIREBASE_CERT_PATH="$FIREBASE_FILE"
fi

# Exec the app
exec $UVICORN_CMD
