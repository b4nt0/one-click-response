"""Domain models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class User:
    id: str
    email: str
    encryption_key: str

    @classmethod
    def from_firestore(cls, doc_id: str, data: dict[str, Any]) -> User:
        return cls(
            id=doc_id,
            email=data["email"],
            encryption_key=data["encryption_key"],
        )

    def to_firestore(self) -> dict[str, Any]:
        return {
            "email": self.email,
            "encryption_key": self.encryption_key,
        }


@dataclass
class Campaign:
    id: str
    name: str
    user_id: str
    record_answers: bool
    forward_answers: bool

    @classmethod
    def from_firestore(cls, doc_id: str, data: dict[str, Any]) -> Campaign:
        return cls(
            id=doc_id,
            name=data["name"],
            user_id=data["user_id"],
            record_answers=data.get("record_answers", False),
            forward_answers=data.get("forward_answers", False),
        )

    def to_firestore(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "user_id": self.user_id,
            "record_answers": self.record_answers,
            "forward_answers": self.forward_answers,
        }


@dataclass
class ResponseButton:
    id: str
    text: str
    campaign_id: str | None = None
    user_id: str | None = None

    @classmethod
    def from_firestore(cls, doc_id: str, data: dict[str, Any]) -> ResponseButton:
        return cls(
            id=doc_id,
            text=data["text"],
            campaign_id=data.get("campaign_id"),
            user_id=data.get("user_id"),
        )

    def to_firestore(self) -> dict[str, Any]:
        result: dict[str, Any] = {"text": self.text}
        if self.campaign_id is not None:
            result["campaign_id"] = self.campaign_id
        if self.user_id is not None:
            result["user_id"] = self.user_id
        return result

    @property
    def is_loose(self) -> bool:
        return self.campaign_id is None


@dataclass
class Response:
    id: str
    text: str
    recipient: str
    subject: str
    campaign_id: str | None
    email_id: str
    response_button_id: str
    created_at: datetime

    @classmethod
    def from_firestore(cls, doc_id: str, data: dict[str, Any]) -> Response:
        created = data["created_at"]
        if hasattr(created, "timestamp"):
            created_at = datetime.fromtimestamp(created.timestamp())
        else:
            created_at = created
        return cls(
            id=doc_id,
            text=data["text"],
            recipient=data["recipient"],
            subject=data["subject"],
            campaign_id=data.get("campaign_id"),
            email_id=data["email_id"],
            response_button_id=data["response_button_id"],
            created_at=created_at,
        )

    def to_firestore(self) -> dict[str, Any]:
        from google.cloud import firestore

        result: dict[str, Any] = {
            "text": self.text,
            "recipient": self.recipient,
            "subject": self.subject,
            "email_id": self.email_id,
            "response_button_id": self.response_button_id,
            "created_at": firestore.SERVER_TIMESTAMP,
        }
        if self.campaign_id is not None:
            result["campaign_id"] = self.campaign_id
        return result


@dataclass
class LinkPayload:
    version: int
    email_id: str
    subject: str
    recipients: list[str]
    response_button_id: str
    campaign_id: str | None
    owner_user_id: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "v": self.version,
            "email_id": self.email_id,
            "subject": self.subject,
            "recipients": self.recipients,
            "response_button_id": self.response_button_id,
            "campaign_id": self.campaign_id,
            "owner_user_id": self.owner_user_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LinkPayload:
        return cls(
            version=data["v"],
            email_id=data["email_id"],
            subject=data["subject"],
            recipients=data["recipients"],
            response_button_id=data["response_button_id"],
            campaign_id=data.get("campaign_id"),
            owner_user_id=data["owner_user_id"],
        )


class AppError(Exception):
    def __init__(
        self,
        message: str,
        status_code: int = 400,
        code: str = "error",
        debug: dict | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code
        self.debug = debug


class DuplicateError(AppError):
    def __init__(self, message: str = "A response has already been submitted."):
        super().__init__(message, status_code=409, code="duplicate")
