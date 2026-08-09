"""Own the eleven mapped authorised Kindelise read operations."""

# KEYWORD: selector — read-only page code that gathers only the saved information a page needs.
# KEYWORD: query — a request to the database for matching saved information.


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


# WHY: Finds the unread notification count information in one place so callers receive the same result.
def get_unread_notification_count(user):
    """Return only the signed-in account's unread message and plan-join count."""
    # WHY: Shared templates may run for anonymous pages, which should simply show no badge.
    if not getattr(user, "is_authenticated", False) or not user.is_active:
        return 0

    # WHY: Counts only this recipient's rows that have no recorded reading time.
    return Notification.objects.filter(recipient=user, read_at__isnull=True).count()


# WHY: Finds the recent notifications information in one place so callers receive the same result.
def get_recent_notifications(user, limit=30):
    """Return the signed-in account's recent alerts with only display-safe context."""
    # WHY: Returns an empty database-shaped result so callers do not need a separate anonymous case.
    if not getattr(user, "is_authenticated", False) or not user.is_active:
        return Notification.objects.none()

    # WHY: Loads only related names and plan details needed to display each permitted alert without extra queries.
    return (
        Notification.objects.filter(recipient=user)
        .select_related(
            "message__conversation",
            "message__sender__profile",
            "participation__plan",
            "participation__user__profile",
        )
        # WHY: Shows newest alerts first and uses the row ID to keep equal-time results stable.
        .order_by("-created_at", "-pk")[:limit]
    )


# WHY: Finds the signed in user account summary information in one place so callers receive the same result.
def get_signed_in_user_account_summary(user):
    """Return the signed-in account's own profile, plans and subscription summary.

    Inputs: the server-known signed-in Django account.
    Returns: a minimal private account summary, or none when access is refused.
    Changes: none.
    Refuses: anonymous, inactive or missing-profile accounts.
    Privacy: omits reports, webhook receipts and raw Stripe identifiers.
    """
    # WHY: Private account information is available only to its active signed-in owner.
    if not getattr(user, "is_authenticated", False) or not user.is_active:
        return None

    # WHY: Loads the owner's profile and interests together so the page does not query once per interest.
    try:
        profile = Profile.objects.prefetch_related("interests").get(user=user)
    except Profile.DoesNotExist:
        return None

    # WHY: A missing subscription is a normal never-paid state, not an account error.
    subscription = PlatformSubscription.objects.filter(user=user).first()

    # WHY: Starts with the safe free-access presentation before applying any saved Stripe history.
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
        # WHY: Any saved Stripe identity means the one-time first-use trial is no longer new.
        has_stripe_history = bool(
            subscription.stripe_customer_id
            or subscription.stripe_subscription_id
        )
        # WHY: Exposes only page decisions, status, and access time—not raw Stripe identifiers.
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

    # WHY: Returns only the owner's email, profile, own plans, and privacy-minimised subscription summary.
    return {
        "account": {"email": user.email},
        "profile": profile,
        "plans": Plan.objects.filter(owner=user).order_by("-created_at"),
        "subscription": subscription_summary,
    }


# WHY: Finds the profiles for discovery grid information in one place so callers receive the same result.
def get_profiles_for_discovery_grid(viewer, selected_filters):
    """Return only verified, permitted and unblocked discovery profiles.

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
    blocked_by_viewer = Block.objects.filter(blocker=viewer).values(
        "blocked_user_id"
    )
    viewers_blockers = Block.objects.filter(blocked_user=viewer).values(
        "blocker_id"
    )
    # WHY: Filters hidden accounts in the database before names, images, or interests reach presentation code.
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
    Refuses: missing, inactive, unverified and either-direction-blocked targets.
    Privacy: uses the same no-result outcome for absence and every denial reason.
    """
    # WHY: Loads the possible target and its display interests before applying the single page policy.
    profile = (
        Profile.objects.select_related("user")
        .prefetch_related("interests")
        .filter(pk=profile_id)
        .first()
    )
    # WHY: Returns the same empty result for missing, inactive, unverified, and blocked targets.
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


# WHY: Finds the plans for plan list information in one place so callers receive the same result.
def get_plans_for_plan_list(user, *, completed=False):
    """Return current plans, or completed plans relevant to the signed-in account.

    Inputs: the server-known signed-in account and a server-chosen completed flag.
    Returns: an ordered Plan queryset containing only list-visible records.
    Changes: none.
    Refuses: every ineligible account with an empty queryset.
    Privacy: completed plans are limited to plans the account hosted or joined.
    """
    # WHY: Ineligible accounts receive no plan rows rather than partial plan information.
    if not can_access_discovery_plans_and_messages(user):
        return Plan.objects.none()

    # WHY: Uses one current time for every future-plan comparison in this list.
    current_time = timezone.now()

    # WHY: Builds the shared card information once before choosing the current or completed list.
    plans = (
        Plan.objects.select_related("owner")
        # WHY: Counts current participants in the same query without returning their identities.
        .annotate(
            joined_count=Count(
                "participations",
                filter=Q(participations__status=Participation.Status.JOINED),
            )
        )
    )
    if completed:
        # WHY: Treats an approved plan as done once its start time has passed, without adding a second saved status.
        joined_plan_ids = Participation.objects.filter(
            user=user,
            status=Participation.Status.JOINED,
        ).values("plan_id")
        return (
            plans.filter(
                status=Plan.Status.APPROVED,
                starts_at__lte=current_time,
            )
            # WHY: Keeps history personal by showing only plans this account hosted or stayed joined to.
            .filter(Q(owner=user) | Q(pk__in=joined_plan_ids))
            .order_by("-starts_at", "-created_at", "-pk")
        )

    # WHY: Shows future approved plans to everyone while preserving all owner-only review and cancelled states.
    return (
        plans.filter(
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
        # WHY: Orders by meeting time, then creation and row ID for a stable card grid.
        .order_by("starts_at", "created_at", "pk")
    )


# WHY: Finds the plan page if viewer is allowed information in one place so callers receive the same result.
def get_plan_page_if_viewer_is_allowed(viewer, plan_id):
    """Return one visible plan with joined count and the viewer's own state.

    Inputs: the server-known viewer and an untrusted route plan ID.
    Returns: a privacy-minimised plan summary, or none for absence or refusal.
    Changes: none.
    Refuses: ineligible viewers and plans hidden by state or ownership.
    Privacy: returns no participant identity or directory.
    """
    # WHY: Requires the same current account gate as the plan list before looking up a target.
    if not can_access_discovery_plans_and_messages(viewer):
        return None

    # WHY: Uses one current time to decide whether an approved plan is still public.
    current_time = timezone.now()

    # WHY: Loads owner display details and the joined count without loading a participant list.
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
    # WHY: Missing plan IDs use the same no-result path as hidden plan states.
    if plan is None:
        return None
    # WHY: Reads this viewer's own participation before deciding whether a past plan remains visible to them.
    viewer_participation_status = Participation.objects.filter(
        plan=plan,
        user=viewer,
    ).values_list("status", flat=True).first()
    # WHY: A plan is public only while approved and still in the future.
    is_public = plan.status == Plan.Status.APPROVED and plan.starts_at > current_time
    # WHY: A completed plan remains visible only to its owner or someone who stayed joined to it.
    is_completed_for_viewer = (
        plan.status == Plan.Status.APPROVED
        and plan.starts_at <= current_time
        and viewer_participation_status == Participation.Status.JOINED
    )
    if plan.owner_id != viewer.pk and not (is_public or is_completed_for_viewer):
        return None

    # WHY: Returns only this viewer's own participation state, never another participant's identity.
    return {
        "plan": plan,
        "joined_count": plan.joined_count,
        "viewer_participation_status": viewer_participation_status,
    }


# WHY: Finds the unblocked conversations for inbox information in one place so callers receive the same result.
def get_unblocked_conversations_for_inbox(user, interest_name=""):
    """Return the account's permitted conversations in recent-activity order.

    Inputs: the server-known signed-in account and an optional controlled interest.
    Returns: an ordered Conversation queryset containing only permitted pairs.
    Changes: none.
    Refuses: every ineligible account with an empty queryset.
    Privacy: removes blocked or ineligible pairs before returning member names.
    """
    # WHY: Ineligible accounts receive an empty inbox before any other person's profile is loaded.
    if not can_access_discovery_plans_and_messages(user):
        return Conversation.objects.none()

    # WHY: Finds blocks in both directions so a closed pair cannot appear in either inbox.
    blocked_by_user = Block.objects.filter(blocker=user).values("blocked_user_id")
    users_blocking_user = Block.objects.filter(blocked_user=user).values("blocker_id")
    # WHY: Loads both member profiles together and removes inactive, unverified, and blocked pairs in the database.
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
    # WHY: When selected, matches only the other person's controlled interests, never the viewer's own interests.
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
    # WHY: Shows the most recently active conversations first with stable equal-time ordering.
    return conversations.order_by("-updated_at", "-pk")


# WHY: Finds the messages if user can open conversation information in one place so callers receive the same result.
def get_messages_if_user_can_open_conversation(user, conversation_id):
    """Return one permitted conversation and its chronological messages.

    Inputs: the server-known account and an untrusted route conversation ID.
    Returns: a conversation/message mapping, or none for absence or refusal.
    Changes: none.
    Refuses: non-members, ineligible pairs, blocks and missing conversations.
    Privacy: reveals no conversation or message content after any refusal.
    """
    # WHY: Refuses before loading a conversation when the account no longer has social access.
    if not can_access_discovery_plans_and_messages(user):
        return None

    # WHY: Loads both current member profiles so messaging permission can be rechecked now.
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
    # WHY: Missing conversations and non-members receive the same no-result response.
    if conversation is None or not conversation.includes_account(user):
        return None
    # WHY: Selects the other saved member from the ordered pair without accepting a browser-provided recipient.
    other_user = (
        conversation.second_user
        if conversation.first_user_id == user.pk
        else conversation.first_user
    )
    # WHY: Rechecks both accounts and both block directions on every conversation open.
    if not can_start_or_continue_direct_messages(user, other_user):
        return None
    return {
        "conversation": conversation,
        # WHY: Returns messages chronologically and loads each sender in the same database request.
        "messages": conversation.messages.select_related("sender").order_by(
            "sent_at",
            "pk",
        ),
    }
