"""Firebase Cloud Function entry point."""

from firebase_functions import https_fn, options
from firebase_functions.options import CorsOptions
from firebase_functions.params import StringParam

from src.api import app

# Non-secret configuration — set via functions/.env or prompted during deploy.
HOST_URL = StringParam(
    "HOST_URL",
    default="http://localhost:5000",
    description="Public Hosting URL used in encrypted response links.",
)

# Declare secrets so Firebase injects them into os.environ at runtime.
_FUNCTION_SECRETS = [
    "GMAIL_CLIENT_ID",
    "GMAIL_CLIENT_SECRET",
    "GMAIL_REFRESH_TOKEN",
    "GMAIL_SENDER_EMAIL",
    "APPS_SCRIPT_OAUTH_CLIENT_ID",
]


def _flask_to_https_response(flask_response) -> https_fn.Response:
    headers = {k: v for k, v in flask_response.headers.items() if k.lower() != "content-length"}
    return https_fn.Response(
        flask_response.get_data(),
        status=flask_response.status_code,
        headers=headers,
    )


@https_fn.on_request(
    cors=CorsOptions(
        cors_origins="*",
        cors_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    ),
    memory=options.MemoryOption.MB_512,
    timeout_sec=60,
    secrets=_FUNCTION_SECRETS,
)
def api(req: https_fn.Request) -> https_fn.Response:
    with app.request_context(req.environ):
        return _flask_to_https_response(app.full_dispatch_request())
