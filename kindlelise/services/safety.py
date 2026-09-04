"""Directional blocking and private-report workflows."""

# WHY: Keeps protective account changes separate from ordinary social actions.
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.utils import timezone

from kindlelise.models import (
    Block,
    Conversation,
    Message,
    Participation,
    Plan,
    PlanChatMessage,
    Report,
)
from kindlelise.policies import can_report_another_user

# KEYWORD: atomic — the function's database work is kept fully or not kept at all.
# =============================================================================
# BLOCKING
# Records one person's block and closes contact between the two accounts.
# =============================================================================

# WHY: Makes the one directional block as a complete database change.
@transaction.atomic
def block_user_from_discovery_and_messages(blocker, blocked_user):
    """Create the directional block once to close discovery and direct messages.

    Inputs: the authenticated blocker and a server-known different account.
    Returns: the single stored Block for that direction.
    Changes: creates the directional block once and never notifies its target.
    Refuses: anonymous, missing, unsaved and self-targeting accounts.
    Privacy: exposes no block state to the blocked account.
    """
    # WHY: Requires two different saved accounts and permits the decision regardless of current verification state.
    if (
        not getattr(blocker, "is_authenticated", False)
        or getattr(blocker, "pk", None) is None
        or getattr(blocked_user, "pk", None) is None
        or blocker.pk == blocked_user.pk
    ):
        raise PermissionDenied("Blocking is not permitted")
    # WHY: Repeating the action returns the same directional block instead of creating duplicates.
    # KEYWORD: get_or_create — finds the existing row or creates it when it is missing.
    block, _created = Block.objects.get_or_create(
        blocker=blocker,
        blocked_user=blocked_user,
    )
    blocked_at = timezone.now()
    # WHY: An owner blocking a confirmed participant removes that participant from every owned plan immediately.
    participations_to_leave = list(
        Participation.objects.select_for_update().filter(
            user=blocked_user,
            status=Participation.Status.JOINED,
            plan__owner=blocker,
        )
    )
    # WHY: A participant blocking an owner leaves every plan owned by that account immediately.
    participations_to_leave.extend(
        Participation.objects.select_for_update().filter(
            user=blocker,
            status=Participation.Status.JOINED,
            plan__owner=blocked_user,
        )
    )
    # WHY: Between two participants, the person creating the block leaves their shared active future plans.
    participations_to_leave.extend(
        Participation.objects.select_for_update()
        .filter(
            user=blocker,
            status=Participation.Status.JOINED,
            plan__status=Plan.Status.APPROVED,
            plan__starts_at__gt=blocked_at,
            plan__participations__user=blocked_user,
            plan__participations__status=Participation.Status.JOINED,
        )
        .exclude(plan__owner__in=(blocker, blocked_user))
    )
    # WHY: De-duplicates rows reached through more than one relationship before preserving each participation as left.
    for participation in {row.pk: row for row in participations_to_leave}.values():
        participation.status = Participation.Status.LEFT
        participation.left_at = blocked_at
        participation.save(update_fields=["status", "left_at"])
    # WHY: Returns the same block for first and repeated requests so callers have one predictable result.
    return block

# =============================================================================
# PRIVATE REPORTING
# Validates and stores a report and its optional supporting context.
# =============================================================================

# WHY: Checks and stores one private report as a single complete database change.
@transaction.atomic
def submit_private_report_about_user(
    reporter,
    reported_user,
    report_details,
    *,
    reported_plan=None,
    reported_conversation=None,
    reported_message=None,
    reported_plan_chat_message=None,
):
    """Create one private report with at most one validated context reference.

    Inputs: server-known accounts, validated PrivateReportForm values and at most
        one server-retrieved plan, conversation or message.
    Returns: the newly stored Report in received state.
    Changes: creates one private report and no finding, sanction or notification.
    Refuses: self/anonymous reports, multiple contexts and unrelated context.
    Privacy: stores the statement for the reporter and authorised staff only.
    """
    # WHY: Keeps reporting available across blocks while still refusing anonymous, missing, or self targets.
    if not can_report_another_user(reporter, reported_user):
        raise PermissionDenied("Private reporting is not permitted")

    # WHY: Counts server-retrieved context objects so one report cannot combine unrelated evidence.
    supplied_contexts = (
        reported_plan,
        reported_conversation,
        reported_message,
        reported_plan_chat_message,
    )
    if sum(context is not None for context in supplied_contexts) > 1:
        raise PermissionDenied("Only one report context is permitted")

    # WHY: Starts with a valid profile-only report and adds one checked context only when supplied.
    context_values = {}
    if reported_plan is not None:
        # WHY: This branch adds plan evidence only; profile-only reports skip it entirely.
        # WHY: Reloads the plan by saved ID instead of trusting the object passed by a page.
        current_plan = Plan.objects.filter(
            pk=getattr(reported_plan, "pk", None)
        ).first()
        if current_plan is None:
            raise PermissionDenied("Report context is not permitted")
        # WHY: Requires both accounts to be connected to the plan as owner or historical participant.
        reporter_connected = current_plan.owner_id == reporter.pk or (
            Participation.objects.filter(plan=current_plan, user=reporter).exists()
        )
        reported_user_connected = current_plan.owner_id == reported_user.pk or (
            Participation.objects.filter(
                plan=current_plan,
                user=reported_user,
            ).exists()
        )
        if not reporter_connected or not reported_user_connected:
            raise PermissionDenied("Report context is not permitted")
        context_values["reported_plan"] = current_plan

    if reported_conversation is not None:
        # WHY: This branch adds a conversation only when both named people are its exact members.
        # WHY: Accepts conversation context only when its exact two members are reporter and reported account.
        current_conversation = Conversation.objects.filter(
            pk=getattr(reported_conversation, "pk", None)
        ).first()
        if current_conversation is None or {
            current_conversation.first_user_id,
            current_conversation.second_user_id,
        } != {reporter.pk, reported_user.pk}:
            raise PermissionDenied("Report context is not permitted")
        context_values["reported_conversation"] = current_conversation

    if reported_message is not None:
        # WHY: This branch ties the report to one saved message that the reporter was allowed to see.
        # WHY: Loads the message with its conversation so prior pair membership can be checked together.
        current_message = (
            Message.objects.select_related("conversation")
            .filter(pk=getattr(reported_message, "pk", None))
            .first()
        )
        # WHY: Pair membership proves prior visibility without letting a later block suppress reporting.
        if current_message is None or {
            current_message.conversation.first_user_id,
            current_message.conversation.second_user_id,
        } != {reporter.pk, reported_user.pk}:
            raise PermissionDenied("Report context is not permitted")
        context_values["reported_message"] = current_message

    if reported_plan_chat_message is not None:
        # WHY: Reloads the exact group message and proves both authorship and the reporter's current or historical visibility.
        current_plan_chat_message = (
            PlanChatMessage.objects.select_related("chat", "chat__plan")
            .filter(pk=getattr(reported_plan_chat_message, "pk", None))
            .first()
        )
        if (
            current_plan_chat_message is None
            or current_plan_chat_message.sender_id != reported_user.pk
        ):
            raise PermissionDenied("Report context is not permitted")
        plan = current_plan_chat_message.chat.plan
        reporter_participation = Participation.objects.filter(
            plan=plan,
            user=reporter,
        ).first()
        reporter_could_see_message = plan.owner_id == reporter.pk or (
            reporter_participation is not None
            and (
                reporter_participation.status == Participation.Status.JOINED
                or (
                    reporter_participation.joined_at is not None
                    and reporter_participation.joined_at
                    <= current_plan_chat_message.sent_at
                    and (
                        reporter_participation.left_at is None
                        or reporter_participation.left_at
                        >= current_plan_chat_message.sent_at
                    )
                )
            )
        )
        if not reporter_could_see_message:
            raise PermissionDenied("Report context is not permitted")
        context_values["reported_plan_chat_message"] = current_plan_chat_message

    # WHY: Stores the reporter's checked statement as Received without notifying or judging the reported account.
    # WHY: Returns the saved report so the page can confirm that the private report was received.
    return Report.objects.create(
        reporter=reporter,
        reported_user=reported_user,
        category=report_details["category"],
        description=report_details["description"],
        status=Report.Status.RECEIVED,
        **context_values,
    )
