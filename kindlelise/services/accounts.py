"""Account, profile, and notification state-changing workflows."""

# WHY: Keeps changes belonging to the signed-in person's own account together.
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.utils import timezone

from kindlelise.models import Notification, Profile


# KEYWORD: atomic — either every database change in the function succeeds, or none of them are kept.
# WHY: Keeps account and profile creation together so an account is never left without its matching profile.
@transaction.atomic
def create_account_and_profile(new_account_details):
    """Create one Django account and its empty unverified profile atomically.

    Inputs: validated AccountSignUpForm values containing email and password1.
    Returns: the newly created Django account.
    Changes: creates one account and exactly one empty unverified profile.
    Refuses: invalid or duplicate values through normal Django database errors.
    Privacy: hashes the password through Django and ignores every extra field.
    """
    # WHY: Uses only values already cleaned by the sign-up form and ignores every extra submitted key.
    email = new_account_details["email"]

    # WHY: Lets Django hash the password and apply account defaults rather than saving password text directly.
    account = get_user_model().objects.create_user(
        username=email,
        email=email,
        password=new_account_details["password1"],
    )
    # WHY: Creates the required empty, unverified profile in the same transaction as the account.
    Profile.objects.create(user=account)
    # WHY: Gives the sign-up page the saved account it needs to start the new signed-in session.
    return account

# WHY: Rolls every profile edit back together if saving a field or its linked interests fails.
@transaction.atomic
def update_signed_in_user_profile(user, profile_changes):
    """Update only the signed-in account's permitted profile fields.

    Inputs: the server-known account and validated ProfileDetailsForm values.
    Returns: the updated profile.
    Changes: replaces supplied public profile fields, interests and availability.
    Refuses: anonymous, inactive or missing-profile accounts.
    Privacy: ignores verification, subscription, ownership and every extra field.
    """
    # WHY: Refuses before loading any profile when the caller is anonymous or inactive.
    if not getattr(user, "is_authenticated", False) or not user.is_active:
        raise PermissionDenied("A signed-in active account is required")

    # WHY: Locks the owner's current profile so two edits cannot silently overwrite each other.
    try:
        profile = Profile.objects.select_for_update().get(user=user)
    except Profile.DoesNotExist as error:
        # WHY: Hides the database detail and gives every caller the same safe refusal.
        raise PermissionDenied("A profile is required") from error

    # WHY: Lists the only ordinary profile values this workflow is allowed to change.
    scalar_fields = (
        "display_name",
        "title_statement",
        "biography",
        "broad_area",
        "broad_areas",
        "availability_start",
        "available_from",
    )
    # WHY: Builds the exact list Django should write instead of rewriting the whole profile row.
    changed_fields = []

    # WHY: Remembers the old stored image so it can be removed only after the new database value succeeds.
    old_image_name = profile.profile_image.name
    new_image = profile_changes.get("profile_image")
    # WHY: Replaces the image only when the validated form supplied a genuinely different file.
    if new_image and getattr(new_image, "name", "") != old_image_name:
        profile.profile_image = new_image
        changed_fields.append("profile_image")
    # WHY: Copies only named allowed fields that the validated form actually supplied.
    for field_name in scalar_fields:
        if field_name in profile_changes:
            setattr(profile, field_name, profile_changes[field_name])
            changed_fields.append(field_name)

    # WHY: Avoids an unnecessary save when no ordinary field changed.
    if changed_fields:
        profile.save(update_fields=changed_fields)
        if old_image_name and "profile_image" in changed_fields:
            image_storage = profile.profile_image.storage
            # WHY: Deletes the old media file only after the database commits, so a failed update keeps usable media.
            transaction.on_commit(
                lambda storage=image_storage, name=old_image_name: storage.delete(name)
            )
    # WHY: Replaces interest links only when the form included them, preserving them in partial updates.
    if "interests" in profile_changes:
        profile.interests.set(profile_changes["interests"])
    # WHY: Returns the same refreshed profile object so the page does not need a second database lookup.
    return profile

# WHY: Records all notifications read so the page can show the visitor's latest state.
def mark_all_notifications_read(user):
    """Mark only the signed-in recipient's unread alerts as read."""
    # WHY: Prevents anonymous or inactive callers changing any notification rows.
    if not getattr(user, "is_authenticated", False) or not user.is_active:
        raise PermissionDenied("A signed-in active account is required")
    # WHY: Updates only this recipient's currently unread rows in one database operation.
    # WHY: Returning Django's count lets the caller know how many alerts actually changed.
    return Notification.objects.filter(recipient=user, read_at__isnull=True).update(
        read_at=timezone.now()
    )
