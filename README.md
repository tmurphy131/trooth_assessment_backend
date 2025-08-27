# T[root]H Assessment API

This is the backend for the **T[root]H Assessment** app — a spiritual mentorship and discipleship platform for churches and Christian organizations.

It provides a RESTful API built with **FastAPI**, backed by a **PostgreSQL database**, and includes support for:
- Spiritual assessments (created by admins)
- Mentor/apprentice relationships
# T[root]H Assessment API

Backend for the T[root]H Assessment platform — a FastAPI service that powers assessments, mentor/apprentice workflows, Firebase auth, OpenAI scoring, and email notifications.

Quick pointers
- Language: Python 3.11+
- Framework: FastAPI
- DB: PostgreSQL (SQLAlchemy + Alembic)
- Auth: Firebase Admin SDK
- Integrations: SendGrid, OpenAI
- Container: Docker (Cloud Run deployment documented)

Important files
- `app/` — application code (routes, models, services)
- `tests/` — unit/integration tests
- `alembic/` — DB migrations
- `Dockerfile`, `entrypoint.sh` — container startup
- `DEPLOYMENT.md` — deployment commands and troubleshooting (detailed)

Getting started (local)
1. Clone and create venv

```bash
git clone https://github.com/tmurphy131/trooth_backend.git
cd trooth_backend
python -m venv venv
source venv/bin/activate
```

2. Install

```bash
pip install -r requirements.txt
```

3. Run migrations (Postgres required)

```bash
alembic upgrade head
```

4. Run tests

```bash
pytest
```

Environment variables
- See `DEPLOYMENT.md` for production secrets. For local development you can use a `.env` with values like:

```env
DATABASE_URL=postgresql://user:password@localhost:5432/trooth
OPENAI_API_KEY=sk-...
SENDGRID_API_KEY=SG-...
FIREBASE_CERT_PATH=./firebase_key.json
ENV=development
```

Deployment (short)
- Full deployment steps and exact commands are in `DEPLOYMENT.md`.
- Summary:
	- Create required secrets in Secret Manager: `DATABASE_URL`, `FIREBASE_CERT_JSON`, `SENDGRID_API_KEY`, `OPENAI_API_KEY`.
	- Grant the Cloud Run runtime service account `roles/secretmanager.secretAccessor` for those secrets.
	- Build an amd64 image and push to `gcr.io/<PROJECT>/trooth-backend:latest` using `docker buildx`.
	- Deploy to Cloud Run and map secrets via `--set-secrets`.

Why the extra entrypoint logic?
- The repo includes an `entrypoint.sh` that reads `FIREBASE_CERT_JSON` from Secret Manager (or accepts a mounted file) and writes it to `/secrets/firebase_key.json`. This supports running locally and in Cloud Run. For simplicity you may choose to mount the secret as a file in Cloud Run instead of fetching it in the entrypoint.

CI workflow (overview)
The recommended CI (GitHub Actions) pipeline runs on pushes and pull requests and performs:

- Lint + static checks (black, isort, ruff/mypy if configured)
- Unit tests (pytest)
- Build container image (docker/build-push-action) for linux/amd64
- Optional smoke test: run the built image in the runner and curl `/health`
- On `main` branch success: push image and deploy to Cloud Run (using a service account key stored in GitHub Secrets or the official Cloud Run deploy action)

Why this flow?
- It ensures code quality and catches syntax/runtime errors (like the earlier brittle python one-liner in `entrypoint.sh`) before deploying.

Example GitHub Actions (minimal)

```yaml
name: CI

on: [push, pull_request]

jobs:
	test_and_build:
		runs-on: ubuntu-latest
		steps:
			- uses: actions/checkout@v4
			- name: Setup Python
				uses: actions/setup-python@v4
				with:
					python-version: '3.11'
			- name: Install deps
				run: |
					python -m pip install --upgrade pip
					pip install -r requirements.txt
			- name: Run tests
				run: pytest -q
			- name: Build & push image (on main)
				if: github.ref == 'refs/heads/main'
				uses: docker/build-push-action@v4
				with:
					push: true
					tags: gcr.io/${{ secrets.GCP_PROJECT }}/trooth-backend:latest
					platforms: linux/amd64

	deploy:
		needs: test_and_build
		if: github.ref == 'refs/heads/main'
		runs-on: ubuntu-latest
		steps:
			- uses: actions/checkout@v4
			- name: Configure gcloud
				uses: google-github-actions/auth@v1
				with:
					credentials_json: ${{ secrets.GCP_SA_KEY }}
			- name: Deploy to Cloud Run
				uses: google-github-actions/deploy-cloudrun@v1
				with:
					service: trooth-backend
					image: gcr.io/${{ secrets.GCP_PROJECT }}/trooth-backend:latest
					region: us-east4

```

Notes on CI secrets and permissions
- `GCP_SA_KEY` — a JSON service account key (stored in GitHub Secrets) with minimal roles: `roles/run.admin` (or google-github-actions workflow recommended roles) and `roles/secretmanager.secretAccessor` if you deploy with secret mounts. Prefer Workload Identity / Workload Identity Federation where possible instead of long-lived keys.
- `GCP_PROJECT` — project id (set as a GitHub secret or organization variable).

Helpful follow-ups
- Consider mounting `FIREBASE_CERT_JSON` as a file in Cloud Run to remove runtime fetching logic.
- Add a CI smoke test that runs the built image and queries `/health` before deployment.

Connecting to Cloud SQL locally (Cloud SQL Auth Proxy)

If your Cloud SQL instance is not mounted as a unix socket (or you prefer TCP), use the Cloud SQL Auth Proxy to forward the instance to localhost.

Example:

```bash
# Start the proxy (replace path and instance)
./scripts/start_cloud_sql_proxy.sh /path/to/key.json trooth-prod:us-east4:app-pg 5432

# Export DATABASE_URL for local backend
export DATABASE_URL=postgresql://trooth:trooth@127.0.0.1:5432/trooth_db

# Start the backend
uvicorn app.main:app --reload
```

The helper script will log to `/tmp/csql-proxy.log` and write the pid to `/tmp/csql-proxy.pid`.

Notes:
- Use TCP forwarding (127.0.0.1:5432) to avoid socket path issues.
- This is the fastest way to get a working local dev environment.

Contributing
- PRs welcome. Run tests and linters locally before opening a PR.

License
- MIT License (c) 2024 tmurphy131
