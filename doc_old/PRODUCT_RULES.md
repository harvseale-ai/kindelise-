# Kindlelise Student MVP Product Rules

> **Archived:** historical supporting document. Current behaviour is governed by
> `docs/VERTICAL_SLICE.md` and `docs/DECISIONS.md`.

> **Status: supporting student-MVP rulebook.** `docs/VERTICAL_SLICE.md` is the
> implementation authority. These rules explain its invariants in plain language
> and cannot add a model, route, function, file or feature. If the documents
> conflict, the vertical slice wins.

## 1. How to read these rules

- **Must** means the implementation and its behavioural tests enforce the rule.
- **Must not** means the behaviour is prohibited in this MVP.
- **May** means an already mapped optional presentation or user choice.
- A hidden button is not enforcement. Server policies, services, selectors and
  database constraints remain authoritative.
- Rules marked deferred are future research and must not be partially scaffolded.

The assessed journey is:

```text
register or sign in
→ complete profile
→ receive manual staff verification
→ enter broad-area discovery
→ create and receive approval for a plan
→ join or leave
→ exchange direct messages
→ block or privately report
```

Stripe supplies one no-card 30-day Premium trial followed by a GBP 4.99 yearly
platform subscription. Ollama Cloud supplies one optional unsent-draft editing
action.

The assessment uses supervised test accounts only. It does not implement age
verification and must not be presented as ready for unrestricted public use.

## 2. Account and verification rules

### PR-ACC-001 — One account has one profile

Registration must create one Django account and its unverified profile in one
transaction. A partial account/profile pair must not remain after failure.

### PR-ACC-002 — Django owns authentication

Django must own password hashing, authentication, sessions and CSRF protection.
Kindlelise must not store a second password or create a replacement account model.
Registration and sign-in use one canonical lowercase email and password through
Django. The same email is stored in the unique username field and email field;
Stripe still never uses it as ownership proof. Registration creates the account
and profile, then redirects to sign-in without authenticating the new account.
Sign-out is a CSRF-protected POST action.

### PR-ACC-003 — Staff verification gates social access

Only an active account with a staff-verified profile may use discovery, create or
join plans, start or continue direct conversations, or request an Ollama draft
edit. Being signed in or paying for Premium is not verification.

An unverified account may view and edit its own permitted profile fields and see
its verification state.

### PR-ACC-004 — Verification is manual and limited

Authorised staff set or remove current verification through mapped Django Admin
actions. The action records the staff account and time and rechecks each selected
profile. It grants verification only when the profile has a non-empty display
name and a broad-area key currently present in `KINDLELISE_AREAS`. It must not be
described as biometric, document, age, identity or safety proof.

### PR-ACC-005 — Authentication responses do not leak account state

Sign-in errors must not reveal whether a particular email exists. After sign-in,
the server may follow only a validated local redirect destination; it must reject
external or otherwise unsafe redirect targets. Session rotation and authentication
remain Django responsibilities.

## 3. Profile, interest and availability rules

### PR-PRO-001 — Profile fields are deliberately small

A user may edit only display name, short biography, broad named area, controlled
interests and the optional fixed availability-start choice. The browser must not
edit verification, Stripe ownership or subscription fields.

The MVP has no uploaded profile image, external social handles, health fields,
ethnicity, sexuality, weight, private-home meeting preference or dark-profile
mode.

### PR-PRO-002 — Interests use a fixed vocabulary

Profiles and discovery filters use a small staff-seeded `Interest` vocabulary.
Users must not create free-text interests. The profile-interest relationship has
no custom model because it carries no additional state.

A reviewed initial data migration seeds Coffee, Walking, Museums, Live music,
Cinema, Food, Games and Study. Staff may maintain the vocabulary through Django
Admin; initial setup does not depend on manual entry.

### PR-PRO-003 — Free now is start-based and derived

`Free now` is true only when the calculated `available_from` exists and is no
later than the current time. There is no second boolean or presence-history
model. A form-only Free now switch starts the same signal immediately; it is not
stored separately. A user may instead choose Today, Tomorrow, This week or As and
when, or clear the signal through profile editing. Availability is optional and
never gates profile completion or staff verification.

The start signal remains current until the owner clears or replaces it. It does
not imply physical presence, agreement to meet or continuous app use.

## 4. Discovery rules

### PR-DSC-001 — Discovery is a profile grid

Discovery contains eligible profile cards only. It is not swiping, matching, a
plan grid, an invitation list or paid ranking.

### PR-DSC-002 — Discovery uses broad named areas

Kindlelise must not collect or display browser coordinates, exact distance,
direction or movement history. `settings.py` owns stable area keys, display labels
and the nearby-area mapping. Profile and filter forms store configured keys and
reject arbitrary area text.

### PR-DSC-003 — Privacy exclusions happen before presentation

A selector must exclude inactive or unverified profiles and either-direction
blocks before returning any result to the view or template. The interface must
not reveal why a profile is absent or how many hidden results exist.

### PR-DSC-004 — Filters have simple free and premium limits

All eligible users may filter controlled interests and optionally require an
`available_from` start that has arrived.

- Free: current broad area and at most two interest filters.
- Premium: current area plus configured nearby broad areas and at most five
  interest filters.

Premium must not weaken verification, blocking or visibility rules.

## 5. Plan and staff-review rules

### PR-PLN-001 — A plan has one public-place proposal

A plan contains one owner, title, description, established public place, public
HTTPS evidence URL, start time and positive capacity. The URL must identify an
independently established public place or organised activity.

A dropped map pin, residential address, payment link or personal social post must
not be accepted as primary evidence. Kindlelise has no plan ticket, attendance
payment or host-payout workflow.

### PR-PLN-002 — Plan review is manual

New plans begin Pending review. Authorised staff manually open the public URL
outside Kindlelise and approve or reject the plan through mapped Django Admin
actions.

Kindlelise records status, reviewer and time only. It must not fetch, scrape,
archive, substantiate or send the URL to AI, and it must not claim that approval
proves venue safety or preserves what staff saw.

Bulk staff actions must iterate through selected plans, recheck current state and
skip locked, cancelled or otherwise ineligible records. They must not use a blind
bulk update that bypasses the ordinary review rules.

### PR-PLN-003 — Plan visibility follows status and ownership

- The owner and authorised staff may see the owner's pending, rejected or
  cancelled plan.
- Only approved future plans enter the public plan list.
- Rejected, cancelled, past or unapproved plans must not accept joins.
- Cancellation removes the plan from public lists and prevents future joins
  without deleting the plan or participation history.

### PR-PLN-004 — Editing before a join is bounded

Only the owner may edit a pending, approved or rejected plan before the first
successful join. Changing an approved plan's public place, public URL or start
time returns it to Pending review. Saving an edited rejected plan resubmits it as
Pending review. A cancelled plan is terminal and cannot be edited, approved or
reactivated.

After the first successful join, the entire plan is read-only except the owner's
separate cancellation action. Template visibility is not sufficient; the service
must enforce the lock.

### PR-PLN-005 — Joining is direct and capacity-safe

There are no join requests, offers or invitations. An active verified non-owner
may join an approved future uncancelled plan only while capacity remains.
Capacity counts participant places only; the owner does not consume a place.

The join service must lock the plan row, recount joined participation and recheck
all conditions in one transaction. The first successful join sets the permanent
meeting-details lock. Two simultaneous requests must not exceed capacity.

### PR-PLN-006 — Leaving and rejoining preserve history

Leaving changes the existing participation from Joined to Left and records the
departure time; it does not delete the row or unlock the plan. A former
participant may rejoin only when every ordinary joining rule still passes.
Rejoining reuses the row, records the latest successful join time and clears the
departure time.

The plan page shows joined count, not a public participant directory.

## 6. Direct messaging rules

### PR-MSG-001 — One direct conversation exists per account pair

Conversations have exactly two different accounts, stored with the lower account
ID first. The database unique constraint is authoritative. If simultaneous starts
conflict, the service fetches and returns the existing conversation.

### PR-MSG-002 — Every access is reauthorised

Opening a conversation, sending a message or requesting AI editing must recheck:

- both accounts are active and verified;
- the requester belongs to the conversation; and
- neither account has blocked the other.

Failure must reveal no conversation or message content.

### PR-MSG-003 — Messages are bounded plain text

Messages must be non-empty, bounded plain text and escaped when rendered. They
refresh through ordinary Django page requests. JavaScript may improve draft
editing but must not be required to send.

The MVP has no attachments, reactions, read receipts, typing state, WebSockets,
sent-message editing, expiring media or group conversations.

### PR-MSG-004 — The inbox contains recent permitted conversations only

The inbox returns only conversations containing the signed-in account, ordered by
recent conversation activity. It must remove every conversation blocked in either
direction before rendering names, previews or message text. A successful send
updates the conversation activity time used for this ordering.

## 7. Blocking and private-reporting rules

### PR-SAF-001 — A block is private and immediately effective

A user may create one directional block against a different user. Product policy
treats either direction as mutual exclusion: both profiles disappear from each
other's discovery, and their direct conversation can no longer be opened or used
to send messages.

The blocked account must not be notified or shown who blocked it.

### PR-SAF-002 — Reporting remains available independently

An authenticated user may report a different account even when a block prevents
discovery or messaging. Report controls are available from permitted profile,
plan and conversation contexts and are never Premium-only.

### PR-SAF-003 — A report is private context, not a finding

A report contains a bounded category and factual description and may reference at
most one server-validated plan, conversation or message. The reported account
must not see the report, reporter identity, report count or a notification.

Submission must not create a finding, sanction, risk score, public warning,
searchable accusation registry or claim of emergency response.

### PR-SAF-004 — Report references must be relevant

The browser cannot establish a trusted reference merely by sending an object ID.
The server must confirm:

- both the reporter and reported account are connected to a referenced plan as
  owner or participant;
- a referenced conversation contains both accounts; or
- a referenced message belongs to that conversation and was visible to the
  reporter.

An invalid reference must reject the submission without creating a partial
report. Eligible message-specific reporting uses the existing report route.

## 8. Stripe Premium rules

### PR-PAY-001 — Stripe owns payment collection

Kindlelise provides one subscription product and one configured GBP 499 yearly
price. A local account without recorded Stripe history receives exactly one
30-day trial through Stripe-hosted Checkout, without required upfront payment
details. Stripe history prevents another trial; a later eligible Checkout omits
the trial, and an active or trialing subscription is managed rather than
duplicated.

At trial end Stripe creates and hosts the first annual invoice. Stripe's hosted
invoice and customer portal handle GBP 4.99 payment, yearly renewal and
cancellation. Kindlelise must not render or store card or bank fields.

### PR-PAY-002 — Stripe ownership never comes from email

Checkout must carry the immutable local user ID in `client_reference_id` and
subscription metadata. Webhooks resolve ownership from that trusted reference or
an existing unique Stripe customer/subscription link. An identifier already
linked to another account must be rejected, not reassigned.

Checkout success, Checkout cancellation and portal-return destinations are built
by the server from the named local account route and never accepted from browser
input.

### PR-PAY-003 — A verified webhook is access authority

Returning from Checkout must not grant Premium. The application accepts only:

```text
checkout.session.completed
customer.subscription.updated
invoice.paid
customer.subscription.deleted
```

Checkout completion records identifiers only. A newer verified subscription
update grants only a `trialing` period with a future trial end. An `active`
subscription update alone is not payment evidence and cannot extend access. A
verified `invoice.paid` for the linked configured price and active subscription
grants only its future paid annual service period. Unpaid, past-due and expired
states deny Premium. Deletion sets local status to Cancelled, clears
`access_until` and updates the latest provider-event time while retaining the
Stripe customer and subscription identifiers. Local `stripe_status` remains
nullable until a supported subscription event supplies it.

### PR-PAY-004 — Webhook processing is ordered and atomic

Stripe event IDs are unique. Older or already processed events must not overwrite
newer accepted state. Receipt and subscription updates occur in one short
database transaction, and no Stripe network request runs inside that transaction.

A durable receipt is created for each accepted supported event ID. A correctly
signed unsupported event is acknowledged without a receipt or subscription
change. Failed supported-event processing commits neither a receipt nor a partial
subscription update.

The raw signed webhook body is verified before trusted parsing and must not be
stored in the minimal receipt or written to logs.

### PR-PAY-005 — Premium has exactly two product effects

Current Premium access expands permitted broad discovery areas and raises the
interest-filter limit from two to five. It must not alter verification, profile
ranking, blocking, reports, plans, messages or safety permissions.

Stripe payment must not be presented as identity or age verification.

### PR-PAY-006 — The customer portal requires a known Stripe customer

The post-trial Pay or Manage subscription action may open Stripe's hosted invoice
or customer portal only when the signed-in account already has its own recorded
Stripe customer ID. Missing or conflicting ownership must fail safely and must
not create, guess or borrow a customer relationship.

## 9. Ollama Cloud rules

### PR-AI-001 — AI editing requires an explicit conversation action

The user must choose Fix grammar or Improve clarity inside a direct conversation
they are currently authorised to use. There is no general AI-writing route.

### PR-AI-002 — Only the unsent draft leaves Kindlelise

Kindlelise sends only the current bounded unsent draft and one fixed goal. It must
not send profile data, recipient details, previous messages, sent messages,
reports or plan data.

### PR-AI-003 — The user remains the sender

The suggestion must be non-empty and no longer than the normal message limit. It
must not replace the draft until the user accepts it. Accepted text passes through
the ordinary message form again, and the user manually presses Send.

Provider failure or invalid output preserves the original draft and sends
nothing. Drafts and suggestions must not be logged or stored as separate durable
records.

The provider's Free plan is an operational choice, not a privacy, availability or
price guarantee.

## 10. Privacy, security and presentation rules

### PR-SEC-001 — Private content stays out of logs

Logs must not contain passwords, session values, message bodies, report
descriptions, secrets, raw Stripe payloads, Ollama drafts or suggestions.

### PR-SEC-002 — State changes use protected server actions

Browser state changes use POST and CSRF protection. The Stripe webhook is exempt
from CSRF only because its signature is verified against the exact raw body.

### PR-SEC-003 — Missing authority fails closed

Missing verification, ownership, membership, block state, Stripe state or valid
provider output must deny or preserve the previous state. The system must use the
same safe missing/restricted response where explaining the difference would leak
another account's existence.

### PR-UI-001 — The interface may not create backend behaviour

The mobile layouts retain the approved compact shape, but controls and pages must
map to behaviour in `docs/VERTICAL_SLICE.md`. The four primary destinations are
Discover, Plans, Messages and Profile.

The interface must not copy third-party branding, icons, advertisements, sample
content, sexual taxonomy, paid ranking or runtime behaviour.

### PR-UI-002 — Important controls remain understandable and reachable

The interface must clearly expose applicable Edit, Join, Join again, Leave,
Cancel, Message, Block, Report, Stripe and Ollama actions. It must include useful
empty, validation, provider-failure and restricted states and must not rely on
colour alone to communicate status.

## 11. Durable truth rules

### PR-DAT-001 — Core uniqueness belongs in the database

Database constraints must enforce:

- one profile and one platform subscription per Django account;
- verified profiles require reviewer and review time while unverified profiles
  require both fields to be null;
- unique interest names;
- one participation row per account and plan;
- joined participation requires null `left_at`, while left participation requires
  a departure time;
- positive plan capacity;
- approved plans require reviewer and approval time, while non-approved plans
  require both fields to be null;
- two different accounts stored lower-ID first and one conversation per unordered
  account pair;
- one block per ordered blocker/blocked pair and no self-block;
- no report targeting its reporter and no more than one optional report context
  reference; and
- unique non-empty Stripe customer IDs, subscription IDs and webhook event IDs.

Services still recheck product policy. A friendly form error or prior read cannot
replace a database constraint when simultaneous requests are possible.

### PR-DAT-002 — Indexes exist only for mapped reads

Indexes are limited to the discovery, plan-state/time, participation,
conversation-activity, chronological-message and report-review reads listed in
`docs/VERTICAL_SLICE.md`. A speculative index or duplicate denormalised field
requires the normal boundary-change justification.

## 12. Module responsibility rules

- `models.py` stores durable state, constraints, indexes and small read-only model
  helpers.
- `forms.py` validates and normalises untrusted browser input.
- `policies.py` answers permission questions without changing state.
- `services.py` owns state-changing user and provider workflows.
- `selectors.py` returns authorised read data without changing state.
- `views.py` translates authenticated HTTP requests and responses.
- `admin.py` owns mapped manual staff actions.
- `ai_message_editor.py` owns the one bounded Ollama request.
- Templates present authorised values and never recreate policy decisions.
- `static/app.js` may enhance only the mapped Ollama draft interaction.

Models must not import views, forms, services, selectors or provider clients.
Network calls must not run inside database transactions.

## 13. Explicitly deferred rules

The following are not active product rules and must not enter the MVP without an
approved boundary change:

- precise proximity, browser geolocation, distance ordering or location history;
- biometric, document, social-media or payment-based age/identity verification;
- automated URL retrieval, substantiation, archived evidence or AI venue review;
- plan versions, immutable meeting artifacts or participation offers;
- signals, thresholds, invitations, social circles or group conversations;
- blind corroboration, sealed safety experiences or safety circles;
- check-ins, emergency workflows or continuous monitoring;
- moderation findings, sanctions, appeals or evidence registries;
- multiple subscriptions, local invoice models, usage billing or custom payment
  forms;
- AI replies, translation, moderation, profiling or automatic sending;
- media, external notifications, native applications or third-party advertising;
- automated retention, privacy-rights or deletion orchestration.

Historical design material does not authorise these features.

## 14. Change-control rule

Before adding a file, model, route, dependency, workflow or feature, follow the
six-step boundary process in `docs/VERTICAL_SLICE.md` and record the approved
decision in `docs/DECISIONS.md` before implementation.

A small function may be added without a new decision only when it remains inside
an existing mapped responsibility, is added to the vertical-slice function map
and receives a behavioural test in the same change.
