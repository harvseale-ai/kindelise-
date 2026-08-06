"""Own the fourteen mapped state-changing Kindlelise workflows."""

from collections.abc import Mapping
from datetime import datetime, timezone as datetime_timezone
from urllib.parse import urlsplit

import stripe
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone

from kindlelise.models import (
    Block,
    Conversation,
    Message,
    Participation,
    Plan,
    PlatformSubscription,
    Profile,
    Report,
    StripeWebhookReceipt,
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

    Inputs: validated AccountSignUpForm values containing email and password1.
    Returns: the newly created Django account.
    Changes: creates one account and exactly one empty unverified profile.
    Refuses: invalid or duplicate values through normal Django database errors.
    Privacy: hashes the password through Django and ignores every extra field.
    """
    email = new_account_details["email"]
    account = get_user_model().objects.create_user(
        username=email,
        email=email,
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
        profile = Profile.objects.select_for_update().get(user=user)
    except Profile.DoesNotExist as error:
        raise PermissionDenied("A profile is required") from error

    scalar_fields = (
        "display_name",
        "title_statement",
        "biography",
        "broad_area",
        "broad_areas",
        "availability_start",
        "available_from",
    )
    changed_fields = []

    old_image_name = profile.profile_image.name
    new_image = profile_changes.get("profile_image")
    if new_image and getattr(new_image, "name", "") != old_image_name:
        profile.profile_image = new_image
        changed_fields.append("profile_image")
    for field_name in scalar_fields:
        if field_name in profile_changes:
            setattr(profile, field_name, profile_changes[field_name])
            changed_fields.append(field_name)

    if changed_fields:
        profile.save(update_fields=changed_fields)
        if old_image_name and "profile_image" in changed_fields:
            image_storage = profile.profile_image.storage
            transaction.on_commit(
                lambda storage=image_storage, name=old_image_name: storage.delete(name)
            )
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
    thumbnail_image = plan_details.get("thumbnail_image")
    if thumbnail_image:
        values["thumbnail_image"] = thumbnail_image
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
    old_thumbnail_name = current_plan.thumbnail_image.name
    new_thumbnail = plan_changes.get("thumbnail_image")
    if new_thumbnail:
        current_plan.thumbnail_image = new_thumbnail
        changed_fields.append("thumbnail_image")
    for field_name in editable_fields:
        if field_name not in plan_changes:
            continue
        current_value = getattr(current_plan, field_name)
        submitted_value = plan_changes[field_name]
        values_differ = current_value != submitted_value
        if field_name == "starts_at":
            # The picker omits database microseconds; that formatting loss is
            # not a user-visible change.
            values_differ = current_value.replace(microsecond=0) != (
                submitted_value.replace(microsecond=0)
            )
            if not values_differ:
                submitted_value = current_value
        if (
            current_plan.status == Plan.Status.APPROVED
            and field_name in review_fields
            and values_differ
        ):
            review_reset_required = True
        setattr(current_plan, field_name, submitted_value)
        changed_fields.append(field_name)

    if review_reset_required:
        current_plan.status = Plan.Status.PENDING
        current_plan.approved_at = None
        current_plan.approved_by = None
        changed_fields.extend(["status", "approved_at", "approved_by"])
    if changed_fields:
        current_plan.save(update_fields=dict.fromkeys(changed_fields))
        if old_thumbnail_name and "thumbnail_image" in changed_fields:
            thumbnail_storage = current_plan.thumbnail_image.storage
            transaction.on_commit(
                lambda storage=thumbnail_storage, name=old_thumbnail_name: storage.delete(name)
            )
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


def _require_signed_in_active_account(user):
    if (
        not getattr(user, "is_authenticated", False)
        or not getattr(user, "is_active", False)
        or getattr(user, "pk", None) is None
    ):
        raise PermissionDenied("A signed-in active account is required")


def _require_absolute_return_url(return_url):
    parsed_url = urlsplit(return_url)
    if (
        parsed_url.scheme not in {"http", "https"}
        or not parsed_url.netloc
        or parsed_url.username
        or parsed_url.password
    ):
        raise PermissionDenied("A server-built return URL is required")


def _require_stripe_hosted_url(url, expected_host):
    if not isinstance(url, str):
        raise ValueError("Stripe did not return a hosted URL")
    parsed_url = urlsplit(url)
    if parsed_url.scheme != "https" or parsed_url.hostname != expected_host:
        raise ValueError("Stripe did not return the expected hosted URL")
    return url


def start_stripe_subscription_checkout(user, success_url, cancel_url):
    """Create hosted Checkout for the one configured Premium subscription.

    Inputs: a server-known account and account-route URLs built by the view.
    Returns: the validated Stripe-hosted Checkout URL.
    Changes: creates a Stripe Checkout session outside a database transaction.
    Refuses: inactive accounts, unsafe URLs, missing configuration and duplicate
        active/trialing subscriptions.
    Privacy: sends only the immutable local user ID and known Stripe customer ID.
    """
    _require_signed_in_active_account(user)
    _require_absolute_return_url(success_url)
    _require_absolute_return_url(cancel_url)
    if not settings.STRIPE_SECRET_KEY or not settings.STRIPE_PRICE_ID:
        raise PermissionDenied("Stripe subscription configuration is unavailable")

    subscription = PlatformSubscription.objects.filter(user=user).first()
    if subscription is not None and subscription.stripe_status in {
        "active",
        "trialing",
    }:
        raise PermissionDenied("Use the existing Stripe subscription")

    has_stripe_history = bool(
        subscription
        and (
            subscription.stripe_customer_id
            or subscription.stripe_subscription_id
        )
    )
    subscription_data = {
        "metadata": {"kindlelise_user_id": str(user.pk)},
    }
    checkout_values = {
        "api_key": settings.STRIPE_SECRET_KEY,
        "mode": "subscription",
        "line_items": [{"price": settings.STRIPE_PRICE_ID, "quantity": 1}],
        "client_reference_id": str(user.pk),
        "payment_method_collection": "if_required",
        "subscription_data": subscription_data,
        "success_url": success_url,
        "cancel_url": cancel_url,
    }
    if subscription is not None and subscription.stripe_customer_id:
        checkout_values["customer"] = subscription.stripe_customer_id
    if not has_stripe_history:
        subscription_data.update(
            {
                "trial_period_days": 30,
                "trial_settings": {
                    "end_behavior": {
                        "missing_payment_method": "create_invoice",
                    }
                },
            }
        )

    checkout_session = stripe.checkout.Session.create(**checkout_values)
    return _require_stripe_hosted_url(
        getattr(checkout_session, "url", None),
        "checkout.stripe.com",
    )


def open_stripe_customer_portal(user, return_url):
    """Create a hosted portal session for the account's known Stripe customer.

    Inputs: a server-known account and account-route return URL built by the view.
    Returns: the validated Stripe-hosted customer-portal URL.
    Changes: creates a Stripe portal session outside a database transaction.
    Refuses: inactive accounts, unsafe URLs, missing configuration or customer ID.
    Privacy: sends only the account's already-linked Stripe customer identifier.
    """
    _require_signed_in_active_account(user)
    _require_absolute_return_url(return_url)
    if not settings.STRIPE_SECRET_KEY:
        raise PermissionDenied("Stripe portal configuration is unavailable")
    subscription = PlatformSubscription.objects.filter(user=user).first()
    if subscription is None or not subscription.stripe_customer_id:
        raise PermissionDenied("A linked Stripe customer is required")

    portal_session = stripe.billing_portal.Session.create(
        api_key=settings.STRIPE_SECRET_KEY,
        customer=subscription.stripe_customer_id,
        return_url=return_url,
    )
    return _require_stripe_hosted_url(
        getattr(portal_session, "url", None),
        "billing.stripe.com",
    )


def _as_mapping(value):
    return value if isinstance(value, Mapping) else {}


def _stripe_identifier(value):
    if isinstance(value, Mapping):
        value = value.get("id")
    if not isinstance(value, str) or not value or len(value) > 255:
        return None
    return value


def _provider_time(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("Stripe event time is invalid")
    try:
        return datetime.fromtimestamp(value, tz=datetime_timezone.utc)
    except (OverflowError, OSError, ValueError) as error:
        raise ValueError("Stripe event time is invalid") from error


def _positive_local_user_id(*values):
    local_user_ids = set()
    for value in values:
        if value in (None, ""):
            continue
        try:
            local_user_id = int(value)
        except (TypeError, ValueError) as error:
            raise ValueError("Stripe account metadata is invalid") from error
        if local_user_id < 1:
            raise ValueError("Stripe account metadata is invalid")
        local_user_ids.add(local_user_id)
    if len(local_user_ids) > 1:
        raise ValueError("Stripe account metadata conflicts")
    return next(iter(local_user_ids), None)


def _stripe_event_identity(event_type, stripe_object):
    object_metadata = _as_mapping(stripe_object.get("metadata"))
    client_reference_id = None
    subscription_metadata_id = object_metadata.get("kindlelise_user_id")
    if event_type == "checkout.session.completed":
        client_reference_id = stripe_object.get("client_reference_id")
        subscription_id = _stripe_identifier(stripe_object.get("subscription"))
    elif event_type.startswith("customer.subscription."):
        subscription_id = _stripe_identifier(stripe_object.get("id"))
    else:
        invoice_parent = _as_mapping(stripe_object.get("parent"))
        subscription_details = _as_mapping(
            invoice_parent.get("subscription_details")
        )
        subscription_value = subscription_details.get("subscription")
        if subscription_value is None:
            subscription_value = stripe_object.get("subscription")
        subscription_id = _stripe_identifier(subscription_value)
        subscription_metadata = _as_mapping(subscription_details.get("metadata"))
        subscription_metadata_id = subscription_metadata.get(
            "kindlelise_user_id",
            subscription_metadata_id,
        )

    customer_id = _stripe_identifier(stripe_object.get("customer"))
    if customer_id is None or subscription_id is None:
        raise ValueError("Stripe ownership identifiers are missing")
    local_user_id = _positive_local_user_id(
        client_reference_id,
        subscription_metadata_id,
    )
    return local_user_id, customer_id, subscription_id


def _resolve_stripe_event_user_id(
    local_user_id,
    customer_id,
    subscription_id,
):
    linked_user_ids = set(
        PlatformSubscription.objects.filter(
            Q(stripe_customer_id=customer_id)
            | Q(stripe_subscription_id=subscription_id)
        ).values_list("user_id", flat=True)
    )
    if len(linked_user_ids) > 1:
        raise ValueError("Stripe identifiers are linked to different accounts")
    linked_user_id = next(iter(linked_user_ids), None)
    if local_user_id is not None and linked_user_id not in {None, local_user_id}:
        raise ValueError("Stripe ownership metadata conflicts with the stored link")
    resolved_user_id = local_user_id or linked_user_id
    if resolved_user_id is None or not get_user_model().objects.filter(
        pk=resolved_user_id
    ).exists():
        raise ValueError("Stripe event has no trusted local account")
    return resolved_user_id


def _paid_invoice_period_end(stripe_object, subscription_id):
    if (
        stripe_object.get("status") != "paid"
        or stripe_object.get("currency") != "gbp"
        or not isinstance(stripe_object.get("amount_paid"), int)
        or stripe_object["amount_paid"] < 499
    ):
        raise ValueError("Stripe invoice is not a paid GBP annual invoice")

    paid_period_ends = []
    invoice_lines = _as_mapping(stripe_object.get("lines")).get("data", [])
    if not isinstance(invoice_lines, list):
        raise ValueError("Stripe invoice lines are invalid")
    for invoice_line in invoice_lines:
        invoice_line = _as_mapping(invoice_line)
        pricing = _as_mapping(invoice_line.get("pricing"))
        price_details = _as_mapping(pricing.get("price_details"))
        if _stripe_identifier(price_details.get("price")) != settings.STRIPE_PRICE_ID:
            continue
        if invoice_line.get("currency") != "gbp" or invoice_line.get("quantity") != 1:
            raise ValueError("Stripe invoice price values are invalid")
        line_parent = _as_mapping(invoice_line.get("parent"))
        subscription_item_details = _as_mapping(
            line_parent.get("subscription_item_details")
        )
        line_subscription_id = _stripe_identifier(
            subscription_item_details.get("subscription")
            or invoice_line.get("subscription")
        )
        if line_subscription_id not in {None, subscription_id}:
            raise ValueError("Stripe invoice line belongs to another subscription")
        period_end = _as_mapping(invoice_line.get("period")).get("end")
        paid_period_ends.append(_provider_time(period_end))
    if len(paid_period_ends) != 1:
        raise ValueError("Stripe invoice must contain one configured annual line")
    paid_period_end = paid_period_ends[0]
    if paid_period_end <= timezone.now():
        raise ValueError("Stripe paid service period is not in the future")
    return paid_period_end


def _active_invoice_subscription_status(stripe_object, subscription_id):
    invoice_parent = _as_mapping(stripe_object.get("parent"))
    subscription_details = _as_mapping(invoice_parent.get("subscription_details"))
    subscription_value = subscription_details.get("subscription")
    if isinstance(subscription_value, Mapping):
        if _stripe_identifier(subscription_value) != subscription_id:
            raise ValueError("Stripe invoice subscription is inconsistent")
        return subscription_value.get("status")
    provider_subscription = stripe.Subscription.retrieve(
        subscription_id,
        api_key=settings.STRIPE_SECRET_KEY,
    )
    if _stripe_identifier(provider_subscription) != subscription_id:
        raise ValueError("Stripe returned another subscription")
    return provider_subscription.get("status")


def _store_processed_receipt(receipt):
    receipt.processed_at = timezone.now()
    receipt.save(update_fields=["processed_at"])


def update_premium_access_from_verified_stripe_event(stripe_event):
    """Project one verified supported Stripe event into local Premium access.

    Inputs: a signature-verified supported Stripe event from the webhook view.
    Returns: true when projection data changed and false for a safe no-op.
    Changes: atomically records one event receipt and the permitted subscription
        identifiers, trial state, paid period or cancellation state.
    Refuses: malformed, unowned, conflicting, unpaid or provider-invalid events.
    Privacy: never uses email or stores card, bank, invoice or raw payload data.
    """
    stripe_event = _as_mapping(stripe_event)
    event_id = _stripe_identifier(stripe_event.get("id"))
    event_type = stripe_event.get("type")
    if event_id is None or event_type not in {
        "checkout.session.completed",
        "customer.subscription.updated",
        "invoice.paid",
        "customer.subscription.deleted",
    }:
        raise ValueError("Stripe event is not supported")
    provider_created_at = _provider_time(stripe_event.get("created"))
    stripe_object = _as_mapping(_as_mapping(stripe_event.get("data")).get("object"))
    if not stripe_object:
        raise ValueError("Stripe event object is missing")
    local_user_id, customer_id, subscription_id = _stripe_event_identity(
        event_type,
        stripe_object,
    )
    resolved_user_id = _resolve_stripe_event_user_id(
        local_user_id,
        customer_id,
        subscription_id,
    )

    paid_period_end = None
    provider_subscription_status = None
    if event_type == "invoice.paid":
        if not settings.STRIPE_SECRET_KEY or not settings.STRIPE_PRICE_ID:
            raise ValueError("Stripe subscription configuration is unavailable")
        paid_period_end = _paid_invoice_period_end(stripe_object, subscription_id)
        # Stripe recommends granting paid access only when the related
        # subscription is active. This authenticated read stays outside the
        # database transaction when the webhook did not expand the subscription.
        provider_subscription_status = _active_invoice_subscription_status(
            stripe_object,
            subscription_id,
        )

    with transaction.atomic():
        receipt, receipt_created = (
            StripeWebhookReceipt.objects.select_for_update().get_or_create(
                stripe_event_id=event_id,
                defaults={
                    "event_type": event_type,
                    "provider_created_at": provider_created_at,
                },
            )
        )
        if not receipt_created:
            if (
                receipt.event_type != event_type
                or receipt.provider_created_at != provider_created_at
            ):
                raise ValueError("Stripe event ID was reused inconsistently")
            if receipt.processed_at is not None:
                return False

        subscription, _created = (
            PlatformSubscription.objects.select_for_update().get_or_create(
                user_id=resolved_user_id
            )
        )
        if PlatformSubscription.objects.exclude(user_id=resolved_user_id).filter(
            Q(stripe_customer_id=customer_id)
            | Q(stripe_subscription_id=subscription_id)
        ).exists():
            raise ValueError("Stripe identifiers already belong to another account")

        latest_event_at = subscription.latest_provider_event_at
        if event_type == "checkout.session.completed":
            if latest_event_at is not None and provider_created_at <= latest_event_at:
                _store_processed_receipt(receipt)
                return False
        elif latest_event_at is not None:
            if provider_created_at < latest_event_at and event_type != "invoice.paid":
                _store_processed_receipt(receipt)
                return False
            if provider_created_at == latest_event_at and event_type != (
                "customer.subscription.deleted"
            ):
                _store_processed_receipt(receipt)
                return False

        replacing_subscription = bool(
            subscription.stripe_subscription_id
            and subscription.stripe_subscription_id != subscription_id
        )
        if subscription.stripe_customer_id not in {None, customer_id}:
            raise ValueError("Stripe customer ownership cannot be reassigned")
        if replacing_subscription:
            replacement_is_newer = (
                latest_event_at is None or provider_created_at > latest_event_at
            )
            if (
                local_user_id is None
                or subscription.stripe_status in {"active", "trialing"}
                or not replacement_is_newer
            ):
                _store_processed_receipt(receipt)
                return False

        changed_fields = []
        if subscription.stripe_customer_id != customer_id:
            subscription.stripe_customer_id = customer_id
            changed_fields.append("stripe_customer_id")
        if subscription.stripe_subscription_id != subscription_id:
            subscription.stripe_subscription_id = subscription_id
            changed_fields.append("stripe_subscription_id")

        if event_type == "checkout.session.completed":
            if changed_fields:
                subscription.save(update_fields=changed_fields)
            _store_processed_receipt(receipt)
            return bool(changed_fields)

        if event_type == "customer.subscription.deleted":
            subscription.stripe_status = "cancelled"
            subscription.access_until = None
            subscription.latest_provider_event_at = provider_created_at
            changed_fields.extend(
                ["stripe_status", "access_until", "latest_provider_event_at"]
            )
        elif event_type == "customer.subscription.updated":
            stripe_status = stripe_object.get("status")
            if not isinstance(stripe_status, str) or len(stripe_status) > 80:
                raise ValueError("Stripe subscription status is invalid")
            subscription.stripe_status = stripe_status
            changed_fields.append("stripe_status")
            if stripe_status == "trialing":
                trial_end = _provider_time(stripe_object.get("trial_end"))
                if trial_end <= timezone.now():
                    raise ValueError("Stripe trial end is not in the future")
                subscription.access_until = trial_end
                changed_fields.append("access_until")
            elif stripe_status != "active":
                subscription.access_until = None
                changed_fields.append("access_until")
            subscription.latest_provider_event_at = provider_created_at
            changed_fields.append("latest_provider_event_at")
        else:
            if provider_subscription_status != "active":
                _store_processed_receipt(receipt)
                return False
            if latest_event_at is not None and provider_created_at < latest_event_at:
                if (
                    subscription.stripe_status != "active"
                    or subscription.access_until is not None
                    and paid_period_end <= subscription.access_until
                ):
                    _store_processed_receipt(receipt)
                    return False
                subscription.access_until = paid_period_end
                changed_fields.append("access_until")
            else:
                subscription.stripe_status = "active"
                subscription.access_until = paid_period_end
                subscription.latest_provider_event_at = provider_created_at
                changed_fields.extend(
                    ["stripe_status", "access_until", "latest_provider_event_at"]
                )

        subscription.save(update_fields=dict.fromkeys(changed_fields))
        _store_processed_receipt(receipt)
        return True
