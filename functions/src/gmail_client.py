"""Gmail API client for forwarding response notifications."""

from __future__ import annotations

import base64
from email.mime.text import MIMEText

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from src import config
from src.models import AppError


class GmailClient:
    def send_notification(
        self,
        owner_email: str,
        *,
        recipients: str,
        answer_text: str,
        subject: str,
        campaign_name: str | None,
    ) -> None:
        if not config.GMAIL_REFRESH_TOKEN:
            raise AppError(
                "Application email forwarding is not configured.",
                status_code=500,
                code="gmail_not_configured",
            )

        creds = Credentials(
            token=None,
            refresh_token=config.GMAIL_REFRESH_TOKEN,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=config.GMAIL_CLIENT_ID,
            client_secret=config.GMAIL_CLIENT_SECRET,
        )

        service = build("gmail", "v1", credentials=creds, cache_discovery=False)

        campaign_line = f"Campaign: {campaign_name}\n" if campaign_name else ""
        body = (
            f"A one-click response was submitted.\n\n"
            f"Recipients: {recipients}\n"
            f"Answer: {answer_text}\n"
            f"{campaign_line}"
            f"Original subject: {subject}\n"
        )
        message = MIMEText(body)
        message["to"] = owner_email
        if config.GMAIL_SENDER_EMAIL:
            message["from"] = config.GMAIL_SENDER_EMAIL
        message["subject"] = f"1CR response: {answer_text}"

        raw = base64.urlsafe_b64encode(message.as_bytes()).decode("ascii")
        service.users().messages().send(userId="me", body={"raw": raw}).execute()
