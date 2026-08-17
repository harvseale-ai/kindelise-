"""Inbox, direct conversations, sending, and draft improvement pages."""

# WHY: This module keeps the private conversation journey together from opening to sending.
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_POST

from kindlelise.ai_message_editor import get_edited_message_draft_suggestion
from kindlelise.forms import MessageDraftForm, MessageEditRequestForm
from kindlelise.policies import can_access_discovery_plans_and_messages
from kindlelise.selectors import (
    get_messages_if_user_can_open_conversation,
    get_profile_page_if_viewer_is_allowed,
    get_unblocked_conversations_for_inbox,
)
from kindlelise.services.messages import (
    find_or_start_direct_conversation,
    send_direct_message,
)

# =============================================================================
# SHARED CONVERSATION HELPERS
# Applies common message access and prepares the conversation page.
# =============================================================================

# WHY: Keeps the message access redirect steps in one named place so they can be understood, checked, and reused.
def _message_access_redirect(request):
    """Return the private-account redirect when current messaging access is absent."""
    # WHY: Returns no redirect when normal inbox or conversation handling may continue.
    if can_access_discovery_plans_and_messages(request.user):
        return None
    messages.info(
        request,
        "Complete your profile and wait for staff verification to use messages.",
    )
    return redirect("account")

# WHY: Keeps the render direct conversation steps in one named place so they can be understood, checked, and reused.
def _render_direct_conversation(request, page_data, form):
    """Render selector-authorised messages with the pair's other public profile."""
    # WHY: Derives the other person from the authorised pair rather than accepting a browser identity.
    conversation = page_data["conversation"]
    other_user = (
        conversation.second_user
        if conversation.first_user_id == request.user.pk
        else conversation.first_user
    )
    # WHY: Keeps authorised messages, the other public profile, and the bound send form together.
    return render(
        request,
        "conversation.html",
        {
            "conversation": conversation,
            "conversation_messages": page_data["messages"],
            "other_profile": other_user.profile,
            "form": form,
        },
    )

# =============================================================================
# MESSAGE INBOX
# Builds the permitted conversation list and interest filter.
# =============================================================================

# WHY: Keeps the inbox page steps in one named place so they can be understood, checked, and reused.
@require_GET
@login_required
def inbox_page(request):
    """Render only the current account's permitted direct conversations.

    Inputs: a signed-in GET request with no browser-supplied member identity.
    Returns: the recent permitted inbox or the generic account access redirect.
    Changes: none.
    Refuses: inactive, unverified or missing-profile accounts.
    Privacy: blocked pairs are excluded before names or message text presentation.
    """
    access_redirect = _message_access_redirect(request)
    if access_redirect is not None:
        return access_redirect

    # WHY: Keeps the small inbox interest shortcuts fixed rather than accepting arbitrary query text.
    interest_names = ("Coffee", "Museums", "Cinema", "Walking", "Drinks", "Night out")
    selected_interest = request.GET.get("interest", "")
    # WHY: Unknown filter values become no filter and never reach the database query.
    if selected_interest not in interest_names:
        selected_interest = ""

    # WHY: Adds only the other member's authorised profile to each already filtered conversation.
    conversation_rows = []
    for conversation in get_unblocked_conversations_for_inbox(
        request.user,
        selected_interest,
    ):
        other_user = (
            conversation.second_user
            if conversation.first_user_id == request.user.pk
            else conversation.first_user
        )
        conversation_rows.append(
            {"conversation": conversation, "other_profile": other_user.profile}
        )
    return render(
        request,
        "inbox.html",
        {
            "conversation_rows": conversation_rows,
            "interest_filters": (
                (name, name == selected_interest) for name in interest_names
            ),
            "selected_interest": selected_interest,
        },
    )

# =============================================================================
# CONVERSATION PAGE
# Loads one permitted conversation and its messages.
# =============================================================================

# WHY: Keeps the conversation page steps in one named place so they can be understood, checked, and reused.
@require_GET
@login_required
def conversation_page(request, conversation_id):
    """Render one authorised conversation with every message escaped as text.

    Inputs: a signed-in GET request and an untrusted conversation route ID.
    Returns: chronological messages or one generic unavailable response.
    Changes: none.
    Refuses: missing, unrelated, inactive, unverified or blocked conversations.
    Privacy: reveals no pair identity or message content after any refusal.
    """
    access_redirect = _message_access_redirect(request)
    if access_redirect is not None:
        return access_redirect
    # WHY: Uses one selector that checks membership, both accounts, and blocks before returning message text.
    page_data = get_messages_if_user_can_open_conversation(
        request.user,
        conversation_id,
    )
    if page_data is None:
        return HttpResponse("Conversation unavailable.", status=404)
    return _render_direct_conversation(request, page_data, MessageDraftForm())

# =============================================================================
# START A CONVERSATION
# Finds or creates the one private conversation between two people.
# =============================================================================

# WHY: Keeps the start direct conversation steps in one named place so they can be understood, checked, and reused.
@require_POST
@login_required
def start_direct_conversation(request, profile_id):
    """Start or return to the one permitted direct conversation for a pair.

    Inputs: a signed-in CSRF-validated POST and untrusted profile route ID.
    Returns: a redirect to the pair's single conversation or generic not found.
    Changes: calls the mapped service, which may create the ordered unique pair.
    Refuses: missing, self, inactive, unverified or either-direction-blocked pairs.
    Privacy: trusts no recipient identity beyond the authorised profile selector.
    """
    access_redirect = _message_access_redirect(request)
    if access_redirect is not None:
        return access_redirect
    # WHY: Selects the recipient through current public-profile permission instead of trusting a submitted user ID.
    profile = get_profile_page_if_viewer_is_allowed(request.user, profile_id)
    if profile is None:
        return HttpResponse("Profile unavailable.", status=404)
    # WHY: Returns the pair's one existing conversation or creates it under the same current messaging rules.
    try:
        conversation = find_or_start_direct_conversation(
            request.user,
            profile.user,
        )
    except PermissionDenied:
        return HttpResponse("Profile unavailable.", status=404)
    return redirect("conversation_detail", conversation_id=conversation.pk)

# =============================================================================
# SEND A MESSAGE
# Validates and sends the current unsent draft.
# =============================================================================

# WHY: Sends conversation message only after the required account and content checks pass.
@require_POST
@login_required
def send_conversation_message(request, conversation_id):
    """Validate and send one bounded plain-text direct message through POST.

    Inputs: a signed-in CSRF-validated POST, route ID and untrusted draft values.
    Returns: a detail redirect, bound form or one generic unavailable response.
    Changes: calls the atomic message service only after form validation.
    Refuses: invalid drafts and missing, unrelated, ineligible or blocked pairs.
    Privacy: sender comes only from the session; message text is never logged.
    """
    access_redirect = _message_access_redirect(request)
    if access_redirect is not None:
        return access_redirect
    # WHY: Rechecks conversation access before reading the draft or attempting a write.
    page_data = get_messages_if_user_can_open_conversation(
        request.user,
        conversation_id,
    )
    if page_data is None:
        return HttpResponse("Conversation unavailable.", status=404)

    # WHY: Applies plain-text, non-empty, and size rules before the message service runs.
    form = MessageDraftForm(request.POST)
    if not form.is_valid():
        return _render_direct_conversation(request, page_data, form)
    # WHY: The service locks and rechecks membership and blocks because they may change between read and send.
    try:
        send_direct_message(
            request.user,
            page_data["conversation"],
            form.cleaned_data["body"],
        )
    except PermissionDenied:
        return HttpResponse("Conversation unavailable.", status=404)
    # WHY: Redirects after success so refreshing the conversation does not send the same message again.
    messages.success(request, "Message sent.")
    return redirect("conversation_detail", conversation_id=conversation_id)

# =============================================================================
# IMPROVE AN UNSENT DRAFT
# Requests a wording suggestion without sending or storing the draft.
# =============================================================================

# WHY: Keeps the request conversation message edit suggestion steps in one named place so they can be understood, checked, and reused.
@require_POST
@login_required
def request_conversation_message_edit_suggestion(request, conversation_id):
    """Return one bounded Ollama suggestion for an authorised unsent draft.

    Inputs: a signed-in CSRF-validated POST, route ID, draft and fixed goal.
    Returns: suggestion JSON, a generic unavailable response or quiet error JSON.
    Changes: calls the mapped Ollama editor; stores and sends no message or draft.
    Refuses: invalid, unrelated, inactive, unverified or blocked conversations,
        invalid draft/goal values and every provider failure.
    Privacy: passes only validated draft and goal, never conversation history or
        account, profile, report, plan or recipient data.
    """
    access_redirect = _message_access_redirect(request)
    if access_redirect is not None:
        return access_redirect
    # WHY: Requires permission to this conversation even though no history or recipient details go outside.
    page_data = get_messages_if_user_can_open_conversation(
        request.user,
        conversation_id,
    )
    if page_data is None:
        return HttpResponse("Conversation unavailable.", status=404)

    # WHY: Accepts only one bounded draft and one of the two fixed wording goals.
    form = MessageEditRequestForm(request.POST)
    if not form.is_valid():
        return JsonResponse({"error": "Draft edit unavailable."}, status=400)
    # WHY: Passes only the cleaned draft and goal to the separate editor, never conversation page data.
    suggestion = get_edited_message_draft_suggestion(
        form.cleaned_data["draft"],
        form.cleaned_data["editing_goal"],
    )
    if suggestion is None:
        return JsonResponse({"error": "Draft edit unavailable."}, status=503)
    return JsonResponse({"suggestion": suggestion})
