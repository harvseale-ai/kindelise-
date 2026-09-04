"""Test Kindelise discovery behaviour."""

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from kindlelise.models import (
    Block,
    Interest,
    Plan,
    PlatformSubscription,
    Profile,
)
from tests.conftest import (
    create_test_plan,
    create_test_user,
    create_verified_test_profile,
)

pytestmark = pytest.mark.django_db


def test_discovery_profile_http_is_safe_and_uses_one_generic_hidden_response():
    viewer = create_test_user()
    create_verified_test_profile(user=viewer, broad_area="central")
    target_user = create_test_user(username="private_target_login")
    target = create_verified_test_profile(
        user=target_user,
        display_name="Public target name",
        biography="Public text <script>alert('no')</script>",
        broad_area="west",
        availability_start=Profile.AvailabilityStart.TODAY,
        available_from=timezone.now() - timezone.timedelta(hours=1),
    )
    coffee = Interest.objects.get(name="Coffee")
    target.interests.add(coffee)
    visible_plan = create_test_plan(
        owner=target_user,
        title="Visible public profile plan",
        status=Plan.Status.APPROVED,
        starts_at=timezone.now() + timezone.timedelta(days=1),
    )
    create_test_plan(
        owner=target_user,
        title="Hidden cancelled profile plan",
        status=Plan.Status.CANCELLED,
    )
    PlatformSubscription.objects.create(
        user=target_user,
        stripe_customer_id="cus_private_profile_http",
    )
    unverified = Profile.objects.create(
        user=create_test_user(),
        display_name="Hidden unverified profile",
        broad_area="central",
    )
    inactive = create_verified_test_profile(
        user=create_test_user(is_active=False),
        display_name="Hidden inactive profile",
        broad_area="central",
    )
    blocked_by_viewer = create_verified_test_profile(broad_area="central")
    viewer_blocked_by = create_verified_test_profile(broad_area="central")
    Block.objects.create(blocker=viewer, blocked_user=blocked_by_viewer.user)
    Block.objects.create(blocker=viewer_blocked_by.user, blocked_user=viewer)
    client = Client()
    client.force_login(viewer)

    response = client.get(reverse("profile_detail", args=[target.pk]))

    assert response.status_code == 200
    assert b"Public target name" in response.content
    assert b"West" in response.content
    assert b"Coffee" in response.content
    assert b"Open to company" in response.content
    assert visible_plan.title.encode() in response.content
    assert reverse("plan_detail", args=[visible_plan.pk]).encode() in response.content
    assert b"Hidden cancelled profile plan" not in response.content
    assert b"&lt;script&gt;" in response.content
    assert b"<script>" not in response.content
    assert b"private_target_login" not in response.content
    assert b"cus_private_profile_http" not in response.content

    unverified_response = client.get(reverse("profile_detail", args=[unverified.pk]))
    assert unverified_response.status_code == 200
    assert b"Hidden unverified profile" in unverified_response.content

    discovery_response = client.get(reverse("discover"))
    assert discovery_response.status_code == 200
    assert b"Hidden unverified profile" in discovery_response.content
    assert blocked_by_viewer.display_name.encode() not in discovery_response.content
    assert viewer_blocked_by.display_name.encode() not in discovery_response.content
    assert b"Hidden inactive profile" not in discovery_response.content

    hidden_profile_ids = (
        999999,
        inactive.pk,
        blocked_by_viewer.pk,
        viewer_blocked_by.pk,
    )
    hidden_responses = [
        client.get(reverse("profile_detail", args=[profile_id]))
        for profile_id in hidden_profile_ids
    ]
    assert {hidden_response.status_code for hidden_response in hidden_responses} == {
        404
    }
    assert {hidden_response.content for hidden_response in hidden_responses} == {
        b"Profile unavailable."
    }
    assert client.post(reverse("profile_detail", args=[target.pk])).status_code == 405
