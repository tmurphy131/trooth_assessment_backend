# Quickstart: validating invite codes

Endpoint shapes and errors are in [contracts/invitations.md](contracts/invitations.md). Fields are in [data-model.md](data-model.md).

## 1. Automated (required before merge)

```bash
cd trooth_assessment_backend
ENV=test pytest tests/test_invite_codes.py tests/test_invite_code_helpers.py tests/test_invitations.py tests/test_email.py -q
ENV=test pytest -q            # full suite must pass (Principle VIII)
```

`tests/test_invite_codes.py` must cover the table below. `tests/test_invite_code_helpers.py` covers the pure helpers (generate, normalize, format) and checks that `app.services.invite_codes` imports no models.

| Scenario | Expected |
|----------|----------|
| Mentor creates an invite | 200; `code` matches `^[2-9A-HJKMNP-Z]{4}-[2-9A-HJKMNP-Z]{4}$`; same code in `pending-invites` |
| Apprentice redeems in canonical form | 200, `relationship: created`; `MentorApprentice` row exists; invite `accepted` |
| Redeem `k7qm3xpr` / `" K7QM-3XPR "` | 200 (normalization) |
| Apprentice email ≠ invited email | 200 (the hidden-email case) |
| Redeem again | 400 already accepted |
| Expired invite | 400 expired |
| Unknown or malformed code | 404 |
| Mentor or admin calls redeem | 403 |
| Apprentice calls `pending-invites` | 403 |
| `apprentice-invites?email=` someone else's email | 403 |
| No auth | 401 |
| `code` missing or 33 characters long | 422 |
| Simultaneous redemption (invite accepted between lookup and accept) | 400 already accepted, no pairing created |
| Redeem logging (`caplog`) | `invite.redeem` logged with outcome; raw code not in log text |
| 10 failed attempts, then an 11th (even a valid code) | 429 with `Retry-After`; succeeds again once failures are older than 1h (move `created_at` back in the test) |
| Previously inactive pairing | 200, `relationship: reactivated`, no duplicate row |
| accept-invite without auth | 401 |
| accept-invite as A with `apprentice_id` = B | 403, nothing changes |
| accept-invite as A with own ID or none | 200 |
| Account deletion | removes the user's `invite_code_attempts` rows |
| Invitation email render | HTML contains the formatted code (SendGrid mocked) |

## 2. Migration (dev database)

```bash
alembic upgrade head        # via the Cloud Run migrate job for dev
```
Check: `SELECT count(*) FROM apprentice_invitations WHERE code IS NULL;` returns 0, and the codes are unique. `alembic downgrade -1` followed by `upgrade head` runs cleanly.

## 3. End to end on dev

1. As a mentor in the app (or with curl and a dev ID token), invite `invitee+test@example.com`. Note the `code`.
2. Open `/invitations/accept-invitation?token=…` from the email. The page shows the code and no raw token.
3. Sign in as a different apprentice account (ideally Apple with Hide My Email). Call `POST /invitations/redeem` with the code. Expect 200.
4. The mentor dashboard lists the apprentice, and the apprentice sees their mentor.
5. Redeem the same code again. Expect 400 "already been accepted".
6. Timing (target p95 under 300 ms): time 5 successful redeems, using 5 invites and 5 different apprentices, plus 9 unknown-code redeems from one other apprentice. Don't go over 9 failures for any one user, or the rate limit (429) will skew the results.
7. Older app build (installed from the store or TestFlight): accept an invite from the invites list. It still succeeds.
