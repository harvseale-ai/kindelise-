"""Read discovery cards, public profiles, and protected profile images."""

from django.db.models import Q
from django.utils import timezone

from kindlelise.models import Block, Profile
from kindlelise.policies import (
    can_view_profile_page,
    get_allowed_discovery_areas_and_interest_limit,
)

# =============================================================================
# DISCOVERY AND PROFILE READS
# Loads permitted discovery cards, public profiles, and profile images.
# =============================================================================


# WHY: Finds the profiles for discovery grid information in one place so callers receive the same result.
def get_profiles_for_discovery_grid(viewer, selected_filters):
    """Return only permitted, active and unblocked discovery profiles.

    Inputs: the server-known viewer and validated DiscoveryFiltersForm values.
    Returns: an ordered Profile queryset containing only presentable rows.
    Changes: none.
    Refuses: stale or excessive filters and every ineligible viewer with no rows.
    Privacy: excludes self, blocks and hidden profiles before returning results.
    """
    # WHY: Starts with server-calculated area reach and interest limits for this exact viewer.
    allowed_areas, interest_limit = get_allowed_discovery_areas_and_interest_limit(
        viewer
    )
    # WHY: Accepts the older one-area shape while treating current multiple areas uniformly.
    selected_areas = selected_filters.get("broad_area") or ()
    if isinstance(selected_areas, str):
        selected_areas = (selected_areas,)
    # WHY: Refuses unusual unhashable values instead of allowing a malformed filter into a database query.
    try:
        selected_area_keys = set(selected_areas)
    except TypeError:
        return Profile.objects.none()
    # WHY: Requires at least one selection and refuses every area outside the viewer's permitted reach.
    if not selected_area_keys or not selected_area_keys.issubset(set(allowed_areas)):
        return Profile.objects.none()

    # WHY: Converts validated Interest objects into IDs without trusting raw browser numbers.
    selected_interests = selected_filters.get("interests")
    if selected_interests is None:
        selected_interests = ()
    interest_ids = []
    for interest in selected_interests:
        if getattr(interest, "pk", None) is None:
            return Profile.objects.none()
        interest_ids.append(interest.pk)
    # WHY: Rechecks the limit here even if a caller forgot to use the discovery form first.
    if len(interest_ids) > interest_limit:
        return Profile.objects.none()

    # WHY: Builds both block directions so neither side appears in the other's discovery results.
    blocked_by_viewer = Block.objects.filter(blocker=viewer).values("blocked_user_id")
    viewers_blockers = Block.objects.filter(blocked_user=viewer).values("blocker_id")
    # WHY: Filters hidden accounts in the database before names, images, or interests reach presentation code.
    profiles = (
        Profile.objects.select_related("user")
        .prefetch_related("interests")
        .filter(
            Q(broad_areas__overlap=list(selected_area_keys))
            | Q(broad_area__in=selected_area_keys),
            user__is_active=True,
        )
        .exclude(user=viewer)
        .exclude(Q(user_id__in=blocked_by_viewer) | Q(user_id__in=viewers_blockers))
    )
    # WHY: Matches any selected interest and removes duplicates caused by several matching interest links.
    if interest_ids:
        profiles = profiles.filter(interests__id__in=interest_ids).distinct()
    # WHY: Free now means the saved start time has arrived; it does not expose the actual time to other users.
    if selected_filters.get("available_now"):
        profiles = profiles.filter(available_from__lte=timezone.now())
    # WHY: Keeps cards alphabetic and stable when two profiles use the same display name.
    return profiles.order_by("display_name", "pk")


# WHY: Finds the profile page if viewer is allowed information in one place so callers receive the same result.
def get_profile_page_if_viewer_is_allowed(viewer, profile_id):
    """Return one profile only when the viewer may open its public page.

    Inputs: the server-known viewer and an untrusted route profile ID.
    Returns: the permitted Profile, or none for every missing or refused target.
    Changes: none.
    Refuses: missing, inactive and either-direction-blocked targets.
    Privacy: uses the same no-result outcome for absence and every denial reason.
    """
    # WHY: Loads the possible target and its display interests before applying the single page policy.
    profile = (
        Profile.objects.select_related("user")
        .prefetch_related("interests")
        .filter(pk=profile_id)
        .first()
    )
    # WHY: Returns the same empty result for missing, inactive and blocked targets.
    if not can_view_profile_page(viewer, profile):
        return None
    return profile


# WHY: Finds the profile image if viewer is allowed information in one place so callers receive the same result.
def get_profile_image_if_viewer_is_allowed(viewer, profile_id):
    """Return one stored image only to its active owner or an allowed viewer.

    Inputs: the server-known viewer and an untrusted route profile ID.
    Returns: the image-bearing Profile, or none for missing and denied cases.
    Changes: none.
    Refuses: anonymous/inactive viewers and hidden, blocked or missing targets.
    Privacy: uses one no-result outcome and never exposes a storage path.
    """
    # WHY: Uploads are never served to anonymous or inactive accounts.
    if not getattr(viewer, "is_authenticated", False) or not viewer.is_active:
        return None

    # WHY: Checks image presence before opening storage and keeps the storage path private.
    profile = Profile.objects.select_related("user").filter(pk=profile_id).first()
    if profile is None or not profile.profile_image:
        return None
    # WHY: Lets an active owner see their own uploaded image while their profile is awaiting verification.
    if profile.user_id == viewer.pk:
        return profile
    if not can_view_profile_page(viewer, profile):
        return None
    return profile
