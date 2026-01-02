# T[root]H Discipleship - Metrics & Reporting System

## Overview

The metrics system provides real-time usage statistics and automated email reports for tracking user engagement and system health.

## Components

### 1. Metrics Service (`app/services/metrics.py`)

Core service that collects metrics from the database:

- **User Metrics**: Total users, role breakdown, new signups
- **Assessment Metrics**: Completed, started, completion rate, errors
- **Mentorship Metrics**: Active pairs, mentor utilization
- **Invitation Metrics**: Sent, accepted, pending, acceptance rate
- **Agreement Metrics**: Signed, awaiting signatures
- **Template Metrics**: Published vs unpublished
- **Mentor Activity**: Notes added, active mentors

### 2. API Endpoints (`app/routes/metrics.py`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/metrics/dashboard` | GET | Simplified metrics for status page (big numbers) |
| `/metrics/full` | GET | Full metrics with period filter (`day`, `week`, `month`, `all`) |
| `/metrics/send-report` | POST | Manually trigger email report |

**Note**: These endpoints are PUBLIC (no authentication required) but are meant to be accessed via hidden URLs only.

### 3. Email Reports (`app/services/metrics_reports.py`)

Automated email report generation and sending:

- **Weekly Reports**: Summary of the past 7 days
- **Monthly Reports**: Summary of the past 30 days
- **Template**: `app/templates/email/metrics_report.html`

### 4. Status Page (`site_files/status.html`)

Hidden HTML dashboard showing:
- Total users, mentors, apprentices
- Active mentor-apprentice pairs
- Assessments completed
- Agreements signed
- This week's activity
- Pending actions (drafts, agreements, invitations)

**URL**: `https://your-domain.com/status.html` (not linked from other pages)

## Configuration

### Environment Variables

```bash
# Comma-separated list of email addresses to receive reports
METRICS_REPORT_RECIPIENTS=admin@example.com,manager@example.com
```

### Scheduling Reports

Reports can be triggered:

1. **Manually via API**:
   ```bash
   # Send weekly report
   curl -X POST "https://api.your-domain.com/metrics/send-report?report_type=weekly"
   
   # Send to specific recipient
   curl -X POST "https://api.your-domain.com/metrics/send-report?report_type=monthly&recipient=test@example.com"
   ```

2. **Via Cloud Scheduler** (recommended for production):
   ```bash
   # Weekly report every Monday at 9am
   gcloud scheduler jobs create http weekly-metrics-report \
     --schedule="0 9 * * 1" \
     --uri="https://api.your-domain.com/metrics/send-report?report_type=weekly" \
     --http-method=POST
   
   # Monthly report on the 1st of each month at 9am
   gcloud scheduler jobs create http monthly-metrics-report \
     --schedule="0 9 1 * *" \
     --uri="https://api.your-domain.com/metrics/send-report?report_type=monthly" \
     --http-method=POST
   ```

3. **Via cron** (alternative):
   ```bash
   # In crontab
   0 9 * * 1 curl -X POST "https://api.your-domain.com/metrics/send-report?report_type=weekly"
   0 9 1 * * curl -X POST "https://api.your-domain.com/metrics/send-report?report_type=monthly"
   ```

## API Response Examples

### Dashboard Metrics

```json
{
  "status": "success",
  "data": {
    "generated_at": "2026-01-01T12:00:00",
    "totals": {
      "users": 150,
      "mentors": 25,
      "apprentices": 120,
      "active_pairs": 85,
      "assessments_completed": 340,
      "agreements_signed": 75
    },
    "activity": {
      "assessments_this_week": 12,
      "new_users_this_week": 5
    },
    "pending": {
      "drafts_in_progress": 8,
      "agreements_awaiting": 10,
      "invitations_pending": 15
    }
  }
}
```

### Full Metrics

```json
{
  "status": "success",
  "data": {
    "generated_at": "2026-01-01T12:00:00",
    "period": "week",
    "users": {
      "total_users": 150,
      "mentors": 25,
      "apprentices": 120,
      "admins": 5,
      "new_users_in_period": 5,
      "new_mentors_in_period": 1,
      "new_apprentices_in_period": 4
    },
    "assessments": {
      "total_completed": 340,
      "completed_in_period": 12,
      "started_in_period": 15,
      "submitted_in_period": 12,
      "active_drafts": 8,
      "processing": 0,
      "errors": 0,
      "completion_rate": 80.0
    },
    "mentorship": {
      "active_relationships": 85,
      "mentors_with_apprentices": 22,
      "total_mentors": 25,
      "avg_apprentices_per_mentor": 3.86,
      "mentor_utilization_percent": 88.0
    },
    "invitations": {
      "total_invitations": 200,
      "sent_in_period": 8,
      "accepted": 150,
      "pending": 15,
      "expired": 35,
      "acceptance_rate": 75.0
    },
    "agreements": {
      "total_agreements": 100,
      "fully_signed": 75,
      "awaiting_apprentice": 8,
      "awaiting_parent": 2,
      "draft": 15,
      "created_in_period": 5,
      "signed_in_period": 3,
      "completion_rate": 75.0
    },
    "templates": {
      "total_templates": 10,
      "published_templates": 6,
      "unpublished_templates": 4
    },
    "mentor_activity": {
      "total_notes": 500,
      "notes_in_period": 25,
      "active_mentors": 15
    }
  }
}
```

## Security Notes

1. **No Authentication**: Metrics endpoints are public but hidden
2. **No PII**: Reports contain aggregate numbers only, no personal data
3. **Hidden Status Page**: Not linked from any public pages
4. **Obscure URL**: Consider using a random path like `/status-x7k9m.html`

## Future Enhancements

- [ ] Historical trend charts
- [ ] Comparison to previous period
- [ ] Anomaly detection alerts
- [ ] Export to CSV/Excel
- [ ] Role-based access control
- [ ] Real-time WebSocket updates
