# Data Model: Link Agreements and Gift Seats to Apprentice Accounts

**No schema changes and no migration.** Every field used already exists.

## Agreement (`agreements`, existing)

| Field | Use in this feature |
|-------|---------------------|
| `apprentice_id` (nullable FK users.id) | Now set **at creation** when the mentor picks a connected apprentice (FR-001), or **when an invite is accepted** (FR-004). Before, it was only set at signing. |
| `apprentice_email` (not null) | Still required in storage. When created by ID it's the **account's** email, lowercased. Otherwise the typed email, as today. |
| `apprentice_name` | Payload name, else the account name when created by ID. |

**Rules**
- Tie-once: after `apprentice_id` is set, nothing in this feature changes it. Attaching only updates rows where `apprentice_id IS NULL`.
- Who may sign in the app: `apprentice_id == signer.id`, **or** (`apprentice_id IS NULL` **and** `apprentice_email == signer.email`).
- Attaching on invite acceptance: `mentor_id == invitation.mentor_id AND apprentice_id IS NULL AND lower(apprentice_email) == lower(invitation.apprentice_email)`.

## MentorApprentice (`mentor_apprentice`, existing)

"Active connection" means a row `(mentor_id, apprentice_id)` with `active = true`. This is now the single rule for agreement-by-ID and gift-seat-by-ID (`has_active_connection`).

## MentorPremiumSeat (`mentor_premium_seats`, existing)

Unchanged. Gifting by ID now needs an active connection. Redeeming a code needs an apprentice account.
