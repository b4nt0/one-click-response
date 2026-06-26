"""Application configuration."""

import os
from urllib.parse import urlparse

_DEFAULT_HOST_URL = "http://localhost:5000"


def validate_host_url(raw: str) -> str:
    """Return a normalized public base URL or raise ValueError."""
    base = raw.strip().rstrip("/")
    parsed = urlparse(base)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError(
            f"HOST_URL must be a full URL with hostname (e.g. https://my-app.web.app), got {raw!r}"
        )
    return base


def get_host_url() -> str:
    """Public hosting base URL from HOST_URL env (no trailing slash)."""
    raw = os.environ.get("HOST_URL", "").strip()
    if not raw:
        raw = _DEFAULT_HOST_URL
    return validate_host_url(raw)


def resolve_public_host_url(host_url_override: str | None = None) -> str:
    """Resolve the public URL embedded in response links.

    Priority:
    1. Explicit host_url from the client (Gmail add-on API_BASE_URL or settings page)
    2. Incoming HTTP request Host / X-Forwarded-* (Firebase Hosting rewrite)
    3. HOST_URL environment variable
    """
    if host_url_override and host_url_override.strip():
        return validate_host_url(host_url_override)

    try:
        from flask import has_request_context, request

        if has_request_context():
            host = request.headers.get("X-Forwarded-Host") or request.host
            proto = request.headers.get("X-Forwarded-Proto")
            if not proto:
                proto = "https" if request.is_secure else request.scheme
            if host and not host.endswith(".cloudfunctions.net"):
                return validate_host_url(f"{proto}://{host}")
    except ImportError:
        pass

    return get_host_url()


# Back-compat for tests/patches; prefer resolve_public_host_url() at call time.
HOST_URL = os.environ.get("HOST_URL", _DEFAULT_HOST_URL)
GMAIL_CLIENT_ID = os.environ.get("GMAIL_CLIENT_ID", "")
GMAIL_CLIENT_SECRET = os.environ.get("GMAIL_CLIENT_SECRET", "")
# OAuth client ID of the Apps Script project (audience for ScriptApp.getIdentityToken()).
APPS_SCRIPT_OAUTH_CLIENT_ID = os.environ.get("APPS_SCRIPT_OAUTH_CLIENT_ID", "")
GMAIL_REFRESH_TOKEN = os.environ.get("GMAIL_REFRESH_TOKEN", "")
GMAIL_SENDER_EMAIL = os.environ.get("GMAIL_SENDER_EMAIL", "")

FIRESTORE_EMULATOR_HOST = os.environ.get("FIRESTORE_EMULATOR_HOST")
FIREBASE_AUTH_EMULATOR_HOST = os.environ.get("FIREBASE_AUTH_EMULATOR_HOST")
