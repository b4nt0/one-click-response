"""Campaign and response button CRUD."""

from __future__ import annotations

import uuid

from src.models import AppError, Campaign, ResponseButton
from src.repositories.campaigns import CampaignRepository
from src.repositories.response_buttons import ResponseButtonRepository
from src.repositories.responses import ResponseRepository


class CampaignService:
    def __init__(
        self,
        campaign_repo: CampaignRepository | None = None,
        button_repo: ResponseButtonRepository | None = None,
        response_repo: ResponseRepository | None = None,
    ):
        self.campaign_repo = campaign_repo or CampaignRepository()
        self.button_repo = button_repo or ResponseButtonRepository()
        self.response_repo = response_repo or ResponseRepository()

    def list_campaigns(self, user_id: str) -> list[Campaign]:
        return self.campaign_repo.list_by_user(user_id)

    def get_campaign(self, user_id: str, campaign_id: str) -> Campaign:
        campaign = self.campaign_repo.get(campaign_id)
        if not campaign or campaign.user_id != user_id:
            raise AppError("Campaign not found.", status_code=404)
        return campaign

    def create_campaign(
        self,
        user_id: str,
        *,
        name: str,
        record_answers: bool = False,
        forward_answers: bool = False,
    ) -> Campaign:
        campaign = Campaign(
            id=str(uuid.uuid4()),
            name=name,
            user_id=user_id,
            record_answers=record_answers,
            forward_answers=forward_answers,
        )
        return self.campaign_repo.create(campaign)

    def update_campaign(
        self,
        user_id: str,
        campaign_id: str,
        *,
        name: str | None = None,
        record_answers: bool | None = None,
        forward_answers: bool | None = None,
    ) -> Campaign:
        campaign = self.get_campaign(user_id, campaign_id)
        if name is not None:
            campaign.name = name
        if record_answers is not None:
            campaign.record_answers = record_answers
        if forward_answers is not None:
            campaign.forward_answers = forward_answers
        return self.campaign_repo.update(campaign)

    def delete_campaign(self, user_id: str, campaign_id: str) -> None:
        self.get_campaign(user_id, campaign_id)
        self.button_repo.delete_by_campaign(campaign_id)
        self.campaign_repo.delete(campaign_id)

    def list_buttons(self, user_id: str, campaign_id: str) -> list[ResponseButton]:
        self.get_campaign(user_id, campaign_id)
        return self.button_repo.list_by_campaign(campaign_id)

    def list_loose_buttons(self, user_id: str) -> list[ResponseButton]:
        return self.button_repo.list_loose_by_user(user_id)

    def create_button(
        self,
        user_id: str,
        *,
        text: str,
        campaign_id: str | None = None,
    ) -> ResponseButton:
        if campaign_id:
            self.get_campaign(user_id, campaign_id)
            button = ResponseButton(
                id=str(uuid.uuid4()),
                text=text,
                campaign_id=campaign_id,
            )
        else:
            button = ResponseButton(
                id=str(uuid.uuid4()),
                text=text,
                user_id=user_id,
            )
        return self.button_repo.create(button)

    def update_button(
        self,
        user_id: str,
        button_id: str,
        *,
        text: str,
    ) -> ResponseButton:
        button = self._get_owned_button(user_id, button_id)
        button.text = text
        return self.button_repo.update(button)

    def delete_button(self, user_id: str, button_id: str) -> None:
        self._get_owned_button(user_id, button_id)
        self.button_repo.delete(button_id)

    def list_responses(self, user_id: str, campaign_id: str) -> list:
        campaign = self.get_campaign(user_id, campaign_id)
        if not campaign.record_answers:
            return []
        return self.response_repo.list_by_campaign(campaign_id)

    def _get_owned_button(self, user_id: str, button_id: str) -> ResponseButton:
        button = self.button_repo.get(button_id)
        if not button:
            raise AppError("Response button not found.", status_code=404)
        if button.campaign_id:
            self.get_campaign(user_id, button.campaign_id)
        elif button.user_id != user_id:
            raise AppError("Response button not found.", status_code=404)
        return button
