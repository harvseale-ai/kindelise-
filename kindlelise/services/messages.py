"""Direct-conversation creation and message-sending workflows."""

# WHY: Keeps private conversation changes together without mixing in page presentation.
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError, transaction
from django.utils import timezone

from kindlelise.models import Conversation, Message, Notification
from kindlelise.policies import can_start_or_continue_direct_messages

# =============================================================================
# CONVERSATION CREATION
# Finds or creates the single permitted conversation between two accounts.
# =============================================================================

# WHY: Keeps the find or start direct conversation steps in one named place so they can be understood, checked, and reused.
def find_or_start_direct_conversation(user, other_user):
    """Store the ordered pair or return its one existing direct conversation.

    Inputs: two server-known Django accounts requesting a direct conversation.
    Returns: the pair's single database-authoritative Conversation.
    Changes: creates the ordered conversation only when it does not already exist.
    Refuses: identical, inactive, unverified or either-direction-blocked accounts.
    Privacy: returns no conversation unless the pair may currently message.
    """
    # WHY: Applies current account and block rules before creating or revealing the pair's conversation.
    if not can_start_or_continue_direct_messages(user, other_user):
        raise PermissionDenied("Direct messaging is not permitted")
    # WHY: Stores the lower account ID first so both people request the exact same database pair.
    first_user, second_user = sorted((user, other_user), key=lambda account: account.pk)
    try:
        # KEYWORD: atomic — either this small database change finishes fully or it is discarded.
        # WHY: Attempts the one database-enforced conversation row inside its own complete change.
        with transaction.atomic():
            return Conversation.objects.create(
                first_user=first_user,
                second_user=second_user,
            )
    # WHY: A simultaneous request may create the row first, so the losing request returns that same row.
    except IntegrityError:
        conversation = Conversation.objects.filter(
            first_user=first_user,
            second_user=second_user,
        ).first()
        if conversation is None:
            # WHY: Re-raises the original database problem when it was not the expected simultaneous creation.
            raise
        # WHY: Both simultaneous callers now receive the same conversation instead of seeing an error.
        return conversation

# =============================================================================
# MESSAGE DELIVERY
# Stores the message, updates inbox order, and creates its notification.
# =============================================================================

# WHY: Stores the message, inbox time and notification as one complete database change.
@transaction.atomic
def send_direct_message(sender, conversation, message_text):
    """Recheck an authorised pair, store plain text and refresh inbox ordering.

    Inputs: the server-known sender/conversation and validated MessageDraftForm text.
    Returns: the newly stored Message.
    Changes: creates one message and updates its conversation activity time.
    Refuses: missing conversations, non-members and ineligible or blocked pairs.
    Privacy: stores text as plain data and never logs or marks it safe.
    """
    # WHY: Refuses a missing or unsaved conversation before current membership is loaded.
    if conversation is None or conversation.pk is None:
        raise PermissionDenied("Direct messaging is not permitted")
    # WHY: Locks and reloads both members so simultaneous messages keep inbox activity ordering consistent.
    try:
        current_conversation = (
            Conversation.objects.select_for_update()
            .select_related("first_user", "second_user")
            .get(pk=conversation.pk)
        )
    except Conversation.DoesNotExist as error:
        raise PermissionDenied("Direct messaging is not permitted") from error
    # WHY: Never accepts the sender identity from the form; it must be a stored member of this pair.
    if not current_conversation.includes_account(sender):
        raise PermissionDenied("Direct messaging is not permitted")

    # WHY: Derives the recipient from the locked conversation rather than a browser-submitted account ID.
    recipient = (
        current_conversation.second_user
        if current_conversation.first_user_id == sender.pk
        else current_conversation.first_user
    )
    # WHY: Rechecks blocks and account access after loading current members because those rules may have changed.
    if not can_start_or_continue_direct_messages(sender, recipient):
        raise PermissionDenied("Direct messaging is not permitted")

    # WHY: Uses one time for the message, inbox ordering, and recipient notification.
    sent_at = timezone.now()
    message = Message.objects.create(
        conversation=current_conversation,
        sender=sender,
        body=message_text,
        sent_at=sent_at,
    )
    # WHY: Moves this conversation to the top of both permitted inboxes after a successful message.
    current_conversation.updated_at = sent_at
    current_conversation.save(update_fields=["updated_at"])
    # WHY: Alerts only the other conversation member and links the alert to this exact message.
    Notification.objects.create(
        recipient=recipient,
        kind=Notification.Kind.MESSAGE,
        message=message,
        created_at=sent_at,
    )
    # WHY: Gives the page the exact saved message and timestamp it should display.
    return message
