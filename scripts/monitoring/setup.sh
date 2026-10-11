#!/bin/bash
# Create or update all monitoring for an environment. See scripts/monitoring/README.md.
#   scripts/monitoring/setup.sh dev|prod [--dry-run]
set -euo pipefail
exec python3 -I "$(dirname "$0")/setup.py" "$@"
