"""Stripe Checkout and customer-portal workflows."""

# WHY: Keeps browser-facing Stripe session creation separate from signed webhook updates.
from urllib.parse import urlsplit

import stripe
from django.conf import settings
from django.core.exceptions import PermissionDenied

from kindlelise.models import PlatformSubscription


# WHY: Keeps the require signed in active account steps in one named place so they can be understood, checked, and reused.
def _require_signed_in_active_account(user):
    # WHY: Applies the same basic account boundary before either Stripe-hosted account action.
    if (
        not getattr(user, "is_authenticated", False)
        or not getattr(user, "is_active", False)
        or getattr(user, "pk", None) is None
    ):
        raise PermissionDenied("A signed-in active account is required")
    # WHY: A successful check needs no return value; reaching this point is the permission result.

# WHY: Keeps the require absolute return url steps in one named place so they can be understood, checked, and reused.
def _require_absolute_return_url(return_url):
    # WHY: Splits a server-built return address so incomplete or credential-bearing addresses can be refused.
    parsed_url = urlsplit(return_url)
    if (
        parsed_url.scheme not in {"http", "https"}
        or not parsed_url.netloc
        or parsed_url.username
        or parsed_url.password
    ):
        raise PermissionDenied("A server-built return URL is required")
    # WHY: User names and passwords are refused so private credentials can never be placed in a redirect address.

# WHY: Keeps the require stripe hosted url steps in one named place so they can be understood, checked, and reused.
def _require_stripe_hosted_url(url, expected_host):
    # WHY: Refuses missing or non-text outside responses before parsing them as web addresses.
    if not isinstance(url, str):
        raise ValueError("Stripe did not return a hosted URL")
    parsed_url = urlsplit(url)
    # WHY: Redirects the browser only to the exact encrypted Stripe host expected for this action.
    if parsed_url.scheme != "https" or parsed_url.hostname != expected_host:
        raise ValueError("Stripe did not return the expected hosted URL")
    # WHY: Returns the already-checked address unchanged for the view's browser redirect.
    return url

# WHY: Keeps the start stripe subscription checkout steps in one named place so they can be understood, checked, and reused.
def start_stripe_subscription_checkout(user, success_url, cancel_url):
    """Create hosted Checkout for the one configured Premium subscription.

    Inputs: a server-known account and account-route URLs built by the view.
    Returns: the validated Stripe-hosted Checkout URL.
    Changes: creates a Stripe Checkout session outside a database transaction.
    Refuses: inactive accounts, unsafe URLs, missing configuration and duplicate
        active/trialing subscriptions.
    Privacy: sends only the immutable local user ID and known Stripe customer ID.
    """
    # WHY: Checks account state and both browser return addresses before contacting Stripe.
    _require_signed_in_active_account(user)
    _require_absolute_return_url(success_url)
    _require_absolute_return_url(cancel_url)
    # WHY: Refuses checkout when the private account key or approved yearly price is missing.
    if not settings.STRIPE_SECRET_KEY or not settings.STRIPE_PRICE_ID:
        raise PermissionDenied("Stripe subscription configuration is unavailable")

    # WHY: Reads only this account's existing Stripe link so active access is not duplicated.
    subscription = PlatformSubscription.objects.filter(user=user).first()
    # WHY: An existing paid or trial account should manage its subscription instead of buying a duplicate.
    if subscription is not None and subscription.stripe_status in {
        "active",
        "trialing",
    }:
        raise PermissionDenied("Use the existing Stripe subscription")

    # WHY: Places the immutable local account ID on the Stripe subscription for signed webhook ownership checks.
    subscription_data = {
        "metadata": {"kindlelise_user_id": str(user.pk)},
    }
    # WHY: Fixes checkout to one subscription, one approved price, and server-built return pages.
    checkout_values = {
        "api_key": settings.STRIPE_SECRET_KEY,
        "mode": "subscription",
        "line_items": [{"price": settings.STRIPE_PRICE_ID, "quantity": 1}],
        "client_reference_id": str(user.pk),
        "subscription_data": subscription_data,
        "success_url": success_url,
        "cancel_url": cancel_url,
    }
    # WHY: Reuses a known Stripe customer so one local account does not create repeated billing identities.
    if subscription is not None and subscription.stripe_customer_id:
        checkout_values["customer"] = subscription.stripe_customer_id

    # WHY: Creates only Stripe's hosted payment page; local Premium access still waits for a signed webhook.
    # WHY: This is the one outside request in the workflow, made only after every local value has been checked.
    checkout_session = stripe.checkout.Session.create(**checkout_values)
    # WHY: Checks Stripe's answer before allowing the browser to leave Kindelise.
    return _require_stripe_hosted_url(
        getattr(checkout_session, "url", None),
        "checkout.stripe.com",
    )

# WHY: Keeps the open stripe customer portal steps in one named place so they can be understood, checked, and reused.
def open_stripe_customer_portal(user, return_url):
    """Create a hosted portal session for the account's known Stripe customer.

    Inputs: a server-known account and account-route return URL built by the view.
    Returns: the validated Stripe-hosted customer-portal URL.
    Changes: creates a Stripe portal session outside a database transaction.
    Refuses: inactive accounts, unsafe URLs, missing configuration or customer ID.
    Privacy: sends only the account's already-linked Stripe customer identifier.
    """
    # WHY: Checks account and return address before revealing or using any Stripe customer identity.
    _require_signed_in_active_account(user)
    _require_absolute_return_url(return_url)
    # WHY: The portal cannot be created safely without the private key used to identify this app to Stripe.
    if not settings.STRIPE_SECRET_KEY:
        raise PermissionDenied("Stripe portal configuration is unavailable")
    # WHY: Uses only the customer ID already linked to this exact local account.
    subscription = PlatformSubscription.objects.filter(user=user).first()
    if subscription is None or not subscription.stripe_customer_id:
        raise PermissionDenied("A linked Stripe customer is required")

    # WHY: Lets Stripe handle payment-method and cancellation controls on its own hosted page.
    # WHY: This outside request creates a short-lived management page for this known customer only.
    portal_session = stripe.billing_portal.Session.create(
        api_key=settings.STRIPE_SECRET_KEY,
        customer=subscription.stripe_customer_id,
        return_url=return_url,
    )
    # WHY: Checks Stripe's answer before allowing the browser to leave Kindelise.
    return _require_stripe_hosted_url(
        getattr(portal_session, "url", None),
        "billing.stripe.com",
    )
