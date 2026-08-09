"""Stripe Checkout, subscription management, and webhook pages."""

# WHY: This module keeps payment-provider code apart from the everyday product pages.
import stripe
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from kindlelise.services.billing import (
    open_stripe_customer_portal,
    start_stripe_subscription_checkout,
)
from kindlelise.services.stripe_events import (
    update_premium_access_from_verified_stripe_event,
)


# WHY: Keeps the start premium subscription checkout steps in one named place so they can be understood, checked, and reused.
@require_POST
@login_required
def start_premium_subscription_checkout(request):
    """Start the account's configured Stripe-hosted Premium subscription.

    Inputs: a signed-in CSRF-validated POST; browser destinations are ignored.
    Returns: a redirect to hosted Checkout or back to the private account page.
    Changes: calls the mapped Stripe Checkout service outside a transaction.
    Refuses: invalid account/configuration, duplicate subscription or provider failure.
    Privacy: sends no browser-selected account, customer or return URL to Stripe.
    """
    # WHY: Builds both Stripe return destinations on the server instead of accepting a browser redirect URL.
    account_url = request.build_absolute_uri(reverse("account"))
    try:
        checkout_url = start_stripe_subscription_checkout(
            request.user,
            account_url,
            account_url,
        )
    # WHY: Gives visitors one quiet retry message for permission, configuration, URL, or Stripe failures.
    except (PermissionDenied, stripe.StripeError, ValueError):
        messages.error(request, "Premium Checkout is unavailable. Please try again.")
        return redirect("account")
    # WHY: Redirects only to the exact Stripe Checkout host already verified by the service.
    return redirect(checkout_url)

# WHY: Keeps the open premium subscription portal steps in one named place so they can be understood, checked, and reused.
@require_POST
@login_required
def open_premium_subscription_portal(request):
    """Open Stripe's hosted portal for the account's linked customer.

    Inputs: a signed-in CSRF-validated POST; the return destination is server-built.
    Returns: a redirect to Stripe's portal or back to the private account page.
    Changes: calls the mapped Stripe portal service outside a transaction.
    Refuses: missing ownership/configuration and every provider or URL failure.
    Privacy: never accepts a customer identifier or return URL from the browser.
    """
    # WHY: Uses the signed-in account page as the only server-built return destination.
    account_url = request.build_absolute_uri(reverse("account"))
    try:
        portal_url = open_stripe_customer_portal(request.user, account_url)
    except (PermissionDenied, stripe.StripeError, ValueError):
        messages.error(request, "Subscription management is unavailable. Please try again.")
        return redirect("account")
    # WHY: Redirects only to the exact Stripe billing host already verified by the service.
    return redirect(portal_url)

# WHY: Keeps the receive and verify stripe webhook steps in one named place so they can be understood, checked, and reused.
@csrf_exempt
@require_POST
def receive_and_verify_stripe_webhook(request):
    """Verify the raw Stripe signature and apply one supported event safely.

    Inputs: the exact raw POST body and Stripe signature header.
    Returns: 400 for invalid input, 200 for safe handling and 500 for retryable failure.
    Changes: calls the atomic receipt/projection service for supported events.
    Refuses: invalid signatures, malformed JSON and unsupported state changes.
    Privacy: never authenticates a browser session or logs/stores the raw payload.
    """
    # WHY: Refuses every webhook when the private signature secret is not configured.
    if not settings.STRIPE_WEBHOOK_SECRET:
        return HttpResponse(status=400)
    # WHY: Verifies the signature against the exact raw body before trusting any event field.
    try:
        stripe_event = stripe.Webhook.construct_event(
            request.body,
            request.headers.get("Stripe-Signature", ""),
            settings.STRIPE_WEBHOOK_SECRET,
            api_key=settings.STRIPE_SECRET_KEY or None,
        )
    except (ValueError, stripe.SignatureVerificationError):
        return HttpResponse(status=400)
    # WHY: Converts Stripe's object wrapper into ordinary labelled values used by the local service.
    if hasattr(stripe_event, "to_dict"):
        stripe_event = stripe_event.to_dict()

    # WHY: Acknowledges unrelated valid Stripe events without changing any local state.
    if stripe_event.get("type") not in {
        "checkout.session.completed",
        "customer.subscription.created",
        "customer.subscription.updated",
        "invoice.paid",
        "customer.subscription.deleted",
    }:
        return HttpResponse(status=200)
    # WHY: Lets Stripe retry a supported event whenever its receipt and local access update did not commit.
    try:
        update_premium_access_from_verified_stripe_event(stripe_event)
    except Exception:
        # WHY: A short failure response avoids exposing payment details while asking Stripe to retry later.
        return HttpResponse(status=500)
    return HttpResponse(status=200)
