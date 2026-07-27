# Kindlelise Architecture

## 1. Purpose

Kindlelise is a proximity-first social application for finding nearby, privately verified people who have a real plan or want someone to join them at a public place or activity.

The product reduces a social invitation to a simple statement:

> I am going here, at this time, and someone may join me.

A representative profile card is:

> **320 m away · Available now**  
> **Going to Fabric at 10 pm**  
> [Official venue URL]  
> Looking for someone to join

The system is general-purpose and non-situational. It is not specifically a ticket, nightlife, university, gallery, music, dating, or friendship-group application. The same framework supports galleries, clubs, concerts, cafés, walks, sport, cinema, lectures, community activities, and other public plans.

## 2. Core product model

Kindlelise uses a proximity-led grid inspired by the directness of location-based social applications:

- One continuous grid of nearby profiles.
- Proximity is the primary ordering mechanism.
- Filters narrow the grid by interest, availability, plan type, time, and other permitted criteria.
- There is no swiping.
- There is no algorithmic matching.
- There is no mutual-match requirement before contact.
- Users may open a profile and message directly.
- Profiles may show an active plan or an `Available now` status.
- Plans may be immediate or scheduled for later.
- An in-person proposal must be anchored to a specific public place or activity, URL, and time.

The canonical journey is:

1. Privately prove that the account is controlled by a real, live person.
2. Open the proximity-ordered grid.
3. Optionally filter by interest, availability, time, distance, or plan type.
4. Open a nearby profile.
5. View an existing plan or propose a plan with a public URL, place, and time.
6. Message directly without swiping or matching.
7. Meet at the linked public place.
8. Receive a private safety check-in after the scheduled meeting begins.

## 3. Foundational principles

### 3.1 Private accountability with user-controlled visibility

> **You may control who sees your face, but nobody participates without privately proving they are real.**

Private face verification is mandatory before a user can:

- Appear in discovery.
- Publish a plan.
- Initiate contact.
- Respond to an invitation.
- Participate in a meeting arranged through the platform.

There are two public presentation states:

- **Visible profile:** `Face verified — live selfie matched to profile photo.`
- **Dark profile:** `Privately face verified — face not publicly displayed.`

Face verification establishes that a live person corresponds to the face used for the account. It does not establish legal identity, perform a background check, prove good intentions, or guarantee safety. The interface must state this distinction accurately.

Dark profiles provide public privacy without anonymity to the platform. Verification records, reports, sanctions, and re-entry controls remain associated with the underlying verified account. Verification media must never be shown to another user automatically and must not be accessible to ordinary staff.

### 3.2 No user-to-user payment or consideration

Hosts must never request or expect money, purchases, gifts, favours, tips, deposits, swaps, or reimbursement from guests.

The platform does not provide ticket resale, user-to-user payments, or price negotiation. A free spare ticket or place may be included in a plan. A host may also simply ask for company at an activity for which each attendee separately handles any normal third-party admission.

Third-party costs may exist when imposed independently by a venue, event, transport provider, or other external party. They must be clear from the plan and required URL, and any payment must be made directly to the third party. Optional personal purchases remain optional.

Valid examples include:

- A genuinely free spare concert ticket.
- A gallery visit with free admission.
- Joining someone at a club where the venue independently charges admission.
- Meeting for coffee where buying a drink is optional.

Invalid examples include:

- Charging for a ticket or place.
- Asking a guest to split a taxi.
- Requiring a drink, gift, tip, donation, deposit, or favour.
- Requesting payment privately after contact.
- Routing a third-party charge through the host.

No `price` field should exist for a user-offered ticket or place. The absence of user-to-user payment is a product invariant, not a selectable listing option.

### 3.3 Every meeting is anchored to a verifiable public place or activity

Every plan and every structured proposal to meet must include:

- A valid public URL.
- A named place, venue, event, or activity.
- A date and time.
- A concise statement of what the host is doing and why someone may join.

Accepted URLs include official event pages, official venue pages, reputable ticket-provider event pages, public activity listings, or public map listings when no event page exists.

The URL requirement gives the other user an independent way to inspect the place, time, organiser, admission conditions, and expected activity. Personal payment links, unrelated social profiles, unsafe URL schemes, private-network addresses, and misleading redirects are not accepted as verification URLs.

### 3.4 Safety is a launch requirement

Protecting users—particularly women and others disproportionately exposed to harassment, stalking, impersonation, and physical risk—is a core architectural concern, not a later feature.

Safety controls must minimise exposure, preserve accountability, and allow rapid action when boundaries are crossed. They must not claim that verification guarantees good intentions or that the platform can guarantee physical safety.

Important protections include:

- Mandatory private face verification.
- User-controlled public face visibility.
- Public and URL-verifiable meeting locations.
- Location privacy and resistance to easy triangulation.
- Contact and visibility controls, including gender-based preferences where lawful and appropriate.
- Immediate blocking in both directions.
- One-step reporting from profiles, plans, and conversations.
- No indication to another user that they were blocked or reported, or by whom.
- Private post-meeting safety feedback.
- Trusted-contact sharing.
- Prioritised human review of serious reports.
- Preservation of relevant evidence following credible reports.
- Temporary suspension when credible urgent risk exists.
- Controls that make sanctioned-user re-entry difficult.

The system should track relevant activity within the platform for accountability. It must not continuously track a person's real-world movement. Location should be processed only as required for current proximity discovery and should not become a staff-accessible movement history.

## 4. Meeting safety check-in

After the agreed meeting start time, both participants privately receive:

> **Is everything as you expected?**

The primary responses are:

- `Yes, all good`
- `Something feels off`
- `We didn't meet`

Selecting `Something feels off` should offer appropriate next steps, such as:

- I am safe, but want to leave.
- They are not who their profile suggested.
- They requested money, a purchase, gift, favour, or reimbursement.
- Inappropriate or threatening behaviour occurred.
- I need urgent help.

The interface may then provide blocking, reporting, trusted-contact sharing, guidance to seek venue staff, and access to the device's emergency-call capability when appropriate. It must not promise automatic emergency-service intervention unless such a process has been specifically designed, staffed, legally reviewed, and validated.

Check-ins are scheduled from the agreed meeting time, not continuous location monitoring. Responses are private and may inform moderation and risk detection. There are no public star ratings, public written reviews, attractiveness scores, personality scores, or public disclosure of who met whom.

Public trust indicators, if introduced, must be factual and privacy-preserving—for example verification state, membership duration, confirmed attendance aggregates, or carefully thresholded reliability signals. Private safety information must not become public reputation content.

## 5. Architectural approach

Kindlelise is a Django-first responsive web application. The core product must be usable from a mobile browser and installable as a progressive web application where supported.

The initial architecture deliberately excludes a separate SwiftUI or native client. A native application may be introduced later, but it must consume the same server-enforced rules and services. Important rules must never depend solely on browser or client behaviour.

Recommended platform components include:

- Django for domain logic, server-rendered views, administration, authentication integration, and security enforcement.
- PostgreSQL with PostGIS for production proximity queries.
- Django templates for the responsive interface.
- HTMX or limited JavaScript for incremental interactions where useful.
- Django Channels only where real-time messaging is justified.
- A background task system for plan expiry, notifications, check-ins, and moderation workflows.
- A specialist liveness and face-matching provider behind an internal verification interface.
- Web Push and email behind a notification service boundary.

Apple services such as Sign in with Apple, Face ID, Touch ID, Keychain, DeviceCheck, or App Attest may later secure authentication and a native client. They do not replace server-side face verification. Face ID confirms access to a device; it does not provide the application with a reusable face identity or compare a live selfie with a public profile photograph.

## 6. Domain boundaries

| Domain | Responsibility |
| --- | --- |
| `accounts` | Users, profiles, onboarding, privacy, dark profiles, verification state, participation restrictions, and provider integration. |
| `discovery` | The single proximity-first grid, proximity representation, filtering, availability, and exclusion of ineligible profiles. |
| `interests` | The controlled taxonomy used by profiles, plans, and discovery filters. |
| `plans` | Immediate and future plans, required URLs, places, times, free spare places, external-cost disclosure, status, and expiry. |
| `messaging` | Direct conversations, messages, real-time delivery where justified, and message-level safety signals. |
| `safety` | Blocking, reporting, meeting check-ins, trusted contacts, urgent-help flows, and incident intake. |
| `moderation` | Case management, evidence, risk signals, sanctions, appeals, duplicate-account investigation, and re-entry prevention. |
| `notifications` | Durable notification records, scheduling, email, web push, reminders, and safety-check delivery. |
| `common/security` | Reusable technical controls such as audit logging, rate limits, safe URL processing, and location privacy. |

`safety` and `common/security` must remain distinct. `safety` owns user-facing protection workflows and incident handling. `common/security` owns reusable technical protections that may be used by several domains.

`interests` remains a separate domain because its controlled taxonomy is shared by profiles, plans, and filters. `notifications` remains separate because delivery attempts, scheduling, retries, and safety-critical notification records require an explicit boundary.

## 7. Module placement rules

The complete scaffold is an architectural contract. Future work must extend the designated responsibility rather than create parallel or ambiguous modules.

| Concern | Required location |
| --- | --- |
| Durable domain state and database constraints | `apps/<domain>/models.py` |
| Permission and business-rule decisions | `apps/<domain>/policies.py` |
| Reusable query and read operations | `apps/<domain>/selectors.py` |
| State-changing use cases | `apps/<domain>/services/` |
| Single-value or input validation | `validators.py` or the designated shared security module |
| HTML form definition and input binding | `forms.py` |
| HTTP request and response translation | `views.py` |
| URL routing | `urls.py` |
| Scheduled and background execution entry points | `tasks.py` |
| Real-time socket handling | `consumers.py` and `routing.py` |
| User-facing domain templates | `apps/<domain>/templates/<domain>/` |
| Cross-domain page templates and components | top-level `templates/` |
| Cross-domain technical security controls | `common/security/` |
| Architecture and product decisions | `docs/` |
| Cross-domain behavioural verification | `tests/requirements`, `tests/integration`, `tests/journeys`, and `tests/security` |

Views must remain thin. They may authenticate, parse input, invoke selectors, policies, and services, and translate outcomes into HTTP responses. They must not become the authoritative home of business rules.

Forms and templates must not be the only enforcement point for verification, payment, URL, blocking, or safety rules. A modified client must not be able to bypass those rules.

Before creating a new module:

1. Inspect this architecture and the existing scaffold.
2. Identify which domain owns the responsibility.
3. Extend the existing designated module when that responsibility already has a home.
4. Do not introduce generic `utils.py`, `helpers.py`, alternative `services.py` files, or competing directories merely for convenience.
5. If no existing location is appropriate, record the reasoning in `docs/DECISIONS.md` before changing the architecture.

## 8. Scaffold policy

The agreed project tree should be created in full before feature implementation. This prevents later work from inventing misaligned files and creates a stable target for references, requirements, and future development.

Every scaffolded Python module should contain a module docstring stating:

- Its responsibility.
- What it may depend on.
- What must not be implemented there.
- Its current status.
- The requirement identifiers it is intended to cover, when known.

Every scaffolded template should contain a template comment stating its purpose, relevant requirement identifiers, and `Scaffold only` status.

Every scaffolded test module should describe its planned behaviours, but must not contain artificial tests that pass without verifying functionality. Placeholder tests must never create a false impression that a requirement has been implemented.

Implementation status should be tracked separately from the presence of scaffold files. A complete directory tree does not mean the application is complete.

## 9. Requirement discipline and traceability

Every significant product requirement must have a stable identifier and be traceable to:

1. A written rule or acceptance criterion.
2. A model constraint, validator, policy, selector, or service.
3. A visible interface state or deliberate non-interface enforcement.
4. One or more automated tests.

`docs/REQUIREMENTS.md` owns numbered requirements. `docs/TRACEABILITY.md` maps those requirements to implementation and tests.

Example:

| Requirement | Enforcement | Interface | Verification |
| --- | --- | --- | --- |
| `IDV-001` Mandatory private face verification | `accounts` policies and services | Verification gate and badge | Account and journey tests |
| `DSC-001` One proximity-first grid | Discovery selectors and proximity service | Discovery grid | Ordering and exclusion tests |
| `PLN-001` Public URL required | Plan validator and safe URL service | Plan form | URL validation tests |
| `PAY-001` No user-to-user payment | Plan policy and message safety | Attestation and reporting flow | Policy and journey tests |
| `SAF-001` Meeting check-in | Safety and notification tasks | Check-in prompt | Scheduling and journey tests |
| `BLK-001` Immediate two-way block | Safety service and discovery/message selectors | Block action | Visibility and contact tests |

Requirements should be grouped under accounts and verification, discovery, interests, plans, payment prohibition, messaging, safety, moderation, notifications, privacy, and technical security.

## 10. Critical requirement set

### Accounts and verification

- Private face verification is mandatory for participation.
- Unverified users do not appear in discovery and cannot create plans or messages.
- Visible and dark profiles use distinct, accurate verification labels.
- Verification is not described as legal identity, background, or safety verification.
- Verification provider callbacks are authenticated, idempotent, and audited.
- Verification media is minimised, protected, and retained only under a documented policy.
- Sanctions apply to the underlying verified account, not merely a public profile.
- Account deletion, appeal, and verification-failure routes are defined.

### Discovery and location

- The main experience is one proximity-first profile grid.
- No swipe or mutual match is required.
- Filters narrow the same grid rather than creating unrelated feeds.
- Available-now state and active plan context can appear on profile cards.
- Unverified, blocked, suspended, and otherwise ineligible profiles are excluded server-side.
- Distance disclosure balances usefulness with resistance to exact-location inference.
- Exact coordinates, direction, home location, movement history, and unnecessary precision are not exposed.
- Location is short-lived or coarsened according to the privacy model.

### Plans and URLs

- Every meeting proposal has a URL, place, and time.
- Plans may be immediate or future.
- Plans expire automatically.
- A plan may include a genuinely free spare ticket or place.
- Safe URL handling permits only appropriate schemes and protects against server-side request forgery, private-network access, DNS rebinding, unsafe redirects, and misleading normalisation.
- Venue metadata is informational and never overrides host confirmation or official source details.

### Payment prohibition

- Users cannot sell tickets or places.
- Hosts cannot request money, purchases, gifts, favours, tips, deposits, swaps, or reimbursement.
- Independent third-party costs are disclosed and paid directly to the third party.
- Optional personal purchases remain optional.
- Payment links and payment language may be flagged and reported.
- Enforcement applies to plans, profiles, and messages.

### Messaging

- Verified and eligible users can contact profiles directly without matching.
- Conversation access is limited to participants and authorised moderators under defined procedures.
- A concrete URL, place, and time are required before a meeting becomes a confirmed plan.
- Blocking immediately prevents further visibility and contact in both directions.
- Relevant evidence can be preserved when a report is submitted.
- Rate limits and abuse controls apply without revealing defensive thresholds.

### Safety and moderation

- Both participants receive a private check-in after the scheduled meeting begins.
- Safety responses are private and do not become public reviews.
- Urgent reports receive priority handling.
- Reports and blocks do not reveal the reporter or blocker.
- Serious reports preserve relevant evidence under a defined retention policy.
- Moderation decisions create durable audit records.
- Credible urgent risk may trigger temporary suspension.
- Users can appeal sanctions.
- Duplicate-account and ban-evasion signals inform review but do not silently become an unreviewable identity judgment.

## 11. Testing strategy

Tests are organised both by domain and by cross-domain behaviour.

- Domain directories verify models, validators, policies, selectors, services, forms, and views.
- `tests/requirements/` verifies individual numbered requirements.
- `tests/integration/` verifies cooperation between domains and infrastructure.
- `tests/journeys/` verifies complete user behaviours.
- `tests/security/` verifies adversarial and privacy-sensitive cases.

Essential journey tests include:

- A verified user publishes a gallery plan with a valid public URL.
- An unverified user cannot appear, publish, or message.
- A dark profile appears without publicly revealing its face.
- A nearby user filters for galleries and finds the plan.
- A guest contacts a host without swiping or matching.
- A meeting proposal cannot be confirmed without a URL, place, and time.
- A block immediately removes visibility and contact in both directions.
- A scheduled meeting triggers private check-ins for both participants.
- A payment request creates an appropriate safety signal and report path.
- A plan expires and disappears from active discovery.

Essential security tests include:

- Safe URL handling and server-side request forgery resistance.
- Location triangulation and precision-leak resistance.
- Horizontal access attempts against conversations, plans, reports, and verification records.
- Forged, replayed, and out-of-order verification webhooks.
- Block bypass and alternate-route contact attempts.
- Banned-account re-entry signals and moderation review.
- Report retaliation and information leakage.
- Rate-limit bypass attempts.
- Exposure of verification media or provider references.
- Unsafe notification content on locked devices.
- Audit record integrity.

## 12. MVP boundaries

### Included

- Responsive Django web application.
- Progressive web application support where appropriate.
- Private face-verification integration boundary.
- Visible and dark verified profiles.
- One proximity-first grid.
- Filters for interests, availability, time, distance, and plan characteristics.
- Available-now and future plans.
- Required public URLs, places, and times.
- Direct messaging without matching.
- Blocking, reporting, trusted contacts, and private check-ins.
- Moderation administration and audit records.
- Email and web-push notification boundaries.

### Excluded

- Native SwiftUI or Android clients.
- Swiping.
- Algorithmic or opaque matching.
- Mutual-match gates.
- Public star ratings or written reviews.
- Popularity or attractiveness scores.
- User-to-user payments.
- Ticket resale, bidding, or transfer-market infrastructure.
- Continuous real-world location tracking.
- Public movement history.
- Social followers, likes, or engagement-ranking mechanics.
- Claims that face verification guarantees identity, intentions, background, or safety.

## 13. Agreed project scaffold

```text
kindlelise/
├── README.md
├── .env.example
├── .gitignore
├── pyproject.toml
├── manage.py
│
├── config/
│   ├── __init__.py
│   ├── asgi.py
│   ├── urls.py
│   ├── wsgi.py
│   └── settings/
│       ├── __init__.py
│       ├── base.py
│       ├── development.py
│       ├── production.py
│       └── testing.py
│
├── apps/
│   ├── accounts/
│   │   ├── migrations/
│   │   ├── verification/
│   │   │   ├── base.py
│   │   │   ├── provider.py
│   │   │   └── webhooks.py
│   │   ├── services/
│   │   │   ├── onboarding.py
│   │   │   ├── face_verification.py
│   │   │   └── account_restrictions.py
│   │   ├── templates/accounts/
│   │   │   ├── onboarding.html
│   │   │   ├── profile.html
│   │   │   ├── profile_edit.html
│   │   │   ├── verification.html
│   │   │   └── privacy.html
│   │   ├── admin.py
│   │   ├── forms.py
│   │   ├── models.py
│   │   ├── policies.py
│   │   ├── selectors.py
│   │   ├── permissions.py
│   │   ├── urls.py
│   │   └── views.py
│   │
│   ├── discovery/
│   │   ├── services/
│   │   │   ├── proximity.py
│   │   │   └── filtering.py
│   │   ├── templates/discovery/
│   │   │   ├── grid.html
│   │   │   ├── filters.html
│   │   │   └── partials/
│   │   │       ├── profile_card.html
│   │   │       └── grid_results.html
│   │   ├── filters.py
│   │   ├── selectors.py
│   │   ├── urls.py
│   │   └── views.py
│   │
│   ├── interests/
│   │   ├── migrations/
│   │   ├── admin.py
│   │   ├── models.py
│   │   ├── selectors.py
│   │   └── services.py
│   │
│   ├── plans/
│   │   ├── migrations/
│   │   ├── services/
│   │   │   ├── create_plan.py
│   │   │   ├── update_plan.py
│   │   │   ├── plan_expiry.py
│   │   │   └── venue_metadata.py
│   │   ├── templates/plans/
│   │   │   ├── create.html
│   │   │   ├── detail.html
│   │   │   ├── edit.html
│   │   │   └── partials/
│   │   │       ├── plan_status.html
│   │   │       └── plan_preview.html
│   │   ├── admin.py
│   │   ├── forms.py
│   │   ├── models.py
│   │   ├── validators.py
│   │   ├── policies.py
│   │   ├── selectors.py
│   │   ├── tasks.py
│   │   ├── urls.py
│   │   └── views.py
│   │
│   ├── messaging/
│   │   ├── migrations/
│   │   ├── services/
│   │   │   ├── conversations.py
│   │   │   ├── messages.py
│   │   │   └── message_safety.py
│   │   ├── templates/messaging/
│   │   │   ├── inbox.html
│   │   │   ├── conversation.html
│   │   │   └── partials/
│   │   │       └── message.html
│   │   ├── consumers.py
│   │   ├── models.py
│   │   ├── policies.py
│   │   ├── selectors.py
│   │   ├── routing.py
│   │   ├── urls.py
│   │   └── views.py
│   │
│   ├── safety/
│   │   ├── migrations/
│   │   ├── services/
│   │   │   ├── blocking.py
│   │   │   ├── reporting.py
│   │   │   ├── check_ins.py
│   │   │   ├── incident_response.py
│   │   │   └── trusted_contacts.py
│   │   ├── templates/safety/
│   │   │   ├── check_in.html
│   │   │   ├── report.html
│   │   │   ├── block.html
│   │   │   └── urgent_help.html
│   │   ├── admin.py
│   │   ├── forms.py
│   │   ├── models.py
│   │   ├── policies.py
│   │   ├── selectors.py
│   │   ├── tasks.py
│   │   ├── urls.py
│   │   └── views.py
│   │
│   ├── moderation/
│   │   ├── migrations/
│   │   ├── services/
│   │   │   ├── cases.py
│   │   │   ├── sanctions.py
│   │   │   ├── risk_signals.py
│   │   │   ├── duplicate_accounts.py
│   │   │   └── evidence.py
│   │   ├── templates/moderation/
│   │   │   ├── queue.html
│   │   │   └── case.html
│   │   ├── admin.py
│   │   ├── models.py
│   │   ├── policies.py
│   │   ├── selectors.py
│   │   ├── urls.py
│   │   └── views.py
│   │
│   └── notifications/
│       ├── migrations/
│       ├── services/
│       │   ├── email.py
│       │   ├── web_push.py
│       │   └── scheduling.py
│       ├── models.py
│       ├── selectors.py
│       └── tasks.py
│
├── common/
│   ├── models.py
│   ├── exceptions.py
│   ├── middleware.py
│   ├── permissions.py
│   └── security/
│       ├── audit.py
│       ├── rate_limits.py
│       ├── safe_urls.py
│       └── location_privacy.py
│
├── templates/
│   ├── base.html
│   ├── home.html
│   ├── about.html
│   ├── rules.html
│   ├── privacy.html
│   ├── terms.html
│   ├── 403.html
│   ├── 404.html
│   ├── 500.html
│   └── components/
│       ├── navigation.html
│       ├── verification_badge.html
│       ├── empty_state.html
│       ├── dialog.html
│       └── toast.html
│
├── static/
│   ├── css/
│   │   ├── base.css
│   │   ├── grid.css
│   │   ├── profiles.css
│   │   ├── messaging.css
│   │   └── safety.css
│   ├── js/
│   │   ├── location.js
│   │   ├── filters.js
│   │   ├── messaging.js
│   │   ├── check-in.js
│   │   └── install.js
│   ├── icons/
│   └── manifest.webmanifest
│
├── tests/
│   ├── accounts/
│   ├── discovery/
│   ├── interests/
│   ├── plans/
│   ├── messaging/
│   ├── safety/
│   ├── moderation/
│   ├── notifications/
│   ├── requirements/
│   ├── integration/
│   ├── journeys/
│   ├── security/
│   ├── factories.py
│   └── conftest.py
│
├── docs/
│   ├── PRODUCT.md
│   ├── REQUIREMENTS.md
│   ├── TRACEABILITY.md
│   ├── USER_FLOWS.md
│   ├── PRODUCT_RULES.md
│   ├── DATA_MODEL.md
│   ├── SAFETY_MODEL.md
│   ├── THREAT_MODEL.md
│   ├── PRIVACY_MODEL.md
│   ├── MODERATION.md
│   ├── DEPLOYMENT.md
│   └── DECISIONS.md
│
├── deployment/
│   ├── Dockerfile
│   ├── compose.yml
│   ├── nginx.conf
│   └── entrypoint.sh
│
└── scripts/
    ├── seed_interests.py
    ├── seed_demo_profiles.py
    └── expire_plans.py
```

When this scaffold is created, `docs/ARCHITECTURE.md` must also remain in `docs/` as the governing architectural contract even though it is not shown in the originally agreed tree.

## 14. Governance

Architecture changes are permitted when evidence shows that the existing boundary is wrong or insufficient. They must not happen implicitly during feature work.

Any structural change should:

1. Identify the problem with the current architecture.
2. Explain why the existing designated module cannot own the responsibility.
3. Describe alternatives considered.
4. Record the decision in `docs/DECISIONS.md`.
5. Update this document, the scaffold, requirements, traceability, and affected tests together.

The goal is not to preserve a tree for its own sake. The goal is to preserve a coherent product model in which privacy, verification, proximity, plans, direct contact, payment prohibition, and safety remain aligned as the application grows.
