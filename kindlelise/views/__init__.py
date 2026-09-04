"""Keep Kindelise page functions available from one familiar import location."""

# =============================================================================
# PAGE MODULE EXPORTS
# Keeps page functions available through the package while their files stay grouped.
# =============================================================================

# -----------------------------------------------------------------------------
# ACCOUNT PAGES
# -----------------------------------------------------------------------------

# WHY: These exports preserve the old ``kindlelise.views`` interface after the file was
# split, so existing imports can keep working while each page group has a clearer home.
from kindlelise.views.accounts import (
    account_page,
    app_guide_page,
    edit_profile_page,
    home_page,
    mark_notifications_read,
    notifications_page,
    profile_image_file,
    sign_in_page,
    sign_out_user,
    sign_up_page,
)

# -----------------------------------------------------------------------------
# PAYMENT PAGES
# -----------------------------------------------------------------------------
from kindlelise.views.billing import (
    open_premium_subscription_portal,
    receive_and_verify_stripe_webhook,
    start_premium_subscription_checkout,
)

# -----------------------------------------------------------------------------
# DISCOVERY PAGES
# -----------------------------------------------------------------------------
from kindlelise.views.discovery import discovery_page, profile_page

# -----------------------------------------------------------------------------
# MESSAGE PAGES
# -----------------------------------------------------------------------------
from kindlelise.views.messages import (
    conversation_page,
    inbox_page,
    plan_chat_page,
    request_conversation_message_edit_suggestion,
    send_conversation_message,
    send_plan_chat_message_view,
    start_direct_conversation,
)

# -----------------------------------------------------------------------------
# PLAN PAGES
# -----------------------------------------------------------------------------
from kindlelise.views.plans import (
    cancel_plan,
    confirm_plan_participation,
    create_plan_page,
    decline_plan_participation,
    edit_plan_page,
    leave_plan,
    plan_detail_page,
    plan_list_page,
    plan_thumbnail_file,
    request_plan_draft,
    request_plan_metadata,
    request_plan_participation,
    withdraw_plan_participation,
)

# -----------------------------------------------------------------------------
# SAFETY PAGES
# -----------------------------------------------------------------------------
from kindlelise.views.safety import (
    block_profile_from_discovery_and_messages,
    report_user_page,
)

# =============================================================================
# PUBLIC PAGE FUNCTIONS
# Lists the page functions other modules are expected to import.
# =============================================================================

# KEYWORD: __all__ — the public names this package deliberately makes available.
# WHY: Listing the supported page functions makes accidental private exports less likely.
__all__ = [
    "account_page",
    "app_guide_page",
    "block_profile_from_discovery_and_messages",
    "cancel_plan",
    "confirm_plan_participation",
    "conversation_page",
    "create_plan_page",
    "decline_plan_participation",
    "discovery_page",
    "edit_plan_page",
    "edit_profile_page",
    "home_page",
    "inbox_page",
    "leave_plan",
    "mark_notifications_read",
    "notifications_page",
    "open_premium_subscription_portal",
    "plan_chat_page",
    "plan_detail_page",
    "plan_list_page",
    "plan_thumbnail_file",
    "profile_image_file",
    "profile_page",
    "receive_and_verify_stripe_webhook",
    "report_user_page",
    "request_conversation_message_edit_suggestion",
    "request_plan_draft",
    "request_plan_metadata",
    "request_plan_participation",
    "send_conversation_message",
    "send_plan_chat_message_view",
    "sign_in_page",
    "sign_out_user",
    "sign_up_page",
    "start_direct_conversation",
    "start_premium_subscription_checkout",
    "withdraw_plan_participation",
]
