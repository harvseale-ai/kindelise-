"""Prove the implemented Kindlelise vertical-slice behaviour."""

import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from threading import Barrier
from types import SimpleNamespace

import pytest
from django.apps import apps
from django.contrib import admin as django_admin
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.models import AnonymousUser, Permission
from django.core.exceptions import PermissionDenied
from django.db import (
    IntegrityError,
    close_old_connections,
    connection,
    connections,
    models,
    transaction,
)
from django.test import Client, TransactionTestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone
from django.utils.html import conditional_escape

from kindlelise.admin import (
    KindleliseUserAdmin,
    approve_selected_plans_after_manual_url_check,
    reject_selected_plans,
    remove_verification_from_selected_profiles,
    verify_selected_profiles_for_discovery_plans_and_messages,
)
import kindlelise.ai_message_editor as ai_message_editor
from kindlelise.ai_message_editor import get_edited_message_draft_suggestion
from kindlelise.forms import (
    AccountSignUpForm,
    DiscoveryFiltersForm,
    MessageDraftForm,
    MessageEditRequestForm,
    PlanDetailsForm,
    PrivateReportForm,
    ProfileDetailsForm,
)
from kindlelise.models import (
    Block,
    Conversation,
    Interest,
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
    can_show_profile_in_discovery_grid,
    can_start_or_continue_direct_messages,
    can_view_profile_page,
    get_allowed_discovery_areas_and_interest_limit,
)
from kindlelise.selectors import (
    get_messages_if_user_can_open_conversation,
    get_plan_page_if_viewer_is_allowed,
    get_plans_for_plan_list,
    get_profile_page_if_viewer_is_allowed,
    get_profiles_for_discovery_grid,
    get_report_target_profile_if_reporter_is_allowed,
    get_signed_in_user_account_summary,
    get_unblocked_conversations_for_inbox,
)
from kindlelise.services import (
    block_user_from_discovery_and_messages,
    cancel_owned_plan_and_hide_it_from_discovery,
    create_account_and_profile,
    create_plan_waiting_for_staff_review,
    find_or_start_direct_conversation,
    join_approved_plan_and_lock_meeting_details,
    leave_plan_and_keep_participation_history,
    open_stripe_customer_portal,
    send_direct_message,
    start_stripe_subscription_checkout,
    submit_private_report_about_user,
    update_premium_access_from_verified_stripe_event,
    update_owned_plan_before_first_join,
    update_signed_in_user_profile,
)
from tests.conftest import (
    build_stripe_test_event,
    create_test_conversation,
    create_test_plan,
    create_test_user,
    create_verified_test_profile,
    replace_ollama_request_with_fake,
)

pytestmark = pytest.mark.django_db


def test_interest_migration_creates_exact_controlled_vocabulary():
    assert set(Interest.objects.values_list("name", flat=True)) == {
        "Coffee",
        "Walking",
        "Museums",
        "Live music",
        "Cinema",
        "Food",
        "Games",
        "Study",
    }
    assert str(Interest.objects.get(name="Coffee")) == "Coffee"
    with pytest.raises(IntegrityError), transaction.atomic():
        Interest.objects.create(name="Coffee")


def test_migration_uses_postgresql_and_exact_model_inventory():
    assert connection.vendor == "postgresql"
    registered_models = {
        model.__name__
        for model in apps.get_app_config("kindlelise").get_models()
    }
    assert registered_models == {
        "Profile",
        "Interest",
        "Plan",
        "Participation",
        "Conversation",
        "Message",
        "Block",
        "Report",
        "PlatformSubscription",
        "StripeWebhookReceipt",
    }
    assert Profile._meta.get_field("interests").remote_field.through._meta.auto_created


def test_account_sign_up_form_creates_unverified_profile_with_email_and_hashed_password():
    form = AccountSignUpForm(
        data={
            "email": "New.Student@Example.Test",
            "password1": "Test-pass-742!",
            "password2": "Test-pass-742!",
        }
    )

    assert tuple(form.fields) == ("email", "password1", "password2")
    assert form.is_valid(), form.errors

    account = create_account_and_profile(form.cleaned_data)
    profile = account.profile

    assert account.username == "new.student@example.test"
    assert account.email == "new.student@example.test"
    assert account.check_password("Test-pass-742!")
    assert account.password != "Test-pass-742!"
    assert authenticate(
        username="new.student@example.test",
        password="Test-pass-742!",
    ) == account
    assert profile.display_name == ""
    assert profile.broad_area == ""
    assert not profile.is_verified


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

    account = get_user_model().objects.get(
        username="phase4.student@example.test"
    )
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
    assert not get_user_model().objects.filter(
        username="not-created@example.test"
    ).exists()
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
    assert missing_errors == inactive_errors == [
        "The email address or password was not accepted."
    ]
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


def test_home_http_redirects_by_current_authentication_and_verification_state():
    anonymous_client = Client()
    assert anonymous_client.get(reverse("home")).url == reverse("sign_in")

    unverified_account = create_test_user()
    Profile.objects.create(user=unverified_account)
    unverified_client = Client()
    unverified_client.force_login(unverified_account)
    assert unverified_client.get(reverse("home")).url == reverse("account")

    verified_account = create_test_user()
    create_verified_test_profile(user=verified_account)
    verified_client = Client()
    verified_client.force_login(verified_account)
    verified_response = verified_client.get(reverse("home"))
    assert verified_response.status_code == 302
    assert verified_response.url == reverse("discover")


def test_discovery_http_gates_access_and_renders_only_authorized_profiles():
    viewer = create_test_user()
    create_verified_test_profile(user=viewer, broad_area="central")
    visible = create_verified_test_profile(
        display_name="Visible discovery profile",
        broad_area="central",
    )
    blocked = create_verified_test_profile(
        display_name="Blocked discovery profile",
        broad_area="central",
    )
    unverified = Profile.objects.create(
        user=create_test_user(),
        display_name="Unverified discovery profile",
        broad_area="central",
    )
    inactive = create_verified_test_profile(
        user=create_test_user(is_active=False),
        display_name="Inactive discovery profile",
        broad_area="central",
    )
    nearby = create_verified_test_profile(
        display_name="Nearby free-hidden profile",
        broad_area="north",
    )
    Block.objects.create(blocker=blocked.user, blocked_user=viewer)
    client = Client()
    client.force_login(viewer)

    response = client.get(reverse("discover"))

    assert response.status_code == 200
    assert visible.display_name.encode() in response.content
    assert reverse("profile_detail", args=[visible.pk]).encode() in response.content
    assert blocked.display_name.encode() not in response.content
    assert unverified.display_name.encode() not in response.content
    assert inactive.display_name.encode() not in response.content
    assert nearby.display_name.encode() not in response.content
    assert b"hidden result" not in response.content.lower()
    assert client.post(reverse("discover")).status_code == 405

    anonymous_response = Client().get(reverse("discover"))
    assert anonymous_response.status_code == 302
    assert anonymous_response.url.startswith(reverse("sign_in"))

    unverified_viewer = create_test_user()
    Profile.objects.create(user=unverified_viewer)
    unverified_client = Client()
    unverified_client.force_login(unverified_viewer)
    unverified_response = unverified_client.get(reverse("discover"))
    assert unverified_response.status_code == 302
    assert unverified_response.url == reverse("account")


def test_discovery_http_enforces_free_and_premium_area_and_interest_limits():
    viewer = create_test_user()
    create_verified_test_profile(user=viewer, broad_area="central")
    nearby = create_verified_test_profile(
        display_name="Premium nearby profile",
        broad_area="north",
    )
    interests = list(Interest.objects.order_by("pk")[:6])
    nearby.interests.add(interests[0])
    client = Client()
    client.force_login(viewer)

    free_nearby_response = client.get(
        reverse("discover"),
        {"broad_area": "north"},
    )
    free_excess_response = client.get(
        reverse("discover"),
        {
            "broad_area": "central",
            "interests": [str(interest.pk) for interest in interests[:3]],
        },
    )
    assert free_nearby_response.status_code == 200
    assert b"Select a valid choice" in free_nearby_response.content
    assert nearby.display_name.encode() not in free_nearby_response.content
    assert b"Select no more than 2 interests" in free_excess_response.content

    PlatformSubscription.objects.create(
        user=viewer,
        stripe_status="active",
        access_until=timezone.now() + timezone.timedelta(days=1),
    )
    premium_response = client.get(
        reverse("discover"),
        {
            "broad_area": "north",
            "interests": [str(interest.pk) for interest in interests[:5]],
        },
    )
    premium_excess_response = client.get(
        reverse("discover"),
        {
            "broad_area": "north",
            "interests": [str(interest.pk) for interest in interests],
        },
    )
    assert premium_response.status_code == 200
    assert nearby.display_name.encode() in premium_response.content
    assert b"up to 5 interests" in premium_response.content
    assert b"Select no more than 5 interests" in premium_excess_response.content


def test_discovery_http_free_now_shows_only_started_availability():
    viewer = create_test_user()
    create_verified_test_profile(user=viewer, broad_area="central")
    started_profile = create_verified_test_profile(
        display_name="Started available profile",
        broad_area="central",
        available_from=timezone.now() - timezone.timedelta(seconds=1),
    )
    future_profile = create_verified_test_profile(
        display_name="Future available profile",
        broad_area="central",
        available_from=timezone.now() + timezone.timedelta(hours=1),
    )
    no_availability_profile = create_verified_test_profile(
        display_name="No availability profile",
        broad_area="central",
    )
    client = Client()
    client.force_login(viewer)

    response = client.get(
        reverse("discover"),
        {"broad_area": "central", "available_now": "on"},
    )

    assert response.status_code == 200
    assert started_profile.display_name.encode() in response.content
    assert b"Free now" in response.content
    assert future_profile.display_name.encode() not in response.content
    assert no_availability_profile.display_name.encode() not in response.content


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


def test_account_http_is_private_and_explains_unverified_state():
    account = create_test_user(username="private_account")
    Profile.objects.create(
        user=account,
        display_name="Private student",
        broad_area="central",
    )
    other_account = create_test_user(username="other_private_account")
    Profile.objects.create(user=other_account, display_name="Hidden student")
    Report.objects.create(
        reporter=other_account,
        reported_user=account,
        category=Report.Category.OTHER,
        description="Private account report marker",
    )
    anonymous_response = Client().get(reverse("account"))
    client = Client()
    client.force_login(account)

    response = client.get(reverse("account"))

    assert anonymous_response.status_code == 302
    assert anonymous_response.url.startswith(reverse("sign_in"))
    assert response.status_code == 200
    assert b"Private student" in response.content
    assert b"waiting for staff verification" in response.content
    assert b"Hidden student" not in response.content
    assert b"stripe_customer" not in response.content
    assert b"Private account report marker" not in response.content


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
    assert b"Free now" in get_response.content
    assert b"Available from" in get_response.content
    assert all(
        label in get_response.content
        for label in (b"Today", b"Tomorrow", b"This week", b"As and when")
    )
    assert tuple(get_response.context["form"].fields) == (
        "display_name",
        "biography",
        "broad_area",
        "free_now",
        "availability_start",
        "interests",
    )

    update_response = client.post(
        reverse("profile_edit"),
        {
            "display_name": "HTTP student",
            "biography": "A browser-updated biography.",
            "broad_area": "north",
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
    assert profile.broad_area == "north"
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
    assert not profile.interests.exists()


def test_sign_out_http_requires_post_and_valid_csrf_before_ending_session():
    account = create_test_user()
    Profile.objects.create(user=account)
    client = Client(enforce_csrf_checks=True)
    client.force_login(account)

    get_response = client.get(reverse("sign_out"))
    missing_csrf_response = client.post(reverse("sign_out"))
    assert get_response.status_code == 405
    assert missing_csrf_response.status_code == 403
    assert client.session["_auth_user_id"] == str(account.pk)

    account_response = client.get(reverse("account"))
    csrf_token = client.cookies["csrftoken"].value
    valid_response = client.post(
        reverse("sign_out"),
        {"csrfmiddlewaretoken": csrf_token},
        HTTP_REFERER=f"http://testserver{account_response.request['PATH_INFO']}",
    )
    assert valid_response.status_code == 302
    assert valid_response.url == reverse("sign_in")
    assert "_auth_user_id" not in client.session


def test_duplicate_or_invalid_account_details_are_rejected_without_writes():
    create_test_user(
        username="existing@example.test",
        email="existing@example.test",
    )
    valid_password = "Test-pass-742!"

    duplicate_form = AccountSignUpForm(
        data={
            "email": "EXISTING@EXAMPLE.TEST",
            "password1": valid_password,
            "password2": valid_password,
        }
    )
    invalid_email_form = AccountSignUpForm(
        data={
            "email": "not-an-email",
            "password1": valid_password,
            "password2": valid_password,
        }
    )
    invalid_password_form = AccountSignUpForm(
        data={
            "email": "another@example.test",
            "password1": "12345678",
            "password2": "12345678",
        }
    )
    mismatched_password_form = AccountSignUpForm(
        data={
            "email": "mismatched@example.test",
            "password1": valid_password,
            "password2": "Different-pass-853!",
        }
    )

    assert not duplicate_form.is_valid()
    assert "email" in duplicate_form.errors
    assert not invalid_email_form.is_valid()
    assert "email" in invalid_email_form.errors
    assert not invalid_password_form.is_valid()
    assert "password2" in invalid_password_form.errors
    assert not mismatched_password_form.is_valid()
    assert "password2" in mismatched_password_form.errors
    assert Profile.objects.count() == 0


def test_account_and_profile_creation_rolls_back_when_profile_write_fails(
    monkeypatch,
):
    def refuse_profile_creation(*args, **kwargs):
        raise RuntimeError("synthetic profile failure")

    monkeypatch.setattr(Profile.objects, "create", refuse_profile_creation)

    with pytest.raises(RuntimeError, match="synthetic profile failure"):
        create_account_and_profile(
            {
                "email": "rolled-back@example.test",
                "password1": "Test-pass-742!",
            }
        )

    assert not Profile.objects.filter(
        user__username="rolled-back@example.test"
    ).exists()
    assert not get_user_model().objects.filter(
        username="rolled-back@example.test"
    ).exists()


def test_profile_details_form_rejects_unknown_and_oversized_values():
    profile = Profile.objects.create(user=create_test_user())

    invalid_form = ProfileDetailsForm(
        data={
            "display_name": "   ",
            "biography": "x" * 501,
            "broad_area": "unconfigured-area",
            "availability_start": "not-an-option",
            "interests": ["999999"],
            "is_verified": "true",
        },
        instance=profile,
    )
    oversized_name_form = ProfileDetailsForm(
        data={
            "display_name": "x" * 81,
            "biography": "",
            "broad_area": "central",
            "availability_start": "",
            "interests": [],
        },
        instance=profile,
    )

    assert tuple(invalid_form.fields) == (
        "display_name",
        "biography",
        "broad_area",
        "free_now",
        "availability_start",
        "interests",
    )
    assert not invalid_form.is_valid()
    assert {
        "display_name",
        "biography",
        "broad_area",
        "availability_start",
        "interests",
    } <= set(
        invalid_form.errors
    )
    assert "is_verified" not in invalid_form.fields
    assert not oversized_name_form.is_valid()
    assert "display_name" in oversized_name_form.errors


@pytest.mark.parametrize("choice", ["today", "this_week", "as_and_when"])
def test_immediate_availability_choices_start_at_submission_time(monkeypatch, choice):
    fixed_time = timezone.make_aware(datetime(2026, 7, 27, 15, 30))
    monkeypatch.setattr("kindlelise.forms.timezone.now", lambda: fixed_time)
    form = ProfileDetailsForm(
        data={
            "display_name": "Optional availability",
            "biography": "",
            "broad_area": "central",
            "availability_start": choice,
            "interests": [],
        },
        instance=Profile.objects.create(user=create_test_user()),
    )

    assert form.is_valid(), form.errors
    assert form.cleaned_data["available_from"] == fixed_time


def test_tomorrow_availability_starts_at_next_local_midnight(monkeypatch):
    fixed_time = timezone.make_aware(datetime(2026, 7, 27, 15, 30))
    monkeypatch.setattr("kindlelise.forms.timezone.now", lambda: fixed_time)
    form = ProfileDetailsForm(
        data={
            "display_name": "Tomorrow profile",
            "biography": "",
            "broad_area": "central",
            "availability_start": "tomorrow",
            "interests": [],
        },
        instance=Profile.objects.create(user=create_test_user()),
    )

    assert form.is_valid(), form.errors
    local_start = timezone.localtime(form.cleaned_data["available_from"])
    assert local_start.date().isoformat() == "2026-07-28"
    assert (local_start.hour, local_start.minute, local_start.second) == (0, 0, 0)


def test_profile_completion_accepts_availability_added_later():
    form = ProfileDetailsForm(
        data={
            "display_name": "Complete without availability",
            "biography": "",
            "broad_area": "central",
            "availability_start": "",
            "interests": [],
        },
        instance=Profile.objects.create(user=create_test_user()),
    )

    assert form.is_valid(), form.errors
    assert form.cleaned_data["available_from"] is None


def test_signed_in_user_profile_update_replaces_and_clears_permitted_values():
    account = create_test_user()
    previous_availability = timezone.now() + timezone.timedelta(minutes=30)
    profile = Profile.objects.create(
        user=account,
        availability_start=Profile.AvailabilityStart.TOMORROW,
        available_from=previous_availability,
    )
    other_profile = Profile.objects.create(user=create_test_user())
    coffee = Interest.objects.get(name="Coffee")
    walking = Interest.objects.get(name="Walking")
    first_form = ProfileDetailsForm(
        data={
            "display_name": "Student One",
            "biography": "A short synthetic biography.",
            "broad_area": "north",
            "availability_start": "today",
            "interests": [str(coffee.pk), str(walking.pk)],
        },
        instance=profile,
    )
    assert first_form.is_valid(), first_form.errors

    profile_changes = dict(first_form.cleaned_data)
    profile_changes.update(
        {
            "user": other_profile.user,
            "is_verified": True,
            "verified_at": timezone.now(),
            "verified_by": create_test_user(is_staff=True),
            "stripe_status": "active",
        }
    )
    updated_profile = update_signed_in_user_profile(account, profile_changes)
    updated_profile.refresh_from_db()

    assert updated_profile.user == account
    assert updated_profile.display_name == "Student One"
    assert updated_profile.biography == "A short synthetic biography."
    assert updated_profile.broad_area == "north"
    assert updated_profile.availability_start == Profile.AvailabilityStart.TODAY
    assert updated_profile.available_from is not None
    assert updated_profile.available_from != previous_availability
    assert updated_profile.is_available_now(timezone.now())
    assert set(updated_profile.interests.all()) == {coffee, walking}
    assert not updated_profile.is_verified
    assert updated_profile.verified_at is None
    assert updated_profile.verified_by is None
    assert other_profile.display_name == ""

    clear_form = ProfileDetailsForm(
        data={
            "display_name": "Student One",
            "biography": "",
            "broad_area": "central",
            "availability_start": "",
            "interests": [],
        },
        instance=updated_profile,
    )
    assert clear_form.is_valid(), clear_form.errors
    update_signed_in_user_profile(account, clear_form.cleaned_data)
    updated_profile.refresh_from_db()

    assert updated_profile.availability_start == ""
    assert updated_profile.available_from is None
    assert updated_profile.broad_area == "central"
    assert not updated_profile.interests.exists()


def test_profile_update_refuses_every_account_without_active_ownership():
    inactive_account = create_test_user(is_active=False)
    Profile.objects.create(user=inactive_account)
    missing_profile_account = create_test_user()
    profile_changes = {
        "display_name": "Refused change",
        "biography": "",
        "broad_area": "central",
        "availability_start": "",
        "available_from": None,
        "interests": [],
    }

    with pytest.raises(PermissionDenied):
        update_signed_in_user_profile(AnonymousUser(), profile_changes)
    with pytest.raises(PermissionDenied):
        update_signed_in_user_profile(inactive_account, profile_changes)
    with pytest.raises(PermissionDenied):
        update_signed_in_user_profile(missing_profile_account, profile_changes)

    assert Profile.objects.get(user=inactive_account).display_name == ""


def test_account_profile_access_policy_fails_closed_for_ineligible_states():
    missing_profile_account = create_test_user()
    unverified_account = create_test_user()
    Profile.objects.create(user=unverified_account)
    verified_account = create_test_user()
    create_verified_test_profile(user=verified_account)
    inactive_account = create_test_user(is_active=False)
    create_verified_test_profile(user=inactive_account)

    assert not can_access_discovery_plans_and_messages(AnonymousUser())
    assert not can_access_discovery_plans_and_messages(missing_profile_account)
    assert not can_access_discovery_plans_and_messages(unverified_account)
    assert not can_access_discovery_plans_and_messages(inactive_account)
    assert can_access_discovery_plans_and_messages(verified_account)


def test_admin_registers_models_with_only_mapped_profile_and_plan_actions():
    registered_models = set(django_admin.site._registry)

    assert {
        Profile,
        Interest,
        Plan,
        Participation,
        Conversation,
        Message,
        Block,
        Report,
        PlatformSubscription,
        StripeWebhookReceipt,
    } <= registered_models
    assert django_admin.site._registry[Profile].actions == (
        verify_selected_profiles_for_discovery_plans_and_messages,
        remove_verification_from_selected_profiles,
    )
    assert django_admin.site._registry[Plan].actions == (
        approve_selected_plans_after_manual_url_check,
        reject_selected_plans,
    )
    assert django_admin.site._registry[Profile].readonly_fields == (
        "is_verified",
        "verified_at",
        "verified_by",
    )
    assert "stripe_event_id" in django_admin.site._registry[
        StripeWebhookReceipt
    ].readonly_fields
    assert isinstance(
        django_admin.site._registry[get_user_model()],
        KindleliseUserAdmin,
    )


def test_user_admin_permissions_checkbox_verifies_and_withdraws_profile():
    staff = create_test_user(is_staff=True, is_superuser=True)
    account = create_test_user(username="permissions@example.test")
    profile = Profile.objects.create(
        user=account,
        display_name="Permissions profile",
        broad_area="central",
    )
    client = Client()
    client.force_login(staff)
    change_url = reverse("admin:auth_user_change", args=[account.pk])
    joined_local = timezone.localtime(account.date_joined)
    standard_user_fields = {
        "username": account.username,
        "first_name": "",
        "last_name": "",
        "email": account.email,
        "is_active": "on",
        "date_joined_0": joined_local.strftime("%Y-%m-%d"),
        "date_joined_1": joined_local.strftime("%H:%M:%S"),
        "_save": "Save",
    }

    get_response = client.get(change_url)

    assert get_response.status_code == 200
    assert b"Permissions" in get_response.content
    assert b"Profile verified" in get_response.content

    verification_response = client.post(
        change_url,
        {
            **standard_user_fields,
            "profile_verified": "on",
        },
    )
    profile.refresh_from_db()

    assert verification_response.status_code == 302
    assert profile.is_verified
    assert profile.verified_at is not None
    assert profile.verified_by == staff

    withdrawal_response = client.post(
        change_url,
        standard_user_fields,
    )
    profile.refresh_from_db()

    assert withdrawal_response.status_code == 302
    assert not profile.is_verified
    assert profile.verified_at is None
    assert profile.verified_by is None


def test_user_admin_permissions_checkbox_refuses_incomplete_profile():
    staff = create_test_user(is_staff=True, is_superuser=True)
    account = create_test_user(username="incomplete@example.test")
    profile = Profile.objects.create(user=account, broad_area="central")
    client = Client()
    client.force_login(staff)

    response = client.post(
        reverse("admin:auth_user_change", args=[account.pk]),
        {
            "username": account.username,
            "first_name": "",
            "last_name": "",
            "email": account.email,
            "is_active": "on",
            "profile_verified": "on",
            "_save": "Save",
        },
    )
    profile.refresh_from_db()

    assert response.status_code == 200
    assert b"Complete the profile display name and broad area first." in (
        response.content
    )
    assert not profile.is_verified
    assert profile.verified_at is None
    assert profile.verified_by is None


def test_user_admin_hides_profile_checkbox_without_profile_change_permission():
    staff = create_test_user(is_staff=True)
    staff.user_permissions.add(
        Permission.objects.get(
            content_type__app_label="auth",
            codename="change_user",
        )
    )
    account = create_test_user(username="permission-limited@example.test")
    profile = Profile.objects.create(
        user=account,
        display_name="Permission limited",
        broad_area="central",
    )
    client = Client()
    client.force_login(staff)

    response = client.get(reverse("admin:auth_user_change", args=[account.pk]))

    assert response.status_code == 200
    assert b"Profile verified" not in response.content

    joined_local = timezone.localtime(account.date_joined)
    forged_response = client.post(
        reverse("admin:auth_user_change", args=[account.pk]),
        {
            "username": account.username,
            "first_name": "",
            "last_name": "",
            "email": account.email,
            "is_active": "on",
            "profile_verified": "on",
            "date_joined_0": joined_local.strftime("%Y-%m-%d"),
            "date_joined_1": joined_local.strftime("%H:%M:%S"),
            "_save": "Save",
        },
    )
    profile.refresh_from_db()

    assert forged_response.status_code == 302
    assert not profile.is_verified


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


def test_staff_removal_action_clears_verification_and_preserves_records(monkeypatch):
    staff = create_test_user(is_staff=True, is_superuser=True)
    verified = create_verified_test_profile()
    existing_plan = create_test_plan(owner=verified.user)
    already_unverified = Profile.objects.create(user=create_test_user())
    profile_admin = django_admin.site._registry[Profile]
    staff_messages = []
    monkeypatch.setattr(
        profile_admin,
        "message_user",
        lambda request, message, **kwargs: staff_messages.append(message),
    )

    remove_verification_from_selected_profiles(
        profile_admin,
        SimpleNamespace(user=staff),
        Profile.objects.filter(pk__in=(verified.pk, already_unverified.pk)),
    )

    verified.refresh_from_db()
    already_unverified.refresh_from_db()
    assert not verified.is_verified
    assert verified.verified_at is None
    assert verified.verified_by is None
    assert not can_access_discovery_plans_and_messages(verified.user)
    assert not already_unverified.is_verified
    assert Plan.objects.filter(pk=existing_plan.pk).exists()
    assert staff_messages == ["Removed verification from 1 profile(s); skipped 1."]


def test_staff_plan_approval_changes_only_pending_future_unlocked_valid_plan(
    monkeypatch,
):
    staff = create_test_user(is_staff=True, is_superuser=True)
    current_time = timezone.now()
    eligible = create_test_plan()
    past = create_test_plan(starts_at=current_time - timezone.timedelta(minutes=1))
    locked = create_test_plan(meeting_details_locked_at=current_time)
    cancelled = create_test_plan(status=Plan.Status.CANCELLED)
    rejected = create_test_plan(status=Plan.Status.REJECTED)
    invalid_url = create_test_plan(public_url="http://example.test/not-https")
    empty_place = create_test_plan(public_place="")
    already_approved = create_test_plan(status=Plan.Status.APPROVED)
    original_approval = (
        already_approved.approved_at,
        already_approved.approved_by_id,
    )
    plan_admin = django_admin.site._registry[Plan]
    staff_messages = []
    monkeypatch.setattr(
        plan_admin,
        "message_user",
        lambda request, message, **kwargs: staff_messages.append(message),
    )

    approve_selected_plans_after_manual_url_check(
        plan_admin,
        SimpleNamespace(user=staff),
        Plan.objects.filter(
            pk__in=(
                eligible.pk,
                past.pk,
                locked.pk,
                cancelled.pk,
                rejected.pk,
                invalid_url.pk,
                empty_place.pk,
                already_approved.pk,
            )
        ),
    )

    for plan in (
        eligible,
        past,
        locked,
        cancelled,
        rejected,
        invalid_url,
        empty_place,
        already_approved,
    ):
        plan.refresh_from_db()
    assert eligible.status == Plan.Status.APPROVED
    assert eligible.approved_at is not None
    assert eligible.approved_by == staff
    assert past.status == Plan.Status.PENDING
    assert locked.status == Plan.Status.PENDING
    assert cancelled.status == Plan.Status.CANCELLED
    assert rejected.status == Plan.Status.REJECTED
    assert invalid_url.status == Plan.Status.PENDING
    assert empty_place.status == Plan.Status.PENDING
    assert (
        already_approved.approved_at,
        already_approved.approved_by_id,
    ) == original_approval
    assert staff_messages == ["Approved 1 plan(s); skipped 7."]


def test_staff_plan_rejection_changes_only_pending_unlocked_plans(monkeypatch):
    staff = create_test_user(is_staff=True, is_superuser=True)
    current_time = timezone.now()
    future_pending = create_test_plan()
    past_pending = create_test_plan(
        starts_at=current_time - timezone.timedelta(minutes=1)
    )
    locked_pending = create_test_plan(meeting_details_locked_at=current_time)
    approved = create_test_plan(status=Plan.Status.APPROVED)
    rejected = create_test_plan(status=Plan.Status.REJECTED)
    cancelled = create_test_plan(status=Plan.Status.CANCELLED)
    plan_admin = django_admin.site._registry[Plan]
    staff_messages = []
    monkeypatch.setattr(
        plan_admin,
        "message_user",
        lambda request, message, **kwargs: staff_messages.append(message),
    )

    reject_selected_plans(
        plan_admin,
        SimpleNamespace(user=staff),
        Plan.objects.filter(
            pk__in=(
                future_pending.pk,
                past_pending.pk,
                locked_pending.pk,
                approved.pk,
                rejected.pk,
                cancelled.pk,
            )
        ),
    )

    for plan in (
        future_pending,
        past_pending,
        locked_pending,
        approved,
        rejected,
        cancelled,
    ):
        plan.refresh_from_db()
    assert future_pending.status == Plan.Status.REJECTED
    assert future_pending.approved_at is None
    assert future_pending.approved_by is None
    assert past_pending.status == Plan.Status.REJECTED
    assert locked_pending.status == Plan.Status.PENDING
    assert approved.status == Plan.Status.APPROVED
    assert rejected.status == Plan.Status.REJECTED
    assert cancelled.status == Plan.Status.CANCELLED
    assert staff_messages == ["Rejected 2 plan(s); skipped 4."]


def test_non_staff_admin_actions_fail_closed_without_mutation():
    non_staff = create_test_user()
    staff_without_permission = create_test_user(is_staff=True)
    profile = Profile.objects.create(
        user=create_test_user(),
        display_name="Complete profile",
        broad_area="central",
    )
    plan = create_test_plan()
    profile_admin = django_admin.site._registry[Profile]
    plan_admin = django_admin.site._registry[Plan]
    request = SimpleNamespace(user=non_staff)

    with pytest.raises(PermissionDenied):
        verify_selected_profiles_for_discovery_plans_and_messages(
            profile_admin,
            request,
            Profile.objects.filter(pk=profile.pk),
        )
    with pytest.raises(PermissionDenied):
        verify_selected_profiles_for_discovery_plans_and_messages(
            profile_admin,
            SimpleNamespace(user=staff_without_permission),
            Profile.objects.filter(pk=profile.pk),
        )
    with pytest.raises(PermissionDenied):
        remove_verification_from_selected_profiles(
            profile_admin,
            request,
            Profile.objects.filter(pk=profile.pk),
        )
    with pytest.raises(PermissionDenied):
        approve_selected_plans_after_manual_url_check(
            plan_admin,
            request,
            Plan.objects.filter(pk=plan.pk),
        )
    with pytest.raises(PermissionDenied):
        reject_selected_plans(
            plan_admin,
            request,
            Plan.objects.filter(pk=plan.pk),
        )

    profile.refresh_from_db()
    plan.refresh_from_db()
    assert not profile.is_verified
    assert plan.status == Plan.Status.PENDING


def test_account_summary_selector_returns_only_owners_safe_records():
    account = create_test_user(
        username="summary@example.test",
        email="summary@example.test",
    )
    profile = Profile.objects.create(
        user=account,
        display_name="Summary owner",
        broad_area="central",
    )
    own_plan = create_test_plan(owner=account)
    other_account = create_test_user()
    Profile.objects.create(user=other_account)
    create_test_plan(owner=other_account)
    future = timezone.now() + timezone.timedelta(days=2)
    PlatformSubscription.objects.create(
        user=account,
        stripe_customer_id="cus_private_summary",
        stripe_subscription_id="sub_private_summary",
        stripe_status="active",
        access_until=future,
    )
    Report.objects.create(
        reporter=account,
        reported_user=other_account,
        category=Report.Category.OTHER,
        description="Private text excluded from the summary.",
    )
    StripeWebhookReceipt.objects.create(
        stripe_event_id="evt_private_summary",
        event_type="customer.subscription.updated",
        provider_created_at=timezone.now(),
    )

    summary = get_signed_in_user_account_summary(account)

    assert set(summary) == {"account", "profile", "plans", "subscription"}
    assert summary["account"] == {"email": "summary@example.test"}
    assert summary["profile"] == profile
    assert list(summary["plans"]) == [own_plan]
    assert summary["subscription"] == {
        "has_premium_access": True,
        "status": "active",
        "access_until": future,
        "customer_portal_available": True,
        "has_stripe_history": True,
        "trial_available": False,
        "checkout_available": False,
    }
    assert "stripe_customer_id" not in summary["subscription"]
    assert "stripe_subscription_id" not in summary["subscription"]
    assert "reports" not in summary
    assert "webhook_receipts" not in summary
    assert get_signed_in_user_account_summary(AnonymousUser()) is None

    account.is_active = False
    account.save(update_fields=["is_active"])
    assert get_signed_in_user_account_summary(account) is None
    assert get_signed_in_user_account_summary(create_test_user()) is None


def test_discovery_premium_limit_policy_changes_reach_without_weakening_access():
    viewer = create_test_user()
    viewer_profile = create_verified_test_profile(
        user=viewer,
        broad_area="central",
    )
    nearby_profile = create_verified_test_profile(broad_area="north")
    unverified_profile = Profile.objects.create(
        user=create_test_user(),
        display_name="Unverified nearby",
        broad_area="north",
    )

    assert get_allowed_discovery_areas_and_interest_limit(viewer) == (
        ("central",),
        2,
    )
    assert not can_show_profile_in_discovery_grid(viewer, viewer_profile)
    assert not can_show_profile_in_discovery_grid(viewer, nearby_profile)
    assert not can_view_profile_page(viewer, unverified_profile)

    PlatformSubscription.objects.create(
        user=viewer,
        stripe_status="active",
        access_until=timezone.now() + timezone.timedelta(days=1),
    )
    viewer.refresh_from_db()
    allowed_areas, interest_limit = (
        get_allowed_discovery_areas_and_interest_limit(viewer)
    )

    assert allowed_areas == ("central", "north", "south", "east", "west")
    assert interest_limit == 5
    assert can_show_profile_in_discovery_grid(viewer, nearby_profile)

    nearby_results = get_profiles_for_discovery_grid(
        viewer,
        {
            "broad_area": "north",
            "interests": [],
            "available_now": False,
        },
    )
    assert list(nearby_results) == [nearby_profile]

    viewer.platform_subscription.access_until = timezone.now()
    viewer.platform_subscription.save(update_fields=["access_until"])
    assert get_allowed_discovery_areas_and_interest_limit(viewer) == (
        ("central",),
        2,
    )
    assert not get_profiles_for_discovery_grid(
        viewer,
        {
            "broad_area": "north",
            "interests": [],
            "available_now": False,
        },
    ).exists()

    viewer.platform_subscription.access_until = timezone.now() + timezone.timedelta(
        days=1
    )
    viewer.platform_subscription.save(update_fields=["access_until"])

    Block.objects.create(blocker=nearby_profile.user, blocked_user=viewer)
    assert not can_show_profile_in_discovery_grid(viewer, nearby_profile)
    assert not can_view_profile_page(viewer, nearby_profile)


def test_discovery_filter_form_rejects_unknown_and_excessive_filters():
    viewer = create_test_user()
    create_verified_test_profile(user=viewer, broad_area="central")
    interests = list(Interest.objects.order_by("pk")[:6])
    free_areas, free_limit = get_allowed_discovery_areas_and_interest_limit(viewer)

    free_form = DiscoveryFiltersForm(
        data={
            "broad_area": "central",
            "interests": [str(interest.pk) for interest in interests[:2]],
            "available_now": "on",
        },
        allowed_areas=free_areas,
        interest_limit=free_limit,
    )
    free_nearby_form = DiscoveryFiltersForm(
        data={"broad_area": "north", "interests": []},
        allowed_areas=free_areas,
        interest_limit=free_limit,
    )
    free_excess_form = DiscoveryFiltersForm(
        data={
            "broad_area": "central",
            "interests": [str(interest.pk) for interest in interests[:3]],
        },
        allowed_areas=free_areas,
        interest_limit=free_limit,
    )
    unknown_interest_form = DiscoveryFiltersForm(
        data={"broad_area": "central", "interests": ["999999"]},
        allowed_areas=free_areas,
        interest_limit=free_limit,
    )

    assert free_form.is_valid(), free_form.errors
    assert free_form.cleaned_data["available_now"]
    assert not free_nearby_form.is_valid()
    assert "broad_area" in free_nearby_form.errors
    assert not free_excess_form.is_valid()
    assert "interests" in free_excess_form.errors
    assert not unknown_interest_form.is_valid()
    assert "interests" in unknown_interest_form.errors

    PlatformSubscription.objects.create(
        user=viewer,
        stripe_status="trialing",
        access_until=timezone.now() + timezone.timedelta(days=1),
    )
    viewer.refresh_from_db()
    premium_areas, premium_limit = (
        get_allowed_discovery_areas_and_interest_limit(viewer)
    )
    premium_form = DiscoveryFiltersForm(
        data={
            "broad_area": "north",
            "interests": [str(interest.pk) for interest in interests[:5]],
        },
        allowed_areas=premium_areas,
        interest_limit=premium_limit,
    )
    premium_excess_form = DiscoveryFiltersForm(
        data={
            "broad_area": "north",
            "interests": [str(interest.pk) for interest in interests],
        },
        allowed_areas=premium_areas,
        interest_limit=premium_limit,
    )

    assert premium_form.is_valid(), premium_form.errors
    assert not premium_excess_form.is_valid()
    assert "interests" in premium_excess_form.errors


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

    allowed_areas, interest_limit = (
        get_allowed_discovery_areas_and_interest_limit(viewer)
    )
    available_form = DiscoveryFiltersForm(
        data={
            "broad_area": "central",
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


def test_discovery_profile_selector_returns_same_none_for_every_denial():
    viewer = create_test_user()
    create_verified_test_profile(user=viewer, broad_area="central")
    allowed = create_verified_test_profile(broad_area="west")
    unverified = Profile.objects.create(
        user=create_test_user(),
        display_name="Unverified target",
        broad_area="central",
    )
    inactive = create_verified_test_profile(
        user=create_test_user(is_active=False),
        broad_area="central",
    )
    blocked_by_viewer = create_verified_test_profile(broad_area="central")
    viewer_blocked_by = create_verified_test_profile(broad_area="central")
    Block.objects.create(blocker=viewer, blocked_user=blocked_by_viewer.user)
    Block.objects.create(blocker=viewer_blocked_by.user, blocked_user=viewer)

    assert get_profile_page_if_viewer_is_allowed(viewer, allowed.pk) == allowed
    assert get_profile_page_if_viewer_is_allowed(viewer, 999999) is None
    assert get_profile_page_if_viewer_is_allowed(viewer, unverified.pk) is None
    assert get_profile_page_if_viewer_is_allowed(viewer, inactive.pk) is None
    assert (
        get_profile_page_if_viewer_is_allowed(viewer, blocked_by_viewer.pk) is None
    )
    assert (
        get_profile_page_if_viewer_is_allowed(viewer, viewer_blocked_by.pk) is None
    )

    viewer.profile.is_verified = False
    viewer.profile.verified_at = None
    viewer.profile.verified_by = None
    viewer.profile.save(
        update_fields=["is_verified", "verified_at", "verified_by"]
    )
    assert get_profile_page_if_viewer_is_allowed(viewer, allowed.pk) is None


def test_plan_http_list_gates_access_and_preserves_owner_only_states():
    viewer = create_test_user()
    create_verified_test_profile(user=viewer)
    other_owner = create_test_user()
    create_verified_test_profile(user=other_owner)
    future = timezone.now() + timezone.timedelta(days=1)
    public_plan = create_test_plan(
        owner=other_owner,
        status=Plan.Status.APPROVED,
        title="Public HTTP plan",
        starts_at=future,
    )
    own_pending = create_test_plan(
        owner=viewer,
        title="Own pending HTTP plan",
        starts_at=future,
    )
    own_rejected = create_test_plan(
        owner=viewer,
        status=Plan.Status.REJECTED,
        title="Own rejected HTTP plan",
        starts_at=future,
    )
    own_cancelled = create_test_plan(
        owner=viewer,
        status=Plan.Status.CANCELLED,
        title="Own cancelled HTTP plan",
        starts_at=future,
    )
    hidden_pending = create_test_plan(
        owner=other_owner,
        title="Hidden pending HTTP plan",
        starts_at=future,
    )
    hidden_rejected = create_test_plan(
        owner=other_owner,
        status=Plan.Status.REJECTED,
        title="Hidden rejected HTTP plan",
        starts_at=future,
    )
    hidden_past = create_test_plan(
        owner=other_owner,
        status=Plan.Status.APPROVED,
        title="Hidden past HTTP plan",
        starts_at=timezone.now() - timezone.timedelta(minutes=1),
    )
    client = Client()
    client.force_login(viewer)

    response = client.get(reverse("plan_list"))

    assert response.status_code == 200
    for visible_plan in (
        public_plan,
        own_pending,
        own_rejected,
        own_cancelled,
    ):
        assert visible_plan.title.encode() in response.content
    for hidden_plan in (hidden_pending, hidden_rejected, hidden_past):
        assert hidden_plan.title.encode() not in response.content
    assert client.post(reverse("plan_list")).status_code == 405

    anonymous_response = Client().get(reverse("plan_list"))
    assert anonymous_response.status_code == 302
    assert anonymous_response.url.startswith(reverse("sign_in"))

    unverified = create_test_user()
    Profile.objects.create(user=unverified)
    unverified_client = Client()
    unverified_client.force_login(unverified)
    unverified_response = unverified_client.get(reverse("plan_list"))
    assert unverified_response.status_code == 302
    assert unverified_response.url == reverse("account")


def test_plan_http_creation_forces_pending_and_preserves_invalid_form():
    owner = create_test_user()
    create_verified_test_profile(user=owner)
    injected_owner = create_test_user()
    client = Client()
    client.force_login(owner)
    future = timezone.now() + timezone.timedelta(days=1)

    get_response = client.get(reverse("plan_create"))
    assert get_response.status_code == 200
    assert tuple(get_response.context["form"].fields) == (
        "title",
        "description",
        "public_place",
        "public_url",
        "starts_at",
        "capacity",
    )

    create_response = client.post(
        reverse("plan_create"),
        {
            "title": "HTTP museum plan",
            "description": "Meet at the staffed public entrance.",
            "public_place": "City Museum",
            "public_url": "https://example.test/city-museum",
            "starts_at": future.strftime("%Y-%m-%d %H:%M:%S"),
            "capacity": "3",
            "owner": injected_owner.pk,
            "status": Plan.Status.APPROVED,
            "approved_by": injected_owner.pk,
            "meeting_details_locked_at": timezone.now().isoformat(),
        },
    )
    plan = Plan.objects.get(title="HTTP museum plan")
    assert create_response.status_code == 302
    assert create_response.url == reverse("plan_detail", args=[plan.pk])
    assert plan.owner == owner
    assert plan.status == Plan.Status.PENDING
    assert plan.approved_at is None
    assert plan.approved_by is None
    assert plan.meeting_details_locked_at is None

    invalid_response = client.post(
        reverse("plan_create"),
        {
            "title": "Invalid HTTP plan",
            "description": "Not written.",
            "public_place": "Private place",
            "public_url": "http://example.test/not-https",
            "starts_at": future.strftime("%Y-%m-%d %H:%M:%S"),
            "capacity": "1",
        },
    )
    assert invalid_response.status_code == 200
    assert b"Enter an HTTPS URL" in invalid_response.content
    assert not Plan.objects.filter(title="Invalid HTTP plan").exists()


def test_plan_http_detail_exposes_count_and_own_state_without_participants():
    viewer = create_test_user()
    create_verified_test_profile(user=viewer)
    owner = create_test_user(username="plan_owner_login")
    create_verified_test_profile(user=owner, display_name="Public plan owner")
    plan = create_test_plan(
        owner=owner,
        status=Plan.Status.APPROVED,
        title="Privacy-safe HTTP plan",
        capacity=3,
    )
    joined_user = create_test_user(username="hidden_joined_user")
    left_user = create_test_user(username="hidden_left_user")
    Participation.objects.create(plan=plan, user=joined_user)
    Participation.objects.create(
        plan=plan,
        user=left_user,
        status=Participation.Status.LEFT,
        left_at=timezone.now(),
    )
    own_pending = create_test_plan(owner=viewer, title="Visible own pending detail")
    other_pending = create_test_plan(owner=owner, title="Hidden other pending detail")
    client = Client()
    client.force_login(viewer)

    response = client.get(reverse("plan_detail", args=[plan.pk]))
    own_response = client.get(reverse("plan_detail", args=[own_pending.pk]))
    hidden_response = client.get(reverse("plan_detail", args=[other_pending.pk]))
    missing_response = client.get(reverse("plan_detail", args=[999999]))

    assert response.status_code == 200
    assert b"Privacy-safe HTTP plan" in response.content
    assert b"Public plan owner" in response.content
    assert b"1 joined / 3" in response.content
    assert b"hidden_joined_user" not in response.content
    assert b"hidden_left_user" not in response.content
    assert b"participant" not in response.content.lower()
    assert b"does not preserve the reviewed webpage" in response.content
    assert own_response.status_code == 200
    assert hidden_response.status_code == missing_response.status_code == 404
    assert hidden_response.content == missing_response.content == b"Plan unavailable."
    assert client.post(reverse("plan_detail", args=[plan.pk])).status_code == 405


def test_plan_http_owner_edit_resets_review_and_hidden_edits_share_404():
    owner = create_test_user()
    create_verified_test_profile(user=owner)
    other_user = create_test_user()
    create_verified_test_profile(user=other_user)
    approved_plan = create_test_plan(
        owner=owner,
        status=Plan.Status.APPROVED,
        title="Approved HTTP edit plan",
    )
    original_reviewer = approved_plan.approved_by
    rejected_plan = create_test_plan(
        owner=owner,
        status=Plan.Status.REJECTED,
        title="Rejected HTTP edit plan",
    )
    locked_plan = create_test_plan(
        owner=owner,
        status=Plan.Status.APPROVED,
        title="Locked HTTP edit plan",
        meeting_details_locked_at=timezone.now(),
    )
    cancelled_plan = create_test_plan(
        owner=owner,
        status=Plan.Status.CANCELLED,
        title="Cancelled HTTP edit plan",
    )
    client = Client()
    client.force_login(owner)

    approved_values = {
        "title": "Renamed approved HTTP plan",
        "description": approved_plan.description,
        "public_place": approved_plan.public_place,
        "public_url": approved_plan.public_url,
        "starts_at": timezone.localtime(approved_plan.starts_at).strftime(
            "%Y-%m-%d %H:%M:%S"
        ),
        "capacity": str(approved_plan.capacity),
    }
    rename_response = client.post(
        reverse("plan_edit", args=[approved_plan.pk]),
        approved_values,
    )
    approved_plan.refresh_from_db()
    assert rename_response.status_code == 302
    assert approved_plan.status == Plan.Status.APPROVED
    assert approved_plan.approved_by == original_reviewer

    approved_values["public_url"] = "https://example.test/review-again-http"
    reset_response = client.post(
        reverse("plan_edit", args=[approved_plan.pk]),
        approved_values,
    )
    approved_plan.refresh_from_db()
    assert reset_response.status_code == 302
    assert approved_plan.status == Plan.Status.PENDING
    assert approved_plan.approved_at is None
    assert approved_plan.approved_by is None

    rejected_response = client.post(
        reverse("plan_edit", args=[rejected_plan.pk]),
        {
            "title": rejected_plan.title,
            "description": "Revised after staff rejection.",
            "public_place": rejected_plan.public_place,
            "public_url": rejected_plan.public_url,
            "starts_at": timezone.localtime(rejected_plan.starts_at).strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
            "capacity": str(rejected_plan.capacity),
        },
    )
    rejected_plan.refresh_from_db()
    assert rejected_response.status_code == 302
    assert rejected_plan.status == Plan.Status.PENDING

    other_client = Client()
    other_client.force_login(other_user)
    hidden_responses = (
        other_client.get(reverse("plan_edit", args=[approved_plan.pk])),
        client.get(reverse("plan_edit", args=[locked_plan.pk])),
        client.get(reverse("plan_edit", args=[cancelled_plan.pk])),
        client.get(reverse("plan_edit", args=[999999])),
    )
    assert {response.status_code for response in hidden_responses} == {404}
    assert {response.content for response in hidden_responses} == {
        b"Plan unavailable."
    }


def test_plan_http_join_leave_rejoin_and_cancel_preserve_history_and_lock():
    owner = create_test_user()
    create_verified_test_profile(user=owner)
    participant = create_test_user()
    create_verified_test_profile(user=participant)
    outsider = create_test_user()
    create_verified_test_profile(user=outsider)
    plan = create_test_plan(
        owner=owner,
        status=Plan.Status.APPROVED,
        title="HTTP participation plan",
        capacity=1,
    )
    participant_client = Client(enforce_csrf_checks=True)
    participant_client.force_login(participant)

    detail_response = participant_client.get(
        reverse("plan_detail", args=[plan.pk])
    )
    missing_csrf_response = participant_client.post(
        reverse("plan_join", args=[plan.pk])
    )
    assert missing_csrf_response.status_code == 403
    assert not Participation.objects.filter(plan=plan).exists()

    csrf_token = participant_client.cookies["csrftoken"].value
    join_response = participant_client.post(
        reverse("plan_join", args=[plan.pk]),
        {"csrfmiddlewaretoken": csrf_token},
        HTTP_REFERER=f"http://testserver{detail_response.request['PATH_INFO']}",
    )
    participation = Participation.objects.get(plan=plan, user=participant)
    plan.refresh_from_db()
    first_lock = plan.meeting_details_locked_at
    first_join = participation.joined_at
    assert join_response.status_code == 302
    assert join_response.url == reverse("plan_detail", args=[plan.pk])
    assert participation.status == Participation.Status.JOINED
    assert first_lock is not None

    owner_client = Client()
    owner_client.force_login(owner)
    owner_detail = owner_client.get(reverse("plan_detail", args=[plan.pk]))
    assert b"can no longer be edited" in owner_detail.content
    assert reverse("plan_edit", args=[plan.pk]).encode() not in owner_detail.content
    assert owner_client.get(reverse("plan_join", args=[plan.pk])).status_code == 405
    owner_join_response = owner_client.post(reverse("plan_join", args=[plan.pk]))
    assert owner_join_response.url == reverse("plan_list")
    assert not Participation.objects.filter(plan=plan, user=owner).exists()

    participant_client = Client()
    participant_client.force_login(participant)
    leave_response = participant_client.post(
        reverse("plan_leave", args=[plan.pk])
    )
    participation.refresh_from_db()
    plan.refresh_from_db()
    assert leave_response.status_code == 302
    assert participation.status == Participation.Status.LEFT
    assert participation.left_at is not None
    assert plan.meeting_details_locked_at == first_lock

    rejoin_response = participant_client.post(
        reverse("plan_join", args=[plan.pk])
    )
    participation.refresh_from_db()
    assert rejoin_response.status_code == 302
    assert participation.status == Participation.Status.JOINED
    assert participation.joined_at >= first_join
    assert participation.left_at is None
    assert Participation.objects.filter(plan=plan, user=participant).count() == 1

    outsider_client = Client()
    outsider_client.force_login(outsider)
    refused_full_response = outsider_client.post(
        reverse("plan_join", args=[plan.pk])
    )
    assert refused_full_response.url == reverse("plan_list")
    assert not Participation.objects.filter(plan=plan, user=outsider).exists()

    cancel_response = owner_client.post(reverse("plan_cancel", args=[plan.pk]))
    plan.refresh_from_db()
    participation.refresh_from_db()
    assert cancel_response.status_code == 302
    assert plan.status == Plan.Status.CANCELLED
    assert plan.approved_at is None
    assert plan.approved_by is None
    assert plan.meeting_details_locked_at == first_lock
    assert participation.status == Participation.Status.JOINED
    assert participant_client.get(reverse("plan_detail", args=[plan.pk])).status_code == 404


def test_plan_service_rechecks_current_verification_despite_cached_profile():
    owner = create_test_user()
    profile = create_verified_test_profile(user=owner)
    assert owner.profile.is_verified
    Profile.objects.filter(pk=profile.pk).update(
        is_verified=False,
        verified_at=None,
        verified_by=None,
    )
    future = timezone.now() + timezone.timedelta(days=1)
    form = PlanDetailsForm(
        data={
            "title": "Refused cached-profile plan",
            "description": "This should not be created.",
            "public_place": "Central Library",
            "public_url": "https://example.test/library",
            "starts_at": future.strftime("%Y-%m-%d %H:%M:%S"),
            "capacity": "1",
        }
    )
    assert form.is_valid(), form.errors

    assert not can_access_discovery_plans_and_messages(owner)
    with pytest.raises(PermissionDenied):
        create_plan_waiting_for_staff_review(owner, form.cleaned_data)
    assert not Plan.objects.filter(title="Refused cached-profile plan").exists()


def test_plan_form_accepts_future_https_details_and_rejects_invalid_bounds():
    future = timezone.now() + timezone.timedelta(days=1)
    valid_form = PlanDetailsForm(
        data={
            "title": "Museum visit",
            "description": "Meet at the public entrance.",
            "public_place": "City Museum",
            "public_url": "https://example.test/city-museum",
            "starts_at": future.strftime("%Y-%m-%d %H:%M:%S"),
            "capacity": "3",
            "status": Plan.Status.APPROVED,
        }
    )
    invalid_form = PlanDetailsForm(
        data={
            "title": "x" * 121,
            "description": "x" * 1001,
            "public_place": "x" * 201,
            "public_url": "http://example.test/private-address",
            "starts_at": (timezone.now() - timezone.timedelta(minutes=1)).strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
            "capacity": "0",
        }
    )

    assert tuple(valid_form.fields) == (
        "title",
        "description",
        "public_place",
        "public_url",
        "starts_at",
        "capacity",
    )
    assert valid_form.is_valid(), valid_form.errors
    assert "status" not in valid_form.cleaned_data
    assert not invalid_form.is_valid()
    assert {
        "title",
        "description",
        "public_place",
        "public_url",
        "starts_at",
        "capacity",
    } <= set(invalid_form.errors)


def test_plan_creation_requires_verification_and_forces_pending_review():
    owner = create_test_user()
    create_verified_test_profile(user=owner)
    other_user = create_test_user()
    form = PlanDetailsForm(
        data={
            "title": "Coffee plan",
            "description": "Meet inside the public cafe.",
            "public_place": "Central Cafe",
            "public_url": "https://example.test/central-cafe",
            "starts_at": (
                timezone.now() + timezone.timedelta(days=1)
            ).strftime("%Y-%m-%d %H:%M:%S"),
            "capacity": "2",
        }
    )
    assert form.is_valid(), form.errors

    plan_details = dict(form.cleaned_data)
    plan_details.update(
        {
            "owner": other_user,
            "status": Plan.Status.APPROVED,
            "approved_at": timezone.now(),
            "approved_by": other_user,
            "meeting_details_locked_at": timezone.now(),
        }
    )
    plan = create_plan_waiting_for_staff_review(owner, plan_details)

    assert can_create_plan_for_staff_review(owner)
    assert plan.owner == owner
    assert plan.status == Plan.Status.PENDING
    assert plan.approved_at is None
    assert plan.approved_by is None
    assert plan.meeting_details_locked_at is None

    unverified_user = create_test_user()
    Profile.objects.create(user=unverified_user)
    with pytest.raises(PermissionDenied):
        create_plan_waiting_for_staff_review(unverified_user, form.cleaned_data)
    assert not can_create_plan_for_staff_review(unverified_user)


@pytest.mark.parametrize(
    ("review_field", "review_value"),
    (
        ("public_place", "Riverside Museum"),
        ("public_url", "https://example.test/review-again"),
        ("starts_at", timezone.now() + timezone.timedelta(days=2)),
    ),
)
def test_plan_edit_resets_only_review_relevant_approval_and_resubmits_rejection(
    review_field,
    review_value,
):
    owner = create_test_user()
    create_verified_test_profile(user=owner)
    approved_plan = create_test_plan(
        owner=owner,
        status=Plan.Status.APPROVED,
    )
    approved_at = approved_plan.approved_at
    approved_by = approved_plan.approved_by

    renamed_plan = update_owned_plan_before_first_join(
        owner,
        approved_plan,
        {"title": "Renamed approved plan"},
    )
    assert renamed_plan.status == Plan.Status.APPROVED
    assert renamed_plan.approved_at == approved_at
    assert renamed_plan.approved_by == approved_by

    resubmitted_plan = update_owned_plan_before_first_join(
        owner,
        renamed_plan,
        {review_field: review_value},
    )
    assert resubmitted_plan.status == Plan.Status.PENDING
    assert resubmitted_plan.approved_at is None
    assert resubmitted_plan.approved_by is None

    rejected_plan = create_test_plan(owner=owner, status=Plan.Status.REJECTED)
    rejected_plan = update_owned_plan_before_first_join(
        owner,
        rejected_plan,
        {"description": "Revised after rejection."},
    )
    assert rejected_plan.status == Plan.Status.PENDING


def test_plan_edit_refuses_non_owner_locked_and_cancelled_states():
    owner = create_test_user()
    create_verified_test_profile(user=owner)
    non_owner = create_test_user()
    create_verified_test_profile(user=non_owner)
    plan = create_test_plan(owner=owner)
    locked_plan = create_test_plan(
        owner=owner,
        meeting_details_locked_at=timezone.now(),
    )
    cancelled_plan = create_test_plan(owner=owner, status=Plan.Status.CANCELLED)

    with pytest.raises(PermissionDenied):
        update_owned_plan_before_first_join(
            non_owner,
            plan,
            {"title": "Unauthorised change"},
        )
    with pytest.raises(PermissionDenied):
        update_owned_plan_before_first_join(
            owner,
            locked_plan,
            {"title": "Late change"},
        )
    with pytest.raises(PermissionDenied):
        update_owned_plan_before_first_join(
            owner,
            cancelled_plan,
            {"title": "Terminal change"},
        )

    plan.refresh_from_db()
    locked_plan.refresh_from_db()
    cancelled_plan.refresh_from_db()
    assert plan.title == "Test plan"
    assert locked_plan.title == "Test plan"
    assert cancelled_plan.title == "Test plan"


def test_plan_join_policy_refuses_owner_state_capacity_and_current_participation():
    owner = create_test_user()
    create_verified_test_profile(user=owner)
    participant = create_test_user()
    create_verified_test_profile(user=participant)
    other_participant = create_test_user()
    create_verified_test_profile(user=other_participant)
    current_time = timezone.now()
    approved_plan = create_test_plan(
        owner=owner,
        status=Plan.Status.APPROVED,
        capacity=1,
    )

    assert can_join_approved_plan(participant, approved_plan, current_time)
    assert not can_join_approved_plan(owner, approved_plan, current_time)

    pending_plan = create_test_plan(owner=owner)
    rejected_plan = create_test_plan(owner=owner, status=Plan.Status.REJECTED)
    cancelled_plan = create_test_plan(owner=owner, status=Plan.Status.CANCELLED)
    past_plan = create_test_plan(
        owner=owner,
        status=Plan.Status.APPROVED,
        starts_at=current_time - timezone.timedelta(minutes=1),
    )
    for refused_plan in (pending_plan, rejected_plan, cancelled_plan, past_plan):
        assert not can_join_approved_plan(participant, refused_plan, current_time)

    joined = Participation.objects.create(plan=approved_plan, user=participant)
    assert not can_join_approved_plan(participant, approved_plan, current_time)
    assert not can_join_approved_plan(other_participant, approved_plan, current_time)

    joined.status = Participation.Status.LEFT
    joined.left_at = timezone.now()
    joined.save(update_fields=["status", "left_at"])
    assert can_join_approved_plan(participant, approved_plan, current_time)

    unverified = create_test_user()
    Profile.objects.create(user=unverified)
    assert not can_join_approved_plan(unverified, approved_plan, current_time)


def test_plan_join_leave_and_rejoin_preserve_one_participation_and_lock():
    owner = create_test_user()
    create_verified_test_profile(user=owner)
    participant = create_test_user()
    create_verified_test_profile(user=participant)
    plan = create_test_plan(
        owner=owner,
        status=Plan.Status.APPROVED,
        capacity=1,
    )

    participation = join_approved_plan_and_lock_meeting_details(participant, plan)
    plan.refresh_from_db()
    first_lock_time = plan.meeting_details_locked_at
    first_join_time = participation.joined_at

    assert participation.status == Participation.Status.JOINED
    assert first_lock_time is not None
    assert plan.participations.count() == 1
    with pytest.raises(PermissionDenied):
        join_approved_plan_and_lock_meeting_details(participant, plan)

    left_participation = leave_plan_and_keep_participation_history(participant, plan)
    assert left_participation.pk == participation.pk
    assert left_participation.status == Participation.Status.LEFT
    assert left_participation.left_at is not None

    rejoined = join_approved_plan_and_lock_meeting_details(participant, plan)
    plan.refresh_from_db()
    assert rejoined.pk == participation.pk
    assert rejoined.status == Participation.Status.JOINED
    assert rejoined.joined_at >= first_join_time
    assert rejoined.left_at is None
    assert plan.meeting_details_locked_at == first_lock_time
    assert plan.participations.count() == 1


def test_plan_leave_refuses_ineligible_or_non_participant_without_mutation():
    owner = create_test_user()
    create_verified_test_profile(user=owner)
    participant = create_test_user()
    participant_profile = create_verified_test_profile(user=participant)
    inactive_participant = create_test_user()
    create_verified_test_profile(user=inactive_participant)
    outsider = create_test_user()
    create_verified_test_profile(user=outsider)
    plan = create_test_plan(
        owner=owner,
        status=Plan.Status.APPROVED,
        capacity=2,
    )
    participation = join_approved_plan_and_lock_meeting_details(participant, plan)
    inactive_participation = join_approved_plan_and_lock_meeting_details(
        inactive_participant,
        plan,
    )
    plan.refresh_from_db()
    first_lock_time = plan.meeting_details_locked_at

    with pytest.raises(PermissionDenied):
        leave_plan_and_keep_participation_history(outsider, plan)

    participant_profile.is_verified = False
    participant_profile.verified_at = None
    participant_profile.verified_by = None
    participant_profile.save(
        update_fields=["is_verified", "verified_at", "verified_by"]
    )
    with pytest.raises(PermissionDenied):
        leave_plan_and_keep_participation_history(participant, plan)

    inactive_participant.is_active = False
    inactive_participant.save(update_fields=["is_active"])
    with pytest.raises(PermissionDenied):
        leave_plan_and_keep_participation_history(inactive_participant, plan)

    participation.refresh_from_db()
    inactive_participation.refresh_from_db()
    plan.refresh_from_db()
    assert participation.status == Participation.Status.JOINED
    assert participation.left_at is None
    assert inactive_participation.status == Participation.Status.JOINED
    assert inactive_participation.left_at is None
    assert plan.meeting_details_locked_at == first_lock_time
    assert plan.participations.count() == 2


def test_plan_cancellation_is_terminal_and_preserves_participation_history():
    owner = create_test_user()
    create_verified_test_profile(user=owner)
    participant = create_test_user()
    create_verified_test_profile(user=participant)
    plan = create_test_plan(owner=owner, status=Plan.Status.APPROVED)
    participation = join_approved_plan_and_lock_meeting_details(participant, plan)
    plan.refresh_from_db()
    first_lock_time = plan.meeting_details_locked_at

    non_owner = create_test_user()
    create_verified_test_profile(user=non_owner)
    with pytest.raises(PermissionDenied):
        cancel_owned_plan_and_hide_it_from_discovery(non_owner, plan)
    plan.refresh_from_db()
    participation.refresh_from_db()
    assert plan.status == Plan.Status.APPROVED
    assert participation.status == Participation.Status.JOINED

    cancelled = cancel_owned_plan_and_hide_it_from_discovery(owner, plan)
    participation.refresh_from_db()
    assert cancelled.status == Plan.Status.CANCELLED
    assert cancelled.approved_at is None
    assert cancelled.approved_by is None
    assert cancelled.meeting_details_locked_at == first_lock_time
    assert participation.status == Participation.Status.JOINED
    assert Participation.objects.filter(pk=participation.pk).exists()

    another_user = create_test_user()
    create_verified_test_profile(user=another_user)
    with pytest.raises(PermissionDenied):
        join_approved_plan_and_lock_meeting_details(another_user, cancelled)
    with pytest.raises(PermissionDenied):
        update_owned_plan_before_first_join(
            owner,
            cancelled,
            {"title": "Cannot reactivate"},
        )
    with pytest.raises(PermissionDenied):
        cancel_owned_plan_and_hide_it_from_discovery(owner, cancelled)

    unverified_owner = create_test_user()
    unverified_profile = create_verified_test_profile(user=unverified_owner)
    unverified_owner_plan = create_test_plan(
        owner=unverified_owner,
        status=Plan.Status.APPROVED,
    )
    unverified_profile.is_verified = False
    unverified_profile.verified_at = None
    unverified_profile.verified_by = None
    unverified_profile.save(
        update_fields=["is_verified", "verified_at", "verified_by"]
    )
    with pytest.raises(PermissionDenied):
        cancel_owned_plan_and_hide_it_from_discovery(
            unverified_owner,
            unverified_owner_plan,
        )
    unverified_owner_plan.refresh_from_db()
    assert unverified_owner_plan.status == Plan.Status.APPROVED


def test_plan_list_selector_preserves_public_and_owner_only_visibility():
    viewer = create_test_user()
    create_verified_test_profile(user=viewer)
    other_owner = create_test_user()
    create_verified_test_profile(user=other_owner)
    future = timezone.now() + timezone.timedelta(days=1)
    past = timezone.now() - timezone.timedelta(days=1)
    public_plan = create_test_plan(
        owner=other_owner,
        status=Plan.Status.APPROVED,
        starts_at=future,
    )
    own_pending = create_test_plan(owner=viewer, starts_at=future)
    own_rejected = create_test_plan(
        owner=viewer,
        status=Plan.Status.REJECTED,
        starts_at=future,
    )
    own_cancelled = create_test_plan(
        owner=viewer,
        status=Plan.Status.CANCELLED,
        starts_at=past,
    )
    create_test_plan(owner=other_owner, starts_at=future)
    create_test_plan(
        owner=other_owner,
        status=Plan.Status.REJECTED,
        starts_at=future,
    )
    create_test_plan(
        owner=other_owner,
        status=Plan.Status.CANCELLED,
        starts_at=future,
    )
    create_test_plan(
        owner=other_owner,
        status=Plan.Status.APPROVED,
        starts_at=past,
    )

    visible_plans = set(get_plans_for_plan_list(viewer))
    assert visible_plans == {
        public_plan,
        own_pending,
        own_rejected,
        own_cancelled,
    }

    viewer.profile.is_verified = False
    viewer.profile.verified_at = None
    viewer.profile.verified_by = None
    viewer.profile.save(
        update_fields=["is_verified", "verified_at", "verified_by"]
    )
    assert not get_plans_for_plan_list(viewer).exists()


def test_plan_page_selector_returns_count_and_own_state_without_participant_list():
    viewer = create_test_user()
    create_verified_test_profile(user=viewer)
    owner = create_test_user()
    create_verified_test_profile(user=owner)
    public_plan = create_test_plan(
        owner=owner,
        status=Plan.Status.APPROVED,
        capacity=3,
    )
    other_participant = create_test_user()
    Participation.objects.create(plan=public_plan, user=other_participant)
    Participation.objects.create(
        plan=public_plan,
        user=viewer,
        status=Participation.Status.LEFT,
        left_at=timezone.now(),
    )
    hidden_plan = create_test_plan(owner=owner)
    own_pending = create_test_plan(owner=viewer)

    summary = get_plan_page_if_viewer_is_allowed(viewer, public_plan.pk)
    own_summary = get_plan_page_if_viewer_is_allowed(viewer, own_pending.pk)

    assert set(summary) == {
        "plan",
        "joined_count",
        "viewer_participation_status",
    }
    assert summary["plan"] == public_plan
    assert summary["joined_count"] == 1
    assert summary["viewer_participation_status"] == Participation.Status.LEFT
    assert "participants" not in summary
    assert own_summary["plan"] == own_pending
    assert get_plan_page_if_viewer_is_allowed(viewer, hidden_plan.pk) is None
    assert get_plan_page_if_viewer_is_allowed(viewer, 999999) is None


class PlanCapacityJoinRaceTests(TransactionTestCase):
    """Prove PostgreSQL row locking prevents two final-capacity joins."""

    def setUp(self):
        self.owner = create_test_user()
        create_verified_test_profile(user=self.owner)
        self.plan = create_test_plan(
            owner=self.owner,
            status=Plan.Status.APPROVED,
            capacity=1,
        )
        self.participants = [create_test_user(), create_test_user()]
        for participant in self.participants:
            create_verified_test_profile(user=participant)

    def test_plan_capacity_join_race_allows_only_one_participation(self):
        start_together = Barrier(2)

        def attempt_join(user_id):
            close_old_connections()
            try:
                user = get_user_model().objects.get(pk=user_id)
                plan = Plan.objects.get(pk=self.plan.pk)
                start_together.wait(timeout=5)
                try:
                    join_approved_plan_and_lock_meeting_details(user, plan)
                except PermissionDenied:
                    return False
                return True
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as executor:
            outcomes = list(
                executor.map(
                    attempt_join,
                    [participant.pk for participant in self.participants],
                )
            )

        self.plan.refresh_from_db()
        self.assertEqual(outcomes.count(True), 1)
        self.assertEqual(outcomes.count(False), 1)
        self.assertEqual(
            Participation.objects.filter(
                plan=self.plan,
                status=Participation.Status.JOINED,
            ).count(),
            1,
        )
        self.assertIsNotNone(self.plan.meeting_details_locked_at)


def test_direct_conversation_http_starts_from_authorised_profile_once_with_csrf():
    viewer = create_test_user()
    create_verified_test_profile(user=viewer, display_name="Message starter")
    target = create_test_user()
    target_profile = create_verified_test_profile(
        user=target,
        display_name="Message target",
    )
    blocked_target = create_test_user()
    blocked_profile = create_verified_test_profile(
        user=blocked_target,
        display_name="Hidden blocked target",
    )
    Block.objects.create(blocker=blocked_target, blocked_user=viewer)
    client = Client(enforce_csrf_checks=True)
    client.force_login(viewer)

    profile_response = client.get(reverse("profile_detail", args=[target_profile.pk]))
    start_url = reverse("direct_conversation_start", args=[target_profile.pk])
    assert profile_response.status_code == 200
    assert start_url.encode() in profile_response.content
    assert b"Message Message target" in profile_response.content
    assert client.get(start_url).status_code == 405

    missing_csrf_response = client.post(start_url)
    assert missing_csrf_response.status_code == 403
    assert not Conversation.objects.exists()

    csrf_token = client.cookies["csrftoken"].value
    start_response = client.post(
        start_url,
        {"csrfmiddlewaretoken": csrf_token, "recipient": blocked_target.pk},
        HTTP_REFERER=f"http://testserver{profile_response.request['PATH_INFO']}",
    )
    conversation = Conversation.objects.get()
    assert start_response.status_code == 302
    assert start_response.url == reverse(
        "conversation_detail",
        args=[conversation.pk],
    )
    assert {conversation.first_user_id, conversation.second_user_id} == {
        viewer.pk,
        target.pk,
    }

    repeated_response = client.post(
        start_url,
        {"csrfmiddlewaretoken": csrf_token},
        HTTP_REFERER=f"http://testserver{profile_response.request['PATH_INFO']}",
    )
    assert repeated_response.url == start_response.url
    assert Conversation.objects.count() == 1

    hidden_response = client.post(
        reverse("direct_conversation_start", args=[blocked_profile.pk]),
        {"csrfmiddlewaretoken": csrf_token},
        HTTP_REFERER=f"http://testserver{profile_response.request['PATH_INFO']}",
    )
    missing_response = client.post(
        reverse("direct_conversation_start", args=[999999]),
        {"csrfmiddlewaretoken": csrf_token},
        HTTP_REFERER=f"http://testserver{profile_response.request['PATH_INFO']}",
    )
    assert hidden_response.status_code == missing_response.status_code == 404
    assert hidden_response.content == missing_response.content == b"Profile unavailable."
    assert Conversation.objects.count() == 1


def test_inbox_http_orders_only_permitted_pairs_without_message_previews():
    viewer = create_test_user()
    create_verified_test_profile(user=viewer)
    older_user = create_test_user()
    create_verified_test_profile(user=older_user, display_name="Older inbox name")
    newer_user = create_test_user()
    create_verified_test_profile(user=newer_user, display_name="Newer inbox name")
    hidden_user = create_test_user()
    create_verified_test_profile(user=hidden_user, display_name="Hidden inbox name")
    unrelated_first = create_test_user()
    create_verified_test_profile(user=unrelated_first, display_name="Unrelated one")
    unrelated_second = create_test_user()
    create_verified_test_profile(user=unrelated_second, display_name="Unrelated two")
    older = create_test_conversation(viewer, older_user)
    newer = create_test_conversation(viewer, newer_user)
    hidden = create_test_conversation(viewer, hidden_user)
    create_test_conversation(unrelated_first, unrelated_second)
    current_time = timezone.now()
    Conversation.objects.filter(pk=older.pk).update(
        updated_at=current_time - timezone.timedelta(hours=2)
    )
    Conversation.objects.filter(pk=newer.pk).update(
        updated_at=current_time - timezone.timedelta(hours=1)
    )
    Message.objects.create(
        conversation=hidden,
        sender=hidden_user,
        body="Private blocked inbox text",
    )
    Block.objects.create(blocker=viewer, blocked_user=hidden_user)
    client = Client()
    client.force_login(viewer)

    response = client.get(reverse("inbox"))

    assert response.status_code == 200
    assert response.content.find(b"Newer inbox name") < response.content.find(
        b"Older inbox name"
    )
    assert b"Hidden inbox name" not in response.content
    assert b"Private blocked inbox text" not in response.content
    assert b"Unrelated one" not in response.content
    assert client.post(reverse("inbox")).status_code == 405

    anonymous_response = Client().get(reverse("inbox"))
    assert anonymous_response.status_code == 302
    assert anonymous_response.url.startswith(reverse("sign_in"))
    unverified = create_test_user()
    Profile.objects.create(user=unverified)
    unverified_client = Client()
    unverified_client.force_login(unverified)
    unverified_response = unverified_client.get(reverse("inbox"))
    assert unverified_response.status_code == 302
    assert unverified_response.url == reverse("account")


def test_conversation_http_escapes_ordered_messages_and_shares_one_hidden_404():
    viewer = create_test_user()
    create_verified_test_profile(user=viewer)
    other_user = create_test_user()
    create_verified_test_profile(user=other_user, display_name="Conversation peer")
    outsider = create_test_user()
    create_verified_test_profile(user=outsider)
    conversation = create_test_conversation(viewer, other_user)
    first_message = Message.objects.create(
        conversation=conversation,
        sender=other_user,
        body="First <script>alert('private')</script>",
        sent_at=timezone.now() - timezone.timedelta(minutes=1),
    )
    second_message = Message.objects.create(
        conversation=conversation,
        sender=viewer,
        body="Second ordinary message",
    )
    client = Client()
    client.force_login(viewer)

    response = client.get(reverse("conversation_detail", args=[conversation.pk]))

    assert response.status_code == 200
    escaped_first = b"First &lt;script&gt;alert(&#x27;private&#x27;)&lt;/script&gt;"
    assert escaped_first in response.content
    assert b"<script>" not in response.content
    assert response.content.find(escaped_first) < response.content.find(
        second_message.body.encode()
    )
    assert b"Conversation peer" in response.content
    assert client.post(
        reverse("conversation_detail", args=[conversation.pk])
    ).status_code == 405

    outsider_client = Client()
    outsider_client.force_login(outsider)
    unrelated_response = outsider_client.get(
        reverse("conversation_detail", args=[conversation.pk])
    )
    missing_response = client.get(reverse("conversation_detail", args=[999999]))
    Block.objects.create(blocker=other_user, blocked_user=viewer)
    blocked_response = client.get(
        reverse("conversation_detail", args=[conversation.pk])
    )
    assert {
        unrelated_response.status_code,
        missing_response.status_code,
        blocked_response.status_code,
    } == {404}
    assert {
        unrelated_response.content,
        missing_response.content,
        blocked_response.content,
    } == {b"Conversation unavailable."}
    assert first_message.body.encode() not in blocked_response.content


def test_conversation_send_http_rechecks_csrf_form_sender_and_current_access(caplog):
    viewer = create_test_user()
    create_verified_test_profile(user=viewer)
    other_user = create_test_user()
    create_verified_test_profile(user=other_user, display_name="Send target")
    injected_sender = create_test_user()
    create_verified_test_profile(user=injected_sender)
    conversation = create_test_conversation(viewer, other_user)
    client = Client(enforce_csrf_checks=True)
    client.force_login(viewer)
    detail_url = reverse("conversation_detail", args=[conversation.pk])
    send_url = reverse("conversation_message_send", args=[conversation.pk])
    detail_response = client.get(detail_url)
    original_activity = conversation.updated_at

    assert client.get(send_url).status_code == 405
    assert client.post(send_url, {"body": "Missing CSRF"}).status_code == 403
    assert not Message.objects.filter(conversation=conversation).exists()

    csrf_token = client.cookies["csrftoken"].value
    invalid_response = client.post(
        send_url,
        {"csrfmiddlewaretoken": csrf_token, "body": "   "},
        HTTP_REFERER=f"http://testserver{detail_response.request['PATH_INFO']}",
    )
    assert invalid_response.status_code == 200
    assert b"This field is required" in invalid_response.content
    assert not Message.objects.filter(conversation=conversation).exists()

    private_body = "  <img src=x onerror=alert('private draft')>  "
    caplog.clear()
    send_response = client.post(
        send_url,
        {
            "csrfmiddlewaretoken": csrf_token,
            "body": private_body,
            "sender": injected_sender.pk,
        },
        HTTP_REFERER=f"http://testserver{detail_response.request['PATH_INFO']}",
    )
    stored_message = Message.objects.get(conversation=conversation)
    conversation.refresh_from_db()
    assert send_response.status_code == 302
    assert send_response.url == detail_url
    assert stored_message.sender == viewer
    assert stored_message.body == private_body.strip()
    assert conversation.updated_at == stored_message.sent_at
    assert conversation.updated_at >= original_activity
    assert private_body.strip() not in caplog.text

    rendered_response = client.get(detail_url)
    assert b"&lt;img src=x onerror=alert" in rendered_response.content
    assert b"<img src=x" not in rendered_response.content

    Block.objects.create(blocker=other_user, blocked_user=viewer)
    refused_response = client.post(
        send_url,
        {"csrfmiddlewaretoken": csrf_token, "body": "Blocked second message"},
        HTTP_REFERER=f"http://testserver{detail_response.request['PATH_INFO']}",
    )
    assert refused_response.status_code == 404
    assert refused_response.content == b"Conversation unavailable."
    assert Message.objects.filter(conversation=conversation).count() == 1


def test_message_draft_form_accepts_plain_text_and_rejects_empty_or_oversized_text():
    valid_form = MessageDraftForm(data={"body": "  Hello <strong>there</strong>  "})
    empty_form = MessageDraftForm(data={"body": "   "})
    oversized_form = MessageDraftForm(data={"body": "x" * 1_001})

    assert tuple(valid_form.fields) == ("body",)
    assert valid_form.is_valid(), valid_form.errors
    assert valid_form.cleaned_data["body"] == "Hello <strong>there</strong>"
    assert not empty_form.is_valid()
    assert "body" in empty_form.errors
    assert not oversized_form.is_valid()
    assert "body" in oversized_form.errors


def test_direct_message_policy_requires_distinct_verified_active_unblocked_pair():
    sender = create_test_user()
    create_verified_test_profile(user=sender)
    recipient = create_test_user()
    create_verified_test_profile(user=recipient)
    unverified = create_test_user()
    Profile.objects.create(user=unverified)
    inactive = create_test_user(is_active=False)
    create_verified_test_profile(user=inactive)
    blocked_by_sender = create_test_user()
    create_verified_test_profile(user=blocked_by_sender)
    sender_blocked_by = create_test_user()
    create_verified_test_profile(user=sender_blocked_by)
    Block.objects.create(blocker=sender, blocked_user=blocked_by_sender)
    Block.objects.create(blocker=sender_blocked_by, blocked_user=sender)

    assert can_start_or_continue_direct_messages(sender, recipient)
    assert can_start_or_continue_direct_messages(recipient, sender)
    assert not can_start_or_continue_direct_messages(sender, sender)
    assert not can_start_or_continue_direct_messages(sender, unverified)
    assert not can_start_or_continue_direct_messages(sender, inactive)
    assert not can_start_or_continue_direct_messages(sender, blocked_by_sender)
    assert not can_start_or_continue_direct_messages(sender, sender_blocked_by)
    assert not can_start_or_continue_direct_messages(AnonymousUser(), recipient)


def test_conversation_service_returns_one_ordered_pair_and_refuses_without_writes():
    first_user = create_test_user()
    create_verified_test_profile(user=first_user)
    second_user = create_test_user()
    create_verified_test_profile(user=second_user)

    conversation = find_or_start_direct_conversation(second_user, first_user)
    existing = find_or_start_direct_conversation(first_user, second_user)

    assert conversation.pk == existing.pk
    assert conversation.first_user_id == min(first_user.pk, second_user.pk)
    assert conversation.second_user_id == max(first_user.pk, second_user.pk)
    assert Conversation.objects.count() == 1

    unverified = create_test_user()
    Profile.objects.create(user=unverified)
    inactive = create_test_user(is_active=False)
    create_verified_test_profile(user=inactive)
    blocked = create_test_user()
    create_verified_test_profile(user=blocked)
    Block.objects.create(blocker=blocked, blocked_user=first_user)

    for refused_user in (first_user, unverified, inactive, blocked):
        with pytest.raises(PermissionDenied):
            find_or_start_direct_conversation(first_user, refused_user)

    assert Conversation.objects.count() == 1


def test_message_service_stores_plain_text_and_updates_conversation_activity():
    sender = create_test_user()
    create_verified_test_profile(user=sender)
    recipient = create_test_user()
    create_verified_test_profile(user=recipient)
    conversation = find_or_start_direct_conversation(sender, recipient)
    previous_activity = conversation.updated_at
    form = MessageDraftForm(data={"body": "<script>alert('hello')</script>"})
    assert form.is_valid(), form.errors

    message = send_direct_message(
        sender,
        conversation,
        form.cleaned_data["body"],
    )
    conversation.refresh_from_db()

    assert message.conversation == conversation
    assert message.sender == sender
    assert message.body == "<script>alert('hello')</script>"
    assert conversation.updated_at == message.sent_at
    assert conversation.updated_at >= previous_activity
    assert str(conditional_escape(message.body)) == (
        "&lt;script&gt;alert(&#x27;hello&#x27;)&lt;/script&gt;"
    )


def test_message_service_refuses_changed_permissions_without_partial_state():
    sender = create_test_user()
    create_verified_test_profile(user=sender)
    recipient = create_test_user()
    recipient_profile = create_verified_test_profile(user=recipient)
    outsider = create_test_user()
    create_verified_test_profile(user=outsider)
    conversation = find_or_start_direct_conversation(sender, recipient)
    original_activity = conversation.updated_at
    original_verification = (
        recipient_profile.verified_at,
        recipient_profile.verified_by,
    )

    with pytest.raises(PermissionDenied):
        send_direct_message(outsider, conversation, "Outsider message")

    recipient_profile.is_verified = False
    recipient_profile.verified_at = None
    recipient_profile.verified_by = None
    recipient_profile.save(
        update_fields=["is_verified", "verified_at", "verified_by"]
    )
    with pytest.raises(PermissionDenied):
        send_direct_message(sender, conversation, "Unverified recipient")

    recipient_profile.is_verified = True
    recipient_profile.verified_at = original_verification[0]
    recipient_profile.verified_by = original_verification[1]
    recipient_profile.save(
        update_fields=["is_verified", "verified_at", "verified_by"]
    )
    recipient.is_active = False
    recipient.save(update_fields=["is_active"])
    with pytest.raises(PermissionDenied):
        send_direct_message(sender, conversation, "Inactive recipient")

    recipient.is_active = True
    recipient.save(update_fields=["is_active"])
    Block.objects.create(blocker=recipient, blocked_user=sender)
    with pytest.raises(PermissionDenied):
        send_direct_message(sender, conversation, "Blocked message")

    conversation.refresh_from_db()
    assert not Message.objects.filter(conversation=conversation).exists()
    assert conversation.updated_at == original_activity


def test_message_service_rolls_back_message_when_activity_update_fails(monkeypatch):
    sender = create_test_user()
    create_verified_test_profile(user=sender)
    recipient = create_test_user()
    create_verified_test_profile(user=recipient)
    conversation = find_or_start_direct_conversation(sender, recipient)
    original_activity = conversation.updated_at
    normal_save = Conversation.save

    def refuse_activity_update(conversation_to_save, *args, **kwargs):
        if kwargs.get("update_fields") == ["updated_at"]:
            raise RuntimeError("synthetic conversation update failure")
        return normal_save(conversation_to_save, *args, **kwargs)

    monkeypatch.setattr(Conversation, "save", refuse_activity_update)

    with pytest.raises(RuntimeError, match="synthetic conversation update failure"):
        send_direct_message(sender, conversation, "Must roll back")

    conversation.refresh_from_db()
    assert not Message.objects.filter(conversation=conversation).exists()
    assert conversation.updated_at == original_activity


def test_inbox_selector_orders_only_currently_permitted_conversations():
    viewer = create_test_user()
    viewer_profile = create_verified_test_profile(user=viewer)
    older_user = create_test_user()
    create_verified_test_profile(user=older_user)
    newer_user = create_test_user()
    create_verified_test_profile(user=newer_user)
    older = create_test_conversation(viewer, older_user)
    newer = create_test_conversation(viewer, newer_user)
    Conversation.objects.filter(pk=older.pk).update(
        updated_at=timezone.now() - timezone.timedelta(hours=2)
    )
    Conversation.objects.filter(pk=newer.pk).update(
        updated_at=timezone.now() - timezone.timedelta(hours=1)
    )

    blocked_by_viewer = create_test_user()
    create_verified_test_profile(user=blocked_by_viewer)
    create_test_conversation(viewer, blocked_by_viewer)
    Block.objects.create(blocker=viewer, blocked_user=blocked_by_viewer)
    viewer_blocked_by = create_test_user()
    create_verified_test_profile(user=viewer_blocked_by)
    create_test_conversation(viewer, viewer_blocked_by)
    Block.objects.create(blocker=viewer_blocked_by, blocked_user=viewer)
    inactive_user = create_test_user(is_active=False)
    create_verified_test_profile(user=inactive_user)
    create_test_conversation(viewer, inactive_user)
    unverified_user = create_test_user()
    Profile.objects.create(user=unverified_user)
    create_test_conversation(viewer, unverified_user)
    unrelated_first = create_test_user()
    create_verified_test_profile(user=unrelated_first)
    unrelated_second = create_test_user()
    create_verified_test_profile(user=unrelated_second)
    create_test_conversation(unrelated_first, unrelated_second)

    with CaptureQueriesContext(connection) as captured_queries:
        permitted_conversations = list(get_unblocked_conversations_for_inbox(viewer))
        for conversation in permitted_conversations:
            conversation.first_user.profile.display_name
            conversation.second_user.profile.display_name
    assert permitted_conversations == [newer, older]
    assert len(captured_queries) == 2

    viewer_profile.is_verified = False
    viewer_profile.verified_at = None
    viewer_profile.verified_by = None
    viewer_profile.save(
        update_fields=["is_verified", "verified_at", "verified_by"]
    )
    assert not get_unblocked_conversations_for_inbox(viewer).exists()


def test_message_selector_returns_chronological_content_only_to_permitted_member():
    viewer = create_test_user()
    create_verified_test_profile(user=viewer)
    other_user = create_test_user()
    create_verified_test_profile(user=other_user)
    outsider = create_test_user()
    create_verified_test_profile(user=outsider)
    conversation = find_or_start_direct_conversation(viewer, other_user)
    first_message = send_direct_message(viewer, conversation, "First message")
    second_message = send_direct_message(other_user, conversation, "Second message")

    page_data = get_messages_if_user_can_open_conversation(
        viewer,
        conversation.pk,
    )

    assert set(page_data) == {"conversation", "messages"}
    assert page_data["conversation"] == conversation
    assert list(page_data["messages"]) == [first_message, second_message]
    assert get_messages_if_user_can_open_conversation(outsider, conversation.pk) is None
    assert get_messages_if_user_can_open_conversation(viewer, 999999) is None

    Block.objects.create(blocker=other_user, blocked_user=viewer)
    assert get_messages_if_user_can_open_conversation(viewer, conversation.pk) is None


def test_block_http_requires_csrf_closes_interaction_and_keeps_reporting_open():
    blocker = create_test_user()
    create_verified_test_profile(user=blocker)
    target = create_test_user()
    target_profile = create_verified_test_profile(
        user=target,
        display_name="HTTP block target",
    )
    conversation = create_test_conversation(blocker, target)
    client = Client(enforce_csrf_checks=True)
    client.force_login(blocker)
    profile_url = reverse("profile_detail", args=[target_profile.pk])
    block_url = reverse(
        "profile_block_messages_and_discovery",
        args=[target_profile.pk],
    )
    report_url = reverse("report_create", args=[target_profile.pk])
    profile_response = client.get(profile_url)

    assert profile_response.status_code == 200
    assert block_url.encode() in profile_response.content
    assert report_url.encode() in profile_response.content
    assert client.get(block_url).status_code == 405
    assert client.post(block_url).status_code == 403
    assert not Block.objects.exists()

    csrf_token = client.cookies["csrftoken"].value
    block_response = client.post(
        block_url,
        {"csrfmiddlewaretoken": csrf_token},
        HTTP_REFERER=f"http://testserver{profile_response.request['PATH_INFO']}",
    )
    assert block_response.status_code == 302
    assert block_response.url == reverse("discover")
    assert Block.objects.filter(blocker=blocker, blocked_user=target).count() == 1
    assert client.get(profile_url).status_code == 404
    assert client.get(
        reverse("conversation_detail", args=[conversation.pk])
    ).status_code == 404
    assert b"HTTP block target" not in client.get(reverse("inbox")).content
    assert client.get(report_url).status_code == 200

    target_client = Client()
    target_client.force_login(target)
    target_account_response = target_client.get(reverse("account"))
    assert b"Interaction closed" not in target_account_response.content
    assert b"blocker" not in target_account_response.content.lower()


def test_private_report_http_forces_authority_stays_private_and_avoids_logs(caplog):
    reporter = create_test_user()
    Profile.objects.create(user=reporter, display_name="Unverified reporter")
    target = create_test_user(username="private_report_target_login")
    target_profile = create_verified_test_profile(
        user=target,
        display_name="Private report target",
    )
    injected_user = create_test_user()
    client = Client(enforce_csrf_checks=True)
    client.force_login(reporter)
    report_url = reverse("report_create", args=[target_profile.pk])
    form_response = client.get(report_url)

    assert form_response.status_code == 200
    assert b"Private report target" in form_response.content
    assert tuple(form_response.context["form"].fields) == (
        "category",
        "description",
    )
    assert client.post(
        report_url,
        {"category": Report.Category.OTHER, "description": "Missing CSRF"},
    ).status_code == 403
    assert not Report.objects.exists()

    csrf_token = client.cookies["csrftoken"].value
    invalid_response = client.post(
        report_url,
        {
            "csrfmiddlewaretoken": csrf_token,
            "category": "invented",
            "description": "   ",
        },
        HTTP_REFERER=f"http://testserver{form_response.request['PATH_INFO']}",
    )
    assert invalid_response.status_code == 200
    assert not Report.objects.exists()

    private_description = "A private factual HTTP report <script>private</script>."
    caplog.clear()
    confirmation = client.post(
        report_url,
        {
            "csrfmiddlewaretoken": csrf_token,
            "category": Report.Category.HARASSMENT,
            "description": private_description,
            "reporter": injected_user.pk,
            "reported_user": injected_user.pk,
            "status": Report.Status.REVIEWED,
            "reported_plan": "999999",
        },
        HTTP_REFERER=f"http://testserver{form_response.request['PATH_INFO']}",
    )
    report = Report.objects.get()
    assert confirmation.status_code == 200
    assert b"Report received" in confirmation.content
    assert b"does not by itself prove wrongdoing" in confirmation.content
    assert private_description.encode() not in confirmation.content
    assert report.reporter == reporter
    assert report.reported_user == target
    assert report.status == Report.Status.RECEIVED
    assert report.reported_plan_id is None
    assert private_description not in caplog.text

    target_client = Client()
    target_client.force_login(target)
    target_response = target_client.get(reverse("account"))
    assert private_description.encode() not in target_response.content
    assert b"Report received" not in target_response.content
    assert b"Private submission" not in target_response.content
    assert reporter.username.encode() not in target_response.content
    self_response = client.get(reverse("report_create", args=[reporter.profile.pk]))
    missing_response = client.get(reverse("report_create", args=[999999]))
    assert self_response.status_code == missing_response.status_code == 404
    assert self_response.content == missing_response.content == b"Report unavailable."


def test_private_report_http_validates_plan_context_and_rejects_unrelated_plan():
    reporter = create_test_user()
    create_verified_test_profile(user=reporter)
    target = create_test_user()
    target_profile = create_verified_test_profile(user=target)
    plan = create_test_plan(owner=target, status=Plan.Status.APPROVED)
    Participation.objects.create(plan=plan, user=reporter)
    unrelated_owner = create_test_user()
    create_verified_test_profile(user=unrelated_owner)
    unrelated_plan = create_test_plan(
        owner=unrelated_owner,
        status=Plan.Status.APPROVED,
        title="Unrelated visible report plan",
    )
    client = Client()
    client.force_login(reporter)
    report_url = reverse("report_create", args=[target_profile.pk])
    plan_response = client.get(reverse("plan_detail", args=[plan.pk]))

    assert plan_response.status_code == 200
    assert (
        f"{report_url}?context_type=plan&amp;context_id={plan.pk}".encode()
        in plan_response.content
    )
    form_response = client.get(
        report_url,
        {"context_type": "plan", "context_id": str(plan.pk)},
    )
    assert form_response.status_code == 200
    assert f"Plan: {plan.title}".encode() in form_response.content
    assert b'name="context_type" value="plan"' in form_response.content

    success_response = client.post(
        report_url,
        {
            "category": Report.Category.MISLEADING_PLAN,
            "description": "The submitted plan information was misleading.",
            "context_type": "plan",
            "context_id": str(plan.pk),
        },
    )
    report = Report.objects.get()
    assert success_response.status_code == 200
    assert report.reported_plan == plan

    refused_response = client.post(
        report_url,
        {
            "category": Report.Category.OTHER,
            "description": "This unrelated plan must be refused.",
            "context_type": "plan",
            "context_id": str(unrelated_plan.pk),
        },
    )
    unknown_response = client.get(
        report_url,
        {"context_type": "unknown", "context_id": str(plan.pk)},
    )
    assert refused_response.status_code == unknown_response.status_code == 404
    assert refused_response.content == unknown_response.content == b"Report unavailable."
    assert Report.objects.count() == 1


def test_private_report_http_validates_conversation_and_received_message_contexts():
    reporter = create_test_user()
    create_verified_test_profile(user=reporter)
    target = create_test_user()
    target_profile = create_verified_test_profile(
        user=target,
        display_name="Report conversation target",
    )
    outsider = create_test_user()
    create_verified_test_profile(user=outsider)
    conversation = create_test_conversation(reporter, target)
    received_message = Message.objects.create(
        conversation=conversation,
        sender=target,
        body="Eligible received report context",
    )
    own_message = Message.objects.create(
        conversation=conversation,
        sender=reporter,
        body="Own message has no report action",
    )
    unrelated_conversation = create_test_conversation(reporter, outsider)
    unrelated_message = Message.objects.create(
        conversation=unrelated_conversation,
        sender=outsider,
        body="Unrelated message context",
    )
    client = Client()
    client.force_login(reporter)
    report_url = reverse("report_create", args=[target_profile.pk])
    conversation_response = client.get(
        reverse("conversation_detail", args=[conversation.pk])
    )

    assert conversation_response.status_code == 200
    assert b"Report this conversation privately" in conversation_response.content
    assert conversation_response.content.count(b"Report this message") == 1
    assert (
        f"context_id={received_message.pk}&amp;context_conversation_id={conversation.pk}".encode()
        in conversation_response.content
    )
    assert (
        f"context_id={own_message.pk}&amp;context_conversation_id={conversation.pk}".encode()
        not in conversation_response.content
    )

    conversation_report_response = client.post(
        report_url,
        {
            "category": Report.Category.OTHER,
            "description": "Private conversation context.",
            "context_type": "conversation",
            "context_id": str(conversation.pk),
        },
    )
    message_report_response = client.post(
        report_url,
        {
            "category": Report.Category.SAFETY_CONCERN,
            "description": "Private received-message context.",
            "context_type": "message",
            "context_id": str(received_message.pk),
            "context_conversation_id": str(conversation.pk),
        },
    )
    reports = list(Report.objects.order_by("pk"))
    assert conversation_report_response.status_code == 200
    assert message_report_response.status_code == 200
    assert reports[0].reported_conversation == conversation
    assert reports[1].reported_message == received_message

    refused_own_response = client.post(
        report_url,
        {
            "category": Report.Category.OTHER,
            "description": "Own message context must be refused.",
            "context_type": "message",
            "context_id": str(own_message.pk),
            "context_conversation_id": str(conversation.pk),
        },
    )
    refused_unrelated_response = client.post(
        report_url,
        {
            "category": Report.Category.OTHER,
            "description": "Unrelated message context must be refused.",
            "context_type": "message",
            "context_id": str(unrelated_message.pk),
            "context_conversation_id": str(unrelated_conversation.pk),
        },
    )
    assert refused_own_response.status_code == refused_unrelated_response.status_code == 404
    assert refused_own_response.content == refused_unrelated_response.content == b"Report unavailable."
    assert Report.objects.count() == 2


def test_private_report_form_accepts_only_bounded_category_and_description():
    valid_form = PrivateReportForm(
        data={
            "category": Report.Category.SAFETY_CONCERN,
            "description": "  A factual synthetic description.  ",
            "reporter": "999999",
            "reported_user": "999998",
            "status": Report.Status.REVIEWED,
            "reported_plan": "999997",
        }
    )
    invalid_form = PrivateReportForm(
        data={
            "category": "unapproved_category",
            "description": "x" * 2_001,
        }
    )
    empty_form = PrivateReportForm(
        data={"category": Report.Category.OTHER, "description": "   "}
    )

    assert tuple(valid_form.fields) == ("category", "description")
    assert valid_form.is_valid(), valid_form.errors
    assert valid_form.cleaned_data == {
        "category": Report.Category.SAFETY_CONCERN,
        "description": "A factual synthetic description.",
    }
    assert not invalid_form.is_valid()
    assert {"category", "description"} <= set(invalid_form.errors)
    assert not empty_form.is_valid()
    assert "description" in empty_form.errors


def test_report_policy_allows_different_authenticated_accounts_despite_blocks():
    reporter = create_test_user()
    reported_user = create_test_user()
    Block.objects.create(blocker=reporter, blocked_user=reported_user)
    Block.objects.create(blocker=reported_user, blocked_user=reporter)

    assert can_report_another_user(reporter, reported_user)
    assert can_report_another_user(reported_user, reporter)
    assert not can_report_another_user(reporter, reporter)
    assert not can_report_another_user(AnonymousUser(), reported_user)
    assert not can_report_another_user(reporter, None)


def test_block_service_is_idempotent_and_closes_discovery_and_messaging():
    blocker = create_test_user()
    create_verified_test_profile(user=blocker, broad_area="central")
    blocked_user = create_test_user()
    blocked_profile = create_verified_test_profile(
        user=blocked_user,
        broad_area="central",
    )
    conversation = find_or_start_direct_conversation(blocker, blocked_user)
    send_direct_message(blocked_user, conversation, "Visible before the block")
    filters = {
        "broad_area": "central",
        "interests": [],
        "available_now": False,
    }

    assert list(get_profiles_for_discovery_grid(blocker, filters)) == [blocked_profile]
    assert get_messages_if_user_can_open_conversation(blocker, conversation.pk)

    block = block_user_from_discovery_and_messages(blocker, blocked_user)
    repeated_block = block_user_from_discovery_and_messages(blocker, blocked_user)

    assert block.pk == repeated_block.pk
    assert Block.objects.filter(
        blocker=blocker,
        blocked_user=blocked_user,
    ).count() == 1
    assert not get_profiles_for_discovery_grid(blocker, filters).exists()
    assert get_profile_page_if_viewer_is_allowed(blocker, blocked_profile.pk) is None
    assert not get_unblocked_conversations_for_inbox(blocker).exists()
    assert get_messages_if_user_can_open_conversation(blocker, conversation.pk) is None
    assert (
        get_messages_if_user_can_open_conversation(blocked_user, conversation.pk)
        is None
    )
    assert not can_start_or_continue_direct_messages(blocker, blocked_user)


def test_block_service_refuses_anonymous_self_and_missing_targets_without_writes():
    blocker = create_test_user()
    target = create_test_user()

    with pytest.raises(PermissionDenied):
        block_user_from_discovery_and_messages(AnonymousUser(), target)
    with pytest.raises(PermissionDenied):
        block_user_from_discovery_and_messages(blocker, blocker)
    with pytest.raises(PermissionDenied):
        block_user_from_discovery_and_messages(blocker, None)

    assert not Block.objects.exists()


def test_report_target_selector_resolves_blocked_different_account_only():
    reporter = create_test_user()
    create_verified_test_profile(user=reporter)
    first_target = create_test_user()
    first_profile = create_verified_test_profile(user=first_target)
    second_target = create_test_user()
    second_profile = create_verified_test_profile(user=second_target)
    Block.objects.create(blocker=reporter, blocked_user=first_target)
    Block.objects.create(blocker=second_target, blocked_user=reporter)

    assert get_profile_page_if_viewer_is_allowed(reporter, first_profile.pk) is None
    assert get_profile_page_if_viewer_is_allowed(reporter, second_profile.pk) is None
    assert (
        get_report_target_profile_if_reporter_is_allowed(reporter, first_profile.pk)
        == first_profile
    )
    assert (
        get_report_target_profile_if_reporter_is_allowed(reporter, second_profile.pk)
        == second_profile
    )
    assert (
        get_report_target_profile_if_reporter_is_allowed(
            reporter,
            reporter.profile.pk,
        )
        is None
    )
    assert get_report_target_profile_if_reporter_is_allowed(reporter, 999999) is None
    assert (
        get_report_target_profile_if_reporter_is_allowed(
            AnonymousUser(),
            first_profile.pk,
        )
        is None
    )


def test_private_report_service_stores_received_reports_with_valid_contexts():
    reporter = create_test_user()
    reported_user = create_test_user()
    Profile.objects.create(user=reported_user)
    plan = create_test_plan(owner=reporter)
    Participation.objects.create(plan=plan, user=reported_user)
    conversation = create_test_conversation(reporter, reported_user)
    message = Message.objects.create(
        conversation=conversation,
        sender=reported_user,
        body="Synthetic report context",
    )
    Block.objects.create(blocker=reported_user, blocked_user=reporter)
    form = PrivateReportForm(
        data={
            "category": Report.Category.HARASSMENT,
            "description": "A bounded private statement.",
        }
    )
    assert form.is_valid(), form.errors
    report_details = dict(form.cleaned_data)
    report_details.update(
        {
            "reporter": reported_user,
            "reported_user": reporter,
            "status": Report.Status.REVIEWED,
            "received_at": timezone.now() - timezone.timedelta(days=1),
        }
    )

    reports = [
        submit_private_report_about_user(reporter, reported_user, report_details),
        submit_private_report_about_user(
            reporter,
            reported_user,
            report_details,
            reported_plan=plan,
        ),
        submit_private_report_about_user(
            reporter,
            reported_user,
            report_details,
            reported_conversation=conversation,
        ),
        submit_private_report_about_user(
            reporter,
            reported_user,
            report_details,
            reported_message=message,
        ),
    ]

    assert Report.objects.count() == 4
    assert all(report.reporter == reporter for report in reports)
    assert all(report.reported_user == reported_user for report in reports)
    assert all(report.status == Report.Status.RECEIVED for report in reports)
    assert reports[0].reported_plan_id is None
    assert reports[1].reported_plan == plan
    assert reports[2].reported_conversation == conversation
    assert reports[3].reported_message == message
    reported_user_summary = get_signed_in_user_account_summary(reported_user)
    assert "reports" not in reported_user_summary


def test_private_report_service_rejects_unrelated_or_multiple_context_without_writes():
    reporter = create_test_user()
    reported_user = create_test_user()
    outsider = create_test_user()
    unrelated_plan = create_test_plan(owner=reporter)
    unrelated_conversation = create_test_conversation(reporter, outsider)
    unrelated_message = Message.objects.create(
        conversation=unrelated_conversation,
        sender=outsider,
        body="Unrelated message",
    )
    report_details = {
        "category": Report.Category.OTHER,
        "description": "A valid bounded description.",
    }

    refused_calls = (
        lambda: submit_private_report_about_user(
            reporter,
            reported_user,
            report_details,
            reported_plan=unrelated_plan,
        ),
        lambda: submit_private_report_about_user(
            reporter,
            reported_user,
            report_details,
            reported_conversation=unrelated_conversation,
        ),
        lambda: submit_private_report_about_user(
            reporter,
            reported_user,
            report_details,
            reported_message=unrelated_message,
        ),
        lambda: submit_private_report_about_user(
            reporter,
            reported_user,
            report_details,
            reported_plan=unrelated_plan,
            reported_conversation=unrelated_conversation,
        ),
        lambda: submit_private_report_about_user(
            reporter,
            reporter,
            report_details,
        ),
        lambda: submit_private_report_about_user(
            AnonymousUser(),
            reported_user,
            report_details,
        ),
    )

    for refused_call in refused_calls:
        with pytest.raises(PermissionDenied):
            refused_call()

    assert not Report.objects.exists()


class ConversationPairRaceTests(TransactionTestCase):
    """Prove PostgreSQL uniqueness resolves simultaneous pair creation once."""

    def setUp(self):
        self.first_user = create_test_user()
        create_verified_test_profile(user=self.first_user)
        self.second_user = create_test_user()
        create_verified_test_profile(user=self.second_user)

    def test_conversation_pair_race_returns_one_database_authoritative_row(self):
        start_together = Barrier(2)

        def start_conversation(user_id, other_user_id):
            close_old_connections()
            try:
                user = get_user_model().objects.get(pk=user_id)
                other_user = get_user_model().objects.get(pk=other_user_id)
                start_together.wait(timeout=5)
                return find_or_start_direct_conversation(user, other_user).pk
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as executor:
            outcomes = list(
                executor.map(
                    lambda pair: start_conversation(*pair),
                    (
                        (self.first_user.pk, self.second_user.pk),
                        (self.second_user.pk, self.first_user.pk),
                    ),
                )
            )

        self.assertEqual(outcomes[0], outcomes[1])
        self.assertEqual(Conversation.objects.count(), 1)
        conversation = Conversation.objects.get()
        self.assertEqual(conversation.first_user_id, self.first_user.pk)
        self.assertEqual(conversation.second_user_id, self.second_user.pk)


def test_profile_verification_constraint_and_availability_helper():
    user = create_test_user()
    reviewer = create_test_user(is_staff=True)

    with pytest.raises(IntegrityError), transaction.atomic():
        Profile.objects.create(user=user, is_verified=True)

    profile = create_verified_test_profile(user=user, verified_by=reviewer)
    with pytest.raises(IntegrityError), transaction.atomic():
        Profile.objects.create(user=user)

    future = timezone.now() + timezone.timedelta(hours=1)
    profile.availability_start = Profile.AvailabilityStart.TOMORROW
    profile.available_from = future
    profile.save(update_fields=["availability_start", "available_from"])

    assert not profile.is_available_now(timezone.now())
    assert profile.is_available_now(future)

    profile.availability_start = ""
    with pytest.raises(IntegrityError), transaction.atomic():
        profile.save(update_fields=["availability_start"])

    profile.is_verified = False
    with pytest.raises(IntegrityError), transaction.atomic():
        profile.save(update_fields=["is_verified"])


def test_plan_approval_and_capacity_constraints_and_open_helper():
    owner = create_test_user()
    reviewer = create_test_user(is_staff=True)

    with pytest.raises(IntegrityError), transaction.atomic():
        create_test_plan(owner=owner, capacity=0)
    with pytest.raises(IntegrityError), transaction.atomic():
        create_test_plan(
            owner=owner,
            status=Plan.Status.APPROVED,
            approved_at=None,
            approved_by=reviewer,
        )

    plan = create_test_plan(owner=owner, status=Plan.Status.APPROVED, capacity=1)
    assert plan.is_open_for_joining(timezone.now())

    participant = create_test_user()
    Participation.objects.create(plan=plan, user=participant)
    assert not plan.is_open_for_joining(timezone.now())


def test_participation_state_and_uniqueness_constraints():
    plan = create_test_plan()
    user = create_test_user()
    Participation.objects.create(plan=plan, user=user)

    with pytest.raises(IntegrityError), transaction.atomic():
        Participation.objects.create(plan=plan, user=user)
    with pytest.raises(IntegrityError), transaction.atomic():
        Participation.objects.create(
            plan=plan,
            user=create_test_user(),
            status=Participation.Status.LEFT,
            left_at=None,
        )
    with pytest.raises(IntegrityError), transaction.atomic():
        Participation.objects.create(
            plan=plan,
            user=create_test_user(),
            status=Participation.Status.JOINED,
            left_at=timezone.now(),
        )


def test_conversation_pair_constraints_and_membership_helper():
    lower_user = create_test_user()
    higher_user = create_test_user()
    outsider = create_test_user()
    conversation = create_test_conversation(lower_user, higher_user)

    assert conversation.includes_account(lower_user)
    assert conversation.includes_account(higher_user)
    assert not conversation.includes_account(outsider)

    with pytest.raises(IntegrityError), transaction.atomic():
        Conversation.objects.create(first_user=lower_user, second_user=lower_user)
    with pytest.raises(IntegrityError), transaction.atomic():
        Conversation.objects.create(first_user=higher_user, second_user=lower_user)
    with pytest.raises(IntegrityError), transaction.atomic():
        Conversation.objects.create(first_user=lower_user, second_user=higher_user)


def test_block_direction_constraints():
    blocker = create_test_user()
    blocked_user = create_test_user()
    Block.objects.create(blocker=blocker, blocked_user=blocked_user)

    with pytest.raises(IntegrityError), transaction.atomic():
        Block.objects.create(blocker=blocker, blocked_user=blocker)
    with pytest.raises(IntegrityError), transaction.atomic():
        Block.objects.create(blocker=blocker, blocked_user=blocked_user)


def test_report_target_and_single_context_constraints():
    reporter = create_test_user()
    reported_user = create_test_user()
    plan = create_test_plan(owner=reporter)
    conversation = create_test_conversation(reporter, reported_user)

    with pytest.raises(IntegrityError), transaction.atomic():
        Report.objects.create(
            reporter=reporter,
            reported_user=reporter,
            category=Report.Category.OTHER,
            description="Synthetic self report",
        )
    with pytest.raises(IntegrityError), transaction.atomic():
        Report.objects.create(
            reporter=reporter,
            reported_user=reported_user,
            category=Report.Category.OTHER,
            description="Synthetic report with excessive context",
            reported_plan=plan,
            reported_conversation=conversation,
        )

    report = Report.objects.create(
        reporter=reporter,
        reported_user=reported_user,
        category=Report.Category.OTHER,
        description="Synthetic context-free report",
    )
    assert report.reported_plan_id is None
    assert report.reported_conversation_id is None
    assert report.reported_message_id is None


def test_first_checkout_uses_one_no_card_trial_and_browser_return_grants_nothing(
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
        "kindlelise.services.stripe.checkout.Session.create",
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
    assert submitted_values["payment_method_collection"] == "if_required"
    assert submitted_values["subscription_data"] == {
        "metadata": {"kindlelise_user_id": str(account.pk)},
        "trial_period_days": 30,
        "trial_settings": {
            "end_behavior": {"missing_payment_method": "create_invoice"}
        },
    }
    assert "customer" not in submitted_values
    assert not PlatformSubscription.objects.filter(user=account).exists()


def test_stripe_history_omits_second_trial_and_active_subscription_is_not_duplicated(
    monkeypatch,
    settings,
):
    account = create_test_user()
    settings.STRIPE_SECRET_KEY = "sk_test_synthetic"
    settings.STRIPE_PRICE_ID = "price_test_gbp_499_year"
    subscription = PlatformSubscription.objects.create(
        user=account,
        stripe_customer_id="cus_test_history",
        stripe_subscription_id="sub_test_cancelled",
        stripe_status="cancelled",
    )
    submitted_values = {}
    provider_call_count = 0

    def create_checkout(**values):
        nonlocal provider_call_count
        provider_call_count += 1
        submitted_values.update(values)
        return SimpleNamespace(
            url="https://checkout.stripe.com/c/pay/cs_test_paid"
        )

    monkeypatch.setattr(
        "kindlelise.services.stripe.checkout.Session.create",
        create_checkout,
    )
    start_stripe_subscription_checkout(
        account,
        "https://kindlelise.test/account/",
        "https://kindlelise.test/account/",
    )

    assert submitted_values["customer"] == "cus_test_history"
    assert submitted_values["subscription_data"] == {
        "metadata": {"kindlelise_user_id": str(account.pk)}
    }

    subscription.stripe_status = "trialing"
    subscription.save(update_fields=["stripe_status"])
    with pytest.raises(PermissionDenied):
        start_stripe_subscription_checkout(
            account,
            "https://kindlelise.test/account/",
            "https://kindlelise.test/account/",
        )
    assert provider_call_count == 1


def test_customer_portal_uses_only_the_owning_accounts_recorded_customer(
    monkeypatch,
    settings,
):
    account = create_test_user()
    other_account = create_test_user()
    settings.STRIPE_SECRET_KEY = "sk_test_synthetic"
    PlatformSubscription.objects.create(
        user=account,
        stripe_customer_id="cus_test_owner",
    )
    submitted_values = {}

    def create_portal(**values):
        submitted_values.update(values)
        return SimpleNamespace(
            url="https://billing.stripe.com/p/session/bps_test_synthetic"
        )

    monkeypatch.setattr(
        "kindlelise.services.stripe.billing_portal.Session.create",
        create_portal,
    )
    portal_url = open_stripe_customer_portal(
        account,
        "https://kindlelise.test/account/",
    )

    assert portal_url.startswith("https://billing.stripe.com/")
    assert submitted_values["customer"] == "cus_test_owner"
    assert submitted_values["return_url"] == "https://kindlelise.test/account/"
    with pytest.raises(PermissionDenied):
        open_stripe_customer_portal(
            other_account,
            "https://kindlelise.test/account/",
        )


def test_checkout_webhook_links_by_immutable_user_id_and_never_grants_access():
    account = create_test_user(email="ignored-owner@example.test")
    event = build_stripe_test_event(
        "checkout.session.completed",
        event_id="evt_test_checkout_identity",
        data={
            "id": "cs_test_identity",
            "customer": "cus_test_identity",
            "subscription": "sub_test_identity",
            "client_reference_id": str(account.pk),
            "customer_details": {"email": "another-account@example.test"},
        },
    )

    assert update_premium_access_from_verified_stripe_event(event)
    subscription = PlatformSubscription.objects.get(user=account)
    receipt = StripeWebhookReceipt.objects.get(
        stripe_event_id="evt_test_checkout_identity"
    )
    assert subscription.stripe_customer_id == "cus_test_identity"
    assert subscription.stripe_subscription_id == "sub_test_identity"
    assert subscription.stripe_status is None
    assert subscription.access_until is None
    assert subscription.latest_provider_event_at is None
    assert not subscription.has_premium_access()
    assert receipt.processed_at is not None

    email_only_event = build_stripe_test_event(
        "checkout.session.completed",
        event_id="evt_test_email_only",
        data={
            "customer": "cus_test_email_only",
            "subscription": "sub_test_email_only",
            "customer_details": {"email": account.email},
        },
    )
    with pytest.raises(ValueError):
        update_premium_access_from_verified_stripe_event(email_only_event)
    assert not StripeWebhookReceipt.objects.filter(
        stripe_event_id="evt_test_email_only"
    ).exists()


def test_conflicting_stripe_identifiers_are_rejected_without_receipt_or_reassignment():
    owner = create_test_user()
    attacker_target = create_test_user()
    PlatformSubscription.objects.create(
        user=owner,
        stripe_customer_id="cus_test_conflict",
        stripe_subscription_id="sub_test_owner",
    )
    event = build_stripe_test_event(
        "customer.subscription.updated",
        event_id="evt_test_conflict",
        data={
            "id": "sub_test_attacker",
            "customer": "cus_test_conflict",
            "status": "trialing",
            "trial_end": int(
                (timezone.now() + timezone.timedelta(days=30)).timestamp()
            ),
            "metadata": {"kindlelise_user_id": str(attacker_target.pk)},
        },
    )

    with pytest.raises(ValueError):
        update_premium_access_from_verified_stripe_event(event)
    assert PlatformSubscription.objects.get(user=owner).stripe_subscription_id == (
        "sub_test_owner"
    )
    assert not PlatformSubscription.objects.filter(user=attacker_target).exists()
    assert not StripeWebhookReceipt.objects.filter(
        stripe_event_id="evt_test_conflict"
    ).exists()


def test_stripe_trialing_update_grants_only_trial_and_ineligible_updates_deny_access():
    account = create_test_user()
    now = timezone.now()
    trial_end = now + timezone.timedelta(days=30)
    trial_event = build_stripe_test_event(
        event_id="evt_test_trialing",
        provider_created_at=now,
        data={
            "id": "sub_test_trialing",
            "customer": "cus_test_trialing",
            "status": "trialing",
            "trial_end": int(trial_end.timestamp()),
            "metadata": {"kindlelise_user_id": str(account.pk)},
        },
    )
    assert update_premium_access_from_verified_stripe_event(trial_event)
    subscription = PlatformSubscription.objects.get(user=account)
    stored_trial_end = subscription.access_until
    assert subscription.stripe_status == "trialing"
    assert abs((stored_trial_end - trial_end).total_seconds()) < 1
    assert subscription.has_premium_access()

    active_event = build_stripe_test_event(
        event_id="evt_test_active_without_payment",
        provider_created_at=now + timezone.timedelta(seconds=1),
        data={
            "id": "sub_test_trialing",
            "customer": "cus_test_trialing",
            "status": "active",
            "metadata": {"kindlelise_user_id": str(account.pk)},
            "current_period_end": int(
                (now + timezone.timedelta(days=395)).timestamp()
            ),
        },
    )
    assert update_premium_access_from_verified_stripe_event(active_event)
    subscription.refresh_from_db()
    assert subscription.stripe_status == "active"
    assert subscription.access_until == stored_trial_end

    past_due_event = build_stripe_test_event(
        event_id="evt_test_past_due",
        provider_created_at=now + timezone.timedelta(seconds=2),
        data={
            "id": "sub_test_trialing",
            "customer": "cus_test_trialing",
            "status": "past_due",
            "metadata": {"kindlelise_user_id": str(account.pk)},
        },
    )
    assert update_premium_access_from_verified_stripe_event(past_due_event)
    subscription.refresh_from_db()
    assert subscription.stripe_status == "past_due"
    assert subscription.access_until is None
    assert not subscription.has_premium_access()

    unpaid_event = build_stripe_test_event(
        event_id="evt_test_unpaid",
        provider_created_at=now + timezone.timedelta(seconds=3),
        data={
            "id": "sub_test_trialing",
            "customer": "cus_test_trialing",
            "status": "unpaid",
            "metadata": {"kindlelise_user_id": str(account.pk)},
        },
    )
    assert update_premium_access_from_verified_stripe_event(unpaid_event)
    subscription.refresh_from_db()
    assert subscription.stripe_status == "unpaid"
    assert subscription.access_until is None
    assert not subscription.has_premium_access()


def test_stripe_paid_invoice_for_configured_gbp_price_grants_only_annual_period(
    settings,
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
        latest_provider_event_at=now - timezone.timedelta(seconds=1),
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
                    "subscription": {"id": "sub_test_paid", "status": "active"},
                    "metadata": {"kindlelise_user_id": str(account.pk)},
                },
            },
            "lines": {
                "data": [
                    {
                        "currency": "gbp",
                        "quantity": 1,
                        "pricing": {
                            "price_details": {
                                "price": "price_test_gbp_499_year"
                            }
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
                        "pricing": {
                            "price_details": {"price": "price_test_other"}
                        },
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
    event["data"]["object"]["lines"]["data"][0]["pricing"]["price_details"][
        "price"
    ] = "price_test_gbp_499_year"
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
                            "price_details": {
                                "price": "price_test_gbp_499_year"
                            }
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
    assert StripeWebhookReceipt.objects.filter(
        stripe_event_id="evt_test_delayed_paid"
    ).count() == 1

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
    newer_period_event["created"] = int((now - timezone.timedelta(seconds=2)).timestamp())
    assert not update_premium_access_from_verified_stripe_event(newer_period_event)
    subscription.refresh_from_db()
    assert subscription.stripe_status == "cancelled"
    assert subscription.access_until is None


def test_stripe_supported_event_failure_rolls_back_receipt_and_subscription_change(
    monkeypatch,
):
    account = create_test_user()
    subscription = PlatformSubscription.objects.create(user=account)
    event = build_stripe_test_event(
        event_id="evt_test_atomic_failure",
        data={
            "id": "sub_test_atomic_failure",
            "customer": "cus_test_atomic_failure",
            "status": "trialing",
            "trial_end": int(
                (timezone.now() + timezone.timedelta(days=30)).timestamp()
            ),
            "metadata": {"kindlelise_user_id": str(account.pk)},
        },
    )

    def refuse_subscription_save(*args, **kwargs):
        raise IntegrityError("synthetic projection failure")

    monkeypatch.setattr(PlatformSubscription, "save", refuse_subscription_save)
    with pytest.raises(IntegrityError):
        update_premium_access_from_verified_stripe_event(event)

    subscription.refresh_from_db()
    assert subscription.stripe_customer_id is None
    assert subscription.stripe_subscription_id is None
    assert subscription.stripe_status is None
    assert not StripeWebhookReceipt.objects.filter(
        stripe_event_id="evt_test_atomic_failure"
    ).exists()


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
        return supported_event

    monkeypatch.setattr(
        "kindlelise.views.stripe.Webhook.construct_event",
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
    assert "private-webhook-marker" not in caplog.text
    assert "whsec_test_synthetic" not in caplog.text
    assert client.get(reverse("stripe_webhook")).status_code == 405

    monkeypatch.setattr(
        "kindlelise.views.stripe.Webhook.construct_event",
        lambda *args, **kwargs: (_ for _ in ()).throw(ValueError("invalid")),
    )
    assert client.post(
        reverse("stripe_webhook"),
        data=b"invalid",
        content_type="application/json",
        HTTP_STRIPE_SIGNATURE="invalid",
    ).status_code == 400

    monkeypatch.setattr(
        "kindlelise.views.stripe.Webhook.construct_event",
        lambda *args, **kwargs: build_stripe_test_event(
            "invoice.created",
            event_id="evt_test_unsupported_http",
        ),
    )
    assert client.post(
        reverse("stripe_webhook"),
        data=b"{}",
        content_type="application/json",
        HTTP_STRIPE_SIGNATURE="synthetic",
    ).status_code == 200
    assert not StripeWebhookReceipt.objects.filter(
        stripe_event_id="evt_test_unsupported_http"
    ).exists()

    monkeypatch.setattr(
        "kindlelise.views.stripe.Webhook.construct_event",
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
        "kindlelise.views.update_premium_access_from_verified_stripe_event",
        lambda event: (_ for _ in ()).throw(IntegrityError("synthetic failure")),
    )
    assert client.post(
        reverse("stripe_webhook"),
        data=raw_body,
        content_type="application/json",
        HTTP_STRIPE_SIGNATURE="synthetic",
    ).status_code == 500
    assert not StripeWebhookReceipt.objects.filter(
        stripe_event_id="evt_test_retryable_http"
    ).exists()
    assert "private-webhook-marker" not in caplog.text


def test_premium_http_uses_csrf_server_urls_and_safe_account_presentation(
    monkeypatch,
    settings,
):
    account = create_test_user()
    Profile.objects.create(user=account, display_name="Premium tester")
    settings.STRIPE_SECRET_KEY = "sk_test_synthetic"
    settings.STRIPE_PRICE_ID = "price_test_gbp_499_year"
    checkout_values = {}

    def create_checkout(**values):
        checkout_values.update(values)
        return SimpleNamespace(
            url="https://checkout.stripe.com/c/pay/cs_test_http"
        )

    monkeypatch.setattr(
        "kindlelise.services.stripe.checkout.Session.create",
        create_checkout,
    )
    client = Client(enforce_csrf_checks=True)
    client.force_login(account)
    account_response = client.get(reverse("account"))
    assert account_response.status_code == 200
    assert b"30 days free" in account_response.content
    assert b"then \xc2\xa34.99 yearly" in account_response.content
    assert b"Start 30-day trial" in account_response.content
    assert b"No payment details are required" in account_response.content
    assert client.post(reverse("premium_subscription_checkout")).status_code == 403

    csrf_token = client.cookies["csrftoken"].value
    checkout_response = client.post(
        reverse("premium_subscription_checkout"),
        {
            "csrfmiddlewaretoken": csrf_token,
            "success_url": "https://attacker.test/",
            "cancel_url": "https://attacker.test/",
            "customer": "cus_attacker",
        },
    )
    assert checkout_response.status_code == 302
    assert checkout_response.url.startswith("https://checkout.stripe.com/")
    assert checkout_values["success_url"] == "http://testserver/account/"
    assert checkout_values["cancel_url"] == "http://testserver/account/"
    assert checkout_values["client_reference_id"] == str(account.pk)
    assert checkout_values.get("customer") is None

    PlatformSubscription.objects.create(
        user=account,
        stripe_customer_id="cus_test_http_portal",
        stripe_subscription_id="sub_test_http_portal",
        stripe_status="past_due",
    )
    portal_values = {}

    def create_portal(**values):
        portal_values.update(values)
        return SimpleNamespace(
            url="https://billing.stripe.com/p/session/bps_test_http"
        )

    monkeypatch.setattr(
        "kindlelise.services.stripe.billing_portal.Session.create",
        create_portal,
    )
    account_response = client.get(reverse("account"))
    assert b"Payment due" in account_response.content
    assert b"Pay \xc2\xa34.99 or manage subscription" in account_response.content
    portal_response = client.post(
        reverse("premium_subscription_portal"),
        {
            "csrfmiddlewaretoken": csrf_token,
            "customer": "cus_attacker",
            "return_url": "https://attacker.test/",
        },
    )
    assert portal_response.status_code == 302
    assert portal_response.url.startswith("https://billing.stripe.com/")
    assert portal_values["customer"] == "cus_test_http_portal"
    assert portal_values["return_url"] == "http://testserver/account/"


def test_ollama_editor_sends_only_bounded_draft_and_each_fixed_goal(
    monkeypatch,
    settings,
    caplog,
):
    settings.OLLAMA_API_URL = "https://ollama.test/api/generate"
    settings.OLLAMA_API_KEY = "ollama_test_synthetic_key"
    settings.OLLAMA_MODEL = "model-test-pinned"
    settings.OLLAMA_TIMEOUT_SECONDS = 3
    private_draft = "  i has a private synthetic draft  "
    private_suggestion = "I have a private synthetic draft."
    provider_response = SimpleNamespace(
        read=lambda byte_limit: json.dumps(
            {
                "model": "model-test-pinned",
                "response": f"  {private_suggestion}  ",
                "done": True,
            }
        ).encode(),
        close=lambda: None,
    )
    fake_request = replace_ollama_request_with_fake(
        monkeypatch,
        ai_message_editor,
        provider_response,
    )

    caplog.clear()
    grammar_suggestion = get_edited_message_draft_suggestion(
        private_draft,
        "fix_grammar",
    )
    clarity_suggestion = get_edited_message_draft_suggestion(
        private_draft,
        "improve_clarity",
    )

    assert grammar_suggestion == clarity_suggestion == private_suggestion
    assert len(fake_request.calls) == 2
    first_request, first_values = fake_request.calls[0]
    second_request, second_values = fake_request.calls[1]
    grammar_request = first_request[0]
    clarity_request = second_request[0]
    grammar_payload = json.loads(grammar_request.data)
    clarity_payload = json.loads(clarity_request.data)
    assert set(grammar_payload) == {"model", "prompt", "system", "stream"}
    assert grammar_payload["model"] == "model-test-pinned"
    assert grammar_payload["prompt"] == private_draft.strip()
    assert grammar_payload["stream"] is False
    assert grammar_payload["system"].startswith("Correct grammar only.")
    assert clarity_payload["system"].startswith("Improve clarity only.")
    assert grammar_payload["system"] != clarity_payload["system"]
    assert grammar_request.full_url == "https://ollama.test/api/generate"
    assert grammar_request.get_method() == "POST"
    assert grammar_request.get_header("Authorization") == (
        "Bearer ollama_test_synthetic_key"
    )
    assert grammar_request.get_header("Content-type") == "application/json"
    assert first_values["timeout"] == second_values["timeout"] == 3
    serialized_payloads = grammar_request.data + clarity_request.data
    assert b"profile" not in serialized_payloads.lower()
    assert b"recipient" not in serialized_payloads.lower()
    assert b"conversation" not in serialized_payloads.lower()
    assert b"report" not in serialized_payloads.lower()
    assert private_draft.strip() not in caplog.text
    assert private_suggestion not in caplog.text
    assert "ollama_test_synthetic_key" not in caplog.text


def test_ollama_form_and_editor_reject_invalid_input_before_provider_call(
    monkeypatch,
    settings,
):
    valid_form = MessageEditRequestForm(
        data={
            "draft": "  Please make this easier to read.  ",
            "editing_goal": "improve_clarity",
            "conversation": "999999",
        }
    )
    invalid_goal_form = MessageEditRequestForm(
        data={"draft": "Bounded draft", "editing_goal": "write_reply"}
    )
    empty_form = MessageEditRequestForm(
        data={"draft": "   ", "editing_goal": "fix_grammar"}
    )
    oversized_form = MessageEditRequestForm(
        data={"draft": "x" * 1_001, "editing_goal": "fix_grammar"}
    )
    assert tuple(valid_form.fields) == ("draft", "editing_goal")
    assert valid_form.is_valid(), valid_form.errors
    assert valid_form.cleaned_data == {
        "draft": "Please make this easier to read.",
        "editing_goal": "improve_clarity",
    }
    assert not invalid_goal_form.is_valid()
    assert not empty_form.is_valid()
    assert not oversized_form.is_valid()

    settings.OLLAMA_API_URL = "https://ollama.test/api/generate"
    settings.OLLAMA_API_KEY = "ollama_test_synthetic_key"
    settings.OLLAMA_MODEL = "model-test-pinned"
    fake_request = replace_ollama_request_with_fake(
        monkeypatch,
        ai_message_editor,
        SimpleNamespace(read=lambda limit: b"{}", close=lambda: None),
    )
    assert get_edited_message_draft_suggestion("   ", "fix_grammar") is None
    assert (
        get_edited_message_draft_suggestion("x" * 1_001, "fix_grammar") is None
    )
    assert get_edited_message_draft_suggestion("Draft", "write_reply") is None
    settings.OLLAMA_API_URL = "http://ollama.test/api/generate"
    assert get_edited_message_draft_suggestion("Draft", "fix_grammar") is None
    settings.OLLAMA_API_URL = "https://user:password@ollama.test/api/generate"
    assert get_edited_message_draft_suggestion("Draft", "fix_grammar") is None
    assert fake_request.calls == []


def test_ollama_timeout_and_invalid_outputs_preserve_draft_without_logs(
    monkeypatch,
    settings,
    caplog,
):
    settings.OLLAMA_API_URL = "https://ollama.test/api/generate"
    settings.OLLAMA_API_KEY = "ollama_test_synthetic_key"
    settings.OLLAMA_MODEL = "model-test-pinned"
    private_draft = "Original private timeout draft"
    invalid_outcomes = (
        TimeoutError("synthetic timeout"),
        SimpleNamespace(read=lambda limit: b"not-json", close=lambda: None),
        SimpleNamespace(
            read=lambda limit: json.dumps(
                {"response": "Incomplete response", "done": False}
            ).encode(),
            close=lambda: None,
        ),
        SimpleNamespace(
            read=lambda limit: json.dumps(
                {"response": "   ", "done": True}
            ).encode(),
            close=lambda: None,
        ),
        SimpleNamespace(
            read=lambda limit: json.dumps(
                {"response": "x" * 1_001, "done": True}
            ).encode(),
            close=lambda: None,
        ),
    )

    caplog.clear()
    for outcome in invalid_outcomes:
        replace_ollama_request_with_fake(
            monkeypatch,
            ai_message_editor,
            outcome,
        )
        assert (
            get_edited_message_draft_suggestion(private_draft, "fix_grammar")
            is None
        )
    assert private_draft not in caplog.text
    assert "Incomplete response" not in caplog.text
    assert "ollama_test_synthetic_key" not in caplog.text


def test_ollama_http_requires_csrf_preserves_draft_then_uses_manual_send(
    monkeypatch,
    caplog,
):
    sender = create_test_user()
    create_verified_test_profile(user=sender)
    recipient = create_test_user()
    create_verified_test_profile(user=recipient, display_name="Ollama test peer")
    conversation = create_test_conversation(sender, recipient)
    edit_calls = []
    original_draft = "  this are the original private draft  "
    suggestion = "This is the suggested <script>plain text</script> draft."

    def return_suggestion(draft, editing_goal):
        edit_calls.append((draft, editing_goal))
        return suggestion

    monkeypatch.setattr(
        "kindlelise.views.get_edited_message_draft_suggestion",
        return_suggestion,
    )
    client = Client(enforce_csrf_checks=True)
    client.force_login(sender)
    detail_url = reverse("conversation_detail", args=[conversation.pk])
    edit_url = reverse(
        "conversation_message_edit_suggestion",
        args=[conversation.pk],
    )
    detail_response = client.get(detail_url)
    assert detail_response.status_code == 200
    assert b"Only this draft" in detail_response.content
    assert b"Fix grammar" in detail_response.content
    assert b"Improve clarity" in detail_response.content
    assert detail_response.content.count(b'data-message-edit-goal=') == 2
    assert b'<script src="/static/app.' in detail_response.content
    assert b'.js" defer></script>' in detail_response.content
    assert client.get(edit_url).status_code == 405
    assert client.post(
        edit_url,
        {"draft": original_draft, "editing_goal": "fix_grammar"},
    ).status_code == 403
    assert edit_calls == []
    assert not Message.objects.filter(conversation=conversation).exists()

    csrf_token = client.cookies["csrftoken"].value
    caplog.clear()
    suggestion_response = client.post(
        edit_url,
        {
            "csrfmiddlewaretoken": csrf_token,
            "draft": original_draft,
            "editing_goal": "fix_grammar",
        },
    )
    assert suggestion_response.status_code == 200
    assert suggestion_response.json() == {"suggestion": suggestion}
    assert edit_calls == [(original_draft.strip(), "fix_grammar")]
    assert not Message.objects.filter(conversation=conversation).exists()
    assert original_draft.strip() not in caplog.text
    assert suggestion not in caplog.text

    send_response = client.post(
        reverse("conversation_message_send", args=[conversation.pk]),
        {
            "csrfmiddlewaretoken": csrf_token,
            "body": suggestion,
        },
    )
    assert send_response.status_code == 302
    stored_message = Message.objects.get(conversation=conversation)
    assert stored_message.sender == sender
    assert stored_message.body == suggestion


def test_ollama_http_refuses_invalid_or_unauthorised_requests_without_provider_call(
    monkeypatch,
):
    sender = create_test_user()
    sender_profile = create_verified_test_profile(user=sender)
    recipient = create_test_user()
    create_verified_test_profile(user=recipient)
    outsider = create_test_user()
    create_verified_test_profile(user=outsider)
    conversation = create_test_conversation(sender, recipient)
    unverified = create_test_user()
    Profile.objects.create(user=unverified)
    unverified_conversation = create_test_conversation(unverified, recipient)
    provider_calls = []

    def record_provider_call(draft, editing_goal):
        provider_calls.append((draft, editing_goal))
        return "Must never be returned"

    monkeypatch.setattr(
        "kindlelise.views.get_edited_message_draft_suggestion",
        record_provider_call,
    )
    edit_url = reverse(
        "conversation_message_edit_suggestion",
        args=[conversation.pk],
    )
    valid_values = {"draft": "Private authorised draft", "editing_goal": "fix_grammar"}

    assert Client().post(edit_url, valid_values).status_code == 302
    outsider_client = Client()
    outsider_client.force_login(outsider)
    assert outsider_client.post(edit_url, valid_values).status_code == 404

    unverified_client = Client()
    unverified_client.force_login(unverified)
    unverified_response = unverified_client.post(
        reverse(
            "conversation_message_edit_suggestion",
            args=[unverified_conversation.pk],
        ),
        valid_values,
    )
    assert unverified_response.status_code == 302
    assert unverified_response.url == reverse("account")

    sender_client = Client()
    sender_client.force_login(sender)
    Block.objects.create(blocker=recipient, blocked_user=sender)
    assert sender_client.post(edit_url, valid_values).status_code == 404
    Block.objects.all().delete()
    Block.objects.create(blocker=sender, blocked_user=recipient)
    assert sender_client.post(edit_url, valid_values).status_code == 404
    Block.objects.all().delete()

    assert sender_client.post(
        edit_url,
        {"draft": "Private draft", "editing_goal": "write_reply"},
    ).status_code == 400
    assert sender_client.post(
        edit_url,
        {"draft": "   ", "editing_goal": "fix_grammar"},
    ).status_code == 400
    assert sender_client.post(
        edit_url,
        {"draft": "x" * 1_001, "editing_goal": "fix_grammar"},
    ).status_code == 400
    assert sender_client.post(
        reverse("conversation_message_edit_suggestion", args=[999999]),
        valid_values,
    ).status_code == 404
    assert provider_calls == []
    assert not Message.objects.exists()
    assert sender_profile.is_verified


def test_ollama_provider_failure_returns_quiet_error_without_sending(
    monkeypatch,
):
    sender = create_test_user()
    create_verified_test_profile(user=sender)
    recipient = create_test_user()
    create_verified_test_profile(user=recipient)
    conversation = create_test_conversation(sender, recipient)
    monkeypatch.setattr(
        "kindlelise.views.get_edited_message_draft_suggestion",
        lambda draft, editing_goal: None,
    )
    client = Client()
    client.force_login(sender)

    response = client.post(
        reverse(
            "conversation_message_edit_suggestion",
            args=[conversation.pk],
        ),
        {
            "draft": "Original draft remains in the browser",
            "editing_goal": "improve_clarity",
        },
    )

    assert response.status_code == 503
    assert response.json() == {"error": "Draft edit unavailable."}
    assert not Message.objects.filter(conversation=conversation).exists()


def test_authenticated_interface_has_accessible_primary_navigation_and_errors():
    viewer = create_test_user()
    create_verified_test_profile(user=viewer)
    client = Client()
    client.force_login(viewer)

    response = client.get(reverse("discover"))

    assert response.status_code == 200
    html = response.content.decode()
    assert 'href="#main-content">Skip to content</a>' in html
    assert '<nav class="primary-navigation" aria-label="Primary navigation">' in html
    assert html.index(">Discover</a>") < html.index(">Plans</a>")
    assert html.index(">Plans</a>") < html.index(">Messages</a>")
    assert html.index(">Messages</a>") < html.index(">Profile</a>")
    assert html.count('aria-current="page"') == 1
    assert 'id="connection-status"' in html
    assert 'role="status" hidden' in html

    invalid_response = client.post(
        reverse("profile_edit"),
        {
            "display_name": "",
            "biography": "",
            "broad_area": "not-configured",
            "availability_start": "",
            "interests": [],
        },
    )
    invalid_html = invalid_response.content.decode()
    assert invalid_response.status_code == 200
    assert 'class="error-summary" role="alert"' in invalid_html
    assert 'aria-invalid="true"' in invalid_html
    assert 'aria-describedby="id_display_name_error"' in invalid_html
    assert 'id="id_display_name_error"' in invalid_html


def test_list_page_query_counts_stay_constant_from_five_to_fifty_rows():
    viewer = create_test_user()
    reviewer = create_test_user(is_staff=True)
    create_verified_test_profile(user=viewer, verified_by=reviewer)
    client = Client()
    client.force_login(viewer)

    def add_visible_rows(first_number, last_number):
        user_model = get_user_model()
        accounts = user_model.objects.bulk_create(
            [user_model(username=f"query_user_{number}") for number in range(first_number, last_number)]
        )
        verified_at = timezone.now()
        Profile.objects.bulk_create(
            [
                Profile(
                    user=account,
                    display_name=f"Query user {account.pk}",
                    broad_area="central",
                    is_verified=True,
                    verified_at=verified_at,
                    verified_by=reviewer,
                )
                for account in accounts
            ]
        )
        Plan.objects.bulk_create(
            [
                Plan(
                    owner=account,
                    title=f"Query plan {account.pk}",
                    description="Synthetic performance fixture.",
                    public_place="Central Library",
                    public_url="https://example.test/library",
                    starts_at=verified_at + timezone.timedelta(days=1),
                    capacity=2,
                    status=Plan.Status.APPROVED,
                    approved_at=verified_at,
                    approved_by=reviewer,
                )
                for account in accounts
            ]
        )
        Conversation.objects.bulk_create(
            [
                Conversation(
                    first_user=viewer if viewer.pk < account.pk else account,
                    second_user=account if viewer.pk < account.pk else viewer,
                )
                for account in accounts
            ]
        )

    def page_query_counts():
        counts = []
        for route_name in ("discover", "plan_list", "inbox"):
            with CaptureQueriesContext(connection) as captured_queries:
                response = client.get(reverse(route_name))
                assert response.status_code == 200
            counts.append(len(captured_queries))
        return tuple(counts)

    add_visible_rows(0, 5)
    five_row_counts = page_query_counts()
    add_visible_rows(5, 50)
    fifty_row_counts = page_query_counts()

    assert five_row_counts == fifty_row_counts


def test_subscription_identifier_constraints_and_access_helper():
    first_user = create_test_user()
    second_user = create_test_user()
    third_user = create_test_user()
    future = timezone.now() + timezone.timedelta(days=1)

    subscription = PlatformSubscription.objects.create(
        user=first_user,
        stripe_customer_id="cus_test_unique",
        stripe_subscription_id="sub_test_unique",
        stripe_status="active",
        access_until=future,
    )
    assert subscription.has_premium_access()

    subscription.stripe_status = "cancelled"
    assert not subscription.has_premium_access()
    subscription.stripe_status = "trialing"
    subscription.access_until = timezone.now() - timezone.timedelta(seconds=1)
    assert not subscription.has_premium_access()

    with pytest.raises(IntegrityError), transaction.atomic():
        PlatformSubscription.objects.create(
            user=second_user,
            stripe_customer_id="cus_test_unique",
        )
    with pytest.raises(IntegrityError), transaction.atomic():
        PlatformSubscription.objects.create(
            user=second_user,
            stripe_subscription_id="sub_test_unique",
        )
    with pytest.raises(IntegrityError), transaction.atomic():
        PlatformSubscription.objects.create(
            user=first_user,
            stripe_customer_id="cus_test_other",
            stripe_subscription_id="sub_test_other",
        )

    PlatformSubscription.objects.create(user=second_user)
    PlatformSubscription.objects.create(user=third_user)


def test_webhook_event_identifier_constraint():
    values = {
        "stripe_event_id": "evt_test_unique",
        "event_type": "customer.subscription.updated",
        "provider_created_at": timezone.now(),
    }
    StripeWebhookReceipt.objects.create(**values)

    with pytest.raises(IntegrityError), transaction.atomic():
        StripeWebhookReceipt.objects.create(**values)


def test_mapped_non_unique_indexes_exist():
    expected_indexes = {
        Profile._meta.db_table: {"profile_verified_area_idx"},
        Plan._meta.db_table: {"plan_status_starts_idx"},
        Participation._meta.db_table: {
            "particip_plan_status_idx",
            "particip_user_status_idx",
        },
        Conversation._meta.db_table: {
            "conv_first_updated_idx",
            "conv_second_updated_idx",
        },
        Message._meta.db_table: {"message_convo_sent_idx"},
        Report._meta.db_table: {"report_status_received_idx"},
    }

    with connection.cursor() as cursor:
        for table_name, expected_names in expected_indexes.items():
            constraints = connection.introspection.get_constraints(cursor, table_name)
            actual_names = {
                name
                for name, details in constraints.items()
                if details["index"] and not details["unique"]
            }
            assert expected_names <= actual_names


def test_foreign_key_deletion_contracts_are_explicit():
    assert Profile._meta.get_field("user").remote_field.on_delete is models.CASCADE
    assert Profile._meta.get_field("verified_by").remote_field.on_delete is models.PROTECT
    assert Plan._meta.get_field("owner").remote_field.on_delete is models.PROTECT
    assert Plan._meta.get_field("approved_by").remote_field.on_delete is models.PROTECT
    assert Participation._meta.get_field("plan").remote_field.on_delete is models.PROTECT
    assert Participation._meta.get_field("user").remote_field.on_delete is models.PROTECT
    assert Conversation._meta.get_field("first_user").remote_field.on_delete is models.PROTECT
    assert Conversation._meta.get_field("second_user").remote_field.on_delete is models.PROTECT
    assert Message._meta.get_field("conversation").remote_field.on_delete is models.PROTECT
    assert Message._meta.get_field("sender").remote_field.on_delete is models.PROTECT
    assert Block._meta.get_field("blocker").remote_field.on_delete is models.CASCADE
    assert Block._meta.get_field("blocked_user").remote_field.on_delete is models.CASCADE
    assert Report._meta.get_field("reporter").remote_field.on_delete is models.PROTECT
    assert Report._meta.get_field("reported_user").remote_field.on_delete is models.PROTECT
    assert Report._meta.get_field("reported_plan").remote_field.on_delete is models.PROTECT
    assert Report._meta.get_field("reported_conversation").remote_field.on_delete is models.PROTECT
    assert Report._meta.get_field("reported_message").remote_field.on_delete is models.PROTECT
    assert PlatformSubscription._meta.get_field("user").remote_field.on_delete is models.PROTECT
