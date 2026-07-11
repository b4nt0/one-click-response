"""Campaign and response button unit tests."""

from unittest.mock import MagicMock, patch

import pytest

from src.models import AppError, ResponseButton
from src.repositories.response_buttons import _sort_buttons
from src.services.campaigns import CampaignService


def test_sort_buttons_by_order_then_id():
    buttons = [
        ResponseButton(id="b", text="B", campaign_id="c1", order=1),
        ResponseButton(id="a", text="A", campaign_id="c1", order=0),
        ResponseButton(id="c", text="C", campaign_id="c1", order=0),
    ]
    sorted_buttons = _sort_buttons(buttons)
    assert [b.id for b in sorted_buttons] == ["a", "c", "b"]


def test_from_firestore_defaults_missing_order():
    button = ResponseButton.from_firestore("btn-1", {"text": "Yes", "campaign_id": "c1"})
    assert button.order == 0


def test_create_campaign_button_assigns_order(mock_campaign):
    button_repo = MagicMock()
    button_repo.next_order_for_campaign.return_value = 2
    button_repo.create.side_effect = lambda b: b

    service = CampaignService(button_repo=button_repo)
    service.campaign_repo = MagicMock()
    service.campaign_repo.get.return_value = mock_campaign

    button = service.create_button("user-1", text="Maybe", campaign_id="camp-1")

    button_repo.next_order_for_campaign.assert_called_once_with("camp-1")
    assert button.order == 2
    assert button.campaign_id == "camp-1"


def test_create_loose_button_assigns_order():
    button_repo = MagicMock()
    button_repo.next_order_for_user.return_value = 1
    button_repo.create.side_effect = lambda b: b

    service = CampaignService(button_repo=button_repo)

    button = service.create_button("user-1", text="Loose")

    button_repo.next_order_for_user.assert_called_once_with("user-1")
    assert button.order == 1
    assert button.user_id == "user-1"


def test_list_buttons_returns_sorted(mock_campaign):
    button_repo = MagicMock()
    button_repo.list_by_campaign.return_value = [
        ResponseButton(id="a", text="A", campaign_id="camp-1", order=0),
        ResponseButton(id="b", text="B", campaign_id="camp-1", order=1),
    ]

    service = CampaignService(button_repo=button_repo)
    service.campaign_repo = MagicMock()
    service.campaign_repo.get.return_value = mock_campaign

    buttons = service.list_buttons("user-1", "camp-1")

    assert [b.id for b in buttons] == ["a", "b"]


def test_reorder_buttons_delegates_to_repo(mock_campaign):
    reordered = [
        ResponseButton(id="b", text="B", campaign_id="camp-1", order=0),
        ResponseButton(id="a", text="A", campaign_id="camp-1", order=1),
    ]
    button_repo = MagicMock()
    button_repo.reorder.return_value = reordered

    service = CampaignService(button_repo=button_repo)
    service.campaign_repo = MagicMock()
    service.campaign_repo.get.return_value = mock_campaign

    result = service.reorder_buttons("user-1", "camp-1", ["b", "a"])

    button_repo.reorder.assert_called_once_with("camp-1", ["b", "a"])
    assert [b.id for b in result] == ["b", "a"]


def test_reorder_rejects_mismatched_ids():
    button_repo = MagicMock()
    button_repo.reorder.side_effect = AppError(
        "button_ids must include every button in the campaign exactly once."
    )

    service = CampaignService(button_repo=button_repo)
    service.campaign_repo = MagicMock()
    service.campaign_repo.get.return_value = MagicMock(user_id="user-1")

    with pytest.raises(AppError) as exc_info:
        service.reorder_buttons("user-1", "camp-1", ["only-one"])

    assert "exactly once" in exc_info.value.message


@patch("src.api.campaign_service")
def test_reorder_campaign_buttons_api(mock_svc, app_client, mock_verify_token, mock_button):
    mock_svc.reorder_buttons.return_value = [
        ResponseButton(id="btn-2", text="No", campaign_id="camp-1", order=0),
        ResponseButton(id=mock_button.id, text=mock_button.text, campaign_id="camp-1", order=1),
    ]

    res = app_client.put(
        "/api/campaigns/camp-1/buttons/reorder",
        json={"button_ids": ["btn-2", "btn-1"]},
        headers={"Authorization": "Bearer test"},
    )

    assert res.status_code == 200
    data = res.get_json()
    assert len(data) == 2
    assert data[0]["order"] == 0
    assert data[1]["order"] == 1
    mock_svc.reorder_buttons.assert_called_once_with("user-1", "camp-1", ["btn-2", "btn-1"])
