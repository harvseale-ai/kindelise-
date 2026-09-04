"""Test Kindelise blocking and private-report behaviour."""

# KEYWORD: test — an automatic check that proves one expected behaviour still works.
# KEYWORD: assert — compares the actual result with the result the check expects.
# KEYWORD: monkeypatch — temporarily replaces a setting or outside call for one check, then restores it.
# KEYWORD: HTTP — the request-and-response rules used when these checks visit a page.
# KEYWORD: CSRF — the private form check that prevents another website submitting as the signed-in visitor.
# KEYWORD: PostgreSQL — the database used by the live site to keep saved information and its rules.

import pytest
from django.core.exceptions import PermissionDenied
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from kindlelise.forms import PrivateReportForm
from kindlelise.models import (
    Block,
    Message,
    Participation,
    Plan,
    Profile,
    Report,
)
from kindlelise.selectors import get_signed_in_user_account_summary
from kindlelise.services import (
    block_user_from_discovery_and_messages,
    confirm_requested_plan_participation,
    request_plan_participation_and_open_owner_conversation,
    send_plan_chat_message,
    submit_private_report_about_user,
)
from tests.conftest import (
    create_test_conversation,
    create_test_plan,
    create_test_user,
    create_verified_test_profile,
)

pytestmark = pytest.mark.django_db


# WHY: Checks that block http requires csrf closes interaction and keeps reporting open so a future change cannot quietly break it.
def test_block_http_requires_csrf_closes_interaction_and_keeps_reporting_open():
    blocker = create_test_user()
    create_verified_test_profile(user=blocker)
    target = create_test_user()
    target_profile = create_verified_test_profile(
        user=target,
        display_name="HTTP block target",
    )
    conversation = create_test_conversation(blocker, target)
    client = Client(enforce_csrf_checks=True)
    client.force_login(blocker)
    profile_url = reverse("profile_detail", args=[target_profile.pk])
    block_url = reverse(
        "profile_block_messages_and_discovery",
        args=[target_profile.pk],
    )
    report_url = reverse("report_create", args=[target_profile.pk])
    profile_response = client.get(profile_url)

    assert profile_response.status_code == 200
    assert block_url.encode() in profile_response.content
    assert report_url.encode() in profile_response.content
    assert client.get(block_url).status_code == 405
    assert client.post(block_url).status_code == 403
    assert not Block.objects.exists()

    csrf_token = client.cookies["csrftoken"].value
    block_response = client.post(
        block_url,
        {"csrfmiddlewaretoken": csrf_token},
        HTTP_REFERER=f"http://testserver{profile_response.request['PATH_INFO']}",
    )
    assert block_response.status_code == 302
    assert block_response.url == reverse("discover")
    assert Block.objects.filter(blocker=blocker, blocked_user=target).count() == 1
    assert client.get(profile_url).status_code == 404
    assert (
        client.get(reverse("conversation_detail", args=[conversation.pk])).status_code
        == 404
    )
    assert b"HTTP block target" not in client.get(reverse("inbox")).content
    assert client.get(report_url).status_code == 200

    target_client = Client()
    target_client.force_login(target)
    target_account_response = target_client.get(reverse("account"))
    assert b"Interaction closed" not in target_account_response.content
    assert b"blocker" not in target_account_response.content.lower()


# WHY: Checks that private report http validates conversation and received message contexts so a future change cannot quietly break it.
def test_private_report_http_validates_conversation_and_received_message_contexts():
    reporter = create_test_user()
    create_verified_test_profile(user=reporter)
    target = create_test_user()
    target_profile = create_verified_test_profile(
        user=target,
        display_name="Report conversation target",
    )
    outsider = create_test_user()
    create_verified_test_profile(user=outsider)
    conversation = create_test_conversation(reporter, target)
    received_message = Message.objects.create(
        conversation=conversation,
        sender=target,
        body="Eligible received report context",
    )
    own_message = Message.objects.create(
        conversation=conversation,
        sender=reporter,
        body="Own message has no report action",
    )
    unrelated_conversation = create_test_conversation(reporter, outsider)
    unrelated_message = Message.objects.create(
        conversation=unrelated_conversation,
        sender=outsider,
        body="Unrelated message context",
    )
    client = Client()
    client.force_login(reporter)
    report_url = reverse("report_create", args=[target_profile.pk])
    conversation_response = client.get(
        reverse("conversation_detail", args=[conversation.pk])
    )

    assert conversation_response.status_code == 200
    assert b"Report this conversation privately" in conversation_response.content
    assert conversation_response.content.count(b"Report this message") == 1
    assert (
        f"context_id={received_message.pk}&amp;context_conversation_id={conversation.pk}".encode()
        in conversation_response.content
    )
    assert (
        f"context_id={own_message.pk}&amp;context_conversation_id={conversation.pk}".encode()
        not in conversation_response.content
    )

    conversation_report_response = client.post(
        report_url,
        {
            "category": Report.Category.OTHER,
            "description": "Private conversation context.",
            "context_type": "conversation",
            "context_id": str(conversation.pk),
        },
    )
    message_report_response = client.post(
        report_url,
        {
            "category": Report.Category.SAFETY_CONCERN,
            "description": "Private received-message context.",
            "context_type": "message",
            "context_id": str(received_message.pk),
            "context_conversation_id": str(conversation.pk),
        },
    )
    reports = list(Report.objects.order_by("pk"))
    assert conversation_report_response.status_code == 200
    assert message_report_response.status_code == 200
    assert reports[0].reported_conversation == conversation
    assert reports[1].reported_message == received_message

    refused_own_response = client.post(
        report_url,
        {
            "category": Report.Category.OTHER,
            "description": "Own message context must be refused.",
            "context_type": "message",
            "context_id": str(own_message.pk),
            "context_conversation_id": str(conversation.pk),
        },
    )
    refused_unrelated_response = client.post(
        report_url,
        {
            "category": Report.Category.OTHER,
            "description": "Unrelated message context must be refused.",
            "context_type": "message",
            "context_id": str(unrelated_message.pk),
            "context_conversation_id": str(unrelated_conversation.pk),
        },
    )
    assert (
        refused_own_response.status_code
        == refused_unrelated_response.status_code
        == 404
    )
    assert (
        refused_own_response.content
        == refused_unrelated_response.content
        == b"Report unavailable."
    )
    assert Report.objects.count() == 2


# WHY: Checks that private report service stores received reports with valid contexts so a future change cannot quietly break it.
def test_private_report_service_stores_received_reports_with_valid_contexts():
    reporter = create_test_user()
    reported_user = create_test_user()
    Profile.objects.create(user=reported_user)
    plan = create_test_plan(owner=reporter)
    Participation.objects.create(plan=plan, user=reported_user)
    conversation = create_test_conversation(reporter, reported_user)
    message = Message.objects.create(
        conversation=conversation,
        sender=reported_user,
        body="Synthetic report context",
    )
    Block.objects.create(blocker=reported_user, blocked_user=reporter)
    form = PrivateReportForm(
        data={
            "category": Report.Category.HARASSMENT,
            "description": "A bounded private statement.",
        }
    )
    assert form.is_valid(), form.errors
    report_details = dict(form.cleaned_data)
    report_details.update(
        {
            "reporter": reported_user,
            "reported_user": reporter,
            "status": Report.Status.REVIEWED,
            "received_at": timezone.now() - timezone.timedelta(days=1),
        }
    )

    reports = [
        submit_private_report_about_user(reporter, reported_user, report_details),
        submit_private_report_about_user(
            reporter,
            reported_user,
            report_details,
            reported_plan=plan,
        ),
        submit_private_report_about_user(
            reporter,
            reported_user,
            report_details,
            reported_conversation=conversation,
        ),
        submit_private_report_about_user(
            reporter,
            reported_user,
            report_details,
            reported_message=message,
        ),
    ]

    assert Report.objects.count() == 4
    assert all(report.reporter == reporter for report in reports)
    assert all(report.reported_user == reported_user for report in reports)
    assert all(report.status == Report.Status.RECEIVED for report in reports)
    assert reports[0].reported_plan_id is None
    assert reports[1].reported_plan == plan
    assert reports[2].reported_conversation == conversation
    assert reports[3].reported_message == message
    reported_user_summary = get_signed_in_user_account_summary(reported_user)
    assert "reports" not in reported_user_summary

    # WHY: Refuses context that does not connect both named people to the same saved event.
    unrelated_plan = create_test_plan(owner=create_test_user())
    with pytest.raises(PermissionDenied):
        submit_private_report_about_user(
            reporter,
            reported_user,
            form.cleaned_data,
            reported_plan=unrelated_plan,
        )
    # WHY: Refuses a report that tries to attach more than one kind of evidence.
    with pytest.raises(PermissionDenied):
        submit_private_report_about_user(
            reporter,
            reported_user,
            form.cleaned_data,
            reported_conversation=conversation,
            reported_message=message,
        )


# WHY: Proves a received plan-chat message can be reported without accepting another sender or hidden chat as evidence.
def test_plan_chat_message_reporting_requires_authorised_received_context():
    owner = create_test_user()
    create_verified_test_profile(user=owner, display_name="Report plan owner")
    reporter = create_test_user()
    create_verified_test_profile(user=reporter, display_name="Plan reporter")
    target = create_test_user()
    target_profile = create_verified_test_profile(
        user=target,
        display_name="Reported participant",
    )
    outsider = create_test_user()
    create_verified_test_profile(user=outsider, display_name="Hidden reporter")
    plan = create_test_plan(
        owner=owner,
        status=Plan.Status.APPROVED,
        title="Reportable plan chat",
        capacity=3,
    )
    chat = None
    for participant in (reporter, target):
        participation, _conversation = (
            request_plan_participation_and_open_owner_conversation(participant, plan)
        )
        _participation, chat = confirm_requested_plan_participation(
            owner,
            plan,
            participation.pk,
        )
    received_message = send_plan_chat_message(target, chat, "Reportable group words")
    own_message = send_plan_chat_message(reporter, chat, "Reporter own words")
    report_url = reverse("report_create", args=[target_profile.pk])
    reporter_client = Client()
    reporter_client.force_login(reporter)
    chat_page = reporter_client.get(reverse("plan_chat_detail", args=[plan.pk]))
    assert chat_page.content.count(b"Report this message") == 1
    assert f"context_id={received_message.pk}".encode() in chat_page.content
    assert f"context_id={own_message.pk}".encode() not in chat_page.content

    report_response = reporter_client.post(
        report_url,
        {
            "category": Report.Category.SAFETY_CONCERN,
            "description": "Private plan chat concern.",
            "context_type": "plan_chat_message",
            "context_id": str(received_message.pk),
        },
    )
    assert report_response.status_code == 200
    saved_report = Report.objects.get()
    assert saved_report.reported_plan_chat_message == received_message
    assert saved_report.reported_user == target

    outsider_client = Client()
    outsider_client.force_login(outsider)
    refused = outsider_client.post(
        report_url,
        {
            "category": Report.Category.OTHER,
            "description": "Must not reveal a hidden group message.",
            "context_type": "plan_chat_message",
            "context_id": str(received_message.pk),
        },
    )
    assert refused.status_code == 404
    assert Report.objects.count() == 1


# WHY: Proves blocking revokes the correct current plan memberships and chat access for every relationship.
def test_blocking_removes_owner_participant_and_shared_participant_chat_access():
    owner = create_test_user()
    create_verified_test_profile(user=owner)
    first = create_test_user()
    create_verified_test_profile(user=first)
    second = create_test_user()
    create_verified_test_profile(user=second)
    plan = create_test_plan(
        owner=owner,
        status=Plan.Status.APPROVED,
        capacity=3,
    )
    participations = {}
    for participant in (first, second):
        participation, _conversation = (
            request_plan_participation_and_open_owner_conversation(participant, plan)
        )
        participations[participant.pk], _chat = confirm_requested_plan_participation(
            owner,
            plan,
            participation.pk,
        )

    block_user_from_discovery_and_messages(first, second)
    participations[first.pk].refresh_from_db()
    participations[second.pk].refresh_from_db()
    assert participations[first.pk].status == Participation.Status.LEFT
    assert participations[second.pk].status == Participation.Status.JOINED
    first_client = Client()
    first_client.force_login(first)
    assert first_client.get(reverse("plan_chat_detail", args=[plan.pk])).status_code == 404

    second_plan = create_test_plan(
        owner=owner,
        status=Plan.Status.APPROVED,
        capacity=2,
        title="Owner blocks participant",
    )
    second_request, _conversation = (
        request_plan_participation_and_open_owner_conversation(second, second_plan)
    )
    second_participation, _chat = confirm_requested_plan_participation(
        owner,
        second_plan,
        second_request.pk,
    )
    block_user_from_discovery_and_messages(owner, second)
    second_participation.refresh_from_db()
    assert second_participation.status == Participation.Status.LEFT
    second_client = Client()
    second_client.force_login(second)
    assert (
        second_client.get(reverse("plan_chat_detail", args=[second_plan.pk])).status_code
        == 404
    )

    third = create_test_user()
    create_verified_test_profile(user=third)
    third_plan = create_test_plan(
        owner=owner,
        status=Plan.Status.APPROVED,
        capacity=2,
        title="Participant blocks owner",
    )
    third_request, _conversation = (
        request_plan_participation_and_open_owner_conversation(third, third_plan)
    )
    third_participation, _chat = confirm_requested_plan_participation(
        owner,
        third_plan,
        third_request.pk,
    )
    block_user_from_discovery_and_messages(third, owner)
    third_participation.refresh_from_db()
    assert third_participation.status == Participation.Status.LEFT
