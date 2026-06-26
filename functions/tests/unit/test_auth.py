"""Auth unit tests."""

from unittest.mock import MagicMock, patch

import pytest

from src.auth import (
    inspect_identity_token,
    resolve_auth_user,
    try_verify_google_identity_token,
    verify_id_token,
)
from src.models import AppError


def _make_jwt(payload: dict) -> str:
    import base64
    import json

    header = base64.urlsafe_b64encode(b'{"alg":"none"}').decode().rstrip("=")
    body = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    return f"{header}.{body}.signature"


def test_verify_id_token_missing_header():
    with pytest.raises(AppError) as exc:
        verify_id_token(None)
    assert exc.value.status_code == 401


def test_verify_id_token_invalid_format():
    with pytest.raises(AppError) as exc:
        verify_id_token("NotBearer token")
    assert exc.value.status_code == 401


@patch("src.auth.auth.verify_id_token")
@patch("src.auth.init_firebase")
def test_verify_id_token_valid(mock_init, mock_verify):
    mock_verify.return_value = {"uid": "u1", "email": "a@b.com"}
    claims = verify_id_token("Bearer good-token")
    assert claims["uid"] == "u1"


@patch("src.auth._firebase_user_for_email")
@patch("src.auth.verify_google_identity_token")
@patch("src.auth.auth.verify_id_token")
@patch("src.auth.init_firebase")
@patch.dict("os.environ", {"APPS_SCRIPT_OAUTH_CLIENT_ID": "apps-script-client.apps.googleusercontent.com"})
def test_resolve_auth_user_firebase_token(
    mock_init, mock_firebase_verify, mock_google_verify, mock_get_user
):
    mock_firebase_verify.return_value = {"uid": "firebase-uid", "email": "user@example.com"}
    result = resolve_auth_user("Bearer firebase-token")
    assert result == {"uid": "firebase-uid", "email": "user@example.com"}
    mock_google_verify.assert_not_called()
    mock_get_user.assert_not_called()


@patch("src.auth.try_verify_google_identity_token")
@patch("src.auth.auth.verify_id_token")
@patch("src.auth.init_firebase")
@patch.dict("os.environ", {"APPS_SCRIPT_OAUTH_CLIENT_ID": "wrong-client.apps.googleusercontent.com"})
def test_resolve_auth_user_tries_token_aud_after_configured_client_fails(
    mock_init, mock_firebase_verify, mock_try_verify
):
    token = _make_jwt({"aud": "actual-client.apps.googleusercontent.com", "email": "user@example.com"})
    mock_firebase_verify.side_effect = ValueError("not a firebase token")
    mock_try_verify.side_effect = [
        (None, "Wrong audience"),
        ({"email": "user@example.com", "sub": "google-sub"}, None),
    ]

    with patch("src.auth._firebase_user_for_email") as mock_get_user:
        mock_get_user.return_value = MagicMock(uid="firebase-uid")
        result = resolve_auth_user(f"Bearer {token}")

    assert result == {"uid": "firebase-uid", "email": "user@example.com"}
    assert mock_try_verify.call_count == 2


@patch("src.auth._firebase_user_for_email")
@patch("src.auth.try_verify_google_identity_token")
@patch("src.auth.auth.verify_id_token")
@patch("src.auth.init_firebase")
@patch.dict("os.environ", {"APPS_SCRIPT_OAUTH_CLIENT_ID": "apps-script-client.apps.googleusercontent.com"})
def test_resolve_auth_user_apps_script_token(
    mock_init, mock_firebase_verify, mock_try_verify, mock_get_user
):
    mock_firebase_verify.side_effect = ValueError("not a firebase token")
    mock_try_verify.return_value = ({"email": "user@example.com", "sub": "google-sub"}, None)
    mock_get_user.return_value = MagicMock(uid="firebase-uid")

    result = resolve_auth_user("Bearer apps-script-token")

    assert result == {"uid": "firebase-uid", "email": "user@example.com"}
    mock_try_verify.assert_called()


@patch("src.auth._firebase_user_for_email")
@patch("src.auth.try_verify_google_identity_token")
@patch("src.auth.auth.verify_id_token")
@patch("src.auth.init_firebase")
@patch.dict("os.environ", {"APPS_SCRIPT_OAUTH_CLIENT_ID": "apps-script-client.apps.googleusercontent.com"})
def test_resolve_auth_user_provisions_new_user(
    mock_init, mock_firebase_verify, mock_try_verify, mock_get_user
):
    mock_firebase_verify.side_effect = ValueError("not a firebase token")
    mock_try_verify.return_value = ({"email": "new@example.com", "email_verified": True}, None)
    mock_get_user.return_value = MagicMock(uid="new-firebase-uid")

    result = resolve_auth_user("Bearer apps-script-token")

    assert result["uid"] == "new-firebase-uid"
    mock_get_user.assert_called_once_with("new@example.com", email_verified=True)


@patch("src.auth.try_verify_google_identity_token")
@patch("src.auth.auth.verify_id_token")
@patch("src.auth.init_firebase")
@patch.dict("os.environ", {"APPS_SCRIPT_OAUTH_CLIENT_ID": "wrong.apps.googleusercontent.com"})
def test_resolve_auth_user_includes_debug_on_failure(mock_init, mock_firebase_verify, mock_try_verify):
    token = _make_jwt({"aud": "actual.apps.googleusercontent.com", "email": "user@example.com"})
    mock_firebase_verify.side_effect = ValueError("not a firebase token")
    mock_try_verify.return_value = (None, "Invalid token")

    with pytest.raises(AppError) as exc:
        resolve_auth_user(f"Bearer {token}")

    assert exc.value.status_code == 401
    assert exc.value.debug is not None
    assert exc.value.debug["token_claims"]["aud"] == "actual.apps.googleusercontent.com"
    assert exc.value.debug["audience_match_hint"] is not None


@patch("src.auth.try_verify_google_identity_token")
@patch("src.auth.auth.verify_id_token")
@patch("src.auth.init_firebase")
def test_inspect_identity_token_reports_audience_mismatch(mock_init, mock_firebase_verify, mock_try_verify):
    token = _make_jwt({"aud": "token-client.apps.googleusercontent.com", "email": "a@b.com"})
    mock_firebase_verify.side_effect = ValueError("not firebase")
    mock_try_verify.return_value = (None, "fail")

    with patch.dict("os.environ", {"APPS_SCRIPT_OAUTH_CLIENT_ID": "other-client.apps.googleusercontent.com"}):
        report = inspect_identity_token(token)

    assert report["token_claims"]["aud"] == "token-client.apps.googleusercontent.com"
    assert "does NOT match" in report["audience_match_hint"]
    assert report["any_verification_succeeded"] is False
