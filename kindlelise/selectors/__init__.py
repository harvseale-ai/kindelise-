"""Expose Kindelise's authorised read operations from one familiar import path."""

# KEYWORD: selector — read-only page code that gathers only the saved information a page needs.
# KEYWORD: query — a request to the database for matching saved information.

# WHY: Re-exports the split selectors so existing views and tests can keep using
# ``from kindlelise.selectors import ...`` without knowing the internal file layout.
from kindlelise.selectors.accounts import (
    get_recent_notifications,
    get_signed_in_user_account_summary,
    get_unread_notification_count,
)
from kindlelise.selectors.discovery import (
    get_profile_image_if_viewer_is_allowed,
    get_profile_page_if_viewer_is_allowed,
    get_profiles_for_discovery_grid,
)
from kindlelise.selectors.messages import (
    get_authorised_plan_chats_for_inbox,
    get_messages_if_user_can_open_conversation,
    get_plan_chat_if_user_can_open,
    get_unblocked_conversations_for_inbox,
)
from kindlelise.selectors.plans import (
    get_pending_plan_requests_for_owner,
    get_plan_page_if_viewer_is_allowed,
    get_plans_for_plan_list,
)
from kindlelise.selectors.safety import (
    get_plan_chat_message_if_reporter_is_allowed,
    get_report_target_profile_if_reporter_is_allowed,
)

# WHY: Lists the supported public selector names so the package boundary stays
# clear when new read operations are added later.
__all__ = [
    "get_authorised_plan_chats_for_inbox",
    "get_messages_if_user_can_open_conversation",
    "get_pending_plan_requests_for_owner",
    "get_plan_chat_if_user_can_open",
    "get_plan_chat_message_if_reporter_is_allowed",
    "get_plan_page_if_viewer_is_allowed",
    "get_plans_for_plan_list",
    "get_profile_image_if_viewer_is_allowed",
    "get_profile_page_if_viewer_is_allowed",
    "get_profiles_for_discovery_grid",
    "get_recent_notifications",
    "get_report_target_profile_if_reporter_is_allowed",
    "get_signed_in_user_account_summary",
    "get_unblocked_conversations_for_inbox",
    "get_unread_notification_count",
]
