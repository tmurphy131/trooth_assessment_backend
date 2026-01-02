# T[root]H Discipleship – Project Requirements

## 🧠 Project Overview

T[root]H (Truth) Assessment is a spiritual mentorship platform designed to help mentors guide apprentices through intentional discipleship. Apprentices complete in-depth spiritual assessments, and the platform uses AI to score responses and recommend mentoring strategies.

---

## 🔑 Functional Requirements

### 👤 User Accounts
- Users must sign up using Firebase Authentication (Google or email/password).
- Users select a role: **Mentor** or **Apprentice**.
- Mentors can invite apprentices via email.
- Account roles determine access to specific APIs and routes.

### 📋 Assessments
- Apprentices can:
  - Start new assessments based on published templates.
  - Save drafts and resume later.
  - Submit completed assessments for scoring.
- Mentors receive:
  - Email notifications with scores and recommendations.
  - Access to dashboards to track apprentice progress.

### 🧠 AI Scoring
- Uses OpenAI API to evaluate assessment answers.
- Scores each response from 1–10.
- Calculates overall and category scores.
- Suggests mentoring focus areas.

### 📊 Admin Panel
- Admins can:
  - Create and manage assessment templates.
  - Add and order questions by category.
  - Clone existing templates.

---

## 📂 Data Models

### Users
- `id`, `name`, `email`, `role`, `created_at`

### Mentor-Apprentice Relationship
- `mentor_id`, `apprentice_id`

### Apprentice Invitations
- `token`, `mentor_id`, `apprentice_email`, `expires_at`, `accepted`

### Assessment Drafts
- `id`, `apprentice_id`, `answers`, `last_question_id`, `is_submitted`, `score`, `template_id`

### Assessment Responses (Final)
- `id`, `draft_id`, `question_id`, `answer`, `score`, `category`

### Assessment Templates
- `id`, `name`, `description`, `is_published`

### Questions and Categories
- `question_id`, `text`, `category_id`
- `category_id`, `name`

---

## ⚙️ Technical Stack

### Backend
- **FastAPI** + Pydantic v2
- PostgreSQL 15
- SQLAlchemy ORM + Alembic migrations
- Firebase Admin SDK (auth + token verification)
- SendGrid (email delivery)
- Docker + Docker Compose

### AI
- OpenAI GPT model (via `openai` Python SDK)
- Custom scoring prompts per category

---

## 🔐 Security

- Firebase Auth token validation with role-based middleware
- Invite tokens are time-limited and unique
- Admin-only routes protected with `require_admin`

---

## 🧪 Testing

- Pytest + HTTPX test client
- Token mocking utilities
- Factory methods for test users, drafts, templates
- Coverage includes:
  - User flows
  - Draft/resume logic
  - Template publishing and cloning
  - AI scoring + email dispatch

---

## 📦 Deployment

- Runs fully in Docker using `docker-compose`
- `.env` file used to configure:
  - `DATABASE_URL`
  - `SENDGRID_API_KEY`
  - `FIREBASE_KEY_PATH`
  - `OPENAI_API_KEY`

---

## ✅ Future Enhancements

- Web or Flutter frontend UI
- In-app chat or mentorship check-ins
- Custom mentor notes on assessments
- Versioning of templates and questions
- Admin UI panel for content managers

---

## 📎 File Structure (Key Directories)

