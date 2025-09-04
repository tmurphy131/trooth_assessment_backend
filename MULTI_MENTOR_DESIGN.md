# Multi-Mentor Support Design (Future Enhancement)

> Status: PROPOSED (Not Implemented)  
> Last Updated: 2025-09-02  
> Owner: (TBD)  

## 1. Purpose
Enable an apprentice to be assigned to multiple mentors simultaneously while preserving security boundaries, template ownership, assessment integrity, and clarity of responsibility.

## 2. Current State (Single Mentor Model)
- Relationship: Implicit or explicit single mentor per apprentice (via `mentor_apprentice` link table or equivalent constraint usage).
- Template visibility:
  - Apprentices: Master assessment + published templates from *their* sole mentor.
  - Mentors: Their own templates (draft + published) + master template.
- Assessments: Attributed to apprentice; mentor context inferred from the single relationship.
- Authorization checks assume ONE mentor → apprentice link.

## 3. Goals for Multi-Mentor Mode
| Goal | Description |
|------|-------------|
| G1 | Allow >1 mentor per apprentice | 
| G2 | Preserve template privacy (mentors never see other mentors' drafts) |
| G3 | Apprentice sees published templates from *all* assigned mentors + master |
| G4 | Track which mentor context applies for assessments, feedback, notes |
| G5 | Avoid accidental privilege expansion / data leakage |
| G6 | Minimal disruption to existing mobile clients (additive API evolution) |

## 4. Data Model Changes
### 4.1 New Join Table (if not already normalized)
`apprentice_mentors` (or reuse `mentor_apprentice` with adjustments):
| Column | Type | Notes |
|--------|------|-------|
| id | UUID (pk) | New primary key (or composite key) |
| apprentice_id | FK users.id | role=apprentice enforced at app layer |
| mentor_id | FK users.id | role=mentor enforced |
| relationship_type | TEXT NULL | (e.g., "primary", "spiritual", "skills") optional |
| active | BOOL DEFAULT TRUE | Soft detach |
| created_at | TIMESTAMP | auditing |
| added_by | FK users.id | who created relationship |

Unique Composite: `(apprentice_id, mentor_id)`

### 4.2 Deprecate Single-Mentor Assumptions
Remove any implicit single reference (e.g., cached `mentor_id` on apprentice) after migration grace period.

### 4.3 Assessment Attribution (Optional Enhancement)
Add `mentor_id` on `assessments` table to record mentor overseeing that assessment *contextually* (if needed for filtering / accountability). Alternative: derive via relationship snapshot at creation time (store in JSON metadata column).

### 4.4 Notes / Drafts / Feedback
Any entity that currently assumes one mentor should gain either:
- `mentor_id` column (denormalized responsibility)
- OR multi-mentor neutral design (only apprentice-owned).  
Decision depends on whether mentors create private artifacts.

## 5. Migration Plan
### Phase 0 – Inventory & Toggle
- Add feature flag: `MULTI_MENTOR_ENABLED=false`.

### Phase 1 – Schema
1. Create join table (`apprentice_mentors`).
2. Backfill rows using existing relationships.
3. Add DB indexes:
   - `IX_apprentice_mentors_apprentice_id`
   - `IX_apprentice_mentors_mentor_id`
   - Unique composite index to prevent duplicates.

### Phase 2 – Read Path Dual Support
- Update read queries to join through new table, *but* fallback to old assumptions if feature flag disabled.

### Phase 3 – Write Path Switch
- All assignment/removal now manipulate join table.
- Deprecate any write to legacy single-mentor field.

### Phase 4 – Clean-Up
- Remove deprecated column/logic after a release window.

### Alembic Migration Sketch
```python
# versions/xxxx_multi_mentor_support.py
from alembic import op
import sqlalchemy as sa
import uuid

revision = 'xxxx_multi_mentor'
down_revision = 'prev'


def upgrade():
    op.create_table(
        'apprentice_mentors',
        sa.Column('id', sa.String(), primary_key=True, default=lambda: str(uuid.uuid4())),
        sa.Column('apprentice_id', sa.String(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('mentor_id', sa.String(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('relationship_type', sa.String(), nullable=True),
        sa.Column('active', sa.Boolean(), server_default=sa.text('1'), nullable=False),
        sa.Column('added_by', sa.String(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_unique_constraint('uq_apprentice_mentor_pair', 'apprentice_mentors', ['apprentice_id', 'mentor_id'])
    op.create_index('ix_apprentice_mentors_apprentice', 'apprentice_mentors', ['apprentice_id'])
    op.create_index('ix_apprentice_mentors_mentor', 'apprentice_mentors', ['mentor_id'])

    # Optional backfill example (pseudo-code comment):
    # conn = op.get_bind()
    # rows = conn.execute(sa.text('SELECT apprentice_id, mentor_id FROM legacy_relationships'))
    # for r in rows: insert if not exists


def downgrade():
    op.drop_index('ix_apprentice_mentors_apprentice', table_name='apprentice_mentors')
    op.drop_index('ix_apprentice_mentors_mentor', table_name='apprentice_mentors')
    op.drop_constraint('uq_apprentice_mentor_pair', 'apprentice_mentors', type_='unique')
    op.drop_table('apprentice_mentors')
```

## 6. API Surface Changes
### New/Adjusted Endpoints
| Endpoint | Method | Purpose | Notes |
|----------|--------|---------|-------|
| `/apprentices/{id}/mentors` | GET | List assigned mentors | Auth: apprentice self OR any assigned mentor OR admin |
| `/apprentices/{id}/mentors` | POST | Assign mentor | Body: `{mentor_id, relationship_type?}` |
| `/apprentices/{id}/mentors/{mentor_id}` | DELETE | Unassign mentor | Soft deactivate maybe |
| `/mentors/{id}/apprentices` | GET | List apprentices for mentor | Already similar; update query |

### Payload Additions
- Assessment creation: optional `mentor_id` acting context (validate membership).
- Template listing for apprentice: no change in URL; logic broadens mentor set aggregation.

### Versioning Strategy
- Keep existing endpoints stable; add new relationship management endpoints.
- Document in OpenAPI & mobile integration guide.

## 7. Authorization Logic Updates
Replace patterns like:
```python
rel = db.query(MentorApprentice).filter_by(apprentice_id=aid, mentor_id=current_user.id).first()
if not rel: deny
```
With set membership check:
```python
exists = db.query(apprentice_mentors).filter_by(apprentice_id=aid, mentor_id=current_user.id, active=True).first()
```
Admin bypass unchanged.

## 8. Template Visibility Logic (Apprentice)
Current (simplified):
```sql
SELECT * FROM assessment_templates
WHERE is_published = 1 AND (
  is_master_assessment = 1 OR created_by = mentor_id_single
)
```
New:
```sql
SELECT t.* FROM assessment_templates t
LEFT JOIN apprentice_mentors am ON t.created_by = am.mentor_id
WHERE t.is_published = 1
  AND (
    t.is_master_assessment = 1
    OR (am.apprentice_id = :apprentice_id AND am.active = 1)
  )
GROUP BY t.id
```
Mentor view unaffected (still only their own + master). No cross-mentor leakage.

## 9. Caching & Performance
- Add composite index `(mentor_id, apprentice_id, active)` if high read volume.
- Consider caching mentor-id list per apprentice in Redis with short TTL (e.g., 60s) to reduce join overhead in template queries.

## 10. Frontend / Mobile Impact
| Area | Change |
|------|--------|
| Mentor Dashboard | Potential filter by mentor if viewing shared apprentice assessments (optional) |
| Apprentice Dashboard | Templates list shows union of all mentor published templates (dedupe) |
| Invites Flow | Choose one mentor or auto-assign inviter; UI to “Add another mentor” later |
| Assessment Creation | If multiple mentors, optionally choose supervising mentor (dropdown) |

## 11. Email & Notifications
- Invitation emails may specify *primary* mentor. Need rule for which mentor triggers notifications on assessment submission (all? primary? last active?).
- Suggest: maintain `primary` flag (single) + allow additional mentors (non-primary) to opt into notifications.

## 12. Auditing
Log events: mentor_added, mentor_removed, mentor_role_changed, primary_mentor_changed.
Include: actor_user_id, apprentice_id, mentor_id, timestamp, reason(optional).

## 13. Testing Strategy
| Layer | Tests |
|-------|-------|
| DB | Unique constraint, backfill works, cascade deletes |
| API | Assign/remove mentor, duplicate assignment 409, unauthorized attach |
| AuthZ | Mentor cannot access unlinked apprentice data |
| Templates | Apprentice sees union set (master + mentors) |
| Assessments | Cannot create with non-associated mentor_id |
| Performance | Query count baseline vs multi-mentor mode |

## 14. Rollout & Risk Mitigation
| Risk | Mitigation |
|------|-----------|
| Data leakage | Strict ownership filters & regression tests |
| Orphan relationships | ON DELETE CASCADE + nightly integrity job |
| Increased query cost | Indexes + optional caching |
| UI confusion | Clear labeling of “Mentor (Primary)” and list expansion UX |

### Feature Flag Phases
1. Dark launch (writes disabled, reads still single mentor)
2. Dual write (both legacy & new join) – optional if legacy column exists
3. Read switch (source of truth = join table)
4. Remove legacy

## 15. Open Questions
1. Do multiple mentors all receive assessment submission notifications? Configurable?  
2. Should one mentor be designated PRIMARY (for escalations & default context)?  
3. Can apprentices remove mentors, or only mentors/admins?  
4. Need visibility of which mentor authored which feedback items?  
5. Are mentor roles differentiated (advisor vs evaluator)?  

## 16. Effort Estimate (Rough)
| Work Item | Size |
|-----------|------|
| Schema + Migration | S |
| Backend Query / Auth Refactor | M |
| New Endpoints + Tests | M |
| Frontend UI Adjustments | M |
| Notifications Logic | S–M |
| Documentation & Migration Guide | S |
| Total (Initial Release) | ~1.5–2.5 dev weeks |

## 17. Decision Summary
Proceed only if there is a validated product requirement (e.g., structured co-mentoring). Otherwise the added complexity may outweigh benefit at current stage.

## 18. Quick Reference Checklist
- [ ] Create `apprentice_mentors` table
- [ ] Backfill existing relationships
- [ ] Add mentor management endpoints
- [ ] Update template visibility query
- [ ] Adjust assessment creation (optional mentor context)
- [ ] Harden authorization checks (membership instead of equality)
- [ ] Add tests (positive + negative)
- [ ] Update docs & mobile integration guide
- [ ] Roll out behind feature flag

---
*This document is a forward-looking design artifact. No code has been altered based on it yet.*
