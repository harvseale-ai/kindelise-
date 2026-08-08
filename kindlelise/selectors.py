"""Own the eleven mapped authorised Kindlelise read operations."""

from django.db.models import Count, Q
from django.utils import timezone

from kindlelise.models import (
    Block,
    Conversation,
    Notification,
    Participation,
    Plan,
    PlatformSubscription,
    Profile,
)
from kindlelise.policies import (
    can_access_discovery_plans_and_messages,
    can_report_another_user,
    can_start_or_continue_direct_messages,
    can_view_profile_page,
    get_allowed_discovery_areas_and_interest_limit,
)


def get_unread_notification_count(user):
    """Return only the signed-in account's unread message and plan-join count."""
    if not getattr(user, "is_authenticated", False) or not user.is_active:
        return 0
    return Notification.objects.filter(recipient=user, read_at__isnull=True).count()


def get_recent_notifications(user, limit=30):
    """Return the signed-in account's recent alerts with only display-safe context."""
    if not getattr(user, "is_authenticated", False) or not user.is_active:
        return Notification.objects.none()
    return (
        Notification.objects.filter(recipient=user)
        .select_related(
            "message__conversation",
            "message__sender__profile",
            "participation__plan",
            "participation__user__profile",
        )
        .order_by("-created_at", "-pk")[:limit]
    )


def get_signed_in_user_account_summary(user):
    """Return the signed-in account's own profile, plans and subscription summary.

    Inputs: the server-known signed-in Django account.
    Returns: a minimal private account summary, or none when access is refused.
    Changes: none.
    Refuses: anonymous, inactive or missing-profile accounts.
    Privacy: omits reports, webhook receipts and raw Stripe identifiers.
    """
    if not getattr(user, "is_authenticated", False) or not user.is_active:
        return None

    try:
        profile = Profile.objects.prefetch_related("interests").get(user=user)
    except Profile.DoesNotExist:
        return None

    subscription = PlatformSubscription.objects.filter(user=user).first()
    subscription_summary = {
        "has_premium_access": False,
        "status": None,
        "access_until": None,
        "customer_portal_available": False,
        "has_stripe_history": False,
        "trial_available": True,
        "checkout_available": True,
    }
    if subscription is not None:
        has_stripe_history = bool(
            subscription.stripe_customer_id
            or subscription.stripe_subscription_id
        )
        subscription_summary.update(
            {
                "has_premium_access": subscription.has_premium_access(),
                "status": subscription.stripe_status,
                "access_until": subscription.access_until,
                "customer_portal_available": bool(subscription.stripe_customer_id),
                "has_stripe_history": has_stripe_history,
                "trial_available": not has_stripe_history,
                "checkout_available": subscription.stripe_status
                not in {"active", "trialing"},
            }
        )

    return {
        "account": {"email": user.email},
        "profile": profile,
        "plans": Plan.objects.filter(owner=user).order_by("-created_at"),
        "subscription": subscription_summary,
    }


def get_profiles_for_discovery_grid(viewer, selected_filters):
    """Return only verified, permitted and unblocked discovery profiles.

    Inputs: the server-known viewer and validated DiscoveryFiltersForm values.
    Returns: an ordered Profile queryset containing only presentable rows.
    Changes: none.
    Refuses: stale or excessive filters and every ineligible viewer with no rows.
    Privacy: excludes self, blocks and hidden profiles before returning results.
    """
    allowed_areas, interest_limit = get_allowed_discovery_areas_and_interest_limit(
        viewer
    )
    selected_areas = selected_filters.get("broad_area") or ()
    if isinstance(selected_areas, str):
        selected_areas = (selected_areas,)
    try:
        selected_area_keys = set(selected_areas)
    except TypeError:
        return Profile.objects.none()
    if not selected_area_keys or not selected_area_keys.issubset(set(allowed_areas)):
        return Profile.objects.none()

    selected_interests = selected_filters.get("interests")
    if selected_interests is None:
        selected_interests = ()
    interest_ids = []
    for interest in selected_interests:
        if getattr(interest, "pk", None) is None:
            return Profile.objects.none()
        interest_ids.append(interest.pk)
    if len(interest_ids) > interest_limit:
        return Profile.objects.none()

    blocked_by_viewer = Block.objects.filter(blocker=viewer).values(
        "blocked_user_id"
    )
    viewers_blockers = Block.objects.filter(blocked_user=viewer).values(
        "blocker_id"
    )
    profiles = (
        Profile.objects.select_related("user")
        .prefetch_related("interests")
        .filter(
            Q(broad_areas__overlap=list(selected_area_keys))
            | Q(broad_area__in=selected_area_keys),
            is_verified=True,
            user__is_active=True,
        )
        .exclude(user=viewer)
        .exclude(
            Q(user_id__in=blocked_by_viewer)
            | Q(user_id__in=viewers_blockers)
        )
    )
    if interest_ids:
        profiles = profiles.filter(interests__id__in=interest_ids).distinct()
    if selected_filters.get("available_now"):
        profiles = profiles.filter(available_from__lte=timezone.now())
    return profiles.order_by("display_name", "pk")


def get_profile_page_if_viewer_is_allowed(viewer, profile_id):
    """Return one profile only when the viewer may open its public page.

    Inputs: the server-known viewer and an untrusted route profile ID.
    Returns: the permitted Profile, or none for every missing or refused target.
    Changes: none.
    Refuses: missing, inactive, unverified and either-direction-blocked targets.
    Privacy: uses the same no-result outcome for absence and every denial reason.
    """
    profile = (
        Profile.objects.select_related("user")
        .prefetch_related("interests")
        .filter(pk=profile_id)
        .first()
    )
    if not can_view_profile_page(viewer, profile):
        return None
    return profile


def get_profile_image_if_viewer_is_allowed(viewer, profile_id):
    """Return one stored image only to its active owner or an allowed viewer.

    Inputs: the server-known viewer and an untrusted route profile ID.
    Returns: the image-bearing Profile, or none for missing and denied cases.
    Changes: none.
    Refuses: anonymous/inactive viewers and hidden, blocked or missing targets.
    Privacy: uses one no-result outcome and never exposes a storage path.
    """
    if not getattr(viewer, "is_authenticated", False) or not viewer.is_active:
        return None
    profile = Profile.objects.select_related("user").filter(pk=profile_id).first()
    if profile is None or not profile.profile_image:
        return None
    if profile.user_id == viewer.pk:
        return profile
    if not can_view_profile_page(viewer, profile):
        return None
    return profile


def get_report_target_profile_if_reporter_is_allowed(reporter, profile_id):
    """Return a report target without applying discovery or messaging visibility.

    Inputs: the possible reporter and an untrusted route profile ID.
    Returns: the permitted target Profile, or none for absence or refusal.
    Changes: none.
    Refuses: anonymous reporters and missing or self-target profiles.
    Privacy: returns no block reason and does not expose any report record.
    """
    profile = Profile.objects.select_related("user").filter(pk=profile_id).first()
    # A block closes interaction, but must never suppress private reporting.
    if profile is None or not can_report_another_user(reporter, profile.user):
        return None
    return profile


def get_plans_for_plan_list(user):
    """Return approved future plans plus the signed-in account's own plan states.

    Inputs: the server-known signed-in account.
    Returns: an ordered Plan queryset containing only list-visible records.
    Changes: none.
    Refuses: every ineligible account with an empty queryset.
    Privacy: excludes every other owner's unapproved or cancelled plan.
    """
    if not can_access_discovery_plans_and_messages(user):
        return Plan.objects.none()
    current_time = timezone.now()
    return (
        Plan.objects.select_related("owner")
        .annotate(
            joined_count=Count(
                "participations",
                filter=Q(participations__status=Participation.Status.JOINED),
            )
        )
        .filter(
            Q(status=Plan.Status.APPROVED, starts_at__gt=current_time)
            | Q(
                owner=user,
                status__in=(
                    Plan.Status.PENDING,
                    Plan.Status.REJECTED,
                    Plan.Status.CANCELLED,
                ),
            )
        )
        .order_by("starts_at", "created_at", "pk")
    )


def get_plan_page_if_viewer_is_allowed(viewer, plan_id):
    """Return one visible plan with joined count and the viewer's own state.

    Inputs: the server-known viewer and an untrusted route plan ID.
    Returns: a privacy-minimised plan summary, or none for absence or refusal.
    Changes: none.
    Refuses: ineligible viewers and plans hidden by state or ownership.
    Privacy: returns no participant identity or directory.
    """
    if not can_access_discovery_plans_and_messages(viewer):
        return None
    current_time = timezone.now()
    plan = (
        Plan.objects.select_related("owner", "owner__profile")
        .annotate(
            joined_count=Count(
                "participations",
                filter=Q(participations__status=Participation.Status.JOINED),
            )
        )
        .filter(pk=plan_id)
        .first()
    )
    if plan is None:
        return None
    is_public = plan.status == Plan.Status.APPROVED and plan.starts_at > current_time
    if plan.owner_id != viewer.pk and not is_public:
        return None

    viewer_participation_status = Participation.objects.filter(
        plan=plan,
        user=viewer,
    ).values_list("status", flat=True).first()
    return {
        "plan": plan,
        "joined_count": plan.joined_count,
        "viewer_participation_status": viewer_participation_status,
    }


def get_unblocked_conversations_for_inbox(user, interest_name=""):
    """Return the account's permitted conversations in recent-activity order.

    Inputs: the server-known signed-in account and an optional controlled interest.
    Returns: an ordered Conversation queryset containing only permitted pairs.
    Changes: none.
    Refuses: every ineligible account with an empty queryset.
    Privacy: removes blocked or ineligible pairs before returning member names.
    """
    if not can_access_discovery_plans_and_messages(user):
        return Conversation.objects.none()

    blocked_by_user = Block.objects.filter(blocker=user).values("blocked_user_id")
    users_blocking_user = Block.objects.filter(blocked_user=user).values("blocker_id")
    conversations = (
        Conversation.objects.select_related(
            "first_user",
            "first_user__profile",
            "second_user",
            "second_user__profile",
        )
        .filter(
            Q(first_user=user) | Q(second_user=user),
            first_user__is_active=True,
            first_user__profile__is_verified=True,
            second_user__is_active=True,
            second_user__profile__is_verified=True,
        )
        .exclude(
            Q(first_user_id__in=blocked_by_user)
            | Q(second_user_id__in=blocked_by_user)
            | Q(first_user_id__in=users_blocking_user)
            | Q(second_user_id__in=users_blocking_user)
        )
    )
    if interest_name:
        conversations = conversations.filter(
            Q(
                first_user_id=user.pk,
                second_user__profile__interests__name=interest_name,
            )
            | Q(
                second_user_id=user.pk,
                first_user__profile__interests__name=interest_name,
            )
        )
    return conversations.order_by("-updated_at", "-pk")


def get_messages_if_user_can_open_conversation(user, conversation_id):
    """Return one permitted conversation and its chronological messages.

    Inputs: the server-known account and an untrusted route conversation ID.
    Returns: a conversation/message mapping, or none for absence or refusal.
    Changes: none.
    Refuses: non-members, ineligible pairs, blocks and missing conversations.
    Privacy: reveals no conversation or message content after any refusal.
    """
    if not can_access_discovery_plans_and_messages(user):
        return None
    conversation = (
        Conversation.objects.select_related(
            "first_user",
            "first_user__profile",
            "second_user",
            "second_user__profile",
        )
        .filter(pk=conversation_id)
        .first()
    )
    if conversation is None or not conversation.includes_account(user):
        return None
    other_user = (
        conversation.second_user
        if conversation.first_user_id == user.pk
        else conversation.first_user
    )
    if not can_start_or_continue_direct_messages(user, other_user):
        return None
    return {
        "conversation": conversation,
        "messages": conversation.messages.select_related("sender").order_by(
            "sent_at",
            "pk",
        ),
    }
