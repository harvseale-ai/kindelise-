"""Preserve one public import point for Kindelise state-changing workflows."""

# =============================================================================
# PUBLIC STATE-CHANGING SERVICES
# Keeps the approved save operations available through one familiar import point.
# =============================================================================

# WHY: These exports keep existing callers working while each workflow has a clearer file.
# WHY: Account pages can keep importing the same service names after the large file was split.
from kindlelise.services.accounts import (
    create_account_and_profile,
    mark_all_notifications_read,
    update_signed_in_user_profile,
)

# WHY: Payment pages receive only the two actions they are allowed to start directly.
from kindlelise.services.billing import (
    open_stripe_customer_portal,
    start_stripe_subscription_checkout,
)

# WHY: Conversation pages share one public route to the two message-changing actions.
from kindlelise.services.messages import (
    find_or_start_direct_conversation,
    send_direct_message,
    send_plan_chat_message,
)

# WHY: Plan pages can find every plan-changing action together under the original import path.
from kindlelise.services.plans import (
    cancel_owned_plan_and_hide_it_from_discovery,
    confirm_requested_plan_participation,
    create_available_plan,
    decline_requested_plan_participation,
    leave_plan_and_keep_participation_history,
    request_plan_participation_and_open_owner_conversation,
    update_owned_plan_before_first_join,
    withdraw_pending_plan_participation,
)

# WHY: Blocking and reporting stay available without exposing their private helper details.
from kindlelise.services.safety import (
    block_user_from_discovery_and_messages,
    submit_private_report_about_user,
)

# WHY: The webhook view needs one carefully checked entry point for changing Premium access.
from kindlelise.services.stripe_events import (
    update_premium_access_from_verified_stripe_event,
)

# =============================================================================
# PUBLIC SERVICE NAMES
# Lists the state-changing functions other modules are expected to import.
# =============================================================================

# KEYWORD: __all__ — the public names this package deliberately makes available.
# WHY: Prevents the many private Stripe parsing helpers becoming accidental public services.
__all__ = [
    "block_user_from_discovery_and_messages",
    "cancel_owned_plan_and_hide_it_from_discovery",
    "confirm_requested_plan_participation",
    "create_account_and_profile",
    "create_available_plan",
    "find_or_start_direct_conversation",
    "decline_requested_plan_participation",
    "leave_plan_and_keep_participation_history",
    "mark_all_notifications_read",
    "open_stripe_customer_portal",
    "request_plan_participation_and_open_owner_conversation",
    "send_direct_message",
    "send_plan_chat_message",
    "start_stripe_subscription_checkout",
    "submit_private_report_about_user",
    "update_owned_plan_before_first_join",
    "update_premium_access_from_verified_stripe_event",
    "update_signed_in_user_profile",
    "withdraw_pending_plan_participation",
]
