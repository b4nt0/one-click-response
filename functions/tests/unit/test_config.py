"""Config unit tests."""

from unittest.mock import patch

import pytest

from src import config


def test_resolve_public_host_url_prefers_client_override():
    with patch.dict("os.environ", {"HOST_URL": "http://"}, clear=False):
        url = config.resolve_public_host_url("https://one-click-response.web.app")
    assert url == "https://one-click-response.web.app"


def test_resolve_public_host_url_from_request(app_client):
    with patch.dict("os.environ", {"HOST_URL": ""}, clear=False):
        with app_client.application.test_request_context(
            "/api/links",
            headers={
                "Host": "one-click-response.web.app",
                "X-Forwarded-Proto": "https",
            },
        ):
            url = config.resolve_public_host_url()
    assert url == "https://one-click-response.web.app"


def test_validate_host_url_rejects_scheme_only():
    with pytest.raises(ValueError):
        config.validate_host_url("http://")
