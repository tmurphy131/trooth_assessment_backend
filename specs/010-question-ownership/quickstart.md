# Quickstart: Validate Question Ownership

## 1. Tests
```bash
.venv/bin/python -m pytest tests/test_question_ownership.py tests/test_access_hardening.py -q
TEST_POSTGRES_URL=postgresql://localhost/trooth_fk .venv/bin/python -m pytest tests/test_question_ownership_postgres.py -q   # backfill
.venv/bin/python -m pytest -q   # full suite, about 15 s
```

## 2. Dev (after `/deploy-dev`, which runs the migration first)
1. **Mentor, own questions:** create a custom question with a correct answer in template management. It attaches, the template shows the correct answer, and editing works.
2. **Mentor, Master:** view the Master template. All answers show as not correct. Clone it, then view the clone: still no answers. The screen doesn't crash.
3. **Apprentice of that mentor:** take the cloned assessment. Scoring and the report work as usual.
4. **Mentor taking an assessment themselves:** the questions show no correct answers.
5. **Mentor reviewing a linked apprentice's submission:** correct answers are shown.

## 3. After the prod migration
Spot-check that mentor custom questions were attributed:
```sql
SELECT count(*) FILTER (WHERE created_by IS NOT NULL) AS owned, count(*) AS total FROM questions;
```
Expected: `owned` is greater than 0 if mentors have custom questions, and Master/spiritual-gifts questions are still NULL.
