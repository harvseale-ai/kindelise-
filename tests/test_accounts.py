"""Test Kindelise account and profile behaviour."""

from types import SimpleNamespace

import pytest
from django.contrib import admin as django_admin
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from kindlelise.admin import (
    verify_selected_profiles_for_discovery_plans_and_messages,
)
from kindlelise.models import (
    Interest,
    Profile,
)
from kindlelise.policies import (
    can_access_discovery_plans_and_messages,
)
from tests.conftest import (
    create_test_user,
    create_verified_test_profile,
)

pytestmark = pytest.mark.django_db


def test_registration_http_creates_unverified_profile_without_authenticating():
    client = Client()

    response = client.post(
        reverse("sign_up"),
        {
            "email": "Phase4.Student@Example.Test",
            "password1": "Test-pass-742!",
            "password2": "Test-pass-742!",
            "is_staff": "on",
        },
    )

    account = get_user_model().objects.get(username="phase4.student@example.test")
    assert response.status_code == 302
    assert response.url == reverse("sign_in")
    assert account.email == "phase4.student@example.test"
    assert not account.is_staff
    assert not account.profile.is_verified
    assert "_auth_user_id" not in client.session

    invalid_response = client.post(
        reverse("sign_up"),
        {
            "email": "not-created@example.test",
            "password1": "Test-pass-742!",
            "password2": "Different-pass-853!",
        },
    )
    assert invalid_response.status_code == 200
    assert (
        not get_user_model()
        .objects.filter(username="not-created@example.test")
        .exists()
    )
    assert not Profile.objects.filter(
        user__username="not-created@example.test"
    ).exists()


def test_sign_in_http_uses_generic_failure_and_only_safe_local_next():
    active_account = create_test_user(
        username="active@example.test",
        email="active@example.test",
    )
    Profile.objects.create(user=active_account)
    inactive_account = create_test_user(
        username="inactive@example.test",
        email="inactive@example.test",
        is_active=False,
    )
    Profile.objects.create(user=inactive_account)
    client = Client()

    missing_response = client.post(
        reverse("sign_in"),
        {"username": "missing@example.test", "password": "Test-pass-742!"},
    )
    inactive_response = client.post(
        reverse("sign_in"),
        {"username": inactive_account.username, "password": "Test-pass-742!"},
    )
    missing_errors = list(missing_response.context["form"].non_field_errors())
    inactive_errors = list(inactive_response.context["form"].non_field_errors())

    assert missing_response.status_code == 200
    assert inactive_response.status_code == 200
    assert (
        missing_errors
        == inactive_errors
        == ["The email address or password was not accepted."]
    )
    assert "_auth_user_id" not in client.session

    session = client.session
    session["before_login"] = "retained"
    session.save()
    previous_session_key = session.session_key
    local_response = client.post(
        reverse("sign_in"),
        {
            "username": "ACTIVE@EXAMPLE.TEST",
            "password": "Test-pass-742!",
            "next": reverse("profile_edit"),
        },
    )
    assert local_response.status_code == 302
    assert local_response.url == reverse("profile_edit")
    assert client.session.session_key != previous_session_key
    assert client.session["_auth_user_id"] == str(active_account.pk)

    client.post(reverse("sign_out"))
    external_response = client.post(
        reverse("sign_in") + "?next=https://attacker.example/leave",
        {
            "username": "ACTIVE@EXAMPLE.TEST",
            "password": "Test-pass-742!",
            "next": "https://attacker.example/leave",
        },
    )
    assert external_response.status_code == 302
    assert external_response.url == reverse("home")
    home_response = client.get(reverse("home"))
    assert home_response.status_code == 302
    assert home_response.url == reverse("plan_list")


def test_profile_edit_http_changes_only_owner_fields_and_clears_availability():
    account = create_test_user()
    profile = Profile.objects.create(user=account)
    other_profile = Profile.objects.create(
        user=create_test_user(),
        display_name="Other unchanged",
    )
    coffee = Interest.objects.get(name="Coffee")
    client = Client()
    client.force_login(account)

    get_response = client.get(reverse("profile_edit"))
    assert get_response.status_code == 200
    assert b"Open to company" in get_response.content
    assert b"Available from" in get_response.content
    assert all(
        label in get_response.content
        for label in (b"Today", b"Tomorrow", b"This week", b"As and when")
    )
    assert tuple(get_response.context["form"].fields) == (
        "profile_image",
        "display_name",
        "title_statement",
        "biography",
        "broad_area",
        "free_now",
        "availability_start",
        "interests",
    )
    assert b"multipart/form-data" in get_response.content

    update_response = client.post(
        reverse("profile_edit"),
        {
            "display_name": "HTTP student",
            "title_statement": "Always up for coffee and museums",
            "biography": "A browser-updated biography.",
            "broad_area": ["north", "east"],
            "free_now": "on",
            "availability_start": "",
            "interests": [str(coffee.pk)],
            "user": other_profile.user_id,
            "is_verified": "on",
            "stripe_status": "active",
        },
    )
    profile.refresh_from_db()
    other_profile.refresh_from_db()

    assert update_response.status_code == 302
    assert update_response.url == reverse("account")
    assert profile.display_name == "HTTP student"
    assert profile.title_statement == "Always up for coffee and museums"
    assert profile.broad_area == "north"
    assert profile.broad_areas == ["north", "east"]
    assert profile.availability_start == Profile.AvailabilityStart.TODAY
    assert profile.available_from <= timezone.now()
    assert list(profile.interests.all()) == [coffee]
    assert not profile.is_verified
    assert other_profile.display_name == "Other unchanged"

    clear_response = client.post(
        reverse("profile_edit"),
        {
            "display_name": "HTTP student",
            "biography": "",
            "broad_area": "central",
            "availability_start": "",
            "interests": [],
        },
    )
    profile.refresh_from_db()
    assert clear_response.status_code == 302
    assert profile.availability_start == ""
    assert profile.available_from is None
    assert profile.broad_areas == ["central"]
    assert not profile.interests.exists()


def test_staff_verification_action_changes_only_complete_configured_profiles(
    monkeypatch,
):
    staff = create_test_user(is_staff=True, is_superuser=True)
    eligible = Profile.objects.create(
        user=create_test_user(),
        display_name="Eligible student",
        broad_area="central",
    )
    empty_name = Profile.objects.create(
        user=create_test_user(),
        display_name="   ",
        broad_area="central",
    )
    unknown_area = Profile.objects.create(
        user=create_test_user(),
        display_name="Unknown area",
        broad_area="unconfigured",
    )
    already_verified = create_verified_test_profile()
    original_review = (
        already_verified.verified_at,
        already_verified.verified_by_id,
    )
    profile_admin = django_admin.site._registry[Profile]
    staff_messages = []
    monkeypatch.setattr(
        profile_admin,
        "message_user",
        lambda request, message, **kwargs: staff_messages.append(message),
    )

    verify_selected_profiles_for_discovery_plans_and_messages(
        profile_admin,
        SimpleNamespace(user=staff),
        Profile.objects.filter(
            pk__in=(
                eligible.pk,
                empty_name.pk,
                unknown_area.pk,
                already_verified.pk,
            )
        ),
    )

    eligible.refresh_from_db()
    empty_name.refresh_from_db()
    unknown_area.refresh_from_db()
    already_verified.refresh_from_db()
    assert eligible.is_verified
    assert eligible.verified_at is not None
    assert eligible.verified_by == staff
    assert can_access_discovery_plans_and_messages(eligible.user)
    assert not empty_name.is_verified
    assert not unknown_area.is_verified
    assert (
        already_verified.verified_at,
        already_verified.verified_by_id,
    ) == original_review
    assert staff_messages == ["Verified 1 profile(s); skipped 3."]
