"""Test Kindelise plan behaviour."""

import base64
import socket
from concurrent.futures import ThreadPoolExecutor
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

import kindlelise.plan_metadata as plan_metadata
import kindlelise.views.plans as plan_views
from kindlelise.models import (
    Participation,
    Plan,
    PlanChat,
    Profile,
)
from kindlelise.services import (
    confirm_requested_plan_participation,
    request_plan_participation_and_open_owner_conversation,
)
from tests.conftest import (
    create_test_plan,
    create_test_user,
    create_verified_test_profile,
    plan_start_form_values,
)

pytestmark = pytest.mark.django_db


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
    assert unverified_response.status_code == 200


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
    assert b"data-plan-image-dropzone" in get_response.content
    assert b'enctype="multipart/form-data"' in get_response.content
    assert b'src="data:image/gif;base64,' in get_response.content
    assert tuple(get_response.context["form"].fields) == (
        "public_url",
        "public_place",
        "public_address",
        "capacity",
        "starts_at",
        "title",
        "description",
        "plan_image",
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


def test_plan_draft_suggestion_validates_facts_and_never_saves(monkeypatch):
    owner = create_test_user()
    create_verified_test_profile(user=owner)
    client = Client()
    client.force_login(owner)
    draft_url = reverse("plan_draft_suggestion")
    future = timezone.now() + timezone.timedelta(days=1)
    captured = {}

    def return_draft(**facts):
        captured.update(facts)
        return {
            "title": "Mahjong at the public games café",
            "description": "Join me for a friendly game of mahjong.",
            "public_place": "Public Games Café",
            "public_address": "10 High Street, London",
            "date": future.date().isoformat(),
            "time": future.strftime("%H:%M"),
        }

    monkeypatch.setattr(plan_views, "get_plan_draft_suggestion", return_draft)
    response = client.post(
        draft_url,
        {
            "idea": "I need three other mahjong players.",
            "public_url": "https://events.example.test/mahjong",
            "public_place": "Public Games Café",
            "public_address": "10 High Street, London",
            "capacity": "3",
        },
    )

    assert response.status_code == 200
    assert response.json()["title"] == "Mahjong at the public games café"
    assert captured["capacity"] == 3
    assert captured["public_url"] == "https://events.example.test/mahjong"
    assert not Plan.objects.filter(title="Mahjong at the public games café").exists()
    assert client.get(draft_url).status_code == 405
    assert client.post(draft_url, {"capacity": "16"}).status_code == 400


def test_plan_fetch_details_rejects_unsafe_targets_and_mismatched_tokens(
    monkeypatch,
):
    fallback_place, fallback_address, fallback_image = plan_metadata._extract_metadata(
        b'<meta property="og:site_name" content="BBC News"><meta property="og:image" content="/news.jpg">',
        "https://www.bbc.co.uk/article",
    )
    assert fallback_place == "BBC News"
    assert fallback_address is None
    assert fallback_image == "https://www.bbc.co.uk/news.jpg"

    owner = create_test_user()
    create_verified_test_profile(user=owner)
    provider_calls = []

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
    assert (
        b"Add venue details again before creating the plan" in create_response.content
    )
    assert not Plan.objects.filter(title="Mismatched thumbnail plan").exists()


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


def test_plan_http_request_confirm_leave_and_reconfirm_preserve_history_and_lock():
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
        reverse("plan_participation_request", args=[plan.pk])
    )
    assert missing_csrf_response.status_code == 403
    assert not Participation.objects.filter(plan=plan).exists()

    csrf_token = participant_client.cookies["csrftoken"].value
    request_response = participant_client.post(
        reverse("plan_participation_request", args=[plan.pk]),
        {"csrfmiddlewaretoken": csrf_token},
        HTTP_REFERER=f"http://testserver{detail_response.request['PATH_INFO']}",
    )
    participation = Participation.objects.get(plan=plan, user=participant)
    plan.refresh_from_db()
    assert request_response.status_code == 302
    assert request_response.url.startswith("/conversations/")
    assert participation.status == Participation.Status.PENDING
    assert participation.joined_at is None
    assert plan.meeting_details_locked_at is None
    assert plan.participations.filter(status=Participation.Status.JOINED).count() == 0

    owner_client = Client()
    owner_client.force_login(owner)
    owner_detail = owner_client.get(reverse("plan_detail", args=[plan.pk]))
    assert b"Pending requests" in owner_detail.content
    assert b"Confirm" in owner_detail.content
    confirm_response = owner_client.post(
        reverse(
            "plan_participation_confirm",
            args=[plan.pk, participation.pk],
        )
    )
    participation.refresh_from_db()
    plan.refresh_from_db()
    first_lock = plan.meeting_details_locked_at
    first_join = participation.joined_at
    assert confirm_response.status_code == 302
    assert participation.status == Participation.Status.JOINED
    assert first_join is not None
    assert first_lock is not None

    owner_detail = owner_client.get(reverse("plan_detail", args=[plan.pk]))
    assert b"can no longer be edited" in owner_detail.content
    assert reverse("plan_edit", args=[plan.pk]).encode() not in owner_detail.content
    assert (
        owner_client.get(
            reverse("plan_participation_request", args=[plan.pk])
        ).status_code
        == 405
    )
    owner_request_response = owner_client.post(
        reverse("plan_participation_request", args=[plan.pk])
    )
    assert owner_request_response.url == reverse("plan_list")
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

    rejoin_response = participant_client.post(
        reverse("plan_participation_request", args=[plan.pk])
    )
    participation.refresh_from_db()
    assert rejoin_response.status_code == 302
    assert participation.status == Participation.Status.PENDING
    assert participation.joined_at is None
    assert participation.left_at is None
    assert Participation.objects.filter(plan=plan, user=participant).count() == 1

    owner_client.post(
        reverse(
            "plan_participation_confirm",
            args=[plan.pk, participation.pk],
        )
    )
    participation.refresh_from_db()
    assert participation.status == Participation.Status.JOINED
    assert participation.joined_at >= first_join

    outsider_client = Client()
    outsider_client.force_login(outsider)
    refused_full_response = outsider_client.post(
        reverse("plan_participation_request", args=[plan.pk])
    )
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

    def test_plan_capacity_confirmation_race_allows_only_one_participation(self):
        pending_requests = []
        for participant in self.participants:
            participation, _conversation = (
                request_plan_participation_and_open_owner_conversation(
                    participant,
                    self.plan,
                )
            )
            pending_requests.append(participation)
        start_together = Barrier(2)

        def attempt_confirm(participation_id):
            close_old_connections()
            try:
                owner = get_user_model().objects.get(pk=self.owner.pk)
                plan = Plan.objects.get(pk=self.plan.pk)
                start_together.wait(timeout=5)
                try:
                    confirm_requested_plan_participation(
                        owner,
                        plan,
                        participation_id,
                    )
                except PermissionDenied:
                    return False
                return True
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as executor:
            outcomes = list(
                executor.map(
                    attempt_confirm,
                    [participation.pk for participation in pending_requests],
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
        self.assertEqual(PlanChat.objects.filter(plan=self.plan).count(), 1)
