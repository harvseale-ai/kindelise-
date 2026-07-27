"""Validate the seven mapped kinds of untrusted browser input."""

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.utils import timezone

from kindlelise.models import Interest, Plan, Profile, Report


class AccountSignUpForm(UserCreationForm):
    """Validate one unique username and a confirmed Django-validated password."""

    class Meta(UserCreationForm.Meta):
        model = get_user_model()
        fields = ("username",)


class ProfileDetailsForm(forms.ModelForm):
    """Validate only the signed-in user's editable profile details."""

    display_name = forms.CharField(max_length=80, strip=True)
    broad_area = forms.ChoiceField(choices=())

    class Meta:
        model = Profile
        fields = (
            "display_name",
            "biography",
            "broad_area",
            "available_until",
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


class DiscoveryFiltersForm(forms.Form):
    """Validate discovery filters against server-calculated account limits."""

    broad_area = forms.ChoiceField(choices=())
    interests = forms.ModelMultipleChoiceField(
        queryset=Interest.objects.none(),
        required=False,
    )
    available_now = forms.BooleanField(required=False)

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


class PrivateReportForm(forms.ModelForm):
    """Validate category and bounded description with server-owned identities."""

    class Meta:
        model = Report
        fields = ("category", "description")
