"""Discovery results and other people's public profile pages."""

# WHY: This module keeps finding people and viewing their public details in one place.
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET

from kindlelise.forms import DiscoveryFiltersForm
from kindlelise.models import Plan
from kindlelise.policies import (
    can_access_discovery_plans_and_messages,
    get_allowed_discovery_areas_and_interest_limit,
)
from kindlelise.selectors import (
    get_profile_page_if_viewer_is_allowed,
    get_profiles_for_discovery_grid,
)
from kindlelise.views.common import _profile_broad_area_label

# =============================================================================
# DISCOVERY GRID
# Validates discovery filters and prepares the permitted profile cards.
# =============================================================================

# WHY: Keeps the discovery page steps in one named place so they can be understood, checked, and reused.
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
    # WHY: Stops before calculating filters or loading profiles when current verified access is absent.
    if not can_access_discovery_plans_and_messages(request.user):
        messages.info(
            request,
            "Complete your profile and wait for staff verification to use discovery.",
        )
        return redirect("account")

    # WHY: Gets server-owned Free or Premium filter reach for this exact account.
    allowed_areas, interest_limit = get_allowed_discovery_areas_and_interest_limit(
        request.user
    )
    # WHY: A verified account with no valid configured area still receives no discovery access.
    if not allowed_areas:
        messages.info(
            request,
            "Complete your profile and wait for staff verification to use discovery.",
        )
        return redirect("account")

    # WHY: Defaults a first visit to all permitted areas while preserving explicit submitted filters.
    form_data = request.GET if request.GET else {"broad_area": list(allowed_areas)}
    form = DiscoveryFiltersForm(
        form_data,
        allowed_areas=allowed_areas,
        interest_limit=interest_limit,
    )
    # WHY: Invalid filters produce no profile rows and remain visible for correction.
    profile_cards = []
    if form.is_valid():
        # WHY: Uses one time for every Free now label on this rendered grid.
        current_time = timezone.now()
        profiles = get_profiles_for_discovery_grid(
            request.user,
            form.cleaned_data,
        )
        # WHY: Adds only display labels to already authorised profile results.
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


# =============================================================================
# PUBLIC PROFILE
# Prepares another person's permitted profile details and available plans.
# =============================================================================

# WHY: Keeps the profile page steps in one named place so they can be understood, checked, and reused.
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
    # WHY: Applies the viewer's current access gate before attempting to find the target profile.
    if not can_access_discovery_plans_and_messages(request.user):
        messages.info(
            request,
            "Complete your profile and wait for staff verification to use discovery.",
        )
        return redirect("account")

    # WHY: Uses the same not-found outcome for missing, blocked, inactive, and unverified profiles.
    profile = get_profile_page_if_viewer_is_allowed(request.user, profile_id)
    if profile is None:
        return HttpResponse("Profile unavailable.", status=404)

    # WHY: Shows only the target's approved future plans, never their review or cancelled states.
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
