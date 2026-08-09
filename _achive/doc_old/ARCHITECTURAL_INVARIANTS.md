# Kindlelise Architectural Invariants

## 1. Purpose of this document

Kindlelise currently contains an architectural scaffold. It reserves one predictable location for each responsibility; a scaffolded file is not evidence that its feature is implemented. The structure exists for navigation, ownership, and prevention of duplicate logic.

Future work must extend the designated file instead of creating competing `utils.py`, `helpers.py`, or alternative service locations. Executable code will be the final source of truth once implementation begins. This document is the source of truth for file placement and responsibility boundaries.

```text
Requirement
→ domain
→ responsibility
→ exact file
→ primary entry point
→ bounded result
→ next responsible file
```

This is a placement guide, not a runtime guide. It makes no claim that scaffolded workflows run.

## 2. Current implementation status

The original audit found 210 meaningful files. This document and `docs/WIREFRAMES.md` brought the inventory to 212 files; `docs/VERTICAL_SLICE.md` brings the current inventory to 213. Generated `.DS_Store`, `__pycache__/`, and `.pyc` files are excluded.

There is no implemented application behavior. Python files contain docstrings but no imports, classes, functions, settings, routes, or models. Templates, browser assets, deployment files, scripts, and tests are placeholders. `manage.py` performs no Django work and no automated test exists.

| Status | Meaning |
| --- | --- |
| Scaffold only | Reserves a responsibility; does not perform it. |
| Partially implemented | Performs part of its primary responsibility. No current file qualifies. |
| Implemented | Performs its primary responsibility. No current application file qualifies. |
| Tested | Implemented and protected by meaningful tests. No current file qualifies. |
| Configuration | Currently defines a repository convention. |
| Documentation | Contains substantive project documentation. |
| Static asset | Non-executable asset or asset placeholder. |
| Migration | Contains real database migration operations. No current file qualifies. |

Current totals: **213 meaningful files**, **198 scaffold-only files**, **0 implemented files**, **20 project-documentation files**, **16 configuration-boundary files**, **12 files under `static/`**, **7 migration-package placeholders**, and **15 files under `tests/`**. Location categories overlap content status; for example, a test-area README is still scaffold-only.

## 3. Central architectural invariant

> Every meaningful file has one clear responsibility, one primary public purpose, and an explicit boundary beyond which work must move to another named file.

A file may contain private helpers only when they support that one responsibility.

```text
product responsibility
→ Django domain
→ architectural layer
→ exact scaffold file
→ reserved responsibility
→ forbidden responsibilities
→ exact adjacent owner
```

## 4. How to read the scaffold

Start with `docs/REQUIREMENTS.md` for outcomes, `docs/PRODUCT_RULES.md` for invariants, this document for exact ownership, and `docs/TRACEABILITY.md` for planned coverage. Check the worktree before trusting a planned traceability path.

In the inventory, “entry” is a **planned** primary entry point unless the row is documentation, configuration, or an asset. Package initialisers have no behavioral entry point. Templates are render targets, never business authority.

## 5. Repository-wide invariants

1. One file owns one primary responsibility.
2. Private helpers support only that responsibility.
3. Business logic is not duplicated across views, forms, models, policies, and services.
4. Views coordinate HTTP work; they do not own multi-step workflows.
5. Forms bind and validate fields; they do not mutate domain state.
6. Services own named state-changing workflows.
7. Selectors perform read-only queries.
8. Policies decide whether an actor may act.
9. Permissions adapt policies to Django request/object boundaries without restating them.
10. Models define persistent state, constraints, and small model-local invariants.
11. Tasks and scripts invoke services; they do not duplicate service rules.
12. Templates and browser JavaScript are never business authority.
13. `common/security/` owns reusable technical security controls.
14. `apps/safety/` owns user-facing safety workflows.
15. Provider adapters translate external systems; they do not own product policy.
16. Tests mirror production responsibilities and contain no fake passing placeholders.
17. Scaffold-only modules stay labelled until executable behavior exists.
18. Do not add a module when an existing file already owns the work.
19. Out-of-scope work names an exact owner, never “elsewhere.”
20. Documentation distinguishes designed, scaffolded, implemented, and tested behavior.

## 6. Dependency-direction rules

```text
URLs
→ views
→ forms / permissions / policies
→ services
→ selectors / models / validators
→ technical or provider adapters

views → selectors → models
tasks → services
scripts → services
```

Prohibited:

```text
models importing views
services rendering templates
selectors mutating state
policies returning HTTP responses
tasks duplicating services
templates deciding permissions
JavaScript bypassing server validation
cross-domain circular imports
```

Cross-domain reads call the owning selector. Cross-domain mutations call the owning service.

## 7. Domain ownership map

All application domains are scaffold-only.

| Area | Owns | Must not own | May depend on / be called by |
| --- | --- | --- | --- |
| `accounts` | Account/profile state, onboarding, verification status, visibility, restrictions. | Discovery, plans, messages, reports, sanctions, URL security. | Account models/policies, security controls, verification adapter / any eligibility caller. |
| `discovery` | Read-only selection, filters, privacy-safe proximity and cards. | Mutations, precise location, messages, verification decisions. | Account/plan/interest reads, location privacy / discovery views. |
| `interests` | Controlled interest taxonomy. | Discovery ranking or profile/plan workflows. | Its models/admin / accounts, plans, discovery via contracts. |
| `plans` | Plan state, place, time, URL requirement, costs, joinability, expiry. | Verification, messaging, blocking, sanctions, network security. | Account eligibility, interests, safe URLs / views, discovery, messaging, tasks. |
| `messaging` | Conversations, messages, message-specific safety checks. | Plan permission, block state, findings, verification state. | Account/plan/block decisions / views and consumers. |
| `safety` | Blocking, experience/report intake, contributor choices and rights, private circle access, check-ins, urgent help, incidents, trusted contacts. | Rate limits, safe URLs, matching signals, adjudication, sanctions, verification providers. | Accounts, plans, messages, notifications, moderation / views and block/report callers. |
| `moderation` | Cases, evidence, signals, sanctions, appeals, duplicate investigation. | Report intake, messaging, discovery, plan creation. | Safety reports, restrictions, audit / staff views/admin. |
| `notifications` | Notification records, schedules, email/push attempts. | Domain decisions. | Domain-issued requests / tasks and delivery callers. |
| `common` | Shared primitives and reusable technical controls. | Product workflows or miscellaneous helpers. | Framework/technical libraries / all domains through narrow APIs. |
| `config` | Django settings, root URLs, ASGI/WSGI exposure. | Product rules. | Environment, Django, domain URLs / process entry points. |
| `templates` | Cross-domain pages and presentation fragments. | Permission, validation, mutation. | View context / Django renderer. |
| `static` | Styling, browser enhancement, PWA metadata/assets. | Server authority or persistent state. | DOM and server-enforced endpoints / browser. |
| `tests` | Future fixtures and behavioral verification. | Production behavior or fake tests. | Public behavior / test runner. |
| `deployment` | Image, topology, startup, proxy. | Domain rules or secrets. | Built app/environment / deployment tools. |
| `scripts` | Thin seed and expiry operator entry points. | Domain rules or direct-model bypass. | Public services / operators. |
| `docs` | Requirements, decisions, architecture, placement, traceability. | Unsupported implementation claims. | Worktree and reviewed decisions / humans. |

## 8. Cross-domain boundaries

- **Accounts:** calls `apps/discovery/selectors.py` for discovery, `apps/plans/services/create_plan.py` for plans, `apps/messaging/services/messages.py` for messages, `apps/safety/services/reporting.py` for reports, `apps/moderation/services/sanctions.py` for sanctions, and `common/security/safe_urls.py` for URL security.
- **Discovery:** reads accounts through `apps/accounts/selectors.py`, plans through `apps/plans/selectors.py`, interests through `apps/interests/selectors.py`, and privacy rules through `common/security/location_privacy.py`. It never mutates them.
- **Plans:** hands verification to `apps/accounts/policies.py`, messaging to `apps/messaging/services/messages.py`, blocking to `apps/safety/services/blocking.py`, sanctions to `apps/moderation/services/sanctions.py`, and technical URL checks to `common/security/safe_urls.py`.
- **Messaging:** hands plan permission to `apps/plans/policies.py`, block authority to `apps/safety/services/blocking.py`, findings to `apps/moderation/services/cases.py`, and verification state to `apps/accounts/services/face_verification.py`.
- **Safety:** hands rate limiting to `common/security/rate_limits.py`, URL parsing to `common/security/safe_urls.py`, blind matching and independence signals to `apps/moderation/services/risk_signals.py`, evidence custody to `apps/moderation/services/evidence.py`, adjudication to `apps/moderation/services/cases.py`, and provider work to `apps/accounts/verification/provider.py`.
- **Moderation:** receives report intake from `apps/safety/services/reporting.py`; it never sends messages, builds discovery, or creates plans.
- **Notifications:** acts only after a requesting domain decides that delivery is needed. Plan validity, report findings, sanctions, and message permission stay in their domain policies/services.

## 9. Safety and authority boundaries

| Invariant | Intended owner |
| --- | --- |
| Client validation is not server permission. | Relevant domain `policies.py`; request adaptation in view/permission file. |
| Face verification is not proof of good intent. | `apps/accounts/verification/base.py` and truthful `templates/components/verification_badge.html`. |
| Approximate proximity is not permission to expose precise location. | `common/security/location_privacy.py` then `apps/discovery/services/proximity.py`. |
| A public URL is not proof that a user owns a ticket. | `apps/plans/policies.py`; technical safety in `common/security/safe_urls.py`. |
| A plan invitation is not consent to unrelated contact. | `apps/messaging/policies.py`. |
| Messaging permission never overrides a block. | `apps/safety/services/blocking.py`, enforced by `apps/messaging/policies.py`. |
| A report is evidence for review, not a finding. | Intake: `apps/safety/services/reporting.py`; finding: `apps/moderation/services/cases.py`. |
| A sealed experience is a contributor's claim, not a fact about the subject. | Intake: `apps/safety/services/reporting.py`; protected persistence: `apps/safety/models.py`. |
| A match is neither corroborated fact nor permission to disclose another contributor. | Match: `apps/moderation/services/risk_signals.py`; disclosure choice/access: `apps/safety/policies.py`. |
| A Shared Experience Circle is peer support, not an investigation or finding. | Access: `apps/safety/policies.py`; findings: `apps/moderation/services/cases.py`. |
| Matching cannot automatically create a significant adverse decision. | `risk_signals.py` may prioritise; `cases.py` records human findings; `sanctions.py` applies appealable action. |
| A signal is not a sanction. | `risk_signals.py` records; `sanctions.py` decides/applies. |
| A notification is not a domain decision. | Requesting domain decides; `apps/notifications/` delivers. |
| A saved record is not proof its contents are true. | Owning `models.py` stores; owning policy/moderation service interprets. |

## 10. Complete current file inventory

“Owns” is reserved when status is Scaffold only. “Handoff” is the exact owner of adjacent work.

### Root, packages, configuration, deployment and scripts

| File | Status | Reserved responsibility | May depend on | Must not own | Out-of-scope owner | Planned primary entry point |
| --- | --- | --- | --- | --- | --- | --- |
| `.env.example` | Scaffold only | Public environment-name contract. | Settings/deployment needs. | Secrets or rules. | `config/settings/base.py`; `deployment/compose.yml`. | Environment names; planned. |
| `.gitignore` | Configuration | Ignore generated, secret, local files. | Tool conventions. | Runtime config. | `.env.example`. | Ignore patterns. |
| `ARCHITECTURE.md` | Documentation | Duplicate architecture copy. | Decisions. | Competing authority. | Likely `docs/ARCHITECTURE.md`. | Document. |
| `README.md` | Documentation | Repository introduction/setup navigation. | Worktree/docs. | Absent behavior claims. | `docs/ARCHITECTURE.md`; `docs/DEPLOYMENT.md`. | Landing page. |
| `manage.py` | Scaffold only | Django CLI boundary. | `config/settings/`. | Domain work. | Owning service. | `execute_from_command_line`; planned. |
| `pyproject.toml` | Scaffold only | Dependencies/tool configuration. | Tool decisions. | App settings. | `config/settings/base.py`. | TOML tables; planned. |
| `apps/__init__.py` | Scaffold only | Application namespace package. | None. | Side effects. | Each domain package. | None. |
| `common/__init__.py` | Scaffold only | Shared-infrastructure package. | None. | Generic behavior. | Exact `common/` file. | None. |
| `config/__init__.py` | Scaffold only | Configuration package. | None. | Settings values. | Exact `config/` file. | None. |
| `config/asgi.py` | Scaffold only | ASGI application/protocol composition. | Settings; messaging routing. | Message behavior. | `apps/messaging/consumers.py`. | `application`; planned. |
| `config/settings/__init__.py` | Scaffold only | Settings package boundary. | Settings modules. | Implicit environment selection. | `base.py` plus override. | None. |
| `config/settings/base.py` | Scaffold only | Environment-neutral Django settings. | Environment/Django. | Domain rules. | Domain `policies.py`. | Setting constants; planned. |
| `config/settings/development.py` | Scaffold only | Local-only setting overrides. | `base.py`. | Production/rules. | `production.py`; domain owner. | Overrides; planned. |
| `config/settings/production.py` | Scaffold only | Secure production overrides/checks. | `base.py`, environment. | Topology/rules. | `deployment/compose.yml`. | Overrides; planned. |
| `config/settings/testing.py` | Scaffold only | Deterministic test overrides. | `base.py`. | Test behavior. | `tests/conftest.py`. | Overrides; planned. |
| `config/urls.py` | Scaffold only | Compose root URL patterns. | Domain `urls.py`. | Domain routes/views. | Exact domain `urls.py`. | `urlpatterns`; planned. |
| `config/wsgi.py` | Scaffold only | WSGI application boundary. | Settings/Django. | Domain/proxy work. | Domain services; `nginx.conf`. | `application`; planned. |
| `deployment/Dockerfile` | Scaffold only | Build application image. | `pyproject.toml`. | Topology/rules. | `compose.yml`; domain services. | Build stages; planned. |
| `deployment/compose.yml` | Scaffold only | Service topology/environment wiring. | Image/env contract. | Secrets/app rules. | Secret manager; `production.py`. | Services; planned. |
| `deployment/entrypoint.sh` | Scaffold only | Bounded container startup. | Image/Django CLI. | Migration/domain rules. | Migrations; domain services. | Shell entry; planned. |
| `deployment/nginx.conf` | Scaffold only | Reverse proxy/static boundary. | Deployed endpoints. | Auth/domain routing. | `config/urls.py`; policies. | Nginx config; planned. |
| `scripts/expire_plans.py` | Scaffold only | Thin expiry operator command. | Expiry service. | Expiry rules/direct writes. | `apps/plans/services/plan_expiry.py`. | `main()`; planned. |
| `scripts/seed_demo_profiles.py` | Scaffold only | Seed non-production profiles via services. | Account services. | Real-verification claims/direct writes. | `onboarding.py`; `face_verification.py`. | `main()`; planned. |
| `scripts/seed_interests.py` | Scaffold only | Seed taxonomy via service. | Interest service. | Direct writes/rules. | `apps/interests/services.py`. | `main()`; planned. |

### Accounts

| File | Status | Reserved responsibility | May depend on | Must not own | Out-of-scope owner | Planned primary entry point |
| --- | --- | --- | --- | --- | --- | --- |
| `apps/accounts/__init__.py` | Scaffold only | Accounts package. | Metadata. | Workflows. | `services/`. | None. |
| `apps/accounts/admin.py` | Scaffold only | Register controlled account admin. | Models/policies. | Verification/sanctions. | `face_verification.py`; `moderation/services/sanctions.py`. | Admin registrations; planned. |
| `apps/accounts/forms.py` | Scaffold only | Bind account/profile form fields. | Policies/presentation. | Mutation/permissions. | `onboarding.py`; `policies.py`. | Form classes; planned. |
| `apps/accounts/migrations/__init__.py` | Scaffold only | Migration package, not migration. | Django discovery. | Operations/models. | Future migration after `models.py`. | None. |
| `apps/accounts/models.py` | Scaffold only | Persist accounts, profiles, verification state. | ORM/shared primitives. | HTTP/provider/discovery. | `views.py`; `verification/provider.py`; `discovery/selectors.py`. | Model classes; planned. |
| `apps/accounts/permissions.py` | Scaffold only | Adapt account policies to Django access. | `policies.py`. | Restating policy/HTTP. | `policies.py`; `views.py`. | Permission classes; planned. |
| `apps/accounts/policies.py` | Scaffold only | Decide participation/profile eligibility. | Account/restriction state. | HTTP/mutation/provider. | `views.py`; account services; provider. | `can_participate()`; planned. |
| `apps/accounts/selectors.py` | Scaffold only | Side-effect-free account/profile reads. | `models.py`. | Mutation/ranking/media exposure. | Account services; `discovery/selectors.py`. | `get_public_profile()`; planned. |
| `apps/accounts/services/__init__.py` | Scaffold only | Deliberate account-service exports. | Named services. | Implementation. | Exact service file. | Exports; planned. |
| `apps/accounts/services/account_restrictions.py` | Scaffold only | Apply/lift authorised restrictions. | Models/policies/audit. | Adjudication/HTTP. | `moderation/services/sanctions.py`; `views.py`. | `apply_account_restriction()`; planned. |
| `apps/accounts/services/face_verification.py` | Scaffold only | Coordinate verification attempt/outcome. | Models/policies/interface. | Provider transport/good-intent claims. | `verification/provider.py`; `verification/base.py`. | `start_face_verification()`; planned. |
| `apps/accounts/services/onboarding.py` | Scaffold only | Advance validated onboarding gates. | Models/policies/verification. | Form/render/discovery. | `forms.py`; `views.py`; `discovery/selectors.py`. | `advance_onboarding()`; planned. |
| `apps/accounts/templates/accounts/onboarding.html` | Scaffold only | Present onboarding. | View context. | Gate/mutation. | `policies.py`; `onboarding.py`. | Render target; planned. |
| `apps/accounts/templates/accounts/privacy.html` | Scaffold only | Present privacy/face visibility. | View context. | Policy/mutation. | `policies.py`; `onboarding.py`. | Render target; planned. |
| `apps/accounts/templates/accounts/profile.html` | Scaffold only | Present permitted profile. | View context. | Access/discovery. | `policies.py`; `discovery/selectors.py`. | Render target; planned. |
| `apps/accounts/templates/accounts/profile_edit.html` | Scaffold only | Present profile-edit form. | `forms.py`. | Mutation/permission. | `onboarding.py`; `policies.py`. | Render target; planned. |
| `apps/accounts/templates/accounts/verification.html` | Scaffold only | Present verification status/start. | View/service result. | Provider/decision. | `face_verification.py`; `verification/provider.py`. | Render target; planned. |
| `apps/accounts/urls.py` | Scaffold only | Map account URLs. | `views.py`. | Request/rules. | `views.py`; `config/urls.py`. | `urlpatterns`; planned. |
| `apps/accounts/verification/__init__.py` | Scaffold only | Verification adapter package. | Named adapter files. | Workflow/policy. | `face_verification.py`; `policies.py`. | Exports; planned. |
| `apps/accounts/verification/base.py` | Scaffold only | Provider-neutral request/result contract. | Standard types. | Transport/persistence/eligibility. | `provider.py`; `face_verification.py`; `policies.py`. | `FaceVerificationProvider`; planned. |
| `apps/accounts/verification/provider.py` | Scaffold only | Translate configured provider. | Base contract/provider SDK. | Participation/callback HTTP. | `policies.py`; `webhooks.py`. | `get_face_verification_provider()`; planned. |
| `apps/accounts/verification/webhooks.py` | Scaffold only | Authenticate/deduplicate callbacks. | Adapter/service/audit. | General views/provider policy. | `face_verification.py`; `provider.py`. | `process_verification_webhook()`; planned. |
| `apps/accounts/views.py` | Scaffold only | Coordinate account HTTP/responses. | Forms/permissions/policies/selectors/services. | Rules/provider calls. | Exact account owner. | View callables; planned. |

### Discovery and interests

| File | Status | Reserved responsibility | May depend on | Must not own | Out-of-scope owner | Planned primary entry point |
| --- | --- | --- | --- | --- | --- | --- |
| `apps/discovery/__init__.py` | Scaffold only | Discovery package. | Metadata. | Behavior. | `selectors.py`. | None. |
| `apps/discovery/filters.py` | Scaffold only | Parse/constrain filter input. | Interests/presentation. | Query/filter application. | `services/filtering.py`; `selectors.py`. | `parse_discovery_filters()`; planned. |
| `apps/discovery/selectors.py` | Scaffold only | Build eligible discovery results. | Account/plan/interest reads; services. | Mutation/exact location. | Owning services; `location_privacy.py`. | `get_discovery_results()`; planned. |
| `apps/discovery/services/__init__.py` | Scaffold only | Discovery-service exports. | Named services. | Implementation. | Exact service. | Exports; planned. |
| `apps/discovery/services/filtering.py` | Scaffold only | Apply parsed permitted filters. | `filters.py`, read contracts. | Parsing/proximity/mutation. | `filters.py`; `proximity.py`. | `apply_discovery_filters()`; planned. |
| `apps/discovery/services/proximity.py` | Scaffold only | Privacy-safe distance/order. | `common/security/location_privacy.py`. | Movement history/exact coordinates. | `location_privacy.py`; `accounts/models.py`. | `calculate_permitted_proximity()`; planned. |
| `apps/discovery/templates/discovery/filters.html` | Scaffold only | Present filter controls. | View context. | Filter authority/query. | `filters.py`; `selectors.py`. | Render target; planned. |
| `apps/discovery/templates/discovery/grid.html` | Scaffold only | Present grid shell. | View context. | Eligibility/order. | `selectors.py`. | Render target; planned. |
| `apps/discovery/templates/discovery/partials/grid_results.html` | Scaffold only | Present result set. | Selector result. | Query/mutation. | `selectors.py`. | Partial; planned. |
| `apps/discovery/templates/discovery/partials/profile_card.html` | Scaffold only | Present permitted card projection. | Selector result. | Visibility/plan/location decisions. | `accounts/policies.py`; `plans/policies.py`; `location_privacy.py`. | Partial; planned. |
| `apps/discovery/urls.py` | Scaffold only | Map discovery URLs. | `views.py`. | Request/query logic. | `views.py`; `config/urls.py`. | `urlpatterns`; planned. |
| `apps/discovery/views.py` | Scaffold only | Coordinate discovery HTTP/rendering. | Filters/selector. | Ranking/rules/mutation. | `filters.py`; `selectors.py`. | View callables; planned. |
| `apps/interests/__init__.py` | Scaffold only | Interests package. | Metadata. | Behavior. | `services.py`. | None. |
| `apps/interests/admin.py` | Scaffold only | Controlled-interest admin. | Models/service. | Mutation rules in admin. | `services.py`. | Admin registrations; planned. |
| `apps/interests/migrations/__init__.py` | Scaffold only | Migration package, not migration. | Django discovery. | Operations/models. | Future migration after `models.py`. | None. |
| `apps/interests/models.py` | Scaffold only | Persist controlled taxonomy. | ORM/shared primitives. | Discovery/profile/plan workflows. | `discovery/filters.py`; account/plan services. | Model classes; planned. |
| `apps/interests/selectors.py` | Scaffold only | Read controlled interests. | `models.py`. | Mutation/filtering. | `services.py`; `discovery/services/filtering.py`. | `get_available_interests()`; planned. |
| `apps/interests/services.py` | Scaffold only | Mutate controlled taxonomy. | Models/selectors/audit. | Account/plan/discovery workflows. | Their exact services. | `update_interest_taxonomy()`; planned. |

### Messaging

| File | Status | Reserved responsibility | May depend on | Must not own | Out-of-scope owner | Planned primary entry point |
| --- | --- | --- | --- | --- | --- | --- |
| `apps/messaging/__init__.py` | Scaffold only | Messaging package. | Metadata. | Behavior. | `services/`. | None. |
| `apps/messaging/consumers.py` | Scaffold only | Coordinate authenticated realtime connections. | Policies/services/Channels. | Rules/persistence/block state. | `services/messages.py`; `safety/services/blocking.py`. | Consumer class; planned. |
| `apps/messaging/migrations/__init__.py` | Scaffold only | Migration package, not migration. | Django discovery. | Operations/models. | Future migration after `models.py`. | None. |
| `apps/messaging/models.py` | Scaffold only | Persist conversations/messages. | ORM/shared primitives. | Access/delivery/reports/plan validity. | `policies.py`; services; safety/plans. | Model classes; planned. |
| `apps/messaging/policies.py` | Scaffold only | Decide access/contact/message permission. | Messaging/account/block/plan state. | HTTP/mutation/sanctions. | `views.py`; `messages.py`; `moderation/services/sanctions.py`. | `can_send_message()`; planned. |
| `apps/messaging/routing.py` | Scaffold only | Map realtime paths. | `consumers.py`. | Auth/message work. | `consumers.py`; `config/asgi.py`. | `websocket_urlpatterns`; planned. |
| `apps/messaging/selectors.py` | Scaffold only | Read permitted conversations/messages. | Models/policies. | Mutation/delivery/evidence. | Services; `moderation/services/evidence.py`. | `get_user_conversations()`; planned. |
| `apps/messaging/services/__init__.py` | Scaffold only | Messaging-service exports. | Named services. | Implementation. | Exact service. | Exports; planned. |
| `apps/messaging/services/conversations.py` | Scaffold only | Get/create permitted conversation. | Models/policies/account/block. | Send messages/confirm plans. | `messages.py`; `plans/policies.py`. | `get_or_create_conversation()`; planned. |
| `apps/messaging/services/message_safety.py` | Scaffold only | Assess message-specific safety signals. | Messaging/safety/audit. | Findings/sanctions. | `safety/services/reporting.py`; `moderation/services/cases.py`. | `assess_message_safety()`; planned. |
| `apps/messaging/services/messages.py` | Scaffold only | Persist one permitted message. | Models/policies/conversation/safety. | Blocks/plans/delivery. | `blocking.py`; `plans/create_plan.py`; `notifications/scheduling.py`. | `send_message()`; planned. |
| `apps/messaging/templates/messaging/conversation.html` | Scaffold only | Present conversation/composer. | View context. | Access/send/report rules. | `policies.py`; `messages.py`; `reporting.py`. | Render target; planned. |
| `apps/messaging/templates/messaging/inbox.html` | Scaffold only | Present conversation list. | Selector result. | Query/ranking. | `selectors.py`. | Render target; planned. |
| `apps/messaging/templates/messaging/partials/message.html` | Scaffold only | Present message projection. | Selector context. | Evidence/access. | `policies.py`; `moderation/services/evidence.py`. | Partial; planned. |
| `apps/messaging/urls.py` | Scaffold only | Map messaging URLs. | `views.py`. | Request/rules. | `views.py`; `config/urls.py`. | `urlpatterns`; planned. |
| `apps/messaging/views.py` | Scaffold only | Coordinate messaging HTTP. | Policies/selectors/services. | Rules/workflow/blocking. | Exact messaging owner; `safety/services/blocking.py`. | View callables; planned. |

### Moderation and notifications

| File | Status | Reserved responsibility | May depend on | Must not own | Out-of-scope owner | Planned primary entry point |
| --- | --- | --- | --- | --- | --- | --- |
| `apps/moderation/__init__.py` | Scaffold only | Moderation package. | Metadata. | Workflows. | `services/`. | None. |
| `apps/moderation/admin.py` | Scaffold only | Controlled moderation admin. | Models/policies/services. | Case/sanction rules. | `cases.py`; `sanctions.py`. | Admin registrations; planned. |
| `apps/moderation/migrations/__init__.py` | Scaffold only | Migration package, not migration. | Django discovery. | Operations/models. | Future migration after `models.py`. | None. |
| `apps/moderation/models.py` | Scaffold only | Persist cases/evidence refs/signals/sanctions. | ORM/shared primitives. | Intake/adjudication/evidence workflow. | `safety/reporting.py`; moderation services. | Model classes; planned. |
| `apps/moderation/policies.py` | Scaffold only | Decide staff access/actions. | Moderation state/roles. | Mutation/sanctions/HTTP. | `cases.py`; `sanctions.py`; `views.py`. | `can_review_case()`; planned. |
| `apps/moderation/selectors.py` | Scaffold only | Read authorised prioritised cases. | Models/policies. | Priority/evidence/sanctions. | `risk_signals.py`; `evidence.py`; `sanctions.py`. | `get_moderation_queue()`; planned. |
| `apps/moderation/services/__init__.py` | Scaffold only | Moderation-service exports. | Named services. | Implementation. | Exact service. | Exports; planned. |
| `apps/moderation/services/cases.py` | Scaffold only | Open/triage/resolve case. | Models/policies/reports. | Intake/evidence mechanics/sanctions. | `safety/reporting.py`; `evidence.py`; `sanctions.py`. | `manage_moderation_case()`; planned. |
| `apps/moderation/services/duplicate_accounts.py` | Scaffold only | Produce reviewable duplicate/re-entry investigation. | Verification refs/moderation state. | Automatic identity/sanction. | `accounts/verification/base.py`; `sanctions.py`. | `investigate_duplicate_account()`; planned. |
| `apps/moderation/services/evidence.py` | Scaffold only | Preserve authorised case evidence. | Cases/message/safety reads/audit. | Truth/outcome/sanction. | `cases.py`; `sanctions.py`. | `preserve_case_evidence()`; planned. |
| `apps/moderation/services/risk_signals.py` | Scaffold only | Perform protected blind matching/independence assessment and record reviewable signals. | Sealed experiences/protected identity/interaction proofs/models. | Subject search/disclosure/findings/sanctions. | `safety/policies.py`; `cases.py`; `sanctions.py`. | `record_risk_signal()` plus an ADR-approved match entry point; planned. |
| `apps/moderation/services/sanctions.py` | Scaffold only | Decide/apply sanctions and appeals. | Policy/cases/restrictions/audit. | Signals/intake/provider. | `risk_signals.py`; `safety/reporting.py`; `provider.py`. | `apply_sanction()`; planned. |
| `apps/moderation/templates/moderation/case.html` | Scaffold only | Present authorised case/actions. | View context. | Findings/evidence/sanctions. | `cases.py`; `evidence.py`; `sanctions.py`. | Render target; planned. |
| `apps/moderation/templates/moderation/queue.html` | Scaffold only | Present prioritised queue. | Selector result. | Priority/access. | `selectors.py`; `policies.py`. | Render target; planned. |
| `apps/moderation/urls.py` | Scaffold only | Map moderation URLs. | `views.py`. | Access/case logic. | `views.py`; `config/urls.py`. | `urlpatterns`; planned. |
| `apps/moderation/views.py` | Scaffold only | Coordinate moderation HTTP. | Policies/selectors/services. | Case/evidence/signal/sanction rules. | Exact moderation service. | View callables; planned. |
| `apps/notifications/__init__.py` | Scaffold only | Notifications package. | Metadata. | Delivery. | `services/`. | None. |
| `apps/notifications/migrations/__init__.py` | Scaffold only | Migration package, not migration. | Django discovery. | Operations/models. | Future migration after `models.py`. | None. |
| `apps/notifications/models.py` | Scaffold only | Persist requests/schedules/attempts. | ORM/shared primitives. | Domain decision/provider transport. | Requesting service; delivery services. | Model classes; planned. |
| `apps/notifications/selectors.py` | Scaffold only | Read due/authorised notifications. | Models. | Scheduling/delivery/decision. | `scheduling.py`; delivery services. | `get_due_notifications()`; planned. |
| `apps/notifications/services/__init__.py` | Scaffold only | Notification-service exports. | Named services. | Implementation. | Exact service. | Exports; planned. |
| `apps/notifications/services/email.py` | Scaffold only | Deliver/record approved email. | Models/email provider. | Purpose/schedule/outcome. | Requesting domain; `scheduling.py`. | `send_email_notification()`; planned. |
| `apps/notifications/services/scheduling.py` | Scaffold only | Persist delivery schedule after request. | Models/selectors. | Whether event warrants notice. | Requesting domain service. | `schedule_notification()`; planned. |
| `apps/notifications/services/web_push.py` | Scaffold only | Deliver/record approved push. | Models/push provider. | Domain decision/browser UI. | Requesting domain; `static/js/install.js`. | `send_web_push_notification()`; planned. |
| `apps/notifications/tasks.py` | Scaffold only | Invoke due delivery services. | Selectors/delivery. | Scheduling/delivery rules. | `scheduling.py`; email/push services. | `deliver_due_notifications()`; planned. |

### Plans

| File | Status | Reserved responsibility | May depend on | Must not own | Out-of-scope owner | Planned primary entry point |
| --- | --- | --- | --- | --- | --- | --- |
| `apps/plans/__init__.py` | Scaffold only | Plans package. | Metadata. | Behavior. | `services/`. | None. |
| `apps/plans/admin.py` | Scaffold only | Controlled plan admin. | Models/policies/services. | Workflow rules. | Exact plan service. | Admin registrations; planned. |
| `apps/plans/forms.py` | Scaffold only | Bind plan fields. | Validators/policies/presentation. | Mutation/permission. | `create_plan.py`; `update_plan.py`; `policies.py`. | Form classes; planned. |
| `apps/plans/migrations/__init__.py` | Scaffold only | Migration package, not migration. | Django discovery. | Operations/models. | Future migration after `models.py`. | None. |
| `apps/plans/models.py` | Scaffold only | Persist host/place/time/URL/status. | ORM/shared primitives. | HTTP/fetching/messaging. | `views.py`; `venue_metadata.py`; messaging. | Model classes; planned. |
| `apps/plans/policies.py` | Scaffold only | Decide plan actions/no-payment rules. | Plan/account state/technical results. | Mutation/HTTP/URL security. | Plan services/views; `safe_urls.py`. | `can_create_plan()`; planned. |
| `apps/plans/selectors.py` | Scaffold only | Read permitted active/detail plans. | Models/policies. | Mutation/expiry/ranking. | Services; `discovery/selectors.py`. | `get_active_plans()`; planned. |
| `apps/plans/services/__init__.py` | Scaffold only | Plan-service exports. | Named services. | Implementation. | Exact service. | Exports; planned. |
| `apps/plans/services/create_plan.py` | Scaffold only | Create one eligible validated plan. | Models/validators/policies/safe URL. | Forms/metadata transport/notification. | `forms.py`; `venue_metadata.py`; `notifications/scheduling.py`. | `create_plan()`; planned. |
| `apps/plans/services/plan_expiry.py` | Scaffold only | Expire due plans. | Models/policies/selectors/audit. | Scheduling/discovery render. | `tasks.py`; `discovery/selectors.py`. | `expire_due_plans()`; planned. |
| `apps/plans/services/update_plan.py` | Scaffold only | Apply authorised validated update. | Models/validators/policies/safe URL. | Form/HTTP/metadata transport. | `forms.py`; `views.py`; `venue_metadata.py`. | `update_plan()`; planned. |
| `apps/plans/services/venue_metadata.py` | Scaffold only | Fetch normalised metadata from approved URL. | `safe_urls.py`/HTTP adapter. | URL policy/host confirmation/mutation. | `safe_urls.py`; create/update services. | `get_venue_metadata()`; planned. |
| `apps/plans/tasks.py` | Scaffold only | Invoke plan services in background. | Named services. | Expiry rules/direct writes. | `plan_expiry.py`. | `expire_plans_task()`; planned. |
| `apps/plans/templates/plans/create.html` | Scaffold only | Present create form. | `forms.py`. | Creation/permission/URL safety. | `create_plan.py`; `policies.py`; `safe_urls.py`. | Render target; planned. |
| `apps/plans/templates/plans/detail.html` | Scaffold only | Present permitted plan/actions. | Selector context. | Access/join/message rules. | `policies.py`; `messaging/policies.py`. | Render target; planned. |
| `apps/plans/templates/plans/edit.html` | Scaffold only | Present update form. | Form/view context. | Update/permission. | `update_plan.py`; `policies.py`. | Render target; planned. |
| `apps/plans/templates/plans/partials/plan_preview.html` | Scaffold only | Present non-authoritative preview. | Clean form context. | Validation/fetch/persist. | `validators.py`; `safe_urls.py`; services. | Partial; planned. |
| `apps/plans/templates/plans/partials/plan_status.html` | Scaffold only | Present decided plan status. | Selector/service result. | Transition/expiry. | `plan_expiry.py`; `policies.py`. | Partial; planned. |
| `apps/plans/urls.py` | Scaffold only | Map plan URLs. | `views.py`. | Request/rules. | `views.py`; `config/urls.py`. | `urlpatterns`; planned. |
| `apps/plans/validators.py` | Scaffold only | Validate plan value/required shape. | Validators/safe URL result. | Permission/mutation/fetch. | `policies.py`; services; `safe_urls.py`; `venue_metadata.py`. | `validate_plan_details()`; planned. |
| `apps/plans/views.py` | Scaffold only | Coordinate plan HTTP. | Forms/policies/selectors/services. | Rules/workflow. | Exact plan owner. | View callables; planned. |

### Safety

| File | Status | Reserved responsibility | May depend on | Must not own | Out-of-scope owner | Planned primary entry point |
| --- | --- | --- | --- | --- | --- | --- |
| `apps/safety/__init__.py` | Scaffold only | Safety package. | Metadata. | Workflows. | `services/`. | None. |
| `apps/safety/admin.py` | Scaffold only | Controlled safety admin. | Models/policies/moderation. | Findings/sanctions. | `moderation/services/cases.py`; `sanctions.py`. | Admin registrations; planned. |
| `apps/safety/forms.py` | Scaffold only | Bind block/experience/report/circle-choice/check-in/help fields. | Policies/presentation. | Mutation/matching/findings. | Exact safety service; `moderation/risk_signals.py`; `cases.py`. | Form classes; planned. |
| `apps/safety/migrations/__init__.py` | Scaffold only | Migration package, not migration. | Django discovery. | Operations/models. | Future migration after `models.py`. | None. |
| `apps/safety/models.py` | Scaffold only | Persist blocks, experiences, protected identity/choices, circles, rights records, reports, check-ins, incidents, and contacts. | ORM/shared primitives. | Workflow/matching/findings/delivery. | Safety services; moderation; notifications. | Model classes; planned. |
| `apps/safety/policies.py` | Scaffold only | Decide private safety, experience, circle, and contributor-rights access/actions. | Safety/account/interaction/choice state. | Mutation/HTTP/matching/findings. | Services/views; moderation. | `can_access_safety_action()`; planned. |
| `apps/safety/selectors.py` | Scaffold only | Read privacy-safe safety/block/contributor/circle projections. | Models/policies. | Mutation/subject search/identity disclosure/public reputation/findings. | Services; messaging/discovery policies. | `get_block_state()` and private projections; planned. |
| `apps/safety/services/__init__.py` | Scaffold only | Safety-service exports. | Named services. | Implementation. | Exact service. | Exports; planned. |
| `apps/safety/services/blocking.py` | Scaffold only | Create effective two-way block. | Models/policies/messaging/discovery/audit. | Delete messages/findings/sanctions. | `messaging/messages.py`; `reporting.py`; `moderation/sanctions.py`. | `block_user()`; planned. |
| `apps/safety/services/check_ins.py` | Scaffold only | Schedule/issue/record private check-ins. | Safety/plan/notifications. | Tracking/public review/delivery. | `location_privacy.py`; `notifications/scheduling.py`. | `schedule_meeting_check_ins()`; planned. |
| `apps/safety/services/incident_response.py` | Scaffold only | Coordinate bounded immediate options. | Safety services/notifications. | Emergency promises/findings. | `urgent_help.html`; `moderation/cases.py`. | `start_incident_response()`; planned. |
| `apps/safety/services/reporting.py` | Scaffold only | Seal firsthand experiences, record granular choices/corrections/rights actions, create formal reports, and hand off signals/cases. | Models/policies/interaction checks/evidence refs/audit. | Subject search/matching algorithm/truth/sanction/evidence custody. | `moderation/risk_signals.py`; `cases.py`; `evidence.py`; `sanctions.py`. | `create_report()` plus an ADR-approved experience entry point; planned. |
| `apps/safety/services/trusted_contacts.py` | Scaffold only | Manage/share with trusted contacts. | Models/policies/notifications. | Findings/surveillance. | `incident_response.py`; `notifications/scheduling.py`. | `share_with_trusted_contact()`; planned. |
| `apps/safety/tasks.py` | Scaffold only | Invoke due safety services. | Named services. | Check-in rules/direct writes. | `check_ins.py`. | `send_due_check_ins()`; planned. |
| `apps/safety/templates/safety/block.html` | Scaffold only | Present block confirmation/outcome. | Form/view context. | Block authority. | `blocking.py`; `policies.py`. | Render target; planned. |
| `apps/safety/templates/safety/check_in.html` | Scaffold only | Present private check-in. | Form/view context. | Schedule/privacy/persist. | `check_ins.py`; `policies.py`. | Render target; planned. |
| `apps/safety/templates/safety/report.html` | Scaffold only | Present report form/confirmation. | Form/view context. | Intake/evidence/findings. | `reporting.py`; moderation evidence/cases. | Render target; planned. |
| `apps/safety/templates/safety/urgent_help.html` | Scaffold only | Present honest immediate options. | Incident result/device capability. | Emergency promises/findings. | `incident_response.py`; `moderation/cases.py`. | Render target; planned. |
| `apps/safety/urls.py` | Scaffold only | Map safety URLs. | `views.py`. | Request/rules. | `views.py`; `config/urls.py`. | `urlpatterns`; planned. |
| `apps/safety/views.py` | Scaffold only | Coordinate private safety HTTP. | Forms/policies/selectors/services. | Workflow/findings. | Exact safety service; moderation handoff. | View callables; planned. |

### Common security

| File | Status | Reserved responsibility | May depend on | Must not own | Out-of-scope owner | Planned primary entry point |
| --- | --- | --- | --- | --- | --- | --- |
| `common/exceptions.py` | Scaffold only | Stable shared technical exceptions. | Standard exceptions. | Domain decisions/HTTP. | Domain policy/service; its view. | Exception classes; planned. |
| `common/middleware.py` | Scaffold only | Request-wide technical controls/context. | Django/security controls. | Domain permissions/workflows. | Domain policies/views; `rate_limits.py`. | Middleware classes; planned. |
| `common/models.py` | Scaffold only | Proven shared abstract model primitives. | ORM. | Domain state. | Exact domain `models.py`. | Abstract classes; planned. |
| `common/permissions.py` | Scaffold only | Cross-domain technical permission adapters. | Domain policies/framework. | Product/account policy. | Domain `policies.py`; `accounts/permissions.py`. | Permission adapters; planned. |
| `common/security/__init__.py` | Scaffold only | Security-control exports. | Named controls. | Implementation/policy. | Exact security file/domain policy. | Exports; planned. |
| `common/security/audit.py` | Scaffold only | Append technical audit events. | Storage/hash/time metadata. | Action/finding/evidence truth. | Owning service; `moderation/cases.py`. | `record_audit_event()`; planned. |
| `common/security/location_privacy.py` | Scaffold only | Coarsen/limit/expire location data. | Geospatial/config primitives. | Ranking/account workflow. | `discovery/services/proximity.py`; `accounts/models.py`. | `coarsen_location()`; planned. |
| `common/security/rate_limits.py` | Scaffold only | Reusable technical rate limits. | Cache/request identity. | Product eligibility. | Domain `policies.py`; `middleware.py`. | `check_rate_limit()`; planned. |
| `common/security/safe_urls.py` | Scaffold only | Validate URL scheme/network/redirect safety. | URL/DNS/network/config. | Plan-required rule/metadata fetch. | `plans/validators.py`; `plans/services/venue_metadata.py`. | `validate_safe_public_url()`; planned. |

### Documentation

| File | Status | Reserved responsibility | May depend on | Must not own | Out-of-scope owner | Planned primary entry point |
| --- | --- | --- | --- | --- | --- | --- |
| `docs/ARCHITECTURE.md` | Documentation | Designed product/domain/layer architecture. | Requirements/decisions. | Current-runtime claims. | Code for behavior; this file for placement. | Architecture reference. |
| `docs/ARCHITECTURAL_INVARIANTS.md` | Documentation | Exact file ownership and handoffs. | Worktree/Kindlelise docs. | Runtime/invented files. | Code; `DECISIONS.md` for changes. | Placement reference. |
| `docs/DATA_MODEL.md` | Documentation | Define the designed relational model, page-to-entity contracts, logic precedence, user profile, interest taxonomy, URL validation, and immutable meet artifact. | Requirements, product rules, wireframes, architecture, and supplied schema notes. | Claims that designed tables exist or page-owned persistence. | Domain `models.py` and services named in the document; unresolved boundaries in `docs/DECISIONS.md`. | Data-model and ERD reference. |
| `docs/DECISIONS.md` | Documentation | Accepted architecture decisions/rationale. | Reviewed evidence. | Unsupported claims. | Changed owning code/docs. | ADR register. |
| `docs/DEPLOYMENT.md` | Scaffold only | Future verified deployment/rollback/ops. | Actual deployment/config. | Fictional commands. | `deployment/`; `production.py`. | Deployment guide; planned. |
| `docs/MODERATION.md` | Scaffold only | Future roles/queues/appeals/operations. | Requirements/implemented moderation. | Safety intake/staffing claims. | `apps/moderation/`; `safety/reporting.py`. | Moderation guide; planned. |
| `docs/PRIVACY_MODEL.md` | Documentation | Designed purposes, classification, exposure, retention, rights, access, and launch gates, especially for blind corroboration. | Requirements/safety/data model and supplied privacy notes. | Compliance claims or implemented-control claims. | Owning models/services; approved legal/operational artefacts; `DECISIONS.md`. | Privacy design reference. |
| `docs/PRODUCT.md` | Scaffold only | Future plain-language product scope. | Requirements/rules. | Placement/status. | `REQUIREMENTS.md`; `PRODUCT_RULES.md`. | Product guide; planned. |
| `docs/PRODUCT_RULES.md` | Documentation | Non-negotiable product invariants. | Decisions/requirements. | File inventory/status claims. | This file; code. | Rule reference. |
| `docs/REQUIREMENTS.md` | Documentation | Numbered outcomes/acceptance criteria. | Product decisions. | Structure/completion claims. | `TRACEABILITY.md`; code/tests. | Requirements register. |
| `docs/SAFETY_MODEL.md` | Documentation | Define the designed blind-corroboration, private-support, moderation separation, safety journeys, limits, and escalation boundaries. | Requirements/privacy/data model and supplied safety notes. | Security implementation, legal approval, guilt, or emergency promises. | Safety/moderation/security files. | Safety design reference. |
| `docs/THREAT_MODEL.md` | Scaffold only | Future assets/threats/controls/residual risk. | Architecture/privacy/implemented controls. | Product safety workflows. | `common/security/`; policies. | Threat model; planned. |
| `docs/TRACEABILITY.md` | Documentation | Map requirements to planned owners/interfaces/tests. | Requirements/worktree. | Treat plans as implementation. | Exact code/test when present. | Traceability matrix. |
| `docs/USER_FLOWS.md` | Scaffold only | Future user journeys/visible states. | Product/requirements/implemented UI. | Business authority/fictional routes. | Domain policies/services/views/templates. | Flow guide; planned. |
| `docs/VERTICAL_SLICE.md` | Documentation | Define the proposed 35-file alpha boundary, exact target tree, responsibilities, constraints and replacement gate. | Pinned product invariants and wireframes. | Permission to implement an unreconciled schema or silently delete the current scaffold. | Approved vertical-slice ERD and explicit replacement approval. | Vertical-slice build contract. |
| `docs/WIREFRAMES.md` | Documentation | Define the mobile wireframe contract derived from the supplied layout references and the pinned person/plan/signal/social-circle/safety boundaries. | Authoritative product invariants, accepted ownership, and supplied captures. | ERD/file-placement authority, copying source-product behavior, or claiming implementation. | Reconciled ERD before implementation; domain owners named conceptually in the document. | Wireframe design reference. |

### Static assets and cross-domain templates

| File | Status | Reserved responsibility | May depend on | Must not own | Out-of-scope owner | Planned primary entry point |
| --- | --- | --- | --- | --- | --- | --- |
| `static/css/base.css` | Scaffold only | Shared visual/accessibility foundation. | Semantic HTML. | Domain behavior. | Domain template/style. | CSS rules; planned. |
| `static/css/grid.css` | Scaffold only | Grid/card styling. | Discovery templates/base. | Ordering/filtering. | `discovery/selectors.py`; `static/js/filters.js`. | CSS rules; planned. |
| `static/css/messaging.css` | Scaffold only | Messaging presentation styling. | Messaging templates/base. | Permission/delivery. | Messaging policy/service. | CSS rules; planned. |
| `static/css/profiles.css` | Scaffold only | Account/profile styling. | Account templates/base. | Visibility/verification. | `accounts/policies.py`; `face_verification.py`. | CSS rules; planned. |
| `static/css/safety.css` | Scaffold only | Safety-interface styling. | Safety templates/base. | Safety workflows. | Exact safety service. | CSS rules; planned. |
| `static/icons/.gitkeep` | Static asset | Preserve empty icon directory. | Version control. | Icons/manifest. | Future icon; `manifest.webmanifest`. | None. |
| `static/js/check-in.js` | Scaffold only | Enhance server-authoritative check-in form. | Check-in template/endpoint. | Scheduling/outcomes/persist. | `safety/check_ins.py`; `safety/forms.py`. | `initCheckIn()`; planned. |
| `static/js/filters.js` | Scaffold only | Enhance filter submission/results. | Filter form/endpoint. | Validation/results. | `discovery/filters.py`; `selectors.py`. | `initDiscoveryFilters()`; planned. |
| `static/js/install.js` | Scaffold only | PWA install/push-permission UI. | Manifest/browser APIs. | Notification policy/delivery. | `notifications/web_push.py`; manifest. | `initInstallPrompt()`; planned. |
| `static/js/location.js` | Scaffold only | Request consented browser location input. | Geolocation/server endpoint. | Coarsening/retention/order. | `location_privacy.py`; `proximity.py`. | `initLocationSharing()`; planned. |
| `static/js/messaging.js` | Scaffold only | Enhance message submission/presentation. | Template/endpoint. | Permission/persist/block. | Messaging policy/service; `blocking.py`. | `initMessaging()`; planned. |
| `static/manifest.webmanifest` | Scaffold only | Installable app identity/assets. | Actual icons/paths. | Install logic/notifications. | `install.js`; future icons. | Manifest fields; planned. |
| `templates/403.html` | Scaffold only | Present non-leaking denial. | View status/context. | Permission. | Domain policy/view. | Render target; planned. |
| `templates/404.html` | Scaffold only | Present non-leaking not-found. | View status/context. | Visibility. | Domain policy/selector/view. | Render target; planned. |
| `templates/500.html` | Scaffold only | Present safe generic error. | Error context. | Logging/details policy. | `common/middleware.py`; deployment config. | Render target; planned. |
| `templates/about.html` | Scaffold only | Present truthful product description. | Future `docs/PRODUCT.md`. | Rules/status claims. | `PRODUCT.md`; `PRODUCT_RULES.md`. | Render target; planned. |
| `templates/base.html` | Scaffold only | Shared page structure/assets/blocks. | Static/view context. | Domain decisions/queries. | Domain view/template. | Base template; planned. |
| `templates/components/dialog.html` | Scaffold only | Accessible dialog shell. | Caller content. | Confirmation decision. | Calling domain service/template. | Component; planned. |
| `templates/components/empty_state.html` | Scaffold only | Generic empty-result presentation. | Caller context. | Query/eligibility. | Calling selector/view. | Component; planned. |
| `templates/components/navigation.html` | Scaffold only | Present server-permitted navigation. | Auth view context. | Access decisions. | Domain policy; `config/urls.py`. | Component; planned. |
| `templates/components/toast.html` | Scaffold only | Present server-selected feedback. | View/form message. | Outcome/error policy. | Calling service/form/view. | Component; planned. |
| `templates/components/verification_badge.html` | Scaffold only | Present accurate verification label. | Account policy/selector result. | Verification/identity/safety claims. | `face_verification.py`; `policies.py`; `verification/base.py`. | Component; planned. |
| `templates/home.html` | Scaffold only | Present landing/next action. | Root view context. | Discovery/onboarding/routing. | Discovery/account views; `config/urls.py`. | Render target; planned. |
| `templates/privacy.html` | Scaffold only | Present reviewed privacy text. | Future privacy model. | Unsupported guarantees. | `PRIVACY_MODEL.md`; data owners. | Render target; planned. |
| `templates/rules.html` | Scaffold only | Present public product rules. | `PRODUCT_RULES.md`. | Enforcement. | Domain policies/services. | Render target; planned. |
| `templates/terms.html` | Scaffold only | Present reviewed terms. | Approved text. | Legal creation/enforcement. | Reviewed docs/domain policies. | Render target; planned. |

### Tests

| File | Status | Reserved responsibility | May depend on | Must not own | Out-of-scope owner | Planned primary entry point |
| --- | --- | --- | --- | --- | --- | --- |
| `tests/__init__.py` | Scaffold only | Test package. | Metadata. | Fixtures/tests. | `conftest.py`; future test. | None. |
| `tests/conftest.py` | Scaffold only | Shared pytest fixtures/setup. | Testing settings/factories. | Product behavior/assertions. | `factories.py`; future test. | Fixtures; planned. |
| `tests/factories.py` | Scaffold only | Reusable valid test data. | Implemented models/services. | Assertions/default bypass state. | Future test; production service. | Factories; planned. |
| `tests/accounts/README.md` | Scaffold only | Reserve account behavior tests. | Requirements/public behavior. | Production/fake tests. | Future deliberate account test. | Area guide; planned. |
| `tests/discovery/README.md` | Scaffold only | Reserve discovery behavior tests. | Requirements/public behavior. | Production/fake tests. | Future deliberate discovery test. | Area guide; planned. |
| `tests/integration/README.md` | Scaffold only | Reserve cross-domain integration tests. | Public integrated behavior. | Unit ownership/fakes. | Future integration test. | Area guide; planned. |
| `tests/interests/README.md` | Scaffold only | Reserve taxonomy behavior tests. | Requirements/public behavior. | Production/fakes. | Future interests test. | Area guide; planned. |
| `tests/journeys/README.md` | Scaffold only | Reserve full user-journey tests. | Implemented workflows. | Domain implementation/invention. | Future journey test. | Area guide; planned. |
| `tests/messaging/README.md` | Scaffold only | Reserve messaging behavior tests. | Requirements/public behavior. | Production/fakes. | Future messaging test. | Area guide; planned. |
| `tests/moderation/README.md` | Scaffold only | Reserve moderation behavior tests. | Requirements/authorised behavior. | Production/fakes. | Future moderation test. | Area guide; planned. |
| `tests/notifications/README.md` | Scaffold only | Reserve scheduling/delivery tests. | Requirements/adapter contracts. | Provider claims/fakes. | Future notification test. | Area guide; planned. |
| `tests/plans/README.md` | Scaffold only | Reserve plan behavior tests. | Requirements/public behavior. | Production/fakes. | Future plan test. | Area guide; planned. |
| `tests/requirements/README.md` | Scaffold only | Reserve numbered-requirement tests. | Requirements/implemented behavior. | Coverage claims without assertions. | Future exact test; `TRACEABILITY.md`. | Area guide; planned. |
| `tests/safety/README.md` | Scaffold only | Reserve private safety behavior tests. | Requirements/public behavior. | Production/unsafe fakes. | Future safety test. | Area guide; planned. |
| `tests/security/README.md` | Scaffold only | Reserve adversarial/privacy tests. | Threat/privacy/controls. | Controls/pass claims. | Future security test; `common/security/`. | Area guide; planned. |

## 11. Primary-entry-point register

All names are planned; none currently exists.

| Exact file | Planned primary entry point | Bounded result / next owner |
| --- | --- | --- |
| `apps/accounts/selectors.py` | `get_public_profile()` | Permitted projection to account/discovery view. |
| `apps/accounts/services/account_restrictions.py` | `apply_account_restriction()` | Restriction result; moderation retains sanction authority. |
| `apps/accounts/services/face_verification.py` | `start_face_verification()` | Provider-neutral attempt/status to account view. |
| `apps/accounts/services/onboarding.py` | `advance_onboarding()` | Gate state to account view. |
| `apps/accounts/verification/provider.py` | `get_face_verification_provider()` | Adapter implementing base contract. |
| `apps/accounts/verification/webhooks.py` | `process_verification_webhook()` | Authenticated result to verification service. |
| `apps/discovery/selectors.py` | `get_discovery_results()` | Permitted cards to view. |
| `apps/discovery/services/filtering.py` | `apply_discovery_filters()` | Constrained read query to selector. |
| `apps/discovery/services/proximity.py` | `calculate_permitted_proximity()` | Safe labels/order to selector. |
| `apps/interests/selectors.py` | `get_available_interests()` | Controlled list to caller. |
| `apps/interests/services.py` | `update_interest_taxonomy()` | Updated taxonomy to admin/operator. |
| `apps/messaging/selectors.py` | `get_user_conversations()` | Authorised projections to view. |
| `apps/messaging/services/conversations.py` | `get_or_create_conversation()` | Conversation to message service/view. |
| `apps/messaging/services/message_safety.py` | `assess_message_safety()` | Signal/report handoff, never finding. |
| `apps/messaging/services/messages.py` | `send_message()` | Persisted message to caller/delivery request. |
| `apps/moderation/selectors.py` | `get_moderation_queue()` | Case projections to staff view. |
| `apps/moderation/services/cases.py` | `manage_moderation_case()` | Updated case state. |
| `apps/moderation/services/duplicate_accounts.py` | `investigate_duplicate_account()` | Reviewable result to case. |
| `apps/moderation/services/evidence.py` | `preserve_case_evidence()` | Evidence reference to case. |
| `apps/moderation/services/risk_signals.py` | `record_risk_signal()` | Signal/priority input to case. |
| `apps/moderation/services/sanctions.py` | `apply_sanction()` | Audited sanction/restriction result. |
| `apps/notifications/selectors.py` | `get_due_notifications()` | Due records to task. |
| `apps/notifications/services/email.py` | `send_email_notification()` | Recorded attempt to task. |
| `apps/notifications/services/scheduling.py` | `schedule_notification()` | Durable schedule to requesting domain. |
| `apps/notifications/services/web_push.py` | `send_web_push_notification()` | Recorded attempt to task. |
| `apps/plans/selectors.py` | `get_active_plans()` | Permitted plans to view/discovery. |
| `apps/plans/services/create_plan.py` | `create_plan()` | Valid plan to view/notification request. |
| `apps/plans/services/plan_expiry.py` | `expire_due_plans()` | Expiry result to task/script. |
| `apps/plans/services/update_plan.py` | `update_plan()` | Updated plan to view. |
| `apps/plans/services/venue_metadata.py` | `get_venue_metadata()` | Informational metadata to plan workflow. |
| `apps/safety/selectors.py` | `get_block_state()` | Private block read to policies. |
| `apps/safety/services/blocking.py` | `block_user()` | Effective block to view/dependent reads. |
| `apps/safety/services/check_ins.py` | `schedule_meeting_check_ins()` | Schedules to notifications. |
| `apps/safety/services/incident_response.py` | `start_incident_response()` | Bounded options to safety view. |
| `apps/safety/services/reporting.py` | `create_report()` | Report and case-intake handoff. |
| `apps/safety/services/trusted_contacts.py` | `share_with_trusted_contact()` | Delivery request to notifications. |
| `common/security/audit.py` | `record_audit_event()` | Append-only reference to caller. |
| `common/security/location_privacy.py` | `coarsen_location()` | Safe representation to proximity service. |
| `common/security/rate_limits.py` | `check_rate_limit()` | Technical result to middleware/caller. |
| `common/security/safe_urls.py` | `validate_safe_public_url()` | Technical result to plan validator/fetcher. |

## 12. Out-of-scope handoff register

| Work | Current boundary | Exact owner |
| --- | --- | --- |
| Plan submission | Bound fields in `plans/forms.py` | Permission: `plans/policies.py`; create/update: exact service. |
| Plan URL | Required shape in `plans/validators.py` | Technical safety: `common/security/safe_urls.py`; fetch: `venue_metadata.py`. |
| HTTP | Auth/input/response in domain view | Read: selector; decision: policy; mutation: exact service in same domain. |
| Django permission | Adapter in permission module | Product decision: owning domain `policies.py`. |
| Background/operator call | Invocation in task/script | Rules/mutation: named service called by it. |
| Verification callback | Auth/translation in `webhooks.py`/`provider.py` | State: `face_verification.py`; eligibility: `accounts/policies.py`. |
| Proximity | Privacy reduction in `location_privacy.py` | Order: `proximity.py`; results: `discovery/selectors.py`. |
| Message safety concern | Assessment in `message_safety.py` | Report: `safety/reporting.py`; evidence: `moderation/evidence.py`; finding: `cases.py`. |
| Block | Create/read in safety blocking/selector | Contact: `messaging/policies.py`; discovery: `discovery/selectors.py`. |
| Safety report | Intake in `safety/reporting.py` | Case/evidence/sanction: exact moderation service. |
| Blind match / risk signal | Protected equality/independence assessment and record in `moderation/risk_signals.py` | Private entry/disclosure choice: `safety/policies.py`; finding: `cases.py`; sanction: `sanctions.py`. |
| Notification | Need/content/time decided by requesting domain | Persist schedule: `notifications/scheduling.py`; transport: `email.py` or `web_push.py`. |
| Audit | Action decided by owning service | Technical record: `common/security/audit.py`. |
| Template/JavaScript | Presentation/input only | Server authority named in inventory. |
| Shared-looking state | Domain model concept | Exact domain `models.py`; `common/models.py` only for proven abstracts. |

## 13. Scaffold status rules

- File presence, a traceability row, or a planned name does not prove implementation.
- Scaffold only remains until the file performs its reserved responsibility.
- Partially implemented requires real behavior plus a documented primary gap.
- Implemented requires executable integration that respects boundaries.
- Tested additionally requires meaningful failing-on-regression tests.
- A migration `__init__.py` is not a migration.
- A test README or fixture docstring is not a test.
- Scaffold documentation uses reserved/future wording.
- Status is never upgraded to improve a completion report.

## 14. Architectural conflicts requiring later review

| Files | Conflict and likely owner | Why it matters | Blocks implementation? |
| --- | --- | --- | --- |
| `ARCHITECTURE.md`, `docs/ARCHITECTURE.md` | Byte-identical competing authorities; likely canonical: `docs/ARCHITECTURE.md`. | They can drift. | Not first slice; settle before editing either. |
| `README.md`, worktree, `docs/ARCHITECTURE.md` | README claims absent `backend/`, `ios/Kindlelise/`, REST/API-doc routes, `requirements.txt`, and SwiftUI behavior. Worktree plus docs architecture are authoritative. | Setup cannot work and client architecture conflicts. | Yes for onboarding/deployment. |
| `docs/TRACEABILITY.md`, `tests/` | Matrix names many absent test modules. | Planned coverage can look tested. | No if labelled planned. |
| Both architecture copies | Tree lists `config/settings/base.py` twice and has conflicting root/docs placement language. | Weakens navigation. | No. |
| `discovery/filters.py`, `services/filtering.py` | Parser vs query-filter application; `filters.py` parses, service applies. | Avoids duplicated validation/query rules. | No if boundary followed. |
| Verification service/provider/webhooks | Workflow state vs provider translation vs callback authentication. | Mixing binds policy to provider and weakens callbacks. | No if separated first. |
| Plan expiry service/task/script | Service owns rules; task/script are thin callers. | Duplicate expiry could diverge. | No if callers stay thin. |
| Message safety, safety reporting, moderation evidence/cases | Assessment, intake, custody, finding are distinct; `cases.py` owns outcome. | A signal/report must not become a finding. | Yes for safety implementation. |
| Safety incident response, moderation cases | Immediate user options vs later adjudication. | Avoids false emergency/staffing promises. | Yes for urgent-help work. |
| `common/permissions.py`, `accounts/permissions.py`, policies | Policies own decisions; permission files only adapt. | Duplicate allow/deny creates bypass risk. | Yes before permissions. |
| `common/models.py`, domain models | Domain models own state; common only proven abstract primitives. | Avoids coupling/migration ambiguity. | No if kept narrow. |
| `audit.py`, moderation evidence | Audit owns action history; evidence owns case custody. | Audit metadata is not proof. | No if separated. |
| Notification scheduling, domain tasks, notification tasks | Requesting domain decides need/time; notification service persists; task delivers. | Prevents missed/duplicate safety notices. | Yes before safety-critical notifications. |
| All scaffold files, `README.md` | Filenames look complete; contents are placeholders. `manage.py check` does nothing. | File presence/tool exit can create false confidence. | Yes for any “runs” claim. |

No executable behavior was found outside an intended layer because no executable application behavior was found.

## 15. Rules for changing the architecture

Before adding or moving a responsibility:

1. Inspect this document.
2. Search the current worktree for the existing owner.
3. Extend the designated file when the responsibility already exists.
4. Do not create generic helper modules.
5. Record a deliberate decision in `docs/DECISIONS.md` when a new boundary is truly required.
6. Update this document in the same reviewed change.
7. Never change scaffold status to implemented without executable behavior and meaningful tests.

When code and this guide disagree about actual behavior, code is final and the guide must be corrected in the same reviewed change. For placement, this document remains authoritative until an accepted architecture decision changes it.
