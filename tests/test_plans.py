"""Test Kindelise plan behaviour."""

# KEYWORD: test — an automatic check that proves one expected behaviour still works.
# KEYWORD: assert — compares the actual result with the result the check expects.
# KEYWORD: monkeypatch — temporarily replaces a setting or outside call for one check, then restores it.
# KEYWORD: HTTP — the request-and-response rules used when these checks visit a page.
# KEYWORD: CSRF — the private form check that prevents another website submitting as the signed-in visitor.
# KEYWORD: PostgreSQL — the database used by the live site to keep saved information and its rules.

import base64
import socket
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from threading import Barrier

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.db import (
    close_old_connections,
    connections,
)
from django.test import Client, TransactionTestCase
from django.urls import reverse
from django.utils import timezone
from PIL import Image

import kindlelise.plan_metadata as plan_metadata
from kindlelise.models import (
    Participation,
    Plan,
    Profile,
)
from kindlelise.services import (
    join_approved_plan_and_lock_meeting_details,
)
from tests.conftest import (
    create_test_plan,
    create_test_user,
    create_verified_test_profile,
    plan_start_form_values,
)

pytestmark = pytest.mark.django_db


# WHY: Checks that admin registers models with only mapped profile and plan actions so a future change cannot quietly break it.


# WHY: Checks that plan http list gates access and preserves owner only states so a future change cannot quietly break it.
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
    assert b'aria-label="Capacity:' not in response.content
    assert b'<span class="visually-hidden">Capacity:</span>' in response.content
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


# WHY: Checks that plan http creation is immediately available and preserves invalid form so a future change cannot quietly break it.
def test_plan_http_creation_is_immediately_available_and_preserves_invalid_form():
    owner = create_test_user()
    create_verified_test_profile(user=owner)
    injected_owner = create_test_user()
    client = Client()
    client.force_login(owner)
    future = timezone.now() + timezone.timedelta(days=1)

    get_response = client.get(reverse("plan_create"))
    assert get_response.status_code == 200
    assert b'type="date"' in get_response.content
    assert b'name="starts_at_0"' in get_response.content
    assert b'<label for="id_starts_at_0">Starts at</label>' in get_response.content
    assert b'aria-label="Start time"' in get_response.content
    assert b'<label for="">Starts at</label>' not in get_response.content
    assert b"this.showPicker()" in get_response.content
    assert b'<select name="starts_at_1"' in get_response.content
    assert b'<option value="09:00">09:00</option>' in get_response.content
    assert b"data-plan-metadata-preview" in get_response.content
    assert b'src="data:image/gif;base64,' in get_response.content
    assert tuple(get_response.context["form"].fields) == (
        "title",
        "description",
        "public_url",
        "public_place",
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
            **plan_start_form_values(future),
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
    assert plan.status == Plan.Status.APPROVED
    assert plan.approved_at is not None
    assert plan.approved_by == owner
    assert plan.meeting_details_locked_at is None

    invalid_response = client.post(
        reverse("plan_create"),
        {
            "title": "Invalid HTTP plan",
            "description": "Not written.",
            "public_place": "Private place",
            "public_url": "http://example.test/not-https",
            **plan_start_form_values(future),
            "capacity": "1",
        },
    )
    assert invalid_response.status_code == 200
    assert b"Enter an HTTPS URL" in invalid_response.content
    assert not Plan.objects.filter(title="Invalid HTTP plan").exists()


# WHY: Checks that plan fetch details stores and serves normalized card thumbnail so a future change cannot quietly break it.
def test_plan_fetch_details_stores_and_serves_normalized_card_thumbnail(
    monkeypatch,
    settings,
    tmp_path,
):
    settings.MEDIA_ROOT = tmp_path
    owner = create_test_user()
    create_verified_test_profile(user=owner)
    image_output = BytesIO()
    Image.new("RGBA", (48, 32), color=(31, 97, 68, 180)).save(
        image_output,
        format="PNG",
    )
    page_html = b"""
        <html><head>
          <script type="application/ld+json">
            {"@type":"Event","location":{"@type":"Place","name":"City Museum","image":"https://images.example.test/museum.png"}}
          </script>
          <meta property="og:site_name" content="Must not become the place">
        </head></html>
    """

    # WHY: Keeps the return public resources steps in one named place so they can be understood, checked, and reused.
    def return_public_resources(url, allowed_content_types, maximum_bytes):
        if url == "https://venue.example.test/visit":
            assert "text/html" in allowed_content_types
            return url, "text/html", page_html
        assert url == "https://images.example.test/museum.png"
        assert "image/png" in allowed_content_types
        return url, "image/png", image_output.getvalue()

    monkeypatch.setattr(
        plan_metadata,
        "_fetch_https_bytes",
        return_public_resources,
    )
    client = Client(enforce_csrf_checks=True)
    client.force_login(owner)
    create_url = reverse("plan_create")
    fetch_url = reverse("plan_metadata_fetch")
    create_page = client.get(create_url)
    assert create_page.status_code == 200
    assert b"Fetch details" in create_page.content
    assert client.get(fetch_url).status_code == 405
    assert (
        client.post(
            fetch_url,
            {"public_url": "https://venue.example.test/visit"},
        ).status_code
        == 403
    )

    csrf_token = client.cookies["csrftoken"].value
    fetch_response = client.post(
        fetch_url,
        {
            "csrfmiddlewaretoken": csrf_token,
            "public_url": "https://venue.example.test/visit",
        },
    )
    assert fetch_response.status_code == 200
    fetched = fetch_response.json()
    assert fetched["public_place"] == "City Museum"
    assert fetched["thumbnail_found"] is True
    assert fetched["thumbnail_preview"].startswith("data:image/jpeg;base64,")
    assert fetched["metadata_token"]

    future = timezone.now() + timezone.timedelta(days=1)
    create_response = client.post(
        create_url,
        {
            "csrfmiddlewaretoken": csrf_token,
            "title": "Museum thumbnail plan",
            "description": "Meet at the staffed public entrance.",
            "public_url": "https://venue.example.test/visit",
            "public_place": fetched["public_place"],
            **plan_start_form_values(future),
            "capacity": "3",
            "fetched_metadata": fetched["metadata_token"],
        },
    )
    plan = Plan.objects.get(title="Museum thumbnail plan")
    assert create_response.status_code == 302
    assert plan.thumbnail_image.name.startswith("plan-thumbnails/")
    thumbnail_path = tmp_path / plan.thumbnail_image.name
    assert thumbnail_path.exists()
    with Image.open(thumbnail_path) as stored_image:
        assert stored_image.format == "JPEG"
        assert not stored_image.getexif()

    list_response = client.get(reverse("plan_list"))
    assert list_response.status_code == 200
    assert b"plan-card--with-image" in list_response.content
    assert reverse("plan_thumbnail", args=[plan.pk]).encode() in list_response.content

    # WHY: Keeps the return place with unavailable image steps in one named place so they can be understood, checked, and reused.
    def return_place_with_unavailable_image(url, allowed_content_types, maximum_bytes):
        if "text/html" in allowed_content_types:
            return url, "text/html", page_html
        raise plan_metadata.PlanMetadataUnavailable

    monkeypatch.setattr(
        plan_metadata,
        "_fetch_https_bytes",
        return_place_with_unavailable_image,
    )
    partial_response = client.post(
        fetch_url,
        {
            "csrfmiddlewaretoken": csrf_token,
            "public_url": "https://venue.example.test/visit",
        },
    )
    assert partial_response.status_code == 200
    assert partial_response.json()["public_place"] == "City Museum"
    assert partial_response.json()["thumbnail_found"] is False
    assert partial_response.json()["metadata_token"] == ""

    edit_url = reverse("plan_edit", args=[plan.pk])
    assert b"Fetch details" in client.get(edit_url).content
    first_thumbnail_name = plan.thumbnail_image.name
    edit_response = client.post(
        edit_url,
        {
            "csrfmiddlewaretoken": csrf_token,
            "title": plan.title,
            "description": plan.description,
            "public_url": plan.public_url,
            "public_place": plan.public_place,
            **plan_start_form_values(future),
            "capacity": str(plan.capacity),
            "fetched_metadata": fetched["metadata_token"],
        },
    )
    plan.refresh_from_db()
    assert edit_response.status_code == 302
    assert plan.thumbnail_image.name != first_thumbnail_name

    image_response = client.get(reverse("plan_thumbnail", args=[plan.pk]))
    assert image_response.status_code == 200
    assert image_response["Content-Type"] == "image/jpeg"
    image_response.close()
    assert Client().get(reverse("plan_thumbnail", args=[plan.pk])).status_code == 302


# WHY: Checks that plan fetch details rejects unsafe targets and mismatched tokens so a future change cannot quietly break it.
def test_plan_fetch_details_rejects_unsafe_targets_and_mismatched_tokens(
    monkeypatch,
):
    fallback_place, fallback_image = plan_metadata._extract_metadata(
        b'<meta property="og:site_name" content="BBC News"><meta property="og:image" content="/news.jpg">',
        "https://www.bbc.co.uk/article",
    )
    assert fallback_place == "BBC News"
    assert fallback_image == "https://www.bbc.co.uk/news.jpg"

    owner = create_test_user()
    create_verified_test_profile(user=owner)
    provider_calls = []

    # WHY: Keeps the record provider call steps in one named place so they can be understood, checked, and reused.
    def record_provider_call(public_url, user_id):
        provider_calls.append((public_url, user_id))
        return None

    monkeypatch.setattr(
        "kindlelise.views.plans.fetch_plan_metadata", record_provider_call
    )
    client = Client()
    client.force_login(owner)
    invalid_response = client.post(
        reverse("plan_metadata_fetch"),
        {"public_url": "http://127.0.0.1/private"},
    )
    assert invalid_response.status_code == 400
    assert provider_calls == []

    monkeypatch.setattr(
        plan_metadata.socket,
        "getaddrinfo",
        lambda *args, **kwargs: [
            (
                socket.AF_INET,
                socket.SOCK_STREAM,
                socket.IPPROTO_TCP,
                "",
                ("127.0.0.1", 443),
            )
        ],
    )
    with pytest.raises(plan_metadata.PlanMetadataUnavailable):
        plan_metadata._global_addresses_for_url("https://internal.example.test/")

    token = plan_metadata.signing.dumps(
        {
            "user_id": owner.pk,
            "public_url": "https://venue.example.test/one",
            "thumbnail": base64.b64encode(b"not-used-as-a-mismatched-image").decode(
                "ascii"
            ),
        },
        salt=plan_metadata.METADATA_TOKEN_SALT,
        compress=True,
    )
    future = timezone.now() + timezone.timedelta(days=1)
    create_response = client.post(
        reverse("plan_create"),
        {
            "title": "Mismatched thumbnail plan",
            "description": "The token belongs to a different URL.",
            "public_url": "https://venue.example.test/two",
            "public_place": "City Museum",
            **plan_start_form_values(future),
            "capacity": "2",
            "fetched_metadata": token,
        },
    )
    assert create_response.status_code == 200
    assert b"Fetch details again before creating the plan" in create_response.content
    assert not Plan.objects.filter(title="Mismatched thumbnail plan").exists()


# WHY: Checks that plan http owner edit stays available and hidden edits share 404 so a future change cannot quietly break it.
def test_plan_http_owner_edit_stays_available_and_hidden_edits_share_404():
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
        **plan_start_form_values(approved_plan.starts_at),
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
    assert approved_plan.status == Plan.Status.APPROVED
    assert approved_plan.approved_by == original_reviewer

    rejected_response = client.post(
        reverse("plan_edit", args=[rejected_plan.pk]),
        {
            "title": rejected_plan.title,
            "description": "Revised after staff rejection.",
            "public_place": rejected_plan.public_place,
            "public_url": rejected_plan.public_url,
            **plan_start_form_values(rejected_plan.starts_at),
            "capacity": str(rejected_plan.capacity),
        },
    )
    rejected_plan.refresh_from_db()
    assert rejected_response.status_code == 302
    assert rejected_plan.status == Plan.Status.APPROVED
    assert rejected_plan.approved_by == owner

    other_client = Client()
    other_client.force_login(other_user)
    hidden_responses = (
        other_client.get(reverse("plan_edit", args=[approved_plan.pk])),
        client.get(reverse("plan_edit", args=[locked_plan.pk])),
        client.get(reverse("plan_edit", args=[cancelled_plan.pk])),
        client.get(reverse("plan_edit", args=[999999])),
    )
    assert {response.status_code for response in hidden_responses} == {404}
    assert {response.content for response in hidden_responses} == {b"Plan unavailable."}


# WHY: Checks that plan http join leave rejoin and cancel preserve history and lock so a future change cannot quietly break it.
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

    detail_response = participant_client.get(reverse("plan_detail", args=[plan.pk]))
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
    leave_response = participant_client.post(reverse("plan_leave", args=[plan.pk]))
    participation.refresh_from_db()
    plan.refresh_from_db()
    assert leave_response.status_code == 302
    assert participation.status == Participation.Status.LEFT
    assert participation.left_at is not None
    assert plan.meeting_details_locked_at == first_lock

    rejoin_response = participant_client.post(reverse("plan_join", args=[plan.pk]))
    participation.refresh_from_db()
    assert rejoin_response.status_code == 302
    assert participation.status == Participation.Status.JOINED
    assert participation.joined_at >= first_join
    assert participation.left_at is None
    assert Participation.objects.filter(plan=plan, user=participant).count() == 1

    outsider_client = Client()
    outsider_client.force_login(outsider)
    refused_full_response = outsider_client.post(reverse("plan_join", args=[plan.pk]))
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
    assert (
        participant_client.get(reverse("plan_detail", args=[plan.pk])).status_code
        == 404
    )


# WHY: Keeps the PlanCapacityJoinRaceTests information and its rules together so they stay consistent.
class PlanCapacityJoinRaceTests(TransactionTestCase):
    """Prove PostgreSQL row locking prevents two final-capacity joins."""

    # WHY: Keeps the setUp steps in one named place so they can be understood, checked, and reused.
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

    # WHY: Checks that plan capacity join race allows only one participation so a future change cannot quietly break it.
    def test_plan_capacity_join_race_allows_only_one_participation(self):
        start_together = Barrier(2)

        # WHY: Keeps the attempt join steps in one named place so they can be understood, checked, and reused.
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
