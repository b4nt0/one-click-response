"""Encrypted link creation for response buttons."""

from __future__ import annotations

import html
import uuid

from src import config
from src.crypto import encrypt_payload
from src.models import AppError, LinkPayload, ResponseButton
from src.repositories.campaigns import CampaignRepository
from src.repositories.response_buttons import ResponseButtonRepository
from src.repositories.responses import DeduplicationRepository
from src.services.users import UserService


class LinksService:
    def __init__(
        self,
        user_service: UserService | None = None,
        button_repo: ResponseButtonRepository | None = None,
        campaign_repo: CampaignRepository | None = None,
        dedup_repo: DeduplicationRepository | None = None,
    ):
        self.user_service = user_service or UserService()
        self.button_repo = button_repo or ResponseButtonRepository()
        self.campaign_repo = campaign_repo or CampaignRepository()
        self.dedup_repo = dedup_repo or DeduplicationRepository()

    def create_links(
        self,
        uid: str,
        email: str,
        *,
        subject: str,
        recipients: list[str],
        buttons: list[dict],
        email_id: str | None = None,
        host_url: str | None = None,
    ) -> dict:
        if not recipients:
            raise AppError("At least one recipient is required.", status_code=400)

        user = self.user_service.get_or_create(uid, email)
        email_id = email_id or str(uuid.uuid4())

        self.dedup_repo.seed(email_id)

        try:
            public_host = config.resolve_public_host_url(host_url)
        except ValueError as exc:
            raise AppError(
                f"{exc}. Set HOST_URL in functions/.env or pass host_url from the client.",
                status_code=500,
                code="server_misconfigured",
            ) from exc

        links = []
        for item in buttons:
            button = self._resolve_button(uid, item)
            campaign_id = button.campaign_id
            payload = LinkPayload(
                version=1,
                email_id=email_id,
                subject=subject,
                recipients=recipients,
                response_button_id=button.id,
                campaign_id=campaign_id,
                owner_user_id=user.id,
            )
            ciphertext = encrypt_payload(payload, user.encryption_key)
            token = f"{user.id}.{ciphertext}"
            url = f"{public_host}/r/?p={token}"
            links.append({"button_id": button.id, "text": button.text, "url": url})

        html_block = self._render_html_block(links)
        return {"email_id": email_id, "links": links, "html": html_block}

    def _resolve_button(self, uid: str, item: dict) -> ResponseButton:
        button_id = item.get("response_button_id")
        if not button_id:
            raise AppError("response_button_id is required for each button.")

        button = self.button_repo.get(button_id)
        if not button:
            raise AppError(f"Response button {button_id} not found.", status_code=404)

        if button.campaign_id:
            campaign = self.campaign_repo.get(button.campaign_id)
            if not campaign or campaign.user_id != uid:
                raise AppError("Unauthorized access to response button.", status_code=403)
        elif button.user_id != uid:
            raise AppError("Unauthorized access to response button.", status_code=403)

        return button

    @staticmethod
    def _render_html_block(links: list[dict]) -> str:
        parts = ['<div style="margin:16px 0;padding:12px;border:1px solid #ddd;border-radius:8px;">']
        parts.append("<p><strong>Quick response:</strong></p>")
        for link in links:
            text = html.escape(link["text"])
            url = html.escape(link["url"])
            parts.append(
                f'<p><a href="{url}" '
                f'style="display:inline-block;padding:8px 16px;margin:4px;'
                f'background:#1a73e8;color:#fff;text-decoration:none;border-radius:4px;">'
                f"{text}</a></p>"
            )
        parts.append("</div>")
        return "\n".join(parts)
