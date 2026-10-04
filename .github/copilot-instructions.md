# T[root]H Discipleship: AI Agent Instructions (Backend API)

Start with these files. They are kept current. This file only points to them.

1. **[.specify/memory/constitution.md](../.specify/memory/constitution.md)** is the source of truth. It sets the rules (MUST/SHOULD) for:
   - auth and ownership
   - errors
   - migrations
   - secrets
   - API compatibility
   - testing
   - deploys
2. **[CLAUDE.md](../CLAUDE.md)** covers layout, commands, environments, and the spec-driven workflow.
3. **[CONTRIBUTING.md](../CONTRIBUTING.md)** covers branches, commit format, PRs, migrations, and deploys.

Feature specs live in `specs/NNN-name/`. The API contracts in each feature's `contracts/` are what the Flutter client (sibling repo `trooth_assessment`) builds against. `MOBILE_API_GUIDE.md` is legacy.

## Domain essentials

**Roles.** There are three roles: admin, mentor and apprentice.
- Authorization is enforced only here, through the helpers in `app/services/auth.py`.
- A mentor sees an apprentice's data only through an active `MentorApprentice` link. An apprentice can have more than one mentor.

**Assessments.** An assessment moves through three stages:
1. A **template**, which is reusable. Only templates with `published` set are visible to apprentices.
2. A **draft**, which the apprentice fills in. It is auto-saved.
3. A submitted **assessment**. The AI scores it through `app/services/llm/`, and after that it does not change.

**Agreements.** The mentor creates and submits an agreement. The apprentice signs it next. If `parent_required` is set, a parent signs last, using a public token link.

**Premium.** Premium features are gated on the server and return 403 when the user doesn't have access. The app treats the 403 status as the signal to show the upgrade screen.
