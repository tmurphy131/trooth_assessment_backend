# T[root]H Discipleship — Backend API

FastAPI backend for the T[root]H spiritual mentorship platform. Its client is the Flutter app at `/Users/tmoney/Developer/trooth_assessment`.

**Source of truth for rules: [.specify/memory/constitution.md](.specify/memory/constitution.md).** If anything here conflicts with it, the constitution wins. Contributor workflow: [CONTRIBUTING.md](CONTRIBUTING.md).

## Project Layout

```
app/
  main.py              # App setup, router registration, global exception handlers
  core/settings.py     # All config from env vars (ENV, secrets, feature flags)
  services/auth.py     # get_current_user, require_mentor/apprentice/admin, require_premium
  routes/              # APIRouter modules (one per domain)
  schemas/             # Pydantic models
  models/              # SQLAlchemy models (sync sessions via app/db.py get_db)
  services/            # Business logic & integrations; services/llm/ = provider factory
  templates/email/     # Jinja email templates
alembic/versions/      # Migrations — new ones named YYYYMMDD_description.py
tests/                 # pytest; conftest.py = SQLite in-memory + auth overrides, sets ENV=test
setup_*_assessment.py  # Idempotent seed scripts (run as Cloud Run jobs)
```

## Commands

```bash
.venv/bin/python -m pytest -q              # full suite (must pass before merge/deploy)
uvicorn app.main:app --reload --port 8000  # local server
alembic revision -m "description"          # then rename to YYYYMMDD_description.py
```

## Environments & Deploy

| Env  | URL | Cloud Run service |
|------|-----|-------------------|
| Dev  | `https://trooth-discipleship-api-dev.onlyblv.com/` | `trooth-backend-dev` |
| Prod | `https://trooth-discipleship-api.onlyblv.com/`     | `trooth-backend`     |

Deploys are manual and run from the **frontend** repo's skills: `/deploy-dev`, then `/deploy-prod` (prod from `main`). They build the image, run the migrate job **before** deploying, and set the full env-var and secret lists (`--set-*` replaces everything — keep them complete). There is no CI in this repo.

## Spec-Driven Workflow (GitHub Spec Kit)

Features are built spec-first. Artifacts live in `specs/NNN-feature-name/`; API contracts in its `contracts/` are the source of truth for the frontend (`MOBILE_API_GUIDE.md` is legacy). Templates are customized in `.specify/templates/overrides/`; never edit the core templates in `.specify/templates/`.

| Step | Command | Use it when |
|------|---------|-------------|
| 0 | `/speckit-constitution` | Only to amend the constitution (via its own PR) |
| 1 | `/speckit-specify <what & why>` | Starting any new endpoint or behavior change. No tech choices here |
| 1b | `/speckit-clarify` | Roles, ownership, premium or compatibility are unclear |
| 2 | `/speckit-plan <tech notes>` | Spec is settled; produces plan, data model, contracts and the Constitution Check |
| 2b | `/speckit-checklist` | Optional quality check on requirements before tasks |
| 3 | `/speckit-tasks` | Plan passes the Constitution Check |
| 3b | `/speckit-analyze` | Before implementing anything non-trivial |
| 4 | `/speckit-implement` | Tasks are approved |
| 5 | `/speckit-converge` | After implementing; repeat implement → converge until "Converged" |

Small bug fixes and chores may skip specs but still follow the constitution. Work on a `feature/`, `fix/` or `chore/` branch (Spec Kit does not create branches here), and don't commit until the user asks.
