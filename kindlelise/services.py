"""Own the fourteen mapped state-changing Kindlelise workflows."""

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError, transaction
from django.utils import timezone

from kindlelise.models import (
    Block,
    Conversation,
    Message,
    Participation,
    Plan,
    Profile,
    Report,
)
from kindlelise.policies import (
    can_access_discovery_plans_and_messages,
    can_create_plan_for_staff_review,
    can_join_approved_plan,
    can_report_another_user,
    can_start_or_continue_direct_messages,
)


@transaction.atomic
def create_account_and_profile(new_account_details):
    """Create one Django account and its empty unverified profile atomically.

    Inputs: validated AccountSignUpForm values containing username and password1.
    Returns: the newly created Django account.
    Changes: creates one account and exactly one empty unverified profile.
    Refuses: invalid or duplicate values through normal Django database errors.
    Privacy: hashes the password through Django and ignores every extra field.
    """
    account = get_user_model().objects.create_user(
        username=new_account_details["username"],
        password=new_account_details["password1"],
    )
    Profile.objects.create(user=account)
    return account


@transaction.atomic
def update_signed_in_user_profile(user, profile_changes):
    """Update only the signed-in account's permitted profile fields.

    Inputs: the server-known account and validated ProfileDetailsForm values.
    Returns: the updated profile.
    Changes: replaces supplied public profile fields, interests and availability.
    Refuses: anonymous, inactive or missing-profile accounts.
    Privacy: ignores verification, subscription, ownership and every extra field.
    """
    if not getattr(user, "is_authenticated", False) or not user.is_active:
        raise PermissionDenied("A signed-in active account is required")

    try:
        profile = Profile.objects.get(user=user)
    except Profile.DoesNotExist as error:
        raise PermissionDenied("A profile is required") from error

    scalar_fields = (
        "display_name",
        "biography",
        "broad_area",
        "available_until",
    )
    changed_fields = []
    for field_name in scalar_fields:
        if field_name in profile_changes:
            setattr(profile, field_name, profile_changes[field_name])
            changed_fields.append(field_name)

    if changed_fields:
        profile.save(update_fields=changed_fields)
    if "interests" in profile_changes:
        profile.interests.set(profile_changes["interests"])
    return profile


@transaction.atomic
def create_plan_waiting_for_staff_review(owner, plan_details):
    """Create a pending plan owned by an account eligible for staff review.

    Inputs: the server-known owner and validated PlanDetailsForm values.
    Returns: the newly created pending Plan.
    Changes: creates one plan with no approval or first-join lock state.
    Refuses: every account that lacks current plan access.
    Privacy: ignores browser-supplied owner, status and staff-review fields.
    """
    if not can_create_plan_for_staff_review(owner):
        raise PermissionDenied("Current verification is required")

    editable_fields = (
        "title",
        "description",
        "public_place",
        "public_url",
        "starts_at",
        "capacity",
    )
    values = {field: plan_details[field] for field in editable_fields}
    return Plan.objects.create(
        owner=owner,
        status=Plan.Status.PENDING,
        approved_at=None,
        approved_by=None,
        meeting_details_locked_at=None,
        **values,
    )


@transaction.atomic
def update_owned_plan_before_first_join(owner, plan, plan_changes):
    """Edit an owned non-cancelled plan only before its first successful join.

    Inputs: the server-known owner/plan and validated PlanDetailsForm values.
    Returns: the freshly locked and updated Plan.
    Changes: edits plan details and resets review state when the contract requires.
    Refuses: ineligible/non-owners and every locked or cancelled plan.
    Privacy: ignores browser-supplied ownership, status, review and lock fields.
    """
    if not can_create_plan_for_staff_review(owner) or plan is None or plan.pk is None:
        raise PermissionDenied("Plan editing is not permitted")

    try:
        current_plan = Plan.objects.select_for_update().get(pk=plan.pk)
    except Plan.DoesNotExist as error:
        raise PermissionDenied("Plan editing is not permitted") from error
    if current_plan.owner_id != owner.pk:
        raise PermissionDenied("Plan editing is not permitted")
    if current_plan.meeting_details_locked_at is not None:
        raise PermissionDenied("Joined plans are read-only")
    if current_plan.status == Plan.Status.CANCELLED:
        raise PermissionDenied("Cancelled plans are terminal")

    editable_fields = (
        "title",
        "description",
        "public_place",
        "public_url",
        "starts_at",
        "capacity",
    )
    review_fields = {"public_place", "public_url", "starts_at"}
    review_reset_required = current_plan.status == Plan.Status.REJECTED
    changed_fields = []
    for field_name in editable_fields:
        if field_name not in plan_changes:
            continue
        if (
            current_plan.status == Plan.Status.APPROVED
            and field_name in review_fields
            and getattr(current_plan, field_name) != plan_changes[field_name]
        ):
            review_reset_required = True
        setattr(current_plan, field_name, plan_changes[field_name])
        changed_fields.append(field_name)

    if review_reset_required:
        current_plan.status = Plan.Status.PENDING
        current_plan.approved_at = None
        current_plan.approved_by = None
        changed_fields.extend(["status", "approved_at", "approved_by"])
    if changed_fields:
        current_plan.save(update_fields=dict.fromkeys(changed_fields))
    return current_plan


@transaction.atomic
def join_approved_plan_and_lock_meeting_details(user, plan):
    """Join an approved plan and set its permanent first-join lock atomically.

    Inputs: the server-known account and plan selected by the request.
    Returns: the newly created or reactivated Participation.
    Changes: joins one participant and sets the plan lock on the first join.
    Refuses: every current eligibility, ownership, state, time or capacity denial.
    Privacy: recounts participation without returning other participant identities.
    """
    if plan is None or plan.pk is None:
        raise PermissionDenied("Plan joining is not permitted")
    try:
        current_plan = Plan.objects.select_for_update().get(pk=plan.pk)
    except Plan.DoesNotExist as error:
        raise PermissionDenied("Plan joining is not permitted") from error

    joined_at = timezone.now()
    if not can_join_approved_plan(user, current_plan, joined_at):
        raise PermissionDenied("Plan joining is not permitted")

    participation = Participation.objects.filter(
        plan=current_plan,
        user=user,
    ).first()
    if participation is None:
        participation = Participation.objects.create(
            plan=current_plan,
            user=user,
            status=Participation.Status.JOINED,
            joined_at=joined_at,
            left_at=None,
        )
    else:
        participation.status = Participation.Status.JOINED
        participation.joined_at = joined_at
        participation.left_at = None
        participation.save(update_fields=["status", "joined_at", "left_at"])

    if current_plan.meeting_details_locked_at is None:
        current_plan.meeting_details_locked_at = joined_at
        current_plan.save(update_fields=["meeting_details_locked_at"])
    return participation


@transaction.atomic
def leave_plan_and_keep_participation_history(user, plan):
    """Mark current participation left while preserving its row and plan lock.

    Inputs: the server-known account and plan selected by the request.
    Returns: the preserved Participation in left state.
    Changes: sets status left and records the departure time.
    Refuses: ineligible accounts and every non-current participation.
    Privacy: changes only the caller's own participation row.
    """
    if plan is None or not can_access_discovery_plans_and_messages(user):
        raise PermissionDenied("Plan leaving is not permitted")
    participation = (
        Participation.objects.select_for_update()
        .filter(
            plan=plan,
            user=user,
            status=Participation.Status.JOINED,
        )
        .first()
    )
    if participation is None:
        raise PermissionDenied("Current participation is required")
    participation.status = Participation.Status.LEFT
    participation.left_at = timezone.now()
    participation.save(update_fields=["status", "left_at"])
    return participation


@transaction.atomic
def cancel_owned_plan_and_hide_it_from_discovery(owner, plan):
    """Cancel an owned plan while preserving it and every participation row.

    Inputs: the server-known owner and plan selected by the request.
    Returns: the freshly locked cancelled Plan.
    Changes: sets terminal cancelled state and clears current approval fields.
    Refuses: ineligible/non-owners, missing plans and already-cancelled plans.
    Privacy: changes no participation and exposes no participant identity.
    """
    if not can_create_plan_for_staff_review(owner) or plan is None or plan.pk is None:
        raise PermissionDenied("Plan cancellation is not permitted")
    try:
        current_plan = Plan.objects.select_for_update().get(pk=plan.pk)
    except Plan.DoesNotExist as error:
        raise PermissionDenied("Plan cancellation is not permitted") from error
    if current_plan.owner_id != owner.pk:
        raise PermissionDenied("Plan cancellation is not permitted")
    if current_plan.status == Plan.Status.CANCELLED:
        raise PermissionDenied("Cancelled plans are terminal")

    current_plan.status = Plan.Status.CANCELLED
    current_plan.approved_at = None
    current_plan.approved_by = None
    current_plan.save(update_fields=["status", "approved_at", "approved_by"])
    return current_plan


def find_or_start_direct_conversation(user, other_user):
    """Store the ordered pair or return its one existing direct conversation.

    Inputs: two server-known Django accounts requesting a direct conversation.
    Returns: the pair's single database-authoritative Conversation.
    Changes: creates the ordered conversation only when it does not already exist.
    Refuses: identical, inactive, unverified or either-direction-blocked accounts.
    Privacy: returns no conversation unless the pair may currently message.
    """
    if not can_start_or_continue_direct_messages(user, other_user):
        raise PermissionDenied("Direct messaging is not permitted")
    first_user, second_user = sorted((user, other_user), key=lambda account: account.pk)
    try:
        with transaction.atomic():
            return Conversation.objects.create(
                first_user=first_user,
                second_user=second_user,
            )
    except IntegrityError:
        conversation = Conversation.objects.filter(
            first_user=first_user,
            second_user=second_user,
        ).first()
        if conversation is None:
            raise
        return conversation


@transaction.atomic
def send_direct_message(sender, conversation, message_text):
    """Recheck an authorised pair, store plain text and refresh inbox ordering.

    Inputs: the server-known sender/conversation and validated MessageDraftForm text.
    Returns: the newly stored Message.
    Changes: creates one message and updates its conversation activity time.
    Refuses: missing conversations, non-members and ineligible or blocked pairs.
    Privacy: stores text as plain data and never logs or marks it safe.
    """
    if conversation is None or conversation.pk is None:
        raise PermissionDenied("Direct messaging is not permitted")
    try:
        current_conversation = (
            Conversation.objects.select_for_update()
            .select_related("first_user", "second_user")
            .get(pk=conversation.pk)
        )
    except Conversation.DoesNotExist as error:
        raise PermissionDenied("Direct messaging is not permitted") from error
    if not current_conversation.includes_account(sender):
        raise PermissionDenied("Direct messaging is not permitted")

    recipient = (
        current_conversation.second_user
        if current_conversation.first_user_id == sender.pk
        else current_conversation.first_user
    )
    if not can_start_or_continue_direct_messages(sender, recipient):
        raise PermissionDenied("Direct messaging is not permitted")

    sent_at = timezone.now()
    message = Message.objects.create(
        conversation=current_conversation,
        sender=sender,
        body=message_text,
        sent_at=sent_at,
    )
    current_conversation.updated_at = sent_at
    current_conversation.save(update_fields=["updated_at"])
    return message


@transaction.atomic
def block_user_from_discovery_and_messages(blocker, blocked_user):
    """Create the directional block once to close discovery and direct messages.

    Inputs: the authenticated blocker and a server-known different account.
    Returns: the single stored Block for that direction.
    Changes: creates the directional block once and never notifies its target.
    Refuses: anonymous, missing, unsaved and self-targeting accounts.
    Privacy: exposes no block state to the blocked account.
    """
    if (
        not getattr(blocker, "is_authenticated", False)
        or getattr(blocker, "pk", None) is None
        or getattr(blocked_user, "pk", None) is None
        or blocker.pk == blocked_user.pk
    ):
        raise PermissionDenied("Blocking is not permitted")
    block, _created = Block.objects.get_or_create(
        blocker=blocker,
        blocked_user=blocked_user,
    )
    return block


@transaction.atomic
def submit_private_report_about_user(
    reporter,
    reported_user,
    report_details,
    *,
    reported_plan=None,
    reported_conversation=None,
    reported_message=None,
):
    """Create one private report with at most one validated context reference.

    Inputs: server-known accounts, validated PrivateReportForm values and at most
        one server-retrieved plan, conversation or message.
    Returns: the newly stored Report in received state.
    Changes: creates one private report and no finding, sanction or notification.
    Refuses: self/anonymous reports, multiple contexts and unrelated context.
    Privacy: stores the statement for the reporter and authorised staff only.
    """
    if not can_report_another_user(reporter, reported_user):
        raise PermissionDenied("Private reporting is not permitted")

    supplied_contexts = (
        reported_plan,
        reported_conversation,
        reported_message,
    )
    if sum(context is not None for context in supplied_contexts) > 1:
        raise PermissionDenied("Only one report context is permitted")

    context_values = {}
    if reported_plan is not None:
        current_plan = Plan.objects.filter(
            pk=getattr(reported_plan, "pk", None)
        ).first()
        if current_plan is None:
            raise PermissionDenied("Report context is not permitted")
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
        current_message = (
            Message.objects.select_related("conversation")
            .filter(pk=getattr(reported_message, "pk", None))
            .first()
        )
        # Pair membership proves prior visibility without letting a later block
        # suppress the separate reporting path.
        if current_message is None or {
            current_message.conversation.first_user_id,
            current_message.conversation.second_user_id,
        } != {reporter.pk, reported_user.pk}:
            raise PermissionDenied("Report context is not permitted")
        context_values["reported_message"] = current_message

    return Report.objects.create(
        reporter=reporter,
        reported_user=reported_user,
        category=report_details["category"],
        description=report_details["description"],
        status=Report.Status.RECEIVED,
        **context_values,
    )
