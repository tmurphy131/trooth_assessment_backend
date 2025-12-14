# T[root]H Assessment - AI Agent Instructions (Backend)

## Project Overview
FastAPI-based backend for T[root]H spiritual mentorship platform. Handles authentication (Firebase Admin SDK), PostgreSQL data persistence, AI-powered assessment scoring (OpenAI), email notifications (SendGrid), and RESTful API for Flutter mobile frontend.

**Critical Context**: This is a role-based system (Admin/Mentor/Apprentice) with complex workflows around assessments, mentorship agreements, and invitations.

## Architecture

### Tech Stack
- **Framework**: FastAPI 0.104+ (async Python web framework)
- **Database**: PostgreSQL with SQLAlchemy 2.0 ORM + Alembic migrations
- **Authentication**: Firebase Admin SDK (verifies Firebase ID tokens from mobile clients)
- **AI Scoring**: OpenAI API (gpt-4o-mini) for assessment evaluation
- **Email**: SendGrid API for transactional emails (invites, reports, agreements)
- **Deployment**: Docker + Google Cloud Run (see `DEPLOYMENT.md` for exact commands)
- **Testing**: pytest with SQLite in-memory test DB

### Directory Structure
```
app/
├── main.py              # FastAPI app initialization, CORS, middleware, route registration
├── config.py            # Firebase initialization
├── db.py                # Database session factory
├── core/
│   ├── settings.py      # Environment-based configuration
│   └── logging_config.py # Structured logging setup
├── middleware/
│   ├── logging.py       # Request correlation IDs, timing
│   └── rate_limit.py    # Rate limiting (slowapi)
├── models/              # SQLAlchemy ORM models (User, Assessment, Template, etc.)
├── schemas/             # Pydantic request/response schemas
├── routes/              # API endpoint modules (user, assessment, mentor, etc.)
├── services/
│   ├── ai_scoring.py    # OpenAI integration for category-based scoring
│   ├── ai_scoring_master.py  # Master assessment wrapper (adds top-3 categories)
│   ├── ai_scoring_generic.py # Fallback numeric scoring without AI
│   ├── email.py         # SendGrid email service
│   └── auth.py          # Firebase token verification, role dependencies
└── templates/           # Jinja2 email templates

alembic/                 # Database migrations
tests/                   # pytest test suite (30+ test files)
```

### Request Flow
1. **Client** sends request with Firebase ID token in `Authorization: Bearer <token>` header
2. **LoggingMiddleware** adds correlation ID, logs request start
3. **Route handler** calls `get_current_user()` dependency → verifies Firebase token → loads User from DB
4. **Role dependency** (`require_mentor`, `require_admin`) checks user role, raises 403 if unauthorized
5. **Business logic** executes (queries DB, calls AI/email services)
6. **Response** includes `X-Correlation-ID` and `X-Process-Time` headers for debugging

## Critical Patterns

### Authentication & Authorization
```python
# Verify Firebase token and load user
from app.services.auth import get_current_user
user: User = Depends(get_current_user)

# Role-based access control
from app.services.auth import require_mentor, require_admin
mentor: User = Depends(require_mentor)
admin: User = Depends(require_admin)
```

**Key files**: `app/services/auth.py`, `app/models/user.py`

**Gotcha**: Firebase SDK init happens in `app/config.py::init_firebase()` - supports both `FIREBASE_CERT_JSON` env var (JSON string) and `FIREBASE_CERT_PATH` (file path). Production uses Secret Manager secret mounted as env var.

### Database Patterns
```python
# Always use dependency injection for sessions
from app.db import get_db
db: Session = Depends(get_db)

# Eager loading for relationships (avoid N+1 queries)
from sqlalchemy.orm import joinedload
assessment = db.query(Assessment).options(
    joinedload(Assessment.template).joinedload(AssessmentTemplate.questions)
).filter(Assessment.id == assessment_id).first()

# Use UUID strings for primary keys
import uuid
user = User(id=str(uuid.uuid4()), email="...", role=UserRole.mentor)
```

**Key files**: `app/db.py`, `app/models/*`

**Testing tip**: Tests use SQLite in-memory with `StaticPool` to share DB across test client and test fixtures. See `tests/conftest.py`.

### AI Scoring Workflow (Critical Business Logic)

#### Assessment Submission Flow
1. Apprentice submits draft via `POST /assessment-drafts/submit`
2. Endpoint creates `Assessment` record, kicks off background task `_process_assessment_background(assessment_id)`
3. Background worker:
   - Loads assessment + questions from template
   - Calls `score_assessment_by_category(answers, questions)` (from `app/services/ai_scoring.py`)
   - Persists scores JSON to `Assessment.scores`
   - Sets `Assessment.status = "done"`
   - Sends mentor email notification with summary

#### Scoring Strategy (see `AI_SCORING_DETAILS.md`)
- **Category-based scoring**: Groups questions by category, one OpenAI API call per category
- **Prompt design**: Treats multiple-choice as factual (correct/incorrect), open-ended as qualitative
- **Output**: JSON with `score` (1-10), `recommendation`, `question_feedback` array
- **Fallback**: If OpenAI API key missing/invalid, uses `generate_mock_detailed_scores()` (deterministic based on answer length)
- **Master wrapper**: `score_master_assessment()` adds `version: "master_v1"`, `top3` categories

**Key files**: `app/services/ai_scoring*.py`, `app/routes/assessment_draft.py`

**Gotcha**: OpenAI calls use `response_format={"type":"json_object"}` + `temperature=0.3` + retry logic for JSON parsing failures.

### Email Notifications
```python
from app.services.email import send_invitation_email, send_mentor_report_email

# All email sends include try-catch, log on failure (don't crash request)
try:
    send_invitation_email(to_email, mentor_name, invite_token)
except Exception as e:
    logger.error(f"Email send failed: {e}")
```

**Templates**: Jinja2 HTML templates in `app/templates/`, e.g., `mentor_report_email_template.html`

**Key files**: `app/services/email.py`, `mentor_report_email_template.html`

**Testing**: If SendGrid API key not set, emails are logged only (no actual send).

## Database Migrations

### Creating Migrations
```bash
# Auto-generate migration from model changes
alembic revision --autogenerate -m "Add new column"

# Edit generated migration in alembic/versions/ - ALWAYS review auto-generated SQL

# Apply migration
alembic upgrade head

# Rollback one version
alembic downgrade -1
```

**Key files**: `alembic/env.py`, `alembic/versions/*`

**Gotcha**: Alembic uses `DATABASE_URL` from env var, NOT from `alembic.ini`. See `alembic/env.py:12-15`.

### Migration Best Practices
- Always test migrations on dev DB before production
- Use `batch_alter_table` for SQLite compatibility (even though prod is PostgreSQL)
- Add indexes for foreign keys and frequently queried columns
- Include both `upgrade()` and `downgrade()` logic

## API Endpoint Conventions

### Route Organization
Each feature has its own router module in `app/routes/`:
- `user.py` - User CRUD, profile
- `assessment.py`, `assessment_draft.py` - Assessment workflow
- `mentor.py` - Mentor-specific endpoints (view apprentices, submissions)
- `agreements.py` - Mentorship agreement workflow
- `invite.py` - Invitation system
- `templates.py`, `admin_template.py` - Assessment template management

**Pattern**: Import router in `app/main.py`, register with `app.include_router(router, prefix="/...", tags=["..."])`

### Response Patterns
```python
# Success (200/201)
return {"message": "Success", "data": {...}}

# Custom exceptions (converted to HTTP responses via exception handlers)
from app.exceptions import NotFoundException, ValidationException, ForbiddenException
raise NotFoundException(f"Assessment {id} not found")  # → 404
raise ValidationException("Invalid email format")      # → 400
raise ForbiddenException("Not your apprentice")       # → 403
```

**Key files**: `app/exceptions.py`, `app/main.py` (exception handlers at bottom)

### CORS Configuration
```python
# In main.py - configured for development, restrict in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,  # ["*"] in dev, specific domains in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Testing Strategy

### Running Tests
```bash
# All tests
pytest

# Specific file
pytest tests/test_invitations.py

# Verbose with output
pytest -v -s

# Coverage report
pytest --cov=app --cov-report=html
```

### Test Fixtures (from `tests/conftest.py`)
```python
@pytest.fixture
def client():  # TestClient with in-memory DB
@pytest.fixture
def admin_user():  # User with role=admin
@pytest.fixture
def mentor_user():  # User with role=mentor
@pytest.fixture
def apprentice_user():  # User with role=apprentice
@pytest.fixture
def auth_headers(user):  # Mock Authorization header (bypasses Firebase)
```

### Test Patterns
```python
# Override auth dependency to skip Firebase verification
def mock_current_user():
    return mentor_user

app.dependency_overrides[get_current_user] = mock_current_user

# Test API call
response = client.post("/invitations/invite-apprentice", 
    json={"apprentice_email": "test@example.com", "apprentice_name": "Test"},
    headers={"Authorization": "Bearer fake-token"})
assert response.status_code == 200
```

**Key insight**: Tests override `get_current_user` dependency to inject test users without Firebase token verification.

## Deployment (Google Cloud Run)

### Required Secrets (in Secret Manager)
- `DATABASE_URL` - PostgreSQL connection string (Cloud SQL socket or TCP)
- `FIREBASE_CERT_JSON` - Firebase service account JSON (entire JSON as string)
- `SENDGRID_API_KEY` - SendGrid API key
- `OPENAI_API_KEY` - OpenAI API key

### Build & Deploy Commands (from `DEPLOYMENT.md`)
```bash
# Build amd64 image (required on Apple Silicon)
docker buildx build --platform linux/amd64 -t gcr.io/PROJECT/trooth-backend:latest --push .

# Deploy to Cloud Run with secrets
gcloud run deploy trooth-backend \
  --image=gcr.io/PROJECT/trooth-backend:latest \
  --region=us-east4 \
  --set-secrets=DATABASE_URL=DATABASE_URL:latest,FIREBASE_CERT_JSON=FIREBASE_CERT_JSON:latest,... \
  --set-env-vars=ENV=development,APP_URL=https://trooth-assessment-dev.onlyblv.com \
  --allow-unauthenticated
```

**Key files**: `Dockerfile`, `entrypoint.sh`, `DEPLOYMENT.md`

**Gotcha**: Container must bind to `PORT` env var (Cloud Run sets it, usually 8080). Uvicorn command in `Dockerfile`: `CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}`

### Local Development
```bash
# Using Docker
docker build -t trooth-backend:local .
docker run -p 8000:8000 -v $(pwd)/firebase_key.json:/secrets/firebase_key.json:ro \
  -e FIREBASE_CERT_PATH=/secrets/firebase_key.json \
  -e DATABASE_URL=postgresql://... \
  trooth-backend:local

# Using venv
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head  # Run migrations
uvicorn app.main:app --reload --port 8000
```

## Common Tasks

### Adding a New Endpoint
1. Create/update route module in `app/routes/my_feature.py`
2. Define Pydantic schemas in `app/schemas/my_feature.py`
3. Add route handler with appropriate auth dependency
4. Register router in `app/main.py`
5. Add tests in `tests/test_my_feature.py`
6. Update `MOBILE_API_GUIDE.md` with endpoint documentation

### Adding a New Database Model
1. Create model in `app/models/my_model.py` (inherit from `Base`)
2. Import model in `app/db.py` (ensures Alembic picks it up)
3. Generate migration: `alembic revision --autogenerate -m "Add MyModel"`
4. Review and edit migration file
5. Test migration: `alembic upgrade head` (dev DB)
6. Update test fixtures in `tests/conftest.py` if needed

### Debugging Production Issues
1. Check Cloud Run logs: `gcloud logging read 'resource.type=cloud_run_revision AND resource.labels.service_name=trooth-backend' --limit=200`
2. Look for correlation ID in logs (from `X-Correlation-ID` response header)
3. Check secrets are mounted: `gcloud run services describe trooth-backend --region=us-east4 --format=json | jq '.spec.template.spec.containers[0].env'`
4. Verify service account has Secret Manager access: `gcloud projects get-iam-policy PROJECT --flatten="bindings[*]" --filter="bindings.members:serviceAccount:*"`

## Project-Specific Gotchas

### 1. Mentorship Agreement System
- **3-party signing**: mentor → apprentice → parent (if under 18)
- **Token-based**: Each party gets unique token in email link for public access
- **Status flow**: `draft` → `awaiting_apprentice` → `awaiting_parent` → `fully_signed`
- **Implementation**: `app/routes/agreements.py`, `app/models/agreement.py`
- **Template seeding**: On startup, seeds initial agreement template from `MENTOR_AGREEMENT.md` if DB empty

### 2. Multi-Mentor Future Design
- Currently: 1 mentor per apprentice (implicit via `mentor_apprentice` table)
- Future: Multiple mentors per apprentice (see `MULTI_MENTOR_DESIGN.md`)
- **When adding features**: Don't assume single mentor - check if multi-mentor support needed

### 3. Assessment Template vs Instance
- **Template** (`AssessmentTemplate`): Reusable blueprint, has `published` flag
- **Draft** (`AssessmentDraft`): In-progress instance, can be resumed
- **Assessment**: Completed & scored instance (immutable)
- Only published templates shown to apprentices via `GET /templates/published`

### 4. Background Task Execution
- FastAPI background tasks run in request worker thread, not separate process
- For long-running tasks (AI scoring), use `BackgroundTasks` parameter
- Current pattern: `_process_assessment_background()` in `app/routes/assessment_draft.py`
- **Future improvement**: Consider Celery/Redis for distributed task queue

### 5. OpenAI API Call Reliability
- AI scoring can fail (API errors, rate limits, JSON parsing issues)
- Always has fallback: `generate_mock_detailed_scores()` based on answer length
- Retry logic: 3 attempts with exponential backoff in `score_category_with_feedback()`
- **Monitor**: Check logs for "OpenAI API error" messages

## Documentation Resources

**This repo**:
- `DEPLOYMENT.md` - Complete deployment guide with exact commands
- `MOBILE_API_GUIDE.md` - API documentation for mobile frontend integration
- `AI_SCORING_DETAILS.md` - AI scoring architecture and improvement proposals
- `MULTI_MENTOR_DESIGN.md` - Future multi-mentor support design (not implemented)

**Frontend repo** (`trooth_assessment`):
- `REQUIREMENTS.md` - Original product specification
- `MENTOR_SECTION_REQUIREMENTS.md` - Mentor UI detailed requirements
- `INVITE_SYSTEM_SUMMARY.md` - Invitation system implementation summary

## Security Best Practices
- **Never log sensitive data**: Mask emails in logs, never log full Firebase tokens
- **Validate on backend**: Frontend role checks are UI-only - always verify on backend
- **Use parameterized queries**: SQLAlchemy ORM prevents SQL injection
- **Rate limiting**: Enabled via `slowapi` (5 requests/second per IP by default)
- **CORS**: Restrict `allow_origins` in production (currently `["*"]` in dev)
