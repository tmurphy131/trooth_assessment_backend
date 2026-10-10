#!/bin/bash
# Switch the two guide test accounts between free and Premium on the DEV database.
#
#   scripts/site/guide_capture/seed/set_plan.sh premium   # mentor_premium / apprentice_premium for 30 days
#   scripts/site/guide_capture/seed/set_plan.sh free
#
# The dev admin endpoint (/subscriptions/admin/set-tier) only changes the calling admin's own tier,
# so this goes through Cloud SQL Proxy with the DB_URL_DEV secret. Only rows whose email is
# guide.mentor@example.com or guide.apprentice@example.com are touched. Needs gcloud auth,
# cloud-sql-proxy and psql.
set -euo pipefail
plan="${1:-}"
[[ "$plan" == "premium" || "$plan" == "free" ]] || { sed -n '2,6p' "$0" | sed 's/^# \{0,1\}//'; exit 2; }

PORT=54329
INSTANCE="trooth-prod:us-east4:app-pg-dev"
URL=$(gcloud secrets versions access latest --secret=DB_URL_DEV --project=trooth-prod)
eval "$(python3 -I -c '
import sys, urllib.parse as u, shlex
p = u.urlparse(sys.argv[1].replace("postgresql+psycopg2://", "postgresql://"))
print("export PGUSER=%s PGPASSWORD=%s PGDATABASE=%s" % (shlex.quote(u.unquote(p.username or "")),
      shlex.quote(u.unquote(p.password or "")), shlex.quote(p.path.lstrip("/"))))' "$URL")"
unset URL

cloud-sql-proxy --port "$PORT" "$INSTANCE" > "${TMPDIR:-/tmp}/guide-csql-proxy.log" 2>&1 &
PROXY=$!
trap 'kill $PROXY 2>/dev/null' EXIT
for _ in $(seq 1 30); do nc -z 127.0.0.1 "$PORT" 2>/dev/null && break; sleep 1; done
export PGHOST=127.0.0.1 PGPORT=$PORT

if [[ "$plan" == "premium" ]]; then
  SET="subscription_tier = (CASE WHEN role::text = 'mentor' THEN 'mentor_premium' ELSE 'apprentice_premium' END)::text::subscriptiontier,
       subscription_platform = 'admin_granted', subscription_expires_at = now() + interval '30 days'"
else
  SET="subscription_tier = 'free', subscription_platform = NULL, subscription_expires_at = NULL"
fi

psql -v ON_ERROR_STOP=1 -X -q <<SQL
UPDATE users SET $SET WHERE email IN ('guide.mentor@example.com', 'guide.apprentice@example.com');
SELECT email, subscription_tier, subscription_platform, subscription_expires_at FROM users
 WHERE email IN ('guide.mentor@example.com', 'guide.apprentice@example.com') ORDER BY email;
SQL
