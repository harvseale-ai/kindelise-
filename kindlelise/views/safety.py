"""Private blocking and reporting pages."""

# WHY: This module keeps protective actions separate from ordinary profile and message pages.
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods, require_POST

from kindlelise.forms import PrivateReportForm
from kindlelise.selectors import (
    get_messages_if_user_can_open_conversation,
    get_plan_page_if_viewer_is_allowed,
    get_profile_page_if_viewer_is_allowed,
    get_report_target_profile_if_reporter_is_allowed,
)
from kindlelise.services.safety import (
    block_user_from_discovery_and_messages,
    submit_private_report_about_user,
)

# =============================================================================
# REPORT CONTEXT
# Checks optional plan, conversation, or message evidence for a private report.
# =============================================================================

# WHY: Keeps the get private report context steps in one named place so they can be understood, checked, and reused.
def _get_private_report_context(request, target_profile):
    """Resolve optional untrusted report context through reporter-scoped selectors."""
    # WHY: Preserves context from the opening link on GET and requires it again with the submitted POST.
    submitted_values = request.POST if request.method == "POST" else request.GET
    context_type = submitted_values.get("context_type", "").strip()
    context_id = submitted_values.get("context_id", "").strip()
    conversation_id = submitted_values.get("context_conversation_id", "").strip()
    # WHY: Allows a valid profile-only report when no optional context was supplied.
    if not context_type and not context_id and not conversation_id:
        return {"service_values": {}, "hidden_values": {}, "label": None}
    # WHY: Refuses unknown context kinds and invalid IDs before any selector is called.
    if context_type not in {"plan", "conversation", "message"}:
        return None
    if not context_id.isdecimal() or int(context_id) < 1:
        return None

    # WHY: Resolves plan context only through the reporter's current authorised plan selector.
    if context_type == "plan":
        plan_page = get_plan_page_if_viewer_is_allowed(
            request.user,
            int(context_id),
        )
        if plan_page is None:
            return None
        return {
            "service_values": {"reported_plan": plan_page["plan"]},
            "hidden_values": {
                "context_type": context_type,
                "context_id": context_id,
            },
            "label": f"Plan: {plan_page['plan'].title}",
        }

    # WHY: Conversation reports use their own ID; message reports carry the containing conversation separately.
    selected_conversation_id = context_id
    if context_type == "message":
        if not conversation_id.isdecimal() or int(conversation_id) < 1:
            return None
        selected_conversation_id = conversation_id
    # WHY: Loads context only when the reporter may open the exact conversation and its messages.
    conversation_page_data = get_messages_if_user_can_open_conversation(
        request.user,
        int(selected_conversation_id),
    )
    if conversation_page_data is None:
        return None
    conversation = conversation_page_data["conversation"]
    # WHY: Requires the pair to be exactly reporter and target, not merely any conversation the reporter can open.
    if {
        conversation.first_user_id,
        conversation.second_user_id,
    } != {request.user.pk, target_profile.user_id}:
        return None

    if context_type == "conversation":
        return {
            "service_values": {"reported_conversation": conversation},
            "hidden_values": {
                "context_type": context_type,
                "context_id": context_id,
            },
            "label": "This direct conversation",
        }

    # WHY: A message report may target only a message received from this profile, never the reporter's own message.
    reported_message = next(
        (
            conversation_message
            for conversation_message in conversation_page_data["messages"]
            if conversation_message.pk == int(context_id)
            and conversation_message.sender_id == target_profile.user_id
        ),
        None,
    )
    if reported_message is None:
        return None
    return {
        "service_values": {"reported_message": reported_message},
        "hidden_values": {
            "context_type": context_type,
            "context_id": context_id,
            "context_conversation_id": conversation_id,
        },
        "label": "A received message in this conversation",
    }

# =============================================================================
# BLOCK A PROFILE
# Closes discovery and messaging contact with one profile.
# =============================================================================

# WHY: Keeps the block profile from discovery and messages steps in one named place so they can be understood, checked, and reused.
@require_POST
@login_required
def block_profile_from_discovery_and_messages(request, profile_id):
    """Call the mapped block service through POST and leave the interaction page.

    Inputs: a signed-in CSRF-validated POST and untrusted profile route ID.
    Returns: a discovery redirect or the same generic profile-not-found response.
    Changes: calls the idempotent directional block service once.
    Refuses: missing, self, inactive, unverified or already-hidden profiles.
    Privacy: never notifies the blocked account or reveals block state to it.
    """
    # WHY: Requires current interaction visibility before accepting a directional block action from this page.
    profile = get_profile_page_if_viewer_is_allowed(request.user, profile_id)
    if profile is None:
        return HttpResponse("Profile unavailable.", status=404)
    try:
        block_user_from_discovery_and_messages(request.user, profile.user)
    except PermissionDenied:
        return HttpResponse("Profile unavailable.", status=404)
    # WHY: Confirms the private local effect without notifying the blocked account.
    messages.success(request, "Interaction closed. You can still submit a private report.")
    return redirect("discover")

# =============================================================================
# PRIVATE REPORT PAGE
# Displays and submits a private report about another account.
# =============================================================================

# WHY: Keeps the report user page steps in one named place so they can be understood, checked, and reused.
@require_http_methods(["GET", "POST"])
@login_required
def report_user_page(request, profile_id):
    """Show and submit a private report form with PrivateReportForm.

    Inputs: an authenticated request, untrusted target ID, form and context values.
    Returns: the bound form, private confirmation or generic unavailable response.
    Changes: creates one received report only after form and context validation.
    Refuses: missing/self targets, invalid context and service relationship changes.
    Privacy: survives blocks, exposes no report directory and never notifies target.
    """
    # WHY: Uses the report-specific selector so reporting remains possible even after a block.
    target_profile = get_report_target_profile_if_reporter_is_allowed(
        request.user,
        profile_id,
    )
    if target_profile is None:
        return HttpResponse("Report unavailable.", status=404)
    # WHY: Resolves optional context through authorised server data before displaying or submitting the form.
    report_context = _get_private_report_context(request, target_profile)
    if report_context is None:
        return HttpResponse("Report unavailable.", status=404)

    # WHY: Lets the visitor provide only category and description; identities and context remain server-owned.
    form = PrivateReportForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        # WHY: The service rechecks every relationship before storing one private Received report.
        try:
            submit_private_report_about_user(
                request.user,
                target_profile.user,
                form.cleaned_data,
                **report_context["service_values"],
            )
        except PermissionDenied:
            return HttpResponse("Report unavailable.", status=404)
        # WHY: Shows confirmation without placing the report contents or target details back on the page.
        return render(
            request,
            "report.html",
            {"mode": "confirmation"},
        )

    return render(
        request,
        "report.html",
        {
            "mode": "form",
            "form": form,
            "target_profile": target_profile,
            "context_label": report_context["label"],
            "hidden_values": report_context["hidden_values"],
        },
    )
