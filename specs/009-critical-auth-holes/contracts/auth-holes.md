# Contract: Critical Authorization Holes

## `POST /users/`: signup (changed behavior, same shape)

**Auth**: Firebase ID token (`Authorization: Bearer <id_token>`), as today.

**Request** (unchanged schema `UserCreate`):
```json
{ "uid": "…", "email": "…", "name": "…", "role": "apprentice" | "mentor" | "admin" }
```
`uid` and `email` in the body are **ignored** for lookup and storage. Identity comes from the token.

**Responses**:
| Status | When | Body |
|---|---|---|
| 200 | New account created, or an existing account (by token uid) returned | `UserOut` |
| 200 | Legacy re-link with a verified email | `UserOut` |
| 400 | Token has no email | `{"detail": "Your sign-in has no email address"}` |
| 403 | `role=admin` for a new account | `{"detail": "This role can't be chosen at sign-up"}` |
| 409 | An account with the token's email exists under another identity and the email isn't verified, or the re-link is blocked by existing data | `{"detail": "We couldn't finish setting up your account. Verify your email address, then try again."}` (generic, per FR-013; doesn't confirm an account exists) |
| 401 | Missing or invalid token | unchanged |

Released apps swallow errors whose text contains `409`, `exist` or `Already` (`signup_screen.dart:100`, `role_selection_screen.dart:58`). The client error string includes the status code, so this 409 is still treated as harmless.

**No longer possible**: changing `role` or `id` of an existing account; becoming `admin`; acting on an account by naming its email.

## `get_current_user` (all signed-in routes)
The fallback re-link by email now requires `email_verified: true`. Otherwise the response is the existing 404 "User not found. Please complete registration first."

## Removed routes
| Route | Replacement | Callers in released apps |
|---|---|---|
| `POST /agreements/{agreement_id}/sign/parent` | `POST /agreements/public/{token}/sign` (emailed parent link) | None. `parentSignAgreement` (`lib/services/api/invites_agreements.dart:202`) is never invoked |
| `POST /users/assign-apprentice` | Invitations (`/invitations/accept-invite`), invite codes (`/invitations/redeem`, spec 006), signed agreements | None. `assignApprentice` (`lib/services/api/users_mentorship.dart:47`) is never invoked and sends the wrong format |

After removal, both return the framework's 404 or 405. `POST /users/assign-apprentice` returns **405**, because the path still matches `GET /users/{user_id}`. `POST /agreements/{id}/sign/parent` returns 404 or 405 depending on which remaining routes share the prefix. Both are refusals with no side effects. Nothing in the app depends on them, so no minimum app version is needed.

## Frontend
No spec needed. Optional cleanup: delete the two unused client functions above.
