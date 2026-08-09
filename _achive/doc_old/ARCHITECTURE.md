# Kindlelise Architecture

> **Archived:** historical supporting document. The active implementation
> authority is [`docs/VERTICAL_SLICE.md`](../../docs/VERTICAL_SLICE.md).

Student MVP architecture aligned with the Kindlelise 36-File Vertical Slice.

## Status and authority

This document explains how the Kindlelise student MVP fits together.

[`docs/VERTICAL_SLICE.md`](../../docs/VERTICAL_SLICE.md) is the authoritative implementation contract. This architecture must not add files, models, functions, routes or features that are absent from that contract. If the documents disagree, the vertical-slice document wins.

The target is a working, readable and defendable student project—not a production-scale social network.

Implementation status: designed, not yet implemented or confirmed by generated
PostgreSQL migrations and behavioural tests.

## 1. Architectural goal

The target journey is:

```text
register or sign in
→ create a profile
→ receive manual staff verification
→ discover eligible profiles in broad areas
→ create a public-place plan
→ receive manual staff plan approval
→ join or leave the plan
→ exchange direct messages
→ block or privately report an account
```

Two deliberately small external integrations support that journey:

- Stripe provides one no-card 30-day Premium trial followed by one GBP 4.99
  yearly subscription through hosted Checkout, invoices and the hosted customer
  portal.
- Ollama Cloud can edit the user's current unsent message draft after an explicit button press.

Neither integration is an identity, age-verification, safety or moderation authority.
The assessment uses supervised test accounts only. It does not implement age
verification and is not architecture for unrestricted public use.

## 2. System shape

Kindlelise is one server-rendered Django application backed by PostgreSQL.

```text
Mobile or desktop browser
        │
        ▼
Django URLs and views
        │
        ├── forms validate submitted values
        ├── policies answer permission questions
        ├── selectors perform reusable reads
        └── services perform state-changing workflows
                    │
                    ▼
              Django models
                    │
                    ▼
                PostgreSQL

Django Admin ──→ manual profile, plan and report handling
Stripe API ────→ hosted billing pages and signed webhooks
Ollama Cloud ──→ optional editing of one unsent draft
```

There are no microservices, background workers, WebSockets or separate domain applications in the student MVP.

## 3. Architectural style

All product code lives in the single `kindlelise` Django app. Responsibility is separated by module rather than by adding more apps or abstraction layers.

```text
urls → views → forms / policies / selectors / services
services → policies / models
selectors → policies / models
admin → services / models
ai_message_editor → configured Ollama Cloud API only
models → Django ORM and standard value types only
```

The boundaries mean:

- `models.py` owns durable data and database constraints.
- `forms.py` validates user-entered values.
- `policies.py` answers whether an action is allowed without changing data.
- `selectors.py` performs reusable, side-effect-free reads.
- `services.py` owns state changes and transaction boundaries.
- `views.py` translates HTTP requests into calls to those modules.
- `admin.py` exposes the four approved staff actions and the related-profile
  verification checkbox on Django's User Permissions form.
- `ai_message_editor.py` is the only module permitted to call Ollama Cloud.

Do not introduce repositories, command buses, event buses, plugin systems, generic workflow engines or background-task abstractions for this slice.

## 4. Authoritative 36 implementation-file maximum

The implementation contract permits at most 36 implementation files. The 33
currently mapped files are listed below; an unused mapped file may remain absent.
Supporting governance and assessment documents sit outside that count. Normal
numbered Django schema migrations and the reviewed initial-interest data migration
are documented mechanical exceptions. This architecture owns no implementation
responsibility and cannot expand the list. Three slots remain deliberately
unallocated.

```text
01  .gitignore
02  .env.example
03  README.md
04  manage.py
05  pyproject.toml

06  config/__init__.py
07  config/settings.py
08  config/urls.py
09  config/asgi.py
10  config/wsgi.py

11  kindlelise/__init__.py
12  kindlelise/apps.py
13  kindlelise/admin.py
14  kindlelise/models.py
15  kindlelise/forms.py
16  kindlelise/policies.py
17  kindlelise/services.py
18  kindlelise/selectors.py
19  kindlelise/views.py
20  kindlelise/urls.py
21  kindlelise/ai_message_editor.py
22  kindlelise/migrations/__init__.py

23  templates/base.html
24  templates/discover.html
25  templates/account.html
26  templates/plan.html
27  templates/inbox.html
28  templates/conversation.html
29  templates/report.html

30  static/app.css
31  static/app.js

32  tests/conftest.py
33  tests/test_vertical_slice.py
```

Other reconciled documents explain product, privacy, safety and requirements. They are not additional code owners and do not justify adding implementation files.

## 5. Durable data model

Django's built-in `User` model owns credentials and authentication. Kindlelise adds exactly ten student-MVP models.

| Model | Plain-language purpose |
| --- | --- |
| `Profile` | Public profile details, broad area, availability and staff verification state for one user. |
| `Interest` | One item in the small staff-seeded interest vocabulary. |
| `Plan` | A proposed meeting at an independently established public place and time. |
| `Participation` | One user's current or historical relationship to one plan. |
| `Conversation` | The single direct conversation allowed for an unordered pair of users, stored lower-ID first. |
| `Message` | One plain-text message sent inside a conversation. |
| `Block` | A directional block from one account to another. |
| `Report` | A private report about another account, with an optional relevant reference. |
| `PlatformSubscription` | The local projection of one user's Stripe subscription access. |
| `StripeWebhookReceipt` | A verified event identifier, provider time and successful processing time. |

```text
Django User ──1:1── Profile
      │                 └── interests ↔ Interest
      │
      ├── creates ──→ Plan ──→ Participation ←── user
      ├── converses through ──→ Conversation ──→ Message
      ├── creates ──→ Block
      ├── submits ──→ Report
      └── 1:1 ──→ PlatformSubscription

StripeWebhookReceipt records processed provider events.
```

### Required database constraints

The database—not only form code—must enforce:

- one profile and one platform subscription per user;
- verified profiles have both verification review fields and unverified profiles
  have neither;
- a unique interest name;
- one participation record per user and plan;
- joined participation has no `left_at`, while left participation has one;
- a positive plan capacity;
- approved plans have both approval fields and every other plan state has neither;
- a consistently ordered, unique user pair for each conversation;
- a unique directional block and no self-block;
- no self-report;
- at most one optional report context reference;
- unique Stripe customer, subscription and webhook event identifiers when present.

Foreign-key deletion behaviour is explicit in the data model: referenced reviewer
accounts and retained history are protected, while records with no meaning after
an account is deleted use only the approved cascades. Referenced staff accounts
are deactivated rather than physically deleted.

### Required indexes

Only the indexes mapped by the vertical slice are included:

- `Profile(is_verified, broad_area)`;
- `Plan(status, starts_at)`;
- `Participation(plan, status)` and `Participation(user, status)`;
- `Conversation(first_user, updated_at)` and `Conversation(second_user, updated_at)`;
- `Message(conversation, sent_at)`;
- `Report(status, received_at)`.

## 6. Accounts and discovery

### Account flow

Registration creates the Django user and its initially incomplete, unverified
profile together in one transaction. The new profile may begin with empty
`display_name` and `broad_area` onboarding values. Profile editing uses the mapped
account form and service to require a non-empty display name and a configured
broad-area key. Staff verification is a manual Django Admin control and refuses an
incomplete profile; Stripe and Ollama never verify identity or age.

Successful registration redirects to the named sign-in route without starting a
session. After the user signs in, the unverified account lands on its private
account page.

Registration and sign-in use one canonical lowercase email and password through
Django's normal authentication. The same value is stored in Django's unique
username field and email field, avoiding a custom User model or authentication
backend. Authenticated verified users land on
discovery; authenticated unverified users land on their private account page.

Only authenticated, active and manually verified accounts may use discovery, plans or messaging.

### Location and availability

The MVP stores a stable configured broad-area key, displayed as a named district.
`config/settings.py` owns the approved keys, labels and nearby-area mapping. Forms
reject arbitrary area text. It does not collect browser coordinates, calculate
exact distance or retain location history.

`available_from` is an optional availability-start statement calculated from the
profile owner's form-only Free now switch or Today, Tomorrow, This week or As and
when choice. It is not required for profile completion or staff verification and
can be cleared later. The profile switch stores no duplicate boolean.
The `Free now` discovery switch returns only profiles whose start has arrived;
there is no second stored presence boolean.

### Discovery flow

```text
authenticated verified viewer
→ validate broad-area, interest and available-now filters
→ apply free or Premium filter limits
→ query verified eligible profiles
→ exclude the viewer and blocked relationships
→ render the profile grid
```

Free members can use the current area and up to two interest filters. Premium
members can include the configured nearby broad areas and use up to five interest
filters. Premium changes reach and filter limits only; it never bypasses
verification, blocks, privacy or safety rules.

A reviewed initial data migration seeds Coffee, Walking, Museums, Live music,
Cinema, Food, Games and Study. Staff may maintain that controlled vocabulary in
Django Admin; ordinary users can only select existing interests.

## 7. Plans and participation

### Plan publication flow

```text
creator submits plan form
→ form validates title, description, public place, normal HTTPS evidence URL, time and capacity
→ service saves a pending plan
→ staff opens the submitted URL manually
→ staff approves or rejects the plan in Django Admin
→ only an approved future plan enters the public plan list and becomes joinable
```

The URL must identify an independently established public place or organised activity. A dropped map pin, residential address, payment link or personal social-media post cannot be approved as primary evidence.

The server does not fetch, scrape or substantiate remote pages. Manual approval records a limited staff decision based on the submitted URL; it does not preserve the reviewed page, prove that the venue controls the plan or guarantee real-world safety.

The public plan list contains approved future plans and the signed-in owner's own pending, rejected or cancelled plans. It never exposes another owner's unapproved plan.

### Editing and locking

- Before anybody joins, the creator may edit a pending, approved or rejected plan.
- Changing an approved plan's public place, public URL or start time before anybody joins resets it to pending staff approval.
- Saving a rejected unlocked plan resubmits it as pending review.
- The first successful join makes the whole plan read-only except cancellation.
- Cancellation removes the plan from discovery, prevents future joins and clears
  its current approval fields. It does not delete participation history or make
  the cancelled plan active again.
- Cancelled plans are terminal and cannot be edited, approved or reactivated.
- Capacity counts participant places only; the owner consumes no participant place.

### Joining transaction

Joining is a service-layer transaction:

```text
lock the plan row with select_for_update()
→ recheck approval, time, capacity, ownership and eligibility
→ create or reactivate the participant's record under the documented rejoin rule
→ make the plan read-only after the first successful join
→ commit
```

Leaving changes the one participation row for the user and plan from `joined` to
`left`, records `left_at` and preserves the row. Rejoining is allowed only while
the plan remains approved, future, uncancelled and below capacity; it changes the
same row back to `joined`, refreshes `joined_at` and clears `left_at`. An existing
`left` row is eligible for reactivation, while a current `joined` row is refused.
Historical participation is never silently deleted.

## 8. Direct messaging, blocking and reporting

### Conversations

A conversation contains exactly two users. The lower user ID is always stored first.

```text
calculate the ordered user pair
→ try to create the conversation
→ database unique conflict
→ retrieve the existing conversation
→ return the one authoritative conversation
```

The service handles `IntegrityError` so simultaneous conversation-start requests
cannot create duplicate conversations.

Opening or sending in a conversation requires membership, two active verified accounts and no block in either direction. Messages use ordinary page refreshes; there are no WebSockets. A successful send updates the conversation's ordering timestamp.

### Blocking

A block applies in both interaction directions even though its stored record is directional. Blocked pairs must not:

- appear to one another in discovery;
- start or continue a conversation;

The student slice maps no unblock workflow or route. Removing a block or adding a
revocation field requires the normal boundary-change approval.

A block does not prevent the affected account from submitting a private report.

### Reporting

Every visible profile, plan and conversation exposes a clear reporting action.
Reports are private to the reporter at submission and confirmation and to
authorised staff. The slice has no report-history page or report-list selector for
ordinary users.

A report may contain at most one optional reference. Both the reporter and reported
account must be connected to a referenced plan as owner or participant. A
referenced conversation must contain both accounts. A referenced message must
belong to that two-account conversation and have been visible to the reporter. The
MVP stores the report and staff handling status; it does not implement findings,
sanctions, appeals, evidence vaults or public accusation records.

## 9. Stripe Premium integration

Stripe owns payment collection and subscription management. Kindlelise never stores card data.
Checkout success, Checkout cancellation and customer-portal return destinations
are constructed by the server from the named account route. Browser input never
supplies a Stripe return URL.

The one configured Stripe Price is GBP 499 recurring yearly. A local account
without recorded Stripe history receives exactly 30 trial days through Checkout,
with payment-method collection only if required and post-trial invoice creation
when no payment method exists. Stripe history exhausts trial eligibility; later
eligible Checkout omits the trial, while an active or trialing subscription is
managed rather than duplicated. The paid subscription renews yearly unless it is
cancelled in Stripe's customer portal.

### Browser-initiated billing

```text
authenticated account
→ server creates Stripe-hosted Checkout or portal session
→ Checkout records the immutable local user ID in `client_reference_id` and subscription metadata
→ external Stripe call completes outside a database transaction
→ browser is redirected to Stripe
```

Returning from Checkout does not grant Premium. The signed webhook is authoritative.

### Supported webhook events

The MVP processes only:

- `checkout.session.completed`;
- `customer.subscription.updated`;
- `invoice.paid`;
- `customer.subscription.deleted`.

```text
receive raw request body
→ verify Stripe signature
→ identify the account from trusted Stripe metadata or stored provider IDs
→ reject a customer or subscription ID already linked to another account
→ atomically claim the unique event receipt
→ compare subscription-state events using provider event time
→ update PlatformSubscription
→ mark the receipt processed
```

Premium access requires webhook-authorised trial or paid evidence and a future
`access_until`. Email is never used as subscription ownership proof.

`checkout.session.completed` records trusted customer and subscription identifiers
only. It never grants Premium or advances `latest_provider_event_at`. A verified
`customer.subscription.updated` event may grant trial access only when its status
is `trialing` and its trial end is in the future. An `active` update alone is not
payment evidence and cannot extend the paid period. Only `invoice.paid` for the
linked configured price and active subscription grants the invoice's future paid
annual service period.

Provider timestamps can tie. At the current ordering timestamp, deletion may
revoke access, while an equal-time non-deletion event cannot overwrite already
accepted state. Older, duplicate and safely refused equal-time events do not
change the subscription projection; safely handled supported events still have a
committed receipt with `processed_at`.

Because Stripe delivers related event types asynchronously, a delayed
`invoice.paid` may extend `access_until` to its later paid service-period end when
the linked subscription has not been revoked by a newer deletion or ineligible
state. It never rewinds status or revives a cancelled subscription.

For `customer.subscription.deleted`, the projection must set:

```text
stripe_status = cancelled
access_until = null
latest_provider_event_at = event creation time
```

Raw webhook payloads and payment details are not stored. Duplicate events are safe because the receipt event ID is unique and receipt processing shares the subscription transaction.

A processing failure rolls back both the new receipt and subscription change, so
no failed unprocessed receipt remains committed. Signature-valid unsupported
events are acknowledged without a receipt or subscription change. Subscription
deletion retains the stored Stripe customer and subscription identifiers for safe
event matching and customer-portal ownership.

The webhook returns `400` for an invalid signature or malformed signed JSON,
`200` for unsupported, duplicate, stale, safely refused equal-time or successfully
applied events, and `500` only when supported processing rolls back so Stripe
should retry.

## 10. Ollama Cloud message editing

AI editing is an optional writing aid, not an autonomous messaging feature.

```text
conversation member with active verification and no block in either direction
→ user enters an unsent draft
→ user explicitly chooses “Fix grammar” or “Improve clarity”
→ server validates conversation access, goal and length
→ send only that draft and fixed editing instruction to Ollama Cloud
→ enforce timeout and bounded output
→ present a suggestion without changing the original draft
→ user accepts it into the draft, changes it or rejects it
→ normal message validation runs again
→ user manually sends
```

`ai_message_editor.py` is the only Ollama owner. It must not receive conversation history, profile data, reports, blocks or other messages. It must not save drafts, persist suggestions or send messages. On failure, the original draft remains unchanged.

The configured model name and credentials come from environment settings. Provider responses are untrusted text and must pass the same length and rendering rules as user-written content.

## 11. HTTP, routes and presentation

`kindlelise/urls.py` owns every product route. Views remain thin: authenticate, bind a form, call one policy/selector/service, and render or redirect.

State changes use `POST` and Django CSRF protection. The Stripe webhook is CSRF-exempt only because it authenticates the raw request with Stripe's signature.

### Template ownership

| Template | Screens it may render |
| --- | --- |
| `base.html` | Shared shell, notices and navigation. |
| `discover.html` | Broad-area profile grid, interest and available-now filters, empty state and free/Premium limit explanation. |
| `account.html` | Registration, sign-in, own/public profile, profile editing and Premium controls. |
| `plan.html` | Plan list, creation, editing, detail and participation actions. |
| `inbox.html` | Direct conversation list. |
| `conversation.html` | Message history, draft editor, AI edit controls, block and report access. |
| `report.html` | Private report form and confirmation. |

`static/app.css` owns the mobile-first visual system. `static/app.js` provides only small progressive enhancement, principally the explicit AI-edit request and replacing the draft after user confirmation. Core account, plan, messaging, block and report journeys must still work without JavaScript.

All message and user text is stored as plain text and escaped by Django templates. User content is never rendered with `safe` or interpreted as HTML.

## 12. Django Admin

The ordinary Django Admin screens expose profiles, interests, plans, reports, subscriptions and webhook receipts.

Four custom staff list actions are required:

1. mark a profile verified only after its display name and configured broad area
   are complete;
2. remove profile verification;
3. approve a pending future unlocked plan after manually reviewing its public-place URL;
4. reject a pending unlocked plan.

Profile verification is also available as a form-only checkbox in Django's User
Permissions section. It requires both User and Profile change permission, applies
the same completion rule and records or clears the same reviewer/time fields.

These transitions are owned by `admin.py`; the vertical slice does not map
separate verification or approval services. Each list action iterates through
its selected records, rechecks that every transition remains valid, changes
eligible records individually and reports how many were changed or skipped. No
path blindly uses `queryset.update()`. Custom admin routes, moderation dashboards
and provider work queues are not part of this slice.

## 13. Configuration and deployment

`config/settings.py` owns:

- installed Django components and middleware;
- PostgreSQL connection settings;
- templates and WhiteNoise static-file serving;
- secure cookie, HTTPS and trusted-host settings;
- Stripe keys, webhook secret and the one Premium price ID;
- Ollama Cloud endpoint, model name, credential and timeout;
- secrets read from environment variables.

Uploaded media is not part of the student MVP.

The deployment target is Heroku with PostgreSQL and Gunicorn serving `config.wsgi`.
WhiteNoise serves collected project static files with `DEBUG = false`; uploaded
media is not supported. `config.asgi` remains the standard Django entry point and
does not add sockets or Channels.

Dependencies should remain minimal: Django, a PostgreSQL driver, Stripe's
supported SDK, WhiteNoise, Gunicorn and the selected test packages. Add an HTTP
client only when the standard library would make the small Ollama boundary
materially less clear.

## 14. Security and privacy boundaries

- Django owns password hashing, sessions and authentication.
- Every private selector and state-changing service checks the current account explicitly.
- Forms reject unknown choices and enforce bounded text lengths.
- Services fail closed when verification, subscription or provider state is unclear.
- Discovery exposes broad areas, never coordinates or exact distance.
- Blocks are applied before discovery profiles, conversations or messages are
  returned; the vertical slice does not add block-based plan filtering.
- Reports, Stripe identifiers and webhook receipts are never public.
- Stripe and Ollama secrets exist only in environment configuration.
- Logs omit message bodies, report narratives, raw webhook bodies and Ollama drafts.
- External network calls occur outside database transactions.
- A verified Stripe webhook may change only the mapped Premium projection. Ollama
  output never authorises access or sends user content.

## 15. Testing architecture

`tests/conftest.py` provides small reusable users, profiles, plans, conversations and provider fixtures. `tests/test_vertical_slice.py` owns all behaviour tests so the test structure does not recreate the removed multi-app architecture.

The highest-risk checks come first:

1. all ten models migrate successfully on PostgreSQL;
2. every mapped constraint and index appears in the generated migration;
3. registration creates an incomplete unverified profile that staff cannot verify
   before display name and broad area are complete;
4. concurrent plan joins cannot exceed capacity;
5. a left participant can rejoin by reusing the same row;
6. concurrent conversation creation returns one pair;
7. Stripe events are signature-checked, idempotent and ordered, including the
   equal-time deletion rule;
8. deleted subscriptions clear `access_until`;
9. blocks remove discovery and direct-message access in either direction;
10. report-plan references require both accounts as owner or participant, while
   conversation/message references use the exact two-account visibility rule;
11. AI editing requires conversation access, preserves the draft until acceptance
    and never sends automatically.

After those pass, test the complete HTTP journey, permissions, form failures and template escaping.

## 16. Failure behaviour

The system should fail simply and safely:

- invalid or unauthorised objects return a generic unavailable response;
- failed external calls preserve the user's current page and input where safe;
- a failed Stripe redirect creates no Premium access;
- an invalid or duplicate webhook creates no duplicate entitlement;
- failed Ollama editing leaves the original unsent draft untouched;
- a join conflict is rechecked and shown as an ordinary capacity or eligibility failure;
- staff approval does not hide the documented limits of manual URL review.

## 17. Explicitly deferred architecture

The following are outside this implementation and must remain future-work documentation only:

- separate Django domain apps, microservices or a public API;
- native applications, PWA infrastructure, HTMX, Channels or WebSockets;
- PostGIS, browser coordinates, exact distance, live tracking or location history;
- automated identity, face, liveness or age-verification providers;
- background workers, scheduled jobs, push notifications or email delivery;
- remote URL fetching, DNS protection, AI substantiation or evidence-version models;
- meet artifacts, plan lineages, invitations, temporary presence or social circles;
- private safety experiences, blind corroboration, check-ins or trusted contacts;
- moderation findings, sanctions, appeals or public safety labels;
- image uploads, albums, social links or content moderation pipelines;
- multiple subscriptions, local invoice models, coupons or a general billing
  ledger;
- AI reply generation, moderation, translation, conversation memory or automatic sending;
- analytics warehouses, general audit-event systems or complex observability platforms.

Future work does not reserve files, models or partially implemented functions in the MVP.

## 18. Architecture change procedure

Before adding a file, model, route, dependency, workflow or feature, or expanding
an existing owner's responsibility:

1. state the concrete student-MVP problem;
2. show why an existing mapped owner cannot solve it clearly;
3. identify the smallest readable change;
4. explain its security, privacy, data and testing effects;
5. obtain explicit approval;
6. update `docs/VERTICAL_SLICE.md` and `docs/DECISIONS.md` before implementation.

A small public function inside an existing approved responsibility does not need
a new architecture decision. It still needs a concrete implementation reason,
an entry in the vertical slice's public function map and a behavioural test in
the same change.

The default decision is to keep the existing boundary. Refactoring is justified by demonstrated implementation difficulty, not by speculative future scale.
