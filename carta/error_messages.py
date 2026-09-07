"""Formatting helpers for user-facing CARTA error messages."""

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import requests


_STATUS_SUGGESTIONS = {
    400: "Check the scripting request parameters.",
    403: "Check the CARTA token and authentication settings.",
    404: "Verify the session ID and confirm that the session is still active.",
    500: "Check the CARTA backend logs for the underlying error.",
    501: "Restart the CARTA backend with the `--enable_scripting` option.",
}


def format_frontend_version_unavailable_error(current, include_warn_suggestion):
    """Format the error raised when the frontend version cannot be retrieved."""
    suggestions = [
        f"Upgrade CARTA to at least {current.carta_minimum_version!r}.",
        "If CARTA is already '6.0.0' or newer, wait until the frontend is fully loaded and retry.",
    ]
    if include_warn_suggestion:
        suggestions.append(
            "If this combination is known to work, set `version_mismatch_action=VersionMismatchAction.WARN`."
        )

    return (
        "CARTA version validation failed:\n"
        "- Could not retrieve `frontendVersion` from the CARTA frontend.\n"
        "- CARTA versions earlier than '6.0.0' do not expose `frontendVersion`.\n"
        f"- carta-python {current.wrapper_label} requires CARTA "
        f"{current.carta_minimum_version!r} or later.\n\n"
        "Suggested actions:\n"
        + "\n".join(f"- {suggestion}" for suggestion in suggestions)
    )


def format_version_mismatch_error(mismatches, suggestions, include_warn_suggestion):
    """Format a CARTA/carta-python version compatibility error."""
    suggestions = list(suggestions)
    if include_warn_suggestion:
        suggestions.append(
            "If this combination is known to work, set `version_mismatch_action=VersionMismatchAction.WARN`."
        )

    message = "CARTA version validation failed:\n" + "\n".join(
        f"- {mismatch}" for mismatch in mismatches
    )
    if suggestions:
        message += "\n\nSuggested actions:\n" + "\n".join(
            f"- {suggestion}" for suggestion in suggestions
        )
    return message


def format_session_validation_error(session_id, uri, timeout, error):
    """Format the error raised when a CARTA session cannot be validated."""
    safe_uri = _redact_url(uri)

    cause = error
    while cause.__cause__ is not None:
        cause = cause.__cause__

    if isinstance(cause, requests.exceptions.Timeout):
        message = (
            f"Could not validate CARTA session {session_id}: "
            f"request timed out after {timeout} seconds.\n"
            f"Endpoint: {safe_uri!r}\n"
            f"Timeout: {timeout} seconds\n"
            "Action: fetchParameter(frontendVersion)\n"
            "The CARTA scripting request did not receive a response before the timeout.\n\n"
            "Possible causes:\n"
            "- The CARTA backend/frontend is not reachable.\n"
            "- The frontend has not finished loading.\n"
            "- The session ID is wrong or the session has closed.\n\n"
            "Suggested actions:\n"
            f"- Retry with a longer `connection_check_timeout` than {timeout} seconds.\n"
            "- Verify that the CARTA session is still active.\n"
        )
    elif getattr(error, "status_code", None) is not None:
        status_code = error.status_code
        backend_message = getattr(error, "backend_message", str(error))
        message = (
            f"Could not validate CARTA session {session_id}: "
            f"the CARTA backend returned HTTP status {status_code}.\n"
            f"Endpoint: {safe_uri!r}\n"
            "Action: fetchParameter(frontendVersion)\n"
            f"Reason: {backend_message}\n"
        )
        suggested_action = _STATUS_SUGGESTIONS.get(status_code)
        if suggested_action:
            message += f"\nSuggested action:\n- {suggested_action}"
    else:
        message = (
            f"Could not validate CARTA session {session_id}.\n"
            f"Endpoint: {safe_uri!r}\n"
            f"Timeout setting: {timeout} seconds\n"
            "Action: fetchParameter(frontendVersion)\n\n"
            f"Original error ({error.__class__.__name__}): {error}"
        )

    return message.rstrip()


def _redact_url(uri):
    """Remove authentication tokens from URLs included in error messages."""
    if uri is None:
        return None

    parsed = urlsplit(uri)
    query = [
        (key, "<redacted>" if key.lower() in {"token", "access_token"} else value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
    ]
    return urlunsplit(parsed._replace(query=urlencode(query)))
