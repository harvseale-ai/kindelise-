"""Expose the small authenticated top-bar notification badge."""

# KEYWORD: context processor — a small helper that makes the same value available to every page template.


from kindlelise.selectors import get_unread_notification_count

# =============================================================================
# SHARED NOTIFICATION BADGE
# Makes the unread count available to the top bar on every page.
# =============================================================================

# WHY: Keeps the notification badge steps in one named place so they can be understood, checked, and reused.
def notification_badge(request):
    """Return the current account's unread activity count for shared templates."""
    # WHY: Uses one authorised count helper so every top bar follows the same sign-in and privacy rules.
    return {"unread_notification_count": get_unread_notification_count(request.user)}
