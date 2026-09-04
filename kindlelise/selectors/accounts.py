"""Read notifications and private account information."""

from django.db.models import Q

from kindlelise.models import (
    Notification,
    Participation,
    Plan,
    PlatformSubscription,
    Profile,
)

# =============================================================================
# NOTIFICATION READS
# Loads the signed-in person's unread count and recent activity list.
# =============================================================================


# WHY: Removes plan-chat alerts as soon as current owner/confirmed membership no longer permits that chat.
def _notifications_visible_to_user(user):
    return (
        Notification.objects.filter(recipient=user)
        .filter(
            ~Q(kind=Notification.Kind.PLAN_CHAT_MESSAGE)
            | Q(plan_chat_message__chat__plan__owner=user)
            | Q(
                plan_chat_message__chat__plan__participations__user=user,
                plan_chat_message__chat__plan__participations__status=Participation.Status.JOINED,
            )
        )
        .distinct()
    )


# WHY: Finds the unread notification count information in one place so callers receive the same result.
def get_unread_notification_count(user):
    """Return only the signed-in account's unread message and plan activity count."""
    # WHY: Shared templates may run for anonymous pages, which should simply show no badge.
    if not getattr(user, "is_authenticated", False) or not user.is_active:
        return 0

    # WHY: Counts only this recipient's rows that have no recorded reading time.
    return _notifications_visible_to_user(user).filter(read_at__isnull=True).count()


# WHY: Finds the recent notifications information in one place so callers receive the same result.
def get_recent_notifications(user, limit=30):
    """Return the signed-in account's recent alerts with only display-safe context."""
    # WHY: Returns an empty database-shaped result so callers do not need a separate anonymous case.
    if not getattr(user, "is_authenticated", False) or not user.is_active:
        return Notification.objects.none()

    # WHY: Loads only related names and plan details needed to display each permitted alert without extra queries.
    return (
        _notifications_visible_to_user(user)
        .select_related(
            "message__conversation",
            "message__sender__profile",
            "participation__plan",
            "participation__user__profile",
            "plan_chat_message__chat__plan",
            "plan_chat_message__sender__profile",
        )
        # WHY: Shows newest alerts first and uses the row ID to keep equal-time results stable.
        .order_by("-created_at", "-pk")[:limit]
    )


# =============================================================================
# PRIVATE ACCOUNT READS
# Loads the profile, plans, and Premium details owned by the signed-in account.
# =============================================================================


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
            subscription.stripe_customer_id or subscription.stripe_subscription_id
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
