#!/bin/bash
# Upload site_files/ paths to onlyblv.com (Namecheap cPanel) through the cPanel API.
#
#   scripts/site/deploy.sh [--dry-run] <path>...     # paths relative to site_files/, files or folders
#   scripts/site/deploy.sh index.html guides.html guides/armory
#
# Credentials come from ~/.config/onlyblv/cpanel.env (CPANEL_HOST, CPANEL_USER, CPANEL_TOKEN; chmod 600).
# Every live file that would be overwritten is first downloaded to ~/.cache/onlyblv/site-backups/<timestamp>/.
# Folders are created as needed; nothing on the server is ever deleted.
set -euo pipefail

SITE_DIR="$(cd "$(dirname "$0")/../../site_files" && pwd)"
ENV_FILE="$HOME/.config/onlyblv/cpanel.env"
SITE_URL="https://onlyblv.com"

dry_run=false
if [[ "${1:-}" == "--dry-run" ]]; then dry_run=true; shift; fi
if [[ $# -eq 0 ]]; then
  sed -n '2,9p' "$0" | sed 's/^# \{0,1\}//'
  exit 2
fi

# Expand arguments into a sorted list of files (relative to site_files/), skipping dotfiles.
files=()
for arg in "$@"; do
  arg="${arg#site_files/}"; arg="${arg%/}"
  if [[ -d "$SITE_DIR/$arg" ]]; then
    while IFS= read -r f; do files+=("${f#"$SITE_DIR"/}"); done \
      < <(find "$SITE_DIR/$arg" -type f ! -name '.*' | sort)
  elif [[ -f "$SITE_DIR/$arg" ]]; then
    files+=("$arg")
  else
    echo "Not found in site_files/: $arg" >&2; exit 1
  fi
done

echo "Uploading ${#files[@]} file(s) to public_html:"
printf '  %s\n' "${files[@]}"
if $dry_run; then echo "(dry run, nothing uploaded)"; exit 0; fi

set -a; . "$ENV_FILE"; set +a
AUTH="Authorization: cpanel $CPANEL_USER:$CPANEL_TOKEN"
API="https://$CPANEL_HOST:2083"

# 1. Back up live copies of anything we're about to overwrite.
backup="$HOME/.cache/onlyblv/site-backups/$(date +%Y%m%d-%H%M%S)"
saved=0
for f in "${files[@]}"; do
  if [[ "$(curl -s -o /dev/null -w '%{http_code}' "$SITE_URL/$f")" == "200" ]]; then
    mkdir -p "$backup/$(dirname "$f")"
    curl -s -o "$backup/$f" "$SITE_URL/$f"
    saved=$((saved + 1))
  fi
done
echo "Backed up $saved live file(s) to $backup"

# 2. Create every folder level we need (mkdir on an existing folder is a harmless error).
dirs=$(for f in "${files[@]}"; do d=$(dirname "$f"); while [[ "$d" != "." ]]; do echo "$d"; d=$(dirname "$d"); done; done | sort -u)
for d in $dirs; do
  parent="public_html"; [[ "$(dirname "$d")" != "." ]] && parent="public_html/$(dirname "$d")"
  curl -sS -H "$AUTH" "$API/json-api/cpanel?cpanel_jsonapi_apiversion=2&cpanel_jsonapi_module=Fileman&cpanel_jsonapi_func=mkdir&path=$parent&name=$(basename "$d")" >/dev/null
done

# 3. Upload, one request per destination folder.
status=0
for d in $(for f in "${files[@]}"; do dirname "$f"; done | sort -u); do
  args=(); i=1
  for f in "${files[@]}"; do
    if [[ "$(dirname "$f")" == "$d" ]]; then args+=(-F "file-$i=@$SITE_DIR/$f"); i=$((i + 1)); fi
  done
  target="public_html"; [[ "$d" != "." ]] && target="public_html/$d"
  curl -sS -H "$AUTH" -F "dir=$target" -F "overwrite=1" "${args[@]}" "$API/execute/Fileman/upload_files" \
    | python3 -c '
import sys, json
d = json.load(sys.stdin)
ok = d.get("status") == 1
count = (d.get("data") or {}).get("succeeded")
print("  %s: %s" % (sys.argv[1], "%s uploaded" % count if ok else "FAILED %s" % d.get("errors")))
sys.exit(0 if ok else 1)' "$target" || status=1
done
exit $status
