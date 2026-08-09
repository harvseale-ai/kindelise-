"""Small presentation helpers shared by more than one page group."""

# WHY: These helpers keep repeated display and safe-return rules consistent across pages.
from django.conf import settings
from django.utils.http import url_has_allowed_host_and_scheme


# WHY: Keeps the safe local redirect steps in one named place so they can be understood, checked, and reused.
def _safe_local_redirect(request):
    """Return a same-site next destination, or no destination when unsafe."""
    # WHY: Prefers a submitted destination but also supports the destination carried on the sign-in link.
    destination = request.POST.get("next") or request.GET.get("next")

    # WHY: Accepts only this website's host and the same encryption level as the current visit.
    if destination and url_has_allowed_host_and_scheme(
        destination,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return destination
    return None

# WHY: Keeps the profile broad area label steps in one named place so they can be understood, checked, and reused.
def _profile_broad_area_label(profile):
    """Return configured labels for one profile's selected broad areas."""
    # WHY: Uses current multiple areas and falls back to the older single-area value.
    area_keys = profile.broad_areas or (profile.broad_area,)

    # WHY: Shows only configured visitor-facing labels and gives incomplete profiles a clear fallback.
    return ", ".join(
        settings.KINDLELISE_AREAS[area_key]
        for area_key in area_keys
        if area_key in settings.KINDLELISE_AREAS
    ) or "Not completed"
