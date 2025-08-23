# T[root]H Assessment API

This is the backend for the **T[root]H Assessment** app — a spiritual mentorship and discipleship platform for churches and Christian organizations.

It provides a RESTful API built with **FastAPI**, backed by a **PostgreSQL database**, and includes support for:
- Spiritual assessments (created by admins)
- Mentor/apprentice relationships
- Firebase authentication
- AI-based assessment scoring (via OpenAI)
- Email notifications (SendGrid)

---

## 🔧 Tech Stack

- **Python 3.11+**
- **FastAPI** — web framework
- **SQLAlchemy** — ORM
- **Alembic** — DB migrations
- **PostgreSQL** — database
- **Pydantic v2** — schema validation
- **Firebase Admin SDK** — auth provider
- **SendGrid** — email service
- **OpenAI** — AI scoring
- **Docker** — optional containerization

---

## 🚀 Getting Started

### 1. Clone the Repo
```bash
git clone https://github.com/tmurphy131/trooth_backend.git
cd trooth_backend
```

### 2. Create and activate a virtual environment
```bash
python -m venv venv
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Set environment variables
Create a `.env` file (or export these directly):

```env
DATABASE_URL=postgresql://user:password@localhost:5432/trooth
OPENAI_API_KEY=sk-...
SENDGRID_API_KEY=SG-...
FIREBASE_CREDENTIALS=./firebase_key.json
```

---

## 🗃️ Database Setup

### Run Migrations
```bash
alembic upgrade head
```

### Create a new migration
```bash
alembic revision --autogenerate -m "describe change"
```

---

## 🧪 Running Tests

```bash
pytest
```

Tests are located in the `tests/` directory and use SQLite in-memory DB with monkeypatched Firebase logic.

---

## 🔐 Authentication

Authentication is handled using Firebase ID tokens. You must include:

```http
Authorization: Bearer <firebase_token>
```

Routes are role-protected via:
- `require_admin`
- `require_mentor`
- `require_apprentice`

---

## 🤖 AI Scoring

The assessment answers are scored using OpenAI's GPT-4 model via the `/score` service.

Make sure your `OPENAI_API_KEY` is valid and your usage quota is available.

---

## 📧 Email Notifications

Emails (e.g. mentor notifications) are sent via SendGrid.

You must set the `SENDGRID_API_KEY` and configure sender info inside `app/services/email.py`.

---

## 📂 Project Structure

```
app/
├── main.py                  # FastAPI app entrypoint
├── models/                  # SQLAlchemy ORM models
├── routes/                  # Route modules per feature
├── schemas/                 # Pydantic schemas
├── services/                # Auth, scoring, email
├── db/                      # DB setup and session
tests/
alembic/                     # DB migrations
.env                        # Environment secrets
```

---

## 🛠 Deployment

You can run locally or deploy using Docker (Dockerfile & docker-compose.yml provided):

```bash
docker-compose up --build
```

Make sure to externalize all secrets in a `.env` file and mount them properly.

---

## 🙏 Contributing

Pull requests are welcome. Please include tests and follow the existing code style (Black + isort).

---

## 📄 License

MIT License (c) 2024 tmurphy131