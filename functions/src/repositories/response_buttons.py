"""Response button repository."""

from __future__ import annotations

import uuid

from src.models import ResponseButton
from src.repositories.db import get_db


class ResponseButtonRepository:
    def list_by_campaign(self, campaign_id: str) -> list[ResponseButton]:
        docs = (
            get_db()
            .collection("response_buttons")
            .where("campaign_id", "==", campaign_id)
            .stream()
        )
        return [ResponseButton.from_firestore(doc.id, doc.to_dict()) for doc in docs]

    def list_loose_by_user(self, user_id: str) -> list[ResponseButton]:
        docs = (
            get_db()
            .collection("response_buttons")
            .where("user_id", "==", user_id)
            .stream()
        )
        return [ResponseButton.from_firestore(doc.id, doc.to_dict()) for doc in docs]

    def get(self, button_id: str) -> ResponseButton | None:
        doc = get_db().collection("response_buttons").document(button_id).get()
        if not doc.exists:
            return None
        return ResponseButton.from_firestore(doc.id, doc.to_dict())

    def create(self, button: ResponseButton) -> ResponseButton:
        doc_id = button.id or str(uuid.uuid4())
        button.id = doc_id
        get_db().collection("response_buttons").document(doc_id).set(button.to_firestore())
        return button

    def update(self, button: ResponseButton) -> ResponseButton:
        get_db().collection("response_buttons").document(button.id).update(button.to_firestore())
        return button

    def delete(self, button_id: str) -> None:
        get_db().collection("response_buttons").document(button_id).delete()

    def delete_by_campaign(self, campaign_id: str) -> None:
        for button in self.list_by_campaign(campaign_id):
            self.delete(button.id)
