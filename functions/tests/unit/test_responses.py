"""Response registration unit tests."""

from unittest.mock import MagicMock, patch

import pytest

from src.crypto import encrypt_payload
from src.models import AppError, DuplicateError, LinkPayload
from src.services.responses import ResponsesService


def _make_token(payload, key):
    ciphertext = encrypt_payload(payload, key)
    return f"{payload.owner_user_id}.{ciphertext}"


def _payload(email_id="email-1", campaign_id="camp-1"):
    return LinkPayload(
        version=1,
        email_id=email_id,
        subject="Test subject",
        recipients=["alice@example.com"],
        response_button_id="btn-1",
        campaign_id=campaign_id,
        owner_user_id="user-1",
    )


@patch("src.services.responses.get_db")
def test_register_requires_confirmation(mock_db, mock_user, mock_button, mock_campaign, sample_key):
    service = ResponsesService(
        user_repo=MagicMock(get=MagicMock(return_value=mock_user)),
        button_repo=MagicMock(get=MagicMock(return_value=mock_button)),
        campaign_repo=MagicMock(get=MagicMock(return_value=mock_campaign)),
    )
    token = _make_token(_payload(), sample_key)
    with pytest.raises(AppError):
        service.register(token, confirmed=False)


@patch("src.services.responses.get_db")
def test_preview_returns_button_text(mock_db, mock_user, mock_button, mock_campaign, sample_key):
    service = ResponsesService(
        user_repo=MagicMock(get=MagicMock(return_value=mock_user)),
        button_repo=MagicMock(get=MagicMock(return_value=mock_button)),
        campaign_repo=MagicMock(get=MagicMock(return_value=mock_campaign)),
    )
    token = _make_token(_payload(), sample_key)
    preview = service.preview(token)
    assert preview.button_text == "Yes"
    assert preview.campaign_name == "Test Campaign"


@patch("src.services.responses.get_db")
def test_register_duplicate_email_id(mock_db, mock_user, mock_button, mock_campaign, sample_key):
    dedup_repo = MagicMock()
    dedup_repo.get_response_received.return_value = True

    mock_transaction = MagicMock()
    mock_db.return_value.transaction.return_value = mock_transaction

    service = ResponsesService(
        user_repo=MagicMock(get=MagicMock(return_value=mock_user)),
        button_repo=MagicMock(get=MagicMock(return_value=mock_button)),
        campaign_repo=MagicMock(get=MagicMock(return_value=mock_campaign)),
        dedup_repo=dedup_repo,
    )

    token = _make_token(_payload(), sample_key)

    with patch("src.services.responses.firestore.transactional", lambda fn: fn):
        with pytest.raises(DuplicateError):
            service.register(token, confirmed=True)


@patch("src.services.responses.get_db")
def test_register_record_only(mock_db, mock_user, mock_button, mock_campaign, sample_key):
    mock_campaign.forward_answers = False
    mock_campaign.record_answers = True

    dedup_repo = MagicMock()
    dedup_repo.get_response_received.return_value = False

    response_repo = MagicMock()
    response_repo.campaign_recipient_exists.return_value = False

    mock_db.return_value.transaction.return_value = MagicMock()

    gmail = MagicMock()

    service = ResponsesService(
        user_repo=MagicMock(get=MagicMock(return_value=mock_user)),
        button_repo=MagicMock(get=MagicMock(return_value=mock_button)),
        campaign_repo=MagicMock(get=MagicMock(return_value=mock_campaign)),
        response_repo=response_repo,
        dedup_repo=dedup_repo,
        gmail_client=gmail,
    )

    token = _make_token(_payload(), sample_key)

    with patch("src.services.responses.firestore.transactional", lambda fn: fn):
        result = service.register(token, confirmed=True)

    assert result.status == "success"
    gmail.send_notification.assert_not_called()
    response_repo.create_in_transaction.assert_called_once()


@patch("src.services.responses.get_db")
def test_register_forward_only(mock_db, mock_user, mock_button, mock_campaign, sample_key):
    mock_campaign.forward_answers = True
    mock_campaign.record_answers = False

    dedup_repo = MagicMock()
    dedup_repo.get_response_received.return_value = False

    response_repo = MagicMock()
    response_repo.campaign_recipient_exists.return_value = False

    mock_db.return_value.transaction.return_value = MagicMock()
    gmail = MagicMock()

    service = ResponsesService(
        user_repo=MagicMock(get=MagicMock(return_value=mock_user)),
        button_repo=MagicMock(get=MagicMock(return_value=mock_button)),
        campaign_repo=MagicMock(get=MagicMock(return_value=mock_campaign)),
        response_repo=response_repo,
        dedup_repo=dedup_repo,
        gmail_client=gmail,
    )

    token = _make_token(_payload(), sample_key)

    with patch("src.services.responses.firestore.transactional", lambda fn: fn):
        service.register(token, confirmed=True)

    gmail.send_notification.assert_called_once_with(
        mock_user.email,
        recipients="alice@example.com",
        answer_text="Yes",
        subject="Test subject",
        campaign_name="Test Campaign",
    )


@patch("src.services.responses.get_db")
def test_register_loose_button_forwards(
    mock_db, mock_user, mock_loose_button, sample_key
):
    payload = LinkPayload(
        version=1,
        email_id="email-loose",
        subject="Loose",
        recipients=["bob@example.com"],
        response_button_id="btn-loose",
        campaign_id=None,
        owner_user_id="user-1",
    )

    dedup_repo = MagicMock()
    dedup_repo.get_response_received.return_value = False
    mock_db.return_value.transaction.return_value = MagicMock()
    gmail = MagicMock()

    service = ResponsesService(
        user_repo=MagicMock(get=MagicMock(return_value=mock_user)),
        button_repo=MagicMock(get=MagicMock(return_value=mock_loose_button)),
        campaign_repo=MagicMock(),
        dedup_repo=dedup_repo,
        gmail_client=gmail,
    )

    token = _make_token(payload, sample_key)

    with patch("src.services.responses.firestore.transactional", lambda fn: fn):
        service.register(token, confirmed=True)

    gmail.send_notification.assert_called_once_with(
        mock_user.email,
        recipients="bob@example.com",
        answer_text="Maybe",
        subject="Loose",
        campaign_name=None,
    )


@patch("src.services.responses.get_db")
def test_register_inline_button_text_forwards(mock_db, mock_user, sample_key):
    payload = LinkPayload(
        version=1,
        email_id="email-inline",
        subject="Inline",
        recipients=["bob@example.com"],
        response_button_id="btn-inline",
        campaign_id=None,
        owner_user_id="user-1",
        button_text="Custom",
    )

    dedup_repo = MagicMock()
    dedup_repo.get_response_received.return_value = False
    mock_db.return_value.transaction.return_value = MagicMock()
    gmail = MagicMock()

    service = ResponsesService(
        user_repo=MagicMock(get=MagicMock(return_value=mock_user)),
        button_repo=MagicMock(get=MagicMock(return_value=None)),
        campaign_repo=MagicMock(),
        dedup_repo=dedup_repo,
        gmail_client=gmail,
    )

    token = _make_token(payload, sample_key)

    with patch("src.services.responses.firestore.transactional", lambda fn: fn):
        result = service.register(token, confirmed=True)

    assert result.button_text == "Custom"
    gmail.send_notification.assert_called_once_with(
        mock_user.email,
        recipients="bob@example.com",
        answer_text="Custom",
        subject="Inline",
        campaign_name=None,
    )
