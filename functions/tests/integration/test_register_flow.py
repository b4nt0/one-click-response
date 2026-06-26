"""Integration tests using Firestore emulator.

Run via: firebase emulators:exec --only firestore 'cd functions && pytest tests/integration'
"""

from __future__ import annotations

import os
import uuid

import pytest

# Emulator env must be set before Firebase imports
os.environ.setdefault("FIRESTORE_EMULATOR_HOST", "127.0.0.1:8080")
os.environ.setdefault("GCLOUD_PROJECT", "one-click-response")


@pytest.fixture(autouse=True)
def emulator_available():
    if not os.environ.get("FIRESTORE_EMULATOR_HOST"):
        pytest.skip("Firestore emulator not running")


@pytest.fixture
def db():
    from src.repositories.db import get_db

    client = get_db()
    # Clear collections between tests
    for collection in ["users", "campaigns", "response_buttons", "responses", "deduplication"]:
        for doc in client.collection(collection).stream():
            doc.reference.delete()
    return client


@pytest.fixture
def integration_user(db, sample_key):
    from src.models import User
    from src.repositories.users import UserRepository

    user = User(id="int-user-1", email="int@example.com", encryption_key=sample_key)
    UserRepository().save(user)
    return user


def test_full_register_flow(db, integration_user, sample_key):
    from src.crypto import encrypt_payload
    from src.models import Campaign, LinkPayload, ResponseButton
    from src.repositories.campaigns import CampaignRepository
    from src.repositories.response_buttons import ResponseButtonRepository
    from src.services.links import LinksService
    from src.services.responses import ResponsesService
    from src.services.users import UserService
    from unittest.mock import MagicMock

    campaign = CampaignRepository().create(
        Campaign(
            id=str(uuid.uuid4()),
            name="Integration Campaign",
            user_id=integration_user.id,
            record_answers=True,
            forward_answers=False,
        )
    )
    button = ResponseButtonRepository().create(
        ResponseButton(id=str(uuid.uuid4()), text="Attending", campaign_id=campaign.id)
    )

    user_svc = UserService()
    links = LinksService(user_service=user_svc)
    email_id = str(uuid.uuid4())

    result = links.create_links(
        integration_user.id,
        integration_user.email,
        subject="Party invite",
        recipients=["guest@example.com"],
        buttons=[{"response_button_id": button.id}],
        email_id=email_id,
    )

    token = result["links"][0]["url"].split("p=")[1]

    responses_svc = ResponsesService(gmail_client=MagicMock())
    reg = responses_svc.register(token, confirmed=True)
    assert reg.status == "success"

    # Duplicate should fail
    from src.models import DuplicateError

    with pytest.raises(DuplicateError):
        responses_svc.register(token, confirmed=True)

    from src.repositories.responses import ResponseRepository

    stored = ResponseRepository().list_by_campaign(campaign.id)
    assert len(stored) == 1
    assert stored[0].text == "Attending"
