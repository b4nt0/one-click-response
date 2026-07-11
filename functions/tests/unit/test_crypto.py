"""Crypto unit tests."""

import json

import pytest

from src.crypto import decrypt_payload, encrypt_payload, generate_encryption_key
from src.models import AppError, LinkPayload


def test_generate_encryption_key_length():
    key = generate_encryption_key()
    assert isinstance(key, str)
    assert len(key) > 0


def test_encrypt_decrypt_round_trip_with_button_text(sample_key):
    payload = LinkPayload(
        version=1,
        email_id="email-1",
        subject="Hello",
        recipients=["a@x.com"],
        response_button_id="btn-1",
        campaign_id=None,
        owner_user_id="user-1",
        button_text="Maybe",
    )
    token = encrypt_payload(payload, sample_key)
    restored = decrypt_payload(token, sample_key)
    assert restored.button_text == "Maybe"


def test_encrypt_decrypt_round_trip(sample_key):
    payload = LinkPayload(
        version=1,
        email_id="email-1",
        subject="Hello",
        recipients=["a@x.com"],
        response_button_id="btn-1",
        campaign_id="camp-1",
        owner_user_id="user-1",
    )
    token = encrypt_payload(payload, sample_key)
    restored = decrypt_payload(token, sample_key)
    assert restored.email_id == payload.email_id
    assert restored.subject == payload.subject
    assert restored.recipients == payload.recipients


def test_decrypt_wrong_key_fails(sample_key):
    payload = LinkPayload(
        version=1,
        email_id="email-1",
        subject="Hello",
        recipients=["a@x.com"],
        response_button_id="btn-1",
        campaign_id=None,
        owner_user_id="user-1",
    )
    token = encrypt_payload(payload, sample_key)
    other_key = generate_encryption_key()
    with pytest.raises(AppError):
        decrypt_payload(token, other_key)


def test_decrypt_tampered_ciphertext_fails(sample_key):
    payload = LinkPayload(
        version=1,
        email_id="email-1",
        subject="Hello",
        recipients=["a@x.com"],
        response_button_id="btn-1",
        campaign_id=None,
        owner_user_id="user-1",
    )
    token = encrypt_payload(payload, sample_key)
    tampered = token[:-4] + "XXXX"
    with pytest.raises(AppError):
        decrypt_payload(tampered, sample_key)
