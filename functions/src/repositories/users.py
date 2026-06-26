"""User repository."""

from __future__ import annotations

from src.models import User
from src.repositories.db import get_db


class UserRepository:
    def get(self, user_id: str) -> User | None:
        doc = get_db().collection("users").document(user_id).get()
        if not doc.exists:
            return None
        return User.from_firestore(doc.id, doc.to_dict())

    def save(self, user: User) -> User:
        get_db().collection("users").document(user.id).set(user.to_firestore())
        return user

    def update_encryption_key(self, user_id: str, key: str) -> None:
        get_db().collection("users").document(user_id).update({"encryption_key": key})
