"""Test Kindelise message and notification behaviour."""

import json
from types import SimpleNamespace

import pytest
from django.test import Client
from django.urls import reverse

import kindlelise.ai_message_editor as ai_message_editor
from kindlelise.ai_message_editor import get_edited_message_draft_suggestion
from kindlelise.models import (
    Block,
    Conversation,
    Message,
    Notification,
    Participation,
    Plan,
    PlanChat,
    PlanChatMessage,
    Profile,
)
from kindlelise.services import (
    confirm_requested_plan_participation,
    request_plan_participation_and_open_owner_conversation,
    send_direct_message,
)
from tests.conftest import (
    create_test_conversation,
    create_test_plan,
    create_test_user,
    create_verified_test_profile,
    replace_ollama_request_with_fake,
)

pytestmark = pytest.mark.django_db


def test_plan_chat_http_reuses_shared_thread_and_revokes_then_restores_access():
    owner = create_test_user()
    create_verified_test_profile(user=owner, display_name="Plan owner")
    participant = create_test_user()
    create_verified_test_profile(user=participant, display_name="Confirmed person")
    pending_user = create_test_user()
    create_verified_test_profile(user=pending_user, display_name="Pending person")
    outsider = create_test_user()
    create_verified_test_profile(user=outsider, display_name="Unrelated person")
    plan = create_test_plan(
        owner=owner,
        status=Plan.Status.APPROVED,
        title="Shared walking plan",
        capacity=3,
    )
    participation, _conversation = (
        request_plan_participation_and_open_owner_conversation(participant, plan)
    )
    confirmed_participation, chat = confirm_requested_plan_participation(
        owner,
        plan,
        participation.pk,
    )
    pending_participation, _pending_conversation = (
        request_plan_participation_and_open_owner_conversation(pending_user, plan)
    )
    chat_url = reverse("plan_chat_detail", args=[plan.pk])
    send_url = reverse("plan_chat_message_send", args=[plan.pk])

    owner_client = Client()
    owner_client.force_login(owner)
    participant_client = Client()
    participant_client.force_login(participant)
    assert owner_client.get(chat_url).status_code == 200
    participant_page = participant_client.get(chat_url)
    assert participant_page.status_code == 200
    assert b"Shared walking plan" in participant_page.content
    assert b"Keep personal information private" in participant_page.content
    assert owner_client.post(send_url, {"body": "Owner welcome"}).status_code == 302

    pending_client = Client()
    pending_client.force_login(pending_user)
    outsider_client = Client()
    outsider_client.force_login(outsider)
    assert pending_client.get(chat_url).status_code == 404
    assert pending_client.post(send_url, {"body": "not permitted"}).status_code == 404
    assert outsider_client.get(chat_url).status_code == 404

    sent_response = participant_client.post(
        send_url,
        {"body": "Hello <script>alert('no')</script>", "sender": owner.pk},
    )
    saved_message = PlanChatMessage.objects.get(body__startswith="Hello")
    assert sent_response.status_code == 302
    assert sent_response.url == chat_url
    assert saved_message.sender == participant
    assert saved_message.body == "Hello <script>alert('no')</script>"
    rendered = owner_client.get(chat_url)
    assert (
        b"Hello &lt;script&gt;alert(&#x27;no&#x27;)&lt;/script&gt;" in rendered.content
    )
    assert b"<script>alert" not in rendered.content

    leave_response = participant_client.post(reverse("plan_leave", args=[plan.pk]))
    assert leave_response.status_code == 302
    assert participant_client.get(chat_url).status_code == 404
    assert (
        participant_client.post(send_url, {"body": "after leaving"}).status_code == 404
    )

    participant_client.post(reverse("plan_participation_request", args=[plan.pk]))
    confirmed_participation.refresh_from_db()
    assert confirmed_participation.status == Participation.Status.PENDING
    _participation, restored_chat = confirm_requested_plan_participation(
        owner,
        plan,
        confirmed_participation.pk,
    )
    assert restored_chat == chat
    restored_page = participant_client.get(chat_url)
    assert restored_page.status_code == 200
    assert b"Hello &lt;script&gt;alert" in restored_page.content
    assert PlanChat.objects.filter(plan=plan).count() == 1
    assert pending_participation.status == Participation.Status.PENDING

    owner_client.post(reverse("plan_cancel", args=[plan.pk]))
    read_only_page = participant_client.get(chat_url)
    assert read_only_page.status_code == 200
    assert b"This plan chat is now read-only" in read_only_page.content
    assert b'id="message-composer"' not in read_only_page.content
    assert participant_client.post(send_url, {"body": "too late"}).status_code == 404


def test_direct_conversation_http_starts_from_authorised_profile_once_with_csrf():
    viewer = create_test_user()
    Profile.objects.create(
        user=viewer,
        display_name="Message starter",
        broad_area="central",
        broad_areas=["central"],
    )
    target = create_test_user()
    target_profile = Profile.objects.create(
        user=target,
        display_name="Message target",
        broad_area="central",
        broad_areas=["central"],
    )
    blocked_target = create_test_user()
    blocked_profile = create_verified_test_profile(
        user=blocked_target,
        display_name="Hidden blocked target",
    )
    Block.objects.create(blocker=blocked_target, blocked_user=viewer)
    client = Client(enforce_csrf_checks=True)
    client.force_login(viewer)

    profile_response = client.get(reverse("profile_detail", args=[target_profile.pk]))
    start_url = reverse("direct_conversation_start", args=[target_profile.pk])
    assert profile_response.status_code == 200
    assert start_url.encode() in profile_response.content
    assert b"Send message" in profile_response.content
    assert client.get(start_url).status_code == 405

    missing_csrf_response = client.post(start_url)
    assert missing_csrf_response.status_code == 403
    assert not Conversation.objects.exists()

    csrf_token = client.cookies["csrftoken"].value
    start_response = client.post(
        start_url,
        {"csrfmiddlewaretoken": csrf_token, "recipient": blocked_target.pk},
        HTTP_REFERER=f"http://testserver{profile_response.request['PATH_INFO']}",
    )
    conversation = Conversation.objects.get()
    assert start_response.status_code == 302
    assert start_response.url == reverse(
        "conversation_detail",
        args=[conversation.pk],
    )
    assert {conversation.first_user_id, conversation.second_user_id} == {
        viewer.pk,
        target.pk,
    }

    repeated_response = client.post(
        start_url,
        {"csrfmiddlewaretoken": csrf_token},
        HTTP_REFERER=f"http://testserver{profile_response.request['PATH_INFO']}",
    )
    assert repeated_response.url == start_response.url
    assert Conversation.objects.count() == 1

    hidden_response = client.post(
        reverse("direct_conversation_start", args=[blocked_profile.pk]),
        {"csrfmiddlewaretoken": csrf_token},
        HTTP_REFERER=f"http://testserver{profile_response.request['PATH_INFO']}",
    )
    missing_response = client.post(
        reverse("direct_conversation_start", args=[999999]),
        {"csrfmiddlewaretoken": csrf_token},
        HTTP_REFERER=f"http://testserver{profile_response.request['PATH_INFO']}",
    )
    assert hidden_response.status_code == missing_response.status_code == 404
    assert (
        hidden_response.content == missing_response.content == b"Profile unavailable."
    )
    assert Conversation.objects.count() == 1


def test_notification_badge_counts_messages_requests_and_decisions_then_marks_read():
    owner = create_test_user()
    create_verified_test_profile(user=owner, display_name="Plan owner")
    participant = create_test_user()
    create_verified_test_profile(user=participant, display_name="Plan participant")
    plan = create_test_plan(
        owner=owner,
        status=Plan.Status.APPROVED,
        title="Notification plan",
    )
    conversation = create_test_conversation(owner, participant)

    message = send_direct_message(participant, conversation, "New message")
    participation, reused_conversation = (
        request_plan_participation_and_open_owner_conversation(participant, plan)
    )
    assert reused_conversation == conversation

    assert set(
        Notification.objects.filter(recipient=owner).values_list("kind", flat=True)
    ) == {Notification.Kind.MESSAGE, Notification.Kind.PLAN_REQUEST}
    assert Notification.objects.get(message=message).recipient == owner
    assert Notification.objects.get(participation=participation).recipient == owner
    assert not Notification.objects.filter(recipient=participant).exists()

    client = Client()
    client.force_login(owner)
    response = client.get(reverse("notifications"))

    assert response.status_code == 200
    assert b'class="site-notification-count"' in response.content
    assert b">2</span>" in response.content
    assert b"Message from Plan participant" in response.content
    assert b"Plan participant asked to join Notification plan" in response.content

    assert client.get(reverse("notifications_read")).status_code == 405
    read_response = client.post(reverse("notifications_read"))
    assert read_response.status_code == 302
    assert read_response.url == reverse("notifications")
    assert not Notification.objects.filter(
        recipient=owner, read_at__isnull=True
    ).exists()
    assert (
        b'class="site-notification-count"'
        not in client.get(reverse("notifications")).content
    )

    confirm_requested_plan_participation(owner, plan, participation.pk)
    participant_client = Client()
    participant_client.force_login(participant)
    decision_response = participant_client.get(reverse("notifications"))
    assert b">1</span>" in decision_response.content
    assert (
        b"Your participation in Notification plan was confirmed"
        in decision_response.content
    )


def test_conversation_send_http_rechecks_csrf_form_sender_and_current_access(caplog):
    viewer = create_test_user()
    create_verified_test_profile(user=viewer)
    other_user = create_test_user()
    create_verified_test_profile(user=other_user, display_name="Send target")
    injected_sender = create_test_user()
    create_verified_test_profile(user=injected_sender)
    conversation = create_test_conversation(viewer, other_user)
    client = Client(enforce_csrf_checks=True)
    client.force_login(viewer)
    detail_url = reverse("conversation_detail", args=[conversation.pk])
    send_url = reverse("conversation_message_send", args=[conversation.pk])
    detail_response = client.get(detail_url)
    original_activity = conversation.updated_at

    assert client.get(send_url).status_code == 405
    assert client.post(send_url, {"body": "Missing CSRF"}).status_code == 403
    assert not Message.objects.filter(conversation=conversation).exists()

    csrf_token = client.cookies["csrftoken"].value
    invalid_response = client.post(
        send_url,
        {"csrfmiddlewaretoken": csrf_token, "body": "   "},
        HTTP_REFERER=f"http://testserver{detail_response.request['PATH_INFO']}",
    )
    assert invalid_response.status_code == 200
    assert b"This field is required" in invalid_response.content
    assert not Message.objects.filter(conversation=conversation).exists()

    private_body = "  <img src=x onerror=alert('private draft')>  "
    caplog.clear()
    send_response = client.post(
        send_url,
        {
            "csrfmiddlewaretoken": csrf_token,
            "body": private_body,
            "sender": injected_sender.pk,
        },
        HTTP_REFERER=f"http://testserver{detail_response.request['PATH_INFO']}",
    )
    stored_message = Message.objects.get(conversation=conversation)
    conversation.refresh_from_db()
    assert send_response.status_code == 302
    assert send_response.url == detail_url
    assert stored_message.sender == viewer
    assert stored_message.body == private_body.strip()
    assert conversation.updated_at == stored_message.sent_at
    assert conversation.updated_at >= original_activity
    assert private_body.strip() not in caplog.text

    rendered_response = client.get(detail_url)
    assert b"&lt;img src=x onerror=alert" in rendered_response.content
    assert b"<img src=x" not in rendered_response.content

    Block.objects.create(blocker=other_user, blocked_user=viewer)
    refused_response = client.post(
        send_url,
        {"csrfmiddlewaretoken": csrf_token, "body": "Blocked second message"},
        HTTP_REFERER=f"http://testserver{detail_response.request['PATH_INFO']}",
    )
    assert refused_response.status_code == 404
    assert refused_response.content == b"Conversation unavailable."
    assert Message.objects.filter(conversation=conversation).count() == 1


def test_ollama_editor_sends_only_bounded_draft_and_each_fixed_goal(
    monkeypatch,
    settings,
    caplog,
):
    settings.OLLAMA_API_URL = "https://ollama.test/api/generate"
    settings.OLLAMA_API_KEY = "ollama_test_synthetic_key"
    settings.OLLAMA_MODEL = "model-test-pinned"
    settings.OLLAMA_TIMEOUT_SECONDS = 3
    private_draft = "  i has a private synthetic draft  "
    private_suggestion = "I have a private synthetic draft."
    provider_response = SimpleNamespace(
        read=lambda byte_limit: json.dumps(
            {
                "model": "model-test-pinned",
                "response": f"  {private_suggestion}  ",
                "done": True,
            }
        ).encode(),
        close=lambda: None,
    )
    fake_request = replace_ollama_request_with_fake(
        monkeypatch,
        ai_message_editor,
        provider_response,
    )

    caplog.clear()
    grammar_suggestion = get_edited_message_draft_suggestion(
        private_draft,
        "fix_grammar",
    )
    clarity_suggestion = get_edited_message_draft_suggestion(
        private_draft,
        "improve_clarity",
    )

    assert grammar_suggestion == clarity_suggestion == private_suggestion
    assert len(fake_request.calls) == 2
    first_request, first_values = fake_request.calls[0]
    second_request, second_values = fake_request.calls[1]
    grammar_request = first_request[0]
    clarity_request = second_request[0]
    grammar_payload = json.loads(grammar_request.data)
    clarity_payload = json.loads(clarity_request.data)
    assert set(grammar_payload) == {"model", "prompt", "system", "stream"}
    assert grammar_payload["model"] == "model-test-pinned"
    assert grammar_payload["prompt"] == private_draft.strip()
    assert grammar_payload["stream"] is False
    assert grammar_payload["system"].startswith("Correct grammar only.")
    assert clarity_payload["system"].startswith("Improve clarity only.")
    assert "Do not rephrase or simplify." in grammar_payload["system"]
    assert "You may restructure sentences" in clarity_payload["system"]
    assert grammar_payload["system"] != clarity_payload["system"]
    assert grammar_request.full_url == "https://ollama.test/api/generate"
    assert grammar_request.get_method() == "POST"
    assert grammar_request.get_header("Authorization") == (
        "Bearer ollama_test_synthetic_key"
    )
    assert grammar_request.get_header("Content-type") == "application/json"
    assert first_values["timeout"] == second_values["timeout"] == 3
    serialized_payloads = grammar_request.data + clarity_request.data
    assert b"profile" not in serialized_payloads.lower()
    assert b"recipient" not in serialized_payloads.lower()
    assert b"conversation" not in serialized_payloads.lower()
    assert b"report" not in serialized_payloads.lower()
    assert private_draft.strip() not in caplog.text
    assert private_suggestion not in caplog.text
    assert "ollama_test_synthetic_key" not in caplog.text
