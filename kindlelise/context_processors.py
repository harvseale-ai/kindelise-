"""Expose the small authenticated top-bar notification badge."""

from kindlelise.selectors import get_unread_notification_count


def notification_badge(request):
    """Return the current account's unread activity count for shared templates."""
    return {"unread_notification_count": get_unread_notification_count(request.user)}
