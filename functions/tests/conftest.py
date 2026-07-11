"""Shared pytest fixtures."""

from __future__ import annotations

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

# Ensure functions package is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


@pytest.fixture
def sample_key():
    from src.crypto import generate_encryption_key

    return generate_encryption_key()


@pytest.fixture
def mock_user(sample_key):
    from src.models import User

    return User(
        id="user-1",
        email="owner@example.com",
        encryption_key=sample_key,
    )


@pytest.fixture
def mock_campaign():
    from src.models import Campaign

    return Campaign(
        id="camp-1",
        name="Test Campaign",
        user_id="user-1",
        record_answers=True,
        forward_answers=False,
    )


@pytest.fixture
def mock_button():
    from src.models import ResponseButton

    return ResponseButton(id="btn-1", text="Yes", campaign_id="camp-1", order=0)


@pytest.fixture
def mock_loose_button():
    from src.models import ResponseButton

    return ResponseButton(id="btn-loose", text="Maybe", user_id="user-1", order=0)


@pytest.fixture
def app_client():
    from src.api import app

    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def auth_headers():
    return {"Authorization": "Bearer test-token"}


@pytest.fixture
def mock_verify_token(mock_user):
    with patch("src.api.resolve_auth_user") as verify:
        verify.return_value = {"uid": mock_user.id, "email": mock_user.email}
        with patch("src.api.user_service") as user_svc:
            user_svc.get_or_create.return_value = mock_user
            yield verify
