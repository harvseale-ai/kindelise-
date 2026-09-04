"""Test Kindelise Stripe and Premium behaviour."""

from types import SimpleNamespace

import pytest
import stripe
from django.core.exceptions import PermissionDenied
from django.db import (
    IntegrityError,
)
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from kindlelise.models import (
    PlatformSubscription,
    StripeWebhookReceipt,
)
from kindlelise.services import (
    open_stripe_customer_portal,
    start_stripe_subscription_checkout,
    update_premium_access_from_verified_stripe_event,
)
from tests.conftest import (
    build_stripe_test_event,
    create_test_user,
)

pytestmark = pytest.mark.django_db


def test_billing_entry_points_use_only_the_accounts_own_customer(
    monkeypatch,
    settings,
):
    account = create_test_user()
    settings.STRIPE_SECRET_KEY = "sk_test_synthetic"
    settings.STRIPE_PRICE_ID = "price_test_gbp_499_year"
    submitted_values = {}

    def create_checkout(**values):
        submitted_values.update(values)
        return SimpleNamespace(
            url="https://checkout.stripe.com/c/pay/cs_test_synthetic"
        )

    monkeypatch.setattr(
        "kindlelise.services.billing.stripe.checkout.Session.create",
        create_checkout,
    )

    checkout_url = start_stripe_subscription_checkout(
        account,
        "https://kindlelise.test/account/",
        "https://kindlelise.test/account/",
    )

    assert checkout_url.startswith("https://checkout.stripe.com/")
    assert submitted_values["mode"] == "subscription"
    assert submitted_values["line_items"] == [
        {"price": "price_test_gbp_499_year", "quantity": 1}
    ]
    assert submitted_values["client_reference_id"] == str(account.pk)
    assert submitted_values["subscription_data"] == {
        "metadata": {"kindlelise_user_id": str(account.pk)},
    }
    assert "payment_method_collection" not in submitted_values
    assert "customer" not in submitted_values
    assert not PlatformSubscription.objects.filter(user=account).exists()

    PlatformSubscription.objects.create(
        user=account,
        stripe_customer_id="cus_test_owner",
    )
    portal_values = {}

    def create_portal(**values):
        portal_values.update(values)
        return SimpleNamespace(url="https://billing.stripe.com/p/test")

    monkeypatch.setattr(
        "kindlelise.services.billing.stripe.billing_portal.Session.create",
        create_portal,
    )
    portal_url = open_stripe_customer_portal(
        account,
        "https://kindlelise.test/account/",
    )

    assert portal_url.startswith("https://billing.stripe.com/")
    assert portal_values["customer"] == "cus_test_owner"
    assert portal_values["return_url"] == "https://kindlelise.test/account/"
    with pytest.raises(PermissionDenied):
        open_stripe_customer_portal(
            create_test_user(),
            "https://kindlelise.test/account/",
        )


def test_stripe_paid_invoice_for_configured_gbp_price_grants_only_annual_period(
    settings,
    monkeypatch,
):
    account = create_test_user()
    settings.STRIPE_SECRET_KEY = "sk_test_synthetic"
    settings.STRIPE_PRICE_ID = "price_test_gbp_499_year"
    now = timezone.now()
    paid_period_end = now + timezone.timedelta(days=365)
    PlatformSubscription.objects.create(
        user=account,
        stripe_customer_id="cus_test_paid",
        stripe_subscription_id="sub_test_paid",
        stripe_status="active",
        latest_provider_event_at=now,
    )
    monkeypatch.setattr(
        stripe.Subscription,
        "retrieve",
        lambda *args, **kwargs: SimpleNamespace(
            id="sub_test_paid",
            status="active",
        ),
    )
    paid_event = build_stripe_test_event(
        "invoice.paid",
        event_id="evt_test_invoice_paid",
        provider_created_at=now,
        data={
            "id": "in_test_paid",
            "customer": "cus_test_paid",
            "status": "paid",
            "currency": "gbp",
            "amount_paid": 499,
            "parent": {
                "type": "subscription_details",
                "subscription_details": {
                    "subscription": "sub_test_paid",
                    "metadata": {"kindlelise_user_id": str(account.pk)},
                },
            },
            "lines": {
                "data": [
                    {
                        "currency": "gbp",
                        "quantity": 1,
                        "pricing": {
                            "price_details": {"price": "price_test_gbp_499_year"}
                        },
                        "parent": {
                            "subscription_item_details": {
                                "subscription": "sub_test_paid"
                            }
                        },
                        "period": {"end": int(paid_period_end.timestamp())},
                    }
                ]
            },
        },
    )

    assert update_premium_access_from_verified_stripe_event(paid_event)
    subscription = PlatformSubscription.objects.get(user=account)
    assert subscription.stripe_status == "active"
    assert abs((subscription.access_until - paid_period_end).total_seconds()) < 1
    assert subscription.has_premium_access()


def test_wrong_price_or_unpaid_invoice_cannot_grant_premium(settings):
    account = create_test_user()
    settings.STRIPE_SECRET_KEY = "sk_test_synthetic"
    settings.STRIPE_PRICE_ID = "price_test_gbp_499_year"
    PlatformSubscription.objects.create(
        user=account,
        stripe_customer_id="cus_test_wrong_invoice",
        stripe_subscription_id="sub_test_wrong_invoice",
        stripe_status="active",
    )
    event = build_stripe_test_event(
        "invoice.paid",
        event_id="evt_test_wrong_invoice",
        data={
            "customer": "cus_test_wrong_invoice",
            "status": "paid",
            "currency": "gbp",
            "amount_paid": 499,
            "parent": {
                "type": "subscription_details",
                "subscription_details": {
                    "subscription": {
                        "id": "sub_test_wrong_invoice",
                        "status": "active",
                    },
                    "metadata": {"kindlelise_user_id": str(account.pk)},
                },
            },
            "lines": {
                "data": [
                    {
                        "currency": "gbp",
                        "quantity": 1,
                        "pricing": {"price_details": {"price": "price_test_other"}},
                        "period": {
                            "end": int(
                                (
                                    timezone.now() + timezone.timedelta(days=365)
                                ).timestamp()
                            )
                        },
                    }
                ]
            },
        },
    )

    with pytest.raises(ValueError):
        update_premium_access_from_verified_stripe_event(event)
    subscription = PlatformSubscription.objects.get(user=account)
    assert subscription.access_until is None
    assert not StripeWebhookReceipt.objects.filter(
        stripe_event_id="evt_test_wrong_invoice"
    ).exists()

    event["id"] = "evt_test_unpaid_invoice"
    event["data"]["object"]["status"] = "open"
    event["data"]["object"]["lines"]["data"][0]["pricing"]["price_details"]["price"] = (
        "price_test_gbp_499_year"
    )
    with pytest.raises(ValueError):
        update_premium_access_from_verified_stripe_event(event)
    subscription.refresh_from_db()
    assert subscription.access_until is None
    assert not StripeWebhookReceipt.objects.filter(
        stripe_event_id="evt_test_unpaid_invoice"
    ).exists()


def test_stripe_duplicate_old_equal_time_and_delayed_paid_events_preserve_ordering(
    settings,
):
    account = create_test_user()
    settings.STRIPE_SECRET_KEY = "sk_test_synthetic"
    settings.STRIPE_PRICE_ID = "price_test_gbp_499_year"
    now = timezone.now().replace(microsecond=0)
    original_end = now + timezone.timedelta(days=200)
    later_paid_end = now + timezone.timedelta(days=365)
    subscription = PlatformSubscription.objects.create(
        user=account,
        stripe_customer_id="cus_test_ordering",
        stripe_subscription_id="sub_test_ordering",
        stripe_status="active",
        access_until=original_end,
        latest_provider_event_at=now,
    )
    delayed_paid_event = build_stripe_test_event(
        "invoice.paid",
        event_id="evt_test_delayed_paid",
        provider_created_at=now - timezone.timedelta(seconds=1),
        data={
            "customer": "cus_test_ordering",
            "status": "paid",
            "currency": "gbp",
            "amount_paid": 499,
            "parent": {
                "type": "subscription_details",
                "subscription_details": {
                    "subscription": {
                        "id": "sub_test_ordering",
                        "status": "active",
                    },
                    "metadata": {"kindlelise_user_id": str(account.pk)},
                },
            },
            "lines": {
                "data": [
                    {
                        "currency": "gbp",
                        "quantity": 1,
                        "pricing": {
                            "price_details": {"price": "price_test_gbp_499_year"}
                        },
                        "parent": {
                            "subscription_item_details": {
                                "subscription": "sub_test_ordering"
                            }
                        },
                        "period": {"end": int(later_paid_end.timestamp())},
                    }
                ]
            },
        },
    )
    assert update_premium_access_from_verified_stripe_event(delayed_paid_event)
    subscription.refresh_from_db()
    assert subscription.access_until == later_paid_end
    assert subscription.latest_provider_event_at == now
    assert not update_premium_access_from_verified_stripe_event(delayed_paid_event)
    assert (
        StripeWebhookReceipt.objects.filter(
            stripe_event_id="evt_test_delayed_paid"
        ).count()
        == 1
    )

    equal_active_event = build_stripe_test_event(
        event_id="evt_test_equal_active",
        provider_created_at=now,
        data={
            "id": "sub_test_ordering",
            "customer": "cus_test_ordering",
            "status": "active",
            "metadata": {"kindlelise_user_id": str(account.pk)},
        },
    )
    assert not update_premium_access_from_verified_stripe_event(equal_active_event)
    subscription.refresh_from_db()
    assert subscription.access_until == later_paid_end

    deletion_event = build_stripe_test_event(
        "customer.subscription.deleted",
        event_id="evt_test_equal_delete",
        provider_created_at=now,
        data={
            "id": "sub_test_ordering",
            "customer": "cus_test_ordering",
            "status": "canceled",
            "metadata": {"kindlelise_user_id": str(account.pk)},
        },
    )
    assert update_premium_access_from_verified_stripe_event(deletion_event)
    subscription.refresh_from_db()
    assert subscription.stripe_status == "cancelled"
    assert subscription.access_until is None
    assert subscription.stripe_customer_id == "cus_test_ordering"
    assert subscription.stripe_subscription_id == "sub_test_ordering"

    newer_period_event = dict(delayed_paid_event)
    newer_period_event["id"] = "evt_test_cannot_revive"
    newer_period_event["created"] = int(
        (now - timezone.timedelta(seconds=2)).timestamp()
    )
    assert not update_premium_access_from_verified_stripe_event(newer_period_event)
    subscription.refresh_from_db()
    assert subscription.stripe_status == "cancelled"
    assert subscription.access_until is None


def test_stripe_webhook_verifies_exact_body_and_returns_mapped_statuses(
    monkeypatch,
    settings,
    caplog,
):
    settings.STRIPE_SECRET_KEY = "sk_test_synthetic"
    settings.STRIPE_WEBHOOK_SECRET = "whsec_test_synthetic"
    account = create_test_user()
    raw_body = b'{"synthetic":"private-webhook-marker"}'
    received = {}
    supported_event = build_stripe_test_event(
        "checkout.session.completed",
        event_id="evt_test_http_webhook",
        data={
            "customer": "cus_test_http_webhook",
            "subscription": "sub_test_http_webhook",
            "client_reference_id": str(account.pk),
        },
    )

    def construct_event(payload, signature, secret, **values):
        received.update(
            {
                "payload": payload,
                "signature": signature,
                "secret": secret,
                "api_key": values.get("api_key"),
            }
        )
        return stripe.Event.construct_from(supported_event, "sk_test_synthetic")

    monkeypatch.setattr(
        "kindlelise.views.billing.stripe.Webhook.construct_event",
        construct_event,
    )
    client = Client(enforce_csrf_checks=True)
    response = client.post(
        reverse("stripe_webhook"),
        data=raw_body,
        content_type="application/json",
        HTTP_STRIPE_SIGNATURE="t=1,v1=synthetic",
    )
    assert response.status_code == 200
    assert received == {
        "payload": raw_body,
        "signature": "t=1,v1=synthetic",
        "secret": "whsec_test_synthetic",
        "api_key": "sk_test_synthetic",
    }
    assert StripeWebhookReceipt.objects.filter(
        stripe_event_id="evt_test_http_webhook"
    ).exists()
    trial_end = timezone.now() + timezone.timedelta(days=30)
    monkeypatch.setattr(
        "kindlelise.views.billing.stripe.Webhook.construct_event",
        lambda *args, **kwargs: build_stripe_test_event(
            "customer.subscription.created",
            event_id="evt_test_http_subscription_created",
            data={
                "id": "sub_test_http_webhook",
                "customer": "cus_test_http_webhook",
                "status": "trialing",
                "trial_end": int(trial_end.timestamp()),
                "metadata": {"kindlelise_user_id": str(account.pk)},
            },
        ),
    )
    assert (
        client.post(
            reverse("stripe_webhook"),
            data=b"{}",
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="synthetic",
        ).status_code
        == 200
    )
    subscription = PlatformSubscription.objects.get(user=account)
    assert subscription.stripe_status == "trialing"
    assert subscription.has_premium_access()
    assert "private-webhook-marker" not in caplog.text
    assert "whsec_test_synthetic" not in caplog.text
    assert client.get(reverse("stripe_webhook")).status_code == 405

    monkeypatch.setattr(
        "kindlelise.views.billing.stripe.Webhook.construct_event",
        lambda *args, **kwargs: (_ for _ in ()).throw(ValueError("invalid")),
    )
    assert (
        client.post(
            reverse("stripe_webhook"),
            data=b"invalid",
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="invalid",
        ).status_code
        == 400
    )

    monkeypatch.setattr(
        "kindlelise.views.billing.stripe.Webhook.construct_event",
        lambda *args, **kwargs: build_stripe_test_event(
            "invoice.created",
            event_id="evt_test_unsupported_http",
        ),
    )
    assert (
        client.post(
            reverse("stripe_webhook"),
            data=b"{}",
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="synthetic",
        ).status_code
        == 200
    )
    assert not StripeWebhookReceipt.objects.filter(
        stripe_event_id="evt_test_unsupported_http"
    ).exists()

    monkeypatch.setattr(
        "kindlelise.views.billing.stripe.Webhook.construct_event",
        lambda *args, **kwargs: build_stripe_test_event(
            "checkout.session.completed",
            event_id="evt_test_retryable_http",
            data={
                "customer": "cus_test_retryable_http",
                "subscription": "sub_test_retryable_http",
                "client_reference_id": str(account.pk),
            },
        ),
    )
    monkeypatch.setattr(
        "kindlelise.views.billing.update_premium_access_from_verified_stripe_event",
        lambda event: (_ for _ in ()).throw(IntegrityError("synthetic failure")),
    )
    assert (
        client.post(
            reverse("stripe_webhook"),
            data=raw_body,
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="synthetic",
        ).status_code
        == 500
    )
    assert not StripeWebhookReceipt.objects.filter(
        stripe_event_id="evt_test_retryable_http"
    ).exists()
    assert "private-webhook-marker" not in caplog.text
