"""Response registration and processing."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from google.cloud import firestore

from src.crypto import decrypt_payload
from src.gmail_client import GmailClient
from src.models import AppError, DuplicateError, Response
from src.repositories.campaigns import CampaignRepository
from src.repositories.db import get_db
from src.repositories.response_buttons import ResponseButtonRepository
from src.repositories.responses import (
    DeduplicationRepository,
    ResponseRepository,
    normalize_recipient,
)
from src.repositories.users import UserRepository


@dataclass
class PreviewResult:
    button_text: str
    subject: str
    campaign_name: str | None


@dataclass
class RegisterResult:
    status: str
    button_text: str
    subject: str
    owner_email: str
    campaign_name: str | None = None


class ResponsesService:
    def __init__(
        self,
        user_repo: UserRepository | None = None,
        button_repo: ResponseButtonRepository | None = None,
        campaign_repo: CampaignRepository | None = None,
        response_repo: ResponseRepository | None = None,
        dedup_repo: DeduplicationRepository | None = None,
        gmail_client: GmailClient | None = None,
    ):
        self.user_repo = user_repo or UserRepository()
        self.button_repo = button_repo or ResponseButtonRepository()
        self.campaign_repo = campaign_repo or CampaignRepository()
        self.response_repo = response_repo or ResponseRepository()
        self.dedup_repo = dedup_repo or DeduplicationRepository()
        self.gmail_client = gmail_client or GmailClient()

    def preview(self, token: str) -> PreviewResult:
        payload, button, campaign, _owner = self._load_context(token)
        return PreviewResult(
            button_text=button.text,
            subject=payload.subject,
            campaign_name=campaign.name if campaign else None,
        )

    def register(self, token: str, *, confirmed: bool) -> RegisterResult:
        if not confirmed:
            raise AppError("Confirmation is required to register a response.", status_code=400)

        payload, button, campaign, owner = self._load_context(token)
        recipient = normalize_recipient(payload.recipients)

        @firestore.transactional
        def _transaction(transaction):
            if self.dedup_repo.get_response_received(transaction, payload.email_id):
                raise DuplicateError()

            if campaign:
                if self.response_repo.campaign_recipient_exists(
                    transaction, campaign.id, recipient
                ):
                    raise DuplicateError()

            should_record = campaign is not None and campaign.record_answers
            should_forward = (campaign is not None and campaign.forward_answers) or button.is_loose

            if should_record and campaign:
                response = Response(
                    id=str(uuid.uuid4()),
                    text=button.text,
                    recipient=recipient,
                    subject=payload.subject,
                    campaign_id=campaign.id,
                    email_id=payload.email_id,
                    response_button_id=button.id,
                    created_at=ResponseRepository.now(),
                )
                self.response_repo.create_in_transaction(transaction, response)

            self.dedup_repo.mark_received(transaction, payload.email_id)

            return should_forward

        db = get_db()
        transaction = db.transaction()
        should_forward = _transaction(transaction)

        if should_forward:
            self.gmail_client.send_notification(
                owner.email,
                recipients=recipient,
                answer_text=button.text,
                subject=payload.subject,
                campaign_name=campaign.name if campaign else None,
            )

        return RegisterResult(
            status="success",
            button_text=button.text,
            subject=payload.subject,
            owner_email=owner.email,
            campaign_name=campaign.name if campaign else None,
        )

    def _load_context(self, token: str):
        if "." not in token:
            raise AppError("Invalid response link.", status_code=400)
        owner_user_id, ciphertext = token.split(".", 1)
        owner = self.user_repo.get(owner_user_id)
        if not owner:
            raise AppError("Invalid response link.", status_code=400)

        payload = decrypt_payload(ciphertext, owner.encryption_key)
        if payload.owner_user_id != owner.id:
            raise AppError("Invalid response link.", status_code=400)

        button = self.button_repo.get(payload.response_button_id)
        if not button:
            raise AppError("Response button not found.", status_code=404)

        campaign = None
        if payload.campaign_id:
            campaign = self.campaign_repo.get(payload.campaign_id)
            if not campaign:
                raise AppError("Campaign not found.", status_code=404)

        return payload, button, campaign, owner
