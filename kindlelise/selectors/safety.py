"""Read the profile that may be used as a private report target."""

from kindlelise.models import Profile
from kindlelise.policies import can_report_another_user

# =============================================================================
# REPORT TARGET READS
# Loads a report target without hiding the safety action after a block.
# =============================================================================


# WHY: Finds the report target profile if reporter is allowed information in one place so callers receive the same result.
def get_report_target_profile_if_reporter_is_allowed(reporter, profile_id):
    """Return a report target without applying discovery or messaging visibility.

    Inputs: the possible reporter and an untrusted route profile ID.
    Returns: the permitted target Profile, or none for absence or refusal.
    Changes: none.
    Refuses: anonymous reporters and missing or self-target profiles.
    Privacy: returns no block reason and does not expose any report record.
    """
    # WHY: Loads the target account for the separate reporting rule without applying discovery visibility.
    profile = Profile.objects.select_related("user").filter(pk=profile_id).first()

    # WHY: A block closes interaction but must never suppress private reporting.
    if profile is None or not can_report_another_user(reporter, profile.user):
        return None
    return profile
