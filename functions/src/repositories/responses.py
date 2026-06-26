"""Response and deduplication repositories."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from google.cloud import firestore

from src.models import Response
from src.repositories.db import get_db


def normalize_recipient(recipients: list[str]) -> str:
    return ", ".join(sorted(r.strip().lower() for r in recipients if r.strip()))


class DeduplicationRepository:
    def seed(self, email_id: str) -> None:
        ref = get_db().collection("deduplication").document(email_id)
        ref.set({"response_received": False}, merge=True)

    def get_response_received(self, transaction, email_id: str) -> bool:
        ref = get_db().collection("deduplication").document(email_id)
        snapshot = next(iter(transaction.get(ref)), None)
        if snapshot is None or not snapshot.exists:
            return False
        return bool(snapshot.to_dict().get("response_received", False))

    def mark_received(self, transaction, email_id: str) -> None:
        ref = get_db().collection("deduplication").document(email_id)
        transaction.set(ref, {"response_received": True}, merge=True)


class ResponseRepository:
    def campaign_recipient_exists(
        self, transaction, campaign_id: str, recipient: str
    ) -> bool:
        query = (
            get_db()
            .collection("responses")
            .where("campaign_id", "==", campaign_id)
            .where("recipient", "==", recipient)
            .limit(1)
        )
        results = list(transaction.get(query))
        return len(results) > 0

    def create_in_transaction(self, transaction, response: Response) -> Response:
        doc_id = response.id or str(uuid.uuid4())
        response.id = doc_id
        ref = get_db().collection("responses").document(doc_id)
        transaction.set(ref, response.to_firestore())
        return response

    def list_by_campaign(self, campaign_id: str) -> list[Response]:
        docs = (
            get_db()
            .collection("responses")
            .where("campaign_id", "==", campaign_id)
            .order_by("created_at", direction=firestore.Query.DESCENDING)
            .stream()
        )
        return [Response.from_firestore(doc.id, doc.to_dict()) for doc in docs]

    @staticmethod
    def now() -> datetime:
        return datetime.now(timezone.utc)
