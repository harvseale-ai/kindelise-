"""Test Kindelise discovery behaviour."""

# KEYWORD: test — an automatic check that proves one expected behaviour still works.
# KEYWORD: assert — compares the actual result with the result the check expects.
# KEYWORD: monkeypatch — temporarily replaces a setting or outside call for one check, then restores it.
# KEYWORD: HTTP — the request-and-response rules used when these checks visit a page.
# KEYWORD: CSRF — the private form check that prevents another website submitting as the signed-in visitor.
# KEYWORD: PostgreSQL — the database used by the live site to keep saved information and its rules.

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from kindlelise.forms import (
    DiscoveryFiltersForm,
)
from kindlelise.models import (
    Block,
    Interest,
    Plan,
    PlatformSubscription,
    Profile,
)
from kindlelise.policies import (
    get_allowed_discovery_areas_and_interest_limit,
)
from kindlelise.selectors import (
    get_profiles_for_discovery_grid,
)
from tests.conftest import (
    create_test_plan,
    create_test_user,
    create_verified_test_profile,
)

pytestmark = pytest.mark.django_db


# WHY: Checks that discovery http gates access and renders only authorized profiles so a future change cannot quietly break it.


# WHY: Checks that discovery profile http is safe and uses one generic hidden response so a future change cannot quietly break it.
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
    assert b"Free now" in response.content
    assert visible_plan.title.encode() in response.content
    assert reverse("plan_detail", args=[visible_plan.pk]).encode() in response.content
    assert b"Hidden cancelled profile plan" not in response.content
    assert b"&lt;script&gt;" in response.content
    assert b"<script>" not in response.content
    assert b"private_target_login" not in response.content
    assert b"cus_private_profile_http" not in response.content

    hidden_profile_ids = (
        999999,
        unverified.pk,
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


# WHY: Checks that discovery selector excludes hidden profiles before presentation so a future change cannot quietly break it.
def test_discovery_selector_excludes_hidden_profiles_before_presentation():
    viewer = create_test_user()
    create_verified_test_profile(user=viewer, broad_area="central")
    coffee = Interest.objects.get(name="Coffee")
    walking = Interest.objects.get(name="Walking")
    future = timezone.now() + timezone.timedelta(hours=2)
    past = timezone.now() - timezone.timedelta(minutes=1)

    eligible = create_verified_test_profile(
        display_name="Eligible",
        broad_area="central",
        available_from=past,
    )
    not_started = create_verified_test_profile(
        display_name="Not started",
        broad_area="central",
        available_from=future,
    )
    no_availability = create_verified_test_profile(
        display_name="No availability",
        broad_area="central",
    )
    wrong_interest = create_verified_test_profile(
        display_name="Wrong interest",
        broad_area="central",
        available_from=past,
    )
    wrong_area = create_verified_test_profile(
        display_name="Wrong area",
        broad_area="north",
        available_from=past,
    )
    unverified = Profile.objects.create(
        user=create_test_user(),
        display_name="Unverified",
        broad_area="central",
        availability_start=Profile.AvailabilityStart.TODAY,
        available_from=past,
    )
    inactive = create_verified_test_profile(
        user=create_test_user(is_active=False),
        display_name="Inactive",
        broad_area="central",
        available_from=past,
    )
    blocked_by_viewer = create_verified_test_profile(
        display_name="Blocked by viewer",
        broad_area="central",
        available_from=past,
    )
    viewer_blocked_by = create_verified_test_profile(
        display_name="Viewer blocked by target",
        broad_area="central",
        available_from=past,
    )
    for profile in (
        eligible,
        not_started,
        no_availability,
        wrong_area,
        unverified,
        inactive,
        blocked_by_viewer,
        viewer_blocked_by,
    ):
        profile.interests.add(coffee)
    wrong_interest.interests.add(walking)
    Block.objects.create(blocker=viewer, blocked_user=blocked_by_viewer.user)
    Block.objects.create(blocker=viewer_blocked_by.user, blocked_user=viewer)

    allowed_areas, interest_limit = get_allowed_discovery_areas_and_interest_limit(
        viewer
    )
    available_form = DiscoveryFiltersForm(
        data={
            "broad_area": ["central"],
            "interests": [str(coffee.pk)],
            "available_now": "on",
        },
        allowed_areas=allowed_areas,
        interest_limit=interest_limit,
    )
    assert available_form.is_valid(), available_form.errors

    available_profiles = get_profiles_for_discovery_grid(
        viewer,
        available_form.cleaned_data,
    )
    all_current_area_profiles = get_profiles_for_discovery_grid(
        viewer,
        {
            "broad_area": "central",
            "interests": [coffee],
            "available_now": False,
        },
    )

    assert list(available_profiles) == [eligible]
    assert set(all_current_area_profiles) == {
        eligible,
        not_started,
        no_availability,
    }

    # WHY: Confirms the page uses the same filtered result and does not reveal why other profiles are hidden.
    client = Client()
    client.force_login(viewer)
    response = client.get(reverse("discover"))
    assert response.status_code == 200
    assert eligible.display_name.encode() in response.content
    assert blocked_by_viewer.display_name.encode() not in response.content
    assert viewer_blocked_by.display_name.encode() not in response.content
    assert unverified.display_name.encode() not in response.content
    assert inactive.display_name.encode() not in response.content
    assert client.post(reverse("discover")).status_code == 405

    # WHY: Stops an unverified account before any discovery results are loaded.
    unverified_viewer = create_test_user()
    Profile.objects.create(user=unverified_viewer)
    client.force_login(unverified_viewer)
    refused_response = client.get(reverse("discover"))
    assert refused_response.status_code == 302
    assert refused_response.url == reverse("account")
