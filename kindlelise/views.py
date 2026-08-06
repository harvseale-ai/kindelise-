"""Translate Kindlelise browser requests into the mapped application owners."""

import stripe
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError
from django.http import FileResponse, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from kindlelise.forms import (
    AccountSignUpForm,
    DiscoveryFiltersForm,
    MessageDraftForm,
    MessageEditRequestForm,
    PlanDetailsForm,
    PlanMetadataRequestForm,
    PrivateReportForm,
    ProfileDetailsForm,
)
from kindlelise.ai_message_editor import get_edited_message_draft_suggestion
from kindlelise.models import Plan
from kindlelise.plan_metadata import (
    fetch_plan_metadata,
    thumbnail_from_metadata_token,
)
from kindlelise.policies import (
    can_access_discovery_plans_and_messages,
    can_join_approved_plan,
    get_allowed_discovery_areas_and_interest_limit,
)
from kindlelise.selectors import (
    get_plan_page_if_viewer_is_allowed,
    get_plans_for_plan_list,
    get_messages_if_user_can_open_conversation,
    get_profile_image_if_viewer_is_allowed,
    get_profile_page_if_viewer_is_allowed,
    get_profiles_for_discovery_grid,
    get_report_target_profile_if_reporter_is_allowed,
    get_signed_in_user_account_summary,
    get_unblocked_conversations_for_inbox,
)
from kindlelise.services import (
    cancel_owned_plan_and_hide_it_from_discovery,
    block_user_from_discovery_and_messages,
    create_account_and_profile,
    create_plan_waiting_for_staff_review,
    find_or_start_direct_conversation,
    join_approved_plan_and_lock_meeting_details,
    leave_plan_and_keep_participation_history,
    open_stripe_customer_portal,
    send_direct_message,
    start_stripe_subscription_checkout,
    submit_private_report_about_user,
    update_premium_access_from_verified_stripe_event,
    update_owned_plan_before_first_join,
    update_signed_in_user_profile,
)


def _safe_local_redirect(request):
    """Return a same-site next destination, or no destination when unsafe."""
    destination = request.POST.get("next") or request.GET.get("next")
    if destination and url_has_allowed_host_and_scheme(
        destination,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return destination
    return None


def _profile_broad_area_label(profile):
    """Return configured labels for one profile's selected broad areas."""
    area_keys = profile.broad_areas or (profile.broad_area,)
    return ", ".join(
        settings.KINDLELISE_AREAS[area_key]
        for area_key in area_keys
        if area_key in settings.KINDLELISE_AREAS
    ) or "Not completed"


@require_http_methods(["GET"])
def home_page(request):
    """Redirect the visitor to the page allowed by current account state.

    Inputs: the current Django request and its server-authenticated account.
    Returns: a redirect to sign-in, the private account or discovery.
    Changes: none.
    Refuses: missing authentication or verification by choosing the safer page.
    Privacy: returns no profile or account details.
    """
    if not request.user.is_authenticated:
        return redirect("sign_in")
    if can_access_discovery_plans_and_messages(request.user):
        return redirect("discover")
    return redirect("account")


@require_http_methods(["GET", "POST"])
def sign_up_page(request):
    """Create one account/profile pair from a valid registration form.

    Inputs: anonymous GET or POST registration input.
    Returns: the registration page or a redirect to the named sign-in route.
    Changes: calls the atomic account/profile service exactly once when valid.
    Refuses: authenticated callers and invalid or raced duplicate input safely.
    Privacy: never authenticates the new account or exposes password values.
    """
    if request.user.is_authenticated:
        return redirect("home")

    form = AccountSignUpForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        try:
            create_account_and_profile(form.cleaned_data)
        except IntegrityError:
            form.add_error("email", "An account already uses this email address.")
        else:
            messages.success(request, "Account created. Sign in to continue.")
            return redirect("sign_in")

    return render(request, "account.html", {"mode": "sign_up", "form": form})


@require_http_methods(["GET", "POST"])
def sign_in_page(request):
    """Authenticate one account and follow only a safe local destination.

    Inputs: anonymous GET or POST email/password input and optional next value.
    Returns: the sign-in page or a redirect after Django starts the session.
    Changes: rotates and authenticates the session after valid credentials.
    Refuses: invalid and inactive accounts with the same generic feedback.
    Privacy: never reveals whether an email exists and never logs credentials.
    """
    if request.user.is_authenticated:
        return redirect("home")

    form_data = request.POST.copy() if request.method == "POST" else None
    if form_data is not None:
        form_data["username"] = form_data.get("username", "").strip().lower()
    form = AuthenticationForm(
        request=request,
        data=form_data,
    )
    form.fields["username"].label = "Email"
    form.fields["username"].widget.input_type = "email"
    form.fields["username"].widget.attrs.update(
        {
            "autocomplete": "email",
            "autocapitalize": "none",
            "spellcheck": "false",
        }
    )
    generic_error = "The email address or password was not accepted."
    form.error_messages["invalid_login"] = generic_error
    form.error_messages["inactive"] = generic_error
    destination = _safe_local_redirect(request)

    if request.method == "POST" and form.is_valid():
        login(request, form.get_user())
        return redirect(destination or reverse("home"))

    return render(
        request,
        "account.html",
        {"mode": "sign_in", "form": form, "next": destination or ""},
    )


@require_POST
@login_required
def sign_out_user(request):
    """End the signed-in account's Django session through POST only.

    Inputs: a signed-in, CSRF-validated POST request.
    Returns: a redirect to the named sign-in route.
    Changes: flushes the current Django session.
    Refuses: anonymous, non-POST or invalid-CSRF requests through Django controls.
    Privacy: returns no session identifier.
    """
    logout(request)
    messages.success(request, "You have signed out.")
    return redirect("sign_in")


@require_http_methods(["GET"])
@login_required
def account_page(request):
    """Show only the signed-in account's private profile summary.

    Inputs: the server-authenticated account; no account identifier is accepted.
    Returns: the private account page or a generic unavailable response.
    Changes: none.
    Refuses: anonymous callers through Django and missing/inactive profiles safely.
    Privacy: uses the authorised selector and exposes no reports or provider IDs.
    """
    summary = get_signed_in_user_account_summary(request.user)
    if summary is None:
        return HttpResponse("Account unavailable.", status=403)

    return render(
        request,
        "account.html",
        {
            "mode": "account",
            "summary": summary,
            "broad_area_label": _profile_broad_area_label(summary["profile"]),
            "is_available_now": summary["profile"].is_available_now(timezone.now()),
        },
    )


@require_http_methods(["GET", "POST"])
@login_required
def edit_profile_page(request):
    """Validate and save only the signed-in account's editable profile fields.

    Inputs: the server-authenticated account and untrusted profile form values.
    Returns: the bound edit page or a redirect to the private account page.
    Changes: calls the mapped profile service after successful validation.
    Refuses: missing/inactive profiles and invalid input without partial changes.
    Privacy: never binds ownership, verification or subscription fields.
    """
    summary = get_signed_in_user_account_summary(request.user)
    if summary is None:
        return HttpResponse("Profile unavailable.", status=403)

    profile = summary["profile"]
    form = ProfileDetailsForm(
        request.POST if request.method == "POST" else None,
        request.FILES if request.method == "POST" else None,
        instance=profile,
    )
    if request.method == "POST" and form.is_valid():
        try:
            update_signed_in_user_profile(request.user, form.cleaned_data)
        except PermissionDenied:
            form.add_error(None, "Your profile could not be updated.")
        else:
            messages.success(request, "Profile updated.")
            return redirect("account")

    return render(
        request,
        "account.html",
        {"mode": "profile_edit", "form": form, "profile": profile},
    )


@require_GET
@login_required
def profile_image_file(request, profile_id):
    """Stream one profile image only after current profile authorisation.

    Inputs: a signed-in GET request and an untrusted profile route identifier.
    Returns: the stored image or one generic not-found response.
    Changes: none.
    Refuses: missing files and anonymous, inactive or disallowed viewers.
    Privacy: exposes neither the storage path nor the reason for refusal.
    """
    profile = get_profile_image_if_viewer_is_allowed(request.user, profile_id)
    if profile is None:
        return HttpResponse("Profile image unavailable.", status=404)
    content_types = {
        ".jpg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }
    suffix = profile.profile_image.name.rsplit(".", 1)[-1].lower()
    content_type = content_types.get(f".{suffix}")
    if content_type is None:
        return HttpResponse("Profile image unavailable.", status=404)
    try:
        image_file = profile.profile_image.open("rb")
    except (FileNotFoundError, OSError):
        return HttpResponse("Profile image unavailable.", status=404)
    return FileResponse(
        image_file,
        content_type=content_type,
        filename=f"profile-image.{suffix}",
    )


@require_GET
@login_required
def discovery_page(request):
    """Render only profiles returned by validated broad-area discovery.

    Inputs: a signed-in GET request with untrusted area/interest/availability filters.
    Returns: the discovery grid or a redirect to the private account page.
    Changes: none.
    Refuses: inactive, unverified or invalid-area accounts and invalid filters.
    Privacy: exposes no hidden counts, exclusion reasons, coordinates or distance.
    """
    if not can_access_discovery_plans_and_messages(request.user):
        messages.info(
            request,
            "Complete your profile and wait for staff verification to use discovery.",
        )
        return redirect("account")

    allowed_areas, interest_limit = get_allowed_discovery_areas_and_interest_limit(
        request.user
    )
    if not allowed_areas:
        messages.info(
            request,
            "Complete your profile and wait for staff verification to use discovery.",
        )
        return redirect("account")

    form_data = request.GET if request.GET else {"broad_area": list(allowed_areas)}
    form = DiscoveryFiltersForm(
        form_data,
        allowed_areas=allowed_areas,
        interest_limit=interest_limit,
    )
    profile_cards = []
    if form.is_valid():
        current_time = timezone.now()
        profiles = get_profiles_for_discovery_grid(
            request.user,
            form.cleaned_data,
        )
        profile_cards = [
            {
                "profile": profile,
                "broad_area_label": _profile_broad_area_label(profile),
                "is_available_now": profile.is_available_now(current_time),
            }
            for profile in profiles
        ]

    return render(
        request,
        "discover.html",
        {
            "form": form,
            "profile_cards": profile_cards,
            "interest_limit": interest_limit,
            "is_premium": interest_limit == 5,
        },
    )


@require_GET
@login_required
def profile_page(request, profile_id):
    """Render one public profile only when the current viewer is allowed.

    Inputs: a signed-in GET request and an untrusted profile route identifier.
    Returns: the safe public-profile mode or one generic not-found response.
    Changes: none.
    Refuses: ineligible viewers and missing, inactive, unverified or blocked targets.
    Privacy: reveals no target existence, block direction or private account state.
    """
    if not can_access_discovery_plans_and_messages(request.user):
        messages.info(
            request,
            "Complete your profile and wait for staff verification to use discovery.",
        )
        return redirect("account")

    profile = get_profile_page_if_viewer_is_allowed(request.user, profile_id)
    if profile is None:
        return HttpResponse("Profile unavailable.", status=404)

    return render(
        request,
        "account.html",
        {
            "mode": "public_profile",
            "profile": profile,
            "broad_area_label": _profile_broad_area_label(profile),
            "is_available_now": profile.is_available_now(timezone.now()),
            "plans": Plan.objects.filter(
                owner=profile.user,
                status=Plan.Status.APPROVED,
                starts_at__gt=timezone.now(),
            ).order_by("-created_at"),
        },
    )


def _plan_access_redirect(request):
    """Return the private-account redirect when current plan access is absent."""
    if can_access_discovery_plans_and_messages(request.user):
        return None
    messages.info(
        request,
        "Complete your profile and wait for staff verification to use plans.",
    )
    return redirect("account")


@require_GET
@login_required
def plan_list_page(request):
    """Render approved future plans and the current owner's private plan states.

    Inputs: a signed-in GET request with no browser-supplied ownership value.
    Returns: the authorised plan list or a redirect to the private account page.
    Changes: none.
    Refuses: inactive, unverified or missing-profile accounts.
    Privacy: excludes other owners' pending, rejected and cancelled plans.
    """
    access_redirect = _plan_access_redirect(request)
    if access_redirect is not None:
        return access_redirect
    selected_filter = request.GET.get("filter", "all")
    plans = get_plans_for_plan_list(request.user)
    if selected_filter == "available":
        plans = plans.filter(status=Plan.Status.APPROVED)
    elif selected_filter == "mine":
        plans = plans.filter(owner=request.user)
    elif selected_filter in {
        Plan.Status.PENDING,
        Plan.Status.REJECTED,
        Plan.Status.CANCELLED,
    }:
        plans = plans.filter(status=selected_filter)
    else:
        selected_filter = "all"

    return render(
        request,
        "plan.html",
        {
            "mode": "list",
            "plans": plans,
            "selected_filter": selected_filter,
        },
    )


@require_POST
@login_required
def request_plan_metadata(request):
    """Return bounded public-place suggestions after one explicit user action.

    Inputs: a signed-in CSRF-validated POST containing one untrusted HTTPS URL.
    Returns: editable place and thumbnail suggestions or one quiet JSON error.
    Changes: performs bounded public HTTPS reads but stores no plan or image.
    Refuses: ineligible accounts, invalid URLs and every unsafe/failing target.
    Privacy: sends no account or profile data to the target public website.
    """
    access_redirect = _plan_access_redirect(request)
    if access_redirect is not None:
        return access_redirect
    form = PlanMetadataRequestForm(request.POST)
    if not form.is_valid():
        return JsonResponse({"error": "Enter a normal HTTPS public-place URL."}, status=400)
    metadata = fetch_plan_metadata(form.cleaned_data["public_url"], request.user.pk)
    if metadata is None:
        return JsonResponse({"error": "Details could not be fetched from that page."}, status=422)
    return JsonResponse(metadata)


@require_http_methods(["GET", "POST"])
@login_required
def create_plan_page(request):
    """Validate and create one pending public-place plan for staff review.

    Inputs: a signed-in GET or POST with untrusted bounded plan fields.
    Returns: the bound creation form or a redirect to the new plan detail.
    Changes: calls the mapped atomic creation service once after validation.
    Refuses: ineligible accounts and invalid form values without a plan write.
    Privacy: never accepts owner, approval, status or lock authority from input.
    """
    access_redirect = _plan_access_redirect(request)
    if access_redirect is not None:
        return access_redirect

    form = PlanDetailsForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        plan_details = dict(form.cleaned_data)
        metadata_token = request.POST.get("fetched_metadata", "")
        if metadata_token:
            thumbnail_image = thumbnail_from_metadata_token(
                metadata_token,
                request.user.pk,
                form.cleaned_data["public_url"],
            )
            if thumbnail_image is None:
                form.add_error("public_url", "Fetch details again before creating the plan.")
            else:
                plan_details["thumbnail_image"] = thumbnail_image
        try:
            plan = (
                None
                if form.errors
                else create_plan_waiting_for_staff_review(request.user, plan_details)
            )
        except PermissionDenied:
            form.add_error(None, "The plan could not be submitted.")
        if plan is not None:
            messages.success(request, "Plan submitted for staff review.")
            return redirect("plan_detail", plan_id=plan.pk)

    return render(
        request,
        "plan.html",
        {"mode": "create", "form": form},
    )


@require_GET
@login_required
def plan_thumbnail_file(request, plan_id):
    """Stream one stored plan thumbnail only when the plan itself is visible."""
    summary = get_plan_page_if_viewer_is_allowed(request.user, plan_id)
    if summary is None or not summary["plan"].thumbnail_image:
        return HttpResponse("Plan image unavailable.", status=404)
    try:
        image_file = summary["plan"].thumbnail_image.open("rb")
    except (FileNotFoundError, OSError):
        return HttpResponse("Plan image unavailable.", status=404)
    return FileResponse(
        image_file,
        content_type="image/jpeg",
        filename="plan-thumbnail.jpg",
    )


@require_GET
@login_required
def plan_detail_page(request, plan_id):
    """Render one visible plan with count and viewer-owned participation state.

    Inputs: a signed-in GET request and an untrusted plan route identifier.
    Returns: the authorised detail page or one generic not-found response.
    Changes: none.
    Refuses: ineligible viewers and missing or ownership-hidden plans.
    Privacy: exposes joined count and own state, never participant identities.
    """
    access_redirect = _plan_access_redirect(request)
    if access_redirect is not None:
        return access_redirect

    summary = get_plan_page_if_viewer_is_allowed(request.user, plan_id)
    if summary is None:
        return HttpResponse("Plan unavailable.", status=404)

    plan = summary["plan"]
    current_time = timezone.now()
    is_owner = plan.owner_id == request.user.pk
    can_edit = (
        is_owner
        and plan.meeting_details_locked_at is None
        and plan.status != plan.Status.CANCELLED
    )
    return render(
        request,
        "plan.html",
        {
            "mode": "detail",
            "summary": summary,
            "is_owner": is_owner,
            "is_past": plan.starts_at <= current_time,
            "can_edit": can_edit,
            "can_cancel": is_owner and plan.status != plan.Status.CANCELLED,
            "can_join": can_join_approved_plan(request.user, plan, current_time),
        },
    )


@require_http_methods(["GET", "POST"])
@login_required
def edit_plan_page(request, plan_id):
    """Validate and update an owned plan only before its first successful join.

    Inputs: a signed-in owner request, untrusted plan ID and bounded plan fields.
    Returns: the bound edit form, success redirect or generic not-found response.
    Changes: calls the mapped locked update service after form validation.
    Refuses: non-owners, hidden, locked, cancelled or newly ineligible requests.
    Privacy: never binds ownership, approval, status or first-join lock fields.
    """
    access_redirect = _plan_access_redirect(request)
    if access_redirect is not None:
        return access_redirect

    summary = get_plan_page_if_viewer_is_allowed(request.user, plan_id)
    if summary is None:
        return HttpResponse("Plan unavailable.", status=404)
    plan = summary["plan"]
    if (
        plan.owner_id != request.user.pk
        or plan.meeting_details_locked_at is not None
        or plan.status == plan.Status.CANCELLED
    ):
        return HttpResponse("Plan unavailable.", status=404)

    form = PlanDetailsForm(
        request.POST if request.method == "POST" else None,
        instance=plan,
    )
    if request.method == "POST" and form.is_valid():
        plan_changes = dict(form.cleaned_data)
        metadata_token = request.POST.get("fetched_metadata", "")
        if metadata_token:
            thumbnail_image = thumbnail_from_metadata_token(
                metadata_token,
                request.user.pk,
                form.cleaned_data["public_url"],
            )
            if thumbnail_image is None:
                form.add_error("public_url", "Fetch details again before saving the plan.")
            else:
                plan_changes["thumbnail_image"] = thumbnail_image
        try:
            updated_plan = (
                None
                if form.errors
                else update_owned_plan_before_first_join(
                    request.user,
                    plan,
                    plan_changes,
                )
            )
        except PermissionDenied:
            form.add_error(None, "This plan can no longer be edited.")
        if updated_plan is not None:
            messages.success(request, "Plan updated.")
            return redirect("plan_detail", plan_id=updated_plan.pk)

    return render(
        request,
        "plan.html",
        {"mode": "edit", "form": form, "plan": plan},
    )


@require_POST
@login_required
def join_plan(request, plan_id):
    """Join an approved plan and lock its details through the mapped service.

    Inputs: a signed-in CSRF-validated POST and untrusted plan route identifier.
    Returns: a detail redirect, generic refusal redirect or generic not found.
    Changes: creates/reactivates participation and sets the first-join lock.
    Refuses: hidden, owner, closed, full, past or already-joined conditions.
    Privacy: accepts no participant identity and returns no participant directory.
    """
    access_redirect = _plan_access_redirect(request)
    if access_redirect is not None:
        return access_redirect
    summary = get_plan_page_if_viewer_is_allowed(request.user, plan_id)
    if summary is None:
        return HttpResponse("Plan unavailable.", status=404)
    try:
        join_approved_plan_and_lock_meeting_details(request.user, summary["plan"])
    except PermissionDenied:
        messages.error(request, "The plan could not be joined.")
        return redirect("plan_list")
    messages.success(request, "You joined the plan.")
    return redirect("plan_detail", plan_id=plan_id)


@require_POST
@login_required
def leave_plan(request, plan_id):
    """Leave one plan while preserving the caller's participation history.

    Inputs: a signed-in CSRF-validated POST and untrusted plan route identifier.
    Returns: a detail redirect, generic refusal redirect or generic not found.
    Changes: marks only the caller's current participation left with a time.
    Refuses: hidden plans, ineligible users and non-current participation.
    Privacy: accepts no participant identity and reveals no other participant.
    """
    access_redirect = _plan_access_redirect(request)
    if access_redirect is not None:
        return access_redirect
    summary = get_plan_page_if_viewer_is_allowed(request.user, plan_id)
    if summary is None:
        return HttpResponse("Plan unavailable.", status=404)
    try:
        leave_plan_and_keep_participation_history(request.user, summary["plan"])
    except PermissionDenied:
        messages.error(request, "The plan could not be left.")
        return redirect("plan_list")
    messages.success(request, "You left the plan.")
    return redirect("plan_detail", plan_id=plan_id)


@require_POST
@login_required
def cancel_plan(request, plan_id):
    """Cancel one owned plan terminally while preserving participation history.

    Inputs: a signed-in CSRF-validated owner POST and untrusted plan identifier.
    Returns: a detail redirect, generic refusal redirect or generic not found.
    Changes: calls the mapped cancellation service and clears current approval.
    Refuses: hidden, non-owned, ineligible or already-cancelled requests.
    Privacy: accepts no owner identity and reveals no participant information.
    """
    access_redirect = _plan_access_redirect(request)
    if access_redirect is not None:
        return access_redirect
    summary = get_plan_page_if_viewer_is_allowed(request.user, plan_id)
    if summary is None:
        return HttpResponse("Plan unavailable.", status=404)
    try:
        cancel_owned_plan_and_hide_it_from_discovery(
            request.user,
            summary["plan"],
        )
    except PermissionDenied:
        messages.error(request, "The plan could not be cancelled.")
        return redirect("plan_list")
    messages.success(request, "Plan cancelled.")
    return redirect("plan_detail", plan_id=plan_id)


def _message_access_redirect(request):
    """Return the private-account redirect when current messaging access is absent."""
    if can_access_discovery_plans_and_messages(request.user):
        return None
    messages.info(
        request,
        "Complete your profile and wait for staff verification to use messages.",
    )
    return redirect("account")


def _render_direct_conversation(request, page_data, form):
    """Render selector-authorised messages with the pair's other public profile."""
    conversation = page_data["conversation"]
    other_user = (
        conversation.second_user
        if conversation.first_user_id == request.user.pk
        else conversation.first_user
    )
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

    conversation_rows = []
    for conversation in get_unblocked_conversations_for_inbox(request.user):
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
        {"conversation_rows": conversation_rows},
    )


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
    page_data = get_messages_if_user_can_open_conversation(
        request.user,
        conversation_id,
    )
    if page_data is None:
        return HttpResponse("Conversation unavailable.", status=404)
    return _render_direct_conversation(request, page_data, MessageDraftForm())


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
    profile = get_profile_page_if_viewer_is_allowed(request.user, profile_id)
    if profile is None:
        return HttpResponse("Profile unavailable.", status=404)
    try:
        conversation = find_or_start_direct_conversation(
            request.user,
            profile.user,
        )
    except PermissionDenied:
        return HttpResponse("Profile unavailable.", status=404)
    return redirect("conversation_detail", conversation_id=conversation.pk)


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
    page_data = get_messages_if_user_can_open_conversation(
        request.user,
        conversation_id,
    )
    if page_data is None:
        return HttpResponse("Conversation unavailable.", status=404)

    form = MessageDraftForm(request.POST)
    if not form.is_valid():
        return _render_direct_conversation(request, page_data, form)
    try:
        send_direct_message(
            request.user,
            page_data["conversation"],
            form.cleaned_data["body"],
        )
    except PermissionDenied:
        return HttpResponse("Conversation unavailable.", status=404)
    messages.success(request, "Message sent.")
    return redirect("conversation_detail", conversation_id=conversation_id)


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
    page_data = get_messages_if_user_can_open_conversation(
        request.user,
        conversation_id,
    )
    if page_data is None:
        return HttpResponse("Conversation unavailable.", status=404)

    form = MessageEditRequestForm(request.POST)
    if not form.is_valid():
        return JsonResponse({"error": "Draft edit unavailable."}, status=400)
    suggestion = get_edited_message_draft_suggestion(
        form.cleaned_data["draft"],
        form.cleaned_data["editing_goal"],
    )
    if suggestion is None:
        return JsonResponse({"error": "Draft edit unavailable."}, status=503)
    return JsonResponse({"suggestion": suggestion})


def _get_private_report_context(request, target_profile):
    """Resolve optional untrusted report context through reporter-scoped selectors."""
    submitted_values = request.POST if request.method == "POST" else request.GET
    context_type = submitted_values.get("context_type", "").strip()
    context_id = submitted_values.get("context_id", "").strip()
    conversation_id = submitted_values.get("context_conversation_id", "").strip()
    if not context_type and not context_id and not conversation_id:
        return {"service_values": {}, "hidden_values": {}, "label": None}
    if context_type not in {"plan", "conversation", "message"}:
        return None
    if not context_id.isdecimal() or int(context_id) < 1:
        return None

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

    selected_conversation_id = context_id
    if context_type == "message":
        if not conversation_id.isdecimal() or int(conversation_id) < 1:
            return None
        selected_conversation_id = conversation_id
    conversation_page_data = get_messages_if_user_can_open_conversation(
        request.user,
        int(selected_conversation_id),
    )
    if conversation_page_data is None:
        return None
    conversation = conversation_page_data["conversation"]
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
    profile = get_profile_page_if_viewer_is_allowed(request.user, profile_id)
    if profile is None:
        return HttpResponse("Profile unavailable.", status=404)
    try:
        block_user_from_discovery_and_messages(request.user, profile.user)
    except PermissionDenied:
        return HttpResponse("Profile unavailable.", status=404)
    messages.success(request, "Interaction closed. You can still submit a private report.")
    return redirect("discover")


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
    target_profile = get_report_target_profile_if_reporter_is_allowed(
        request.user,
        profile_id,
    )
    if target_profile is None:
        return HttpResponse("Report unavailable.", status=404)
    report_context = _get_private_report_context(request, target_profile)
    if report_context is None:
        return HttpResponse("Report unavailable.", status=404)

    form = PrivateReportForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        try:
            submit_private_report_about_user(
                request.user,
                target_profile.user,
                form.cleaned_data,
                **report_context["service_values"],
            )
        except PermissionDenied:
            return HttpResponse("Report unavailable.", status=404)
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


@require_POST
@login_required
def start_premium_subscription_checkout(request):
    """Start the account's configured Stripe-hosted Premium subscription.

    Inputs: a signed-in CSRF-validated POST; browser destinations are ignored.
    Returns: a redirect to hosted Checkout or back to the private account page.
    Changes: calls the mapped Stripe Checkout service outside a transaction.
    Refuses: invalid account/configuration, duplicate subscription or provider failure.
    Privacy: sends no browser-selected account, customer or return URL to Stripe.
    """
    account_url = request.build_absolute_uri(reverse("account"))
    try:
        checkout_url = start_stripe_subscription_checkout(
            request.user,
            account_url,
            account_url,
        )
    except (PermissionDenied, stripe.StripeError, ValueError):
        messages.error(request, "Premium Checkout is unavailable. Please try again.")
        return redirect("account")
    return redirect(checkout_url)


@require_POST
@login_required
def open_premium_subscription_portal(request):
    """Open Stripe's hosted portal for the account's linked customer.

    Inputs: a signed-in CSRF-validated POST; the return destination is server-built.
    Returns: a redirect to Stripe's portal or back to the private account page.
    Changes: calls the mapped Stripe portal service outside a transaction.
    Refuses: missing ownership/configuration and every provider or URL failure.
    Privacy: never accepts a customer identifier or return URL from the browser.
    """
    account_url = request.build_absolute_uri(reverse("account"))
    try:
        portal_url = open_stripe_customer_portal(request.user, account_url)
    except (PermissionDenied, stripe.StripeError, ValueError):
        messages.error(request, "Subscription management is unavailable. Please try again.")
        return redirect("account")
    return redirect(portal_url)


@csrf_exempt
@require_POST
def receive_and_verify_stripe_webhook(request):
    """Verify the raw Stripe signature and apply one supported event safely.

    Inputs: the exact raw POST body and Stripe signature header.
    Returns: 400 for invalid input, 200 for safe handling and 500 for retryable failure.
    Changes: calls the atomic receipt/projection service for supported events.
    Refuses: invalid signatures, malformed JSON and unsupported state changes.
    Privacy: never authenticates a browser session or logs/stores the raw payload.
    """
    if not settings.STRIPE_WEBHOOK_SECRET:
        return HttpResponse(status=400)
    try:
        stripe_event = stripe.Webhook.construct_event(
            request.body,
            request.headers.get("Stripe-Signature", ""),
            settings.STRIPE_WEBHOOK_SECRET,
            api_key=settings.STRIPE_SECRET_KEY or None,
        )
    except (ValueError, stripe.SignatureVerificationError):
        return HttpResponse(status=400)

    if stripe_event.get("type") not in {
        "checkout.session.completed",
        "customer.subscription.updated",
        "invoice.paid",
        "customer.subscription.deleted",
    }:
        return HttpResponse(status=200)
    try:
        update_premium_access_from_verified_stripe_event(stripe_event)
    except Exception:
        # A supported event must be retried if its receipt/projection did not
        # commit. Returning a short response avoids exposing provider payloads.
        return HttpResponse(status=500)
    return HttpResponse(status=200)
