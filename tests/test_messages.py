"""Test Kindelise message and notification behaviour."""

# KEYWORD: test — an automatic check that proves one expected behaviour still works.
# KEYWORD: assert — compares the actual result with the result the check expects.
# KEYWORD: monkeypatch — temporarily replaces a setting or outside call for one check, then restores it.
# KEYWORD: HTTP — the request-and-response rules used when these checks visit a page.
# KEYWORD: CSRF — the private form check that prevents another website submitting as the signed-in visitor.
# KEYWORD: PostgreSQL — the database used by the live site to keep saved information and its rules.

import json
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from types import SimpleNamespace

import pytest
from django.contrib.auth import get_user_model
from django.db import (
    close_old_connections,
    connections,
)
from django.test import Client, TransactionTestCase
from django.urls import reverse
from django.utils import timezone

import kindlelise.ai_message_editor as ai_message_editor
from kindlelise.ai_message_editor import get_edited_message_draft_suggestion
from kindlelise.models import (
    Block,
    Conversation,
    Message,
    Notification,
    Plan,
)
from kindlelise.services import (
    find_or_start_direct_conversation,
    join_approved_plan_and_lock_meeting_details,
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


# WHY: Checks that direct conversation http starts from authorised profile once with csrf so a future change cannot quietly break it.


# WHY: Checks that direct conversation http starts from authorised profile once with csrf so a future change cannot quietly break it.
def test_direct_conversation_http_starts_from_authorised_profile_once_with_csrf():
    viewer = create_test_user()
    create_verified_test_profile(user=viewer, display_name="Message starter")
    target = create_test_user()
    target_profile = create_verified_test_profile(
        user=target,
        display_name="Message target",
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
    assert b"Send Message" in profile_response.content
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


# WHY: Checks that notification badge counts messages and plan joins then marks them read so a future change cannot quietly break it.
def test_notification_badge_counts_messages_and_plan_joins_then_marks_them_read():
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
    participation = join_approved_plan_and_lock_meeting_details(participant, plan)

    assert set(
        Notification.objects.filter(recipient=owner).values_list("kind", flat=True)
    ) == {Notification.Kind.MESSAGE, Notification.Kind.PLAN_JOIN}
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
    assert b"Plan participant joined Notification plan" in response.content

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


# WHY: Checks that conversation http escapes ordered messages and shares one hidden 404 so a future change cannot quietly break it.
def test_conversation_http_escapes_ordered_messages_and_shares_one_hidden_404():
    viewer = create_test_user()
    create_verified_test_profile(user=viewer)
    other_user = create_test_user()
    create_verified_test_profile(user=other_user, display_name="Conversation peer")
    outsider = create_test_user()
    create_verified_test_profile(user=outsider)
    conversation = create_test_conversation(viewer, other_user)
    first_message = Message.objects.create(
        conversation=conversation,
        sender=other_user,
        body="First <script>alert('private')</script>",
        sent_at=timezone.now() - timezone.timedelta(minutes=1),
    )
    second_message = Message.objects.create(
        conversation=conversation,
        sender=viewer,
        body="Second ordinary message",
    )
    client = Client()
    client.force_login(viewer)

    response = client.get(reverse("conversation_detail", args=[conversation.pk]))

    assert response.status_code == 200
    escaped_first = b"First &lt;script&gt;alert(&#x27;private&#x27;)&lt;/script&gt;"
    assert escaped_first in response.content
    assert b"<script>" not in response.content
    assert response.content.find(escaped_first) < response.content.find(
        second_message.body.encode()
    )
    expected_sent_at = timezone.localtime(first_message.sent_at).strftime(
        "%Y-%m-%dT%H:%M:%S"
    )
    assert f'datetime="{expected_sent_at}"'.encode() in response.content
    assert b"Conversation peer" in response.content
    assert (
        client.post(reverse("conversation_detail", args=[conversation.pk])).status_code
        == 405
    )

    outsider_client = Client()
    outsider_client.force_login(outsider)
    unrelated_response = outsider_client.get(
        reverse("conversation_detail", args=[conversation.pk])
    )
    missing_response = client.get(reverse("conversation_detail", args=[999999]))
    Block.objects.create(blocker=other_user, blocked_user=viewer)
    blocked_response = client.get(
        reverse("conversation_detail", args=[conversation.pk])
    )
    assert {
        unrelated_response.status_code,
        missing_response.status_code,
        blocked_response.status_code,
    } == {404}
    assert {
        unrelated_response.content,
        missing_response.content,
        blocked_response.content,
    } == {b"Conversation unavailable."}
    assert first_message.body.encode() not in blocked_response.content


# WHY: Checks that conversation send http rechecks csrf form sender and current access so a future change cannot quietly break it.
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


# WHY: Keeps the ConversationPairRaceTests information and its rules together so they stay consistent.
class ConversationPairRaceTests(TransactionTestCase):
    """Prove PostgreSQL uniqueness resolves simultaneous pair creation once."""

    # WHY: Keeps the setUp steps in one named place so they can be understood, checked, and reused.
    def setUp(self):
        self.first_user = create_test_user()
        create_verified_test_profile(user=self.first_user)
        self.second_user = create_test_user()
        create_verified_test_profile(user=self.second_user)

    # WHY: Checks that conversation pair race returns one database authoritative row so a future change cannot quietly break it.
    def test_conversation_pair_race_returns_one_database_authoritative_row(self):
        start_together = Barrier(2)

        # WHY: Keeps the start conversation steps in one named place so they can be understood, checked, and reused.
        def start_conversation(user_id, other_user_id):
            close_old_connections()
            try:
                user = get_user_model().objects.get(pk=user_id)
                other_user = get_user_model().objects.get(pk=other_user_id)
                start_together.wait(timeout=5)
                return find_or_start_direct_conversation(user, other_user).pk
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as executor:
            outcomes = list(
                executor.map(
                    lambda pair: start_conversation(*pair),
                    (
                        (self.first_user.pk, self.second_user.pk),
                        (self.second_user.pk, self.first_user.pk),
                    ),
                )
            )

        self.assertEqual(outcomes[0], outcomes[1])
        self.assertEqual(Conversation.objects.count(), 1)
        conversation = Conversation.objects.get()
        self.assertEqual(conversation.first_user_id, self.first_user.pk)
        self.assertEqual(conversation.second_user_id, self.second_user.pk)


# WHY: Checks that ollama editor sends only bounded draft and each fixed goal so a future change cannot quietly break it.
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


# WHY: Checks that ollama provider failure returns quiet error without sending so a future change cannot quietly break it.
def test_ollama_provider_failure_returns_quiet_error_without_sending(
    monkeypatch,
):
    sender = create_test_user()
    create_verified_test_profile(user=sender)
    recipient = create_test_user()
    create_verified_test_profile(user=recipient)
    conversation = create_test_conversation(sender, recipient)
    monkeypatch.setattr(
        "kindlelise.views.messages.get_edited_message_draft_suggestion",
        lambda draft, editing_goal: None,
    )
    client = Client()
    client.force_login(sender)

    response = client.post(
        reverse(
            "conversation_message_edit_suggestion",
            args=[conversation.pk],
        ),
        {
            "draft": "Original draft remains in the browser",
            "editing_goal": "improve_clarity",
        },
    )

    assert response.status_code == 503
    assert response.json() == {"error": "Draft edit unavailable."}
    assert not Message.objects.filter(conversation=conversation).exists()
