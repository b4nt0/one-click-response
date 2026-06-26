"""API endpoint unit tests."""

from unittest.mock import MagicMock, patch

import pytest


def test_health(app_client):
    res = app_client.get("/api/health")
    assert res.status_code == 200
    assert res.get_json()["status"] == "ok"


def test_create_links_unauthorized(app_client):
    res = app_client.post("/api/links", json={})
    assert res.status_code == 401


@patch("src.api.links_service")
def test_create_links_success(mock_links, app_client, mock_verify_token):
    mock_links.create_links.return_value = {"email_id": "e1", "links": [], "html": "<div/>"}
    res = app_client.post(
        "/api/links",
        json={"subject": "Hi", "recipients": ["a@b.com"], "buttons": []},
        headers={"Authorization": "Bearer test"},
    )
    assert res.status_code == 200


@patch("src.api.responses_service")
def test_preview_response(mock_svc, app_client):
    mock_svc.preview.return_value = MagicMock(
        button_text="Yes", subject="Party", campaign_name="Birthday"
    )
    res = app_client.post("/api/responses/preview", json={"p": "user-1.token"})
    assert res.status_code == 200
    assert res.get_json()["button_text"] == "Yes"


@patch("src.api.campaign_service")
def test_list_campaigns(mock_svc, app_client, mock_verify_token):
    from src.models import Campaign

    mock_svc.list_campaigns.return_value = [
        Campaign("c1", "Test", "user-1", True, False)
    ]
    res = app_client.get("/api/campaigns", headers={"Authorization": "Bearer test"})
    assert res.status_code == 200
    assert len(res.get_json()) == 1


@patch("src.api.user_service")
def test_rotate_key(mock_user_svc, app_client, mock_verify_token):
    mock_user_svc.rotate_key.return_value = "new-key"
    res = app_client.post("/api/users/rotate-key", headers={"Authorization": "Bearer test"})
    assert res.status_code == 200
    assert res.get_json()["encryption_key_rotated"] is True
