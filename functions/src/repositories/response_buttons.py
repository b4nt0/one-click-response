"""Response button repository."""

from __future__ import annotations

import uuid

from src.models import AppError, ResponseButton
from src.repositories.db import get_db


def _sort_buttons(buttons: list[ResponseButton]) -> list[ResponseButton]:
    return sorted(buttons, key=lambda b: (b.order, b.id))


class ResponseButtonRepository:
    def list_by_campaign(self, campaign_id: str) -> list[ResponseButton]:
        docs = (
            get_db()
            .collection("response_buttons")
            .where("campaign_id", "==", campaign_id)
            .stream()
        )
        return _sort_buttons(
            [ResponseButton.from_firestore(doc.id, doc.to_dict()) for doc in docs]
        )

    def list_loose_by_user(self, user_id: str) -> list[ResponseButton]:
        docs = (
            get_db()
            .collection("response_buttons")
            .where("user_id", "==", user_id)
            .stream()
        )
        return _sort_buttons(
            [ResponseButton.from_firestore(doc.id, doc.to_dict()) for doc in docs]
        )

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

    def next_order_for_campaign(self, campaign_id: str) -> int:
        buttons = self.list_by_campaign(campaign_id)
        if not buttons:
            return 0
        return max(b.order for b in buttons) + 1

    def next_order_for_user(self, user_id: str) -> int:
        buttons = self.list_loose_by_user(user_id)
        if not buttons:
            return 0
        return max(b.order for b in buttons) + 1

    def reorder(self, campaign_id: str, button_ids: list[str]) -> list[ResponseButton]:
        buttons = self.list_by_campaign(campaign_id)
        existing_ids = {b.id for b in buttons}
        if set(button_ids) != existing_ids:
            raise AppError("button_ids must include every button in the campaign exactly once.")

        button_by_id = {b.id: b for b in buttons}
        for index, button_id in enumerate(button_ids):
            button = button_by_id[button_id]
            button.order = index
            self.update(button)

        return [button_by_id[button_id] for button_id in button_ids]
