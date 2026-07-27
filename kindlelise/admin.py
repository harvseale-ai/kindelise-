"""Expose ordinary staff screens and the mapped review controls."""

from django import forms
from django.conf import settings
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.forms import UserChangeForm
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.utils import timezone

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


def _profile_is_complete_for_verification(profile):
    return (
        profile is not None
        and bool(profile.display_name.strip())
        and profile.broad_area in settings.KINDLELISE_AREAS
    )


def _set_profile_verification(profile, staff_user, should_verify):
    """Set one profile's internally consistent staff-verification state."""
    if should_verify:
        if not _profile_is_complete_for_verification(profile):
            raise ValueError("Complete the profile before verifying it.")
        if profile.is_verified:
            return False
        profile.is_verified = True
        profile.verified_at = timezone.now()
        profile.verified_by = staff_user
    else:
        if not profile.is_verified:
            return False
        profile.is_verified = False
        profile.verified_at = None
        profile.verified_by = None
    profile.save(update_fields=["is_verified", "verified_at", "verified_by"])
    return True


class _UserProfileVerificationForm(UserChangeForm):
    profile_verified = forms.BooleanField(
        required=False,
        label="Profile verified",
        help_text=(
            "Allows discovery, plans and messages after the profile has a "
            "display name and configured broad area."
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        profile = Profile.objects.filter(user=self.instance).first()
        self.fields["profile_verified"].initial = bool(
            profile and profile.is_verified
        )

    def clean_profile_verified(self):
        should_verify = self.cleaned_data["profile_verified"]
        profile = Profile.objects.filter(user=self.instance).first()
        if should_verify and not _profile_is_complete_for_verification(profile):
            raise forms.ValidationError(
                "Complete the profile display name and broad area first."
            )
        return should_verify


class KindleliseUserAdmin(DjangoUserAdmin):
    """Add related-profile verification to Django's User Permissions section."""

    form = _UserProfileVerificationForm
    fieldsets = (
        DjangoUserAdmin.fieldsets[0],
        DjangoUserAdmin.fieldsets[1],
        (
            DjangoUserAdmin.fieldsets[2][0],
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "profile_verified",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        DjangoUserAdmin.fieldsets[3],
    )

    def get_fieldsets(self, request, obj=None):
        """Hide profile verification without Kindlelise Profile change access."""
        fieldsets = super().get_fieldsets(request, obj)
        if obj is None or request.user.has_perm("kindlelise.change_profile"):
            return fieldsets
        return tuple(
            (
                heading,
                {
                    **options,
                    "fields": tuple(
                        field_name
                        for field_name in options["fields"]
                        if field_name != "profile_verified"
                    ),
                },
            )
            for heading, options in fieldsets
        )

    @transaction.atomic
    def save_model(self, request, obj, form, change):
        """Save Django User fields and the authorised related verification state."""
        should_update_profile = (
            "profile_verified" in form.cleaned_data
            and request.user.has_perm("kindlelise.change_profile")
        )
        profile = None
        if should_update_profile:
            profile = Profile.objects.select_for_update().filter(user=obj).first()
            if form.cleaned_data["profile_verified"] and not (
                _profile_is_complete_for_verification(profile)
            ):
                raise PermissionDenied("A complete profile is required")

        super().save_model(request, obj, form, change)
        if should_update_profile and profile is not None:
            _set_profile_verification(
                profile,
                request.user,
                form.cleaned_data["profile_verified"],
            )


def _require_authorized_staff(model_admin, request):
    """Refuse action calls outside Django Admin's normal change permission."""
    user = getattr(request, "user", None)
    if (
        not getattr(user, "is_authenticated", False)
        or not user.is_active
        or not user.is_staff
        or not model_admin.has_change_permission(request)
    ):
        raise PermissionDenied("Staff change permission is required")


def _selected_primary_keys(records):
    """Return each selected primary key once before rows are rechecked."""
    return tuple(dict.fromkeys(records.values_list("pk", flat=True)))


@admin.action(description="Verify eligible profiles for social features")
def verify_selected_profiles_for_discovery_plans_and_messages(
    model_admin,
    request,
    profiles,
):
    """Recheck and verify each complete, configured, currently unverified profile.

    Inputs: the Profile admin, authorised staff request and selected profiles.
    Returns: none; the admin message reports changed and skipped counts.
    Changes: records current verification, responsible staff account and time.
    Refuses: unauthorised staff and skips incomplete or already verified profiles.
    Privacy: records no identity, age, character or safety claim.
    """
    _require_authorized_staff(model_admin, request)
    profile_ids = _selected_primary_keys(profiles)
    changed = 0
    with transaction.atomic():
        current_profiles = Profile.objects.select_for_update().filter(
            pk__in=profile_ids
        )
        for profile in current_profiles:
            if profile.is_verified or not _profile_is_complete_for_verification(
                profile
            ):
                continue
            _set_profile_verification(profile, request.user, True)
            changed += 1
    skipped = len(profile_ids) - changed
    model_admin.message_user(
        request,
        f"Verified {changed} profile(s); skipped {skipped}.",
    )


@admin.action(description="Remove current profile verification")
def remove_verification_from_selected_profiles(model_admin, request, profiles):
    """Recheck and withdraw only current verification from each selected profile.

    Inputs: the Profile admin, authorised staff request and selected profiles.
    Returns: none; the admin message reports changed and skipped counts.
    Changes: clears current verification, reviewer and verification time.
    Refuses: unauthorised staff and skips profiles already unverified.
    Privacy: preserves every profile and existing social record.
    """
    _require_authorized_staff(model_admin, request)
    profile_ids = _selected_primary_keys(profiles)
    changed = 0
    with transaction.atomic():
        current_profiles = Profile.objects.select_for_update().filter(
            pk__in=profile_ids
        )
        for profile in current_profiles:
            if not profile.is_verified:
                continue
            _set_profile_verification(profile, request.user, False)
            changed += 1
    skipped = len(profile_ids) - changed
    model_admin.message_user(
        request,
        f"Removed verification from {changed} profile(s); skipped {skipped}.",
    )


@admin.action(description="Approve eligible plans after manual URL check")
def approve_selected_plans_after_manual_url_check(model_admin, request, plans):
    """Recheck and approve only pending, future, unlocked manually checked plans.

    Inputs: the Plan admin, authorised staff request and manually checked plans.
    Returns: none; the admin message reports changed and skipped counts.
    Changes: records approved status, responsible staff account and review time.
    Refuses: unauthorised staff and skips non-pending, past, locked or invalid plans.
    Privacy: stores no webpage copy, private note or venue-safety claim.
    """
    _require_authorized_staff(model_admin, request)
    plan_ids = _selected_primary_keys(plans)
    changed = 0
    approved_at = timezone.now()
    with transaction.atomic():
        current_plans = Plan.objects.select_for_update().filter(pk__in=plan_ids)
        for plan in current_plans:
            is_eligible = (
                plan.status == Plan.Status.PENDING
                and plan.starts_at > approved_at
                and plan.meeting_details_locked_at is None
                and bool(plan.public_place.strip())
                and plan.public_url.lower().startswith("https://")
            )
            if not is_eligible:
                continue
            plan.status = Plan.Status.APPROVED
            plan.approved_at = approved_at
            plan.approved_by = request.user
            plan.save(update_fields=["status", "approved_at", "approved_by"])
            changed += 1
    skipped = len(plan_ids) - changed
    model_admin.message_user(
        request,
        f"Approved {changed} plan(s); skipped {skipped}.",
    )


@admin.action(description="Reject eligible pending plans")
def reject_selected_plans(model_admin, request, plans):
    """Recheck and reject only pending, unlocked plans without private notes.

    Inputs: the Plan admin, authorised staff request and selected plans.
    Returns: none; the admin message reports changed and skipped counts.
    Changes: records rejected status with null approval reviewer and time.
    Refuses: unauthorised staff and skips non-pending or locked plans.
    Privacy: stores no finding, private staff note or venue-safety claim.
    """
    _require_authorized_staff(model_admin, request)
    plan_ids = _selected_primary_keys(plans)
    changed = 0
    with transaction.atomic():
        current_plans = Plan.objects.select_for_update().filter(pk__in=plan_ids)
        for plan in current_plans:
            if (
                plan.status != Plan.Status.PENDING
                or plan.meeting_details_locked_at is not None
            ):
                continue
            plan.status = Plan.Status.REJECTED
            plan.approved_at = None
            plan.approved_by = None
            plan.save(update_fields=["status", "approved_at", "approved_by"])
            changed += 1
    skipped = len(plan_ids) - changed
    model_admin.message_user(
        request,
        f"Rejected {changed} plan(s); skipped {skipped}.",
    )


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    """Expose profiles while keeping verification changes in mapped actions."""

    actions = (
        verify_selected_profiles_for_discovery_plans_and_messages,
        remove_verification_from_selected_profiles,
    )
    readonly_fields = ("is_verified", "verified_at", "verified_by")


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    """Expose plans while keeping review changes in mapped actions."""

    actions = (
        approve_selected_plans_after_manual_url_check,
        reject_selected_plans,
    )
    readonly_fields = (
        "status",
        "approved_at",
        "approved_by",
        "meeting_details_locked_at",
    )


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    """Let staff review private reports without rewriting their statement."""

    readonly_fields = (
        "reporter",
        "reported_user",
        "category",
        "description",
        "reported_plan",
        "reported_conversation",
        "reported_message",
        "received_at",
    )


@admin.register(PlatformSubscription)
class PlatformSubscriptionAdmin(admin.ModelAdmin):
    """Expose the webhook-owned subscription projection as read-only state."""

    readonly_fields = (
        "user",
        "stripe_customer_id",
        "stripe_subscription_id",
        "stripe_status",
        "access_until",
        "latest_provider_event_at",
        "updated_at",
    )


@admin.register(StripeWebhookReceipt)
class StripeWebhookReceiptAdmin(admin.ModelAdmin):
    """Expose immutable webhook receipt identity and processing state read-only."""

    readonly_fields = (
        "stripe_event_id",
        "event_type",
        "provider_created_at",
        "processed_at",
    )


admin.site.register((Interest, Participation, Conversation, Message, Block))
admin.site.unregister(get_user_model())
admin.site.register(get_user_model(), KindleliseUserAdmin)
