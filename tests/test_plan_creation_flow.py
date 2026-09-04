"""Focused non-database checks for the compact, review-before-save plan flow."""

import json

from django.utils import timezone

from kindlelise import ai_plan_drafter
from kindlelise.forms import PlanDetailsForm
from kindlelise.models import Plan


def test_new_plan_form_uses_exact_capacity_choices_and_empty_time():
    form = PlanDetailsForm(
        initial={"starts_at": [timezone.localdate().isoformat(), ""]}
    )

    assert list(form.fields["capacity"].choices) == [
        (value, str(value)) for value in range(1, 16)
    ]
    assert form.fields["capacity"].initial == 1
    rendered_start = str(form["starts_at"])
    assert f'value="{timezone.localdate().isoformat()}"' in rendered_start
    assert '<option value="" selected>Select a time</option>' in rendered_start
    assert f'min="{timezone.localdate().isoformat()}"' in rendered_start


def test_existing_larger_capacity_remains_available_only_for_that_plan():
    legacy_plan = Plan(pk=42, capacity=30)
    edit_form = PlanDetailsForm(instance=legacy_plan)

    assert list(edit_form.fields["capacity"].choices)[-1] == (
        30,
        "30 (current capacity)",
    )
    assert 30 not in dict(PlanDetailsForm().fields["capacity"].choices)


def test_plan_draft_uses_only_bounded_public_facts_and_returns_editable_fields(
    monkeypatch,
):
    captured = {}

    def fake_request(prompt, system_instruction, maximum_length):
        captured["prompt"] = json.loads(prompt)
        captured["system"] = system_instruction
        captured["maximum_length"] = maximum_length
        return json.dumps(
            {
                "title": "Mahjong at the public games café",
                "description": "Join me for a friendly game of mahjong.",
                "public_place": "Public Games Café",
                "public_address": "10 High Street, London",
                "date": (timezone.localdate() + timezone.timedelta(days=1)).isoformat(),
                "time": "19:00",
            }
        )

    monkeypatch.setattr(ai_plan_drafter, "request_ollama_text", fake_request)
    suggestion = ai_plan_drafter.get_plan_draft_suggestion(
        "I need three other mahjong players.",
        "https://events.example.test/mahjong",
        3,
        "Public Games Café",
        "10 High Street, London",
    )

    assert suggestion == {
        "title": "Mahjong at the public games café",
        "description": "Join me for a friendly game of mahjong.",
        "public_place": "Public Games Café",
        "public_address": "10 High Street, London",
        "date": (timezone.localdate() + timezone.timedelta(days=1)).isoformat(),
        "time": "19:00",
    }
    assert set(captured["prompt"]) == {
        "copied_event_text",
        "public_url",
        "venue_name_hint",
        "venue_address_hint",
        "people_who_can_join",
        "current_date",
    }
    assert captured["prompt"]["people_who_can_join"] == 3
    assert "exact number" in captured["system"]
    assert captured["maximum_length"] == 4_096


def test_plan_draft_rejects_unexpected_or_oversized_provider_output(monkeypatch):
    monkeypatch.setattr(
        ai_plan_drafter,
        "request_ollama_text",
        lambda *args: json.dumps(
            {"title": "Valid title", "description": "Valid", "extra": "No"}
        ),
    )
    assert (
        ai_plan_drafter.get_plan_draft_suggestion(
            "A walk", "https://events.example.test/walk", 2
        )
        is None
    )

    monkeypatch.setattr(
        ai_plan_drafter,
        "request_ollama_text",
        lambda *args: json.dumps(
            {
                "title": "x" * 121,
                "description": "Valid",
                "public_place": "Public park",
                "public_address": "",
                "date": "",
                "time": "",
            }
        ),
    )
    assert (
        ai_plan_drafter.get_plan_draft_suggestion(
            "A walk", "https://events.example.test/walk", 2
        )
        is None
    )
