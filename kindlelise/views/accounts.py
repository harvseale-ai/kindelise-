"""Account entry, profile ownership, images, and notification pages."""

# WHY: This module keeps the pages about the signed-in person's own account together.
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError
from django.http import FileResponse, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from kindlelise.forms import AccountSignUpForm, ProfileDetailsForm
from kindlelise.policies import can_access_discovery_plans_and_messages
from kindlelise.selectors import (
    get_profile_image_if_viewer_is_allowed,
    get_recent_notifications,
    get_signed_in_user_account_summary,
)
from kindlelise.services.accounts import (
    create_account_and_profile,
    mark_all_notifications_read,
    update_signed_in_user_profile,
)
from kindlelise.views.common import _profile_broad_area_label, _safe_local_redirect

# =============================================================================
# ENTRY AND HELP PAGES
# Directs visitors to the right starting page and provides the public guide.
# =============================================================================

# WHY: Keeps the home page steps in one named place so they can be understood, checked, and reused.
@require_http_methods(["GET"])
def home_page(request):
    """Redirect the visitor to the page allowed by current account state.

    Inputs: the current Django request and its server-authenticated account.
    Returns: a redirect to sign-in, the private account or discovery.
    Changes: none.
    Refuses: missing authentication or verification by choosing the safer page.
    Privacy: returns no profile or account details.
    """
    # WHY: Sends each visitor straight to the safest useful starting point for their current account state.
    if not request.user.is_authenticated:
        return redirect("sign_in")
    if can_access_discovery_plans_and_messages(request.user):
        return redirect("discover")
    return redirect("account")

# WHY: Keeps the app guide page steps in one named place so they can be understood, checked, and reused.
@require_GET
def app_guide_page(request):
    """Show the compact public guide to the implemented Kindelise journey."""
    # WHY: The guide is public and needs no private account information.
    return render(request, "guide.html")


# =============================================================================
# NOTIFICATIONS
# Shows the signed-in person's activity and records when it has been read.
# =============================================================================

# WHY: Keeps the notifications page steps in one named place so they can be understood, checked, and reused.
@require_GET
@login_required
def notifications_page(request):
    """Show only the signed-in account's recent message and plan-join alerts."""
    # WHY: Supplies only alerts selected for the signed-in recipient.
    return render(
        request,
        "notifications.html",
        {"notifications": get_recent_notifications(request.user)},
    )

# WHY: Records notifications read so the page can show the visitor's latest state.
@require_POST
@login_required
def mark_notifications_read(request):
    """Mark the signed-in account's alerts read and return to its notification page."""
    # WHY: Changes only this recipient's rows, then reloads the notification list to show the new state.
    mark_all_notifications_read(request.user)
    return redirect("notifications")


# =============================================================================
# ACCOUNT ACCESS
# Handles account creation, sign-in, and sign-out pages.
# =============================================================================

# WHY: Keeps the sign up page steps in one named place so they can be understood, checked, and reused.
@require_http_methods(["GET", "POST"])
def sign_up_page(request):
    """Create one account/profile pair from a valid registration form.

    Inputs: anonymous GET or POST registration input.
    Returns: the registration page or a redirect to the named sign-in route.
    Changes: calls the atomic account/profile service exactly once when valid.
    Refuses: authenticated callers and invalid or raced duplicate input safely.
    Privacy: never authenticates the new account or exposes password values.
    """
    # WHY: A signed-in visitor already has an account and should not create another through this session.
    if request.user.is_authenticated:
        return redirect("home")

    # WHY: Binds submitted values only for POST; GET receives a clean empty form.
    form = AccountSignUpForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        # WHY: Handles a simultaneous duplicate registration without exposing whether an account already existed.
        try:
            create_account_and_profile(form.cleaned_data)
        except IntegrityError:
            form.add_error("email", "An account already uses this email address.")
        else:
            # WHY: Requires the new account to sign in explicitly instead of silently starting a session.
            messages.success(request, "Account created. Sign in to continue.")
            return redirect("sign_in")

    return render(request, "account.html", {"mode": "sign_up", "form": form})

# WHY: Keeps the sign in page steps in one named place so they can be understood, checked, and reused.
@require_http_methods(["GET", "POST"])
def sign_in_page(request):
    """Authenticate one account and follow only a safe local destination.

    Inputs: anonymous GET or POST email/password input and optional next value.
    Returns: the sign-in page or a redirect after Django starts the session.
    Changes: rotates and authenticates the session after valid credentials.
    Refuses: invalid and inactive accounts with the same generic feedback.
    Privacy: never reveals whether an email exists and never logs credentials.
    """
    # WHY: A signed-in visitor needs the normal home decision rather than another sign-in form.
    if request.user.is_authenticated:
        return redirect("home")

    # WHY: Copies submitted data so the email can be normalised without changing Django's request object.
    form_data = request.POST.copy() if request.method == "POST" else None
    if form_data is not None:
        form_data["username"] = form_data.get("username", "").strip().lower()
    # WHY: Reuses Django's password and inactive-account checks rather than implementing authentication here.
    form = AuthenticationForm(
        request=request,
        data=form_data,
    )
    form.fields["username"].label = "Email"
    form.fields["username"].widget.input_type = "email"
    form.fields["username"].widget.attrs.update(
        {
            "autocomplete": "email",
            "autocapitalize": "none",
            "spellcheck": "false",
        }
    )
    # WHY: Uses the same response for a missing account, wrong password, or inactive account.
    generic_error = "The email address or password was not accepted."
    form.error_messages["invalid_login"] = generic_error
    form.error_messages["inactive"] = generic_error
    # WHY: Checks the optional next address before a successful sign-in may follow it.
    destination = _safe_local_redirect(request)

    if request.method == "POST" and form.is_valid():
        # WHY: Lets Django rotate and authenticate the session only after the complete form succeeds.
        login(request, form.get_user())
        return redirect(destination or reverse("home"))

    return render(
        request,
        "account.html",
        {"mode": "sign_in", "form": form, "next": destination or ""},
    )

# WHY: Keeps the sign out user steps in one named place so they can be understood, checked, and reused.
@require_POST
@login_required
def sign_out_user(request):
    """End the signed-in account's Django session through POST only.

    Inputs: a signed-in, CSRF-validated POST request.
    Returns: a redirect to the named sign-in route.
    Changes: flushes the current Django session.
    Refuses: anonymous, non-POST or invalid-CSRF requests through Django controls.
    Privacy: returns no session identifier.
    """
    # WHY: Flushes the server-owned session before showing confirmation and returning to sign-in.
    logout(request)
    messages.success(request, "You have signed out.")
    return redirect("sign_in")


# =============================================================================
# PRIVATE PROFILE
# Displays and updates the profile owned by the signed-in person.
# =============================================================================

# WHY: Keeps the account page steps in one named place so they can be understood, checked, and reused.
@require_http_methods(["GET"])
@login_required
def account_page(request):
    """Show only the signed-in account's private profile summary.

    Inputs: the server-authenticated account; no account identifier is accepted.
    Returns: the private account page or a generic unavailable response.
    Changes: none.
    Refuses: anonymous callers through Django and missing/inactive profiles safely.
    Privacy: uses the authorised selector and exposes no reports or provider IDs.
    """
    # WHY: Turns Stripe's server-chosen return marker into the existing pop-out message, then removes it from the address.
    payment_result = request.GET.get("premium_payment")
    if payment_result == "success":
        messages.success(request, "Payment successful. Premium access will update shortly.")
        return redirect("account")
    if payment_result == "cancelled":
        messages.error(request, "Payment cancelled. No charge was made.")
        return redirect("account")

    # WHY: Uses an owner-only selector rather than accepting an account or profile ID from the address.
    summary = get_signed_in_user_account_summary(request.user)
    if summary is None:
        return HttpResponse("Account unavailable.", status=403)

    # WHY: Adds only presentation labels and a current yes-or-no availability result to the authorised summary.
    return render(
        request,
        "account.html",
        {
            "mode": "account",
            "summary": summary,
            "broad_area_label": _profile_broad_area_label(summary["profile"]),
            "is_available_now": summary["profile"].is_available_now(timezone.now()),
        },
    )

# WHY: Keeps the edit profile page steps in one named place so they can be understood, checked, and reused.
@require_http_methods(["GET", "POST"])
@login_required
def edit_profile_page(request):
    """Validate and save only the signed-in account's editable profile fields.

    Inputs: the server-authenticated account and untrusted profile form values.
    Returns: the bound edit page or a redirect to the private account page.
    Changes: calls the mapped profile service after successful validation.
    Refuses: missing/inactive profiles and invalid input without partial changes.
    Privacy: never binds ownership, verification or subscription fields.
    """
    # WHY: Confirms this active account still owns a profile before building or accepting an edit form.
    summary = get_signed_in_user_account_summary(request.user)
    if summary is None:
        return HttpResponse("Profile unavailable.", status=403)

    profile = summary["profile"]

    # WHY: Binds text and files only on POST and ties every edit to the server-selected owner profile.
    form = ProfileDetailsForm(
        request.POST if request.method == "POST" else None,
        request.FILES if request.method == "POST" else None,
        instance=profile,
    )
    if request.method == "POST" and form.is_valid():
        # WHY: Keeps a last permission refusal on the same form without partially saving the profile.
        try:
            update_signed_in_user_profile(request.user, form.cleaned_data)
        except PermissionDenied:
            form.add_error(None, "Your profile could not be updated.")
        else:
            messages.success(request, "Profile updated.")
            return redirect("account")

    return render(
        request,
        "account.html",
        {"mode": "profile_edit", "form": form, "profile": profile},
    )


# =============================================================================
# PROTECTED PROFILE IMAGE
# Streams a stored profile picture only after the viewer has been checked.
# =============================================================================

# WHY: Keeps the profile image file steps in one named place so they can be understood, checked, and reused.
@require_GET
@login_required
def profile_image_file(request, profile_id):
    """Stream one profile image only after current profile authorisation.

    Inputs: a signed-in GET request and an untrusted profile route identifier.
    Returns: the stored image or one generic not-found response.
    Changes: none.
    Refuses: missing files and anonymous, inactive or disallowed viewers.
    Privacy: exposes neither the storage path nor the reason for refusal.
    """
    # WHY: Loads the image reader only on this media route, where the stored bytes must be checked again.
    from PIL import Image, UnidentifiedImageError

    # WHY: Uses one authorised selector so missing files and refused viewers share the same response.
    profile = get_profile_image_if_viewer_is_allowed(request.user, profile_id)
    if profile is None:
        return HttpResponse("Profile image unavailable.", status=404)
    # WHY: Opens the stored bytes and reads their real format rather than trusting a filename ending.
    try:
        image_file = profile.profile_image.open("rb")
        with Image.open(image_file) as stored_image:
            image_format = stored_image.format
        image_file.seek(0)
    except (FileNotFoundError, OSError, UnidentifiedImageError):
        return HttpResponse("Profile image unavailable.", status=404)
    # WHY: Serves only the three formats accepted and rewritten by the profile form.
    content_types = {
        "JPEG": ("jpg", "image/jpeg"),
        "PNG": ("png", "image/png"),
        "WEBP": ("webp", "image/webp"),
    }
    suffix, content_type = content_types.get(image_format, (None, None))
    # WHY: Closes the file before refusing an unexpected stored format.
    if content_type is None:
        image_file.close()
        return HttpResponse("Profile image unavailable.", status=404)
    # WHY: Streams the authorised image without revealing its private storage path.
    return FileResponse(
        image_file,
        content_type=content_type,
        filename=f"profile-image.{suffix}",
    )
