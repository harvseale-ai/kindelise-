"""Plan listing, creation, editing, images, and participation pages."""

# WHY: This module keeps the full life of a plan together, from creation to cancellation.
from urllib.parse import quote_plus

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import BooleanField, Case, F, Q, Value, When
from django.http import FileResponse, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from kindlelise.ai_plan_drafter import get_plan_draft_suggestion
from kindlelise.forms import (
    PlanDraftRequestForm,
    PlanImageDetailsForm,
    PlanMetadataRequestForm,
)
from kindlelise.models import Participation, Plan, PlanChat
from kindlelise.plan_metadata import fetch_plan_metadata, thumbnail_from_metadata_token
from kindlelise.policies import (
    can_access_discovery_plans_and_messages,
    can_request_plan_participation,
)
from kindlelise.selectors import (
    get_pending_plan_requests_for_owner,
    get_plan_page_if_viewer_is_allowed,
    get_plans_for_plan_list,
)
from kindlelise.services.plans import (
    cancel_owned_plan_and_hide_it_from_discovery,
    confirm_requested_plan_participation,
    create_available_plan,
    decline_requested_plan_participation,
    leave_plan_and_keep_participation_history,
    request_plan_participation_and_open_owner_conversation,
    update_owned_plan_before_first_join,
    withdraw_pending_plan_participation,
)

# =============================================================================
# SHARED PLAN ACCESS
# Applies the common account gate used by every plan page.
# =============================================================================

# WHY: Keeps the plan access redirect steps in one named place so they can be understood, checked, and reused.
def _plan_access_redirect(request):
    """Return the private-account redirect when current plan access is absent."""
    # WHY: Returns no redirect when normal plan handling may continue.
    if can_access_discovery_plans_and_messages(request.user):
        return None
    # WHY: Sends an ineligible visitor to their own profile with one useful next-step notice.
    messages.info(
        request,
        "Complete your profile to use plans.",
    )
    return redirect("account")

# =============================================================================
# PLAN LIST
# Loads and filters the plan cards shown on the Plans page.
# =============================================================================

# WHY: Gives the full results page and shared topbar suggestions one identical public/open search boundary.
def _filter_open_plans_by_search(plans, search_query):
    """Return open upcoming plans whose public wording contains one bounded phrase."""
    return plans.filter(
        status=Plan.Status.APPROVED,
        starts_at__gt=timezone.now(),
        joined_count__lt=F("capacity"),
    ).filter(
        Q(title__icontains=search_query)
        | Q(description__icontains=search_query)
        | Q(public_place__icontains=search_query)
        | Q(public_address__icontains=search_query)
    )

# WHY: Keeps the plan list page steps in one named place so they can be understood, checked, and reused.
@require_GET
@login_required
def plan_list_page(request):
    """Render approved future plans and the current owner's private plan states.

    Inputs: a signed-in GET request with no browser-supplied ownership value.
    Returns: the authorised plan list or a redirect to the private account page.
    Changes: none.
    Refuses: inactive or missing-profile accounts.
    Privacy: excludes other owners' private states and unrelated completed plans.
    """
    # WHY: Uses the same access response as every plan page before reading filters or plan rows.
    access_redirect = _plan_access_redirect(request)
    if access_redirect is not None:
        return access_redirect
    # WHY: Treats an absent filter as All and validates every other value with explicit branches below.
    selected_filter = request.GET.get("filter", "all")
    # WHY: Bounds one plain search phrase before it reaches the database or is returned to the page.
    search_query = request.GET.get("q", "").strip()[:100]
    # WHY: Loads a separate privacy-safe history only when the visitor explicitly chooses Done.
    if selected_filter == "done":
        plans = get_plans_for_plan_list(request.user, completed=True)
    else:
        plans = get_plans_for_plan_list(request.user)
        current_time = timezone.now()
        # WHY: Narrows the already privacy-safe current plan list without creating separate visibility rules.
        if selected_filter == "available":
            plans = plans.filter(
                status=Plan.Status.APPROVED,
                joined_count__lt=F("capacity"),
            )
        elif selected_filter == "full":
            plans = plans.filter(
                status=Plan.Status.APPROVED,
                joined_count__gte=F("capacity"),
            )
        elif selected_filter == "mine":
            plans = plans.filter(owner=request.user)
        elif selected_filter == "joined":
            plans = plans.filter(
                participations__user=request.user,
                participations__status=Participation.Status.JOINED,
            ).distinct()
        elif selected_filter == "this_week":
            plans = plans.filter(
                starts_at__gte=current_time,
                starts_at__lte=current_time + timezone.timedelta(days=7),
            )
        elif selected_filter == "this_month":
            plans = plans.filter(
                starts_at__gte=current_time,
                starts_at__lte=current_time + timezone.timedelta(days=30),
            )
        elif selected_filter in {
            Plan.Status.PENDING,
            Plan.Status.REJECTED,
            Plan.Status.CANCELLED,
        }:
            plans = plans.filter(status=selected_filter)
        # WHY: Unknown filter words safely fall back to All instead of becoming database input.
        else:
            selected_filter = "all"

    # WHY: Search is intentionally limited to public, upcoming plans with room; private states and full plans never become results.
    if len(search_query) >= 2:
        plans = _filter_open_plans_by_search(plans, search_query)

    return render(
        request,
        "plan.html",
        {
            "mode": "list",
            "plans": plans,
            "selected_filter": selected_filter,
            "search_query": search_query,
        },
    )


# WHY: Supplies the same small authorised dropdown on pages that do not already contain plan cards.
@require_GET
@login_required
def plan_search_suggestions(request):
    """Return at most six open-plan suggestions for the shared topbar search."""
    access_redirect = _plan_access_redirect(request)
    if access_redirect is not None:
        return JsonResponse({"results": []}, status=403)
    search_query = request.GET.get("q", "").strip()[:100]
    if len(search_query) < 2:
        return JsonResponse({"results": []})
    plans = _filter_open_plans_by_search(
        get_plans_for_plan_list(request.user),
        search_query,
    )
    rows = plans.values("pk", "title", "public_place", "starts_at").annotate(
        has_thumbnail=Case(
            When(thumbnail_image__isnull=False, then=Value(True)),
            default=Value(False),
            output_field=BooleanField(),
        )
    )[:6]
    results = []
    for row in rows:
        results.append(
            {
                "url": reverse("plan_detail", args=[row["pk"]]),
                "image_url": (
                    reverse("plan_thumbnail", args=[row["pk"]])
                    if row["has_thumbnail"]
                    else ""
                ),
                "title": row["title"],
                "place": row["public_place"],
                "date": timezone.localtime(row["starts_at"]).strftime("%-d %b · %H:%M"),
            }
        )
    return JsonResponse({"results": results})

# =============================================================================
# PUBLIC PLACE DETAILS
# Fetches optional place text and image suggestions from a submitted public URL.
# =============================================================================

# WHY: Keeps the request plan metadata steps in one named place so they can be understood, checked, and reused.
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
    # WHY: Allows outside fetching only for accounts currently permitted to create plans.
    access_redirect = _plan_access_redirect(request)
    if access_redirect is not None:
        return access_redirect
    # WHY: Validates the one submitted URL before any network request begins.
    form = PlanMetadataRequestForm(request.POST)
    if not form.is_valid():
        return JsonResponse({"error": "Enter a normal HTTPS public-place URL."}, status=400)
    # WHY: Binds any returned image proof to the signed-in account's server-known ID.
    metadata = fetch_plan_metadata(form.cleaned_data["public_url"], request.user.pk)
    if metadata is None:
        return JsonResponse({"error": "Details could not be fetched from that page."}, status=422)
    return JsonResponse(metadata)


# WHY: Keeps optional AI wording behind the same plan access and future-fact validation as plan creation.
@require_POST
@login_required
def request_plan_draft(request):
    """Return one bounded editable title and description suggestion without saving."""
    access_redirect = _plan_access_redirect(request)
    if access_redirect is not None:
        return access_redirect
    form = PlanDraftRequestForm(request.POST)
    if not form.is_valid():
        return JsonResponse({"error": "Complete the labelled plan details first."}, status=400)
    suggestion = get_plan_draft_suggestion(**form.cleaned_data)
    if suggestion is None:
        return JsonResponse(
            {"error": "A draft could not be generated. You can write it manually."},
            status=503,
        )
    return JsonResponse(suggestion)

# =============================================================================
# CREATE PLAN
# Validates and saves a new plan.
# =============================================================================

# WHY: Builds plan page with all required starting values and checks applied.
@require_http_methods(["GET", "POST"])
@login_required
def create_plan_page(request):
    """Validate and create one immediately available public-place plan.

    Inputs: a signed-in GET or POST with untrusted bounded plan fields.
    Returns: the bound creation form or a redirect to the new plan detail.
    Changes: calls the mapped atomic creation service once after validation.
    Refuses: ineligible accounts and invalid form values without a plan write.
    Privacy: never accepts owner, status, approval or lock authority from input.
    """
    # WHY: Uses the shared plan-access response before showing or accepting the form.
    access_redirect = _plan_access_redirect(request)
    if access_redirect is not None:
        return access_redirect

    # WHY: Starts new plans on today's local date while keeping time deliberately unselected.
    form = PlanImageDetailsForm(
        request.POST if request.method == "POST" else None,
        request.FILES if request.method == "POST" else None,
        initial={"starts_at": [timezone.localdate().isoformat(), ""]},
    )
    if request.method == "POST" and form.is_valid():
        # WHY: Starts service input with form-cleaned plan fields and adds only a separately verified thumbnail.
        plan_details = dict(form.cleaned_data)
        uploaded_thumbnail = plan_details.pop("plan_image", None)
        metadata_token = request.POST.get("fetched_metadata", "")
        # WHY: An explicit upload is the fallback image and takes precedence over an older fetched token.
        if uploaded_thumbnail:
            plan_details["thumbnail_image"] = uploaded_thumbnail
        # WHY: Without an upload, a supplied token must still match this account and current URL.
        elif metadata_token:
            thumbnail_image = thumbnail_from_metadata_token(
                metadata_token,
                request.user.pk,
                form.cleaned_data["public_url"],
            )
            if thumbnail_image is None:
                form.add_error("public_url", "Add venue details again before creating the plan.")
            else:
                plan_details["thumbnail_image"] = thumbnail_image
        # WHY: Does not call the creation service while thumbnail verification has added a form error.
        try:
            plan = None if form.errors else create_available_plan(request.user, plan_details)
        except PermissionDenied:
            form.add_error(None, "The plan could not be created.")
        # WHY: Redirects after success so refreshing the detail page cannot create a duplicate plan.
        if plan is not None:
            messages.success(request, "Plan created.")
            return redirect("plan_detail", plan_id=plan.pk)

    return render(
        request,
        "plan.html",
        {"mode": "create", "form": form},
    )

# =============================================================================
# PROTECTED PLAN IMAGE
# Checks plan visibility before streaming its thumbnail.
# =============================================================================

# WHY: Keeps the plan thumbnail file steps in one named place so they can be understood, checked, and reused.
@require_GET
@login_required
def plan_thumbnail_file(request, plan_id):
    """Stream one stored plan thumbnail only when the plan itself is visible."""
    # WHY: Serves an image only when the same viewer may open its plan page.
    summary = get_plan_page_if_viewer_is_allowed(request.user, plan_id)
    if summary is None or not summary["plan"].thumbnail_image:
        return HttpResponse("Plan image unavailable.", status=404)
    # WHY: Handles a missing storage object with the same response as an unavailable plan image.
    try:
        image_file = summary["plan"].thumbnail_image.open("rb")
    except (FileNotFoundError, OSError):
        return HttpResponse("Plan image unavailable.", status=404)
    # WHY: Streams the server-normalised JPEG under a neutral filename, not its storage path.
    return FileResponse(
        image_file,
        content_type="image/jpeg",
        filename="plan-thumbnail.jpg",
    )

# =============================================================================
# PLAN DETAIL
# Prepares one visible plan and the actions available to this visitor.
# =============================================================================

# WHY: Keeps the plan detail page steps in one named place so they can be understood, checked, and reused.
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
    # WHY: Applies account access before asking whether this particular plan is visible.
    access_redirect = _plan_access_redirect(request)
    if access_redirect is not None:
        return access_redirect

    # WHY: Uses one generic unavailable response for missing and state-hidden plans.
    summary = get_plan_page_if_viewer_is_allowed(request.user, plan_id)
    if summary is None:
        return HttpResponse("Plan unavailable.", status=404)

    plan = summary["plan"]
    # WHY: Produces a normal maps search that opens in the browser or installed maps app without a paid API.
    directions_query = plan.public_address.strip() or plan.public_place.strip()
    # WHY: Uses one time for past and join decisions shown on this page.
    current_time = timezone.now()
    is_owner = plan.owner_id == request.user.pk
    # WHY: The plan-chat link appears only after the first confirmation and only to a derived current member.
    plan_chat_available = PlanChat.objects.filter(plan=plan).exists() and (
        is_owner
        or summary["viewer_participation_status"] == Participation.Status.JOINED
    )
    # WHY: Shows Edit only to the owner before the first join and before cancellation.
    can_edit = (
        is_owner
        and plan.meeting_details_locked_at is None
        and plan.status != plan.Status.CANCELLED
    )
    # WHY: Supplies page decisions rather than making the template repeat ownership and lifecycle rules.
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
            "can_request_participation": can_request_plan_participation(
                request.user,
                plan,
                current_time,
            ),
            "plan_chat_available": plan_chat_available,
            "pending_requests": get_pending_plan_requests_for_owner(
                request.user,
                plan,
            ),
            "directions_url": (
                f"https://www.google.com/maps/search/?api=1&query={quote_plus(directions_query)}"
                if directions_query
                else ""
            ),
        },
    )

# =============================================================================
# EDIT PLAN
# Validates owner changes before the first person joins.
# =============================================================================

# WHY: Keeps the edit plan page steps in one named place so they can be understood, checked, and reused.
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

    # WHY: Begins with ordinary plan visibility, then applies the stricter owner-edit boundary.
    summary = get_plan_page_if_viewer_is_allowed(request.user, plan_id)
    if summary is None:
        return HttpResponse("Plan unavailable.", status=404)
    plan = summary["plan"]
    # WHY: Uses the same not-found response for non-owners, locked plans, and cancelled plans.
    if (
        plan.owner_id != request.user.pk
        or plan.meeting_details_locked_at is not None
        or plan.status == plan.Status.CANCELLED
    ):
        return HttpResponse("Plan unavailable.", status=404)

    # WHY: Binds edits to the server-selected current plan and never exposes protected fields.
    form = PlanImageDetailsForm(
        request.POST if request.method == "POST" else None,
        request.FILES if request.method == "POST" else None,
        instance=plan,
    )
    if request.method == "POST" and form.is_valid():
        # WHY: Starts with cleaned public facts and adds only a verified fetched image when supplied.
        plan_changes = dict(form.cleaned_data)
        uploaded_thumbnail = plan_changes.pop("plan_image", None)
        metadata_token = request.POST.get("fetched_metadata", "")
        # WHY: A deliberate replacement upload takes precedence over fetched metadata just as it does on creation.
        if uploaded_thumbnail:
            plan_changes["thumbnail_image"] = uploaded_thumbnail
        elif metadata_token:
            thumbnail_image = thumbnail_from_metadata_token(
                metadata_token,
                request.user.pk,
                form.cleaned_data["public_url"],
            )
            if thumbnail_image is None:
                form.add_error("public_url", "Add venue details again before saving the plan.")
            else:
                plan_changes["thumbnail_image"] = thumbnail_image
        # WHY: The locked service rechecks ownership and lifecycle because either may change after page loading.
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
        # WHY: Redirects after success so refreshing cannot repeat the edit submission.
        if updated_plan is not None:
            messages.success(request, "Plan updated.")
            return redirect("plan_detail", plan_id=updated_plan.pk)

    return render(
        request,
        "plan.html",
        {"mode": "edit", "form": form, "plan": plan},
    )

# =============================================================================
# PLAN PARTICIPATION AND CANCELLATION
# Handles joining, leaving, and owner cancellation actions.
# =============================================================================

# WHY: Keeps the ask to join steps in one named place so pending access and the owner conversation stay together.
@require_POST
@login_required
def request_plan_participation(request, plan_id):
    """Create a pending request and redirect to the existing owner conversation.

    Inputs: a signed-in CSRF-validated POST and untrusted plan route identifier.
    Returns: a conversation redirect, generic refusal redirect or generic not found.
    Changes: creates/reactivates pending participation without consuming capacity.
    Refuses: hidden, owner, blocked, closed, full, past, pending or joined conditions.
    Privacy: accepts no participant identity and returns no participant directory.
    """
    access_redirect = _plan_access_redirect(request)
    if access_redirect is not None:
        return access_redirect
    # WHY: Requires current page visibility before the locked service rechecks join eligibility.
    summary = get_plan_page_if_viewer_is_allowed(request.user, plan_id)
    if summary is None:
        return HttpResponse("Plan unavailable.", status=404)
    try:
        _participation, conversation = (
            request_plan_participation_and_open_owner_conversation(
                request.user,
                summary["plan"],
            )
        )
    except PermissionDenied:
        messages.error(request, "The participation request could not be sent.")
        return redirect("plan_list")
    messages.success(request, "Request sent. Message the plan owner to introduce yourself.")
    return redirect("conversation_detail", conversation_id=conversation.pk)


# WHY: Keeps owner confirmation behind an explicit CSRF-checked action and the locked capacity service.
@require_POST
@login_required
def confirm_plan_participation(request, plan_id, participation_id):
    """Confirm one pending requester as a capacity-counted participant."""
    access_redirect = _plan_access_redirect(request)
    if access_redirect is not None:
        return access_redirect
    summary = get_plan_page_if_viewer_is_allowed(request.user, plan_id)
    if summary is None:
        return HttpResponse("Plan unavailable.", status=404)
    try:
        confirm_requested_plan_participation(
            request.user,
            summary["plan"],
            participation_id,
        )
    except PermissionDenied:
        messages.error(request, "The participation request could not be confirmed.")
        return redirect("plan_detail", plan_id=plan_id)
    messages.success(request, "Participation confirmed.")
    return redirect("plan_detail", plan_id=plan_id)


# WHY: Keeps owner decline separate from confirmation so a request cannot change in the wrong direction.
@require_POST
@login_required
def decline_plan_participation(request, plan_id, participation_id):
    """Decline one pending request without consuming a capacity place."""
    access_redirect = _plan_access_redirect(request)
    if access_redirect is not None:
        return access_redirect
    summary = get_plan_page_if_viewer_is_allowed(request.user, plan_id)
    if summary is None:
        return HttpResponse("Plan unavailable.", status=404)
    try:
        decline_requested_plan_participation(
            request.user,
            summary["plan"],
            participation_id,
        )
    except PermissionDenied:
        messages.error(request, "The participation request could not be declined.")
        return redirect("plan_detail", plan_id=plan_id)
    messages.success(request, "Participation request declined.")
    return redirect("plan_detail", plan_id=plan_id)


# WHY: Lets the signed-in requester withdraw only their own pending row.
@require_POST
@login_required
def withdraw_plan_participation(request, plan_id):
    """Withdraw the caller's pending request while preserving its row."""
    access_redirect = _plan_access_redirect(request)
    if access_redirect is not None:
        return access_redirect
    summary = get_plan_page_if_viewer_is_allowed(request.user, plan_id)
    if summary is None:
        return HttpResponse("Plan unavailable.", status=404)
    try:
        withdraw_pending_plan_participation(request.user, summary["plan"])
    except PermissionDenied:
        messages.error(request, "The participation request could not be withdrawn.")
        return redirect("plan_detail", plan_id=plan_id)
    messages.success(request, "Participation request withdrawn.")
    return redirect("plan_detail", plan_id=plan_id)

# WHY: Keeps the leave plan steps in one named place so they can be understood, checked, and reused.
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
    # WHY: Allows leaving only through a plan page the account may currently open.
    summary = get_plan_page_if_viewer_is_allowed(request.user, plan_id)
    if summary is None:
        return HttpResponse("Plan unavailable.", status=404)
    # WHY: The service checks the caller's own current participation and preserves its history.
    try:
        leave_plan_and_keep_participation_history(request.user, summary["plan"])
    except PermissionDenied:
        messages.error(request, "The plan could not be left.")
        return redirect("plan_list")
    messages.success(request, "You left the plan.")
    return redirect("plan_detail", plan_id=plan_id)

# WHY: Keeps the cancel plan steps in one named place so they can be understood, checked, and reused.
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
    # WHY: Loads a visible plan, while the service independently rechecks ownership and terminal state.
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
