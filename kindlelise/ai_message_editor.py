"""Request one bounded edit of an unsent message draft from Ollama Cloud."""

import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from django.conf import settings

_MAX_MESSAGE_LENGTH = 1_000
_MAX_RESPONSE_BYTES = 65_536
_EDITING_INSTRUCTIONS = {
    "fix_grammar": (
        "Correct grammar only. Preserve the meaning and tone. "
        "Return only the revised draft as plain text."
    ),
    "improve_clarity": (
        "Improve clarity only. Preserve the meaning and tone. "
        "Return only the revised draft as plain text."
    ),
}


def get_edited_message_draft_suggestion(draft, editing_goal):
    """Send only one bounded unsent draft and fixed goal to Ollama Cloud.

    Inputs: a plain-text draft and one mapped grammar or clarity goal.
    Returns: bounded non-empty suggestion text, or None after safe failure.
    Changes: makes one short external request; stores and sends no message.
    Refuses: invalid input, configuration, endpoint, response or provider failure.
    Privacy: sends no account, profile, recipient, history, report or plan data and
        never logs the draft, suggestion or credential.
    """
    if not isinstance(draft, str) or editing_goal not in _EDITING_INSTRUCTIONS:
        return None
    clean_draft = draft.strip()
    if not clean_draft or len(clean_draft) > _MAX_MESSAGE_LENGTH:
        return None

    api_url = settings.OLLAMA_API_URL
    api_key = settings.OLLAMA_API_KEY
    model = settings.OLLAMA_MODEL
    if not all(isinstance(value, str) and value for value in (api_url, api_key, model)):
        return None
    parsed_url = urlsplit(api_url)
    if (
        parsed_url.scheme != "https"
        or not parsed_url.netloc
        or parsed_url.username
        or parsed_url.password
        or parsed_url.fragment
    ):
        return None

    request_body = json.dumps(
        {
            "model": model,
            "prompt": clean_draft,
            "system": _EDITING_INSTRUCTIONS[editing_goal],
            "stream": False,
        }
    ).encode("utf-8")
    provider_request = Request(
        api_url,
        data=request_body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        provider_response = urlopen(
            provider_request,
            timeout=settings.OLLAMA_TIMEOUT_SECONDS,
        )
        try:
            raw_response = provider_response.read(_MAX_RESPONSE_BYTES + 1)
        finally:
            provider_response.close()
        if len(raw_response) > _MAX_RESPONSE_BYTES:
            return None
        response_values = json.loads(raw_response.decode("utf-8"))
    except (
        HTTPError,
        URLError,
        TimeoutError,
        OSError,
        UnicodeDecodeError,
        json.JSONDecodeError,
    ):
        return None

    if not isinstance(response_values, dict) or response_values.get("done") is not True:
        return None
    suggestion = response_values.get("response")
    if not isinstance(suggestion, str):
        return None
    suggestion = suggestion.strip()
    if not suggestion or len(suggestion) > _MAX_MESSAGE_LENGTH:
        return None
    return suggestion
