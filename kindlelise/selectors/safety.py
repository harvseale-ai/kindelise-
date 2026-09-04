"""Read profiles and plan-chat messages permitted as private report targets."""

from kindlelise.models import PlanChatMessage, Profile
from kindlelise.policies import can_read_plan_chat, can_report_another_user

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


# WHY: Resolves a plan-chat message only while the reporter can open its chat and the named target sent it.
def get_plan_chat_message_if_reporter_is_allowed(
    reporter,
    message_id,
    reported_user,
):
    """Return one received plan-chat message currently visible to the reporter."""
    message = (
        PlanChatMessage.objects.select_related("chat", "chat__plan", "sender")
        .filter(pk=message_id, sender=reported_user)
        .first()
    )
    if (
        message is None
        or message.sender_id == getattr(reporter, "pk", None)
        or not can_read_plan_chat(reporter, message.chat)
    ):
        return None
    return message
