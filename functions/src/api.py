"""HTTP API routing."""

from __future__ import annotations

from functools import wraps

from flask import Flask, jsonify, request

from src import config
from src.auth import (
    inspect_authorization_header,
    resolve_auth_user,
    verify_google_identity_token,
)
from src.models import AppError, DuplicateError
from src.services.campaigns import CampaignService
from src.services.links import LinksService
from src.services.responses import ResponsesService
from src.services.users import UserService

app = Flask(__name__)

user_service = UserService()
links_service = LinksService(user_service=user_service)
responses_service = ResponsesService()
campaign_service = CampaignService()


def _json_error(error: AppError):
    body: dict = {"error": error.message, "code": error.code}
    if error.debug:
        body["debug"] = error.debug
    return jsonify(body), error.status_code


def require_auth(handler):
    @wraps(handler)
    def wrapper(*args, **kwargs):
        try:
            claims = resolve_auth_user(request.headers.get("Authorization"))
            user = user_service.get_or_create(claims["uid"], claims.get("email", ""))
            return handler(user, *args, **kwargs)
        except AppError as exc:
            return _json_error(exc)

    return wrapper


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/api/links", methods=["POST"])
@require_auth
def create_links(user):
    try:
        body = request.get_json(silent=True) or {}
        result = links_service.create_links(
            user.id,
            user.email,
            subject=body.get("subject", ""),
            recipients=body.get("recipients", []),
            buttons=body.get("buttons", []),
            email_id=body.get("email_id"),
            host_url=body.get("host_url"),
        )
        return jsonify(result)
    except AppError as exc:
        return _json_error(exc)


@app.route("/api/responses/preview", methods=["POST"])
def preview_response():
    try:
        body = request.get_json(silent=True) or {}
        token = body.get("p", "")
        preview = responses_service.preview(token)
        return jsonify(
            {
                "button_text": preview.button_text,
                "subject": preview.subject,
                "campaign_name": preview.campaign_name,
            }
        )
    except AppError as exc:
        return _json_error(exc)


@app.route("/api/responses", methods=["POST"])
def register_response():
    try:
        body = request.get_json(silent=True) or {}
        token = body.get("p", "")
        result = responses_service.register(token, confirmed=bool(body.get("confirmed")))
        return jsonify(
            {
                "status": result.status,
                "button_text": result.button_text,
                "subject": result.subject,
                "owner_email": result.owner_email,
                "campaign_name": result.campaign_name,
            }
        )
    except DuplicateError as exc:
        return _json_error(exc)
    except AppError as exc:
        return _json_error(exc)


@app.route("/api/campaigns", methods=["GET"])
@require_auth
def list_campaigns(user):
    campaigns = campaign_service.list_campaigns(user.id)
    return jsonify([_campaign_to_dict(c) for c in campaigns])


@app.route("/api/campaigns", methods=["POST"])
@require_auth
def create_campaign(user):
    body = request.get_json(silent=True) or {}
    campaign = campaign_service.create_campaign(
        user.id,
        name=body.get("name", ""),
        record_answers=bool(body.get("record_answers", False)),
        forward_answers=bool(body.get("forward_answers", False)),
    )
    return jsonify(_campaign_to_dict(campaign)), 201


@app.route("/api/campaigns/<campaign_id>", methods=["GET"])
@require_auth
def get_campaign(user, campaign_id):
    try:
        campaign = campaign_service.get_campaign(user.id, campaign_id)
        return jsonify(_campaign_to_dict(campaign))
    except AppError as exc:
        return _json_error(exc)


@app.route("/api/campaigns/<campaign_id>", methods=["PUT"])
@require_auth
def update_campaign(user, campaign_id):
    try:
        body = request.get_json(silent=True) or {}
        campaign = campaign_service.update_campaign(
            user.id,
            campaign_id,
            name=body.get("name"),
            record_answers=body.get("record_answers"),
            forward_answers=body.get("forward_answers"),
        )
        return jsonify(_campaign_to_dict(campaign))
    except AppError as exc:
        return _json_error(exc)


@app.route("/api/campaigns/<campaign_id>", methods=["DELETE"])
@require_auth
def delete_campaign(user, campaign_id):
    try:
        campaign_service.delete_campaign(user.id, campaign_id)
        return "", 204
    except AppError as exc:
        return _json_error(exc)


@app.route("/api/campaigns/<campaign_id>/buttons/reorder", methods=["PUT"])
@require_auth
def reorder_campaign_buttons(user, campaign_id):
    try:
        body = request.get_json(silent=True) or {}
        button_ids = body.get("button_ids", [])
        buttons = campaign_service.reorder_buttons(user.id, campaign_id, button_ids)
        return jsonify([_button_to_dict(b) for b in buttons])
    except AppError as exc:
        return _json_error(exc)


@app.route("/api/campaigns/<campaign_id>/buttons", methods=["GET"])
@require_auth
def list_buttons(user, campaign_id):
    try:
        buttons = campaign_service.list_buttons(user.id, campaign_id)
        return jsonify([_button_to_dict(b) for b in buttons])
    except AppError as exc:
        return _json_error(exc)


@app.route("/api/campaigns/<campaign_id>/buttons", methods=["POST"])
@require_auth
def create_campaign_button(user, campaign_id):
    try:
        body = request.get_json(silent=True) or {}
        button = campaign_service.create_button(
            user.id, text=body.get("text", ""), campaign_id=campaign_id
        )
        return jsonify(_button_to_dict(button)), 201
    except AppError as exc:
        return _json_error(exc)


@app.route("/api/loose-buttons", methods=["GET"])
@require_auth
def list_loose_buttons(user):
    buttons = campaign_service.list_loose_buttons(user.id)
    return jsonify([_button_to_dict(b) for b in buttons])


@app.route("/api/loose-buttons", methods=["POST"])
@require_auth
def create_loose_button(user):
    body = request.get_json(silent=True) or {}
    button = campaign_service.create_button(user.id, text=body.get("text", ""))
    return jsonify(_button_to_dict(button)), 201


@app.route("/api/buttons/<button_id>", methods=["PUT"])
@require_auth
def update_button(user, button_id):
    try:
        body = request.get_json(silent=True) or {}
        button = campaign_service.update_button(user.id, button_id, text=body.get("text", ""))
        return jsonify(_button_to_dict(button))
    except AppError as exc:
        return _json_error(exc)


@app.route("/api/buttons/<button_id>", methods=["DELETE"])
@require_auth
def delete_button(user, button_id):
    try:
        campaign_service.delete_button(user.id, button_id)
        return "", 204
    except AppError as exc:
        return _json_error(exc)


@app.route("/api/campaigns/<campaign_id>/responses", methods=["GET"])
@require_auth
def list_responses(user, campaign_id):
    try:
        responses = campaign_service.list_responses(user.id, campaign_id)
        return jsonify([_response_to_dict(r) for r in responses])
    except AppError as exc:
        return _json_error(exc)


@app.route("/api/users/rotate-key", methods=["POST"])
@require_auth
def rotate_key(user):
    user_service.rotate_key(user.id)
    return jsonify({"encryption_key_rotated": True, "message": "Encryption key rotated."})


@app.route("/api/auth/inspect", methods=["POST", "GET"])
def inspect_auth():
    """Return detailed (non-secret) diagnostics for a Bearer identity token."""
    report = inspect_authorization_header(request.headers.get("Authorization"))
    if report.get("any_verification_succeeded"):
        return jsonify(report)
    return jsonify(report), 401


@app.route("/api/auth/gmail-addon", methods=["POST"])
def gmail_addon_auth():
    """Exchange Apps Script identity token for Firebase custom token flow info."""
    try:
        body = request.get_json(silent=True) or {}
        identity_token = body.get("identity_token", "")
        if not identity_token:
            raise AppError("identity_token is required", status_code=400)
        audience = body.get("audience", config.GMAIL_CLIENT_ID)
        claims = verify_google_identity_token(identity_token, audience)
        email = claims.get("email", "")
        return jsonify({"email": email, "sub": claims.get("sub")})
    except AppError as exc:
        return _json_error(exc)


def _campaign_to_dict(campaign):
    return {
        "id": campaign.id,
        "name": campaign.name,
        "record_answers": campaign.record_answers,
        "forward_answers": campaign.forward_answers,
    }


def _button_to_dict(button):
    return {
        "id": button.id,
        "text": button.text,
        "campaign_id": button.campaign_id,
        "user_id": button.user_id,
        "order": button.order,
    }


def _response_to_dict(response):
    return {
        "id": response.id,
        "text": response.text,
        "recipient": response.recipient,
        "subject": response.subject,
        "email_id": response.email_id,
        "created_at": response.created_at.isoformat(),
    }


def create_app() -> Flask:
    return app
