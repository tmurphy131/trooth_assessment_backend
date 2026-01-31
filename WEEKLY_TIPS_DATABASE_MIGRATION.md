# Weekly Tips Database Migration Plan

> **Status**: Future enhancement (hardcoded approach is sufficient for launch)
> **Created**: January 19, 2026

## Current Implementation

Weekly tips are currently hardcoded in two locations:
- **Backend**: `app/routes/scheduled_tasks.py` - Contains tip titles for push notifications
- **Frontend**: `lib/data/weekly_tips_data.dart` and `lib/data/apprentice_weekly_tips_data.dart` - Contains full tip content

This works for launch but has limitations around content management and single-source-of-truth.

---

## Database Migration Plan

### 1. New Database Model

Create `app/models/weekly_tip.py`:

```python
from sqlalchemy import Column, String, Integer, Text, DateTime, Enum as SQLEnum, UniqueConstraint
from datetime import datetime
from app.db import Base
import uuid
import enum


class TipAudience(enum.Enum):
    mentor = "mentor"
    apprentice = "apprentice"


class WeeklyTip(Base):
    """Weekly tips stored in database for push notifications and display."""
    __tablename__ = "weekly_tips"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    week_number = Column(Integer, nullable=False, index=True)  # 1-52
    audience = Column(SQLEnum(TipAudience), nullable=False, index=True)  # mentor or apprentice
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    scripture = Column(String(500), nullable=True)
    action_step = Column(Text, nullable=True)
    is_active = Column(String, default="true")  # Allow disabling tips
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('week_number', 'audience', name='uq_weekly_tips_week_audience'),
    )

    def __repr__(self):
        return f"<WeeklyTip week={self.week_number} audience={self.audience.value} title='{self.title[:30]}'>"
```

### 2. Alembic Migration

Create migration file `alembic/versions/YYYYMMDD_add_weekly_tips_table.py`:

```python
"""Add weekly_tips table

Revision ID: add_weekly_tips_table
Revises: add_device_tokens_push
Create Date: YYYY-MM-DD
"""
from alembic import op
import sqlalchemy as sa


revision = 'add_weekly_tips_table'
down_revision = 'add_device_tokens_push'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'weekly_tips',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('week_number', sa.Integer(), nullable=False),
        sa.Column('audience', sa.Enum('mentor', 'apprentice', name='tipaudience'), nullable=False),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('scripture', sa.String(500), nullable=True),
        sa.Column('action_step', sa.Text(), nullable=True),
        sa.Column('is_active', sa.String(), default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_weekly_tips_week_number', 'weekly_tips', ['week_number'])
    op.create_index('ix_weekly_tips_audience', 'weekly_tips', ['audience'])
    op.create_unique_constraint('uq_weekly_tips_week_audience', 'weekly_tips', ['week_number', 'audience'])


def downgrade() -> None:
    op.drop_constraint('uq_weekly_tips_week_audience', 'weekly_tips', type_='unique')
    op.drop_index('ix_weekly_tips_audience', table_name='weekly_tips')
    op.drop_index('ix_weekly_tips_week_number', table_name='weekly_tips')
    op.drop_table('weekly_tips')
    op.execute('DROP TYPE IF EXISTS tipaudience')
```

### 3. Pydantic Schemas

Create `app/schemas/weekly_tip.py`:

```python
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class TipAudienceEnum(str, Enum):
    mentor = "mentor"
    apprentice = "apprentice"


class WeeklyTipBase(BaseModel):
    week_number: int = Field(..., ge=1, le=52, description="Week number (1-52)")
    audience: TipAudienceEnum
    title: str = Field(..., max_length=200)
    content: str
    scripture: Optional[str] = Field(None, max_length=500)
    action_step: Optional[str] = None


class WeeklyTipCreate(WeeklyTipBase):
    pass


class WeeklyTipUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=200)
    content: Optional[str] = None
    scripture: Optional[str] = Field(None, max_length=500)
    action_step: Optional[str] = None
    is_active: Optional[bool] = None


class WeeklyTipOut(WeeklyTipBase):
    id: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
```

### 4. Service Layer

Create `app/services/weekly_tips.py`:

```python
from sqlalchemy.orm import Session
from typing import Optional, List
from app.models.weekly_tip import WeeklyTip, TipAudience


def get_tip_for_week(db: Session, week_number: int, audience: str) -> Optional[WeeklyTip]:
    """Get tip from database for given week and audience."""
    tip_audience = TipAudience.mentor if audience == "mentor" else TipAudience.apprentice
    return db.query(WeeklyTip).filter(
        WeeklyTip.week_number == week_number,
        WeeklyTip.audience == tip_audience,
        WeeklyTip.is_active == "true"
    ).first()


def get_all_tips(db: Session, audience: Optional[str] = None) -> List[WeeklyTip]:
    """Get all tips, optionally filtered by audience."""
    query = db.query(WeeklyTip)
    if audience:
        tip_audience = TipAudience.mentor if audience == "mentor" else TipAudience.apprentice
        query = query.filter(WeeklyTip.audience == tip_audience)
    return query.order_by(WeeklyTip.audience, WeeklyTip.week_number).all()


def get_tips_for_notification(db: Session, week_number: int) -> dict:
    """Get both mentor and apprentice tips for a week (for scheduled notifications)."""
    mentor_tip = get_tip_for_week(db, week_number, "mentor")
    apprentice_tip = get_tip_for_week(db, week_number, "apprentice")
    return {
        "mentor": mentor_tip,
        "apprentice": apprentice_tip
    }


def create_tip(db: Session, tip_data: dict) -> WeeklyTip:
    """Create a new weekly tip."""
    tip = WeeklyTip(**tip_data)
    db.add(tip)
    db.commit()
    db.refresh(tip)
    return tip


def update_tip(db: Session, tip_id: str, update_data: dict) -> Optional[WeeklyTip]:
    """Update an existing weekly tip."""
    tip = db.query(WeeklyTip).filter(WeeklyTip.id == tip_id).first()
    if not tip:
        return None
    for key, value in update_data.items():
        if value is not None:
            setattr(tip, key, value)
    db.commit()
    db.refresh(tip)
    return tip
```

### 5. Admin API Endpoints

Add to `app/routes/admin_weekly_tips.py`:

```python
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List

from app.db import get_db
from app.services.auth import require_admin
from app.models.user import User
from app.models.weekly_tip import WeeklyTip, TipAudience
from app.schemas.weekly_tip import WeeklyTipCreate, WeeklyTipUpdate, WeeklyTipOut
from app.services import weekly_tips as tip_service

router = APIRouter()


@router.get("/weekly-tips", response_model=List[WeeklyTipOut])
def list_all_tips(
    audience: Optional[str] = Query(None, enum=["mentor", "apprentice"]),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin)
):
    """List all weekly tips, optionally filtered by audience."""
    return tip_service.get_all_tips(db, audience)


@router.get("/weekly-tips/{week_number}", response_model=List[WeeklyTipOut])
def get_tips_for_week(
    week_number: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin)
):
    """Get both mentor and apprentice tips for a specific week."""
    tips = db.query(WeeklyTip).filter(WeeklyTip.week_number == week_number).all()
    if not tips:
        raise HTTPException(status_code=404, detail=f"No tips found for week {week_number}")
    return tips


@router.post("/weekly-tips", response_model=WeeklyTipOut)
def create_tip(
    tip_data: WeeklyTipCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin)
):
    """Create a new weekly tip."""
    # Check if tip already exists for this week/audience
    existing = db.query(WeeklyTip).filter(
        WeeklyTip.week_number == tip_data.week_number,
        WeeklyTip.audience == TipAudience(tip_data.audience.value)
    ).first()
    if existing:
        raise HTTPException(
            status_code=400, 
            detail=f"Tip already exists for week {tip_data.week_number} ({tip_data.audience.value})"
        )
    return tip_service.create_tip(db, tip_data.model_dump())


@router.put("/weekly-tips/{tip_id}", response_model=WeeklyTipOut)
def update_tip(
    tip_id: str,
    update_data: WeeklyTipUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin)
):
    """Update a weekly tip's content."""
    tip = tip_service.update_tip(db, tip_id, update_data.model_dump(exclude_unset=True))
    if not tip:
        raise HTTPException(status_code=404, detail="Tip not found")
    return tip


@router.delete("/weekly-tips/{tip_id}")
def delete_tip(
    tip_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin)
):
    """Delete a weekly tip (soft delete by setting is_active=false)."""
    tip = db.query(WeeklyTip).filter(WeeklyTip.id == tip_id).first()
    if not tip:
        raise HTTPException(status_code=404, detail="Tip not found")
    tip.is_active = "false"
    db.commit()
    return {"message": "Tip deactivated", "id": tip_id}
```

### 6. Public API Endpoint (for Flutter app)

Add to `app/routes/resources.py` or similar:

```python
@router.get("/weekly-tips/current")
def get_current_week_tips(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get the current week's tip for the user's role."""
    from datetime import datetime
    
    now = datetime.now()
    first_day = datetime(now.year, 1, 1)
    week_number = ((now - first_day).days // 7 % 52) + 1
    
    audience = "mentor" if current_user.role.value == "mentor" else "apprentice"
    tip = tip_service.get_tip_for_week(db, week_number, audience)
    
    if not tip:
        return {"message": "No tip available for this week", "week_number": week_number}
    
    return {
        "week_number": tip.week_number,
        "title": tip.title,
        "content": tip.content,
        "scripture": tip.scripture,
        "action_step": tip.action_step
    }


@router.get("/weekly-tips/all")
def get_all_available_tips(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all tips available to the user (current week and earlier)."""
    from datetime import datetime
    
    now = datetime.now()
    first_day = datetime(now.year, 1, 1)
    current_week = ((now - first_day).days // 7 % 52) + 1
    
    audience = "mentor" if current_user.role.value == "mentor" else "apprentice"
    tip_audience = TipAudience.mentor if audience == "mentor" else TipAudience.apprentice
    
    tips = db.query(WeeklyTip).filter(
        WeeklyTip.audience == tip_audience,
        WeeklyTip.week_number <= current_week,
        WeeklyTip.is_active == "true"
    ).order_by(WeeklyTip.week_number.desc()).all()
    
    return [
        {
            "week_number": t.week_number,
            "title": t.title,
            "content": t.content,
            "scripture": t.scripture,
            "action_step": t.action_step
        }
        for t in tips
    ]
```

### 7. Data Seeding Script

Create `scripts/seed_weekly_tips.py`:

```python
"""Seed weekly tips from existing data.

Run with: python -m scripts.seed_weekly_tips
"""
import sys
sys.path.insert(0, '.')

from app.db import SessionLocal
from app.models.weekly_tip import WeeklyTip, TipAudience
import uuid

# Import the existing hardcoded data
# (You'd need to convert the Dart data to Python dicts)

MENTOR_TIPS = [
    {
        "week_number": 1,
        "title": "Start with Prayer",
        "content": """Begin each mentoring session by praying together...""",
        "scripture": "Philippians 4:6 - ...",
        "action_step": "At your next meeting, ask your apprentice if you can open in prayer together."
    },
    # ... all 52 mentor tips
]

APPRENTICE_TIPS = [
    {
        "week_number": 1,
        "title": "Show Up Consistently",
        "content": """The most important thing you can do in mentorship is simply show up...""",
        "scripture": "Hebrews 10:25 - ...",
        "action_step": "Set a recurring reminder for your mentoring meetings."
    },
    # ... all 52 apprentice tips
]


def seed_tips():
    db = SessionLocal()
    try:
        # Check if already seeded
        existing_count = db.query(WeeklyTip).count()
        if existing_count > 0:
            print(f"Database already has {existing_count} tips. Skipping seed.")
            return
        
        # Seed mentor tips
        for tip_data in MENTOR_TIPS:
            tip = WeeklyTip(
                id=str(uuid.uuid4()),
                audience=TipAudience.mentor,
                **tip_data
            )
            db.add(tip)
        
        # Seed apprentice tips
        for tip_data in APPRENTICE_TIPS:
            tip = WeeklyTip(
                id=str(uuid.uuid4()),
                audience=TipAudience.apprentice,
                **tip_data
            )
            db.add(tip)
        
        db.commit()
        print(f"✅ Seeded {len(MENTOR_TIPS)} mentor tips and {len(APPRENTICE_TIPS)} apprentice tips")
    
    except Exception as e:
        db.rollback()
        print(f"❌ Error seeding tips: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_tips()
```

### 8. Update Scheduled Tasks

Update `app/routes/scheduled_tasks.py` to use database:

```python
@router.post("/weekly-tips")
def trigger_weekly_tips(
    db: Session = Depends(get_db),
    _verified: bool = Depends(verify_cron_secret)
):
    """Send weekly tip push notifications to all mentors and apprentices."""
    from app.services.weekly_tips import get_tips_for_notification
    
    # Get current week number
    now = datetime.now()
    first_day = datetime(now.year, 1, 1)
    week_number = ((now - first_day).days // 7 % 52) + 1
    
    logger.info(f"Triggering weekly tips for week {week_number}")
    
    # Get tips from database
    tips = get_tips_for_notification(db, week_number)
    
    mentor_tip_title = tips["mentor"].title if tips["mentor"] else f"Week {week_number} Mentor Tip"
    apprentice_tip_title = tips["apprentice"].title if tips["apprentice"] else f"Week {week_number} Apprentice Tip"
    
    # ... rest of the notification logic
```

---

## Benefits of Database Approach

| Feature | Hardcoded | Database |
|---------|-----------|----------|
| Edit tips without code deploy | ❌ | ✅ |
| Admin UI for content management | ❌ | ✅ |
| A/B testing different tips | ❌ | ✅ |
| Track which tips have been sent | ❌ | ✅ |
| Add seasonal/special tips | ❌ | ✅ |
| Single source of truth (frontend + backend) | ❌ | ✅ |
| Version history/audit trail | ❌ | ✅ |
| Localization/multiple languages | ❌ | ✅ |

---

## Migration Checklist

- [ ] Create `WeeklyTip` model
- [ ] Create Alembic migration
- [ ] Create Pydantic schemas
- [ ] Create service layer functions
- [ ] Create admin API endpoints
- [ ] Create public API endpoints
- [ ] Create data seeding script
- [ ] Seed database from existing Dart data
- [ ] Update `scheduled_tasks.py` to use database
- [ ] Register new router in `main.py`
- [ ] Update Flutter app to fetch tips from API (optional - can still use hardcoded)
- [ ] Add admin UI for managing tips (optional)
- [ ] Write tests for new endpoints

---

## Flutter App Updates (Optional)

If you want the Flutter app to fetch tips from the API instead of using hardcoded data:

1. Add API methods to `ApiService`:
```dart
Future<Map<String, dynamic>> getCurrentWeekTip() async {
  final r = await _request('GET', '/resources/weekly-tips/current');
  if (r.statusCode == 200) return jsonDecode(r.body);
  throw Exception('Failed to get current tip');
}

Future<List<dynamic>> getAllAvailableTips() async {
  final r = await _request('GET', '/resources/weekly-tips/all');
  if (r.statusCode == 200) return jsonDecode(r.body);
  throw Exception('Failed to get tips');
}
```

2. Update `MentorResourcesScreen` and `ApprenticeResourcesScreen` to fetch from API
3. Add caching to avoid repeated API calls
4. Keep hardcoded data as fallback if API fails
