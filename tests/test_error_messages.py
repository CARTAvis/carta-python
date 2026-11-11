import pytest

from carta.error_messages import _redact_url, format_session_validation_error
from carta.util import CartaRequestFailed


@pytest.mark.parametrize(
    "uri, expected",
    [
        (None, None),
        ("http://localhost:3002/", "http://localhost:3002/"),
        ("http://localhost:3002/?token=abc", "http://localhost:3002/?token=<redacted>"),
        ("http://localhost:3002/?a=1&TOKEN=abc&b=x%20y", "http://localhost:3002/?a=1&TOKEN=<redacted>&b=x%20y"),
        ("http://h/?access_token=abc;token=def", "http://h/?access_token=<redacted>;token=<redacted>"),
        ("http://h/?mytoken=abc", "http://h/?mytoken=abc"),
        ("http://user:secret@h:3002/?token=abc", "http://<redacted>@h:3002/?token=<redacted>"),
        ("http://h/#token=abc", "http://h/#token=<redacted>"),
    ],
)
def test_redact_url(uri, expected):
    assert _redact_url(uri) == expected


def test_session_validation_error_redacts_endpoint():
    error = CartaRequestFailed("failed", status_code=403, backend_message="Forbidden")

    message = format_session_validation_error(
        session_id=1, uri="http://h:3002/?token=secret", timeout=10, error=error
    )

    assert "secret" not in message
    assert "Endpoint: 'http://h:3002/?token=<redacted>'" in message
