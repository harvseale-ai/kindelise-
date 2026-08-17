"""Verified Stripe-event parsing and local Premium-access updates."""

# KEYWORD: webhook — a signed notice Stripe sends after payment or subscription changes.
# KEYWORD: invoice — Stripe's record of a payment and the service period it covers.
# WHY: Keeps the larger signed-event rules together so payment ordering remains reviewable.
from collections.abc import Mapping
from datetime import datetime
from datetime import timezone as datetime_timezone

import stripe
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from kindlelise.models import PlatformSubscription, StripeWebhookReceipt

# =============================================================================
# SAFE STRIPE VALUE READING
# Turns Stripe values into bounded local values used by later payment checks.
# =============================================================================

# WHY: Keeps the as mapping steps in one named place so they can be understood, checked, and reused.
def _as_mapping(value):
    # WHY: Turns an unexpected Stripe value into an empty labelled object so later reads fail safely.
    # WHY: Keeping this rule here avoids repeating the same type check at every nested Stripe field.
    return value if isinstance(value, Mapping) else {}

# WHY: Keeps the stripe identifier steps in one named place so they can be understood, checked, and reused.
def _stripe_identifier(value):
    # WHY: Accepts a dictionary, Stripe library object or plain ID using one bounded rule.
    if isinstance(value, Mapping):
        # WHY: Expanded Stripe objects carry their usable identifier under the same `id` key.
        value = value.get("id")
    elif not isinstance(value, str):
        # WHY: Current Stripe library objects expose the same identifier as an `id` attribute.
        value = getattr(value, "id", None)
    if not isinstance(value, str) or not value or len(value) > 255:
        # WHY: Missing, wrongly shaped or unusually long identifiers must never be used in database lookups.
        return None
    # WHY: Returns only the small plain-text identifier needed by the local subscription record.
    return value

# WHY: Keeps the provider time steps in one named place so they can be understood, checked, and reused.
def _provider_time(value):
    # WHY: Refuses booleans because Python otherwise treats them like the numbers zero and one.
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("Stripe event time is invalid")
    # WHY: Converts Stripe's number of seconds into a clear UTC moment used for ordering.
    try:
        return datetime.fromtimestamp(value, tz=datetime_timezone.utc)
    except (OverflowError, OSError, ValueError) as error:
        # WHY: Converts several computer-specific time failures into one predictable event error.
        raise ValueError("Stripe event time is invalid") from error

# WHY: Keeps the positive local user id steps in one named place so they can be understood, checked, and reused.
def _positive_local_user_id(*values):
    # WHY: Collects every local account ID claimed in different trusted parts of the Stripe event.
    local_user_ids = set()
    for value in values:
        # WHY: Missing optional identity fields are allowed when another trusted link supplies the account.
        if value in (None, ""):
            continue
        try:
            local_user_id = int(value)
        except (TypeError, ValueError) as error:
            raise ValueError("Stripe account metadata is invalid") from error
        if local_user_id < 1:
            raise ValueError("Stripe account metadata is invalid")
        local_user_ids.add(local_user_id)
    # WHY: Refuses an event whose own fields point at different local accounts.
    if len(local_user_ids) > 1:
        raise ValueError("Stripe account metadata conflicts")
    # WHY: Returns the one agreed account ID, or no ID when every optional location was empty.
    return next(iter(local_user_ids), None)

# =============================================================================
# SUBSCRIPTION OWNERSHIP
# Extracts and cross-checks account, customer, and subscription identities.
# =============================================================================

# WHY: Keeps the stripe event identity steps in one named place so they can be understood, checked, and reused.
def _stripe_event_identity(event_type, stripe_object):
    # WHY: Reads the local account ID from the location Stripe uses for this particular event type.
    object_metadata = _as_mapping(stripe_object.get("metadata"))
    client_reference_id = None
    subscription_metadata_id = object_metadata.get("kindlelise_user_id")
    # WHY: Checkout, subscription, and invoice events carry subscription ownership in different shapes.
    if event_type == "checkout.session.completed":
        # WHY: Checkout provides the local reference separately from its subscription identifier.
        client_reference_id = stripe_object.get("client_reference_id")
        subscription_id = _stripe_identifier(stripe_object.get("subscription"))
    elif event_type.startswith("customer.subscription."):
        # WHY: For subscription notices, the event object itself is the subscription.
        subscription_id = _stripe_identifier(stripe_object.get("id"))
    else:
        # WHY: Invoice notices nest subscription ownership inside their parent payment details.
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

    # WHY: Every supported event must identify both one Stripe customer and one Stripe subscription.
    customer_id = _stripe_identifier(stripe_object.get("customer"))
    if customer_id is None or subscription_id is None:
        raise ValueError("Stripe ownership identifiers are missing")
    local_user_id = _positive_local_user_id(
        client_reference_id,
        subscription_metadata_id,
    )
    # WHY: Returns the three ownership clues together so they can be cross-checked before any save.
    return local_user_id, customer_id, subscription_id

# WHY: Keeps the resolve stripe event user id steps in one named place so they can be understood, checked, and reused.
def _resolve_stripe_event_user_id(
    local_user_id,
    customer_id,
    subscription_id,
):
    # WHY: Finds any local account already owning either Stripe identity before accepting event metadata.
    linked_user_ids = set(
        PlatformSubscription.objects.filter(
            Q(stripe_customer_id=customer_id)
            | Q(stripe_subscription_id=subscription_id)
        ).values_list("user_id", flat=True)
    )
    # WHY: Refuses customer and subscription IDs that are already split across different local accounts.
    if len(linked_user_ids) > 1:
        raise ValueError("Stripe identifiers are linked to different accounts")
    linked_user_id = next(iter(linked_user_ids), None)
    if local_user_id is not None and linked_user_id not in {None, local_user_id}:
        raise ValueError("Stripe ownership metadata conflicts with the stored link")
    # WHY: Prefers the event's immutable local ID and falls back only to an existing trusted Stripe link.
    resolved_user_id = local_user_id or linked_user_id
    if resolved_user_id is None or not get_user_model().objects.filter(
        pk=resolved_user_id
    ).exists():
        raise ValueError("Stripe event has no trusted local account")
    # WHY: From this point onward every change is tied to a real local account.
    return resolved_user_id

# =============================================================================
# PAID INVOICE CHECKS
# Confirms the paid price, billing period, and active subscription state.
# =============================================================================

# WHY: Keeps the paid invoice period end steps in one named place so they can be understood, checked, and reused.
def _paid_invoice_period_end(stripe_object, subscription_id):
    # WHY: Grants paid access only for a completed GBP payment of at least the configured yearly amount.
    if (
        stripe_object.get("status") != "paid"
        or stripe_object.get("currency") != "gbp"
        or not isinstance(stripe_object.get("amount_paid"), int)
        or stripe_object["amount_paid"] < 499
    ):
        raise ValueError("Stripe invoice is not a paid GBP annual invoice")

    # WHY: Collects service end times only from invoice lines using the one configured Premium price.
    paid_period_ends = []
    invoice_lines = _as_mapping(stripe_object.get("lines")).get("data", [])
    if not isinstance(invoice_lines, list):
        raise ValueError("Stripe invoice lines are invalid")
    for invoice_line in invoice_lines:
        # WHY: Safely reads each nested line and skips unrelated Stripe prices.
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
        # WHY: Refuses a configured-price line that belongs to another subscription.
        if line_subscription_id not in {None, subscription_id}:
            raise ValueError("Stripe invoice line belongs to another subscription")
        period_end = _as_mapping(invoice_line.get("period")).get("end")
        # WHY: Keeps only the matching paid service end, converted into the same UTC form used locally.
        paid_period_ends.append(_provider_time(period_end))
    # WHY: Requires exactly one matching annual line so access time is not ambiguous or counted twice.
    if len(paid_period_ends) != 1:
        raise ValueError("Stripe invoice must contain one configured annual line")
    paid_period_end = paid_period_ends[0]
    if paid_period_end <= timezone.now():
        raise ValueError("Stripe paid service period is not in the future")
    # WHY: This checked future date becomes the exact end of local Premium access.
    return paid_period_end

# WHY: Keeps the active invoice subscription status steps in one named place so they can be understood, checked, and reused.
def _active_invoice_subscription_status(stripe_object, subscription_id):
    # WHY: Uses subscription details already included in the signed invoice when Stripe supplied them.
    invoice_parent = _as_mapping(stripe_object.get("parent"))
    subscription_details = _as_mapping(invoice_parent.get("subscription_details"))
    subscription_value = subscription_details.get("subscription")
    if isinstance(subscription_value, Mapping):
        if _stripe_identifier(subscription_value) != subscription_id:
            raise ValueError("Stripe invoice subscription is inconsistent")
        # WHY: Reuses signed subscription details already present instead of making an unnecessary outside request.
        return subscription_value.get("status")
    # WHY: Otherwise asks Stripe for the current subscription and confirms it returned the requested identity.
    provider_subscription = stripe.Subscription.retrieve(
        subscription_id,
        api_key=settings.STRIPE_SECRET_KEY,
    )
    if _stripe_identifier(provider_subscription) != subscription_id:
        raise ValueError("Stripe returned another subscription")
    # WHY: Only the current status is needed to decide whether a paid invoice may grant access.
    if isinstance(provider_subscription, Mapping):
        return provider_subscription.get("status")
    # WHY: Current Stripe library objects expose their status as an attribute, not a dictionary key.
    return getattr(provider_subscription, "status", None)

# -----------------------------------------------------------------------------
# PROCESSED EVENT RECEIPTS
# Records provider events so repeated notices cannot be applied twice.
# -----------------------------------------------------------------------------

# WHY: Keeps the store processed receipt steps in one named place so they can be understood, checked, and reused.
def _store_processed_receipt(receipt):
    # WHY: Marks the signed notice complete so a retry can return safely without applying it twice.
    receipt.processed_at = timezone.now()
    receipt.save(update_fields=["processed_at"])

# =============================================================================
# APPLY A VERIFIED STRIPE EVENT
# Orders, records, and applies one signed event to local Premium access.
# =============================================================================

# WHY: Changes premium access from verified stripe event in one controlled place so linked values stay correct.
def update_premium_access_from_verified_stripe_event(stripe_event):
    """Project one verified supported Stripe event into local Premium access.

    Inputs: a signature-verified supported Stripe event from the webhook view.
    Returns: true when projection data changed and false for a safe no-op.
    Changes: atomically records one event receipt and the permitted subscription
        identifiers, trial state, paid period or cancellation state.
    Refuses: malformed, unowned, conflicting, unpaid or provider-invalid events.
    Privacy: never uses email or stores card, bank, invoice or raw payload data.
    """
    # WHY: Stripe is contacted before the database section below, so an outside delay never holds local row locks.
    # WHY: Treats an unexpected top-level value as invalid labelled data rather than allowing attribute errors.
    stripe_event = _as_mapping(stripe_event)

    # WHY: Accepts only a bounded event ID and the five event types this local access model understands.
    event_id = _stripe_identifier(stripe_event.get("id"))
    event_type = stripe_event.get("type")
    if event_id is None or event_type not in {
        "checkout.session.completed",
        "customer.subscription.created",
        "customer.subscription.updated",
        "invoice.paid",
        "customer.subscription.deleted",
    }:
        raise ValueError("Stripe event is not supported")
    # WHY: Uses Stripe's signed creation time for delayed-event ordering, not the local arrival time.
    provider_created_at = _provider_time(stripe_event.get("created"))

    # WHY: Reads only the signed event object and refuses a missing or malformed one.
    stripe_object = _as_mapping(_as_mapping(stripe_event.get("data")).get("object"))
    if not stripe_object:
        raise ValueError("Stripe event object is missing")
    # WHY: Extracts and cross-checks ownership identities before any subscription row is changed.
    local_user_id, customer_id, subscription_id = _stripe_event_identity(
        event_type,
        stripe_object,
    )
    resolved_user_id = _resolve_stripe_event_user_id(
        local_user_id,
        customer_id,
        subscription_id,
    )

    # WHY: Calculates paid invoice access before opening a database transaction or holding row locks.
    paid_period_end = None
    provider_subscription_status = None
    if event_type == "invoice.paid":
        # WHY: Paid access requires the private Stripe key and configured price used for verification.
        if not settings.STRIPE_SECRET_KEY or not settings.STRIPE_PRICE_ID:
            raise ValueError("Stripe subscription configuration is unavailable")
        paid_period_end = _paid_invoice_period_end(stripe_object, subscription_id)
        # WHY: Paid access also requires an active related subscription; this outside read happens before row locks.
        provider_subscription_status = _active_invoice_subscription_status(
            stripe_object,
            subscription_id,
        )

    # WHY: Keeps receipt recording and local access projection together so neither can succeed alone.
    with transaction.atomic():
        # WHY: Creates one receipt for a new event ID or locks the existing receipt for safe retry handling.
        receipt, receipt_created = (
            StripeWebhookReceipt.objects.select_for_update().get_or_create(
                stripe_event_id=event_id,
                defaults={
                    "event_type": event_type,
                    "provider_created_at": provider_created_at,
                },
            )
        )
        # WHY: A repeated ID must describe the exact same event and a completed retry becomes a no-op.
        if not receipt_created:
            if (
                receipt.event_type != event_type
                or receipt.provider_created_at != provider_created_at
            ):
                raise ValueError("Stripe event ID was reused inconsistently")
            if receipt.processed_at is not None:
                # WHY: Stripe may retry a successful notice; returning false confirms nothing needed changing again.
                return False

        # WHY: Creates or locks this local account's one subscription summary before changing identifiers.
        subscription, _created = (
            PlatformSubscription.objects.select_for_update().get_or_create(
                user_id=resolved_user_id
            )
        )
        # WHY: Prevents either Stripe identity being attached to any other local account.
        if PlatformSubscription.objects.exclude(user_id=resolved_user_id).filter(
            Q(stripe_customer_id=customer_id)
            | Q(stripe_subscription_id=subscription_id)
        ).exists():
            raise ValueError("Stripe identifiers already belong to another account")

        # WHY: Uses the most recent accepted Stripe time to stop delayed notices undoing newer state.
        latest_event_at = subscription.latest_provider_event_at
        if event_type == "checkout.session.completed":
            if latest_event_at is not None and provider_created_at <= latest_event_at:
                # WHY: A checkout link older than known subscription state cannot improve or replace that state.
                _store_processed_receipt(receipt)
                return False
        elif latest_event_at is not None:
            if provider_created_at < latest_event_at and event_type != "invoice.paid":
                # WHY: An older status notice must not undo a newer cancellation, trial or active state.
                _store_processed_receipt(receipt)
                return False
            if provider_created_at == latest_event_at and event_type not in {
                "customer.subscription.deleted",
                "invoice.paid",
            }:
                # WHY: Equal-time ordinary notices add nothing; deletion and paid access still carry distinct facts.
                _store_processed_receipt(receipt)
                return False

        # WHY: Treats a new subscription ID as a replacement requiring stronger ownership and timing proof.
        replacing_subscription = bool(
            subscription.stripe_subscription_id
            and subscription.stripe_subscription_id != subscription_id
        )
        # WHY: A local subscription may gain its first customer ID but can never be reassigned to another customer.
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
                # WHY: Keeps the current subscription when replacement ownership or timing is not strong enough.
                _store_processed_receipt(receipt)
                return False

        # WHY: Tracks only values that genuinely changed so database updates remain narrow and reviewable.
        changed_fields = []
        if subscription.stripe_customer_id != customer_id:
            subscription.stripe_customer_id = customer_id
            changed_fields.append("stripe_customer_id")
        if subscription.stripe_subscription_id != subscription_id:
            subscription.stripe_subscription_id = subscription_id
            changed_fields.append("stripe_subscription_id")

        # WHY: Checkout completion links identities only; it never grants Premium before subscription or payment proof.
        if event_type == "checkout.session.completed":
            if changed_fields:
                subscription.save(update_fields=changed_fields)
            _store_processed_receipt(receipt)
            # WHY: True means an identity link changed; false means the same safe link was already stored.
            return bool(changed_fields)

        # WHY: Deletion ends access immediately and records its event as the latest provider state.
        if event_type == "customer.subscription.deleted":
            subscription.stripe_status = "cancelled"
            subscription.access_until = None
            subscription.latest_provider_event_at = provider_created_at
            changed_fields.extend(
                ["stripe_status", "access_until", "latest_provider_event_at"]
            )
        # WHY: Creation and update events copy the current Stripe state and handle trial access explicitly.
        elif event_type in {
            "customer.subscription.created",
            "customer.subscription.updated",
        }:
            stripe_status = stripe_object.get("status")
            if not isinstance(stripe_status, str) or len(stripe_status) > 80:
                raise ValueError("Stripe subscription status is invalid")
            subscription.stripe_status = stripe_status
            changed_fields.append("stripe_status")
            # WHY: Trialing access lasts only until Stripe's signed future trial end.
            if stripe_status == "trialing":
                trial_end = _provider_time(stripe_object.get("trial_end"))
                if trial_end <= timezone.now():
                    raise ValueError("Stripe trial end is not in the future")
                subscription.access_until = trial_end
                changed_fields.append("access_until")
            # WHY: Every non-active, non-trial state clears local access immediately.
            elif stripe_status != "active":
                subscription.access_until = None
                changed_fields.append("access_until")
            # WHY: Active status alone keeps the present date; a paid invoice supplies any new paid end date.
            subscription.latest_provider_event_at = provider_created_at
            changed_fields.append("latest_provider_event_at")
        else:
            # WHY: The remaining supported event is a paid invoice, which grants access only for an active subscription.
            if provider_subscription_status != "active":
                # WHY: A payment cannot grant access when Stripe says the related subscription is not active.
                _store_processed_receipt(receipt)
                return False
            # WHY: An older paid invoice may extend access but may not replace a newer status or shorten access.
            if latest_event_at is not None and provider_created_at < latest_event_at:
                if (
                    subscription.stripe_status != "active"
                    or subscription.access_until is not None
                    and paid_period_end <= subscription.access_until
                ):
                    # WHY: Ignores an older invoice that cannot safely extend currently active access.
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

        # WHY: Saves each changed field once, then completes the receipt inside the same transaction.
        subscription.save(update_fields=dict.fromkeys(changed_fields))
        _store_processed_receipt(receipt)
        # WHY: True tells the webhook page that this accepted notice changed local Premium information.
        return True
