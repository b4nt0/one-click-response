"""Firestore client singleton."""

from __future__ import annotations

from google.cloud import firestore

from src.auth import init_firebase

_db: firestore.Client | None = None


def get_db() -> firestore.Client:
    global _db
    if _db is None:
        init_firebase()
        _db = firestore.Client()
    return _db
