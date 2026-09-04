"""Validate the seven mapped kinds of untrusted browser input."""

# KEYWORD: form — the rules for reading, checking, and cleaning information entered on a page.
# KEYWORD: widget — the visible input control used to collect one form value.
# KEYWORD: validation — checks that stop missing, unsafe, or unsuitable values before saving.


from datetime import datetime, time, timedelta
from io import BytesIO

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from PIL import Image, ImageOps

from kindlelise.models import Interest, Plan, Profile, Report
from kindlelise.plan_metadata import (
    PlanMetadataUnavailable,
    normalise_public_https_url,
    thumbnail_from_uploaded_file,
)

# =============================================================================
# PLAN DATE AND TIME CONTROL
# Combines separate date and time inputs into one saved plan start time.
# =============================================================================

# WHY: Keeps the PlanStartDateTimeWidget information and its rules together so they stay consistent.
class PlanStartDateTimeWidget(forms.MultiWidget):
    """Render a calendar followed by a 15-minute start-time dropdown."""

    # WHY: Prepares this object with the values it needs before any other step uses it.
    def __init__(self, attrs=None):
        # WHY: Starts with a prompt so an untouched time field is not mistaken for midnight.
        time_choices = [("", "Select a time")]

        # WHY: Offers every quarter hour explicitly so plans use predictable start times.
        time_choices.extend(
            (
                f"{hour:02d}:{minute:02d}",
                f"{hour:02d}:{minute:02d}",
            )
            for hour in range(24)
            for minute in range(0, 60, 15)
        )
        # WHY: Keeps the date and time easy to choose while Django still treats them as one value.
        widgets = (
            forms.DateInput(
                attrs={
                    "type": "date",
                    "onclick": "if (this.showPicker) this.showPicker()",
                },
                format="%Y-%m-%d",
            ),
            forms.Select(attrs={"aria-label": "Start time"}, choices=time_choices),
        )
        # WHY: Lets Django perform the standard combined-widget setup after these two controls are prepared.
        super().__init__(widgets, attrs)

    # WHY: Connects the visible Starts label to the first real control instead of producing an empty label target.
    def id_for_label(self, id_):
        return f"{id_}_0" if id_ else ""

    # WHY: Keeps the decompress steps in one named place so they can be understood, checked, and reused.
    def decompress(self, value):
        """Return local date and dropdown values for an existing datetime."""
        # WHY: Gives an empty form two empty controls rather than trying to read a missing date.
        if not value:
            return (None, None)

        # WHY: Converts stored time to the site's local time before showing it for editing.
        if timezone.is_aware(value):
            value = timezone.localtime(value)
        return (value.date(), value.strftime("%H:%M"))

# =============================================================================
# ACCOUNT REGISTRATION FORM
# Checks the details used to create a new Kindelise account.
# =============================================================================

# WHY: Keeps the AccountSignUpForm information and its rules together so they stay consistent.
class AccountSignUpForm(UserCreationForm):
    """Validate one canonical email and a confirmed Django-validated password."""

    # WHY: Uses the email as the only public account identifier and helps browsers fill it correctly.
    email = forms.EmailField(
        max_length=150,
        widget=forms.EmailInput(
            attrs={
                "autocomplete": "email",
                "autocapitalize": "none",
                "spellcheck": "false",
            }
        ),
    )

    # WHY: Keeps database or form rules beside the information they control.
    class Meta(UserCreationForm.Meta):
        # WHY: Saves through Django's configured account model rather than assuming a built-in one.
        model = get_user_model()

        # WHY: Shows email here while inherited password fields keep Django's standard password checks.
        fields = ("email",)

    # WHY: Checks and tidies the email value before the site trusts or saves it.
    def clean_email(self):
        """Return one lowercase email not already used as a login identifier."""
        # WHY: Treats capitalisation and surrounding spaces as the same email address.
        email = self.cleaned_data["email"].strip().lower()

        # WHY: Checks the real login field without revealing any password or existing account details.
        if get_user_model().objects.filter(username__iexact=email).exists():
            raise forms.ValidationError("An account already uses this email address.")
        return email


# =============================================================================
# PROFILE EDIT FORM
# Checks public details, discovery choices, availability, and profile images.
# =============================================================================

# WHY: Keeps the ProfileDetailsForm information and its rules together so they stay consistent.
class ProfileDetailsForm(forms.ModelForm):
    """Validate only the signed-in user's editable profile details."""

    # WHY: Limits the browser chooser to the image types that the server can safely reopen and rewrite.
    profile_image = forms.ImageField(
        required=False,
        label="Profile image",
        help_text="Optional. JPG, PNG or WebP, up to 5 MB.",
        widget=forms.FileInput(
            attrs={"accept": "image/jpeg,image/png,image/webp"}
        ),
    )
    display_name = forms.CharField(max_length=80, strip=True)
    title_statement = forms.CharField(
        max_length=120,
        required=False,
        strip=True,
        label="Title statement",
    )
    # WHY: Allows several broad areas through the checkbox list shown on the current profile form.
    broad_area = forms.MultipleChoiceField(
        choices=(),
        widget=forms.CheckboxSelectMultiple(),
    )
    # WHY: Gives visitors one quick switch for immediate availability without asking for a date.
    free_now = forms.BooleanField(
        required=False,
        label="Open to company",
        help_text="Turn this off and leave Available from unset to clear your availability.",
        widget=forms.CheckboxInput(attrs={"class": "availability-toggle"}),
    )
    # WHY: Offers only the relative availability choices understood by the saved profile rules.
    availability_start = forms.ChoiceField(
        choices=(("", "Add later / not set"), *Profile.AvailabilityStart.choices),
        required=False,
        label="Available from",
        help_text=(
            "Today, This week and As and when start now. Tomorrow starts at "
            "local midnight. You can add or clear this later."
        ),
    )

    # WHY: Keeps database or form rules beside the information they control.
    class Meta:
        # WHY: Restricts editing to the public profile fields owned by the signed-in account.
        model = Profile
        fields = (
            "profile_image",
            "display_name",
            "title_statement",
            "biography",
            "broad_area",
            "free_now",
            "availability_start",
            "interests",
        )
        # WHY: Chooses controls suited to longer biography text and selecting several interests.
        widgets = {
            "biography": forms.Textarea(
                attrs={"placeholder": "Tell people a little about yourself."}
            ),
            "interests": forms.CheckboxSelectMultiple(
                attrs={"class": "interest-checkboxes"}
            )
        }

    # WHY: Prepares this object with the values it needs before any other step uses it.
    def __init__(self, *args, **kwargs):
        """Load the current configured areas and controlled interests."""
        # WHY: Lets Django create and bind every declared field before choices are adjusted.
        super().__init__(*args, **kwargs)

        # WHY: Builds area choices from trusted site settings instead of values sent by the browser.
        self.fields["broad_area"].choices = [
            (area_key, area_label)
            for area_key, area_label in settings.KINDLELISE_AREAS.items()
        ]
        # WHY: Shows all saved areas only when the form is first opened, never over a failed submission.
        if not self.is_bound:
            self.initial["broad_area"] = self.instance.broad_areas or (
                [self.instance.broad_area] if self.instance.broad_area else []
            )
        # WHY: Offers only saved staff-controlled interests in a predictable alphabetical order.
        self.fields["interests"].queryset = Interest.objects.order_by("name")
        self.fields["interests"].help_text = "Select all that apply."
        # WHY: Shows current availability without overwriting values the visitor just tried to submit.
        if not self.is_bound and self.instance.pk:
            is_available = self.instance.is_available_now(timezone.now())
            self.initial["free_now"] = is_available
            if is_available:
                self.initial["availability_start"] = ""

    # WHY: Checks and tidies the profile image value before the site trusts or saves it.
    def clean_profile_image(self):
        """Return one bounded image re-encoded without embedded metadata."""
        # WHY: Keeps the existing image when no new uploaded file was supplied.
        uploaded_image = self.cleaned_data.get("profile_image")
        if not uploaded_image or not hasattr(uploaded_image, "size"):
            return uploaded_image
        # WHY: Applies the upload limit before opening the image to avoid needless memory and processing work.
        maximum_bytes = 5 * 1024 * 1024
        if uploaded_image.size > maximum_bytes:
            raise forms.ValidationError("Choose an image no larger than 5 MB.")

        # WHY: Maps each permitted real image format to a safe filename ending and browser content type.
        approved_formats = {
            "JPEG": ("jpg", "image/jpeg"),
            "PNG": ("png", "image/png"),
            "WEBP": ("webp", "image/webp"),
        }
        # WHY: Rewinds the uploaded file because earlier checks may already have read part of it.
        uploaded_image.seek(0)
        try:
            # WHY: Opens and fully reads the file as an image instead of trusting its filename or browser label.
            with Image.open(uploaded_image) as source_image:
                image_format = source_image.format
                if image_format not in approved_formats:
                    raise forms.ValidationError("Choose a JPG, PNG or WebP image.")
                # WHY: Refuses extreme dimensions even when the compressed file itself is small.
                if max(source_image.size) > 4_096:
                    raise forms.ValidationError(
                        "Choose an image no larger than 4,096 pixels per side."
                    )
                # WHY: Loads pixels now so damaged image data is caught before anything is saved.
                source_image.load()

                # WHY: Applies camera rotation while removing the need to retain private EXIF information.
                normalised_image = ImageOps.exif_transpose(source_image)

                # WHY: Converts JPEG pixels to a colour mode that can be saved consistently.
                if image_format == "JPEG":
                    normalised_image = normalised_image.convert("RGB")
                # WHY: Rewrites only the visible pixels into a fresh in-memory image file.
                output = BytesIO()
                normalised_image.save(output, format=image_format)
        # WHY: Preserves the clear validation messages raised by the checks above.
        except forms.ValidationError:
            raise
        # WHY: Turns unreadable or damaged image failures into one safe message for the visitor.
        except (OSError, ValueError) as error:
            raise forms.ValidationError(
                "Choose a valid JPG, PNG or WebP image."
            ) from error

        # WHY: Rechecks size after rewriting because the clean image can be larger than the uploaded version.
        image_bytes = output.getvalue()
        if len(image_bytes) > maximum_bytes:
            raise forms.ValidationError("Choose an image no larger than 5 MB.")
        suffix, content_type = approved_formats[image_format]
        # WHY: Returns a newly named clean upload so the original filename and embedded details are not kept.
        return SimpleUploadedFile(
            f"profile.{suffix}",
            image_bytes,
            content_type=content_type,
        )

    # WHY: Checks and tidies the clean value before the site trusts or saves it.
    def clean(self):
        """Convert the optional relative availability choice to one start time."""
        # WHY: Starts with Django's field-by-field results so this step only connects related choices.
        cleaned_data = super().clean()

        # WHY: Saves every selected area while keeping the first one in the older primary-area field.
        broad_areas = cleaned_data.get("broad_area")
        if broad_areas:
            cleaned_data["broad_areas"] = tuple(broad_areas)
            cleaned_data["broad_area"] = broad_areas[0]
        availability_start = cleaned_data.get("availability_start")

        # WHY: The Free now switch always means availability begins at the actual submission time.
        if cleaned_data.get("free_now"):
            cleaned_data["availability_start"] = Profile.AvailabilityStart.TODAY
            cleaned_data["available_from"] = timezone.now()
            return cleaned_data
        # WHY: An empty availability choice deliberately clears the saved start time.
        if not availability_start:
            cleaned_data["available_from"] = None
            return cleaned_data

        # WHY: Uses one current time so all calculations within this submission agree.
        current_time = timezone.now()

        # WHY: Tomorrow begins at local midnight; every other chosen option begins immediately.
        if availability_start == Profile.AvailabilityStart.TOMORROW:
            local_tomorrow = timezone.localdate(current_time) + timedelta(days=1)
            cleaned_data["available_from"] = timezone.make_aware(
                datetime.combine(local_tomorrow, time.min),
                timezone.get_current_timezone(),
            )
        else:
            cleaned_data["available_from"] = current_time
        return cleaned_data


# =============================================================================
# DISCOVERY FILTER FORM
# Checks broad-area, interest, and availability filters for the current account.
# =============================================================================

# WHY: Keeps the DiscoveryFiltersForm information and its rules together so they stay consistent.
class DiscoveryFiltersForm(forms.Form):
    """Validate discovery filters against server-calculated account limits."""

    # WHY: Requires at least one server-approved broad area to keep discovery deliberately broad.
    broad_area = forms.MultipleChoiceField(
        choices=(),
        label="Areas",
        widget=forms.CheckboxSelectMultiple(
            attrs={"class": "area-checkboxes"}
        ),
    )
    # WHY: Uses saved Interest records so made-up browser values cannot become filters.
    interests = forms.ModelMultipleChoiceField(
        queryset=Interest.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple(
            attrs={"class": "interest-checkboxes"}
        ),
    )
    # WHY: Adds an optional current-availability filter without changing who is permitted to appear.
    available_now = forms.BooleanField(required=False, label="Open to company")

    # WHY: Prepares this object with the values it needs before any other step uses it.
    def __init__(self, *args, allowed_areas, interest_limit, **kwargs):
        """Apply trusted policy output to this request's available filters."""
        # WHY: Builds the ordinary fields first, then narrows them with permission results supplied by the page.
        super().__init__(*args, **kwargs)

        # WHY: Remembers the current account's limit for the later submitted-interest check.
        self.interest_limit = interest_limit

        # WHY: Exposes only areas already allowed by the account policy and site configuration.
        self.fields["broad_area"].choices = [
            (area_key, settings.KINDLELISE_AREAS[area_key])
            for area_key in allowed_areas
            if area_key in settings.KINDLELISE_AREAS
        ]
        self.fields["interests"].queryset = Interest.objects.order_by("name")

    # WHY: Checks and tidies the interests value before the site trusts or saves it.
    def clean_interests(self):
        """Reject an interest selection beyond the account's current limit."""
        # WHY: Counts only Interest records Django has already matched and validated.
        interests = self.cleaned_data["interests"]
        if interests.count() > self.interest_limit:
            raise forms.ValidationError(
                f"Select no more than {self.interest_limit} interests."
            )
        return interests


# =============================================================================
# PLAN FORMS
# Checks plan details and the public URL used to request optional place metadata.
# =============================================================================

# WHY: Gives new plans exact participant limits while keeping the owner outside the selected number.
PLAN_CAPACITY_CHOICES = tuple((value, str(value)) for value in range(1, 16))


# WHY: Keeps the PlanDetailsForm information and its rules together so they stay consistent.
class PlanDetailsForm(forms.ModelForm):
    """Validate bounded future plan details and a normal HTTPS evidence URL."""

    # WHY: Accepts a typed web address for later HTTPS checking while applying a clear length limit.
    public_url = forms.URLField(max_length=500, assume_scheme="http")
    starts_at = forms.SplitDateTimeField(
        input_date_formats=("%Y-%m-%d",),
        input_time_formats=("%H:%M",),
        help_text="Choose a future date and start time.",
        widget=PlanStartDateTimeWidget(),
    )
    # WHY: Makes the exact number of people who may join explicit and bounded for new plans.
    capacity = forms.TypedChoiceField(
        choices=PLAN_CAPACITY_CHOICES,
        coerce=int,
        initial=1,
        help_text="Choose how many people can join you.",
    )

    # WHY: Preserves an older plan's larger capacity during unrelated edits without offering it to new plans.
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["starts_at"].widget.widgets[0].attrs["min"] = (
            timezone.localdate().isoformat()
        )
        current_capacity = getattr(self.instance, "capacity", None)
        if self.instance.pk and current_capacity and current_capacity > 15:
            self.fields["capacity"].choices = (
                *PLAN_CAPACITY_CHOICES,
                (current_capacity, f"{current_capacity} (current capacity)"),
            )

    # WHY: Keeps database or form rules beside the information they control.
    class Meta:
        # WHY: Allows only the owner-editable public plan facts, never status or approval fields.
        model = Plan
        fields = (
            "public_url",
            "public_place",
            "public_address",
            "capacity",
            "starts_at",
            "title",
            "description",
        )

    # WHY: Checks and tidies the public url value before the site trusts or saves it.
    def clean_public_url(self):
        """Accept HTTPS evidence syntax without fetching or approving the URL."""
        # WHY: Applies the same normal HTTPS address rule used by the separate Fetch details action.
        try:
            return normalise_public_https_url(self.cleaned_data["public_url"])
        except ValueError as error:
            raise forms.ValidationError(str(error)) from error

    # WHY: Checks and tidies the starts at value before the site trusts or saves it.
    def clean_starts_at(self):
        """Reject a meeting time that is no longer in the future."""
        # WHY: Uses Django's already combined and time-zone-aware date and time value.
        starts_at = self.cleaned_data["starts_at"]
        if starts_at <= timezone.now():
            raise forms.ValidationError("Choose a future start time.")
        return starts_at


# WHY: Adds one optional manually chosen image to the existing create and edit plan facts.
class PlanImageDetailsForm(PlanDetailsForm):
    """Validate plan details and an optional replacement card image."""

    plan_image = forms.ImageField(
        required=False,
        label="Plan photo",
        help_text="Optional. JPG, PNG or WebP, up to 5 MB.",
        widget=forms.FileInput(
            attrs={
                "accept": "image/jpeg,image/png,image/webp",
                "data-plan-image-input": "",
                "aria-label": "Upload a plan photo",
            }
        ),
    )

    class Meta(PlanDetailsForm.Meta):
        fields = (*PlanDetailsForm.Meta.fields, "plan_image")

    def clean_plan_image(self):
        """Return the same normalized JPEG used by fetched plan thumbnails."""
        uploaded_image = self.cleaned_data.get("plan_image")
        if not uploaded_image:
            return None
        try:
            return thumbnail_from_uploaded_file(uploaded_image)
        except PlanMetadataUnavailable as error:
            raise forms.ValidationError(
                "Choose a valid JPG, PNG or WebP image no larger than 5 MB."
            ) from error


# WHY: Keeps the PlanMetadataRequestForm information and its rules together so they stay consistent.
class PlanMetadataRequestForm(forms.Form):
    """Validate the sole URL accepted by the explicit metadata fetch action."""

    # WHY: Accepts only the one value needed by Fetch details, not an entire plan submission.
    public_url = forms.URLField(max_length=500, assume_scheme="http")

    # WHY: Checks and tidies the public url value before the site trusts or saves it.
    def clean_public_url(self):
        """Apply the same URL syntax boundary as the eventual plan submission."""
        try:
            return normalise_public_https_url(self.cleaned_data["public_url"])
        except ValueError as error:
            raise forms.ValidationError(str(error)) from error


# WHY: Validates only the bounded facts an authorised visitor may send for an optional plan-writing suggestion.
class PlanDraftRequestForm(forms.Form):
    """Validate the three inputs used to extract an editable plan draft."""

    idea = forms.CharField(max_length=6_000, strip=True)
    public_url = forms.URLField(max_length=500, assume_scheme="http")
    capacity = forms.TypedChoiceField(choices=PLAN_CAPACITY_CHOICES, coerce=int)
    public_place = forms.CharField(max_length=200, strip=True, required=False)
    public_address = forms.CharField(max_length=300, strip=True, required=False)

    def clean_public_url(self):
        """Apply the normal public HTTPS boundary before including the URL as draft context."""
        try:
            return normalise_public_https_url(self.cleaned_data["public_url"])
        except ValueError as error:
            raise forms.ValidationError(str(error)) from error


# =============================================================================
# MESSAGE FORMS
# Checks an unsent message and the optional wording goal chosen for it.
# =============================================================================

# WHY: Keeps the MessageDraftForm information and its rules together so they stay consistent.
class MessageDraftForm(forms.Form):
    """Validate one bounded non-empty plain-text message draft."""

    # WHY: Refuses empty or oversized text while preserving message content as plain text.
    body = forms.CharField(max_length=1_000, strip=True)


# WHY: Keeps the MessageEditRequestForm information and its rules together so they stay consistent.
class MessageEditRequestForm(forms.Form):
    """Validate one bounded unsent draft and one fixed editing goal."""

    # WHY: Fixes the only two permitted wording requests so visitors cannot supply hidden instructions.
    EDITING_GOALS = (
        ("fix_grammar", "Fix grammar"),
        ("improve_clarity", "Improve clarity"),
    )

    # WHY: Applies the same size boundary to the unsent draft as the eventual message form.
    draft = forms.CharField(max_length=1_000, strip=True)
    editing_goal = forms.ChoiceField(choices=EDITING_GOALS)


# =============================================================================
# PRIVATE REPORT FORM
# Checks the category and factual description submitted to authorised staff.
# =============================================================================

# WHY: Keeps the PrivateReportForm information and its rules together so they stay consistent.
class PrivateReportForm(forms.ModelForm):
    """Validate category and bounded description with server-owned identities."""

    # WHY: Keeps database or form rules beside the information they control.
    class Meta:
        # WHY: Lets the reporter provide only a reason and description; identities and context come from the server.
        model = Report
        fields = ("category", "description")
