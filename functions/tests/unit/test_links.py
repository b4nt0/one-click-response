"""Links service unit tests."""

from unittest.mock import MagicMock, patch

import pytest

from src.models import AppError
from src.services.links import LinksService


def test_create_links_requires_recipients(mock_user, mock_button, mock_campaign):
    service = LinksService(
        user_service=MagicMock(get_or_create=MagicMock(return_value=mock_user)),
        button_repo=MagicMock(),
        campaign_repo=MagicMock(),
        dedup_repo=MagicMock(),
    )
    with pytest.raises(AppError) as exc:
        service.create_links("user-1", "owner@example.com", subject="Hi", recipients=[], buttons=[])
    assert "recipient" in exc.value.message.lower()


@patch("src.services.links.config.resolve_public_host_url", return_value="https://example.com")
def test_create_links_returns_html(mock_resolve_host, mock_user, mock_button, mock_campaign, sample_key):
    user_svc = MagicMock()
    user_svc.get_or_create.return_value = mock_user

    button_repo = MagicMock()
    button_repo.get.return_value = mock_button

    campaign_repo = MagicMock()
    campaign_repo.get.return_value = mock_campaign

    dedup_repo = MagicMock()

    service = LinksService(
        user_service=user_svc,
        button_repo=button_repo,
        campaign_repo=campaign_repo,
        dedup_repo=dedup_repo,
    )

    result = service.create_links(
        "user-1",
        "owner@example.com",
        subject="Party?",
        recipients=["guest@example.com"],
        buttons=[{"response_button_id": "btn-1"}],
        email_id="email-abc",
    )

    assert result["email_id"] == "email-abc"
    assert len(result["links"]) == 1
    assert "https://example.com/r/?p=" in result["links"][0]["url"]
    assert "Yes" in result["html"]
    assert "Quick response" not in result["html"]
    dedup_repo.seed.assert_called_once_with("email-abc")


def test_render_html_block_layout():
    html = LinksService._render_html_block(
        [
            {"text": "Yes", "url": "https://example.com/r/?p=token1"},
            {"text": "No", "url": "https://example.com/r/?p=token2"},
        ]
    )

    assert "Quick response" not in html
    assert html.count("<a ") == 2
    assert "display:inline-block" in html
    assert "border:1px solid #dadce0" in html
    assert "background-color:#1a73e8" in html
    assert "color:#ffffff" in html


@patch.dict("os.environ", {"HOST_URL": "http://"}, clear=False)
def test_create_links_rejects_invalid_host_url(mock_user, mock_button, mock_campaign):
    user_svc = MagicMock()
    user_svc.get_or_create.return_value = mock_user
    button_repo = MagicMock()
    button_repo.get.return_value = mock_button
    campaign_repo = MagicMock()
    campaign_repo.get.return_value = mock_campaign

    service = LinksService(
        user_service=user_svc,
        button_repo=button_repo,
        campaign_repo=campaign_repo,
        dedup_repo=MagicMock(),
    )

    with pytest.raises(AppError) as exc:
        service.create_links(
            "user-1",
            "owner@example.com",
            subject="Hi",
            recipients=["guest@example.com"],
            buttons=[{"response_button_id": "btn-1"}],
            host_url="http://",
        )

    assert exc.value.code == "server_misconfigured"
    assert "HOST_URL" in exc.value.message


@patch("src.services.links.config.resolve_public_host_url", return_value="https://example.com")
def test_create_links_uses_host_url_override(mock_resolve_host, mock_user, mock_button, mock_campaign):
    user_svc = MagicMock()
    user_svc.get_or_create.return_value = mock_user
    button_repo = MagicMock()
    button_repo.get.return_value = mock_button
    campaign_repo = MagicMock()
    campaign_repo.get.return_value = mock_campaign

    service = LinksService(
        user_service=user_svc,
        button_repo=button_repo,
        campaign_repo=campaign_repo,
        dedup_repo=MagicMock(),
    )

    service.create_links(
        "user-1",
        "owner@example.com",
        subject="Hi",
        recipients=["guest@example.com"],
        buttons=[{"response_button_id": "btn-1"}],
        host_url="https://one-click-response.web.app",
    )

    mock_resolve_host.assert_called_once_with("https://one-click-response.web.app")
