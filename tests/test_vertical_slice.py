"""Prove the implemented Kindlelise vertical-slice behaviour."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from django.apps import apps
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied
from django.db import (
    IntegrityError,
    close_old_connections,
    connection,
    connections,
    models,
    transaction,
)
from django.test import TransactionTestCase
from django.utils import timezone
from django.utils.html import conditional_escape

from kindlelise.forms import (
    AccountSignUpForm,
    DiscoveryFiltersForm,
    MessageDraftForm,
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
    send_direct_message,
    submit_private_report_about_user,
    update_owned_plan_before_first_join,
    update_signed_in_user_profile,
)
from tests.conftest import (
    create_test_conversation,
    create_test_plan,
    create_test_user,
    create_verified_test_profile,
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


def test_account_sign_up_form_creates_unverified_profile_with_hashed_password():
    form = AccountSignUpForm(
        data={
            "username": "new_student",
            "password1": "Test-pass-742!",
            "password2": "Test-pass-742!",
            "email": "ignored@example.test",
        }
    )

    assert tuple(form.fields) == ("username", "password1", "password2")
    assert form.is_valid(), form.errors

    account = create_account_and_profile(form.cleaned_data)
    profile = account.profile

    assert account.username == "new_student"
    assert account.email == ""
    assert account.check_password("Test-pass-742!")
    assert account.password != "Test-pass-742!"
    assert authenticate(
        username="new_student",
        password="Test-pass-742!",
    ) == account
    assert (
        authenticate(
            email="ignored@example.test",
            password="Test-pass-742!",
        )
        is None
    )
    assert profile.display_name == ""
    assert profile.broad_area == ""
    assert not profile.is_verified


def test_duplicate_or_invalid_account_details_are_rejected_without_writes():
    create_test_user(username="existing_student")
    valid_password = "Test-pass-742!"

    duplicate_form = AccountSignUpForm(
        data={
            "username": "existing_student",
            "password1": valid_password,
            "password2": valid_password,
        }
    )
    invalid_username_form = AccountSignUpForm(
        data={
            "username": "invalid username",
            "password1": valid_password,
            "password2": valid_password,
        }
    )
    invalid_password_form = AccountSignUpForm(
        data={
            "username": "another_student",
            "password1": "12345678",
            "password2": "12345678",
        }
    )
    mismatched_password_form = AccountSignUpForm(
        data={
            "username": "mismatched_student",
            "password1": valid_password,
            "password2": "Different-pass-853!",
        }
    )

    assert not duplicate_form.is_valid()
    assert "username" in duplicate_form.errors
    assert not invalid_username_form.is_valid()
    assert "username" in invalid_username_form.errors
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
                "username": "rolled_back_student",
                "password1": "Test-pass-742!",
            }
        )

    assert not Profile.objects.filter(user__username="rolled_back_student").exists()
    assert not get_user_model().objects.filter(username="rolled_back_student").exists()


def test_profile_details_form_rejects_unknown_and_oversized_values():
    profile = Profile.objects.create(user=create_test_user())

    invalid_form = ProfileDetailsForm(
        data={
            "display_name": "   ",
            "biography": "x" * 501,
            "broad_area": "unconfigured-area",
            "available_until": "",
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
            "available_until": "",
            "interests": [],
        },
        instance=profile,
    )

    assert tuple(invalid_form.fields) == (
        "display_name",
        "biography",
        "broad_area",
        "available_until",
        "interests",
    )
    assert not invalid_form.is_valid()
    assert {"display_name", "biography", "broad_area", "interests"} <= set(
        invalid_form.errors
    )
    assert "is_verified" not in invalid_form.fields
    assert not oversized_name_form.is_valid()
    assert "display_name" in oversized_name_form.errors


def test_signed_in_user_profile_update_replaces_and_clears_permitted_values():
    account = create_test_user()
    previous_availability = timezone.now() + timezone.timedelta(minutes=30)
    profile = Profile.objects.create(
        user=account,
        available_until=previous_availability,
    )
    other_profile = Profile.objects.create(user=create_test_user())
    coffee = Interest.objects.get(name="Coffee")
    walking = Interest.objects.get(name="Walking")
    future = timezone.now() + timezone.timedelta(hours=2)
    first_form = ProfileDetailsForm(
        data={
            "display_name": "Student One",
            "biography": "A short synthetic biography.",
            "broad_area": "north",
            "available_until": future.strftime("%Y-%m-%d %H:%M:%S"),
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
    assert updated_profile.available_until is not None
    assert updated_profile.available_until != previous_availability
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
            "available_until": "",
            "interests": [],
        },
        instance=updated_profile,
    )
    assert clear_form.is_valid(), clear_form.errors
    update_signed_in_user_profile(account, clear_form.cleaned_data)
    updated_profile.refresh_from_db()

    assert updated_profile.available_until is None
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
        "available_until": None,
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


def test_account_summary_selector_returns_only_owners_safe_records():
    account = create_test_user(username="summary_owner")
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
    assert summary["account"] == {"username": "summary_owner"}
    assert summary["profile"] == profile
    assert list(summary["plans"]) == [own_plan]
    assert summary["subscription"] == {
        "has_premium_access": True,
        "status": "active",
        "access_until": future,
        "customer_portal_available": True,
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
        available_until=future,
    )
    expired = create_verified_test_profile(
        display_name="Expired",
        broad_area="central",
        available_until=past,
    )
    no_availability = create_verified_test_profile(
        display_name="No availability",
        broad_area="central",
    )
    wrong_interest = create_verified_test_profile(
        display_name="Wrong interest",
        broad_area="central",
        available_until=future,
    )
    wrong_area = create_verified_test_profile(
        display_name="Wrong area",
        broad_area="north",
        available_until=future,
    )
    unverified = Profile.objects.create(
        user=create_test_user(),
        display_name="Unverified",
        broad_area="central",
        available_until=future,
    )
    inactive = create_verified_test_profile(
        user=create_test_user(is_active=False),
        display_name="Inactive",
        broad_area="central",
        available_until=future,
    )
    blocked_by_viewer = create_verified_test_profile(
        display_name="Blocked by viewer",
        broad_area="central",
        available_until=future,
    )
    viewer_blocked_by = create_verified_test_profile(
        display_name="Viewer blocked by target",
        broad_area="central",
        available_until=future,
    )
    for profile in (
        eligible,
        expired,
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
        expired,
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

    assert list(get_unblocked_conversations_for_inbox(viewer)) == [newer, older]

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
    profile.available_until = future
    profile.save(update_fields=["available_until"])

    assert profile.is_available_now(timezone.now())
    assert not profile.is_available_now(future)

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
