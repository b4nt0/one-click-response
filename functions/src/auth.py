"""Firebase Auth token verification."""

from __future__ import annotations

import base64
import json
import logging
import os
import time
from typing import Any

import firebase_admin
from firebase_admin import auth

from src.models import AppError

logger = logging.getLogger(__name__)

_app_initialized = False


def init_firebase() -> None:
    global _app_initialized
    if _app_initialized:
        return
    if os.environ.get("FIRESTORE_EMULATOR_HOST"):
        firebase_admin.initialize_app(options={"projectId": os.environ.get("GCLOUD_PROJECT", "one-click-response")})
    else:
        firebase_admin.initialize_app()
    _app_initialized = True


def _extract_bearer_token(authorization_header: str | None) -> str:
    if not authorization_header or not authorization_header.startswith("Bearer "):
        raise AppError("Missing or invalid authorization header", status_code=401, code="unauthorized")
    return authorization_header.removeprefix("Bearer ").strip()


def _fingerprint(value: str) -> str:
    """Short non-secret identifier for OAuth client IDs in logs and API debug output."""
    if not value:
        return "(unset)"
    if len(value) <= 16:
        return value[:4] + "…" if len(value) > 4 else value
    return f"{value[:12]}…{value[-6:]}"


def _decode_jwt_payload_unverified(token: str) -> dict[str, Any]:
    """Decode JWT payload without verification — diagnostics only."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return {"decode_error": f"expected 3 JWT parts, got {len(parts)}"}
        payload = parts[1]
        padding = "=" * (-len(payload) % 4)
        data = json.loads(base64.urlsafe_b64decode((payload + padding).encode("ascii")))
        if not isinstance(data, dict):
            return {"decode_error": "payload is not a JSON object"}
        return data
    except Exception as exc:
        return {"decode_error": f"{type(exc).__name__}: {exc}"}


def _safe_token_claims(token: str) -> dict[str, Any]:
    """Return token claims safe to echo back to the caller for debugging."""
    claims = _decode_jwt_payload_unverified(token)
    if "decode_error" in claims:
        return claims

    exp = claims.get("exp")
    now = int(time.time())
    exp_info: dict[str, Any] = {}
    if isinstance(exp, (int, float)):
        exp_info = {
            "exp": int(exp),
            "expires_in_seconds": int(exp) - now,
            "expired": int(exp) < now,
        }

    return {
        "iss": claims.get("iss"),
        "aud": claims.get("aud"),
        "azp": claims.get("azp"),
        "sub": claims.get("sub"),
        "email": claims.get("email"),
        "email_verified": claims.get("email_verified"),
        "iat": claims.get("iat"),
        **exp_info,
    }


def _configured_audience_candidates() -> list[dict[str, str]]:
    """Ordered OAuth client ID candidates from trusted server configuration only."""
    raw_candidates = [
        ("APPS_SCRIPT_OAUTH_CLIENT_ID", os.environ.get("APPS_SCRIPT_OAUTH_CLIENT_ID", "")),
        ("GMAIL_CLIENT_ID", os.environ.get("GMAIL_CLIENT_ID", "")),
    ]

    seen: set[str] = set()
    result: list[dict[str, str]] = []
    for source, value in raw_candidates:
        if value and value not in seen:
            seen.add(value)
            result.append({"source": source, "audience": value, "fingerprint": _fingerprint(value)})
    return result


def verify_id_token(authorization_header: str | None) -> dict:
    token = _extract_bearer_token(authorization_header)
    try:
        init_firebase()
        return auth.verify_id_token(token)
    except AppError:
        raise
    except Exception as exc:
        logger.warning("Firebase ID token verification failed: %s: %s", type(exc).__name__, exc)
        raise AppError("Invalid authentication token", status_code=401, code="unauthorized") from exc


def try_verify_google_identity_token(token: str, audience: str) -> tuple[dict | None, str | None]:
    """Attempt Google OIDC verification; return (claims, error_message)."""
    from google.auth.transport import requests as google_requests
    from google.oauth2 import id_token as google_id_token

    try:
        claims = google_id_token.verify_oauth2_token(
            token, google_requests.Request(), audience=audience
        )
        return claims, None
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        logger.warning(
            "Google identity token verification failed: audience=%s (%s) error=%s",
            _fingerprint(audience),
            audience,
            error,
        )
        return None, error


def verify_google_identity_token(token: str, audience: str) -> dict:
    """Verify Apps Script / Google OIDC identity token."""
    claims, error = try_verify_google_identity_token(token, audience)
    if claims is not None:
        return claims
    raise AppError("Invalid identity token", status_code=401, code="unauthorized")


def inspect_identity_token(token: str) -> dict[str, Any]:
    """Build a full auth diagnostic report (safe to return to the token holder)."""
    claims = _safe_token_claims(token)
    candidates = _configured_audience_candidates()

    firebase_attempt: dict[str, Any] = {"attempted": True}
    try:
        init_firebase()
        firebase_claims = auth.verify_id_token(token)
        firebase_attempt = {
            "attempted": True,
            "success": True,
            "uid": firebase_claims.get("uid"),
            "email": firebase_claims.get("email"),
        }
    except Exception as exc:
        firebase_attempt = {
            "attempted": True,
            "success": False,
            "error": f"{type(exc).__name__}: {exc}",
        }

    verification_attempts: list[dict[str, Any]] = []
    for candidate in candidates:
        claims_result, error = try_verify_google_identity_token(token, candidate["audience"])
        verification_attempts.append(
            {
                "source": candidate["source"],
                "audience_fingerprint": candidate["fingerprint"],
                "success": claims_result is not None,
                "error": error,
                "email": (claims_result or {}).get("email") if claims_result else None,
            }
        )

    configured = {
        "APPS_SCRIPT_OAUTH_CLIENT_ID": {
            "set": bool(os.environ.get("APPS_SCRIPT_OAUTH_CLIENT_ID")),
            "fingerprint": _fingerprint(os.environ.get("APPS_SCRIPT_OAUTH_CLIENT_ID", "")),
        },
        "GMAIL_CLIENT_ID": {
            "set": bool(os.environ.get("GMAIL_CLIENT_ID")),
            "fingerprint": _fingerprint(os.environ.get("GMAIL_CLIENT_ID", "")),
        },
    }

    token_aud = claims.get("aud") if isinstance(claims, dict) else None
    apps_script_fp = configured["APPS_SCRIPT_OAUTH_CLIENT_ID"]["fingerprint"]
    token_aud_fp = _fingerprint(token_aud) if isinstance(token_aud, str) else "(not a string)"
    audience_match_hint = None
    if isinstance(token_aud, str) and token_aud:
        if configured["APPS_SCRIPT_OAUTH_CLIENT_ID"]["set"]:
            if token_aud == os.environ.get("APPS_SCRIPT_OAUTH_CLIENT_ID", ""):
                audience_match_hint = "token aud matches APPS_SCRIPT_OAUTH_CLIENT_ID"
            else:
                audience_match_hint = (
                    f"token aud ({token_aud_fp}) does NOT match configured "
                    f"APPS_SCRIPT_OAUTH_CLIENT_ID ({apps_script_fp})"
                )
        else:
            audience_match_hint = "APPS_SCRIPT_OAUTH_CLIENT_ID is not set on the backend"

    any_google_success = any(a["success"] for a in verification_attempts)

    return {
        "token_claims": claims,
        "configured_secrets": configured,
        "audience_candidates": candidates,
        "audience_match_hint": audience_match_hint,
        "firebase_id_token_attempt": firebase_attempt,
        "google_identity_verification_attempts": verification_attempts,
        "any_verification_succeeded": firebase_attempt.get("success") or any_google_success,
        "hint": (
            "Set APPS_SCRIPT_OAUTH_CLIENT_ID to the token aud claim shown above, then redeploy functions."
            if isinstance(token_aud, str) and token_aud and not any_google_success
            else None
        ),
    }


def _firebase_user_for_email(email: str, *, email_verified: bool = False):
    """Load Firebase Auth user by email, creating one if the add-on identity is new."""
    try:
        return auth.get_user_by_email(email)
    except auth.UserNotFoundError:
        return auth.create_user(email=email, email_verified=email_verified)


def resolve_auth_user(authorization_header: str | None) -> dict:
    """Resolve {uid, email} from Firebase ID token (web) or Google identity token (add-on)."""
    token = _extract_bearer_token(authorization_header)
    init_firebase()

    # Web settings uses Firebase ID tokens.
    try:
        claims = auth.verify_id_token(token)
        logger.info("Authenticated via Firebase ID token: uid=%s", claims.get("uid"))
        return {"uid": claims["uid"], "email": claims.get("email", "")}
    except Exception as exc:
        logger.info("Not a Firebase ID token (%s: %s); trying Google identity token", type(exc).__name__, exc)

    candidates = _configured_audience_candidates()
    if not candidates:
        debug_report = inspect_identity_token(token)
        logger.error("No OAuth audience candidates configured for add-on auth")
        raise AppError(
            "Add-on authentication is not configured (APPS_SCRIPT_OAUTH_CLIENT_ID).",
            status_code=500,
            code="server_misconfigured",
            debug=debug_report,
        )

    last_error: str | None = None
    for candidate in candidates:
        audience = candidate["audience"]
        claims, error = try_verify_google_identity_token(token, audience)
        if claims is not None:
            email = claims.get("email")
            if not email:
                debug_report = inspect_identity_token(token)
                logger.error("Identity token verified but missing email claim: aud=%s", _fingerprint(audience))
                raise AppError(
                    "Identity token is missing email.",
                    status_code=401,
                    code="unauthorized",
                    debug=debug_report,
                )
            firebase_user = _firebase_user_for_email(
                email, email_verified=bool(claims.get("email_verified"))
            )
            logger.info(
                "Authenticated via Google identity token: email=%s uid=%s audience=%s",
                email,
                firebase_user.uid,
                _fingerprint(audience),
            )
            return {"uid": firebase_user.uid, "email": email}
        last_error = error

    debug_report = inspect_identity_token(token)
    logger.error(
        "All identity token verification attempts failed. token_aud=%s configured_apps_script=%s last_error=%s",
        debug_report.get("token_claims", {}).get("aud"),
        debug_report.get("configured_secrets", {}).get("APPS_SCRIPT_OAUTH_CLIENT_ID"),
        last_error,
    )
    raise AppError(
        "Invalid authentication token. Check APPS_SCRIPT_OAUTH_CLIENT_ID matches the add-on OAuth client (token aud claim).",
        status_code=401,
        code="unauthorized",
        debug=debug_report,
    )


def inspect_authorization_header(authorization_header: str | None) -> dict[str, Any]:
    """Diagnostic entry point for /api/auth/inspect."""
    try:
        token = _extract_bearer_token(authorization_header)
    except AppError as exc:
        return {
            "error": exc.message,
            "code": exc.code,
            "token_claims": None,
        }
    return inspect_identity_token(token)
