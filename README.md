# T[root]H Discipleship API

The FastAPI backend for **T[root]H Discipleship**, a spiritual mentorship platform. Mentors guide
apprentices through Bible-based assessments, AI-generated growth reports, a shared prayer journal
and Bible trivia.

The iOS and Android app is the Flutter repo
[`trooth_assessment_frontend`](https://github.com/tmurphy131/trooth_assessment_frontend).

**Rules for this codebase live in the [constitution](.specify/memory/constitution.md).** Day-to-day
workflow is in [CONTRIBUTING.md](CONTRIBUTING.md). If anything here disagrees with them, they win.

## Contents

- [Features](#features)
- [Tech stack](#tech-stack)
- [Project layout](#project-layout)
- [Local setup](#local-setup)
- [Configuration](#configuration)
- [Database and migrations](#database-and-migrations)
- [API](#api)
- [Scheduled jobs](#scheduled-jobs)
- [Testing](#testing)
- [Deploying](#deploying)
- [Seeding data](#seeding-data)
- [Contributing](#contributing)
- [Other docs](#other-docs)

## Features

- **Mentors and apprentices:** invitations, multi-mentor links, mentorship agreements with
  multi-party signatures, mentor notes and resources.
- **Assessments:** Master T[root]H, Spiritual Gifts (72 questions), Bible book assessments and
  mentor-created templates. Drafts auto-save, and submissions are scored in the background.
- **AI scoring and reports:** LLM-scored answers with full mentor and apprentice reports, sent by
  email and as PDFs.
- **Prayer journal:** private entries, with optional sharing to a mentor.
- **Bible trivia:**
  - server-run single player (graded and timed on the server);
  - head-to-head challenges (creating one is premium);
  - a daily question with streaks, freezes and reward codes;
  - leaderboard competitions with Shopify prize codes.
- **Premium:** RevenueCat subscriptions, mentor-gifted seats and admin grants. Premium is enforced
  here, with HTTP 403 when a user doesn't have it.
- **Engagement:** push notifications, weekly tips, email reminder campaigns, and weekly and monthly
  metrics reports.

## Tech stack

| Area | Technology |
|---|---|
| Framework | FastAPI on Python 3.11 |
| Database | PostgreSQL (Cloud SQL), SQLAlchemy 2.0 (sync sessions), Alembic |
| Auth | Firebase Admin SDK (Firebase ID tokens) |
| AI | `app/services/llm/` provider layer: Vertex AI Gemini by default, OpenAI as fallback |
| Email | SendGrid with Jinja2 templates |
| Push | Firebase Cloud Messaging |
| Payments | RevenueCat (webhooks and server-side verification) |
| Shop and prizes | Shopify Admin API (discount codes), Shopify Storefront and Printful (product listings) |
| Hosting | Docker on Google Cloud Run, Secret Manager, Cloud Scheduler |
| Tests | pytest with SQLite in memory |

## Project layout

```text
app/
  main.py                FastAPI app and router registration
  core/settings.py       all configuration, read from environment variables
  db.py                  session factory
  models/                SQLAlchemy models
  schemas/               Pydantic request and response models
  routes/                API routers (keep them thin)
  services/              business logic and integrations
    llm/                 provider factory (Gemini, OpenAI) with timeouts, retries, fallback
  templates/             Jinja2 email templates
  middleware/            correlation IDs, rate limiting
alembic/versions/        migrations (YYYYMMDD_description.py)
scripts/                 seeding and import scripts and Cloud Run job helpers
specs/NNN-name/          Spec Kit specs; contracts/ is the API source of truth
tests/                   pytest suite
```

## Local setup

**Prerequisites:** Python 3.11, PostgreSQL 14+, and a Firebase service account key.

1. **Create a virtual environment and install dependencies:**
   ```bash
   python3.11 -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. **Create the database:**
   ```bash
   createdb trooth_db
   ```
3. **Add a `.env` file** (see [Configuration](#configuration)). The minimum is:
   ```env
   ENV=development
   DATABASE_URL=postgresql://trooth_user:password@localhost:5432/trooth_db
   FIREBASE_CERT_PATH=./firebase_key.json
   LLM_PROVIDER=openai          # or gemini, with `gcloud auth application-default login`
   OPENAI_API_KEY=sk-...
   ```
4. **Run migrations and start the server:**
   ```bash
   alembic upgrade head
   uvicorn app.main:app --reload --port 8000
   ```

Interactive docs are at `http://localhost:8000/docs`. Never commit `.env` or `firebase_key.json`.

To run in Docker instead:
```bash
docker build -t trooth-backend:local .
docker run -p 8000:8000 --env-file .env \
  -v $(pwd)/firebase_key.json:/app/firebase_key.json:ro trooth-backend:local
```

## Configuration

All settings are read from environment variables in `app/core/settings.py`. Secrets come from
Secret Manager in Cloud Run; nothing secret belongs in source.

| Group | Variables |
|---|---|
| Core | `ENV` (`development`, `dev`, `production`), `DATABASE_URL`, `CORS_ORIGINS`, `APP_URL`, `BACKEND_API_URL`, `SHOW_DOCS`, `LOG_LEVEL`, `RATE_LIMIT_ENABLED` |
| Database pool / Cloud SQL | `DB_POOL_SIZE`, `DB_MAX_OVERFLOW`, `DB_POOL_RECYCLE`, `CLOUD_SQL_INSTANCE`, `CLOUD_SQL_IAM_AUTH`, `CLOUD_SQL_USE_PRIVATE_IP`, `DB_USER`, `DB_PASS`, `DB_NAME` |
| Auth | `FIREBASE_CERT_JSON` (Cloud Run) or `FIREBASE_CERT_PATH` (local) |
| AI | `LLM_PROVIDER` (`gemini` default), `LLM_MODEL`, `LLM_FALLBACK_ENABLED`, `OPENAI_API_KEY`, `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION` |
| Email | `SENDGRID_API_KEY`, `EMAIL_FROM_ADDRESS`, `METRICS_REPORT_RECIPIENTS` |
| Premium | `REVENUECAT_WEBHOOK_SECRET`, `REVENUECAT_SECRET_API_KEY`, `REVENUECAT_API_KEY`, `PREMIUM_FEATURES_ENABLED` (testing only) |
| Shop and prizes | `SHOPIFY_CLIENT_ID`, `SHOPIFY_CLIENT_SECRET`, `SHOPIFY_ADMIN_API_VERSION`, `SHOPIFY_PRIZE_COLLECTION_ID`, `SHOPIFY_STORE_DOMAIN`, `SHOPIFY_STOREFRONT_TOKEN`, `SHOP_URL`, `PRINTFUL_API_TOKEN`, `PRINTFUL_STORE_ID` |
| Trivia | `TRIVIA_COMPETITION_EXCLUDED_EMAILS`, `TRIVIA_COMPETITION_ADMIN_EMAILS`, `TRIVIA_LEGACY_SINGLE_ENABLED` (`false` in prod since app 2.2.0) |
| Scheduled jobs | `CRON_SECRET` (sent as `X-Cron-Secret` by Cloud Scheduler) |

When the Shopify credentials are missing, prize and reward codes run in dry-run mode outside prod and
are refused in prod. Without `SENDGRID_API_KEY`, emails are logged instead of sent.

> **Deploys replace the whole list.** `gcloud run deploy --set-env-vars/--set-secrets` replaces
> everything on the service. The deploy skills keep complete lists; a dropped entry silently turns a
> feature off. For example, missing Shopify secrets stop prize codes, and a missing
> `TRIVIA_LEGACY_SINGLE_ENABLED=false` reopens the old trivia endpoints.

## Database and migrations

- **Every model change needs a migration** in `alembic/versions/`, named `YYYYMMDD_description.py`,
  with a working `downgrade()`.
- **Migrations run before the new image serves traffic.** The deploy skills run the
  `migrate-and-populate` (prod) or `migrate-and-populate-dev` Cloud Run job first.
- **Autogenerate misses some models.** `alembic/env.py` doesn't import every model, including the
  trivia ones, so write those migrations by hand. Reuse existing Postgres enum types with
  `postgresql.ENUM(..., create_type=False)`; creating them again fails on Cloud SQL.
- **Commands:**
  ```bash
  alembic revision -m "describe change"   # then edit; use --autogenerate only if the models are imported
  alembic upgrade head
  alembic downgrade -1
  ```
- **Connect to Cloud SQL locally** with `scripts/start_cloud_sql_proxy.sh`.

## API

- **Auth:** endpoints need `Authorization: Bearer <Firebase ID token>`, except health, public
  token links, webhooks and `/scheduled/*`, which checks `X-Cron-Secret` instead.
- **Contracts:** the API contract for each feature is in `specs/NNN-name/contracts/`. That is the
  source of truth for the app. `MOBILE_API_GUIDE.md` is legacy.
- **Compatibility:** released app versions can't be forced to update, so changes are additive.
  Removing anything requires a spec that names the minimum app version.

| Prefix | Area |
|---|---|
| `/health` | Health check |
| `/users` | Registration, profile, timezone |
| `/mentor`, `/apprentice` | Role dashboards, reports, links; `/mentor/seats` for gifted seats |
| `/invitations`, `/agreements` | Apprentice invitations, mentorship agreements |
| `/templates`, `/admin` | Published assessment templates; template and admin management |
| `/assessment-drafts`, `/assessments`, `/question` | Draft, submit and score assessments |
| `/spiritual-gifts`, `/master-trooth`, `/generic-assessments` | Assessment-specific flows and reports |
| `/progress` | Progress and score history |
| `/prayer-journal` | Prayer journal |
| `/trivia` | Single player sessions, challenges, leaderboard, competitions, profiles |
| `/trivia/daily` | Daily question and streaks |
| `/subscriptions`, `/admin/subscriptions` | Status, restore, RevenueCat webhook, admin grants |
| `/push-notifications` | Device tokens, test pushes |
| `/shop`, `/support` | Merch listings; support requests |
| `/campaigns`, `/metrics`, `/scheduled` | Engagement campaigns, metrics reports, cron entry points |
| `/r` | Redirect links |

Mentor, apprentice and resource routes are registered without a prefix in `app/main.py`; see `/docs`
for the full list.

## Scheduled jobs

Cloud Scheduler (us-east4) calls these endpoints with `X-Cron-Secret`:

| Job | Schedule | Endpoint |
|---|---|---|
| `daily-trivia-prod` | hourly | `/scheduled/daily-trivia` (9am local reminders, streak rewards) |
| `trivia-competition-finalize-prod` | hourly | `/scheduled/trivia-competition-finalize` |
| `trivia-expiry-prod` | daily 03:00 ET | `/scheduled/trivia-expiry` (expires challenges idle 7 days, closes abandoned single player games) |
| `trooth-weekly-tips` | Sun 09:00 ET | `/scheduled/weekly-tips` |
| `weekly-metrics-report` / `monthly-metrics-report` | Mon 14:00 ET / 1st 14:00 ET | `/metrics/send-report` |
| `campaigns-draft-reminders-{prod,dev}` | daily 19:00 UTC | `/campaigns/run-draft-reminders` |
| `campaigns-inactive-reminders-{prod,dev}` | daily 08:00 UTC | `/campaigns/run-inactive-reminders` |


## Testing

```bash
pytest -q
```

`pytest` must pass before every merge and deploy; there is no CI here, so the local suite is the
only gate.

- **Database:** tests use an in-memory SQLite database (`tests/conftest.py`). Note that SQLite
  returns naive datetimes.
- **Auth:** override `get_current_user` in tests.
- **External services:** never call live services (LLM, SendGrid, Firebase, RevenueCat, Shopify);
  mock them.
- **Coverage for new or changed endpoints:** test the success path and every authorization failure
  that applies (wrong role, not the owner, not premium).

## Deploying

Deploys use Claude Code skills in the frontend repo:

| Skill | What it does |
|---|---|
| `/deploy-dev` | Cloud Build image → `migrate-and-populate-dev` job → deploy `trooth-backend-dev` |
| `/deploy-prod` | Cloud Build image tagged with the commit → `migrate-and-populate` job → deploy `trooth-backend` |

- Deploy to **dev** first and verify there.
- **Prod** is built from `main`.
- The gcloud project must be `trooth-prod` (`gcloud config set project trooth-prod`).

| Env | URL |
|---|---|
| Dev | `https://trooth-discipleship-api-dev.onlyblv.com/` |
| Prod | `https://trooth-discipleship-api.onlyblv.com/` |

Secret creation and one-time setup are in [DEPLOYMENT.md](DEPLOYMENT.md).

## Seeding data

| What | How |
|---|---|
| Spiritual Gifts assessment | `python scripts/seed_spiritual_gifts.py --version 1 --publish` (or `scripts/create_and_run_spiritual_gifts_seed_job.sh`) |
| Master T[root]H mini | `python scripts/seed_master_mini.py` |
| Trivia questions | `scripts/import_trivia_questions.py`; Cloud Run jobs via `scripts/run_import_trivia_questions_job.sh` (prod) and `scripts/run_trivia_import_dev_job.sh` (dev) |
| Mentorship agreement template | Seeded on first startup from `MENTOR_AGREEMENT.md` |

Seed scripts are idempotent. They skip rows that already exist.

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md). In short:

- **Specs first:** features go through [GitHub Spec Kit](https://github.com/github/spec-kit), with
  artifacts in `specs/NNN-name/`. Bug fixes and chores can skip the spec.
- **Branches and PRs:** branch from `main` as `feature/`, `fix/` or `chore/`. Use Conventional
  Commits (`type(scope): summary`). Every change reaches `main` through a PR that links its spec and
  says how it was verified (pytest, dev deploy).
- **Formatting:** `black` and `isort` are optional for new files. Don't reformat existing files in
  an unrelated change.

## Other docs

| Doc | Topic |
|---|---|
| [DEPLOYMENT.md](DEPLOYMENT.md), [DEV_ENVIRONMENT_SETUP.md](DEV_ENVIRONMENT_SETUP.md) | Infrastructure setup |
| [AI_SCORING_DETAILS.md](AI_SCORING_DETAILS.md) | How scoring prompts and reports work |
| [METRICS_SYSTEM.md](METRICS_SYSTEM.md) | Metrics and reports |
| [EMAIL_SETUP_GUIDE.md](EMAIL_SETUP_GUIDE.md), [ENGAGEMENT_EMAIL_STRATEGY.md](ENGAGEMENT_EMAIL_STRATEGY.md) | Email and engagement campaigns |
| [SPIRITUAL_GIFT_ASSESSMENT.md](SPIRITUAL_GIFT_ASSESSMENT.md), [MULTI_MENTOR_DESIGN.md](MULTI_MENTOR_DESIGN.md) | Feature design notes |
| [SCALING_GUIDE.md](SCALING_GUIDE.md) | Scaling notes |

Root-level `*_COMPLETE.md` and `PHASE_*.md` files are historical status reports. Current features are
specified in `specs/`.
