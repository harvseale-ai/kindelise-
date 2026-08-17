"""Read permitted inbox rows and private conversation histories."""

from django.db.models import Q

from kindlelise.models import Block, Conversation
from kindlelise.policies import (
    can_access_discovery_plans_and_messages,
    can_start_or_continue_direct_messages,
)

# =============================================================================
# CONVERSATION READS
# Loads permitted inbox rows and one authorised conversation history.
# =============================================================================


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
