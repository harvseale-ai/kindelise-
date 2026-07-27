# TRACEABILITY

This matrix connects stable requirements to the policy/service owner, user-facing or system interface, and planned tests.

Rows may reference files that are still scaffold-only. A row is not considered complete until the implementation and tests both enforce the requirement.

| Requirement | Policy/service | Interface | Tests |
| --- | --- | --- | --- |
| IDV-001 | `apps/accounts/policies.py` | Verification gate | `tests/accounts/test_verification_gate.py` |
| IDV-002 | `apps/accounts/verification/base.py` | Verification result contract | `tests/accounts/test_verification_scope.py` |
| IDV-003 | `apps/accounts/selectors.py` | Public profile card | `tests/accounts/test_public_verified_face.py` |
| IDV-004 | `apps/accounts/policies.py` | Dark profile visibility | `tests/accounts/test_dark_profile_verification.py` |
| IDV-005 | `apps/accounts/verification/provider.py` | Staff/admin media access | `tests/accounts/test_verification_media_access.py` |
| IDV-006 | `apps/moderation/services/duplicate_accounts.py` | Suspension enforcement | `tests/moderation/test_suspended_person_block.py` |
| DSC-001 | `apps/discovery/selectors.py` | Proximity grid | `tests/discovery/test_profile_grid.py` |
| DSC-002 | `apps/discovery/views.py` | Discovery UI | `tests/discovery/test_no_swiping_or_matching.py` |
| DSC-003 | `apps/discovery/services/proximity.py` | Proximity grid | `tests/discovery/test_grid_ordering.py` |
| DSC-004 | `apps/discovery/services/filtering.py` | Discovery filters | `tests/discovery/test_filters.py` |
| DSC-005 | `apps/discovery/selectors.py` | Profile cards | `tests/discovery/test_profile_card_plans.py` |
| DSC-006 | `apps/discovery/selectors.py` | Discovery queryset | `tests/discovery/test_discovery_exclusions.py` |
| DSC-007 | `common/security/location_privacy.py` | Distance display | `tests/security/test_location_privacy.py` |
| PLN-001 | `apps/plans/policies.py` | Plan form | `tests/plans/test_public_url_required.py` |
| PLN-002 | `apps/plans/validators.py` | Plan form | `tests/plans/test_place_and_time_required.py` |
| PLN-003 | `apps/plans/services/create_plan.py` | Plan creation | `tests/plans/test_immediate_and_scheduled_plans.py` |
| PLN-004 | `apps/plans/policies.py` | Spare ticket/place option | `tests/plans/test_free_spare_place.py` |
| PLN-005 | `apps/plans/services/plan_expiry.py` | Expiry task | `tests/plans/test_plan_expiry.py` |
| PLN-006 | `common/security/safe_urls.py` | URL validation | `tests/security/test_safe_urls.py` |
| PAY-001 | `apps/plans/policies.py` | Host attestation | `tests/plans/test_payment_prohibition.py` |
| PAY-002 | `apps/plans/policies.py` | Plan creation and messaging policy | `tests/plans/test_compensation_requests.py` |
| PAY-003 | `apps/plans/policies.py` | Third-party cost disclosure | `tests/plans/test_third_party_costs.py` |
| PAY-004 | `apps/plans/policies.py` | Optional personal purchases | `tests/plans/test_optional_personal_purchases.py` |
| PAY-005 | `apps/safety/services/reporting.py` | Report action | `tests/safety/test_payment_reports.py` |
| MSG-001 | `apps/messaging/policies.py` | Direct message action | `tests/messaging/test_direct_contact.py` |
| MSG-002 | `apps/messaging/policies.py` | Meeting confirmation | `tests/messaging/test_confirmed_meeting_requires_plan.py` |
| MSG-003 | `apps/safety/services/blocking.py` | Block action | `tests/safety/test_block_visibility.py` |
| MSG-004 | `apps/messaging/services/message_safety.py` | Safety report submission | `tests/messaging/test_report_message_preservation.py` |
| MSG-005 | `apps/safety/policies.py` | Block/report privacy | `tests/safety/test_block_report_privacy.py` |
| SAF-001 | `apps/safety/services/check_ins.py` | Check-in modal | `tests/safety/test_check_in_schedule.py` |
| SAF-002 | `apps/safety/forms.py` | Check-in modal | `tests/safety/test_check_in_question.py` |
| SAF-003 | `apps/safety/forms.py` | Check-in modal | `tests/safety/test_check_in_responses.py` |
| SAF-004 | `apps/safety/views.py` | Safety options | `tests/safety/test_something_feels_off.py` |
| SAF-005 | `apps/safety/policies.py` | Check-in response access | `tests/safety/test_private_check_in_answers.py` |
| SAF-006 | `apps/accounts/views.py` | Public profile and meeting history | `tests/safety/test_no_public_reviews.py` |
| SAF-007 | `apps/plans/validators.py` | Plan creation | `tests/plans/test_public_url_verifiable_locations.py` |
| SAF-008 | `apps/safety/services/check_ins.py` | Check-in scheduling | `tests/safety/test_no_continuous_location_surveillance.py` |
| BCR-001 | `apps/safety/policies.py` | Safety-area access and absence of subject lookup | `tests/safety/test_no_experience_search.py` |
| BCR-002 | `apps/safety/services/reporting.py` | Firsthand-experience intake | `tests/safety/test_experience_qualification.py` |
| BCR-003 | `apps/safety/services/reporting.py` | Sealed experience and correction flow | `tests/safety/test_sealed_experience.py` |
| BCR-004 | `apps/safety/services/reporting.py` | Safety-purpose controls | `tests/safety/test_granular_processing_choices.py` |
| BCR-005 | `apps/notifications/services/web_push.py` and `email.py` | Private safety update | `tests/notifications/test_private_safety_preview.py` |
| BCR-006 | `apps/safety/policies.py` with `apps/moderation/services/risk_signals.py` | Circle invitation and entry | `tests/safety/test_circle_qualification_and_entry.py` |
| BCR-007 | `apps/safety/policies.py` and `apps/moderation/services/evidence.py` | Circle statement sharing | `tests/safety/test_circle_content_separation.py` |
| BCR-008 | `apps/safety/policies.py` | Circle member projection | `tests/safety/test_circle_pseudonymity.py` |
| BCR-009 | `apps/moderation/services/cases.py` | Circle and staff interfaces | `tests/moderation/test_circle_is_not_finding.py` |
| BCR-010 | `apps/moderation/services/risk_signals.py` | Matching and moderation priority | `tests/moderation/test_match_cannot_sanction.py` |
| BCR-011 | `apps/moderation/services/cases.py` and `sanctions.py` | Moderation finding and appeal | `tests/moderation/test_human_finding_and_appeal.py` |
| BCR-012 | `apps/safety/policies.py` and `common/security/audit.py` | Safety identity vault and access audit | `tests/security/test_safety_purpose_separation.py` |
| BCR-013 | `apps/safety/services/reporting.py` | Private safety dashboard | `tests/safety/test_contributor_controls_and_rights.py` |
| BCR-014 | `apps/safety/policies.py` and `config/settings/production.py` | Feature enablement | `tests/safety/test_blind_corroboration_launch_gate.py` |
| MOD-001 | `apps/safety/services/blocking.py` | Block action | `tests/safety/test_one_tap_blocking.py` |
| MOD-002 | `apps/moderation/services/cases.py` | Moderation queue | `tests/moderation/test_prioritised_queue.py` |
| MOD-003 | `apps/moderation/services/evidence.py` | Report handling | `tests/moderation/test_evidence_preservation.py` |
| MOD-004 | `common/security/audit.py` | Moderation action | `tests/moderation/test_immutable_audit_records.py` |
| MOD-005 | `apps/moderation/services/sanctions.py` | Appeal flow | `tests/moderation/test_suspension_appeals.py` |
| MOD-006 | `apps/moderation/services/risk_signals.py` | Urgent risk handling | `tests/moderation/test_temporary_suspension.py` |
