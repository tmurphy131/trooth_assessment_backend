#!/usr/bin/env bash
# Helper script to run Alembic migrations inside the built container image.
# Usage examples:
#   Local (env DB): DATABASE_URL=postgresql+psycopg://... ./run_migrations.sh
#   Cloud Run Job:  set same env vars / secrets and use this as the command.
set -euo pipefail

echo "[migrate] Starting Alembic upgrade -> head"
# Ensure working directory is project root (where alembic.ini lives)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ -z "${DATABASE_URL:-}" ]; then
  echo "[migrate] ERROR: DATABASE_URL not set" >&2
  exit 1
fi

# Optional: acquire a PostgreSQL advisory lock to avoid concurrent migration runs.
if [[ "$DATABASE_URL" == postgresql* || "$DATABASE_URL" == postgres* ]]; then
  python - <<'PY'
import os, sys
from sqlalchemy import create_engine, text
url = os.environ['DATABASE_URL']
try:
    eng = create_engine(url, isolation_level='AUTOCOMMIT')
    with eng.begin() as conn:
        # Arbitrary lock key (two int32). Change if you need a different namespace.
        got = conn.execute(text('SELECT pg_try_advisory_lock(871234, 42)')).scalar()
        if not got:
            print('[migrate] Another migration process holds the lock; exiting.', file=sys.stderr)
            sys.exit(0)
        print('[migrate] Acquired advisory lock, running migrations...')
except Exception as e:
    print(f'[migrate] Could not acquire advisory lock (continuing anyway): {e}', file=sys.stderr)
PY
fi

# Run Alembic
python -m alembic upgrade 20260101_mentor_notes_updated

echo "[migrate] Completed Alembic upgrade"
