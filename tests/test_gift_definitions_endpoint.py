"""Spiritual gift definitions endpoint (and the path released apps call)."""
import uuid
from datetime import UTC, datetime

import pytest

from app.main import app
from app.models.spiritual_gift_definition import SpiritualGiftDefinition
from app.models.user import User
from app.services.auth import get_current_user


@pytest.fixture
def signed_in(db_session):
    u = User(id=str(uuid.uuid4()), name="A", email=f"a+{uuid.uuid4().hex[:8]}@example.com",
             role="apprentice", created_at=datetime.now(UTC))
    db_session.add(u)
    db_session.commit()
    app.dependency_overrides[get_current_user] = lambda: u
    yield u
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def definitions(db_session):
    db_session.add_all([
        SpiritualGiftDefinition(gift_slug="teaching", display_name="Teaching", short_summary="Explain.",
                                full_definition="Explains Scripture clearly.", version=1, locale="en"),
        SpiritualGiftDefinition(gift_slug="tongues_interpretation", display_name="Tongues & Interpretation",
                                short_summary="Edify.", full_definition="Spirit-led utterance.", version=1, locale="en"),
    ])
    db_session.commit()


@pytest.mark.parametrize("path", ["/assessments/spiritual-gifts/definitions", "/spiritual-gifts/definitions"])
def test_definitions_with_scripture(client, signed_in, definitions, path):
    r = client.get(path)
    assert r.status_code == 200, r.text
    by_slug = {d["gift_slug"]: d for d in r.json()}
    assert by_slug["teaching"]["description"] == "Explains Scripture clearly."
    assert "Romans 12:7" in by_slug["teaching"]["scripture_refs"]
    # The app's built-in list spells this slug differently
    assert by_slug["tongues-interpretation"]["slug"] == "tongues-and-interpretation"


@pytest.mark.parametrize("path", ["/assessments/spiritual-gifts/definitions", "/spiritual-gifts/definitions"])
def test_definitions_require_sign_in(client, path):
    app.dependency_overrides.pop(get_current_user, None)
    assert client.get(path).status_code == 401
