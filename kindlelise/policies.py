"""Answer the eight mapped Kindelise permission questions."""

# KEYWORD: policy — one named yes-or-no rule that decides whether an action is allowed.


from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Q

from kindlelise.models import (
    Block,
    Participation,
    PlatformSubscription,
    Profile,
)


# WHY: Answers whether access discovery plans and messages so every page follows the same permission rule.
def can_access_discovery_plans_and_messages(user):
    """Return true only for an active account with a staff-verified profile.

    Inputs: a possible authenticated Django account.
    Returns: the social-feature access decision.
    Changes: none.
    Refuses: anonymous, inactive, missing-profile and unverified states.
    Privacy: returns only a decision and no profile details.
    """
    # WHY: Treats missing, anonymous, and unsaved account values as not allowed without raising an error.
    if not getattr(user, "is_authenticated", False) or getattr(user, "pk", None) is None:
        return False

    # WHY: Reads current saved account and profile state so staff removal takes effect immediately.
    return get_user_model().objects.filter(
        pk=user.pk,
        is_active=True,
        profile__is_verified=True,
    ).exists()


# WHY: Finds the allowed discovery areas and interest limit information in one place so callers receive the same result.
def get_allowed_discovery_areas_and_interest_limit(user):
    """Return the exact discovery areas and interest limit allowed to the account.

    Inputs: the server-known account and its current subscription projection.
    Returns: an ordered area-key tuple and a maximum selected-interest count.
    Changes: none.
    Refuses: ineligible accounts and unconfigured current areas with empty limits.
    Privacy: returns only configured area keys and a numeric limit.
    """
    # WHY: Gives an ineligible account no areas and no interest filters rather than partial discovery access.
    if not can_access_discovery_plans_and_messages(user):
        return (), 0

    # WHY: Reads only the two area fields needed for this decision, not the whole profile.
    profile_areas = Profile.objects.filter(user_id=user.pk).values(
        "broad_area",
        "broad_areas",
    ).first()
    # WHY: Handles a missing related profile as no access even if the account object looked valid earlier.
    if profile_areas is None:
        return (), 0

    # WHY: Uses current multiple areas when present and falls back to the older single-area value.
    stored_areas = profile_areas["broad_areas"] or (profile_areas["broad_area"],)

    # WHY: Removes duplicates and unknown keys while preserving the visitor's saved area order.
    current_areas = tuple(
        dict.fromkeys(
            area for area in stored_areas if area in settings.KINDLELISE_AREAS
        )
    )
    # WHY: Refuses discovery when none of the saved areas still exist in site configuration.
    if not current_areas:
        return (), 0

    # WHY: Reads the account's own local subscription summary rather than trusting browser payment claims.
    subscription = PlatformSubscription.objects.filter(user_id=user.pk).first()
    has_premium_access = (
        subscription.has_premium_access() if subscription is not None else False
    )

    # WHY: Free access stays within the profile's own areas and allows two selected interests.
    if not has_premium_access:
        return current_areas, 2

    # WHY: Premium begins with every current area before adding only configured neighbouring areas.
    areas = dict.fromkeys(current_areas)
    for current_area in current_areas:
        areas.update(
            dict.fromkeys(
                settings.KINDLELISE_NEARBY_AREAS.get(current_area, ())
            )
        )
    # WHY: Filters the expanded list through the main area configuration before returning it.
    allowed_areas = tuple(
        area_key for area_key in areas if area_key in settings.KINDLELISE_AREAS
    )
    return allowed_areas, 5


# WHY: Answers whether view profile page so every page follows the same permission rule.
def can_view_profile_page(viewer, profile):
    """Return true only when both accounts may interact and neither has blocked.

    Inputs: the server-known viewer and a retrieved target profile.
    Returns: whether the target's public profile page may be shown.
    Changes: none.
    Refuses: ineligible accounts and a block in either direction.
    Privacy: returns one decision without revealing the refusal reason.
    """
    # WHY: Requires both a real target profile and a currently eligible viewer.
    if profile is None or not can_access_discovery_plans_and_messages(viewer):
        return False

    # WHY: Hides profiles whose owning account no longer has verified active access.
    if not can_access_discovery_plans_and_messages(profile.user):
        return False

    # WHY: Treats a block from either person as closing profile viewing in both directions.
    return not Block.objects.filter(
        Q(blocker=viewer, blocked_user=profile.user)
        | Q(blocker=profile.user, blocked_user=viewer)
    ).exists()


# WHY: Answers whether show profile in discovery grid so every page follows the same permission rule.
def can_show_profile_in_discovery_grid(viewer, profile):
    """Return true only for an allowed-area profile with no eligibility block.

    Inputs: the server-known viewer and one candidate profile.
    Returns: whether the candidate may enter the viewer's discovery grid.
    Changes: none.
    Refuses: self, ineligible accounts, disallowed areas and either-direction blocks.
    Privacy: returns one decision without exposing hidden-profile details.
    """
    # WHY: Never shows a missing target or the viewer's own profile as a discovery result.
    if profile is None or profile.user_id == getattr(viewer, "pk", None):
        return False

    # WHY: Reuses the full profile-page permission before checking the additional area rule.
    if not can_view_profile_page(viewer, profile):
        return False
    allowed_areas, _interest_limit = get_allowed_discovery_areas_and_interest_limit(
        viewer
    )
    # WHY: A candidate needs only one broad area shared with the viewer's permitted discovery reach.
    profile_areas = profile.broad_areas or (profile.broad_area,)
    return bool(set(profile_areas).intersection(allowed_areas))


# WHY: Answers whether create plan so every page follows the same permission rule.
def can_create_plan(user):
    """Return true only when the account may create a public-place plan.

    Inputs: a possible authenticated Django account.
    Returns: whether a plan may be created for that account.
    Changes: none.
    Refuses: anonymous, inactive, missing-profile and unverified states.
    Privacy: returns only a decision and no profile details.
    """
    # WHY: Plan creation uses the same verified active-account gate as discovery and messages.
    return can_access_discovery_plans_and_messages(user)


# WHY: Answers whether join approved plan so every page follows the same permission rule.
def can_join_approved_plan(user, plan, at_time):
    """Return true only when the account may join the approved plan now.

    Inputs: the server-known account, current plan and supplied aware time.
    Returns: whether a new or left participation may become joined.
    Changes: none.
    Refuses: ineligible users, owners, closed/full plans and current participants.
    Privacy: returns only a decision and no participant identities.
    """
    # WHY: Requires a real plan and current account access before checking plan-specific rules.
    if plan is None or not can_access_discovery_plans_and_messages(user):
        return False

    # WHY: Owners cannot join their own plan, and closed, past, or full plans cannot accept anyone.
    if plan.owner_id == user.pk or not plan.is_open_for_joining(at_time):
        return False

    # WHY: Prevents a currently joined account occupying capacity twice.
    return not Participation.objects.filter(
        plan=plan,
        user=user,
        status=Participation.Status.JOINED,
    ).exists()


# WHY: Answers whether start or continue direct messages so every page follows the same permission rule.
def can_start_or_continue_direct_messages(sender, recipient):
    """Return true only when two eligible accounts may message each other.

    Inputs: the server-known sender and intended different recipient accounts.
    Returns: whether the pair may start, open or continue direct messages.
    Changes: none.
    Refuses: identical, inactive, unverified or either-direction-blocked accounts.
    Privacy: returns one decision without revealing which condition refused access.
    """
    # WHY: Direct messages always require two different, known accounts.
    if sender is None or recipient is None or sender.pk == recipient.pk:
        return False

    # WHY: Rechecks each side independently because either account may have lost access since the last message.
    if not can_access_discovery_plans_and_messages(sender):
        return False
    if not can_access_discovery_plans_and_messages(recipient):
        return False
    # WHY: A block in either direction closes the conversation for both people.
    return not Block.objects.filter(
        Q(blocker=sender, blocked_user=recipient)
        | Q(blocker=recipient, blocked_user=sender)
    ).exists()


# WHY: Answers whether report another user so every page follows the same permission rule.
def can_report_another_user(reporter, reported_user):
    """Return true for an authenticated reporter targeting a different account.

    Inputs: the possible reporter and a server-known reported account.
    Returns: whether the reporter may submit a private report about that account.
    Changes: none.
    Refuses: anonymous, missing, unsaved and self-targeting accounts.
    Privacy: deliberately ignores blocks so blocked interactions remain reportable.
    """
    # WHY: Reporting stays available across blocks but still requires a signed-in person and a different target.
    return (
        getattr(reporter, "is_authenticated", False)
        and getattr(reporter, "pk", None) is not None
        and getattr(reported_user, "pk", None) is not None
        and reporter.pk != reported_user.pk
    )
