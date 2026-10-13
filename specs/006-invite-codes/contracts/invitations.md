# Contract: Invitations (invite codes)

Base path: `/invitations`. All bodies are JSON. Errors use FastAPI's usual body: `{"detail": "<message>"}`.

`code` is always returned in display form, `XXXX-XXXX`: 8 characters from `23456789ABCDEFGHJKMNPQRSTUVWXYZ` with a dash in the middle. Clients may send it in any case, with or without the dash, and with any whitespace (internal or surrounding).

---

## POST `/invitations/redeem` (new)

An apprentice joins a mentor by entering an invite code.

**Auth**: signed in, role `apprentice` (`require_apprentice`).

**Request**
```json
{ "code": "K7QM-3XPR" }
```
`code`: string, required, 1–32 characters before normalizing.

**200 OK**: `InviteRedeemOut`
```json
{
  "message": "Invitation accepted, relationship created",
  "mentor_id": "uid_mentor",
  "mentor_name": "Marcus Lee",
  "relationship": "created"
}
```
`relationship` is one of `created`, `reactivated` or `already_active`.

**Errors**
| Status | `detail` | When |
|--------|----------|------|
| 401 | (auth default) | Not signed in |
| 403 | `Apprentice access required` | Signed-in user isn't an apprentice |
| 404 | `Invite code not found` | No invite has this code. Also used for malformed and revoked codes. |
| 400 | `This invitation has expired.` | Invite expired. Same text as accept-by-token. Clients tell expired and used apart by this exact `detail`. |
| 400 | `Invitation has already been accepted` | Already used, including losing a race |
| 422 | (validation default) | `code` missing or longer than 32 characters |
| 429 | `Too many invalid codes. Try again later.` | 10 or more failed attempts by this user in the last hour. Includes a `Retry-After` header (seconds). |

The 401, 403 and 422 responses aren't counted as attempts. 404, 400 and 200 are recorded.

---

## POST `/invitations/invite-apprentice` (changed, additive)

**Auth**: unchanged (`require_mentor`). **Request**: unchanged.

**200 OK**: new fields added. `message` is unchanged.
```json
{
  "message": "Invitation sent",
  "id": "inv_uuid",
  "code": "K7QM-3XPR",
  "expires_at": "2026-10-20T14:03:00"
}
```

---

## GET `/invitations/pending-invites` (changed, additive)

**Auth**: unchanged (`require_mentor`). Each `InviteOut` gains `"code": "K7QM-3XPR"`.

## GET `/invitations/apprentice-invites?email=` (changed, additive)

**Auth**: unchanged. Each item gains `"code"`.

`InviteOut.code` is declared `str | None` for schema safety. After the migration it is always set.

---

## POST `/invitations/accept-invite` (changed: now requires sign-in)

**Auth**: **now** signed in, role `apprentice` (`require_apprentice`). It used to have no auth.

**Request**
```json
{ "token": "uuid-token", "apprentice_id": "uid_apprentice" }
```
`apprentice_id` is now **optional**. If it's present, it must equal the signed-in user's ID. The apprentice is always the signed-in user.

**200 OK**: `InviteAcceptOut`, same body as today (`{"message": "Invitation accepted, relationship created" | "Invitation accepted, relationship reactivated"}`). An already-active pairing returns the reactivated message.

**Errors**
| Status | `detail` | When |
|--------|----------|------|
| 401 | (auth default) | Not signed in (**new**) |
| 403 | `Apprentice access required` | Not an apprentice. This used to be 404 `Apprentice not found`. |
| 403 | `You can only accept invitations for yourself` | `apprentice_id` given and isn't the caller (**new**) |
| 400 | `Invitation is invalid or expired` | Unknown token (unchanged) |
| 400 | `This invitation has expired.` | Expired (unchanged) |
| 400 | `Invitation has already been accepted` | Used (unchanged) |

**Compatibility**: released apps call this signed in, with their own ID, so they keep working. No minimum app version is needed (spec FR-010/FR-011).

---

## GET `/invitations/accept-invitation?token=` (public HTML, changed)

Still public. The "Invitation Token" box is replaced by an "Invite code" box that shows `code` in display form, with the line "Open the T[root]H app and enter this code to join your mentor."

## Invitation email (`account/invitation.html`)

Shows the code in display form above the existing button, with the same instruction. The context gains an optional `code`; the block is left out when it's missing.

---

## Frontend consumers

The `trooth_assessment` spec for invite codes and social-first login links this file. It needs:
- `redeemInviteCode(code)` → `POST /invitations/redeem`. Show the `detail` text for 400/404/429.
- Mentor invite screen: read `code` from `invite-apprentice` and `pending-invites`, with Copy and Share buttons.
