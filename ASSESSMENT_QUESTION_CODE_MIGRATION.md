# Spiritual Gifts Assessment: Question Code Migration Plan

Date: 2025-09-15
Owner: (fill in)
Status: Draft
Scope: Introduce durable `question_code` identifiers for the 72 (and future) Spiritual Gifts assessment questions **before** first production seeding of those question rows.

---
## 1. Goals
- Add a stable, human-readable, immutable code for each assessment question (e.g. `Q01`..`Q72`).
- Ensure repeatable idempotent seeding using codes instead of matching by raw text.
- Protect future edits to wording without breaking scoring or historical responses.
- Lay groundwork for multi-version and localization support.

## 2. Non-Goals (Explicitly Out of Scope For This Migration)
- Implement scoring endpoints (separate effort).
- Introduce localization tables (future enhancement).
- Change existing non–Spiritual Gifts assessments.
- Backfill historical spiritual gifts responses (none exist yet).

## 3. Current State (Baseline)
- Script: `scripts/seed_spiritual_gifts.py` seeds definitions, optionally 72 question texts, linking by *text equality*.
- No `question_code` column in `question` table.
- MAP (gift → 3 question codes) + QUESTION_ITEMS lives only in script constants.
- Questions have not yet been seeded in the target environment (per request).

## 4. High-Level Strategy
Because questions are not yet seeded, we can:
1. Add the new column with NOT NULL + UNIQUE constraint from the start.
2. Seed all 72 questions with their codes in one migration (no backfill complexity).
3. Update seeding script to rely on `question_code` lookups -> true idempotency.

If any environment *already* seeded without codes (edge case), add a fallback mini-backfill procedure described in §9.

## 5. Data Model Changes
| Table | Change | Details |
|-------|--------|---------|
| `question` | Add column | `question_code VARCHAR(16) NOT NULL UNIQUE` (length generous; index automatically via unique constraint). |

### Column Characteristics
- Immutable after initial insert (enforce in application service layer / seeding logic; optional DB trigger if desired later).
- Canonical key for referencing questions in scoring, analytics, exports.

## 6. Migration Steps (DB)
1. Create Alembic revision: `add_question_code_to_question`.
2. In `upgrade()`:
   - Add column `question_code` (nullable=False if empty DB for these rows; else add nullable=True temporarily – see §9 fallback).
   - Add unique constraint.
3. In `downgrade()`:
   - Drop unique constraint.
   - Drop column.
4. Verify revision order (head should now include this migration before any scoring-related future migrations).

## 7. Seed Script Updates (`scripts/seed_spiritual_gifts.py`)
Update logic when `--seed-questions` flag is used:
- Maintain authoritative `QUESTION_ITEMS = [(code, gift_slug, text), ...]` (already present).
- On run:
  1. Build dict `code -> (gift_slug, text)`.
  2. Query all existing questions WHERE `question_code IN codes`.
  3. For each code:
     - If exists: optionally update text only if changed (log diff). Provide `--allow-text-update` flag (default: warn + skip).
     - If missing: insert new `Question(question_code=code, text=..., type=<likert or generic>)`.
  4. Flush, then link via `AssessmentTemplateQuestion` with deterministic `order` (1..72) using list index.
  5. Validate: count(question_codes) == 72 and all appear in template link table.
  6. Commit (unless `--dry-run`).
- Remove (or gracefully ignore) old text-based lookup path.
- Add `--verify-only` flag: run validations without mutating (ensures CI check).

## 8. Scoring & MAP Integrity (Forward Dependency)
- Future scoring service should import a single source MAP from a dedicated module (e.g. `app.core.spiritual_gifts_map`).
- That module should assert at import time that all listed codes exist in DB (fast fail on deployment drift).
- Seed script remains canonical for first insertion; MAP module is canonical for runtime mapping.

## 9. Edge Case: Pre-Existing Rows Without Codes (Fallback Procedure)
Only required if any environment already has text-only rows:
1. Temporarily add column nullable.
2. For each `(code, text)` in `QUESTION_ITEMS`:
   - Lookup row by exact `text`.
   - If found and `question_code IS NULL`: update with corresponding `code`.
   - If not found: insert new row with code & text.
3. After population: enforce uniqueness; ensure 72 distinct codes present.
4. ALTER COLUMN to `SET NOT NULL`.
5. Proceed with normal idempotent logic going forward.

## 10. Validation / QA Checklist
Item | Method | Pass Criteria
-----|--------|--------------
Migration applies | Alembic upgrade | Column present, unique constraint exists
Idempotent seeding | Run seed twice | Second run makes zero inserts/updates (unless text changed intentionally)
Drift detection | Run with `--verify-only` | Exits 0 and prints "All 72 questions present" message
Template linkage | Query link count | Exactly 72 rows for template/version
MAP coverage | Script validation | No missing/extra codes
Text change safety | Modify one text & run without flag | Warning emitted, no DB update
Text update allowed | Run with `--allow-text-update` | Text updated, log shows change
Dry run | Run with `--dry-run` | No persistent inserts after rollback

## 11. Rollback Plan
- If migration causes issues before production responses exist: downgrade migration (drops column), revert script changes, re-run old script (definitions only).
- If production responses existed (future case): do NOT drop column (data loss risk). Instead fix forward.

## 12. Risks & Mitigations
Risk | Impact | Mitigation
-----|--------|-----------
Accidental code typo | Orphaned MAP entry | Script validation + CI verify-only job
Future reordering of questions | Broken historical order assumptions | Order driven by list index; store explicit `order` (already) and never assume code implies order
Silent text edits | Analytics mismatch / meaning drift | Require `--allow-text-update` flag; audit log change set
Multiple scripts defining codes | Divergence | Single authoritative source; if needed, extract constants to `app/core/` module

## 13. Future Extensions (Not Now)
- Localization table keyed by `question_code` + `locale`.
- Question deprecation flag (soft retire old codes).
- Admin UI to view & compare question revisions.
- Export/import YAML for content governance.

## 14. Implementation Order (Actionable Sequence)
1. Create Alembic migration (nullable=False since fresh) & upgrade locally.
2. Refactor seed script to use `question_code` (add new flags).
3. Run: `python scripts/seed_spiritual_gifts.py --version 1 --file scripts/spiritual_gift_definitions_v1.json --seed-questions --publish --verify-only` (should pass pre-insert? adjust: verify-only after initial seed).
4. Run actual seed (no dry-run) to insert 72 questions.
5. Re-run with `--verify-only` to confirm idempotency.
6. (Optional) Commit MAP constants to a runtime module (`app/core/spiritual_gifts_map.py`).
7. Add lightweight test validating MAP ↔ DB integrity.
8. Proceed to implement scoring endpoint referencing MAP module.

## 15. Operational Notes
- Run this migration + seed before exposing the assessment in production UI.
- Avoid manual inserts—only seed script should create these rows.
- Keep codes stable; if semantics change materially create a *new* code (do not recycle).

## 16. Open Questions (Fill Before Finalizing)
- Column name: `question_code` vs `code`? (Recommend `question_code` for clarity.)
- Should we store `gift_slug` directly on `question`? (Likely no—keep separation; mapping lives in scoring/MAP module.)
- Do we need a `question_type` enum now? (Can defer; Likert logic currently UI-driven.)

## 17. Approval Checklist
- [ ] Stakeholder sign-off on naming & constraints
- [ ] Alembic migration merged
- [ ] Seed script updated & tested locally
- [ ] Verification run documented
- [ ] MAP module (if extracted) added & imported nowhere else yet

---
**End of Document**
