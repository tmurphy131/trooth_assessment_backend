#!/usr/bin/env bash
# Start Cloud SQL Auth Proxy forwarding a Cloud SQL instance to localhost TCP.
# Usage:
#   ./start_cloud_sql_proxy.sh /path/to/key.json trooth-prod:us-east4:app-pg 5432
# or set env vars:
#   CLOUDSQL_KEY=/path/to/key.json CLOUDSQL_INSTANCE=project:region:instance PORT=5432 ./start_cloud_sql_proxy.sh

set -euo pipefail

KEY=${1:-${CLOUDSQL_KEY:-}}
INSTANCE=${2:-${CLOUDSQL_INSTANCE:-}}
PORT=${3:-${PORT:-5432}}

if [ -z "$KEY" ] || [ -z "$INSTANCE" ]; then
  echo "Usage: $0 /path/to/key.json project:region:instance [port]"
  exit 2
fi

PROXY_BIN=${CLOUD_SQL_PROXY_BIN:-cloud-sql-proxy}
LOGFILE=${CLOUD_SQL_PROXY_LOG:-/tmp/csql-proxy.log}

echo "Starting Cloud SQL Auth Proxy for instance $INSTANCE -> tcp:127.0.0.1:$PORT"
echo "Logs: $LOGFILE"

mkdir -p "$(dirname "$LOGFILE")"

# Launch in background
"$PROXY_BIN" --credentials-file="$KEY" -instances="$INSTANCE"=tcp:127.0.0.1:$PORT >"$LOGFILE" 2>&1 &
echo $! > /tmp/csql-proxy.pid
sleep 1
if ps -p $(cat /tmp/csql-proxy.pid) > /dev/null 2>&1; then
  echo "Proxy started, pid=$(cat /tmp/csql-proxy.pid)"
  echo "To stop: kill "+$(cat /tmp/csql-proxy.pid)
else
  echo "Proxy failed to start; see $LOGFILE"
  tail -n 200 "$LOGFILE"
  exit 1
fi

echo "Set environment for backend to connect via TCP:"
echo "  export DATABASE_URL=postgresql://<DB_USER>:<DB_PASS>@127.0.0.1:$PORT/<DB_NAME>"
echo "Or add to .env in backend: DATABASE_URL=postgresql://trooth:trooth@127.0.0.1:$PORT/trooth_db"
