"""Seed Firestore emulator with sample data for local development."""

from __future__ import annotations

import os
import sys
import uuid

os.environ.setdefault("FIRESTORE_EMULATOR_HOST", "127.0.0.1:8080")
os.environ.setdefault("GCLOUD_PROJECT", "one-click-response")

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.crypto import generate_encryption_key
from src.models import Campaign, ResponseButton, User
from src.repositories.campaigns import CampaignRepository
from src.repositories.response_buttons import ResponseButtonRepository
from src.repositories.users import UserRepository


def main():
    user = User(
        id="dev-user-1",
        email="dev@example.com",
        encryption_key=generate_encryption_key(),
    )
    UserRepository().save(user)

    campaign = CampaignRepository().create(
        Campaign(
            id=str(uuid.uuid4()),
            name="Dev Campaign",
            user_id=user.id,
            record_answers=True,
            forward_answers=True,
        )
    )

    for text in ["Yes", "No", "Maybe"]:
        ResponseButtonRepository().create(
            ResponseButton(id=str(uuid.uuid4()), text=text, campaign_id=campaign.id)
        )

    print(f"Seeded user={user.id} campaign={campaign.id}")


if __name__ == "__main__":
    main()
