# Contract: Agreements and gift seats by apprentice account (spec 007)

Errors use FastAPI's usual body `{"detail": "..."}`. Only the changes are listed; everything else matches today's API.

---

## POST `/agreements` (changed, additive)

**Auth**: unchanged (`require_mentor`).

**Request**: `apprentice_id` is **new and optional**, and `apprentice_email` becomes **optional**. At least one of the two is required.

```json
{
  "template_version": 1,
  "apprentice_id": "uid_apprentice",
  "apprentice_name": "Jordan",
  "apprentice_is_minor": false,
  "parent_required": false,
  "parent_email": null,
  "fields": { "...": "..." }
}
```

- **With** `apprentice_id`: the apprentice must have an **active** connection with the calling mentor. The stored `apprentice_email` becomes the account's email (lowercased). `apprentice_name` defaults to the account name. Any `apprentice_email` sent alongside is ignored.
- **Without** `apprentice_id`: today's behavior (email required).

**200**: `AgreementOut`, unchanged shape. `apprentice_id` is now filled in when created by ID.

**Errors (new)**

| Status | `detail` | When |
|--------|----------|------|
| 422 | (validation) | Neither `apprentice_id` nor `apprentice_email` sent |
| 403 | `This apprentice is not connected to you` | `apprentice_id` isn't an apprentice with an active connection to the mentor |

---

## POST `/agreements/{id}/sign/apprentice` (changed: wider access)

The signer may sign when the agreement is **tied to their account**, or when it's tied to no account **and** its email equals theirs. It's still 403 `Not authorized to sign` otherwise, including an agreement tied to a different account. Status codes and responses are otherwise unchanged.

---

## Side effect: POST `/invitations/redeem` and POST `/invitations/accept-invite` (spec 006)

There's no change to the request or response. On success, the mentor's agreements addressed to the **invitation's email** that aren't tied to an account yet become tied to the accepting apprentice. Reads such as `GET /agreements/my` then include them.

---

## Unchanged reads (they now cover agreements tied by account)

`GET /agreements/my`, `GET /agreements/{id}`, `GET /apprentice/agreements/pending`, `POST /agreements/{id}/request-resend-parent`, `POST /agreements/{id}/request-reschedule`, and `POST /apprentice/mentor/revoke` (blocked while an agreement is pending). Each already matches by **account ID or email**.

---

## Gift seats

### POST `/mentor/seats/purchase` and POST `/mentor/seats/{seat_id}/assign` (stricter)

When `apprentice_id` is sent, the apprentice must have an **active** connection with the mentor. Before, an ended connection was accepted.
- `assign`: a non-connected apprentice gets 403 `This apprentice is not linked to you`, the same as today for never-connected apprentices.
- `purchase`: the ID is ignored, the same as today for never-connected apprentices. The seat stays unassigned unless an `apprentice_email` is also sent and matches an apprentice account; that existing email path is unchanged by this spec.

### POST `/apprentice/redeem-code` (stricter)

**Auth**: now `require_apprentice`. Mentor and admin accounts get **403** `Apprentice access required`. The request and response (`success`, `message`, ...) are unchanged.

---

## Frontend consumers

The matching frontend spec (`trooth_assessment`) links this file. It needs:
- **Mentor agreement screen:** pick a connected apprentice (from the existing mentor apprentices list) and send `apprentice_id`; keep email entry for apprentices who aren't connected yet.
- **Apprentice "Redeem gift code" screen:** `POST /apprentice/redeem-code`. Show the result from the `success` boolean. Handle 403 by status code.
