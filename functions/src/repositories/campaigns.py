"""Campaign repository."""

from __future__ import annotations

import uuid

from src.models import Campaign
from src.repositories.db import get_db


class CampaignRepository:
    def list_by_user(self, user_id: str) -> list[Campaign]:
        docs = (
            get_db()
            .collection("campaigns")
            .where("user_id", "==", user_id)
            .stream()
        )
        return [Campaign.from_firestore(doc.id, doc.to_dict()) for doc in docs]

    def get(self, campaign_id: str) -> Campaign | None:
        doc = get_db().collection("campaigns").document(campaign_id).get()
        if not doc.exists:
            return None
        return Campaign.from_firestore(doc.id, doc.to_dict())

    def create(self, campaign: Campaign) -> Campaign:
        doc_id = campaign.id or str(uuid.uuid4())
        campaign.id = doc_id
        get_db().collection("campaigns").document(doc_id).set(campaign.to_firestore())
        return campaign

    def update(self, campaign: Campaign) -> Campaign:
        get_db().collection("campaigns").document(campaign.id).update(campaign.to_firestore())
        return campaign

    def delete(self, campaign_id: str) -> None:
        get_db().collection("campaigns").document(campaign_id).delete()
