# Quickstart: Validating Trivia Integrity

## Automated

```bash
cd trooth_assessment_backend
pytest tests/test_trivia_session.py tests/test_trivia_challenge_gate.py tests/test_trivia_competition.py -q
pytest -q          # full suite must pass (Principle VIII)
```

Expected coverage:

| Scenario | Expected |
|---|---|
| Start, then answer correctly ×N | Score and streak follow 100 × multiplier. No `correct_option` in any `question`. |
| Answer the wrong `question_id` | 400, state unchanged |
| Retry the last answer | 200, same state, not graded twice |
| Answer after 33 s (clock patched) | `timed_out=true`, graded wrong |
| Wrong answer with no token | `finished`, one score row with `verified=true` |
| 10 correct, then wrong, then `grace use=true` | Token spent, streak kept, next question served |
| Grace after the deadline | `finished` |
| Answer or grace on a finished game | 409 |
| Another user's session | 404 |
| `finish` twice | Same result, one score row |
| Start while one is unfinished | Old one finished and recorded |
| Old submit with flag on | 200, `verified=false`, not in competition standings |
| Old draw or submit with flag off | 426, nothing recorded |
| Free user creates a challenge | 403 `premium_required`, no challenge row |
| Premium user challenges a free user | Free user can accept and answer to completion |
| Challenge answer for the wrong question | 400 |

## Manual on dev (after `/deploy-dev`; the migration runs first)

1. Get a dev ID token for a test account and set `API=https://trooth-discipleship-api-dev.onlyblv.com`.
2. `curl -X POST $API/trivia/single/start -H "Authorization: Bearer $T" -H 'Content-Type: application/json' -d '{"category":"random","difficulty":"challenger"}'`. Confirm there is no `correct_option` anywhere in the body.
3. Answer with the returned `question.id`. Then send the same request with another ID and expect 400.
4. Wait more than 33 s before answering and expect `timed_out: true`.
5. With a free account, `POST $API/trivia/challenges` and expect 403 `premium_required`.
6. Deploy dev with `TRIVIA_LEGACY_SINGLE_ENABLED=false`. `GET $API/trivia/questions/draw?category=random&difficulty=beginner` should return 426. Set it back to `true` until the app is released.

## Prod cutover

1. Deploy the backend to prod with the flag unset (the old flow stays on).
2. Release app 2.2.0 and wait until it's live in both stores.
3. Add `TRIVIA_LEGACY_SINGLE_ENABLED=false` to the `--set-env-vars` list in `deploy-prod` and redeploy. Do this before 2026-11-01.
4. Check `GET /trivia/competition` still loads, and that the old draw endpoint returns 426.
