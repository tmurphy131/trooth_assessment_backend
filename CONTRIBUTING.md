# Contributing to the T[root]H Discipleship API

The rules for how this API is built are in the
[constitution](.specify/memory/constitution.md). This guide is the day-to-day workflow; where
they differ, the constitution wins. The Flutter client lives in the sibling repo
`trooth_assessment` with its own constitution and guide.

## 1. Spec-driven workflow

New endpoints and behavior changes start with a spec using
[GitHub Spec Kit](https://github.com/github/spec-kit) (v1.1.0). In Claude Code:

1. `/speckit-specify <what and why>` → `specs/NNN-name/spec.md`. State roles, ownership,
   premium gating and backward compatibility.
2. `/speckit-clarify` (optional) to resolve open questions.
3. `/speckit-plan <technical notes>` → `plan.md`, `data-model.md` and `contracts/`. Its
   **Constitution Check** must pass, or the exception is justified in Complexity Tracking.
4. `/speckit-tasks`, then `/speckit-analyze` for anything non-trivial.
5. `/speckit-implement`, then `/speckit-converge` until it reports *Converged*.

**API contracts.** `specs/NNN-name/contracts/` is the contract the frontend builds against.
Link it from the matching frontend spec. `MOBILE_API_GUIDE.md` is a legacy reference and is no
longer updated.

Bug fixes and chores may skip the spec but still follow the constitution.

## 2. Branches

Branch from `main` using a prefix and a kebab-case name:

| Prefix | For |
|---|---|
| `feature/` | New features (`feature/trivia-competition`) |
| `fix/` | Bug fixes (`fix/invite-expiry-check`) |
| `chore/` | Tooling, docs, dependencies (`chore/adopt-speckit`) |

Don't commit directly to `main`. Spec folders are numbered on their own (`specs/004-prayer-journal/`).

## 3. Commit messages

Use [Conventional Commits](https://www.conventionalcommits.org/) in the form `type(scope): summary`.

- **Types:** `feat`, `fix`, `chore`, `refactor`, `perf`, `test`, `docs`, `build`, `ci`. Scope by
  domain, for example `subscriptions`, `trivia` or `auth`.
- **Summary:** lowercase, no trailing period, and describe the behavior that changed.
- **Body:** explain why. Wrapped bullets are fine for multi-part changes.

## 4. Pull requests

Every change reaches `main` through a GitHub pull request.

- **Description:**
  - Link the spec folder if there is one.
  - Summarize the API changes: endpoints, fields, status codes.
  - Name any migration.
  - Say how you verified the change: `pytest`, plus the dev deploy result.
- **Before requesting review:**
  - `pytest` passes.
  - Touched files are formatted with `black` and `isort`.
- **New config or secrets:** update both deploy skills in the frontend repo, `/deploy-dev` and
  `/deploy-prod`, with the **complete** env and secret lists.
- **Separate PRs:**
  - Constitution amendments.
  - Repo-wide reformatting.

## 5. Testing and linting

| Check | Command |
|---|---|
| Full suite | `.venv/bin/python -m pytest -q` |
| One file | `.venv/bin/python -m pytest tests/test_<domain>.py -v` |
| Formatting (touched files) | `black <files> && isort <files>` |

Tests use an in-memory SQLite database and auth overrides from `tests/conftest.py`, which sets
`ENV=test`.

- **Every new or changed endpoint needs tests** for the success path and for each authorization
  failure that applies: wrong role, not the owner, not premium.
- **Mock external services.** Tests must not call live LLM providers, SendGrid, Firebase,
  RevenueCat or Shopify.
- **Scripts that hit live services stay out of `tests/`.** If a script calls a real service,
  don't name it `test_*.py` inside that folder.

## 6. Database migrations

1. Change the model, then run `alembic revision -m "description"`. Rename the file to
   `YYYYMMDD_description.py`.
2. Implement `downgrade()`, or explain in the file why the change can't be reversed.
3. Check it locally with `alembic upgrade head`.
4. `/deploy-dev` and `/deploy-prod` run the migrate job **before** the new revision deploys.
   Never deploy a schema-dependent change without running the migration first.

## 7. Code review standards

Reviewers check the PR against the constitution:

- **Auth:** every non-public endpoint requires auth or a role helper.
- **Mentor access:** a mentor reaching an apprentice's data is checked against an active
  `MentorApprentice` link.
- **Premium:** features are gated server-side and return a 403.
- **Test shortcuts:** nothing that skips auth works outside `ENV=test`.
- **Compatibility:** changes are additive, so apps already in the stores keep working.
- **Errors:** use `HTTPException` or the classes in `app/exceptions.py`. Stack traces are not
  returned outside development.
- **Logging:** through `logging.getLogger(__name__)`, with no tokens, secrets or personal data.
- **Secrets:** none in source. Config is read through `app/core/settings.py`.
- **LLM calls:** go through `app/services/llm/`.
- **Tests and migrations:** both are present where needed.

## 8. Deploying

Deploys run from the frontend repo's Claude Code skills:

1. `/deploy-dev`, then verify the change on dev.
2. `/deploy-prod`, from `main` only.

See [DEPLOYMENT.md](DEPLOYMENT.md) for the underlying commands.

## 9. Changing the constitution

1. Open a `chore/` branch and run `/speckit-constitution <the change and why>`.
2. Bump the version using semver, as set out in the constitution's Governance section:
   - **MAJOR**: a principle is removed or redefined.
   - **MINOR**: a principle is added or expanded.
   - **PATCH**: wording only.
3. Update the affected files in `.specify/templates/overrides/`, plus this guide and
   `CLAUDE.md`.
4. Make changes to Principle X (cross-repo contract) in the frontend constitution too.
5. Open a PR that contains only the amendment. Remove the Sync Impact Report comment before you
   merge.
