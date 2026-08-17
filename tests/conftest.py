"""Provide the approved Kindelise test setup helpers."""

# KEYWORD: fixture helper — builds known sample information so many checks can start the same way.
# KEYWORD: fake — a controlled replacement for an outside service used only while running checks.

from itertools import count

from django.contrib.auth import get_user_model
from django.utils import timezone

from kindlelise.models import Conversation, Interest, Plan, Profile

_user_numbers = count(1)
_interest_numbers = count(1)


# WHY: Builds test user with all required starting values and checks applied.
def create_test_user(username=None, password="Test-pass-742!", **changes):
    """Create an active Django user with supplied safe defaults.

    Inputs: an optional username/password and explicit Django User field changes.
    Returns: the saved Django User.
    Changes: creates one authentication account.
    Privacy: uses a test-only password and no real personal data.
    """
    username = username or f"test_user_{next(_user_numbers)}"
    return get_user_model().objects.create_user(
        username=username,
        password=password,
        **changes,
    )


# WHY: Builds verified test profile with all required starting values and checks applied.
def create_verified_test_profile(user=None, verified_by=None, **changes):
    """Create a profile whose staff verification fields are internally consistent.

    Inputs: optional user/reviewer records and explicit profile field changes.
    Returns: the saved verified Profile.
    Changes: creates missing test users and one verified profile.
    Privacy: uses synthetic profile values only.
    """
    user = user or create_test_user()
    verified_by = verified_by or create_test_user(is_staff=True)
    values = {
        "display_name": "Test user",
        "broad_area": "central",
        "is_verified": True,
        "verified_at": timezone.now(),
        "verified_by": verified_by,
    }
    values.update(changes)
    values.setdefault("broad_areas", [values["broad_area"]])
    if values.get("available_from") is not None:
        values.setdefault("availability_start", Profile.AvailabilityStart.TODAY)
    return Profile.objects.create(user=user, **values)


# WHY: Builds test interest with all required starting values and checks applied.
def create_test_interest(name=None):
    """Create one controlled interest.

    Inputs: an optional synthetic unique name.
    Returns: the saved Interest.
    Changes: creates one controlled vocabulary row.
    """
    name = name or f"Test interest {next(_interest_numbers)}"
    return Interest.objects.create(name=name)


# WHY: Builds test plan with all required starting values and checks applied.
def create_test_plan(owner=None, status=Plan.Status.PENDING, **changes):
    """Create a plan in the explicitly requested state.

    Inputs: an optional owner, one mapped status and explicit field changes.
    Returns: the saved Plan with approval fields consistent with its status.
    Changes: creates missing test users and one plan.
    """
    owner = owner or create_test_user()
    values = {
        "title": "Test plan",
        "description": "A synthetic public-place plan.",
        "public_place": "Central Library",
        "public_url": "https://example.test/central-library",
        "starts_at": timezone.now() + timezone.timedelta(days=1),
        "capacity": 2,
        "status": status,
        "approved_at": None,
        "approved_by": None,
    }
    if status == Plan.Status.APPROVED:
        values["approved_at"] = timezone.now()
        values["approved_by"] = create_test_user(is_staff=True)
    values.update(changes)
    return Plan.objects.create(owner=owner, **values)


# WHY: Builds the two current plan start controls from one readable test datetime.
def plan_start_form_values(value):
    """Return the date and time values submitted by the current plan form."""
    # WHY: Matches the local date and time shown to the visitor before the form is submitted.
    if timezone.is_aware(value):
        value = timezone.localtime(value)
    return {
        "starts_at_0": value.date().isoformat(),
        "starts_at_1": value.strftime("%H:%M"),
    }


# WHY: Builds test conversation with all required starting values and checks applied.
def create_test_conversation(first_user=None, second_user=None):
    """Create one correctly ordered account pair.

    Inputs: two optional distinct saved Django users.
    Returns: the saved Conversation with the lower account ID first.
    Changes: creates missing test users and one direct conversation.
    """
    first_user = first_user or create_test_user()
    second_user = second_user or create_test_user()
    lower_user, higher_user = sorted(
        (first_user, second_user), key=lambda user: user.pk
    )
    return Conversation.objects.create(
        first_user=lower_user,
        second_user=higher_user,
    )


# WHY: Keeps the build stripe test event steps in one named place so they can be understood, checked, and reused.
def build_stripe_test_event(
    event_type="customer.subscription.updated",
    *,
    event_id="evt_test_safe",
    provider_created_at=None,
    data=None,
):
    """Build one supported or deliberately unsupported event with no real Stripe data.

    Inputs: a synthetic type, ID, provider time and object payload.
    Returns: a dictionary shaped like the limited event values used by tests.
    Changes: none.
    Privacy: contains no real Stripe customer or payment data.
    """
    provider_created_at = provider_created_at or timezone.now()
    return {
        "id": event_id,
        "type": event_type,
        "created": int(provider_created_at.timestamp()),
        "data": {"object": data or {}},
    }


# WHY: Keeps the replace ollama request with fake steps in one named place so they can be understood, checked, and reused.
def replace_ollama_request_with_fake(monkeypatch, request_owner, outcome):
    """Prevent a network call and return the exact requested test outcome.

    Inputs: pytest monkeypatch, the module owning urlopen and a value or exception.
    Returns: the installed fake request callable.
    Changes: replaces only the supplied test module's urlopen attribute.
    Privacy: sends and stores no draft or provider credential.
    """

    # WHY: Returns a controlled reply during checks so no real outside request is made.
    def fake_request(*args, **kwargs):
        fake_request.calls.append((args, kwargs))
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome

    fake_request.calls = []
    monkeypatch.setattr(request_owner, "urlopen", fake_request)
    return fake_request
