"""User provisioning and key management."""

from __future__ import annotations

from src.crypto import generate_encryption_key
from src.models import AppError, User
from src.repositories.users import UserRepository


class UserService:
    def __init__(self, user_repo: UserRepository | None = None):
        self.user_repo = user_repo or UserRepository()

    def get_or_create(self, uid: str, email: str) -> User:
        existing = self.user_repo.get(uid)
        if existing:
            return existing
        user = User(
            id=uid,
            email=email,
            encryption_key=generate_encryption_key(),
        )
        return self.user_repo.save(user)

    def get_user(self, uid: str) -> User:
        user = self.user_repo.get(uid)
        if not user:
            raise AppError("User not found", status_code=404)
        return user

    def rotate_key(self, uid: str) -> str:
        new_key = generate_encryption_key()
        self.user_repo.update_encryption_key(uid, new_key)
        return new_key
