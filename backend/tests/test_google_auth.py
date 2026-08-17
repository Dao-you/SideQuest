"""Tests for strict Google Identity Services token verification."""

from unittest.mock import patch

import pytest

from app.config import settings
from app.models.user import GoogleAuthRequest
from app.services.user_service import UserService


@pytest.fixture
def user_service():
    return UserService()


def test_get_google_auth_config_disabled_without_client_id(user_service, monkeypatch):
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", "")

    config = user_service.get_google_auth_config()

    assert config.enabled is False
    assert config.client_id == ""


def test_login_with_verified_google_id_token(user_service, monkeypatch):
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", "web-client.apps.googleusercontent.com")
    verified_claims = {
        "sub": "109283746501928374650",
        "email": "kevin@example.com",
        "email_verified": True,
        "name": "Kevin",
        "picture": "https://lh3.googleusercontent.com/a/test-avatar",
        "aud": settings.GOOGLE_CLIENT_ID,
        "iss": "https://accounts.google.com",
    }

    with patch("google.oauth2.id_token.verify_oauth2_token", return_value=verified_claims) as verify:
        response = user_service.login_google(GoogleAuthRequest(credential="signed-google-token"))

    verify.assert_called_once()
    assert verify.call_args.kwargs["audience"] == settings.GOOGLE_CLIENT_ID
    assert response.success is True
    assert response.user.user_id == "google_1092837465019283"
    assert response.user.email == "kevin@example.com"
    assert response.user.avatar_url == verified_claims["picture"]
    assert response.user.auth_provider == "google"
    assert response.user.is_mock_account is False
    assert response.user.calendar_events == []


def test_login_rejects_unsigned_or_invalid_token(user_service, monkeypatch):
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", "web-client.apps.googleusercontent.com")

    with patch("google.oauth2.id_token.verify_oauth2_token", side_effect=ValueError("bad signature")):
        with pytest.raises(ValueError, match="無效或已過期"):
            user_service.login_google(GoogleAuthRequest(credential="unsigned.jwt.payload"))


def test_login_rejects_unverified_email(user_service, monkeypatch):
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", "web-client.apps.googleusercontent.com")
    claims = {
        "sub": "123",
        "email": "unverified@example.com",
        "email_verified": False,
    }

    with patch("google.oauth2.id_token.verify_oauth2_token", return_value=claims):
        with pytest.raises(ValueError, match="已驗證的身分資料"):
            user_service.login_google(GoogleAuthRequest(credential="signed-google-token"))
