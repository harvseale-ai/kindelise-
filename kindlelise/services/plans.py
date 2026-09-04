"""Plan creation, editing, participation, and cancellation workflows."""

# WHY: Keeps every saved change in a plan's life together from creation to cancellation.
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.utils import timezone

from kindlelise.models import Notification, Participation, Plan, PlanChat
from kindlelise.policies import (
    can_access_discovery_plans_and_messages,
    can_confirm_plan_participation,
    can_create_plan,
    can_request_plan_participation,
)
from kindlelise.services.messages import find_or_start_direct_conversation

# KEYWORD: atomic — all database changes in the function are kept together or rolled back together.
# =============================================================================
# PLAN CREATION
# Saves a complete new plan and its optional fetched image.
# =============================================================================

# WHY: Keeps every starting plan value together so a partly created plan cannot be shown.
@transaction.atomic
def create_available_plan(owner, plan_details):
    """Create an immediately available plan owned by an eligible account.

    Inputs: the server-known owner and validated PlanDetailsForm values.
    Returns: the newly created available Plan.
    Changes: creates one approved plan with no first-join lock state.
    Refuses: every account that lacks current plan access.
    Privacy: ignores browser-supplied owner, status and approval fields.
    """
    # WHY: Rechecks current account access here even if the page already hid the creation form.
    if not can_create_plan(owner):
        raise PermissionDenied("Current account access is required")

    # WHY: Copies only public meeting fields and ignores browser attempts to choose owner, status, or approver.
    editable_fields = (
        "title",
        "description",
        "public_place",
        "public_address",
        "public_url",
        "starts_at",
        "capacity",
    )
    values = {field: plan_details[field] for field in editable_fields}
    # WHY: Adds a thumbnail only when the server produced a trusted validated image file.
    thumbnail_image = plan_details.get("thumbnail_image")
    if thumbnail_image:
        values["thumbnail_image"] = thumbnail_image
    # WHY: Makes a newly valid plan immediately available while recording the owner as its initial approver.
    # WHY: Returns the saved plan immediately so the page can redirect to its new detail address.
    return Plan.objects.create(
        owner=owner,
        status=Plan.Status.APPROVED,
        approved_at=timezone.now(),
        approved_by=owner,
        meeting_details_locked_at=None,
        **values,
    )

# =============================================================================
# PLAN EDITING
# Saves owner changes while meeting details are still editable.
# =============================================================================

# WHY: Keeps the plan edit and its renewed available state together as one database change.
@transaction.atomic
def update_owned_plan_before_first_join(owner, plan, plan_changes):
    """Edit an owned non-cancelled plan only before its first successful join.

    Inputs: the server-known owner/plan and validated PlanDetailsForm values.
    Returns: the freshly locked and updated Plan.
    Changes: edits plan details and activates a revised legacy rejected plan.
    Refuses: ineligible/non-owners and every locked or cancelled plan.
    Privacy: ignores browser-supplied ownership, status, approval and lock fields.
    """
    # WHY: Requires current plan access and a real saved plan before any row is locked.
    if not can_create_plan(owner) or plan is None or plan.pk is None:
        raise PermissionDenied("Plan editing is not permitted")

    # WHY: Reloads and locks current database state rather than trusting an older page copy.
    try:
        current_plan = Plan.objects.select_for_update().get(pk=plan.pk)
    except Plan.DoesNotExist as error:
        raise PermissionDenied("Plan editing is not permitted") from error
    # WHY: Checks ownership from the locked plan and keeps joined or cancelled plans read-only.
    if current_plan.owner_id != owner.pk:
        raise PermissionDenied("Plan editing is not permitted")
    if current_plan.meeting_details_locked_at is not None:
        raise PermissionDenied("Joined plans are read-only")
    if current_plan.status == Plan.Status.CANCELLED:
        raise PermissionDenied("Cancelled plans are terminal")

    # WHY: Keeps editable meeting facts separate from protected lifecycle and ownership fields.
    editable_fields = (
        "title",
        "description",
        "public_place",
        "public_address",
        "public_url",
        "starts_at",
        "capacity",
    )
    # WHY: A rejected legacy plan becomes available again only when its owner deliberately submits an edit.
    activate_revised_plan = current_plan.status == Plan.Status.REJECTED
    changed_fields = []
    # WHY: Keeps the old thumbnail until the updated plan has committed successfully.
    old_thumbnail_name = current_plan.thumbnail_image.name
    new_thumbnail = plan_changes.get("thumbnail_image")
    if new_thumbnail:
        current_plan.thumbnail_image = new_thumbnail
        changed_fields.append("thumbnail_image")
    # WHY: Applies only submitted allowed fields and leaves absent fields unchanged.
    for field_name in editable_fields:
        if field_name not in plan_changes:
            continue
        current_value = getattr(current_plan, field_name)
        submitted_value = plan_changes[field_name]
        values_differ = current_value != submitted_value
        if field_name == "starts_at":
            # WHY: The picker omits hidden microseconds, so that formatting loss is not treated as a real edit.
            values_differ = current_value.replace(microsecond=0) != (
                submitted_value.replace(microsecond=0)
            )
            if not values_differ:
                submitted_value = current_value
        setattr(current_plan, field_name, submitted_value)
        changed_fields.append(field_name)

    # WHY: Records a fresh available state, time, and owner approval for the deliberately revised plan.
    if activate_revised_plan:
        current_plan.status = Plan.Status.APPROVED
        current_plan.approved_at = timezone.now()
        current_plan.approved_by = owner
        changed_fields.extend(["status", "approved_at", "approved_by"])
    # WHY: Saves only touched fields and removes the old stored thumbnail only after commit.
    if changed_fields:
        current_plan.save(update_fields=dict.fromkeys(changed_fields))
        if old_thumbnail_name and "thumbnail_image" in changed_fields:
            thumbnail_storage = current_plan.thumbnail_image.storage
            transaction.on_commit(
                lambda storage=thumbnail_storage, name=old_thumbnail_name: storage.delete(name)
            )
    # WHY: Returns the locked current version, not the older plan object passed in by the page.
    return current_plan

# =============================================================================
# PLAN PARTICIPATION
# Handles requests, owner decisions and leaving while preserving participation history.
# =============================================================================

# WHY: Stores the pending request and its private owner conversation as one deliberate workflow.
@transaction.atomic
def request_plan_participation_and_open_owner_conversation(user, plan):
    """Request participation and return the existing or new owner conversation.

    Inputs: the server-known account and plan selected by the request.
    Returns: the pending Participation and authorised direct Conversation.
    Changes: creates or resets one request and alerts the owner.
    Refuses: every current eligibility, ownership, block, state, time or capacity denial.
    Privacy: accepts no requester or owner identity from the browser.
    """
    if plan is None or plan.pk is None:
        raise PermissionDenied("Plan participation cannot be requested")
    try:
        current_plan = Plan.objects.select_for_update().get(pk=plan.pk)
    except Plan.DoesNotExist as error:
        raise PermissionDenied("Plan participation cannot be requested") from error

    requested_at = timezone.now()
    if not can_request_plan_participation(user, current_plan, requested_at):
        raise PermissionDenied("Plan participation cannot be requested")

    # WHY: Locks and reuses the one historical row after a decline or departure instead of creating duplicates.
    participation = Participation.objects.select_for_update().filter(
        plan=current_plan,
        user=user,
    ).first()
    if participation is None:
        participation = Participation.objects.create(
            plan=current_plan,
            user=user,
            status=Participation.Status.PENDING,
            requested_at=requested_at,
            joined_at=None,
            decided_at=None,
            left_at=None,
        )
    else:
        participation.status = Participation.Status.PENDING
        participation.requested_at = requested_at
        participation.joined_at = None
        participation.decided_at = None
        participation.left_at = None
        participation.save(
            update_fields=[
                "status",
                "requested_at",
                "joined_at",
                "decided_at",
                "left_at",
            ]
        )

    # WHY: Reuses the existing safe pair conversation instead of adding a request-specific messaging system.
    conversation = find_or_start_direct_conversation(user, current_plan.owner)
    Notification.objects.create(
        recipient=current_plan.owner,
        kind=Notification.Kind.PLAN_REQUEST,
        participation=participation,
        created_at=requested_at,
    )
    return participation, conversation


# WHY: Confirms one exact pending request under the same lock that protects capacity and meeting details.
@transaction.atomic
def confirm_requested_plan_participation(owner, plan, participation_id):
    """Confirm one pending request without allowing capacity races."""
    if plan is None or plan.pk is None:
        raise PermissionDenied("Plan participation cannot be confirmed")
    try:
        current_plan = Plan.objects.select_for_update().get(pk=plan.pk)
    except Plan.DoesNotExist as error:
        raise PermissionDenied("Plan participation cannot be confirmed") from error
    participation = (
        Participation.objects.select_for_update()
        .select_related("user", "plan")
        .filter(pk=participation_id, plan=current_plan)
        .first()
    )
    decided_at = timezone.now()
    if not can_confirm_plan_participation(owner, participation, decided_at):
        raise PermissionDenied("Plan participation cannot be confirmed")

    participation.status = Participation.Status.JOINED
    participation.joined_at = decided_at
    participation.decided_at = decided_at
    participation.left_at = None
    participation.save(
        update_fields=["status", "joined_at", "decided_at", "left_at"]
    )
    if current_plan.meeting_details_locked_at is None:
        current_plan.meeting_details_locked_at = decided_at
        current_plan.save(update_fields=["meeting_details_locked_at"])
    # WHY: The first confirmation creates the plan's one shared chat; later confirmations reuse it.
    chat, _created = PlanChat.objects.get_or_create(plan=current_plan)
    Notification.objects.create(
        recipient=participation.user,
        kind=Notification.Kind.PLAN_CONFIRMED,
        participation=participation,
        created_at=decided_at,
    )
    return participation, chat


# WHY: Lets only the owner close one pending request without changing capacity or meeting details.
@transaction.atomic
def decline_requested_plan_participation(owner, plan, participation_id):
    """Decline one pending request belonging to the owner's plan."""
    if plan is None or plan.pk is None or not can_access_discovery_plans_and_messages(owner):
        raise PermissionDenied("Plan participation cannot be declined")
    try:
        current_plan = Plan.objects.select_for_update().get(pk=plan.pk)
    except Plan.DoesNotExist as error:
        raise PermissionDenied("Plan participation cannot be declined") from error
    participation = (
        Participation.objects.select_for_update()
        .select_related("user")
        .filter(
            pk=participation_id,
            plan=current_plan,
            status=Participation.Status.PENDING,
        )
        .first()
    )
    if participation is None or current_plan.owner_id != owner.pk:
        raise PermissionDenied("Plan participation cannot be declined")
    decided_at = timezone.now()
    participation.status = Participation.Status.DECLINED
    participation.joined_at = None
    participation.decided_at = decided_at
    participation.left_at = None
    participation.save(
        update_fields=["status", "joined_at", "decided_at", "left_at"]
    )
    Notification.objects.create(
        recipient=participation.user,
        kind=Notification.Kind.PLAN_DECLINED,
        participation=participation,
        created_at=decided_at,
    )
    return participation


# WHY: Lets a requester remove only their own pending request before the owner decides it.
@transaction.atomic
def withdraw_pending_plan_participation(user, plan):
    """Withdraw the caller's pending request while retaining its history row."""
    if plan is None or not can_access_discovery_plans_and_messages(user):
        raise PermissionDenied("Plan participation cannot be withdrawn")
    participation = (
        Participation.objects.select_for_update()
        .filter(plan=plan, user=user, status=Participation.Status.PENDING)
        .first()
    )
    if participation is None:
        raise PermissionDenied("Pending participation is required")
    withdrawn_at = timezone.now()
    participation.status = Participation.Status.LEFT
    participation.joined_at = None
    participation.decided_at = withdrawn_at
    participation.left_at = withdrawn_at
    participation.save(
        update_fields=["status", "joined_at", "decided_at", "left_at"]
    )
    return participation

# WHY: Saves leaving as one complete change while deliberately keeping the original join history.
@transaction.atomic
def leave_plan_and_keep_participation_history(user, plan):
    """Mark current participation left while preserving its row and plan lock.

    Inputs: the server-known account and plan selected by the request.
    Returns: the preserved Participation in left state.
    Changes: sets status left and records the departure time.
    Refuses: ineligible accounts and every non-current participation.
    Privacy: changes only the caller's own participation row.
    """
    # WHY: Requires a real plan and current social access before looking for participation.
    if plan is None or not can_access_discovery_plans_and_messages(user):
        raise PermissionDenied("Plan leaving is not permitted")
    # WHY: Locks only this account's currently joined row so a repeated leave cannot race with another action.
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
        # WHY: Stops repeated leave requests or requests from somebody who never joined.
        raise PermissionDenied("Current participation is required")
    # WHY: Changes state and records the ending time while preserving who joined and when.
    participation.status = Participation.Status.LEFT
    participation.left_at = timezone.now()
    participation.save(update_fields=["status", "left_at"])
    # WHY: Returns the preserved row so the page can show that participation is now finished.
    return participation

# =============================================================================
# PLAN CANCELLATION
# Closes an owned plan and retains its participation history.
# =============================================================================

# WHY: Saves every cancellation value together so the plan cannot remain partly approved.
@transaction.atomic
def cancel_owned_plan_and_hide_it_from_discovery(owner, plan):
    """Cancel an owned plan while preserving it and every participation row.

    Inputs: the server-known owner and plan selected by the request.
    Returns: the freshly locked cancelled Plan.
    Changes: sets terminal cancelled state and clears current approval fields.
    Refuses: ineligible/non-owners, missing plans and already-cancelled plans.
    Privacy: changes no participation and exposes no participant identity.
    """
    # WHY: Requires current access and a real saved target before reloading current state.
    if not can_create_plan(owner) or plan is None or plan.pk is None:
        raise PermissionDenied("Plan cancellation is not permitted")
    # WHY: Locks the plan so another edit, join, or cancellation cannot interleave with this change.
    try:
        current_plan = Plan.objects.select_for_update().get(pk=plan.pk)
    except Plan.DoesNotExist as error:
        raise PermissionDenied("Plan cancellation is not permitted") from error
    # WHY: Only the saved owner can cancel; a plan ID from the browser never proves ownership.
    if current_plan.owner_id != owner.pk:
        raise PermissionDenied("Plan cancellation is not permitted")
    # WHY: Repeating a final cancellation is refused rather than changing its history again.
    if current_plan.status == Plan.Status.CANCELLED:
        raise PermissionDenied("Cancelled plans are terminal")

    # WHY: Cancellation is terminal and clears approval evidence while preserving the plan and participation history.
    current_plan.status = Plan.Status.CANCELLED
    current_plan.approved_at = None
    current_plan.approved_by = None
    current_plan.save(update_fields=["status", "approved_at", "approved_by"])
    # WHY: Returns the locked cancelled version so callers do not keep using stale plan state.
    return current_plan
