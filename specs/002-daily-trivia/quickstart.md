# Quickstart: Daily Trivia (backend 002)

How to prove the feature works. Shapes are defined in [contracts/daily-trivia-api.md](contracts/daily-trivia-api.md) and the rules in [data-model.md](data-model.md).

## Automated

```bash
pytest tests/test_daily_trivia.py -q
pytest -q                       # full suite must stay green
```

The tests mock Shopify and FCM, and freeze "now" to drive multi-day streaks.

## Dev environment

Prerequisites:
- the migration has been applied (`alembic upgrade head`, run by the migrate job before deploy);
- the dev database has approved beginner/challenger trivia questions;
- Shopify is either unconfigured (you get `DRYRUN-` codes) or pointed at the dev store.

1. **Same question for everyone.** Call `GET /trivia/daily/today` as two users with the same timezone. The `question` is identical and has no `correct_option`.
2. **Answer once.** Call `POST /trivia/daily/today/answer` with the returned `date`. The response includes `correct_option`, and `streak.current_streak` is 1. Posting again returns 409 `already_answered`.
3. **Midnight guard.** Post with yesterday's date. You get 409 `question_expired`.
4. **Timezone.** `PUT /users/me/timezone` with `Pacific/Kiritimati` succeeds and moves the user's `date` ahead. `Mars/Olympus` returns 422.
5. **Reward.** In the dev database, set a test user's streak row to `current_streak=44` and `last_answered_date=yesterday`, then answer. The response has `new_reward` (tier 45, status pending). Within seconds `GET /trivia/daily/streak` shows `active_reward` with a code, and the email and push arrive.
6. **Upgrade.** Set `current_streak=59`, answer, and confirm a 35% or 45% code. The 45-day reward is now `superseded`, and in the Shopify admin it is deactivated (skipped for dry-run codes).
7. **Cron.** Run:
   ```bash
   curl -X POST -H "X-Cron-Secret: $CRON_SECRET" $DEV/scheduled/daily-trivia
   ```
   during an hour when 9am falls in a test user's timezone. That user gets exactly one push. Running it again in the same hour reminds 0 users.
8. **Scheduler job (dev):**
   ```bash
   gcloud scheduler jobs create http daily-trivia-dev --schedule="0 * * * *" \
     --uri="$DEV/scheduled/daily-trivia" --http-method=POST \
     --headers="X-Cron-Secret=$CRON_SECRET" --location=us-central1
   ```
