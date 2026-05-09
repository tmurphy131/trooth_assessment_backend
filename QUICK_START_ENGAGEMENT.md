# Engagement Campaign Implementation - Quick Start

## Summary

**Good news:** Most infrastructure already exists! 🎉

### ✅ Already Built (No Migration Needed)
- **Push notification infrastructure** - DeviceToken table exists
- **Email logging** - EmailSendEvent table exists  
- **SendGrid integration** - Working email service
- **Jinja2 templating** - Template system ready

### 🚧 Requires Alembic Migration

**Two migrations created and ready to run:**

1. **`20260508_add_user_engagement_fields.py`** - REQUIRED  
   Adds to User table:
   - `last_activity_at` - Track inactive users
   - `push_enabled` - User opt-in preference
   - `push_quiet_hours_start/end` - Respect quiet hours
   - `timezone` - Smart timezone scheduling

2. **`20260508_expand_email_tracking.py`** - OPTIONAL (recommended)  
   Adds to EmailSendEvent table:
   - `campaign_type` - Filter by campaign
   - `context` - Flexible JSON metadata
   - `delivery_status` - Track bounces/opens

## 🚀 Run Migrations Now

```bash
cd /Users/tmoney/Developer/trooth_assessment_backend
source .venv/bin/activate

# Run both migrations
alembic upgrade head

# Verify migrations applied
alembic current
```

**Expected output:**
```
INFO  [alembic.runtime.migration] Running upgrade add_device_tokens_push -> 20260508_add_user_engagement_fields, Add user engagement tracking fields
INFO  [alembic.runtime.migration] Running upgrade 20260508_add_user_engagement_fields -> 20260508_expand_email_tracking, Expand email tracking for campaigns
```

## ✅ Model Updates (Already Done)

I've already updated:
- ✅ `app/models/user.py` - Added 5 new columns
- ✅ `app/models/email_send_event.py` - Added 3 new columns

## 📅 Implementation Timeline

### Week 1 (Immediate)
1. ✅ Run migrations (5 minutes)
2. Create email template for draft reminders (2-3 hours)
3. Build `scripts/send_draft_reminders.py` (2-3 hours)
4. Test locally (1 hour)

### Week 2
5. Schedule cron job for daily sends
6. Create new template notification email
7. Add push notification service code

### Week 3-4
8. Launch first campaigns
9. Monitor metrics
10. Iterate based on data

## 🎯 First Campaign to Build: Incomplete Draft Reminders

**Why start here:**
- Highest ROI - directly drives assessment completion
- You already have the data (AssessmentDraft table)
- Simple logic - find drafts 5/10/14 days old
- Clear user value - helps them finish what they started

**Files to Create:**
1. `app/templates/email/campaigns/incomplete_draft_reminder.html` - Email template
2. `scripts/send_draft_reminders.py` - Daily batch script
3. Add `send_draft_reminder_email()` to `app/services/email.py`

**Example template structure:** (see ENGAGEMENT_EXECUTION_PLAN.md for full code)

## 📊 Success Metrics to Watch

Track after launch:
- **Draft completion rate within 14 days** - Target: +15-20% improvement
- **Email open rate** - Target: 20-30%
- **Click rate** - Target: 5-10%
- **Unsubscribe rate** - Target: <1%

## 🔗 Full Documentation

- **Strategy:** [ENGAGEMENT_EMAIL_STRATEGY.md](ENGAGEMENT_EMAIL_STRATEGY.md)
- **Execution Plan:** [ENGAGEMENT_EXECUTION_PLAN.md](ENGAGEMENT_EXECUTION_PLAN.md)

Both documents include:
- All 8 campaign types with examples
- Push notification evaluation
- Complete code examples
- Phased rollout plan
- Risk mitigation strategies

## ❓ Quick Q&A

**Q: Do I need to rebuild my Flutter app?**  
A: Not immediately. Push notification handling can be added incrementally.

**Q: Will this slow down my API?**  
A: No. Activity tracking uses async updates. Campaigns run via cron jobs, not in request cycle.

**Q: What if users complain about too many emails?**  
A: Start conservative (only draft reminders). Add preference center later. Monitor unsubscribe rate closely.

**Q: How do I test before sending to real users?**  
A: Run scripts locally, filter to your own email address first. Once verified, expand to small user subset.

---

## 🎬 Action Items Right Now

1. **Run migrations:**
   ```bash
   cd trooth_assessment_backend
   source .venv/bin/activate
   alembic upgrade head
   ```

2. **Verify in database:**
   ```sql
   -- Check new columns exist
   SELECT column_name FROM information_schema.columns 
   WHERE table_name = 'users' AND column_name IN 
   ('last_activity_at', 'push_enabled', 'timezone');
   ```

3. **Read execution plan** for next steps

That's it! You're ready to start building engagement campaigns. 🚀
