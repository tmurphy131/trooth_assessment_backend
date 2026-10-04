# T[root]H Discipleship API Constitution

## Core Principles

### I. Authenticated by Default

- Every endpoint that is not explicitly public MUST depend on `get_current_user` or a role
  helper from `app/services/auth.py` (`require_mentor`, `require_apprentice`, `require_admin`,
  `require_mentor_or_admin`).
- Endpoints that touch an apprentice's data on behalf of a mentor MUST verify an active
  `MentorApprentice` link between them (or an admin role).
- Premium features MUST be gated server-side with `require_premium`, `require_premium_mentor`
  or `is_premium_user`, and MUST fail with HTTP 403. The app relies on that status code.
- Test-only auth shortcuts (mock tokens, header overrides) MUST be impossible unless
  `ENV == "test"`, and every such shortcut MUST have a test proving it is rejected otherwise.

**Rationale**: the frontend's role and premium checks are UI-only; this API is the only real
access control over minors' spiritual and personal data.

### II. Errors

- Handlers MUST raise `HTTPException` or the types in `app/exceptions.py`. Error bodies MUST
  keep the `detail` field. The global handlers add `correlation_id`; new code MUST NOT bypass
  them with ad-hoc 4xx/5xx bodies.
- Stack traces and exception types MUST be returned only when `ENV == "development"`.

**Rationale**: the app maps responses by status code and shows `detail`; correlation IDs tie
user reports to logs.

### III. Schema Changes Through Alembic

- Every model change MUST ship with an Alembic migration in `alembic/versions/`. New
  migrations MUST be named `YYYYMMDD_description.py` and MUST implement `downgrade()` or
  state in the file why it cannot be reversed.
- Migrations MUST run via the Cloud Run migrate job **before** the new image is deployed, so
  new code never starts against an old schema.
- Seed/setup scripts MUST be idempotent: check for existing rows (e.g. template `key`) and skip.

**Rationale**: Cloud Run starts new revisions immediately; schema drift there is an outage.

### IV. Config & Secrets

- Configuration MUST be read through `app/core/settings.py` from environment variables.
- Secrets MUST come from Secret Manager via Cloud Run `--set-secrets`. `.env`,
  `firebase_key.json` and any credentials MUST NOT be committed.
- New code MUST NOT put real secret values or usable fallback secrets in source defaults.
- Deploy commands MUST list the complete env-var and secret sets, because `--set-env-vars` and
  `--set-secrets` replace everything on the service.

**Rationale**: a dropped secret silently disables features (e.g. Shopify prize codes); a
committed one is a breach.

### V. Logging

- New code MUST log with `logger = logging.getLogger(__name__)`, not `print`.
- Logs MUST NOT contain tokens, secrets, or request bodies with personal data.

**Rationale**: Cloud Run captures stdout permanently; structured, named logs are searchable.

### VI. API Compatibility

- Released app versions cannot be force-updated, so changes to existing endpoints MUST be
  additive: new optional fields, new endpoints. Removing or renaming a route, field or status
  code MUST be specified in a feature spec that names the minimum app version that no longer
  needs it.
- New handlers SHOULD declare a `response_model`.

**Rationale**: the codebase already carries compat routes, legacy `/health` and dual report
formats for exactly this reason; breaking a live app version strands users.

### VII. Layering

- Integrations and reusable business logic (LLM, email, push, payments, auth, metrics) SHOULD
  live in `app/services/`; route modules SHOULD stay focused on request handling.
- LLM calls MUST go through `app/services/llm/` (provider factory with timeouts, retries and
  fallback), never a provider SDK called directly from a route.

**Rationale**: provider switching (OpenAI → Gemini) and retry policy live in one place.

### VIII. Testing

- `pytest` MUST pass before merge and before any deploy.
- New or changed endpoints MUST have tests in `tests/` using the conftest fixtures (SQLite
  in-memory DB, `get_current_user` overrides), covering the success path and the authorization
  failures that apply (wrong role, not the owner, non-premium).
- Tests MUST NOT call live external services (LLM providers, SendGrid, Firebase, RevenueCat,
  Shopify); mock them. Ad-hoc scripts that hit live services MUST NOT be named `test_*.py`
  inside `tests/`.

**Rationale**: there is no CI here; the local suite is the only gate before Cloud Run.

### IX. Environments & Deploy

- Every change MUST be deployed to dev (`/deploy-dev`) and verified there before prod.
- Prod deploys (`/deploy-prod`) MUST be built from `main`.

**Rationale**: dev and prod share the deploy scripts; dev is the only rehearsal.

### X. Cross-Repo Contract

- A feature that adds or changes API behavior MUST define its contract in this repo's
  `specs/NNN-name/contracts/`: endpoints, request/response shapes, and error status codes.
  This is the source of truth for the frontend. `MOBILE_API_GUIDE.md` is a legacy reference
  and is not maintained.
- The matching frontend spec MUST link that contract.

**Rationale**: the two repos ship independently; a written contract stops drift.

### XI. Formatting

- Files you change SHOULD be formatted with `black` and `isort`. Repo-wide reformatting MUST
  be its own PR.

**Rationale**: both tools are already in `requirements.txt`; formatting only touched files
keeps diffs reviewable.

## Technology Constraints & Known Debt

- Stack: Python 3.11, FastAPI, SQLAlchemy (sync sessions), Alembic, PostgreSQL on Cloud SQL,
  Firebase Admin, SendGrid, Vertex Gemini / OpenAI via `app/services/llm/`, Cloud Run.
- Principles apply to new or touched code. Known existing violations are grandfathered;
  touching the code SHOULD fix them, and no change may increase them:
  - `CRON_SECRET` and Shopify storefront token defaults in `app/core/settings.py` (IV)
  - ~25 `print(` calls in `app/` (V)
  - 4 migrations with empty `downgrade()` (III)
  - ~55% of handlers without `response_model`; much business logic in routes (VI, VII)
  - two premium-403 body shapes (string vs. object `detail`) (II)

## Development Workflow

- Every change reaches `main` through a GitHub pull request; direct pushes and local merges to
  `main` are not allowed. Work happens on `feature/<kebab-name>`, `fix/<kebab-name>` or
  `chore/<kebab-name>` branches.
- Commits follow Conventional Commits: `type(scope): summary` with types `feat`, `fix`, `chore`,
  `refactor`, `perf`, `test`, `docs`, `build`, `ci`.
- Non-trivial features follow the Spec Kit flow: `/speckit-specify` → `/speckit-plan` →
  `/speckit-tasks` → `/speckit-implement` → `/speckit-converge`, with artifacts in
  `specs/NNN-name/`. Bug fixes and chores MAY skip specs.
- The PR description links its spec folder (if any) and states how it was verified (pytest,
  dev deploy).

See [CONTRIBUTING.md](../../CONTRIBUTING.md) for the day-to-day details.

## Governance

- This constitution supersedes other guidance in the repo (CLAUDE.md, CONTRIBUTING.md, README,
  `.github/copilot-instructions.md`); those documents MUST be updated if they conflict with it.
- Amendments are made by pull request that edits this file, updates the Sync Impact Report, and
  updates any affected templates in `.specify/templates/overrides/` and CONTRIBUTING.md. An
  amendment to Principle X MUST be mirrored in the frontend constitution.
- Versioning follows semver: MAJOR for removing or redefining a principle, MINOR for adding a
  principle or materially expanding one, PATCH for wording and clarifications.
- Compliance is checked at two points: the Constitution Check gate in every `plan.md`, and PR
  review. Any deviation MUST be recorded in the plan's Complexity Tracking table with a
  justification, or the PR is not merged.

**Version**: 1.0.0 | **Ratified**: 2026-10-04 | **Last Amended**: 2026-10-04
