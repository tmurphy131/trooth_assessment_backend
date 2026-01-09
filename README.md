# T[root]H Discipleship API

Backend for the **T[root]H Discipleship** platform — a spiritual mentorship app connecting mentors with apprentices through Bible-based assessments, AI-powered scoring, and growth tracking.

## Table of Contents

- [Overview](#overview)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [Environment Variables](#environment-variables)
- [Database Setup](#database-setup)
- [Running the Server](#running-the-server)
- [API Overview](#api-overview)
- [Assessment System](#assessment-system)
- [AI Scoring](#ai-scoring)
- [Email Notifications](#email-notifications)
- [Testing](#testing)
- [Deployment](#deployment)
- [Seeding Data](#seeding-data)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

T[root]H Discipleship enables:
- **Mentors** to guide apprentices through spiritual growth journeys
- **Apprentices** to take Bible-based assessments and track progress
- **AI-powered scoring** with personalized feedback and recommendations
- **Mentorship agreements** with multi-party digital signatures
- **Progress tracking** across multiple assessment categories

## Tech Stack

| Component | Technology |
|-----------|------------|
| Framework | FastAPI (Python 3.11+) |
| Database | PostgreSQL + SQLAlchemy 2.0 ORM |
| Migrations | Alembic |
| Authentication | Firebase Admin SDK |
| AI Scoring | OpenAI API (gpt-4o-mini) |
| Email | SendGrid |
| Deployment | Docker + Google Cloud Run |
| Testing | pytest |

## Project Structure

```
trooth_assessment_backend/
├── app/
│   ├── main.py                 # FastAPI app initialization
│   ├── config.py               # Firebase initialization
│   ├── db.py                   # Database session factory
│   ├── exceptions.py           # Custom exception classes
│   ├── core/
│   │   ├── settings.py         # Environment-based configuration
│   │   └── logging_config.py   # Structured logging
│   ├── middleware/
│   │   ├── logging.py          # Request correlation IDs
│   │   └── rate_limit.py       # Rate limiting (slowapi)
│   ├── models/                 # SQLAlchemy ORM models
│   ├── schemas/                # Pydantic request/response schemas
│   ├── routes/                 # API endpoint modules
│   ├── services/               # Business logic (AI, email, auth)
│   └── templates/              # Jinja2 email templates
├── alembic/                    # Database migrations
├── scripts/                    # Utility scripts (seeding, etc.)
├── tests/                      # pytest test suite
├── Dockerfile                  # Container definition
├── entrypoint.sh               # Container startup script
├── requirements.txt            # Python dependencies
└── DEPLOYMENT.md               # Detailed deployment guide
```

## Getting Started

### Prerequisites

- Python 3.11+
- PostgreSQL 14+
- Firebase project with service account
- (Optional) OpenAI API key for AI scoring
- (Optional) SendGrid API key for emails

### 1. Clone and Setup Virtual Environment

```bash
git clone https://github.com/your-org/trooth_assessment_backend.git
cd trooth_assessment_backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment

Create a `.env` file in the project root:

```env
# Database
DATABASE_URL=postgresql://trooth_user:your_password@localhost:5432/trooth_db

# Firebase (path to service account JSON)
FIREBASE_CERT_PATH=./firebase_key.json

# OpenAI (optional - falls back to mock scoring if not set)
OPENAI_API_KEY=sk-your-openai-api-key

# SendGrid (optional - logs emails if not set)
SENDGRID_API_KEY=SG.your-sendgrid-api-key
SENDGRID_FROM_EMAIL=noreply@yourdomain.com
SENDGRID_FROM_NAME=T[root]H Discipleship

# App Settings
ENV=development
APP_URL=http://localhost:8000
CORS_ORIGINS=http://localhost:3000,http://localhost:5000
```

### 4. Setup Firebase

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Create a project or use an existing one
3. Go to Project Settings → Service Accounts
4. Generate a new private key
5. Save as `firebase_key.json` in project root

### 5. Run Database Migrations

```bash
# Create the database first
createdb trooth_db

# Run migrations
alembic upgrade head
```

### 6. Start the Server

```bash
uvicorn app.main:app --reload --port 8000
```

Visit `http://localhost:8000/docs` for interactive API documentation.

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | ✅ | PostgreSQL connection string |
| `FIREBASE_CERT_PATH` | ✅* | Path to Firebase service account JSON |
| `FIREBASE_CERT_JSON` | ✅* | Firebase service account as JSON string (alternative to path) |
| `OPENAI_API_KEY` | ❌ | OpenAI API key for AI scoring |
| `SENDGRID_API_KEY` | ❌ | SendGrid API key for emails |
| `SENDGRID_FROM_EMAIL` | ❌ | Sender email address |
| `SENDGRID_FROM_NAME` | ❌ | Sender display name |
| `ENV` | ❌ | Environment: `development`, `staging`, `production` |
| `APP_URL` | ❌ | Base URL for email links |
| `CORS_ORIGINS` | ❌ | Comma-separated allowed origins |
| `SHOW_DOCS` | ❌ | Set to `true` to enable Swagger docs in production |

*One of `FIREBASE_CERT_PATH` or `FIREBASE_CERT_JSON` is required.

---

## Database Setup

### Local PostgreSQL

```bash
# Create user and database
psql -U postgres
CREATE USER trooth_user WITH PASSWORD 'your_password';
CREATE DATABASE trooth_db OWNER trooth_user;
GRANT ALL PRIVILEGES ON DATABASE trooth_db TO trooth_user;
\q

# Run migrations
alembic upgrade head
```

### Cloud SQL (Production)

Use Cloud SQL Auth Proxy for local development against production DB:

```bash
# Start the proxy
./cloud-sql-proxy PROJECT:REGION:INSTANCE --port=5432

# Export connection string
export DATABASE_URL=postgresql://user:pass@127.0.0.1:5432/trooth_db

# Run backend
uvicorn app.main:app --reload
```

### Creating New Migrations

```bash
# Auto-generate migration from model changes
alembic revision --autogenerate -m "Add new column"

# Apply migration
alembic upgrade head

# Rollback
alembic downgrade -1
```

---

## Running the Server

### Development

```bash
uvicorn app.main:app --reload --port 8000
```

### With Docker

```bash
# Build
docker build -t trooth-backend:local .

# Run
docker run -p 8000:8000 \
  -e DATABASE_URL=postgresql://... \
  -e FIREBASE_CERT_PATH=/secrets/firebase_key.json \
  -v $(pwd)/firebase_key.json:/secrets/firebase_key.json:ro \
  trooth-backend:local
```

---

## API Overview

### Authentication

All authenticated endpoints require a Firebase ID token in the `Authorization` header:

```
Authorization: Bearer <firebase_id_token>
```

### Main Endpoint Groups

| Prefix | Description |
|--------|-------------|
| `/health` | Health check endpoint |
| `/users` | User registration and profile |
| `/mentor` | Mentor-specific operations |
| `/apprentice` | Apprentice-specific operations |
| `/templates` | Assessment templates (published) |
| `/admin/templates` | Template management (admin only) |
| `/assessment-drafts` | In-progress assessments |
| `/assessments` | Completed assessments |
| `/generic-assessments` | Generic assessment workflow |
| `/spiritual-gifts` | Spiritual gifts assessment |
| `/master-trooth` | Master T[root]H assessment |
| `/agreements` | Mentorship agreements |
| `/invitations` | Apprentice invitations |
| `/mentor-notes` | Mentor notes on apprentices |
| `/progress` | Progress tracking |
| `/resources/mentor` | Mentor resource guides |
| `/resources/apprentice` | Apprentice growth guides |

### Key Endpoints

```bash
# Health check
GET /health

# User registration (creates user from Firebase token)
POST /users/

# Get current user profile
GET /apprentice/me
GET /mentor/profile

# List published assessment templates
GET /templates/published

# Start an assessment
POST /assessment-drafts/start
Body: {"template_id": "uuid"}

# Auto-save answers
PATCH /assessment-drafts
Body: {"draft_id": "uuid", "answers": {"Q1": "answer"}}

# Submit for scoring
POST /assessment-drafts/submit
Body: {"draft_id": "uuid"}

# View completed assessment
GET /assessments/{assessment_id}

# Invite apprentice (mentor)
POST /invitations/invite-apprentice
Body: {"apprentice_email": "email@example.com", "apprentice_name": "Name"}
```

---

## Assessment System

### Assessment Types

1. **Master T[root]H Assessment** - Comprehensive spiritual assessment
2. **Spiritual Gifts Assessment** - 72 questions identifying spiritual gifts
3. **Bible Book Assessments** - Romans, Samuel, Ephesians, Galatians, etc.

### Assessment Workflow

```
1. Apprentice selects template
         ↓
2. Frontend shows preview (title, description, history)
         ↓
3. POST /assessment-drafts/start → Creates draft
         ↓
4. Apprentice answers questions
         ↓
5. PATCH /assessment-drafts (auto-save on each answer)
         ↓
6. POST /assessment-drafts/submit → Triggers AI scoring
         ↓
7. Backend scores asynchronously
         ↓
8. Assessment status: "done"
         ↓
9. Mentor notified via email
```

### Template Structure

Templates contain:
- Name, description, category
- Questions (multiple choice or open-ended)
- Scoring rubrics for AI evaluation
- `is_master_assessment` flag for official assessments

---

## AI Scoring

### How It Works

1. Assessment submitted → Background task triggered
2. Questions grouped by category
3. Each category scored via OpenAI API call
4. Scoring prompt evaluates:
   - Multiple choice: correct/incorrect
   - Open-ended: qualitative analysis against rubric
5. Returns JSON with scores, recommendations, feedback

### Configuration

```python
# Uses gpt-4o-mini by default
# Temperature: 0.3 for consistency
# Response format: JSON
```

### Fallback

If `OPENAI_API_KEY` is not set, the system uses deterministic mock scoring based on answer length. This allows development/testing without API costs.

---

## Email Notifications

### Email Types

- **Invitation emails** - When mentor invites apprentice
- **Assessment completion** - Mentor notified when apprentice finishes
- **Agreement signing** - Multi-party signature notifications
- **Password reset** - Via Firebase (not backend)

### Configuration

```env
SENDGRID_API_KEY=SG.xxx
SENDGRID_FROM_EMAIL=noreply@yourdomain.com
SENDGRID_FROM_NAME=T[root]H Discipleship
```

If SendGrid is not configured, emails are logged but not sent.

---

## Testing

### Run All Tests

```bash
pytest
```

### Run Specific Tests

```bash
# Single file
pytest tests/test_invitations.py

# With verbose output
pytest -v -s

# With coverage
pytest --cov=app --cov-report=html
```

### Test Database

Tests use SQLite in-memory database with `StaticPool` for connection sharing. No external database required.

### Test Fixtures

```python
# Available fixtures in tests/conftest.py
@pytest.fixture
def client():      # TestClient with test DB
@pytest.fixture
def admin_user():  # User with role=admin
@pytest.fixture
def mentor_user(): # User with role=mentor
@pytest.fixture
def apprentice_user(): # User with role=apprentice
```

---

## Deployment

Full deployment instructions are in [DEPLOYMENT.md](DEPLOYMENT.md).

### Quick Summary

1. **Build image** (on Apple Silicon, use `--platform linux/amd64`)
   ```bash
   docker buildx build --platform linux/amd64 -t gcr.io/PROJECT/trooth-backend:latest --push .
   ```

2. **Create secrets** in Secret Manager:
   - `DATABASE_URL`
   - `FIREBASE_CERT_JSON`
   - `SENDGRID_API_KEY`
   - `OPENAI_API_KEY`

3. **Deploy to Cloud Run**
   ```bash
   gcloud run deploy trooth-backend \
     --image=gcr.io/PROJECT/trooth-backend:latest \
     --region=us-east4 \
     --set-secrets=DATABASE_URL=DATABASE_URL:latest,... \
     --allow-unauthenticated
   ```

---

## Seeding Data

### Seed Assessment Templates

Assessment templates are seeded via Python scripts that can run locally or as Cloud Run Jobs.

```bash
# Spiritual Gifts Assessment (72 questions)
python scripts/seed_spiritual_gifts.py --version 1 --publish

# Master T[root]H Assessment
python setup_master_assessment.py

# Bible Book Assessments (examples)
python setup_romans_assessment.py
python setup_galatians_philippians_assessment.py
python setup_ephesians_colossians_assessment.py
```

### Run Seeder as Cloud Run Job

```bash
gcloud run jobs create seed-assessment \
  --image gcr.io/PROJECT/trooth-backend:latest \
  --region us-east4 \
  --command python \
  --args setup_galatians_philippians_assessment.py \
  --set-secrets DATABASE_URL=DATABASE_URL:latest \
  --max-retries=1

gcloud run jobs execute seed-assessment --region us-east4
```

### Seed Agreement Template

The mentorship agreement template is auto-seeded on first startup from `MENTOR_AGREEMENT.md`.

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Run tests (`pytest`)
4. Run linter (`black . && isort .`)
5. Commit changes (`git commit -m 'Add amazing feature'`)
6. Push to branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

### Code Style

- Use `black` for formatting
- Use `isort` for import sorting
- Follow FastAPI conventions for route handlers
- Add tests for new endpoints


