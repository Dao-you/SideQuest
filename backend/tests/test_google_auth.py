"""Unit tests for Real Google Account Authentication and Google Identity flow."""

import pytest
from app.models.user import GoogleAuthRequest
from app.services.user_service import UserService


@pytest.fixture
def user_service():
    """Returns a fresh UserService instance."""
    return UserService()


def test_get_google_auth_config(user_service):
    """Verify Google OAuth configuration endpoint."""
    config = user_service.get_google_auth_config()
    assert config.enabled is True
    assert config.client_id != ""


def test_login_with_google_direct_profile(user_service):
    """Verify authentication with direct Google Profile."""
    req = GoogleAuthRequest(
        email="bradly093@gmail.com",
        name="Bradly Google",
        picture="https://lh3.googleusercontent.com/a/test-avatar",
        sub="109283746501928374650",
    )
    res = user_service.login_google(req)
    assert res.success is True
    assert res.user.email == "bradly093@gmail.com"
    assert res.user.name == "Bradly Google"
    assert res.user.google_account_connected is True
    assert res.user.auth_provider == "google"
    assert res.user.is_mock_account is False
    assert len(res.user.calendar_events) > 0


def test_login_with_google_id_token_jwt_payload(user_service):
    """Verify authentication by decoding base64 JWT payload."""
    import base64
    import json

    header = base64.urlsafe_b64encode(json.dumps({"alg": "RS256"}).encode()).decode().rstrip("=")
    payload_data = {
        "email": "kevin.devjam@gmail.com",
        "name": "Kevin DevJam",
        "picture": "https://lh3.googleusercontent.com/a/kevin-avatar",
        "sub": "998877665544332211",
        "aud": "917216410511.apps.googleusercontent.com",
    }
    payload = base64.urlsafe_b64encode(json.dumps(payload_data).encode()).decode().rstrip("=")
    simulated_jwt = f"{header}.{payload}.signature"

    req = GoogleAuthRequest(id_token=simulated_jwt)
    res = user_service.login_google(req)
    assert res.success is True
    assert res.user.email == "kevin.devjam@gmail.com"
    assert res.user.name == "Kevin DevJam"
    assert res.user.avatar_url == "https://lh3.googleusercontent.com/a/kevin-avatar"
    assert res.user.google_account_connected is True
    assert res.user.auth_provider == "google"
