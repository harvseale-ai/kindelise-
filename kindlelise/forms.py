"""Validate the seven mapped kinds of untrusted browser input."""

from datetime import datetime, time, timedelta

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.utils import timezone

from kindlelise.models import Interest, Plan, Profile, Report


class AccountSignUpForm(UserCreationForm):
    """Validate one canonical email and a confirmed Django-validated password."""

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

    class Meta(UserCreationForm.Meta):
        model = get_user_model()
        fields = ("email",)

    def clean_email(self):
        """Return one lowercase email not already used as a login identifier."""
        email = self.cleaned_data["email"].strip().lower()
        if get_user_model().objects.filter(username__iexact=email).exists():
            raise forms.ValidationError("An account already uses this email address.")
        return email


class ProfileDetailsForm(forms.ModelForm):
    """Validate only the signed-in user's editable profile details."""

    display_name = forms.CharField(max_length=80, strip=True)
    broad_area = forms.ChoiceField(choices=())
    free_now = forms.BooleanField(
        required=False,
        label="Free now",
        help_text="Turn this off and leave Available from unset to clear it.",
        widget=forms.CheckboxInput(attrs={"class": "availability-toggle"}),
    )
    availability_start = forms.ChoiceField(
        choices=(("", "Add later / not set"), *Profile.AvailabilityStart.choices),
        required=False,
        label="Available from",
        help_text=(
            "Today, This week and As and when start now. Tomorrow starts at "
            "local midnight. You can add or clear this later."
        ),
    )

    class Meta:
        model = Profile
        fields = (
            "display_name",
            "biography",
            "broad_area",
            "free_now",
            "availability_start",
            "interests",
        )

    def __init__(self, *args, **kwargs):
        """Load the current configured areas and controlled interests."""
        super().__init__(*args, **kwargs)
        self.fields["broad_area"].choices = [
            (area_key, area_label)
            for area_key, area_label in settings.KINDLELISE_AREAS.items()
        ]
        self.fields["interests"].queryset = Interest.objects.order_by("name")
        if not self.is_bound and self.instance.pk:
            is_available = self.instance.is_available_now(timezone.now())
            self.initial["free_now"] = is_available
            if is_available:
                self.initial["availability_start"] = ""

    def clean(self):
        """Convert the optional relative availability choice to one start time."""
        cleaned_data = super().clean()
        availability_start = cleaned_data.get("availability_start")
        if cleaned_data.get("free_now"):
            cleaned_data["availability_start"] = Profile.AvailabilityStart.TODAY
            cleaned_data["available_from"] = timezone.now()
            return cleaned_data
        if not availability_start:
            cleaned_data["available_from"] = None
            return cleaned_data

        current_time = timezone.now()
        if availability_start == Profile.AvailabilityStart.TOMORROW:
            local_tomorrow = timezone.localdate(current_time) + timedelta(days=1)
            cleaned_data["available_from"] = timezone.make_aware(
                datetime.combine(local_tomorrow, time.min),
                timezone.get_current_timezone(),
            )
        else:
            cleaned_data["available_from"] = current_time
        return cleaned_data


class DiscoveryFiltersForm(forms.Form):
    """Validate discovery filters against server-calculated account limits."""

    broad_area = forms.ChoiceField(choices=())
    interests = forms.ModelMultipleChoiceField(
        queryset=Interest.objects.none(),
        required=False,
    )
    available_now = forms.BooleanField(required=False, label="Free now")

    def __init__(self, *args, allowed_areas, interest_limit, **kwargs):
        """Apply trusted policy output to this request's available filters."""
        super().__init__(*args, **kwargs)
        self.interest_limit = interest_limit
        self.fields["broad_area"].choices = [
            (area_key, settings.KINDLELISE_AREAS[area_key])
            for area_key in allowed_areas
            if area_key in settings.KINDLELISE_AREAS
        ]
        self.fields["interests"].queryset = Interest.objects.order_by("name")

    def clean_interests(self):
        """Reject an interest selection beyond the account's current limit."""
        interests = self.cleaned_data["interests"]
        if interests.count() > self.interest_limit:
            raise forms.ValidationError(
                f"Select no more than {self.interest_limit} interests."
            )
        return interests


class PlanDetailsForm(forms.ModelForm):
    """Validate bounded future plan details and a normal HTTPS evidence URL."""

    public_url = forms.URLField(max_length=500, assume_scheme="http")
    capacity = forms.IntegerField(min_value=1)

    class Meta:
        model = Plan
        fields = (
            "title",
            "description",
            "public_place",
            "public_url",
            "starts_at",
            "capacity",
        )

    def clean_public_url(self):
        """Accept HTTPS evidence syntax without fetching or approving the URL."""
        public_url = self.cleaned_data["public_url"]
        if not public_url.lower().startswith("https://"):
            raise forms.ValidationError("Enter an HTTPS URL.")
        return public_url

    def clean_starts_at(self):
        """Reject a meeting time that is no longer in the future."""
        starts_at = self.cleaned_data["starts_at"]
        if starts_at <= timezone.now():
            raise forms.ValidationError("Choose a future start time.")
        return starts_at


class MessageDraftForm(forms.Form):
    """Validate one bounded non-empty plain-text message draft."""

    body = forms.CharField(max_length=1_000, strip=True)


class MessageEditRequestForm(forms.Form):
    """Validate one bounded unsent draft and one fixed editing goal."""

    EDITING_GOALS = (
        ("fix_grammar", "Fix grammar"),
        ("improve_clarity", "Improve clarity"),
    )

    draft = forms.CharField(max_length=1_000, strip=True)
    editing_goal = forms.ChoiceField(choices=EDITING_GOALS)


class PrivateReportForm(forms.ModelForm):
    """Validate category and bounded description with server-owned identities."""

    class Meta:
        model = Report
        fields = ("category", "description")
