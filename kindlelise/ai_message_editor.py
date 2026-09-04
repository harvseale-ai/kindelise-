"""Request one bounded edit of an unsent message draft from Ollama Cloud."""

# KEYWORD: API — a controlled way for this site to ask another service for a result.
# KEYWORD: JSON — a labelled text format used to send and receive small pieces of information.


import json
import ssl
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

import certifi
from django.conf import settings

# =============================================================================
# DRAFT AND RESPONSE LIMITS
# Defines the fixed boundaries and two permitted wording goals.
# =============================================================================

# WHY: Keeps both sent and returned wording within the same limit as an ordinary message.
_MAX_MESSAGE_LENGTH = 1_000

# WHY: Stops an unexpected outside response from using unbounded memory.
_MAX_RESPONSE_BYTES = 65_536

# WHY: Keeps the two allowed editing goals fixed so visitors cannot send hidden instructions.
_EDITING_INSTRUCTIONS = {
    "fix_grammar": (
        "Correct grammar only. Fix spelling, punctuation, capitalisation and "
        "grammar, but preserve the original wording, order, meaning and tone. "
        "Do not rephrase or simplify. "
        "Return only the revised draft as plain text."
    ),
    "improve_clarity": (
        "Improve clarity only. Rewrite for clear, concise and natural wording. "
        "You may restructure sentences and remove repetition, but preserve the "
        "meaning and tone and do not invent facts. "
        "Return only the revised draft as plain text."
    ),
}


# =============================================================================
# OLLAMA DRAFT SUGGESTION
# Sends one bounded unsent draft and returns one suggestion for review.
# =============================================================================

# WHY: Gives plan and message wording tools one bounded provider request without duplicating credential and transport rules.
def request_ollama_text(prompt, system_instruction, maximum_length):
    """Return one complete bounded plain-text Ollama response, or None safely."""
    if (
        not isinstance(prompt, str)
        or not isinstance(system_instruction, str)
        or not isinstance(maximum_length, int)
    ):
        return None
    clean_prompt = prompt.strip()
    if not clean_prompt or not system_instruction or maximum_length < 1:
        return None

    api_url = settings.OLLAMA_API_URL
    api_key = settings.OLLAMA_API_KEY
    model = settings.OLLAMA_MODEL
    if not all(isinstance(value, str) and value for value in (api_url, model)):
        return None

    parsed_url = urlsplit(api_url)
    is_local_http = (
        parsed_url.scheme == "http"
        and parsed_url.hostname in {"127.0.0.1", "localhost", "::1"}
    )
    if (
        parsed_url.scheme != "https" and not is_local_http
        or not parsed_url.netloc
        or parsed_url.username
        or parsed_url.password
        or parsed_url.fragment
    ):
        return None
    if parsed_url.scheme == "https" and not api_key:
        return None

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    request_body = json.dumps(
        {
            "model": model,
            "prompt": clean_prompt,
            "system": system_instruction,
            "stream": False,
        }
    ).encode("utf-8")
    provider_request = Request(
        api_url,
        data=request_body,
        headers=headers,
        method="POST",
    )

    try:
        provider_response = urlopen(  # nosec B310
            provider_request,
            timeout=settings.OLLAMA_TIMEOUT_SECONDS,
            context=ssl.create_default_context(cafile=certifi.where()),
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
    response_text = response_values.get("response")
    if not isinstance(response_text, str):
        return None
    response_text = response_text.strip()
    if not response_text or len(response_text) > maximum_length:
        return None
    return response_text


# WHY: Finds the edited message draft suggestion information in one place so callers receive the same result.
def get_edited_message_draft_suggestion(draft, editing_goal):
    """Send only one bounded unsent draft and fixed goal to Ollama Cloud.

    Inputs: a plain-text draft and one mapped grammar or clarity goal.
    Returns: bounded non-empty suggestion text, or None after safe failure.
    Changes: makes one short external request; stores and sends no message.
    Refuses: invalid input, configuration, endpoint, response or provider failure.
    Privacy: sends no account, profile, recipient, history, report or plan data and
        never logs the draft, suggestion or credential.
    """
    # WHY: Refuses unknown goals and non-text input before contacting the outside service.
    if not isinstance(draft, str) or editing_goal not in _EDITING_INSTRUCTIONS:
        return None

    # WHY: Removes empty space around the draft while preserving the words inside it.
    clean_draft = draft.strip()

    # WHY: Refuses empty or oversized drafts before any information leaves this site.
    if not clean_draft or len(clean_draft) > _MAX_MESSAGE_LENGTH:
        return None

    # WHY: Reuses the shared transport while retaining this feature's fixed instruction and message-sized boundary.
    return request_ollama_text(
        clean_draft,
        _EDITING_INSTRUCTIONS[editing_goal],
        _MAX_MESSAGE_LENGTH,
    )
