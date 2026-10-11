"""Create or update all monitoring for one environment (specs/003-integration-health-alerts).

    scripts/monitoring/setup.sh dev|prod [--dry-run]

Idempotent: every resource is looked up by name first and updated in place, so rerunning
creates nothing new. Uses gcloud for auth, Secret Manager and Cloud Scheduler, and the Cloud
Logging / Monitoring REST APIs for log metrics, uptime checks, the email channel and alert
policies. Never prints the scheduler secret.
"""
import json
import os
import ssl
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

PROJECT = "trooth-prod"
REGION = "us-east4"
ALERT_EMAIL = "admin@onlyblv.com"
RENOTIFY = "1800s"
AUTO_CLOSE = "1800s"

ENVS = {
    "dev": {"service": "trooth-backend-dev", "api": "https://trooth-discipleship-api-dev.onlyblv.com",
            "prefix": "[dev]", "website": False},
    "prod": {"service": "trooth-backend", "api": "https://trooth-discipleship-api.onlyblv.com",
             "prefix": "[prod]", "website": True},
}

MONITORING = f"https://monitoring.googleapis.com/v3/projects/{PROJECT}"
LOGGING = f"https://logging.googleapis.com/v2/projects/{PROJECT}"
DRY_RUN = "--dry-run" in sys.argv
# python.org builds of Python ship without CA certificates; fall back to the macOS bundle.
_SSL = ssl.create_default_context(cafile="/etc/ssl/cert.pem") if os.path.exists("/etc/ssl/cert.pem") else None


def gcloud(*args, secret=False):
    out = subprocess.run(["gcloud", *args, f"--project={PROJECT}"], capture_output=True, text=True)
    if out.returncode != 0:
        msg = "gcloud command failed" if secret else f"gcloud {' '.join(args[:3])} failed: {out.stderr.strip()[:400]}"
        raise SystemExit(msg)
    return out.stdout.strip()


_TOKEN = None


def api(method, url, body=None):
    global _TOKEN
    _TOKEN = _TOKEN or gcloud("auth", "print-access-token")
    req = urllib.request.Request(url, method=method, data=json.dumps(body).encode() if body is not None else None)
    req.add_header("Authorization", f"Bearer {_TOKEN}")
    req.add_header("Content-Type", "application/json")
    req.add_header("x-goog-user-project", PROJECT)
    try:
        with urllib.request.urlopen(req, timeout=60, context=_SSL) as r:
            text = r.read().decode()
            return json.loads(text) if text else {}
    except urllib.error.HTTPError as e:
        if e.code == 404 and method == "GET":
            return None
        raise SystemExit(f"{method} {url} -> {e.code}: {e.read().decode()[:500]}")


def report(kind, name, action):
    print(f"  {action:8} {kind}: {name}")


def list_all(url, key):
    items, page = [], ""
    while True:
        sep = "&" if "?" in url else "?"
        data = api("GET", f"{url}{sep}pageSize=500" + (f"&pageToken={page}" if page else "")) or {}
        items += data.get(key, [])
        page = data.get("nextPageToken")
        if not page:
            return items


# ---------------------------------------------------------------------------

def ensure_channel():
    channels = list_all(f"{MONITORING}/notificationChannels", "notificationChannels")
    for ch in channels:
        if ch.get("type") == "email" and ch.get("labels", {}).get("email_address") == ALERT_EMAIL:
            report("channel", ALERT_EMAIL, "exists")
            return ch["name"]
    if DRY_RUN:
        report("channel", ALERT_EMAIL, "create?")
        return "projects/-/notificationChannels/DRY_RUN"
    ch = api("POST", f"{MONITORING}/notificationChannels",
             {"type": "email", "displayName": ALERT_EMAIL, "labels": {"email_address": ALERT_EMAIL}})
    report("channel", ALERT_EMAIL, "created")
    return ch["name"]


def ensure_log_metric(name, filter_, labels=None):
    body = {"name": name, "filter": filter_, "description": "specs/003-integration-health-alerts",
            "metricDescriptor": {"metricKind": "DELTA", "valueType": "INT64",
                                 "labels": [{"key": k, "valueType": "STRING"} for k in (labels or {})]}}
    if labels:
        body["labelExtractors"] = labels
    current = api("GET", f"{LOGGING}/metrics/{name}")
    if DRY_RUN:
        report("metric", name, "update?" if current else "create?")
    elif current:
        api("PUT", f"{LOGGING}/metrics/{name}", body)
        report("metric", name, "updated")
    else:
        api("POST", f"{LOGGING}/metrics", body)
        report("metric", name, "created")
    return f"logging.googleapis.com/user/{name}"


def ensure_uptime(display_name, host, path):
    for cfg in list_all(f"{MONITORING}/uptimeCheckConfigs", "uptimeCheckConfigs"):
        if cfg.get("displayName") == display_name:
            report("uptime", display_name, "exists")
            return cfg["name"].rsplit("/", 1)[-1]
    if DRY_RUN:
        report("uptime", display_name, "create?")
        return "DRY_RUN"
    cfg = api("POST", f"{MONITORING}/uptimeCheckConfigs", {
        "displayName": display_name,
        "monitoredResource": {"type": "uptime_url", "labels": {"project_id": PROJECT, "host": host}},
        "httpCheck": {"path": path, "port": 443, "useSsl": True, "validateSsl": True},
        "period": "60s", "timeout": "10s",
    })
    report("uptime", display_name, "created")
    return cfg["name"].rsplit("/", 1)[-1]


def _threshold(display, filter_, aligner, reducer, group_by, threshold, window, duration="0s"):
    return {"displayName": display, "conditionThreshold": {
        "filter": filter_,
        "aggregations": [{"alignmentPeriod": window, "perSeriesAligner": aligner,
                          "crossSeriesReducer": reducer, "groupByFields": group_by}],
        "comparison": "COMPARISON_GT", "thresholdValue": threshold,
        "duration": duration, "trigger": {"count": 1}}}


def ensure_policy(display_name, condition, channel, doc):
    body = {
        "displayName": display_name, "combiner": "OR", "enabled": True,
        "conditions": [condition],
        "notificationChannels": [channel],
        "documentation": {"content": doc, "mimeType": "text/markdown"},
        "alertStrategy": {"autoClose": AUTO_CLOSE,
                          "notificationChannelStrategy": [{"notificationChannelNames": [channel],
                                                           "renotifyInterval": RENOTIFY}]},
    }
    existing = [p for p in list_all(f"{MONITORING}/alertPolicies", "alertPolicies")
                if p.get("displayName") == display_name]
    if DRY_RUN:
        report("policy", display_name, "update?" if existing else "create?")
    elif existing:
        mask = "displayName,combiner,enabled,conditions,notificationChannels,documentation,alertStrategy"
        api("PATCH", f"https://monitoring.googleapis.com/v3/{existing[0]['name']}?updateMask={mask}", body)
        report("policy", display_name, "updated")
    else:
        api("POST", f"{MONITORING}/alertPolicies", body)
        report("policy", display_name, "created")


def ensure_scheduler(env, cfg):
    job = f"integrations-health-{env}"
    secret = gcloud("secrets", "versions", "access", "latest", "--secret=CRON_SECRET", secret=True)
    common = [f"--location={REGION}", "--schedule=*/15 * * * *", "--time-zone=UTC",
              f"--uri={cfg['api']}/health/integrations", "--http-method=GET", "--attempt-deadline=60s"]
    exists = subprocess.run(["gcloud", "scheduler", "jobs", "describe", job, f"--location={REGION}",
                             f"--project={PROJECT}"], capture_output=True).returncode == 0
    if DRY_RUN:
        report("scheduler", job, "update?" if exists else "create?")
        return
    if exists:
        gcloud("scheduler", "jobs", "update", "http", job, *common,
               f"--update-headers=X-Cron-Secret={secret}", secret=True)
        report("scheduler", job, "updated")
    else:
        gcloud("scheduler", "jobs", "create", "http", job, *common,
               f"--headers=X-Cron-Secret={secret}", secret=True)
        report("scheduler", job, "created")


# ---------------------------------------------------------------------------

def main():
    env = next((a for a in sys.argv[1:] if not a.startswith("--")), "")
    if env not in ENVS:
        raise SystemExit(__doc__)
    cfg = ENVS[env]
    svc = cfg["service"]
    prefix = cfg["prefix"]
    on_service = f'resource.type="cloud_run_revision" AND resource.labels.service_name="{svc}"'
    print(f"Monitoring for {env} ({svc}){' [dry run]' if DRY_RUN else ''}")

    channel = ensure_channel()

    # US1: integration down
    down = ensure_log_metric(f"integration_down_{env}", f'{on_service} AND textPayload:"integration_down"',
                             {"integration": 'REGEXP_EXTRACT(textPayload, "integration=(\\\\S+)")'})
    ensure_scheduler(env, cfg)
    ensure_policy(f"{prefix} Integration down", _threshold(
        "integration_down logged", f'metric.type="{down}" AND resource.type="cloud_run_revision"',
        "ALIGN_SUM", "REDUCE_SUM", ["metric.label.integration"], 0, "300s"), channel,
        f"An integration failed its live check in **{env}**. The alert names the integration.\n\n"
        f"Check: `curl -H 'X-Cron-Secret: …' {cfg['api']}/health/integrations`")

    # US2: availability
    api_host = cfg["api"].removeprefix("https://")
    checks = [(f"{prefix} API /health", api_host, "/health", f"{prefix} API down")]
    if cfg["website"]:
        checks.append(("onlyblv.com website", "onlyblv.com", "/", "onlyblv.com down"))
    for display, host, path, policy in checks:
        check_id = ensure_uptime(display, host, path)
        ensure_policy(policy, _threshold(
            f"{display} failing",
            f'metric.type="monitoring.googleapis.com/uptime_check/check_passed" AND '
            f'metric.label.check_id="{check_id}" AND resource.type="uptime_url"',
            "ALIGN_NEXT_OLDER", "REDUCE_COUNT_FALSE", ["resource.label.host"], 1, "60s", duration="300s"),
            channel, f"`https://{host}{path}` has failed uptime checks from multiple regions for 5 minutes.")

    # US3: real-traffic failures and 5xx
    traffic = [
        ("llm_provider_error", 'textPayload:"[llm] provider=" AND textPayload:"error="', "AI generation failures",
         "AI provider calls are failing for real requests."),
        ("scoring_fallback", 'textPayload:"Failed to build mentor_blob"', "Scoring fallback",
         "Assessments are being scored with the empty fallback report."),
        ("email_send_failed", 'textPayload:"[email]" AND (textPayload:"Failed send" OR textPayload:"Exception during send" OR textPayload:"Skipping send" OR textPayload:"No from_email" OR textPayload:"Failed to instantiate")',
         "Email send failures", "Transactional emails are failing to send."),
    ]
    for metric, filt, title, doc in traffic:
        mtype = ensure_log_metric(f"{metric}_{env}", f"{on_service} AND {filt}")
        ensure_policy(f"{prefix} {title}", _threshold(
            title, f'metric.type="{mtype}" AND resource.type="cloud_run_revision"',
            "ALIGN_SUM", "REDUCE_SUM", [], 0, "600s"), channel, f"{doc} Environment: **{env}**.")
    ensure_policy(f"{prefix} Server errors", _threshold(
        "5xx responses",
        f'metric.type="run.googleapis.com/request_count" AND resource.type="cloud_run_revision" AND '
        f'resource.label.service_name="{svc}" AND metric.label.response_code_class="5xx"',
        "ALIGN_SUM", "REDUCE_SUM", [], 5, "300s"), channel,
        f"More than 5 server errors in 5 minutes on **{env}** ({svc}).")
    print("Done.")


if __name__ == "__main__":
    main()
