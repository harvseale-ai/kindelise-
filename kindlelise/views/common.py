"""Small presentation helpers shared by more than one page group."""

# WHY: These helpers keep repeated display and safe-return rules consistent across pages.
from io import BytesIO

from django.conf import settings
from django.http import FileResponse
from django.utils.http import url_has_allowed_host_and_scheme
from PIL import Image, ImageOps, UnidentifiedImageError

# =============================================================================
# SHARED PAGE HELPERS
# Provides small presentation and safe-return helpers used by several pages.
# =============================================================================

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


def _responsive_image_response(image_file, variant):
    """Return a small WebP variant for a card or avatar, when requested."""
    dimensions = {
        "avatar": (128, 128),
        "card": (360, 480),
    }.get(variant)
    if dimensions is None:
        return None

    try:
        with Image.open(image_file) as source_image:
            source_image.load()
            prepared_image = ImageOps.fit(
                ImageOps.exif_transpose(source_image).convert("RGB"),
                dimensions,
                method=Image.Resampling.LANCZOS,
            )
            output = BytesIO()
            prepared_image.save(output, format="WEBP", quality=76, method=6)
            output.seek(0)
    except (OSError, ValueError, UnidentifiedImageError):
        return None

    response = FileResponse(
        output,
        content_type="image/webp",
        filename=f"{variant}.webp",
    )
    response["Cache-Control"] = "private, max-age=31536000, immutable"
    return response
