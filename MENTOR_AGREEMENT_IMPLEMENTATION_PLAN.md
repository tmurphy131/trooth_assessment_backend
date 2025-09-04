# Mentor–Apprentice Agreement Implementation Plan

Status: APPROVED DESIGN (not implemented)
Last Updated: 2025-09-02

## 1. Confirmed Requirements
- Versioned agreement template system (track template revisions).
- Apprentice must sign (typed full name + timestamp) before relationship becomes active.
- Mentor may mark apprentice as a minor (under 17). If so:
  - Parent email must be provided.
  - Mentor can toggle whether parent signature is required.
  - Parent receives an acknowledgment email (and signs if required).
- Relationship (mentor ↔ apprentice link) is created ONLY after all required signatures collected.
- Fields mentor can customize per agreement; minimal mandatory fields:
  - meeting_location (required)
  - meeting_duration_minutes (required, > 0)
  - Optional: meeting_day, meeting_time, meeting_frequency, start_date, additional_notes.
- Ability to revoke an agreement (soft revoke) after creation (state transition + audit trail).
- Immutable snapshot of rendered agreement (content + SHA256 hash) stored.
- Ability to list template versions and use a specific version when creating a new agreement.
- Parent signature is optional unless mentor explicitly requires it.

## 2. Data Model Additions
### 2.1 Agreement Templates
`agreement_templates`
| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| version | INT | Monotonic, unique, sequential |
| markdown_source | TEXT | Raw template with tokens (e.g., `{{meeting_location}}`) |
| created_at | TIMESTAMP | Default now |
| is_active | BOOL | Only one (or several) active at a time |
| supersedes_version | INT NULL | Link chain |
| author_user_id | FK users.id NULL | Audit |
| notes | TEXT NULL | Changelog / rationale |

### 2.2 Agreements (Instances)
`agreements`
| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| template_version | INT | FK agreement_templates.version |
| mentor_id | FK users.id | Must have role=mentor |
| apprentice_id | FK users.id NULL | Resolved *after* apprentice account creation (could be null initially if invitation not accepted yet) |
| apprentice_email | VARCHAR | For pre-account phase |
| status | ENUM | `draft`, `awaiting_apprentice`, `awaiting_parent`, `fully_signed`, `revoked`, `expired` |
| apprentice_is_minor | BOOL | Derived from mentor toggle |
| parent_required | BOOL | If true, parent signature required |
| parent_email | VARCHAR NULL | Required if apprentice_is_minor |
| fields_json | JSON | Custom field values (meeting_location, duration, etc.) |
| content_rendered | TEXT | Fully substituted markdown (or HTML) |
| content_hash | CHAR(64) | SHA256(content_rendered) |
| apprentice_signature_name | VARCHAR NULL | Typed name |
| apprentice_signed_at | TIMESTAMP NULL | Timestamp |
| parent_signature_name | VARCHAR NULL | Typed name |
| parent_signed_at | TIMESTAMP NULL | Timestamp |
| revoked_at | TIMESTAMP NULL | Soft revoke |
| revoked_by | FK users.id NULL | Actor |
| created_at | TIMESTAMP | Default now |
| activated_at | TIMESTAMP NULL | When relationship created |

### 2.3 Agreement Tokens (for secure signing links)
`agreement_tokens`
| Column | Type | Notes |
| token | UUID | PK |
| agreement_id | FK agreements.id | |
| token_type | ENUM | `apprentice`, `parent` |
| expires_at | TIMESTAMP | 7 days default |
| used_at | TIMESTAMP NULL | Set once used |
| created_at | TIMESTAMP | |

### 2.4 Relationship Creation
Existing `MentorApprentice` creation moves to post-signature hook:
- Trigger when agreement transitions to `fully_signed`.
- Link apprentice_id + mentor_id (if not already existing).

### 2.5 Optional Audit Log
`agreement_events` (future): event_type, actor_user_id/null (for parent), timestamp, metadata JSON (state diffs, hash).

## 3. Template Token Strategy
Supported tokens in the template (safe substitutions):
- `{{meeting_location}}` (required)
- `{{meeting_duration_minutes}}` (required)
- `{{meeting_day}}`
- `{{meeting_time}}`
- `{{meeting_frequency}}`
- `{{start_date}}`
- `{{mentor_name}}`
- `{{apprentice_name}}`
- `{{additional_notes}}`

Missing optional tokens replaced with an empty string. Validation ensures required ones are present in `fields_json` before rendering.

## 4. Lifecycle & State Machine
```
mentor drafts -> draft
mentor submits -> awaiting_apprentice
apprentice signs -> (if parent_required) awaiting_parent ELSE fully_signed
parent signs (if required) -> fully_signed
fully_signed -> relationship created + activated_at set
mentor/admin revoke -> revoked (cannot revert)
(optional) auto expire (no signature within X days) -> expired
```
Invalid transitions produce 409 Conflict.

## 5. Endpoints (Proposed)
| Method | Path | Purpose | Auth |
|--------|------|---------|------|
| GET | /agreements/templates | List active template versions | Mentor/Admin |
| POST | /agreements/templates | Create new template version | Admin only |
| GET | /agreements/templates/{version} | Fetch template details | Mentor/Admin |
| POST | /agreements | Create agreement draft (template_version + fields) | Mentor |
| GET | /agreements/{id} | Get agreement (ownership enforced) | Mentor / Apprentice (if email match / user link) |
| POST | /agreements/{id}/submit | Move draft -> awaiting_apprentice (validates required fields) | Mentor |
| GET | /agreements/{id}/public/{token} | Public view via token (no PII edit) | Token |
| POST | /agreements/{id}/sign/apprentice | Apprentice sign (token or auth) | Apprentice/Token |
| POST | /agreements/{id}/sign/parent | Parent sign (token) | Parent token |
| POST | /agreements/{id}/revoke | Revoke (mentor or admin) | Mentor owner / Admin |
| GET | /agreements/{id}/integrity | Return stored hash + recomputed hash | Mentor/Admin |

Integration with existing invitation flow (optional phase):
- Add parameter `create_agreement=true` to `/invitations/invite-apprentice` returning {invitation_id, agreement_id, apprentice_token_url}.

## 6. Rendering & Hashing
- Upon draft submit: load template by version, substitute tokens, produce `content_rendered`.
- Compute `content_hash = sha256(content_rendered.encode())`.
- Store both; never regenerate dynamically after that (immutability guarantee).

## 7. Validation Rules
| Rule | Enforcement |
|------|-------------|
| meeting_location required | 400 if missing |
| meeting_duration_minutes int > 0 | 400 if invalid |
| apprentice_email valid format | 400 |
| parent_email required if apprentice_is_minor | 400 |
| parent_required implies parent_email present | 400 |
| Cannot submit draft without required fields | 409 |
| Cannot sign after revoke/expire | 409 |
| Duplicate signature attempt | 409 |

## 8. Email Flows
### Apprentice Invitation / Signature
- Apprentice token email: link -> agreement view -> sign form (typed name + confirm checkbox).
- After apprentice sign (and if parent not required): send confirmation email to mentor & apprentice.

### Parent Acknowledgment
- If parent_required or apprentice_is_minor: send parent token email with link to view agreement + sign (or simple acknowledgment if not required to sign).

### Revocation
- Send notice to apprentice (and parent if existed) with reason (optional free-text reason captured in revoke payload).

## 9. Revocation Semantics
- Endpoint accepts optional `reason` (stored in events table metadata). 
- Sets status=revoked, revoked_at, revoked_by.
- Relationship (if already created) optionally remains or is disabled (Decision: DISABLE link → remove MentorApprentice row or mark inactive? Recommend add `active` bool column to `MentorApprentice` to avoid historic data loss.)

## 10. Security & Authorization
- All agreement endpoints enforce ownership: mentors can access only their agreements; apprentices only those where apprentice_email matches their user email or apprentice_id matches.
- Token-based endpoints use `agreement_tokens` with one-time (or single-purpose) semantics; mark `used_at` for signing but still allow viewing until expiration.
- No PII leaks: parent email not returned to unauthorized roles.

## 11. Logging & Audit
Log (structured):
- agreement.create (id, mentor_id, template_version)
- agreement.render (id, hash)
- agreement.submit (id)
- agreement.sign.apprentice / .parent (id, signer, elapsed_from_creation)
- agreement.activate (relationship_id)
- agreement.revoke (id, actor, reason)
- agreement.integrity.check (id, match=true/false)

## 12. Migration Outline (Alembic)
1. Create `agreement_templates`.
2. Insert initial version (v1) using current generic markdown.
3. Create `agreements`.
4. Create `agreement_tokens`.
5. (Optional) Add `active` column to `mentor_apprentice` for revocation side effects.

## 13. Frontend (High-Level)
Mentor Flow:
1. Open “Create Agreement” form (fields + minor toggle + parent signature required toggle).
2. Preview rendered text (client can render markdown) – optional.
3. Submit -> shows status awaiting apprentice.
4. Dashboard row with status + actions (copy link, revoke).

Apprentice Flow:
1. Click invite link -> agreement view.
2. Fill typed name, check “I agree”, submit.
3. If parent required: show message “Pending parent acknowledgment.”

Parent Flow:
1. Receives email -> view link -> typed name (if required) or simple acknowledgment button.

Status Badges: draft, awaiting you, awaiting parent, active, revoked.

## 14. Edge Cases & Handling
| Edge | Handling |
|------|----------|
| Mentor edits after submit | Disallow (must revoke & recreate) |
| Parent email typo | Mentor revokes + recreates agreement |
| Expired tokens | Provide endpoint to regenerate new token (invalidating old) |
| Apprentice already linked to mentor | Reject activation if relationship exists & active (409) |
| Multiple active agreements | Optionally restrict one active per pair (enforce at activation) |

## 15. Optional Future Enhancements
- PDF generation (wkhtmltopdf or external service).
- Digital fingerprint (store hash on external notarization service).
- Agreement renewal workflow upon new template major version.
- Multi-language templates with locale field.

## 16. Implementation Phases
Phase 1: Schema + template insert + create agreement (draft -> submit) + apprentice sign -> activation.
Phase 2: Parent flow (minor logic + parent tokens + signature).
Phase 3: Revocation + audit events + integrity endpoint.
Phase 4: UI polish (preview, status filters) + renewal support.
Phase 5: PDF export & notifications refinement.

## 17. Estimated Effort
| Phase | Estimate |
|-------|----------|
| 1 | 1–1.5 days |
| 2 | 1 day |
| 3 | 0.5 day |
| 4 | 1 day |
| 5 | 0.5–1 day |
Total: ~4–5 developer days (backend + frontend) initial.

## 18. Decision Resolutions
All previously open minor decisions have been finalized:

| Item | Decision | Notes |
|------|----------|-------|
| Relationship disable strategy | Inactive flag (retain row) | Add `active BOOLEAN DEFAULT 1` to `mentor_apprentice`; set to 0 on agreement revocation. Historical links preserved. |
| Token expiry duration | 7 days | `expires_at = created_at + interval '7 days'` for apprentice & parent tokens. Regeneration resets window. |
| Parent token resend | Allowed | New endpoint to regenerate parent token if not yet signed; old token invalidated. |
| Rate limiting | Use existing global limiter | No special override; signing endpoints inherit middleware limits. |

### 18.1 New Endpoint (Parent Token Resend)
`POST /agreements/{id}/resend/parent-token`
Auth: Mentor owner OR Admin. Preconditions: agreement.status in (`awaiting_parent`), parent_required true, parent_signed_at is null. Action: generate new parent token (invalidate prior by setting `used_at` or deleting), send email, log `agreement.parent_token_resent` event.

### 18.2 Revocation Behavior Clarification
On revoke:
1. Set agreement.status = revoked, revoked_at, revoked_by.
2. If relationship already active: set `mentor_apprentice.active = 0` (do not delete).
3. Emit `agreement.revoke` event with reason (if provided).

### 18.3 Integrity & Resend Interaction
Resending parent token does not alter `content_rendered` nor `content_hash`; only token row changes. Audit keeps both prior and new token records (old marked expired or used_at set with reason="superseded").

## 19. Ready for Build Checklist
- [x] Confirm relationship disable choice (inactive flag)
- [x] Confirm token expiry (7 days)
- [x] Decide if mentor can resend parent token (yes)
- [ ] Provide initial markdown template file path for version seeding (default: `MENTOR_AGREEMENT.md`)
- [ ] Finalize allowed optional fields list displayed in UI (current draft OK)
- [ ] Add migration for agreement + tokens + active flag
- [ ] Implement Phase 1 endpoints
- [ ] Write backend tests (creation, submit, apprentice sign, activation, integrity)

---
This plan reflects all confirmed decisions. No code has been changed yet.
