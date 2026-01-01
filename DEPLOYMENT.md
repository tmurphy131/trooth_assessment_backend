## Trooth backend — deployment notes

Purpose: a compact reference of deployment prerequisites, exact commands that worked for this project, and the troubleshooting steps we used when Cloud Run revisions failed to start.

Checklist
- Secrets needed in Secret Manager: DATABASE_URL, FIREBASE_CERT_JSON, SENDGRID_API_KEY, OPENAI_API_KEY (optional: REDIS_URL).
- Service account must have Secret Manager access (roles/secretmanager.secretAccessor) and appropriate Cloud SQL access if using a socket.
- Image must be built for linux/amd64 (Cloud Run managed expects linux/amd64).
- Entrypoint must not crash and the container must bind to the PORT environment variable (Cloud Run sets PORT=8080).

1) High level requirements
- GCP project with Cloud Run and Secret Manager enabled.
- Runtime service account (the one Cloud Run uses) with:
  - roles/secretmanager.secretAccessor on the secrets you create
  - any DB / Cloud SQL permissions required by `DATABASE_URL`
- A container image pushed to a container registry the Cloud Run service can access (gcr.io, us.gcr.io, or Artifact Registry).

2) Secrets (examples)
- DATABASE_URL — the full SQLAlchemy DB URL (for Cloud SQL you can use the socket-style URL).
- FIREBASE_CERT_JSON — the Firebase service account JSON (store whole JSON as the secret payload).
- SENDGRID_API_KEY, OPENAI_API_KEY — API keys used by the app.

3) Commands that worked in this repo (examples)

Create secrets (example using stdin):

```bash
# create a secret and populate it from stdin
printf "%s" "<your-secret-value>" | \
  gcloud secrets create SENDGRID_API_KEY --data-file=- --project=trooth-prod

# if a secret already exists, add a version instead
printf "%s" "<your-new-value>" | \
  gcloud secrets versions add OPENAI_API_KEY --data-file=- --project=trooth-prod

# create the Firebase JSON secret from a file
gcloud secrets create FIREBASE_CERT_JSON --data-file=/path/to/firebase_key.json --project=trooth-prod
```

Grant Cloud Run runtime service account access to secrets:

```bash
gcloud secrets add-iam-policy-binding FIREBASE_CERT_JSON \
  --member=serviceAccount:301248215198-compute@developer.gserviceaccount.com \
  --role=roles/secretmanager.secretAccessor --project=trooth-prod
```

Build & push an amd64 image (this is important on Apple Silicon):

```bash
cd /path/to/repo
docker buildx build --platform linux/amd64 \
  -t gcr.io/trooth-prod/trooth-backend:latest --push .
```

Deploy to Cloud Run mapping secrets and environment variables (the flags we used):

```bash
gcloud run deploy trooth-backend \
  --image=gcr.io/trooth-prod/trooth-backend:latest \
  --region=us-east4 --platform=managed --project=trooth-prod \
  --service-account=301248215198-compute@developer.gserviceaccount.com \
  --set-secrets=DATABASE_URL=DATABASE_URL:latest,\
              SENDGRID_API_KEY=SENDGRID_API_KEY:latest,\
              OPENAI_API_KEY=OPENAI_API_KEY:latest,\
              FIREBASE_CERT_JSON=FIREBASE_CERT_JSON:latest \
  --set-env-vars=EMAIL_FROM_ADDRESS=admin@onlyblv.com,ENV=development,APP_URL=https://trooth-discipleship-api.onlyblv.com \
  --allow-unauthenticated
```

4) Local smoke test (quick check before pushing)

Run the container locally with the firebase file mounted and a lightweight DB override:

```bash
docker build -t trooth-backend:local .
docker run -d --name trooth-smoke -p 8000:8000 \
  -v /path/to/firebase_key.json:/secrets/firebase_key.json:ro \
  -e FIREBASE_CERT_PATH=/secrets/firebase_key.json \
  -e ENV=test -e DATABASE_URL="sqlite+pysqlite:///:memory:" \
  trooth-backend:local

# verify
curl http://localhost:8000/health
```

5) Troubleshooting steps we used (and why)

- Cloud Run revision failing to start / not listening on PORT=8080
  - Inspect the service to find the failing revision:

```bash
gcloud run services describe trooth-backend --region=us-east4 --project=trooth-prod --format=json
```

  - Fetch logs for that revision (look for stderr and TCP probe messages):

```bash
gcloud logging read 'resource.type=cloud_run_revision AND resource.labels.service_name=trooth-backend AND resource.labels.revision_name=<REVISION_NAME>' --project=trooth-prod --limit=200 --format=json
```

  - Common causes we hit and fixes:
    - SyntaxError in `entrypoint.sh` caused by a fragile inline python -c one-liner.
      Fix: replace the one-liner with a small heredoc Python script that reads the downloaded JSON, decodes the base64 payload and writes it to the file. See `entrypoint.sh` in the repo.
    - Permission denied when writing `/secrets` inside the container. Fix: ensure the Dockerfile pre-creates `/secrets` and chowns it to the non-root runtime user before switching users.
    - Image architecture mismatch (arm/arm64 image on Apple Silicon). Fix: use `docker buildx build --platform linux/amd64` and push the multi-arch/amd64 image.
    - Missing Cloud Build permission when using `gcloud builds submit`. Fix: grant `roles/cloudbuild.builds.builder` to the user or build locally and push with Docker.

- If the app starts locally but fails in Cloud Run:
  - Check that the container binds to the PORT env var (Cloud Run sets PORT=8080). In the repo we updated `entrypoint.sh` to use ${PORT:-8000} so it works locally and in Cloud Run.
  - Ensure the runtime service account has the IAM permissions for any resource the app accesses at startup (Secret Manager, Cloud SQL, etc.).

6) Useful log messages and what they mean
- "SyntaxError: invalid syntax" in Cloud Run stderr — indicates a shell-embedded python invocation had quoting/newline issues; search for python -c in `entrypoint.sh`.
- "mkdir: cannot create directory '/secrets': Permission denied" — image does not pre-create the path or chown correctly before switching to non-root user.
- "Default STARTUP TCP probe failed ... Connection failed with status CANCELLED" — container didn't accept TCP connections on the expected port during the startup probe window.

7) Optional follow-ups (sensible improvements)
- Mount `FIREBASE_CERT_JSON` as a file via Cloud Run secret mount (console or via YAML) instead of fetching from Secret Manager in the entrypoint. This removes the custom fetching code and avoids metadata access complexities.
- Add a tiny CI smoke test that builds the image, runs the container and curls `/health` before pushing/deploying.
- Add a short README snippet in this repo's README linking to this file for maintainers.

References
- Cloud Run troubleshooting: https://cloud.google.com/run/docs/troubleshooting
- Secret Manager docs: https://cloud.google.com/secret-manager/docs

---
Last updated: 2025-08-24
