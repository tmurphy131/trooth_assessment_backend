# T[root]H Engagement Email & Push Notification Execution Plan

**Status:** Ready for Implementation  
**Last Updated:** May 8, 2026  
**Timeline:** 6-8 weeks for full rollout

---

## 📊 Current Infrastructure Status

### ✅ Already Implemented
1. **Push Notification Infrastructure**
   - ✅ `DeviceToken` model exists (`app/models/device_token.py`)
   - ✅ Migration `20260119_add_device_tokens_push.py` applied
   - ✅ Stores FCM tokens with platform, device name, is_active flag
   - ✅ User relationship already established

2. **Email Tracking**
   - ✅ `EmailSendEvent` model exists (`app/models/email_send_event.py`)
   - ✅ Migration `20250913_add_email_send_events_table.py` applied
   - ✅ Tracks sender, target, assessment, purpose, timestamp
   - ✅ Indexed for query performance

3. **Email Infrastructure**
   - ✅ SendGrid integration in `app/services/email.py`
   - ✅ Jinja2 templating system
   - ✅ Multiple email types already supported (invitations, assessments, reports)

### 🚧 Needs Implementation
1. **User Activity Tracking** - Need `last_activity_at` column
2. **Push Notification Preferences** - Need quiet hours, timezone, opt-in columns
3. **Campaign Services** - New email/push sending functions
4. **Scheduled Jobs** - Cron or Cloud Scheduler setup
5. **Email Templates** - New Jinja2 templates for campaigns

---

## 🔧 Required Database Migrations

### Migration 1: Add User Engagement Fields
**File:** `alembic/versions/20260508_add_user_engagement_fields.py`

**Purpose:** Track user activity and push notification preferences

**Schema Changes:**
```sql
ALTER TABLE users ADD COLUMN last_activity_at TIMESTAMP;
ALTER TABLE users ADD COLUMN push_enabled BOOLEAN DEFAULT TRUE;
ALTER TABLE users ADD COLUMN push_quiet_hours_start INTEGER;  -- 0-23 hour
ALTER TABLE users ADD COLUMN push_quiet_hours_end INTEGER;    -- 0-23 hour
ALTER TABLE users ADD COLUMN timezone VARCHAR(100);           -- e.g., "America/New_York"
```

**Alembic Migration Code:**
```python
"""Add user engagement tracking fields

Revision ID: 20260508_add_user_engagement_fields
Revises: add_device_tokens_push
Create Date: 2026-05-08
"""
from alembic import op
import sqlalchemy as sa

revision = '20260508_add_user_engagement_fields'
down_revision = 'add_device_tokens_push'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Add activity tracking
    op.add_column('users', 
        sa.Column('last_activity_at', sa.DateTime(), nullable=True)
    )
    
    # Add push notification preferences
    op.add_column('users', 
        sa.Column('push_enabled', sa.Boolean(), nullable=False, server_default='true')
    )
    op.add_column('users', 
        sa.Column('push_quiet_hours_start', sa.Integer(), nullable=True)
    )
    op.add_column('users', 
        sa.Column('push_quiet_hours_end', sa.Integer(), nullable=True)
    )
    op.add_column('users', 
        sa.Column('timezone', sa.String(100), nullable=True)
    )
    
    # Backfill last_activity_at from created_at for existing users
    op.execute("""
        UPDATE users 
        SET last_activity_at = created_at 
        WHERE last_activity_at IS NULL
    """)

def downgrade() -> None:
    op.drop_column('users', 'timezone')
    op.drop_column('users', 'push_quiet_hours_end')
    op.drop_column('users', 'push_quiet_hours_start')
    op.drop_column('users', 'push_enabled')
    op.drop_column('users', 'last_activity_at')
```

**Run Migration:**
```bash
cd /Users/tmoney/Developer/trooth_assessment_backend
source .venv/bin/activate
alembic revision -m "add_user_engagement_fields"
# Copy the code above into the generated file
alembic upgrade head
```

---

### Migration 2: Expand Email Tracking (Optional)
**File:** `alembic/versions/20260508_expand_email_tracking.py`

**Purpose:** Better campaign tracking and analytics

**Schema Changes:**
```sql
ALTER TABLE email_send_events ADD COLUMN campaign_type VARCHAR(100);  -- 'draft_reminder', 'new_template', etc.
ALTER TABLE email_send_events ADD COLUMN context JSON;                -- Flexible metadata
ALTER TABLE email_send_events ADD COLUMN delivery_status VARCHAR(50); -- 'sent', 'bounced', 'opened'
```

**Implementation:**
```python
"""Expand email tracking for campaigns

Revision ID: 20260508_expand_email_tracking
Revises: 20260508_add_user_engagement_fields
Create Date: 2026-05-08
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '20260508_expand_email_tracking'
down_revision = '20260508_add_user_engagement_fields'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column('email_send_events', 
        sa.Column('campaign_type', sa.String(100), nullable=True)
    )
    op.add_column('email_send_events', 
        sa.Column('context', sa.JSON(), nullable=True)
    )
    op.add_column('email_send_events', 
        sa.Column('delivery_status', sa.String(50), nullable=True, server_default='sent')
    )
    
    # Create index for campaign queries
    op.create_index(
        'ix_email_send_events_campaign', 
        'email_send_events', 
        ['campaign_type', 'created_at']
    )

def downgrade() -> None:
    op.drop_index('ix_email_send_events_campaign', table_name='email_send_events')
    op.drop_column('email_send_events', 'delivery_status')
    op.drop_column('email_send_events', 'context')
    op.drop_column('email_send_events', 'campaign_type')
```

**Run Migration:**
```bash
alembic revision -m "expand_email_tracking"
# Copy the code above into the generated file
alembic upgrade head
```

---

## 📅 Phase 1: Foundation (Week 1-2)

### Week 1: Database & Core Services

#### Day 1-2: Database Migrations
- [ ] Create and run migration `20260508_add_user_engagement_fields.py`
- [ ] Create and run migration `20260508_expand_email_tracking.py` (optional)
- [ ] Update `app/models/user.py` to include new columns
- [ ] Update `app/models/email_send_event.py` if migration 2 applied
- [ ] Test migrations on dev database

**File Changes:**
```python
# app/models/user.py - Add these columns to User class:
last_activity_at = Column(DateTime, nullable=True)
push_enabled = Column(Boolean, nullable=False, default=True, server_default="true")
push_quiet_hours_start = Column(Integer, nullable=True)  # 0-23
push_quiet_hours_end = Column(Integer, nullable=True)    # 0-23
timezone = Column(String(100), nullable=True)
```

#### Day 3-4: Activity Tracking Middleware
- [ ] Create `app/middleware/activity_tracker.py`
- [ ] Update `last_activity_at` on every authenticated request
- [ ] Register middleware in `app/main.py`

**Implementation:**
```python
# app/middleware/activity_tracker.py
from datetime import datetime, UTC
from starlette.middleware.base import BaseHTTPMiddleware
from app.db import SessionLocal
from app.models import User

class ActivityTrackerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        
        # Get user_id from request state (set by auth middleware)
        user_id = getattr(request.state, "user_id", None)
        
        if user_id:
            # Update last_activity_at in background (don't block response)
            try:
                db = SessionLocal()
                db.query(User).filter(User.id == user_id).update({
                    "last_activity_at": datetime.now(UTC)
                })
                db.commit()
                db.close()
            except Exception as e:
                # Log but don't fail request
                import logging
                logging.error(f"Failed to update activity: {e}")
        
        return response
```

```python
# app/main.py - Add after other middleware
from app.middleware.activity_tracker import ActivityTrackerMiddleware
app.add_middleware(ActivityTrackerMiddleware)
```

#### Day 5: Push Notification Service Enhancements
- [ ] Create `app/services/push_notification.py` (use code from strategy doc)
- [ ] Add campaign-specific push functions:
  - `send_draft_reminder_push()`
  - `send_new_template_push()`
  - `send_mentor_report_ready_push()`
- [ ] Add quiet hours checking logic
- [ ] Add timezone-aware scheduling helper

**Key Functions:**
```python
# app/services/push_notification.py

def is_quiet_hours(user: User) -> bool:
    """Check if current time is in user's quiet hours."""
    if not user.push_quiet_hours_start or not user.push_quiet_hours_end:
        # Default quiet hours: 10 PM - 8 AM
        current_hour = datetime.now(UTC).hour
        return current_hour >= 22 or current_hour < 8
    
    # Use user's timezone if available
    if user.timezone:
        import pytz
        user_tz = pytz.timezone(user.timezone)
        current_time = datetime.now(user_tz)
        current_hour = current_time.hour
    else:
        current_hour = datetime.now(UTC).hour
    
    start = user.push_quiet_hours_start
    end = user.push_quiet_hours_end
    
    if start < end:
        return start <= current_hour < end
    else:  # Wraps midnight
        return current_hour >= start or current_hour < end
```

---

### Week 2: Email Templates & Campaign Services

#### Day 1-3: Email Template Creation
- [ ] Create `app/templates/email/campaigns/` directory
- [ ] Build Jinja2 templates:
  - `incomplete_draft_reminder.html`
  - `new_assessment_notification.html`
  - `welcome_apprentice.html`
  - `welcome_mentor.html`
  - `inactive_reengagement.html`
  - `milestone_celebration.html`

**Template Structure:** (base on existing `_base.html`)
```html
<!-- app/templates/email/campaigns/incomplete_draft_reminder.html -->
{% extends "email/_base.html" %}

{% block content %}
<h1 style="color: #D4AF37; font-family: 'Unkempt', cursive;">You're Almost There! 🌱</h1>

<p>Hi {{ apprentice_name }},</p>

<p>We noticed you started the <strong>{{ assessment_name }}</strong> assessment {{ days_ago }} days ago. 
You're <strong>{{ progress_percent }}% complete</strong> – just a few more questions!</p>

<div style="background: #2a2a2a; padding: 20px; border-radius: 8px; margin: 20px 0;">
    <h3 style="color: #D4AF37; margin-top: 0;">Your Progress</h3>
    <div style="background: #1a1a1a; height: 30px; border-radius: 15px; overflow: hidden;">
        <div style="background: linear-gradient(90deg, #D4AF37, #FFD700); 
                    width: {{ progress_percent }}%; height: 100%; 
                    display: flex; align-items: center; justify-content: center;">
            <span style="color: #000; font-weight: bold;">{{ progress_percent }}%</span>
        </div>
    </div>
    <p style="color: #ccc; margin-bottom: 0;">
        {{ answered_count }} of {{ total_questions }} questions answered
    </p>
</div>

<p>Your mentor, <strong>{{ mentor_name }}</strong>, is waiting to review your results and 
provide personalized guidance for your spiritual growth.</p>

<a href="{{ resume_link }}" 
   style="display: inline-block; background: #D4AF37; color: #1a1a1a; 
          padding: 15px 30px; text-decoration: none; border-radius: 8px; 
          font-weight: bold; margin: 20px 0;">
    Resume Assessment →
</a>

<p style="color: #888; font-size: 14px; margin-top: 30px;">
    This should only take 5-10 more minutes. Your spiritual growth journey is worth it!
</p>
{% endblock %}
```

#### Day 4-5: Campaign Email Service Functions
- [ ] Add functions to `app/services/email.py`:
  - `send_draft_reminder_email()`
  - `send_new_template_email()`
  - `send_welcome_email()`
  - `send_inactive_reengagement_email()`
  - `send_milestone_email()`
- [ ] Each function logs to `EmailSendEvent` table
- [ ] Add campaign_type tracking

**Example Implementation:**
```python
# app/services/email.py

def send_draft_reminder_email(
    user: User,
    draft: AssessmentDraft,
    mentor_name: str,
    days_since_start: int
) -> bool:
    """Send reminder email for incomplete draft."""
    
    # Calculate progress
    total_questions = len(draft.template.questions)
    answered_count = len(draft.answers) if draft.answers else 0
    progress_percent = int((answered_count / total_questions) * 100)
    
    # Build context
    context = {
        'apprentice_name': user.name,
        'assessment_name': draft.template.name,
        'days_ago': days_since_start,
        'progress_percent': progress_percent,
        'answered_count': answered_count,
        'total_questions': total_questions,
        'mentor_name': mentor_name,
        'resume_link': f"{settings.app_url}/assessment/draft/{draft.id}",
        'year': datetime.now().year,
    }
    
    # Render template
    env = get_email_template_env()
    template = env.get_template('campaigns/incomplete_draft_reminder.html')
    html_content = template.render(**context)
    
    # Plain text fallback
    plain_content = f"""
    Hi {user.name},
    
    You started the {draft.template.name} assessment {days_since_start} days ago.
    You're {progress_percent}% complete - just a few more questions!
    
    Resume here: {context['resume_link']}
    
    Your mentor {mentor_name} is waiting to help guide your spiritual growth.
    """
    
    # Send
    subject = f"You're {progress_percent}% Through Your Assessment! 🌱"
    success = send_email(user.email, subject, html_content, plain_content)
    
    # Log campaign
    if success:
        from app.models import EmailSendEvent
        from app.db import SessionLocal
        db = SessionLocal()
        db.add(EmailSendEvent(
            sender_user_id=user.id,  # Or system user ID
            target_user_id=user.id,
            assessment_id=None,
            campaign_type='draft_reminder',
            purpose='engagement',
            context={
                'draft_id': draft.id,
                'days_since_start': days_since_start,
                'progress_percent': progress_percent,
            }
        ))
        db.commit()
        db.close()
    
    return success
```

---

## 📅 Phase 2: Core Campaigns (Week 3-4)

### Week 3: Incomplete Draft Reminders

#### Day 1-2: Draft Reminder Script
- [ ] Create `scripts/send_draft_reminders.py`
- [ ] Query logic for 5-day, 10-day, 14-day stale drafts
- [ ] Batch processing (limit to avoid spam)
- [ ] Prevent duplicate sends (check EmailSendEvent)

**Implementation:**
```python
# scripts/send_draft_reminders.py
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from datetime import datetime, timedelta, UTC
from app.db import SessionLocal
from app.models import User, AssessmentDraft, EmailSendEvent
from app.services.email import send_draft_reminder_email
from sqlalchemy import and_

def send_daily_draft_reminders():
    """Send draft reminder emails for abandoned drafts.
    
    Runs daily, sends reminders at 5, 10, and 14 days after draft start.
    """
    db = SessionLocal()
    now = datetime.now(UTC)
    
    # Define reminder windows (day boundaries)
    reminder_days = [5, 10, 14]
    
    for days in reminder_days:
        # Calculate window: drafts updated exactly N days ago (±12 hours)
        window_start = now - timedelta(days=days, hours=12)
        window_end = now - timedelta(days=days - 1, hours=12)
        
        print(f"Checking drafts from {window_start} to {window_end} ({days} days old)...")
        
        # Find stale drafts in window
        drafts = db.query(AssessmentDraft).filter(
            AssessmentDraft.is_submitted == False,
            AssessmentDraft.updated_at >= window_start,
            AssessmentDraft.updated_at < window_end
        ).all()
        
        print(f"Found {len(drafts)} drafts")
        
        for draft in drafts:
            # Check if we already sent reminder for this draft at this interval
            existing = db.query(EmailSendEvent).filter(
                EmailSendEvent.target_user_id == draft.apprentice_id,
                EmailSendEvent.campaign_type == 'draft_reminder',
                EmailSendEvent.context['draft_id'].astext == draft.id,
                EmailSendEvent.created_at > window_start
            ).first()
            
            if existing:
                print(f"Already sent reminder for draft {draft.id}, skipping")
                continue
            
            # Get user and mentor
            user = db.query(User).filter(User.id == draft.apprentice_id).first()
            if not user:
                continue
            
            # Get mentor name (if available)
            # TODO: Query mentor relationship
            mentor_name = "your mentor"  # Placeholder
            
            # Send email
            print(f"Sending {days}-day reminder to {user.email} for draft {draft.id}")
            success = send_draft_reminder_email(
                user=user,
                draft=draft,
                mentor_name=mentor_name,
                days_since_start=days
            )
            
            if success:
                print(f"✓ Sent to {user.email}")
            else:
                print(f"✗ Failed to send to {user.email}")
    
    db.close()
    print("Draft reminders complete!")

if __name__ == "__main__":
    send_daily_draft_reminders()
```

#### Day 3: Testing & Validation
- [ ] Test script locally with test database
- [ ] Verify email rendering in SendGrid
- [ ] Check EmailSendEvent logging works
- [ ] Confirm no duplicate sends

**Test Command:**
```bash
cd /Users/tmoney/Developer/trooth_assessment_backend
source .venv/bin/activate
python scripts/send_draft_reminders.py
```

#### Day 4-5: Schedule Daily Cron
- [ ] Set up cron job (local or server)
- [ ] OR set up Google Cloud Scheduler
- [ ] Schedule for 7 PM UTC (evening for most users)
- [ ] Monitor first week of sends

**Cron Setup (Local/Server):**
```bash
# Edit crontab
crontab -e

# Add line (runs daily at 7 PM UTC)
0 19 * * * cd /Users/tmoney/Developer/trooth_assessment_backend && /Users/tmoney/Developer/trooth_assessment_backend/.venv/bin/python scripts/send_draft_reminders.py >> /tmp/draft_reminders.log 2>&1
```

**Cloud Scheduler Setup (Production):**
```bash
# Create endpoint in backend
# POST /admin/campaigns/run-draft-reminders (admin auth required)

# Schedule with Cloud Scheduler
gcloud scheduler jobs create http draft-reminders \
  --schedule="0 19 * * *" \
  --uri="https://trooth-discipleship-api.onlyblv.com/admin/campaigns/run-draft-reminders" \
  --http-method=POST \
  --headers="Authorization=Bearer YOUR_ADMIN_TOKEN"
```

---

### Week 4: New Template Notifications

#### Day 1-2: Template Publication Hook
- [ ] Add email trigger to template creation endpoint
- [ ] `POST /admin/templates` - on publish, queue notifications
- [ ] `PATCH /admin/templates/:id` - on status change to published
- [ ] Batch notifications if multiple apprentices

**Implementation:**
```python
# app/routes/admin_template.py (or wherever templates are created)

@router.post("/admin/templates")
async def create_template(
    template_data: TemplateCreateSchema,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks
):
    # ... existing template creation logic ...
    
    # If published immediately, send notifications
    if template.published:
        background_tasks.add_task(
            notify_new_template_available,
            template_id=template.id,
            db=db
        )
    
    return {"message": "Template created", "template_id": template.id}


def notify_new_template_available(template_id: str, db: Session):
    """Send email/push to all apprentices about new template."""
    from app.models import User, UserRole, AssessmentTemplate
    from app.services.email import send_new_template_email
    from app.services.push_notification import send_new_template_push
    
    template = db.query(AssessmentTemplate).filter(
        AssessmentTemplate.id == template_id
    ).first()
    
    if not template:
        return
    
    # Get all apprentices
    apprentices = db.query(User).filter(
        User.role == UserRole.apprentice
    ).all()
    
    # Send to each (implement batching if 1000+ users)
    for user in apprentices:
        # Check if user already completed this template (avoid spam)
        # TODO: Query assessment history
        
        # Email
        send_new_template_email(user, template)
        
        # Push (if enabled)
        if user.push_enabled:
            send_new_template_push(user, template.name, template.id)
```

#### Day 3-5: Push Notification Implementation
- [ ] Register FCM token endpoint (already exists via DeviceToken model)
- [ ] Test push notification sending
- [ ] Handle push notification taps in Flutter app
- [ ] Add deep linking to template screen

**Flutter Deep Link Handling:**
```dart
// lib/main.dart
FirebaseMessaging.onMessageOpenedApp.listen((RemoteMessage message) {
  final data = message.data;
  final templateId = data['template_id'];
  
  if (templateId != null) {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => AssessmentTemplateDetailScreen(templateId: templateId)
      )
    );
  }
});
```

---

## 📅 Phase 3: Engagement Campaigns (Week 5-6)

### Week 5: Welcome Series

#### Day 1-2: Welcome Email on Signup
- [ ] Add welcome email trigger to user creation endpoint
- [ ] Separate templates for mentor vs apprentice
- [ ] Send immediately on successful signup

**Implementation:**
```python
# app/routes/user.py

@router.post("/users")
async def create_user(
    user_data: UserCreateSchema,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    # ... existing user creation logic ...
    
    # Send welcome email
    background_tasks.add_task(
        send_welcome_email,
        user_id=user.id,
        role=user.role
    )
    
    return {"message": "User created", "user_id": user.id}
```

#### Day 3-5: Inactive User Re-Engagement
- [ ] Create `scripts/send_inactive_reminders.py`
- [ ] Query users with `last_activity_at` > 14/30/60 days
- [ ] Segment by role (apprentice vs mentor)
- [ ] Different messaging for each segment

---

### Week 6: Milestones & Refinement

#### Day 1-2: Milestone Celebrations
- [ ] Add milestone detection on assessment completion
- [ ] Send immediate email + push on milestone
- [ ] Track milestone in user profile (avoid duplicate celebrations)

**Milestones to Track:**
- First assessment completed
- 5th assessment completed
- 10th assessment completed
- 1-year anniversary
- 7-day streak (if tracking daily activity)

#### Day 3-5: Testing & Optimization
- [ ] Review all campaign analytics in EmailSendEvent table
- [ ] Check bounce rates, open rates (if SendGrid webhooks set up)
- [ ] Adjust email copy based on early metrics
- [ ] Fine-tune send times

---

## 📅 Phase 4: Advanced Features (Week 7-8)

### Week 7: Analytics & Reporting

#### Dashboard for Campaign Performance
- [ ] Create admin endpoint `/admin/campaigns/stats`
- [ ] Show emails sent per campaign type
- [ ] Show conversion rates (email sent → action taken)
- [ ] Chart trends over time

**Query Example:**
```python
# Count draft reminder emails sent last 30 days
from sqlalchemy import func
from datetime import datetime, timedelta, UTC

thirty_days_ago = datetime.now(UTC) - timedelta(days=30)

stats = db.query(
    EmailSendEvent.campaign_type,
    func.count(EmailSendEvent.id).label('count')
).filter(
    EmailSendEvent.created_at >= thirty_days_ago
).group_by(
    EmailSendEvent.campaign_type
).all()

# stats = [('draft_reminder', 45), ('new_template', 120), ...]
```

---

### Week 8: A/B Testing Framework

#### Simple A/B Test Implementation
- [ ] Add `variant` field to EmailSendEvent
- [ ] Randomly assign users to variant A or B
- [ ] Track which variant performs better

**Example:**
```python
import random

def send_draft_reminder_with_ab_test(user, draft):
    # 50/50 split
    variant = 'A' if random.random() < 0.5 else 'B'
    
    if variant == 'A':
        subject = "You're 60% Through Your Assessment! 🌱"
    else:  # Variant B - more urgency
        subject = "Finish Your Assessment Today! ⏰"
    
    # Send email...
    # Log variant in EmailSendEvent.context
```

---

## 🚀 Production Deployment Checklist

### Pre-Launch
- [ ] All migrations tested on staging database
- [ ] Email templates reviewed for typos/branding
- [ ] SendGrid domain verified (SPF/DKIM)
- [ ] Unsubscribe links working in all emails
- [ ] Push notifications tested on iOS + Android
- [ ] Deep links working in app
- [ ] Cron jobs scheduled OR Cloud Scheduler configured
- [ ] Error logging and monitoring set up

### Launch Day
- [ ] Deploy migrations to production: `alembic upgrade head`
- [ ] Deploy new backend code
- [ ] Enable first campaign (draft reminders only)
- [ ] Monitor logs for errors
- [ ] Check first batch of emails sent successfully

### Week 1 Post-Launch
- [ ] Review email delivery rates daily
- [ ] Check for user complaints/unsubscribes
- [ ] Monitor database performance (activity tracking middleware)
- [ ] Adjust send times if needed
- [ ] Enable second campaign (new templates)

### Week 2-4 Post-Launch
- [ ] Enable remaining campaigns one at a time
- [ ] Gather user feedback on email frequency
- [ ] Review campaign analytics
- [ ] Build optimization plan based on data

---

## 📊 Success Metrics to Track

### Email Metrics (from SendGrid)
- **Delivery Rate:** % successfully delivered (target: >95%)
- **Open Rate:** % emails opened (target: 20-30% for engagement emails)
- **Click Rate:** % clicked CTA (target: 5-10%)
- **Unsubscribe Rate:** % opted out (target: <1%)

### Business Metrics (from database)
- **Draft Completion Rate:** % of started drafts completed within 14 days
  - Before campaign: Baseline measurement
  - After campaign: Target +15-20% improvement
  
- **User Retention:** % users active 30 days after signup
  - Before: Baseline
  - After welcome series: Target +10%

- **Assessment Frequency:** Avg days between assessments per user
  - Before: Baseline
  - After campaigns: Target -25% (more frequent)

### Push Notification Metrics
- **Opt-In Rate:** % users with push enabled (target: >60%)
- **Open Rate:** % push notifications tapped (target: 8-12%)
- **Uninstall Correlation:** Monitor uninstall rate after push campaigns

---

## 🔄 Maintenance & Iteration

### Weekly
- [ ] Review EmailSendEvent logs for errors
- [ ] Check campaign stats dashboard
- [ ] Monitor user complaints/support tickets related to emails

### Monthly
- [ ] Review KPIs vs targets
- [ ] A/B test new email subject lines
- [ ] Optimize send times based on open rate data
- [ ] Update email templates for freshness

### Quarterly
- [ ] Major campaign strategy review
- [ ] Add new campaign types based on user behavior
- [ ] Deprecate low-performing campaigns
- [ ] Survey users about email preferences

---

## 👥 Team Responsibilities

### Backend Developer
- Database migrations
- Campaign service functions
- Cron job setup
- API endpoints for push token registration

### Frontend/Mobile Developer
- Flutter push notification handling
- Deep link routing
- User preference screens (manage email/push settings)

### Designer
- Email template design
- Push notification copy review
- In-app notification UI

### Product/Marketing
- Email copy writing
- Campaign strategy decisions
- A/B test planning
- Analytics review

---

## ⚠️ Risks & Mitigations

### Risk 1: Email Marked as Spam
**Mitigation:**
- Verify SendGrid domain with SPF/DKIM/DMARC
- Start with low volume, ramp up gradually
- Always include unsubscribe link
- Use clear "from" name (T[root]H, not no-reply)
- Monitor bounce rate and clean email list

### Risk 2: Push Notification Fatigue
**Mitigation:**
- Enforce max 1 marketing push/day
- Respect quiet hours
- Make opt-out easy
- Focus on transactional pushes (mentor reports) first
- A/B test frequency

### Risk 3: Performance Impact
**Mitigation:**
- Activity tracking uses async background update
- Batch email/push sends (don't send 1000 emails in loop)
- Use indexes on query columns (last_activity_at, created_at)
- Consider queue system (Celery) if user base grows >10k

### Risk 4: User Annoyance
**Mitigation:**
- Start conservative (fewer emails)
- Gather feedback early
- Implement preference center (let users choose campaigns)
- Monitor unsubscribe rate closely

---

## 📚 Reference Documents

- **Main Strategy:** [ENGAGEMENT_EMAIL_STRATEGY.md](ENGAGEMENT_EMAIL_STRATEGY.md)
- **Backend API Docs:** [MOBILE_API_GUIDE.md](MOBILE_API_GUIDE.md)
- **Deployment Guide:** [DEPLOYMENT.md](DEPLOYMENT.md)
- **SendGrid Docs:** https://docs.sendgrid.com/
- **Firebase Cloud Messaging:** https://firebase.google.com/docs/cloud-messaging

---

## 🎯 Summary Action Items

### Start Immediately (This Week)
1. ✅ Create migration `20260508_add_user_engagement_fields.py`
2. ✅ Update User model with new columns
3. ✅ Add activity tracking middleware
4. ✅ Create first email template (draft reminder)
5. ✅ Build `scripts/send_draft_reminders.py`

### Next Week
6. Test draft reminder campaign with small user subset
7. Create new template notification email
8. Set up push notification service
9. Schedule cron job

### Within 30 Days
10. Launch all Phase 1 & 2 campaigns
11. Set up analytics dashboard
12. Gather initial metrics
13. Begin A/B testing

---

**Questions? Contact:** Backend Team Lead  
**Document Status:** READY FOR IMPLEMENTATION  
**Last Review:** May 8, 2026
