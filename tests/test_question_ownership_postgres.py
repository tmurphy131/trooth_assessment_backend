"""specs/010: the one-time question attribution backfill, against a migrated Postgres database.

    TEST_POSTGRES_URL=postgresql://localhost/trooth_fk pytest tests/test_question_ownership_postgres.py
"""
import importlib.util
import os
import pathlib
import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.models.assessment_template import AssessmentTemplate
from app.models.assessment_template_question import AssessmentTemplateQuestion
from app.models.question import Question
from app.models.user import User, UserRole

PG_URL = os.getenv("TEST_POSTGRES_URL")
pytestmark = pytest.mark.skipif(not PG_URL, reason="TEST_POSTGRES_URL not set")

_MIGRATION = pathlib.Path(__file__).resolve().parents[1] / "alembic/versions/20261014_question_owner.py"


def _backfill_sql():
    spec = importlib.util.spec_from_file_location("question_owner_migration", _MIGRATION)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.BACKFILL_SQL


@pytest.fixture
def pg():
    engine = create_engine(PG_URL)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()
    engine.dispose()


def test_backfill_attributes_only_unambiguous_mentor_questions(pg):
    def user(role):
        u = User(id=str(uuid.uuid4()), name=role.value, email=f"{role.value}-{uuid.uuid4().hex[:8]}@example.com",
                 role=role, created_at=datetime.now(UTC))
        pg.add(u)
        return u

    def question():
        q = Question(text=f"Q {uuid.uuid4().hex[:4]}", question_code=f"QT{uuid.uuid4().hex[:12]}")
        pg.add(q)
        return q

    def template(owner=None, master=False, qs=()):
        t = AssessmentTemplate(name=f"T {uuid.uuid4().hex[:4]}", created_by=owner.id if owner else None,
                               is_master_assessment=master)
        pg.add(t)
        pg.flush()
        for i, q in enumerate(qs, 1):
            pg.add(AssessmentTemplateQuestion(template_id=t.id, question_id=q.id, order=i))
        return t

    m1, m2, admin = user(UserRole.mentor), user(UserRole.mentor), user(UserRole.admin)
    only_m1, on_master, split, admin_owned, unused = question(), question(), question(), question(), question()
    pg.flush()
    t1 = template(m1, qs=[only_m1, split])
    template(m1, qs=[only_m1])                      # same owner twice -> still unambiguous
    master = template(None, master=True, qs=[on_master])
    template(m1, qs=[on_master])                    # clone-style link to a Master question
    template(m2, qs=[split])                        # two owners
    template(admin, qs=[admin_owned])               # owner isn't a mentor
    pg.commit()
    created = [only_m1, on_master, split, admin_owned, unused]
    try:
        pg.execute(text(_backfill_sql()))
        pg.commit()
        pg.expire_all()
        owners = {q.id: pg.get(Question, q.id).created_by for q in created}
        assert owners[only_m1.id] == m1.id
        assert owners[on_master.id] is None
        assert owners[split.id] is None
        assert owners[admin_owned.id] is None
        assert owners[unused.id] is None

        pg.execute(text(_backfill_sql()))           # idempotent
        pg.commit()
        assert pg.get(Question, only_m1.id).created_by == m1.id
    finally:
        pg.rollback()
        ids = [q.id for q in created]
        pg.query(AssessmentTemplateQuestion).filter(AssessmentTemplateQuestion.question_id.in_(ids)).delete(synchronize_session=False)
        pg.query(AssessmentTemplate).filter(AssessmentTemplate.created_by.in_([m1.id, m2.id, admin.id]) | (AssessmentTemplate.id == master.id)).delete(synchronize_session=False)
        pg.query(Question).filter(Question.id.in_(ids)).delete(synchronize_session=False)
        pg.query(User).filter(User.id.in_([m1.id, m2.id, admin.id])).delete(synchronize_session=False)
        pg.commit()


def test_mentor_can_create_a_question_on_postgres(pg):
    """question_code is NOT NULL + unique on Postgres; the create route must supply one."""
    from fastapi.testclient import TestClient

    from app.db import get_db
    from app.main import app
    from app.services.auth import get_current_user

    mentor = User(id=str(uuid.uuid4()), name="Mentor", email=f"m-{uuid.uuid4().hex[:8]}@example.com",
                  role=UserRole.mentor, created_at=datetime.now(UTC))
    pg.add(mentor)
    pg.commit()
    previous_db = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = lambda: pg
    app.dependency_overrides[get_current_user] = lambda: mentor
    created = []
    try:
        client = TestClient(app)
        for _ in range(2):  # two in a row: codes must be unique
            r = client.post("/question/questions", json={"text": "Custom", "question_type": "open_ended"})
            assert r.status_code == 200, r.text
            created.append(r.json()["id"])
        rows = pg.query(Question).filter(Question.id.in_(created)).all()
        assert all(q.question_code and q.created_by == mentor.id for q in rows)
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        if previous_db is not None:
            app.dependency_overrides[get_db] = previous_db
        else:
            app.dependency_overrides.pop(get_db, None)
        pg.rollback()
        pg.query(Question).filter(Question.id.in_(created)).delete(synchronize_session=False)
        pg.query(User).filter(User.id == mentor.id).delete(synchronize_session=False)
        pg.commit()
