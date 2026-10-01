# T[root]H Engagement Email Strategy

## Overview
Automated email campaigns to increase app engagement, assessment completion, and mentor-apprentice interaction. All emails leverage existing SendGrid infrastructure and Jinja2 templates.

---

## 📊 Data Available for Triggers

### User Model
- `created_at` - Account creation date
- `assessment_count` - Completed assessments (denormalized)
- `subscription_tier` - Free vs Premium
- `role` - Apprentice, Mentor, Admin

### AssessmentDraft Model
- `created_at` - When draft started
- `updated_at` - Last activity on draft
- `is_submitted` - Completion status
- `answers` - Progress tracking (count answered questions)

### Assessment Model
- `created_at` - Completion date
- `template_id` - Which assessment

### AssessmentTemplate Model
- `created_at` - When template published
- `published` - Visibility status

---

## 🎯 Proposed Engagement Campaigns

### 1. **Incomplete Assessment Nudge** (HIGH PRIORITY)
**Trigger:** Draft started but not submitted after 4-5 days

**Target:** Apprentices with `AssessmentDraft` where:
- `is_submitted = false`
- `updated_at` < 4-5 days ago
- `created_at` indicates draft exists

**Email Content:**
- Subject: "You're Almost There! Complete Your [Assessment Name] 🌱"
- Show progress: "You've answered X of Y questions"
- Encouragement: "Your mentor [Mentor Name] is waiting to support you"
- CTA: Deep link to resume draft in app

**Frequency:** 
- First email: 5 days after start
- Second email: 10 days after start (if still incomplete)
- Final email: 14 days after start with "We'll save your progress" message

**Implementation Notes:**
```python
# Query for stale drafts
stale_drafts = db.query(AssessmentDraft).filter(
    AssessmentDraft.is_submitted == False,
    AssessmentDraft.updated_at < (datetime.now(UTC) - timedelta(days=5))
).all()
```

---

### 2. **New Assessment Published** (HIGH PRIORITY)
**Trigger:** New `AssessmentTemplate` with `published=True` created

**Target:** 
- All apprentices (if general template)
- Specific apprentices (if mentor-created custom template)

**Email Content:**
- Subject: "New Spiritual Growth Assessment Available! ✨"
- Preview template description/category
- Highlight: "This new assessment takes ~15 minutes"
- CTA: "Start Assessment"

**Frequency:** Immediately upon template publication

**Implementation Notes:**
```python
# In admin/mentor template creation endpoint
if template.published:
    send_new_template_notification(
        template_id=template.id,
        template_name=template.name,
        target_role=UserRole.apprentice
    )
```

---

### 3. **Welcome Series** (MEDIUM PRIORITY)
**Trigger:** User account creation (`created_at`)

**Email Sequence:**

#### Email 1: Immediate Welcome
- Subject: "Welcome to T[root]H! Your Spiritual Growth Starts Here 🙏"
- Explain app purpose
- CTA: "Take Your First Assessment" (for apprentices) or "Invite an Apprentice" (for mentors)

#### Email 2: Day 3 - Feature Overview
- Subject: "Here's How T[root]H Helps You Grow"
- Explain AI scoring, mentor reports, progress tracking
- Show example report preview

#### Email 3: Day 7 - Social Proof
- Subject: "See How Others Are Growing with T[root]H"
- Testimonials (if available)
- CTA: Complete first assessment or invite more apprentices

**Implementation Notes:**
- Schedule via background task on user creation
- Track sent emails in new `email_log` table to prevent duplicates

---

### 4. **Inactive User Re-Engagement** (HIGH PRIORITY)
**Trigger:** No activity in X days

**Segmentation:**

#### Apprentices - Never Completed Assessment
- Last login > 14 days, `assessment_count = 0`
- Subject: "Still Thinking About Your Spiritual Growth? 🤔"
- Emphasize: "Your mentor is ready to guide you"
- CTA: "Browse Available Assessments"

#### Apprentices - Completed Assessment But Dormant
- Last login > 30 days, `assessment_count > 0`
- Subject: "Time for a Spiritual Check-In? 🌿"
- Highlight: "You last completed an assessment on [Date]"
- Show available new assessments
- CTA: "Continue Your Growth Journey"

#### Mentors - No Recent Apprentice Activity
- Last apprentice submission > 30 days
- Subject: "Your Apprentices May Need Encouragement 💪"
- List dormant apprentices
- Suggest: "Send them a personal message via the app"
- CTA: "View Apprentice Progress"

**Frequency:**
- First email: 14 days (apprentice), 30 days (mentor)
- Second email: 30 days
- Third email: 60 days (final win-back attempt)

**Implementation Notes:**
```python
# Requires adding last_login tracking to User model
# Alternative: Use last Assessment.created_at or AssessmentDraft.updated_at
inactive_apprentices = db.query(User).filter(
    User.role == UserRole.apprentice,
    User.assessment_count == 0,
    User.created_at < (datetime.now(UTC) - timedelta(days=14))
).all()
```

---

### 5. **Post-Assessment Engagement** (MEDIUM PRIORITY)
**Trigger:** Assessment submitted and scored

**Email Sequence:**

#### Email 1: Immediate - Acknowledgment
- Subject: "Assessment Complete! Your Report is Ready 📊"
- Congratulate completion
- Notify mentor has been emailed
- CTA: "View Your Results" (if premium feature)

#### Email 2: Day 7 - Reflect & Discuss
- Subject: "Have You Discussed Your Results with [Mentor Name]?"
- Prompt conversation: "Here are 3 questions to ask your mentor"
- CTA: "Schedule a Mentor Call" (if calendar feature exists)

#### Email 3: Day 30 - Next Assessment
- Subject: "Ready for Your Next Growth Step? 🚀"
- Suggest related assessments based on previous results
- Show improvement opportunity
- CTA: "Take Another Assessment"

**Implementation Notes:**
- Already have `send_assessment_email()` for immediate
- Add follow-up scheduling in assessment completion background task

---

### 6. **Mentor-Specific Engagement** (MEDIUM PRIORITY)

#### New Apprentice Submission Alert
- Already exists (mentor report email)
- Enhancement: Add "Respond within 48 hours for best engagement"

#### Weekly Digest (if multiple apprentices)
- Subject: "Your Weekly T[root]H Mentorship Summary"
- List apprentices with recent activity
- Highlight pending reviews
- Show apprentices who haven't submitted recently
- CTA: "View Dashboard"

#### Monthly Progress Report
- Subject: "Your Mentorship Impact This Month 📈"
- Stats: Assessments reviewed, avg response time
- Growth trends across apprentices
- Encourage: "You've helped X apprentices grow!"

---

### 7. **Milestone Celebrations** (LOW PRIORITY - DELIGHT)
**Trigger:** Achievement milestones

**Examples:**
- First assessment completed
- 5th assessment completed (growth journey)
- 1-year anniversary in app
- All assessments in category completed

**Email Content:**
- Subject: "🎉 Milestone Achieved: [Achievement Name]"
- Visual badge/achievement graphic
- Personal stats summary
- Encourage sharing or mentor recognition

---

### 8. **Freemium Conversion** (BUSINESS PRIORITY)
**Trigger:** Free user hitting limits or viewing premium content

#### Apprentice - Assessment Limit Reached
- Subject: "Unlock Unlimited Growth Assessments 🔓"
- Show what they're missing
- Pricing comparison
- CTA: "Upgrade to Premium"

#### Mentor - Second Apprentice Invitation Attempt
- Subject: "Want to Mentor More? Upgrade to Premium 👥"
- Explain mentor seat limits
- Show bulk pricing or mentor-gifted seats
- CTA: "Upgrade Your Account"

**Frequency:**
- Immediate upon limit hit
- Follow-up after 3 days
- Final offer after 7 days with limited-time discount (if applicable)

---

## 🛠️ Implementation Roadmap

### Phase 1: Quick Wins (Week 1-2)
1. **Incomplete Assessment Nudge** - Highest engagement impact
2. **New Assessment Published** - Leverage existing content creation

### Phase 2: User Lifecycle (Week 3-4)
3. **Welcome Series** - Reduce early churn
4. **Post-Assessment Engagement** - Drive repeat usage

### Phase 3: Re-Engagement (Month 2)
5. **Inactive User Re-Engagement** - Win back dormant users
6. **Mentor Weekly Digest** - Keep mentors engaged

### Phase 4: Growth & Monetization (Month 3)
7. **Freemium Conversion** - Drive revenue
8. **Milestone Celebrations** - Brand loyalty

---

## 🔧 Technical Requirements

### 1. Email Template Creation
Create Jinja2 templates in `app/templates/email/engagement/`:
- `incomplete_draft_nudge.html`
- `new_assessment_available.html`
- `welcome_apprentice.html`
- `welcome_mentor.html`
- `inactive_reengagement.html`
- `mentor_weekly_digest.html`
- `milestone_celebration.html`

### 2. Email Service Functions
Add to `app/services/email.py`:
```python
def send_draft_reminder_email(...)
def send_new_template_announcement_email(...)
def send_welcome_email(...)
def send_inactive_user_email(...)
def send_mentor_weekly_digest_email(...)
def send_milestone_email(...)
```

### 3. Database Tracking
Consider adding `email_log` table:
```python
class EmailLog(Base):
    __tablename__ = "email_logs"
    
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"))
    email_type = Column(String)  # "draft_reminder", "new_template", etc.
    sent_at = Column(DateTime)
    context = Column(JSON)  # draft_id, template_id, etc.
```

**Purpose:** Prevent duplicate sends, track campaign effectiveness

### 4. Scheduled Jobs System
**Options:**

#### Option A: Cron + Management Script (Simple)
```bash
# crontab
0 9 * * * /path/to/venv/bin/python /app/scripts/send_daily_emails.py
```

Create `scripts/send_daily_emails.py`:
- Query for users matching each campaign criteria
- Send emails via existing email service
- Log results

#### Option B: Celery + Redis (Scalable)
- Add Celery configuration
- Create periodic tasks for each campaign
- Better for high-volume users

#### Option C: Cloud Scheduler + HTTP Endpoint (Cloud-Native)
- Create `/admin/email-campaigns/run-daily` endpoint
- Secure with admin auth token
- Schedule via Google Cloud Scheduler
- Logs in Cloud Run

**Recommendation:** Start with Option A (cron script), migrate to Option C when scaling

### 5. User Activity Tracking Enhancement
Add `last_activity_at` to User model:
```python
last_activity_at = Column(DateTime, nullable=True)
```

Update on:
- Login (Firebase auth)
- Assessment draft creation/update
- Assessment submission
- Mentor report view

**Alternative:** Derive from `MAX(AssessmentDraft.updated_at, Assessment.created_at)`

---

## 📈 Success Metrics

### Email Campaign KPIs
Track in `email_log` or external analytics:

1. **Delivery Rate:** % emails successfully delivered
2. **Open Rate:** % emails opened (SendGrid tracking)
3. **Click Rate:** % clicked CTA links (deep link tracking)
4. **Conversion Rate:** % completed target action (assessment, upgrade)
5. **Unsubscribe Rate:** % opted out (must respect)

### Business Impact Metrics
1. **Assessment Completion Rate:** % drafts completed within 14 days
2. **User Retention:** % users active 30 days after signup
3. **Free-to-Premium Conversion:** % upgraded after freemium email
4. **Mentor Engagement:** % mentors viewing reports within 48 hours

---

## 🚨 Best Practices & Considerations

### 1. Email Frequency Caps
- Max 1 email per day per user (except transactional)
- Max 3 marketing emails per week
- Store user preferences for frequency

### 2. Unsubscribe Compliance
- Add unsubscribe link to all marketing emails
- Respect opt-outs immediately
- Transactional emails (assessment complete, mentor report) exempt from opt-out

### 3. Personalization
- Use user's name, mentor's name, apprentice names
- Reference specific assessments/templates by name
- Include progress percentages

### 4. Deep Linking
- All CTAs should deep link to specific app screens
- Format: `trooth://assessment/draft/{draft_id}`
- Fallback to web app if mobile not installed

### 5. A/B Testing
- Test subject lines for each campaign
- Test send times (morning vs evening)
- Test content variations (short vs detailed)

### 6. Spam Prevention
- Use verified SendGrid domain
- SPF/DKIM/DMARC configured
- Avoid spam trigger words
- Clear subject lines

---

## 🎨 Email Design Principles

### Visual Consistency
- Use existing T[root]H brand colors (black, gold, grey)
- Unkempt font for logo, Poppins for body (web fonts in email)
- Mobile-responsive templates (60%+ users on mobile)

### Content Guidelines
- Subject lines: 40-50 characters optimal
- Preview text: 80-100 characters (shows in inbox)
- Body: Scannable, bullet points, clear CTA
- Single primary CTA button (not multiple competing actions)

### Tone of Voice
- Encouraging, supportive (spiritual growth focus)
- Avoid pushy sales language
- Mentor/apprentice relationship language
- Biblical references where appropriate

---

## � Push Notification Evaluation

### Campaign Suitability for Push Notifications

Each email campaign rated for push notification effectiveness:

| Campaign | Push Priority | Rationale | Recommended Push Strategy |
|----------|---------------|-----------|---------------------------|
| **Incomplete Assessment Nudge** | 🔥 **EXCELLENT** | Time-sensitive, action-oriented, clear CTA | Yes - send push at optimal times |
| **New Assessment Published** | ⭐ **VERY GOOD** | Fresh content, immediate availability | Yes - but batch daily to avoid spam |
| **Welcome Series** | ✅ **GOOD** | Onboarding critical moment | Yes - but limit to 1-2 key messages |
| **Post-Assessment Engagement** | ⭐ **VERY GOOD** | Timely feedback loop, discussion prompt | Yes - especially "mentor responded" |
| **Inactive User Re-Engagement** | ⚠️ **MODERATE** | May feel intrusive if dormant too long | Cautious - only after 14+ days |
| **Mentor Weekly Digest** | ❌ **EMAIL ONLY** | Too much info for push format | No - digest better suited for email |
| **Milestone Celebrations** | ✅ **GOOD** | Positive reinforcement, delight factor | Yes - celebratory, unexpected joy |
| **Freemium Conversion** | ⚠️ **MODERATE** | Can feel salesy via push | Cautious - use sparingly, value-focused |

---

### 🔥 Priority 1: Implement Push Notifications ASAP

#### 1. **Incomplete Assessment Nudge** 
**Why Push Works:**
- User already invested time (answered some questions)
- Gentle reminder keeps assessment top-of-mind
- Mobile context: "5 min while waiting in line"
- High conversion potential (studies show 2-3x email open rates)

**Push Notification Examples:**
```
Day 5: "You're 60% through your Faith Assessment! 5 minutes to finish 🌱"

Day 10: "Your mentor is waiting! Finish your assessment to get personalized guidance 📊"

Day 14: "Almost there! Complete your spiritual growth assessment today ✨"
```

**Implementation:**
- Firebase Cloud Messaging (FCM) already set up for Flutter app
- Trigger: Daily cron checks for drafts with `updated_at` > X days
- Deep link: `trooth://assessment/draft/{draft_id}`
- Time: 7 PM local time (post-dinner, pre-bedtime reflection time)

**Best Practices:**
- Personalize with assessment name and % complete
- Limit to 3 total push notifications per draft (avoid annoyance)
- Respect quiet hours (no notifications 10 PM - 8 AM)

---

#### 2. **New Assessment Published**
**Why Push Works:**
- Content freshness creates FOMO
- Users expect new content notifications from spiritual apps
- Immediate availability = immediate action

**Push Notification Examples:**
```
New Template: "New Assessment: 'Prayer Life Inventory' 🙏 Discover your prayer strengths today!"

Category Update: "3 new assessments in Biblical Knowledge added! Start growing 📖"

Mentor Custom: "Your mentor created a personalized assessment for you! Check it out 👀"
```

**Implementation Strategy:**
- **Batch delivery:** If multiple templates published same day, send ONE combined push
- Timing: Morning (8-9 AM) for "start your day with growth" framing
- Segment by user interests (if tracked): Bible study enthusiasts get Bible assessments first
- Include template emoji/icon for visual appeal

**Throttling:**
- Max 1 "new content" push per week to prevent fatigue
- Premium users: All new templates
- Free users: Only major/featured templates (avoid overwhelming)

---

#### 3. **Post-Assessment: Mentor Responded**
**Why Push Works:**
- Transactional notification (user expects response)
- Social element: someone cared enough to review and respond
- High engagement: users want to see mentor feedback

**Push Notification Examples:**
```
Mentor Report Ready: "Your mentor reviewed your Faith Assessment! View their insights 📋"

Mentor Note Added: "[Mentor Name] left you a note on your latest assessment 💬"

Quick Turnaround: "Wow! Your mentor responded in 6 hours. Check their guidance now 🚀"
```

**Implementation:**
- Trigger: When mentor views submitted assessment or adds a mentor note
- Priority: HIGH (transactional, expected)
- Time: Immediately (no batching, no quiet hours override for daytime)
- Include mentor name for personalization

**Rich Notification Options (iOS/Android):**
- Quick action: "View Report" button opens app directly to report
- Preview: Show first line of mentor's note (if text-based)

---

### ⭐ Priority 2: Good Push Candidates

#### 4. **Welcome Series - Simplified**
**Push vs Email Strategy:**
- **Push:** Only 1-2 critical onboarding messages
- **Email:** Full detailed series (3 emails)

**Recommended Push Notifications:**

**Day 0 (Immediate):**
```
"Welcome to T[root]H! 🙏 Take your first assessment and start your growth journey"
```

**Day 3 (ONLY if zero activity):**
```
"Still exploring? Your first assessment takes just 10 minutes 🌱"
```

**Skip:** Day 7 email (too much, email handles this)

**Implementation:**
- Send Day 0 push immediately after account creation
- Day 3 push ONLY if `assessment_count = 0` AND no active drafts
- Deep link: Directly to assessment selection screen

---

#### 5. **Milestone Celebrations**
**Why Push Works:**
- Unexpected delight (surprise factor)
- Positive reinforcement for continued use
- Short, celebratory message ideal for push format

**Push Notification Examples:**
```
First Assessment: "🎉 First assessment complete! You've taken the first step in your spiritual growth"

5th Assessment: "Amazing! 5 assessments completed. You're building a growth habit 🔥"

1-Year Anniversary: "1 year with T[root]H! 🎂 You've completed X assessments. See your progress!"

Streak Milestone: "7 days in a row! Your consistency is inspiring 💪"
```

**Implementation:**
- Trigger: Immediately after milestone achievement
- Time: Real-time (e.g., right when 5th assessment submits)
- Visual: Use emoji liberally for celebratory feel
- CTA: "View Your Stats" → deep link to progress/history screen

**Unique to Push:**
- Immediacy creates dopamine hit (gamification psychology)
- Can include rich notification with badge/achievement graphic
- Consider vibration pattern for extra delight

---

### ⚠️ Priority 3: Use Cautiously

#### 6. **Inactive User Re-Engagement**
**Why Push is Risky:**
- User hasn't engaged in weeks = may perceive push as spam
- Higher uninstall/opt-out risk
- "Why are you bothering me?" sentiment

**When to Push (vs Email Only):**
- **Email first:** 14 days inactive → email re-engagement
- **Push if email opened:** If user opens email but doesn't act → follow up push 2 days later
- **Never push cold:** Don't push to users who haven't engaged in 30+ days

**Push Notification Examples (Conservative):**
```
Email Responders Only: "Still thinking about your growth? Quick 10-min assessment inside 🌿"

Strategic Timing: "Weekend reflection time? New assessments waiting for you 📖"
```

**Best Practices:**
- Require email engagement before push
- Use "pull" language (invitation) not "push" (obligation)
- Provide easy opt-out in notification settings
- Consider NOT using push for this at all (email safer)

---

#### 7. **Freemium Conversion**
**Why Push is Tricky:**
- Can feel too "salesy" and damage trust
- Users hate being sold to via notifications
- High opt-out risk if overused

**When Push is Acceptable:**
- **In-context prompt:** User tries to access locked feature → immediate push with solution
- **Value-first framing:** Focus on benefit, not transaction

**Push Notification Examples (Value-Focused):**

**Apprentice Limit Hit:**
```
❌ Salesy: "Upgrade to Premium for $4.99/month!"
✅ Value-Focused: "Ready to take more assessments? Unlock unlimited growth for less than a coffee ☕"
```

**Mentor Seat Limit:**
```
❌ Pushy: "Buy Premium to add more apprentices!"
✅ Helpful: "Your mentorship is making an impact! Upgrade to guide more apprentices 👥"
```

**Implementation Strategy:**
- Limit: Max 1 conversion push per user per month
- Context: Only after user demonstrates intent (hits limit, views premium content)
- Timing: Immediate when limit hit (in-context), NOT days later
- Provide snooze option: "Remind me later" action button

**Alternative Approach (Safer):**
- Use in-app banners for conversion messaging
- Reserve push for time-limited offers only (e.g., "24-hour discount")

---

### ❌ Priority 4: Email Only (Don't Use Push)

#### 8. **Mentor Weekly Digest**
**Why Push Doesn't Work:**
- Too much information for push notification format
- Users expect digest content in email (inbox = information archive)
- Push truncation makes summary useless

**Example of Why It Fails:**
```
Push: "Weekly Digest: 3 apprentices active, 2 pending reviews, 1 new..." [TRUNCATED]
Better as Email: Full digest with stats, charts, apprentice list, action items
```

**Recommendation:** Email only, possibly with ONE push if critical:
```
Only if urgent: "Urgent: 3 apprentice assessments waiting for your review! 📊"
```

---

## 🔧 Push Notification Technical Implementation

### 1. Firebase Cloud Messaging Setup (Already Exists)
Your Flutter app likely already has FCM configured. Verify:
- `android/app/google-services.json` (Android)
- `ios/Runner/GoogleService-Info.plist` (iOS)
- Flutter `firebase_messaging` package in `pubspec.yaml`

### 2. Backend Integration Required

#### A. Store FCM Tokens
Add to User model:
```python
# app/models/user.py
class User(Base):
    # ... existing fields
    fcm_token = Column(String, nullable=True)  # Firebase Cloud Messaging device token
    push_enabled = Column(Boolean, default=True)  # User opt-in preference
    push_quiet_hours_start = Column(Integer, nullable=True)  # Hour 0-23 (e.g., 22 = 10 PM)
    push_quiet_hours_end = Column(Integer, nullable=True)    # Hour 0-23 (e.g., 8 = 8 AM)
    timezone = Column(String, nullable=True)  # e.g., "America/New_York" for smart timing
```

#### B. Token Registration Endpoint
```python
# app/routes/user.py
@router.post("/users/register-push-token")
async def register_push_token(
    token: str = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Register FCM token for push notifications."""
    current_user.fcm_token = token
    current_user.push_enabled = True
    db.commit()
    return {"message": "Push token registered"}
```

#### C. Push Notification Service
Create `app/services/push_notification.py`:
```python
from firebase_admin import messaging
import logging

logger = logging.getLogger("app.push")

def send_push_notification(
    fcm_token: str,
    title: str,
    body: str,
    data: dict = None,
    deep_link: str = None
):
    """Send push notification via Firebase Cloud Messaging.
    
    Args:
        fcm_token: User's device token
        title: Notification title (bold, ~50 chars)
        body: Notification body (~150 chars)
        data: Custom data payload for app handling
        deep_link: Deep link URL (e.g., trooth://assessment/draft/123)
    """
    try:
        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            data=data or {},
            token=fcm_token,
            android=messaging.AndroidConfig(
                priority='high',
                notification=messaging.AndroidNotification(
                    click_action='FLUTTER_NOTIFICATION_CLICK',
                    channel_id='high_importance_channel',
                )
            ),
            apns=messaging.APNSConfig(
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(
                        sound='default',
                        badge=1,
                    )
                )
            ),
        )
        
        if deep_link:
            message.data['deep_link'] = deep_link
        
        response = messaging.send(message)
        logger.info(f"Push sent successfully: {response}")
        return True
        
    except Exception as e:
        logger.error(f"Push notification failed: {e}")
        return False


# Specific notification functions
def send_draft_reminder_push(user: User, draft: AssessmentDraft, progress_pct: int):
    """Send push reminder for incomplete draft."""
    if not user.fcm_token or not user.push_enabled:
        return False
    
    return send_push_notification(
        fcm_token=user.fcm_token,
        title="Finish Your Assessment! 🌱",
        body=f"You're {progress_pct}% through. Just a few more minutes!",
        data={
            'type': 'draft_reminder',
            'draft_id': draft.id,
        },
        deep_link=f"trooth://assessment/draft/{draft.id}"
    )


def send_new_template_push(user: User, template_name: str, template_id: str):
    """Send push for new assessment template."""
    if not user.fcm_token or not user.push_enabled:
        return False
    
    return send_push_notification(
        fcm_token=user.fcm_token,
        title="New Assessment Available! ✨",
        body=f"Start '{template_name}' and continue your growth journey",
        data={
            'type': 'new_template',
            'template_id': template_id,
        },
        deep_link=f"trooth://assessment/template/{template_id}"
    )


def send_mentor_report_ready_push(user: User, mentor_name: str, assessment_id: str):
    """Send push when mentor reviews assessment."""
    if not user.fcm_token or not user.push_enabled:
        return False
    
    return send_push_notification(
        fcm_token=user.fcm_token,
        title="Your Mentor Responded! 📋",
        body=f"{mentor_name} reviewed your assessment. See their insights now",
        data={
            'type': 'mentor_report',
            'assessment_id': assessment_id,
        },
        deep_link=f"trooth://assessment/report/{assessment_id}"
    )
```

### 3. Scheduled Push Jobs
Same cron system as emails, but with additional logic:

```python
# scripts/send_push_notifications.py
from datetime import datetime, timedelta
from app.services.push_notification import send_draft_reminder_push
from app.db import SessionLocal
from app.models import User, AssessmentDraft

def send_daily_draft_reminders():
    """Run daily at 7 PM to send draft reminder pushes."""
    db = SessionLocal()
    
    # Find stale drafts (5, 10, 14 days old)
    cutoff_dates = [
        datetime.now(UTC) - timedelta(days=5),
        datetime.now(UTC) - timedelta(days=10),
        datetime.now(UTC) - timedelta(days=14),
    ]
    
    for cutoff in cutoff_dates:
        drafts = db.query(AssessmentDraft).join(User).filter(
            AssessmentDraft.is_submitted == False,
            AssessmentDraft.updated_at < cutoff,
            AssessmentDraft.updated_at > cutoff - timedelta(hours=1),  # Only drafts from that day
            User.push_enabled == True,
            User.fcm_token.isnot(None)
        ).all()
        
        for draft in drafts:
            # Calculate progress
            total_questions = len(draft.template.questions)
            answered = len(draft.answers) if draft.answers else 0
            progress_pct = int((answered / total_questions) * 100)
            
            send_draft_reminder_push(draft.apprentice, draft, progress_pct)
            
    db.close()

if __name__ == "__main__":
    send_daily_draft_reminders()
```

### 4. Flutter App Handling
Update Flutter app to handle push notification taps:

```dart
// lib/main.dart
FirebaseMessaging.onMessageOpenedApp.listen((RemoteMessage message) {
  final data = message.data;
  final deepLink = data['deep_link'];
  
  if (deepLink != null) {
    // Parse deep link and navigate
    if (deepLink.contains('/assessment/draft/')) {
      final draftId = deepLink.split('/').last;
      Navigator.push(
        context,
        MaterialPageRoute(builder: (_) => AssessmentDraftScreen(draftId: draftId))
      );
    }
  }
});
```

---

## 📊 Push Notification Best Practices

### Character Limits
- **Title:** 40-50 characters ideal (65 max before truncation)
- **Body:** 120-150 characters ideal (240 max)
- **Keep it punchy:** Every word counts on lock screen

### Emoji Strategy
- ✅ Use emojis for visual appeal and personality
- ✅ 1-2 emojis per notification (avoid emoji soup)
- ✅ Use category-appropriate emojis (spiritual: 🙏🌱📖✨)
- ❌ Avoid excessive or unprofessional emojis

### Timing Optimization
1. **Incomplete Drafts:** 7-9 PM (evening reflection time)
2. **New Templates:** 8-9 AM (morning motivation)
3. **Mentor Reports:** Immediate (transactional, expected)
4. **Milestones:** Immediate (dopamine hit)
5. **Avoid:** Late night (10 PM - 8 AM), work hours (9 AM - 5 PM on weekdays)

### Frequency Caps (Critical)
- **Max 1 marketing push per day** (non-transactional)
- **Max 3 total pushes per week** (including transactional)
- **Exception:** Mentor report notifications (transactional, always allowed)

### A/B Testing Ideas
1. **Emoji vs No Emoji:** Do emojis increase open rate?
2. **Time of Day:** 7 PM vs 8 PM vs 9 PM
3. **Message Length:** Short punchy vs detailed
4. **Urgency Language:** "Finish now" vs "When you're ready"

---

## 🎯 Recommended Implementation Order

### Phase 1: Critical Push Features (Week 1)
1. ✅ User FCM token storage + registration endpoint
2. ✅ Push notification service (`push_notification.py`)
3. ✅ Draft reminder push (5-day)
4. ✅ Mentor report ready push

### Phase 2: Content & Engagement (Week 2-3)
5. ✅ New template announcement push
6. ✅ Milestone celebration push
7. ✅ Welcome push (Day 0 only)

### Phase 3: Advanced Features (Month 2)
8. ✅ Timezone-aware scheduling
9. ✅ Quiet hours respect
10. ✅ Rich notifications with action buttons
11. ✅ A/B testing framework

### Phase 4: Refinement (Ongoing)
12. ✅ Analytics tracking (open rate, conversion)
13. ✅ User preference granularity (notification types)
14. ✅ Smart frequency capping
15. ✅ Predictive send time optimization

---

## �🔮 Future Enhancements

### 1. AI-Powered Engagement
- Use OpenAI to personalize email content based on assessment results
- Suggest specific growth areas in re-engagement emails
- Custom mentor recommendations per apprentice

### 2. SMS Notifications
- High-urgency reminders (assessment due, mentor waiting)
- Opt-in during onboarding
- Use Twilio integration

### 3. In-App Notifications
- Combine with email for multi-channel approach
- Push notifications via Firebase Cloud Messaging
- Rich notifications with action buttons

### 4. Behavioral Triggers
- Time-of-day optimization (send when user typically opens app)
- Cohort analysis (what works for different user segments)
- Predictive churn modeling (ML to identify at-risk users)

---

## 📝 Next Steps

1. **Prioritize campaigns** based on business goals (retention vs growth vs revenue)
2. **Create email templates** for Phase 1 campaigns
3. **Add email service functions** in `app/services/email.py`
4. **Set up daily cron job** for automated sends
5. **Implement email_log tracking** for analytics
6. **Test with small user segment** before full rollout
7. **Monitor metrics weekly** and iterate

---

## 🤔 Questions to Answer

1. **User preference:** Should users have granular email preferences (e.g., "weekly digest only")?
2. **Send times:** What time zone(s) are most users in? Optimal send time?
3. **Freemium strategy:** How aggressive should conversion emails be?
4. **Mentor involvement:** Should mentors be CC'd on apprentice engagement emails?
5. **Multi-mentor future:** How will emails change when one apprentice has multiple mentors?

---

**Document Owner:** Backend Team  
**Last Updated:** May 8, 2026  
**Status:** DRAFT - Pending Implementation
