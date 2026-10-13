# Quickstart: validating spec 007

See [contracts/api.md](contracts/api.md) for shapes and errors, and [data-model.md](data-model.md) for the rules.

## 1. Automated (required before merge)

Run on the pinned versions (FastAPI 0.143.0 / Starlette 1.8.0, Python 3.11 venv):

```bash
ENV=test pytest tests/test_connected_apprentice_linking.py tests/test_agreements.py tests/test_invite_codes.py tests/test_subscription_security.py -q
ENV=test pytest -q
```

`tests/test_connected_apprentice_linking.py` must cover:

| Scenario | Expected |
|----------|----------|
| Mentor creates an agreement with a connected apprentice's ID | 200; `apprentice_id` set; `apprentice_email` = account email |
| Create by ID for an apprentice whose connection has ended | 403 |
| Create by ID for an unconnected apprentice, or a non-apprentice ID | 403 |
| Create with neither ID nor email | 422 |
| Create by email only (old path) | 200; `apprentice_id` empty, as today |
| An agreement tied by ID whose email differs from the account: `/agreements/my`, `GET /agreements/{id}`, `/apprentice/agreements/pending` | Included / 200 |
| The same agreement: in-app sign | 200 |
| Agreement tied to account X; Y with the same email signs | 403 |
| Pending tied agreement blocks `POST /apprentice/mentor/revoke` | 409, as today |
| Mentor has untied agreements for E; apprentice redeems an invite addressed to E | Those agreements are now tied to the apprentice; they appear in `/agreements/my` |
| Another mentor's untied agreement for E | Not attached |
| An agreement already tied to another account | Not changed |
| Accept by token (`accept-invite`) | Attaches the same way |
| Assign a seat by ID to an apprentice whose connection has ended | 403 |
| Purchase-confirm with an ID whose connection has ended (no email sent) | Seat stays unassigned |
| Purchase-confirm with an ID whose connection is active | Seat assigned to that apprentice |
| Apprentice calls `POST /agreements` | 403 |
| Tied agreement: request-resend-parent / request-reschedule as the apprentice | Not 403 |
| Gift code redeemed by a mentor account | 403; seat stays unredeemed |
| Gift code redeemed by an apprentice | 200 `success: true`; log has no emails (`caplog`) |

## 2. Manual on dev

1. Connect a mentor and an apprentice (redeem an invite code). The apprentice account should use a different email from the invite.
2. As the mentor, `POST /agreements` with `apprentice_id`, then submit it. As the apprentice, the app's agreements list shows it; sign it in the app and expect 200.
3. As a mentor, invite `newperson+test@example.com` **and** create an agreement for the same email. Sign up a different-email apprentice and redeem the code. `GET /agreements/my` includes that agreement.
