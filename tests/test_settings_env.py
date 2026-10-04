import pytest

from app.core.settings import Settings
from app.exceptions import ValidationException


@pytest.mark.parametrize(
    "env, production, development",
    [
        ("production", True, False),
        ("prod", True, False),
        ("PRODUCTION", True, False),
        ("dev", False, False),
        ("development", False, True),
        ("test", False, False),
    ],
)
def test_env_flags(monkeypatch, env, production, development):
    monkeypatch.setenv("ENV", env)
    s = Settings()
    assert s.is_production is production
    assert s.is_development is development


def test_prod_alias_normalized(monkeypatch):
    monkeypatch.setenv("ENV", "prod")
    assert Settings().environment == "production"


def test_validation_exception_status_matches_handler():
    assert ValidationException().status_code == 400


def test_cors_allows_dev_api_and_localhost_origins(client):
    for origin in (
        "https://trooth-discipleship-api-dev.onlyblv.com",
        "http://localhost:3000",
    ):
        r = client.options(
            "/",
            headers={"Origin": origin, "Access-Control-Request-Method": "GET"},
        )
        assert r.headers.get("access-control-allow-origin") == origin
