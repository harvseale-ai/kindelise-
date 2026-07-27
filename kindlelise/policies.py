"""Answer the eight mapped Kindlelise permission questions."""

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Q

from kindlelise.models import (
    Block,
    Participation,
    PlatformSubscription,
    Profile,
)


def can_access_discovery_plans_and_messages(user):
    """Return true only for an active account with a staff-verified profile.

    Inputs: a possible authenticated Django account.
    Returns: the social-feature access decision.
    Changes: none.
    Refuses: anonymous, inactive, missing-profile and unverified states.
    Privacy: returns only a decision and no profile details.
    """
    if not getattr(user, "is_authenticated", False) or getattr(user, "pk", None) is None:
        return False
    # Query durable state so a cached request relation cannot outlive staff removal.
    return get_user_model().objects.filter(
        pk=user.pk,
        is_active=True,
        profile__is_verified=True,
    ).exists()


def get_allowed_discovery_areas_and_interest_limit(user):
    """Return the exact discovery areas and interest limit allowed to the account.

    Inputs: the server-known account and its current subscription projection.
    Returns: an ordered area-key tuple and a maximum selected-interest count.
    Changes: none.
    Refuses: ineligible accounts and unconfigured current areas with empty limits.
    Privacy: returns only configured area keys and a numeric limit.
    """
    if not can_access_discovery_plans_and_messages(user):
        return (), 0

    current_area = Profile.objects.filter(user_id=user.pk).values_list(
        "broad_area",
        flat=True,
    ).first()
    if current_area not in settings.KINDLELISE_AREAS:
        return (), 0

    subscription = PlatformSubscription.objects.filter(user_id=user.pk).first()
    has_premium_access = (
        subscription.has_premium_access() if subscription is not None else False
    )

    if not has_premium_access:
        return (current_area,), 2

    configured_nearby_areas = settings.KINDLELISE_NEARBY_AREAS.get(
        current_area,
        (),
    )
    areas = dict.fromkeys((current_area, *configured_nearby_areas))
    allowed_areas = tuple(
        area_key for area_key in areas if area_key in settings.KINDLELISE_AREAS
    )
    return allowed_areas, 5


def can_view_profile_page(viewer, profile):
    """Return true only when both accounts may interact and neither has blocked.

    Inputs: the server-known viewer and a retrieved target profile.
    Returns: whether the target's public profile page may be shown.
    Changes: none.
    Refuses: ineligible accounts and a block in either direction.
    Privacy: returns one decision without revealing the refusal reason.
    """
    if profile is None or not can_access_discovery_plans_and_messages(viewer):
        return False
    if not can_access_discovery_plans_and_messages(profile.user):
        return False
    return not Block.objects.filter(
        Q(blocker=viewer, blocked_user=profile.user)
        | Q(blocker=profile.user, blocked_user=viewer)
    ).exists()


def can_show_profile_in_discovery_grid(viewer, profile):
    """Return true only for an allowed-area profile with no eligibility block.

    Inputs: the server-known viewer and one candidate profile.
    Returns: whether the candidate may enter the viewer's discovery grid.
    Changes: none.
    Refuses: self, ineligible accounts, disallowed areas and either-direction blocks.
    Privacy: returns one decision without exposing hidden-profile details.
    """
    if profile is None or profile.user_id == getattr(viewer, "pk", None):
        return False
    if not can_view_profile_page(viewer, profile):
        return False
    allowed_areas, _interest_limit = get_allowed_discovery_areas_and_interest_limit(
        viewer
    )
    return profile.broad_area in allowed_areas


def can_create_plan_for_staff_review(user):
    """Return true only when the account may submit a plan for staff review.

    Inputs: a possible authenticated Django account.
    Returns: whether a pending plan may be created for that account.
    Changes: none.
    Refuses: anonymous, inactive, missing-profile and unverified states.
    Privacy: returns only a decision and no profile details.
    """
    return can_access_discovery_plans_and_messages(user)


def can_join_approved_plan(user, plan, at_time):
    """Return true only when the account may join the approved plan now.

    Inputs: the server-known account, current plan and supplied aware time.
    Returns: whether a new or left participation may become joined.
    Changes: none.
    Refuses: ineligible users, owners, closed/full plans and current participants.
    Privacy: returns only a decision and no participant identities.
    """
    if plan is None or not can_access_discovery_plans_and_messages(user):
        return False
    if plan.owner_id == user.pk or not plan.is_open_for_joining(at_time):
        return False
    return not Participation.objects.filter(
        plan=plan,
        user=user,
        status=Participation.Status.JOINED,
    ).exists()


def can_start_or_continue_direct_messages(sender, recipient):
    """Return true only when two eligible accounts may message each other.

    Inputs: the server-known sender and intended different recipient accounts.
    Returns: whether the pair may start, open or continue direct messages.
    Changes: none.
    Refuses: identical, inactive, unverified or either-direction-blocked accounts.
    Privacy: returns one decision without revealing which condition refused access.
    """
    if sender is None or recipient is None or sender.pk == recipient.pk:
        return False
    if not can_access_discovery_plans_and_messages(sender):
        return False
    if not can_access_discovery_plans_and_messages(recipient):
        return False
    return not Block.objects.filter(
        Q(blocker=sender, blocked_user=recipient)
        | Q(blocker=recipient, blocked_user=sender)
    ).exists()


def can_report_another_user(reporter, reported_user):
    """Return true for an authenticated reporter targeting a different account.

    Inputs: the possible reporter and a server-known reported account.
    Returns: whether the reporter may submit a private report about that account.
    Changes: none.
    Refuses: anonymous, missing, unsaved and self-targeting accounts.
    Privacy: deliberately ignores blocks so blocked interactions remain reportable.
    """
    return (
        getattr(reporter, "is_authenticated", False)
        and getattr(reporter, "pk", None) is not None
        and getattr(reported_user, "pk", None) is not None
        and reporter.pk != reported_user.pk
    )
