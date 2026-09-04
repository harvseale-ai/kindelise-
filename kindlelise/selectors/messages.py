"""Read permitted inbox rows and private conversation histories."""

from django.db.models import Q
from django.utils import timezone

from kindlelise.models import Block, Conversation, PlanChat
from kindlelise.policies import (
    can_access_discovery_plans_and_messages,
    can_read_plan_chat,
    can_send_plan_chat_message,
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
    # WHY: Loads both member profiles together and removes inactive and blocked pairs in the database.
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
            second_user__is_active=True,
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


# WHY: Lists only plan chats whose membership is currently derived from ownership or confirmed participation.
def get_authorised_plan_chats_for_inbox(user):
    """Return current owner/confirmed plan chats in recent-activity order."""
    if not can_access_discovery_plans_and_messages(user):
        return PlanChat.objects.none()
    return (
        PlanChat.objects.select_related("plan", "plan__owner", "plan__owner__profile")
        .filter(
            Q(plan__owner=user)
            | Q(
                plan__participations__user=user,
                plan__participations__status="joined",
            )
        )
        .distinct()
        .order_by("-updated_at", "-pk")
    )


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


# WHY: Returns one plan chat only after deriving current membership from its plan and participation rows.
def get_plan_chat_if_user_can_open(user, plan_id):
    """Return an authorised plan chat and chronological messages, or none."""
    if not can_access_discovery_plans_and_messages(user):
        return None
    chat = (
        PlanChat.objects.select_related("plan", "plan__owner", "plan__owner__profile")
        .filter(plan_id=plan_id)
        .first()
    )
    at_time = timezone.now()
    if chat is None or not can_read_plan_chat(user, chat, at_time):
        return None
    return {
        "chat": chat,
        "messages": chat.messages.select_related("sender", "sender__profile").order_by(
            "sent_at",
            "pk",
        ),
        "can_send": can_send_plan_chat_message(user, chat, at_time),
    }
