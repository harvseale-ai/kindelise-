"""Expose ordinary staff screens and the mapped review controls."""

# KEYWORD: decorator — a line beginning with @ that adds a rule to the function or class below it.
# KEYWORD: staff action — a task a permitted staff member can run on selected saved records.


from django import forms
from django.conf import settings
from django.contrib import admin, messages
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.forms import UserChangeForm
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import HttpResponseRedirect
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


# WHY: Keeps the profile is complete for verification steps in one named place so they can be understood, checked, and reused.
def _profile_is_complete_for_verification(profile):
    # WHY: Verification requires a real profile, a visible name, and at least one permitted broad area.
    return (
        profile is not None
        and bool(profile.display_name.strip())
        and bool(
            set(profile.broad_areas or (profile.broad_area,)).intersection(
                settings.KINDLELISE_AREAS
            )
        )
    )


# WHY: Keeps the set profile verification steps in one named place so they can be understood, checked, and reused.
def _set_profile_verification(profile, staff_user, should_verify):
    """Set one profile's internally consistent staff-verification state."""
    # WHY: Keeps granting and withdrawing verification as two explicit paths with matching saved fields.
    if should_verify:
        # WHY: Prevents staff granting product access to a profile that visitors could not understand or discover.
        if not _profile_is_complete_for_verification(profile):
            raise ValueError("Complete the profile before verifying it.")
        # WHY: Avoids rewriting the reviewer and time when the requested state is already saved.
        if profile.is_verified:
            return False
        profile.is_verified = True
        profile.verified_at = timezone.now()
        profile.verified_by = staff_user
    else:
        # WHY: Avoids an unnecessary database write when verification is already absent.
        if not profile.is_verified:
            return False
        profile.is_verified = False
        profile.verified_at = None
        profile.verified_by = None
    # WHY: Writes only the three verification fields so unrelated profile edits remain untouched.
    profile.save(update_fields=["is_verified", "verified_at", "verified_by"])
    return True


# WHY: Keeps the UserProfileVerificationForm information and its rules together so they stay consistent.
class _UserProfileVerificationForm(UserChangeForm):
    # WHY: Places the related profile decision beside Django's existing account permissions.
    profile_verified = forms.BooleanField(
        required=False,
        label="Profile verified",
        help_text=(
            "Allows discovery, plans and messages after the profile has a "
            "display name and configured broad area."
        ),
    )

    # WHY: Prepares this object with the values it needs before any other step uses it.
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # WHY: Shows the currently saved profile state when staff open the account form.
        profile = Profile.objects.filter(user=self.instance).first()
        self.fields["profile_verified"].initial = bool(
            profile and profile.is_verified
        )

    # WHY: Checks and tidies the profile verified value before the site trusts or saves it.
    def clean_profile_verified(self):
        # WHY: Reads the staff member's checkbox choice only after Django has cleaned the form value.
        should_verify = self.cleaned_data["profile_verified"]
        # WHY: Looks up the account's related profile rather than trusting a browser-supplied profile identity.
        profile = Profile.objects.filter(user=self.instance).first()
        if should_verify and not _profile_is_complete_for_verification(profile):
            raise forms.ValidationError(
                "Complete the profile display name and broad area first."
            )
        return should_verify


# WHY: Keeps the KindleliseUserAdmin information and its rules together so they stay consistent.
class KindleliseUserAdmin(DjangoUserAdmin):
    """Add related-profile verification to Django's User Permissions section."""

    # WHY: Reuses Django's account editor while adding only the mapped profile-verification field.
    form = _UserProfileVerificationForm

    # WHY: Keeps the extra checkbox inside User Permissions, where staff expect access decisions.
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

    # WHY: Finds the fieldsets information in one place so callers receive the same result.
    def get_fieldsets(self, request, obj=None):
        """Hide profile verification without Kindelise Profile change access."""
        # WHY: Begins with Django's normal account layout so built-in account controls are preserved.
        fieldsets = super().get_fieldsets(request, obj)

        # WHY: New accounts and staff with profile permission may see the added verification choice.
        if obj is None or request.user.has_perm("kindlelise.change_profile"):
            return fieldsets

        # WHY: Removes only the profile checkbox when staff may edit accounts but not profiles.
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

    # WHY: Keeps the save model steps in one named place so they can be understood, checked, and reused.
    @transaction.atomic
    def save_model(self, request, obj, form, change):
        """Save Django User fields and the authorised related verification state."""
        # WHY: Changes profile verification only when the field was shown and the staff member still has permission.
        should_update_profile = (
            "profile_verified" in form.cleaned_data
            and request.user.has_perm("kindlelise.change_profile")
        )
        profile = None
        if should_update_profile:
            # WHY: Locks the related profile so two staff changes cannot overwrite each other's verification decision.
            profile = Profile.objects.select_for_update().filter(user=obj).first()
            if form.cleaned_data["profile_verified"] and not (
                _profile_is_complete_for_verification(profile)
            ):
                raise PermissionDenied("A complete profile is required")

        # WHY: Lets Django save the normal account fields before applying the related profile state.
        super().save_model(request, obj, form, change)
        if should_update_profile and profile is not None:
            _set_profile_verification(
                profile,
                request.user,
                form.cleaned_data["profile_verified"],
            )


# WHY: Keeps the require authorized staff steps in one named place so they can be understood, checked, and reused.
def _require_authorized_staff(model_admin, request):
    """Refuse action calls outside Django Admin's normal change permission."""
    # WHY: Handles even an unusual request without a user value as unauthorised.
    user = getattr(request, "user", None)

    # WHY: Requires sign-in, an active staff account, and the exact change permission for this staff screen.
    if (
        not getattr(user, "is_authenticated", False)
        or not user.is_active
        or not user.is_staff
        or not model_admin.has_change_permission(request)
    ):
        raise PermissionDenied("Staff change permission is required")


# WHY: Keeps the selected primary keys steps in one named place so they can be understood, checked, and reused.
def _selected_primary_keys(records):
    """Return each selected primary key once before rows are rechecked."""
    # WHY: Removes duplicate selections before locked rows are fetched and counted.
    return tuple(dict.fromkeys(records.values_list("pk", flat=True)))


# WHY: Keeps the verify selected profiles for discovery plans and messages steps in one named place so they can be understood, checked, and reused.
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
    # WHY: Rechecks staff permission inside the action instead of relying only on the visible Admin button.
    _require_authorized_staff(model_admin, request)

    # WHY: Freezes the intended selection before current rows are loaded and checked again.
    profile_ids = _selected_primary_keys(profiles)
    changed = 0

    # WHY: Keeps all verification changes together if one database write unexpectedly fails.
    with transaction.atomic():
        # WHY: Locks current profiles so eligibility cannot change between the check and the save.
        current_profiles = Profile.objects.select_for_update().filter(
            pk__in=profile_ids
        )
        for profile in current_profiles:
            # WHY: Skips existing verification and incomplete profiles without altering them.
            if profile.is_verified or not _profile_is_complete_for_verification(
                profile
            ):
                continue
            _set_profile_verification(profile, request.user, True)
            changed += 1
    # WHY: Reports both outcomes so staff know some selected records may have been left unchanged.
    skipped = len(profile_ids) - changed
    model_admin.message_user(
        request,
        f"Verified {changed} profile(s); skipped {skipped}.",
    )


# WHY: Removes verification from selected profiles in a deliberate, repeatable way.
@admin.action(description="Remove current profile verification")
def remove_verification_from_selected_profiles(model_admin, request, profiles):
    """Recheck and withdraw only current verification from each selected profile.

    Inputs: the Profile admin, authorised staff request and selected profiles.
    Returns: none; the admin message reports changed and skipped counts.
    Changes: clears current verification, reviewer and verification time.
    Refuses: unauthorised staff and skips profiles already unverified.
    Privacy: preserves every profile and existing social record.
    """
    # WHY: Applies the same permission, selection, locking, and clear result count as the granting action.
    _require_authorized_staff(model_admin, request)
    profile_ids = _selected_primary_keys(profiles)
    changed = 0
    with transaction.atomic():
        # WHY: Locks current profiles so a simultaneous staff change cannot be lost.
        current_profiles = Profile.objects.select_for_update().filter(
            pk__in=profile_ids
        )
        for profile in current_profiles:
            # WHY: Leaves already-unverified profiles untouched and counts them as skipped.
            if not profile.is_verified:
                continue
            _set_profile_verification(profile, request.user, False)
            changed += 1
    skipped = len(profile_ids) - changed
    model_admin.message_user(
        request,
        f"Removed verification from {changed} profile(s); skipped {skipped}.",
    )


# WHY: Keeps the approve selected plans after manual url check steps in one named place so they can be understood, checked, and reused.
@admin.action(description="Approve eligible plans after manual URL check")
def approve_selected_plans_after_manual_url_check(model_admin, request, plans):
    """Recheck and approve only pending, future, unlocked manually checked plans.

    Inputs: the Plan admin, authorised staff request and manually checked plans.
    Returns: none; the admin message reports changed and skipped counts.
    Changes: records approved status, responsible staff account and review time.
    Refuses: unauthorised staff and skips non-pending, past, locked or invalid plans.
    Privacy: stores no webpage copy, private note or venue-safety claim.
    """
    # WHY: Requires plan-change permission again even if someone submits the action address directly.
    _require_authorized_staff(model_admin, request)
    plan_ids = _selected_primary_keys(plans)
    changed = 0

    # WHY: Uses one time for every plan in this staff action so their review record is consistent.
    approved_at = timezone.now()
    with transaction.atomic():
        # WHY: Locks the current plans while eligibility and approval are decided.
        current_plans = Plan.objects.select_for_update().filter(pk__in=plan_ids)
        for plan in current_plans:
            # WHY: Approves only pending future plans whose public details remain editable and complete.
            is_eligible = (
                plan.status == Plan.Status.PENDING
                and plan.starts_at > approved_at
                and plan.meeting_details_locked_at is None
                and bool(plan.public_place.strip())
                and plan.public_url.lower().startswith("https://")
            )
            if not is_eligible:
                continue
            # WHY: Stores who approved the plan and when instead of keeping an unexplained status alone.
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


# WHY: Keeps the reject selected plans steps in one named place so they can be understood, checked, and reused.
@admin.action(description="Reject eligible pending plans")
def reject_selected_plans(model_admin, request, plans):
    """Recheck and reject only pending, unlocked plans without private notes.

    Inputs: the Plan admin, authorised staff request and selected plans.
    Returns: none; the admin message reports changed and skipped counts.
    Changes: records rejected status with null approval reviewer and time.
    Refuses: unauthorised staff and skips non-pending or locked plans.
    Privacy: stores no finding, private staff note or venue-safety claim.
    """
    # WHY: Uses the same direct permission check and locked re-read as every other staff action.
    _require_authorized_staff(model_admin, request)
    plan_ids = _selected_primary_keys(plans)
    changed = 0
    with transaction.atomic():
        # WHY: Reloads selected plans under a lock rather than trusting an older staff-list result.
        current_plans = Plan.objects.select_for_update().filter(pk__in=plan_ids)
        for plan in current_plans:
            # WHY: Refuses rejection after a plan left the pending state or its meeting details were locked.
            if (
                plan.status != Plan.Status.PENDING
                or plan.meeting_details_locked_at is not None
            ):
                continue
            # WHY: Clears approval details because a rejected plan must not retain an approver or approval time.
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


# WHY: Keeps the ProfileAdmin information and its rules together so they stay consistent.
@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    """Expose profiles while keeping verification changes in mapped actions."""

    # WHY: Adds the single-profile Yes button while retaining Django's ordinary staff form.
    change_form_template = "admin/kindlelise/profile/change_form.html"
    actions = (
        verify_selected_profiles_for_discovery_plans_and_messages,
        remove_verification_from_selected_profiles,
    )
    # WHY: Forces verification changes through the checked buttons instead of free-form field editing.
    readonly_fields = ("is_verified", "verified_at", "verified_by")

    # WHY: Keeps uploaded image handling on the user-facing form rather than exposing storage details to staff.
    exclude = ("profile_image",)

    # WHY: Keeps the response change steps in one named place so they can be understood, checked, and reused.
    def response_change(self, request, obj):
        """Handle the explicit one-profile verification button."""
        # WHY: Lets every normal Admin save action continue through Django unchanged.
        if "_verify_profile" not in request.POST:
            return super().response_change(request, obj)

        # WHY: Rechecks permission and current profile data when the special Yes button is used.
        _require_authorized_staff(self, request)
        with transaction.atomic():
            # WHY: Locks the exact profile so its completion and verification cannot change mid-action.
            profile = Profile.objects.select_for_update().get(pk=obj.pk)
            if not _profile_is_complete_for_verification(profile):
                self.message_user(
                    request,
                    "Complete the profile display name and broad area first.",
                    level=messages.ERROR,
                )
            elif _set_profile_verification(profile, request.user, True):
                self.message_user(request, "Profile verified.", level=messages.SUCCESS)
        # WHY: Reloads the same staff page so the saved verification state and notice are immediately visible.
        return HttpResponseRedirect(".")


# WHY: Keeps the PlanAdmin information and its rules together so they stay consistent.
@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    """Expose plans while keeping review changes in mapped actions."""

    # WHY: Limits plan state changes to the two reviewed actions defined above.
    actions = (
        approve_selected_plans_after_manual_url_check,
        reject_selected_plans,
    )
    # WHY: Prevents staff bypassing the action checks by typing status or reviewer values directly.
    readonly_fields = (
        "status",
        "approved_at",
        "approved_by",
        "meeting_details_locked_at",
    )


# WHY: Keeps the ReportAdmin information and its rules together so they stay consistent.
@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    """Let staff review private reports without rewriting their statement."""

    # WHY: Preserves the reporter's original private statement and its recorded context during staff review.
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


# WHY: Keeps the PlatformSubscriptionAdmin information and its rules together so they stay consistent.
@admin.register(PlatformSubscription)
class PlatformSubscriptionAdmin(admin.ModelAdmin):
    """Expose the webhook-owned subscription projection as read-only state."""

    # WHY: Makes Stripe-owned subscription facts visible for support without allowing manual access grants.
    readonly_fields = (
        "user",
        "stripe_customer_id",
        "stripe_subscription_id",
        "stripe_status",
        "access_until",
        "latest_provider_event_at",
        "updated_at",
    )


# WHY: Keeps the StripeWebhookReceiptAdmin information and its rules together so they stay consistent.
@admin.register(StripeWebhookReceipt)
class StripeWebhookReceiptAdmin(admin.ModelAdmin):
    """Expose immutable webhook receipt identity and processing state read-only."""

    # WHY: Preserves the evidence that each signed Stripe notice was handled only once.
    readonly_fields = (
        "stripe_event_id",
        "event_type",
        "provider_created_at",
        "processed_at",
    )


# WHY: Gives staff ordinary read-and-change screens for records that need no custom staff workflow.
admin.site.register((Interest, Participation, Conversation, Message, Block))

# WHY: Replaces Django's standard account screen with the small verification-aware version above.
admin.site.unregister(get_user_model())
admin.site.register(get_user_model(), KindleliseUserAdmin)
