# Implementation Plan: [FEATURE]

**Branch**: `feature/[name]` (or `fix/`, `chore/`) | **Date**: [DATE] | **Spec**: [link]

**Input**: Feature specification from `/specs/[###-feature-name]/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

[Extract from feature spec: primary requirement + technical approach from research]

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: Python 3.11

**Primary Dependencies**: FastAPI, SQLAlchemy, Alembic, Firebase Admin [+ any NEW package with justification]

**Storage**: PostgreSQL (Cloud SQL) [new tables/columns + migration name, or N/A]

**Testing**: pytest (`tests/`, SQLite in-memory via conftest fixtures)

**Target Platform**: Google Cloud Run (dev and prod services)

**Project Type**: web-service (client: Flutter app in `trooth_assessment`)

**Performance Goals**: [domain-specific, e.g., 1000 req/s, 10k lines/sec, 60 fps or NEEDS CLARIFICATION]

**Constraints**: [domain-specific, e.g., <200ms p95, <100MB memory, offline-capable or NEEDS CLARIFICATION]

**Scale/Scope**: [domain-specific, e.g., 10k users, 1M LOC, 50 screens or NEEDS CLARIFICATION]

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Source: `.specify/memory/constitution.md`. Mark each ✅ / ❌ / N/A; every ❌ needs a row in
Complexity Tracking.

- [ ] **I. Auth**: every non-public endpoint uses `get_current_user`/role helper; mentor→apprentice access checks active `MentorApprentice`; premium gated server-side with 403; no test shortcuts outside `ENV=test`
- [ ] **II. Errors**: `HTTPException`/`app/exceptions.py`; `detail` preserved; no traces outside development
- [ ] **III. Migrations**: Alembic migration `YYYYMMDD_description.py` with `downgrade()`; run via migrate job before deploy; seeds idempotent
- [ ] **IV. Config & secrets**: via `app/core/settings.py`; secrets via Secret Manager; no secret defaults; deploy env/secret lists updated in full
- [ ] **V. Logging**: `logging.getLogger(__name__)`; no tokens/secrets/PII in logs
- [ ] **VI. Compatibility**: changes additive for released app versions; `response_model` declared
- [ ] **VII. Layering**: integrations in `app/services/`; LLM via `app/services/llm/`
- [ ] **VIII. Tests**: success + authz-failure tests per endpoint; no live external calls; `pytest` passes
- [ ] **IX. Deploy**: verified on dev before prod; prod from `main`
- [ ] **X. Contract**: `contracts/` documents endpoints, shapes and status codes; frontend spec links it
- [ ] **XI. Formatting**: no unrelated reformatting of existing files (formatting not yet required)

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)
<!--
  ACTION REQUIRED: List the real files this feature adds or changes.
-->

```text
app/
├── routes/<domain>.py        # APIRouter; registered in app/main.py
├── schemas/<domain>.py       # Pydantic request/response models
├── models/<entity>.py        # SQLAlchemy models (import in alembic/env.py)
├── services/<integration>.py # business logic, integrations; LLM via services/llm/
└── templates/email/          # Jinja email templates
alembic/versions/YYYYMMDD_description.py
tests/test_<domain>.py
```

**Structure Decision**: [Document the selected structure and reference the real
directories captured above]

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
