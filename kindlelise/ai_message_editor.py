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

    # WHY: Reads the changeable service details from deployment settings rather than saving secrets here.
    api_url = settings.OLLAMA_API_URL
    api_key = settings.OLLAMA_API_KEY
    model = settings.OLLAMA_MODEL
    # WHY: Stops quietly when the service address or chosen model has not been configured.
    if not all(isinstance(value, str) and value for value in (api_url, model)):
        return None

    # WHY: Separates the address into parts so unsafe forms can be refused explicitly.
    parsed_url = urlsplit(api_url)

    # WHY: Allows unencrypted HTTP only for a service running on the same computer during development.
    is_local_http = (
        parsed_url.scheme == "http"
        and parsed_url.hostname in {"127.0.0.1", "localhost", "::1"}
    )
    # WHY: Refuses public unencrypted addresses, embedded passwords, fragments, and incomplete hosts.
    if (
        parsed_url.scheme != "https" and not is_local_http
        or not parsed_url.netloc
        or parsed_url.username
        or parsed_url.password
        or parsed_url.fragment
    ):
        return None
    # WHY: Requires the private service key whenever a request leaves the local computer.
    if parsed_url.scheme == "https" and not api_key:
        return None

    # WHY: Labels the body as JSON and adds the private key only when one is configured.
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    # WHY: Sends only the model, unsent draft, fixed goal, and a request for one complete reply.
    request_body = json.dumps(
        {
            "model": model,
            "prompt": clean_draft,
            "system": _EDITING_INSTRUCTIONS[editing_goal],
            "stream": False,
        }
    ).encode("utf-8")
    # WHY: Prepares one POST request without including any account, recipient, or message history.
    provider_request = Request(
        api_url,
        data=request_body,
        headers=headers,
        method="POST",
    )

    try:
        # WHY: The URL scheme, host, and embedded credentials were restricted above.
        provider_response = urlopen(  # nosec B310
            provider_request,
            timeout=settings.OLLAMA_TIMEOUT_SECONDS,
            context=ssl.create_default_context(cafile=certifi.where()),
        )
        # WHY: Reads one byte beyond the limit so an oversized reply can be detected and refused.
        try:
            raw_response = provider_response.read(_MAX_RESPONSE_BYTES + 1)
        finally:
            # WHY: Closes the network response even if reading it fails.
            provider_response.close()

        # WHY: Refuses an oversized reply rather than attempting to use partial wording.
        if len(raw_response) > _MAX_RESPONSE_BYTES:
            return None

        # WHY: Converts the service's labelled text response into values this code can check.
        response_values = json.loads(raw_response.decode("utf-8"))
    # WHY: Treats network, timeout, decoding, and invalid-response failures alike without exposing private details.
    except (
        HTTPError,
        URLError,
        TimeoutError,
        OSError,
        UnicodeDecodeError,
        json.JSONDecodeError,
    ):
        return None

    # WHY: Accepts only a complete labelled response rather than an unfinished streamed reply.
    if not isinstance(response_values, dict) or response_values.get("done") is not True:
        return None

    # WHY: Reads only the expected suggestion field from the checked response.
    suggestion = response_values.get("response")
    if not isinstance(suggestion, str):
        return None
    # WHY: Removes surrounding space and applies the same size rule as the original draft.
    suggestion = suggestion.strip()
    if not suggestion or len(suggestion) > _MAX_MESSAGE_LENGTH:
        return None
    # WHY: Returns wording for review only; this function never saves or sends the message.
    return suggestion
