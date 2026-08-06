# Kindlelise Student MVP Decision Log

> **Authority:** `docs/VERTICAL_SLICE.md` is the implementation boundary. This
> document records why that boundary exists; it does not add models, routes,
> functions, files or product behaviour. If the documents conflict, the vertical
> slice wins.

## Status meanings

- **Accepted** — required for the current student MVP.
- **Deferred** — potentially useful future work, but prohibited in this MVP.
- **Superseded** — an earlier decision that no longer controls implementation.
- **Rejected** — considered and deliberately not selected.

## ADR-001: Use the 36-implementation-file vertical slice as the authority

**Status:** Accepted
**Recorded:** 2026-07-18  
**Clarified:** 2026-07-22

### Context

The earlier architecture described a production-scale social coordination system
with many domains, files and operational controls. It could not reasonably be
built, tested and explained by one student within the project period.

### Decision

Build only this assessed journey:

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

Stripe provides one no-card 30-day Premium trial followed by a GBP 4.99 yearly
subscription. Ollama Cloud edits one unsent message draft.
`docs/VERTICAL_SLICE.md` owns the exact files, functions, routes, states,
constraints and tests.

Registration creates the account and initial unverified profile, then redirects
to the named sign-in route without authenticating the new account. Authentication
remains the separate mapped Django sign-in action.

The assessment uses supervised test accounts only. It does not implement age
verification and is not presented as ready for unrestricted public use.

### Alternatives rejected

- Implement the earlier production architecture before proving the core journey.
- Treat all existing design documents as equally authoritative.
- Scaffold future domains with empty files or placeholder models.

### Consequences

The project becomes small enough to demonstrate and defend. Production features
remain reference material only and cannot leak into implementation.

## ADR-002: Treat 36 implementation files as a maximum and use one Django application

**Status:** Accepted
**Recorded:** 2026-07-18

### Context

Splitting a student project into many Django applications, repositories, domain
packages or service layers would add navigation and integration work without
improving the assessed journey.

### Decision

Use one `kindlelise` Django application with the dependency direction:

```text
urls → views → forms / policies / services / selectors
services → policies / models
selectors → policies / models
admin → services / models
ai_message_editor → configured Ollama Cloud API only
```

The 36 implementation files are a maximum, not a completion target. The current
map names 33 implementation files and deliberately leaves three slots
unallocated. Supporting governance and assessment documents are outside this count.
Django-generated schema migrations and the reviewed initial-interest data
migration are mechanical exceptions and do not authorise new features.

### Alternatives rejected

- One Django application per product domain.
- Repository, command-bus, event-bus or provider-abstraction frameworks.
- A separate template for every page mode when an existing template has a clear
  responsibility.

### Consequences

Every behaviour has one readable owner. Authentication and public-profile modes
may share `account.html`; plan list/create/edit/detail modes may share
`plan.html`; the Premium comparison remains an account-page mode rather than a
new route.

`docs/IMPLEMENTATION_PLAN.md` is an explicitly approved supporting document
outside the implementation-file count. It owns sequencing, completion gates and
runtime evidence only; it cannot add implementation responsibility or product
scope. The vertical slice and existing requirements were rejected as task-tracker
owners because their contracts should remain stable while progress changes.

## ADR-003: Use ten Kindlelise models plus Django User

**Status:** Accepted  
**Recorded:** 2026-07-18  
**Clarified:** 2026-07-22

### Context

The MVP needs durable accountability, social discovery, plans, messaging,
blocking, reporting and a minimal Stripe projection. It does not need the
production model families previously proposed.

### Decision

Use exactly these Kindlelise models:

```text
Profile
Interest
Plan
Participation
Conversation
Message
Block
Report
PlatformSubscription
StripeWebhookReceipt
```

Django's existing `User` owns the account. The automatic profile-interest join
table has no custom model because the relationship has no additional behaviour.
Authentication uses one canonical lowercase email and password through Django's
normal authentication. The same email is stored in Django's unique `username`
field and `email` field, so no replacement User model or authentication backend
is required. Stripe ownership remains independent of email. `Interest.name` is
the interest's unique identity in this slice; no slug or second identifier is
added. This authentication portion was amended by ADR-017 on 2026-07-27.

### Alternatives rejected

- A replacement account model.
- Separate presence, verification-history or profile-interest models.
- Plan URL, substantiation, anchor-decision, artifact or version-lineage models.
- Participation offers or invitations.
- Generic relationship, circle or polymorphic safety tables.

### Consequences

The database remains understandable and can enforce the small set of uniqueness,
check and indexing rules in the vertical slice. New durable concepts require an
approved boundary change.

## ADR-004: Replace precise proximity and automated verification with broad areas and staff review

**Status:** Accepted  
**Recorded:** 2026-07-18  
**Clarified:** 2026-07-22

### Context

Precise location processing and external identity/biometric verification would
create privacy, provider and operational work beyond the assessment.

### Decision

- Store one stable configured broad-area key on the profile.
- Let `settings.py` own the approved area keys, display labels and nearby-area
  mapping; reject arbitrary area text in forms.
- Never collect browser coordinates, exact distance or movement history.
- Create the one-to-one profile atomically at registration even though its
  `display_name` and `broad_area` are initially empty onboarding values.
- Require `ProfileDetailsForm` to supply a non-empty display name and a configured
  broad-area key when the user completes or later edits the profile.
- Let authorised staff set the profile's verification state in Django Admin, but
  refuse verification until those two profile values are valid.
- Store optional `available_from`; derive current availability instead of storing
  a second presence value. ADR-018 defines the relative choices and replaces the
  earlier expiry semantics.
- Allow discovery to filter broad area, controlled interests and, optionally,
  profiles whose availability start has arrived.
- Apply active-account, verification and either-direction block exclusions before
  any profile enters presentation data.

Free accounts use their current broad area and at most two interest filters.
Premium accounts may use configured nearby broad areas and at most five interest
filters. Premium never weakens privacy or eligibility rules.

A reviewed data migration seeds Coffee, Walking, Museums, Live music, Cinema,
Food, Games and Study. Staff may maintain this controlled vocabulary through
Django Admin; ordinary users cannot create interests.

### Alternatives rejected

- Browser geolocation, distance ordering or triangulation-resistant proximity.
- Biometric, document, social-media or Stripe-based age/identity verification.
- Permanent online status or a separate presence-history model.

### Consequences

Discovery is coarse and manually governed but explainable. Staff verification is
an assessment control, not proof of age, identity or safety. The empty initial
profile is never eligible for discovery, plans or messaging.

## ADR-005: Use manual plan URL approval and lock the whole plan after first join

**Status:** Superseded by ADR-023; first-join locking remains accepted
**Recorded:** 2026-07-18  
**Clarified:** 2026-07-22

### Context

The product needs meetings anchored to an independently established public place
or organised activity, but safe URL fetching, evidence preservation and formal
anchor decisions are too large for the student MVP.

### Historical decision

A plan stores one title, description, public place, public HTTPS evidence URL,
start time and capacity. Authorised staff manually open the URL outside the
application and approve or reject the plan in Django Admin.

The application records only status, reviewer and review time. It does not fetch,
archive or substantiate the webpage and does not claim the venue is safe. A
dropped map pin, residential address, payment link or personal post is not valid
primary evidence.

Only approved future plans enter the public plan list and accept joins. The join
service locks the plan row, recounts current participants and sets the first-join
lock in one transaction. After the first successful join, the entire plan is
read-only except cancellation. Leaving preserves the participation row; an
eligible rejoin reuses it.

Pending plans are editable. Approved plans are editable before the first join,
with changes to `public_place`, `public_url` or `starts_at` returning them to
pending. Saving an edited rejected plan resubmits it as pending. Cancelled plans
are terminal and cannot be edited, approved or reactivated. Capacity counts
participant places and excludes the owner.

There is one participation row per user and plan. Joining creates the row when
none exists; leaving changes `joined` to `left`; an eligible rejoin changes that
same row back to `joined`, refreshes `joined_at` and clears `left_at`. A current
`joined` row is refused, while an existing `left` row is not treated as current
participation.

### Alternatives rejected

- Server-side URL retrieval, redirect/DNS analysis or AI venue approval.
- Stored page versions, URL substantiations or meeting-anchor decisions.
- Editing meeting details after somebody has accepted them.
- Deleting participation history on leave or plan cancellation.

### Consequences

The safety claim remains honest and limited. Concurrent joins require PostgreSQL
row locking and behavioural tests; the system makes no preserved-evidence or
venue-safety guarantee.

## ADR-006: Use direct, refreshed plain-text messaging

**Status:** Accepted  
**Recorded:** 2026-07-18

### Context

Users need to communicate without swiping or mutual matching. Live delivery and
media would expand storage, privacy and frontend complexity.

### Decision

Store one conversation per unordered account pair, with the lower user ID first.
Handle simultaneous creation through the database unique constraint: attempt the
create, catch the unique conflict and fetch the existing pair.

Messages are bounded plain text, escaped when rendered and refreshed through
ordinary Django page requests. Every conversation open, send and AI request
rechecks active verification, membership and blocking in both directions.

### Alternatives rejected

- WebSockets, Channels, typing indicators or delivery/read receipts.
- Message attachments, reactions, editing sent messages or group conversations.
- Swiping, matching or a separate contact-request workflow.

### Consequences

Messaging is slower than a live chat but reliable, testable and small. JavaScript
may improve the interface but cannot be required to send a message.

## ADR-007: Make blocking immediate and reports private but non-adjudicative

**Status:** Accepted  
**Recorded:** 2026-07-18  
**Clarified:** 2026-07-22

### Context

The MVP needs a direct user safety control and a way to provide staff context
without building a complete moderation or evidence platform.

### Decision

A directional block has mutual product effect: both accounts disappear from each
other's discovery and can no longer open or send direct messages. The blocked
account is not notified.

A report always targets a different account and may reference at most one
server-validated plan, conversation or message. It is private to the reporter and
authorised staff and is never displayed to the reported account. Submission
creates no finding, sanction, risk score, public label or accusation registry.
The reporter sees the submitted form and private confirmation only; this decision
does not create a report-history page or report-list selector.

Both accounts must be connected to a referenced plan as owner or participant. A
referenced conversation must contain both accounts. A referenced message must
belong to that conversation and have been visible to the reporter; no vague
additional “relates to” test is applied.

The existing report route handles profile-, plan-, conversation- and eligible
message-specific context. It resolves the route's target independently of
discovery or messaging visibility so a block cannot suppress reporting, while an
optional plan, conversation or message reference remains reporter-scoped and is
revalidated by the service. No separate route or model is added.

### Alternatives rejected

- Public report counts, searchable allegations or automatic sanctions.
- Moderation findings, appeals, evidence custody or emergency-response promises.
- A separate blocking dashboard for the first MVP.

### Consequences

Block and Report remain visible and never premium-only. Staff review is small and
manual; the product must not claim to provide a full safeguarding service.

## ADR-008: Use one Stripe subscription with webhook-authoritative access

**Status:** Accepted  
**Recorded:** 2026-07-18  
**Clarified:** 2026-07-22

**Amended:** 2026-07-27

### Context

Stripe is required, but custom billing, multiple products and local payment forms
would distract from the social journey and increase payment-data exposure. The
approved offer is one no-card-required 30-day trial followed by GBP 4.99 for one
year of Premium.

### Decision

- Configure one Stripe product and one recurring GBP 499 yearly price.
- Permit one 30-day trial per local account. A recorded Stripe customer or
  subscription exhausts trial eligibility; cancellation cannot reset it.
- For the first eligible Checkout, set `payment_method_collection=if_required`,
  `trial_period_days=30` and missing-payment-method end behaviour to
  `create_invoice`. A later eligible Checkout omits the trial, and an existing
  active or trialing subscription is managed through the customer portal rather
  than duplicated.
- At trial end, let Stripe create and host the first GBP 4.99 annual invoice.
  Use Stripe's hosted invoice/customer-portal surfaces for payment, and renew the
  annual subscription unless the customer cancels it through the portal.
- Use Stripe-hosted Checkout and customer portal.
- Construct Checkout success/cancellation and portal-return URLs on the server from
  the named account route; never accept these destinations from browser input.
- Pass the immutable Kindlelise user ID through `client_reference_id` and
  subscription metadata; never resolve ownership from email.
- Accept only `checkout.session.completed`, `customer.subscription.updated`,
  `invoice.paid` and `customer.subscription.deleted`.
- Let Checkout store identifiers only; it never grants premium access.
- Grant trial access only from a verified `trialing` update with a future trial
  end. An `active` subscription update alone is not payment evidence.
- Grant paid access only from a verified `invoice.paid` event for the linked
  configured price and active subscription, using its future paid service-period
  end as `access_until`. Unpaid, past-due and expired states deny access.
- On deletion, set the local status to cancelled, clear `access_until` and update
  the latest provider-event time.
- Order subscription-state events by `provider_created_at`; Checkout completion
  does not advance that ordering cursor. At an equal timestamp, deletion may
  revoke access, while a non-deletion event cannot overwrite an already accepted
  state.
- Permit a delayed `invoice.paid` to extend `access_until` to its later paid
  service-period end only while the linked subscription remains active and has
  not been revoked or made ineligible by a newer event. It cannot rewind status
  or revive a cancelled subscription.
- Process the unique event receipt and subscription projection atomically, with no
  Stripe network request inside the database transaction.
- Create a durable receipt for each safely handled supported event ID, including
  stale or safely refused equal-time events, and set `processed_at` only when the
  transaction succeeds. A correctly signed unsupported event is acknowledged
  without a receipt or state change. A failed supported event rolls back both its
  receipt and subscription update.
- Keep `stripe_status` nullable until a supported subscription event supplies it.
- Retain Stripe customer and subscription identifiers after deletion for safe
  matching and portal ownership.

### Alternatives rejected

- Email-based Stripe ownership.
- Collecting payment details before the free trial.
- Repeating trials after cancellation or creating duplicate active subscriptions.
- Inline card collection, usage billing or multiple tiers.
- Treating a Checkout return or successful payment as age/identity verification.
- Granting permanent premium from a stale local boolean.

### Consequences

Kindlelise stores no card or bank details. Premium expands configured discovery
areas and interest-filter count only. Stripe owns the post-trial invoice and
annual payment surfaces. Duplicate and older events cannot overwrite newer
accepted state, and an unpaid invoice cannot create a free paid year.

## ADR-009: Limit Ollama Cloud to explicit unsent-draft editing

**Status:** Accepted  
**Recorded:** 2026-07-18

### Context

The assessment requires AI, but general reply generation or conversation analysis
would disclose more private content and be harder to explain and test.

### Decision

The user explicitly chooses `Fix grammar` or `Improve clarity` within an
authorised direct conversation. Send only the current bounded unsent draft and
fixed goal to the configured Ollama Cloud endpoint.

Do not send profile data, recipient details, previous messages, sent messages or
reports. A non-empty bounded suggestion returns to the draft interface but
replaces nothing until accepted. The ordinary message form validates it again,
and the user manually sends. Provider failure preserves the original draft.

### Alternatives rejected

- Automatic replies, sending, translation, moderation or sentiment analysis.
- A general AI endpoint outside a conversation.
- Conversation-history or profile context.
- Durable AI-suggestion records or logging drafts and outputs.

### Consequences

The integration is one small file and one conversation-bound route. Provider
terms and retention still require review before real personal data is used; a free
plan is not a privacy guarantee.

## ADR-010: Enforce privacy through server-side owners and honest limitations

**Status:** Accepted  
**Recorded:** 2026-07-18

### Context

The project needs defensible privacy behaviour without claiming production legal
or operational capabilities that are not implemented.

### Decision

Use the historical data inventory and access boundaries in
`doc_old/PRIVACY_MODEL.md` only as background. Keep
message bodies, report descriptions, passwords, secrets, raw webhook payloads and
AI drafts out of logs. Use generic not-found responses where explaining a denial
would reveal hidden state.

The MVP does not claim a privacy dashboard, automated retention/deletion,
self-service export, biometric verification, emergency response or legal
compliance. Real public use requires appropriate legal review and operating
procedures beyond the assessment implementation.

### Alternatives rejected

- Treat template visibility as authorisation.
- Promise automatic erasure or compliance without implementing the operations.
- Reuse reports, messages, location or AI content for advertising and ranking.

### Consequences

Privacy decisions remain simple enough to test. Some production rights,
retention, audit and incident workflows are explicitly deferred rather than
represented by empty scaffolding.

## ADR-011: Preserve reference wireframe shapes without copying source behaviour

**Status:** Accepted  
**Recorded:** 2026-07-18

### Context

The supplied screenshots provide useful mobile layout patterns, while their
branding, content and several product behaviours do not belong to Kindlelise.

### Decision

Retain compact headers, dense profile grids, horizontal chips, long forms, fixed
actions, inbox rows, account panels and strong empty states. Replace obsolete
features only where they are absent from the vertical slice.

Use four destinations: Discover, Plans, Messages and Profile. The discovery grid
contains verified profile cards only. The Premium comparison is an account-page
mode. `doc_old/WIREFRAMES.md` may describe presentation but cannot create backend
requirements.

### Alternatives rejected

- Copy branding, icons, sample content, sexual taxonomy, advertising or paid
  ranking.
- Restore obsolete signals, circles, group conversations or safety check-ins to
  fill a reference screen.
- Add a route or model solely because a screenshot contains a control.

### Consequences

The UI remains visually coherent while the product and implementation stay
original and within the student scope.

## ADR-012: Supersede production-scale decisions for current implementation

**Status:** Accepted; supersedes earlier production-scale implementation decisions  
**Recorded:** 2026-07-18

### Context

Earlier decisions accepted a multi-domain architecture, precise proximity,
provider-based face verification, immutable meeting artifacts, check-ins,
threshold-created circles and blind safety corroboration.

### Decision

None of those decisions authorises code in the 36-implementation-file vertical
slice. Potential future work includes privacy-preserving proximity, formal URL
evidence, immutable meeting artifacts, threshold-created social circles and
separately isolated safety corroboration, but each requires a fresh approved
boundary decision.

Blind corroboration in particular remains outside the MVP. No sealed experience,
matching token, safety circle, finding, sanction, appeal or safety-notification
entity may be added from the historical design.

### Alternatives rejected

- Leave the earlier ADRs marked Accepted and rely on developers to infer which
  architecture controls implementation.
- Partially scaffold deferred models or routes for later use.

### Consequences

There is one implementation authority and no renamed duplicate architecture. The
future product direction is not erased, but it cannot silently expand the student
project.

## ADR-013: Require explicit approval for boundary expansion

**Status:** Accepted  
**Recorded:** 2026-07-18

### Context

Earlier documentation and function growth caused the repository plan to expand
faster than the core journey could be implemented.

### Decision

Before adding a file, model, route, dependency, workflow or feature:

1. state the user-visible requirement;
2. identify why the current owner cannot handle it safely;
3. show the smallest design attempted within the boundary;
4. describe privacy, security, testing and assessment consequences;
5. obtain explicit approval; and
6. update `docs/VERTICAL_SLICE.md` and this decision log before implementation.

A small function may be added without a new ADR only when it remains inside an
existing responsibility, is added to the public function map and receives a
behavioural test in the same change.

### Alternatives rejected

- Add speculative abstractions or extension points “for later”.
- Add files because an existing file feels long without first consolidating.
- Add functionality first and document it afterwards.

### Consequences

The project prefers deletion, consolidation, plain functions and Django defaults.
Every structural expansion is visible and reviewable.

## ADR-014: Serve assessment static files with WhiteNoise

**Status:** Accepted  
**Recorded:** 2026-07-18

### Context

The approved Heroku deployment must serve the existing CSS and JavaScript with
`DEBUG = false`. The file map has no reverse proxy or separate static hosting
service, and relying on Django's development server would make the deployed
runtime incomplete.

### Decision

Add the small WhiteNoise dependency and configure its middleware/storage in
`config/settings.py`. Continue to build assets with Django `collectstatic` and
keep all project-owned assets in the existing `static/` files. This adds no model,
route, feature or implementation file.

### Alternatives rejected

- Serve static files with Django's development server in production.
- Add a separate asset service or new deployment scripts for this student MVP.
- Add a health endpoint solely to test static delivery.

### Consequences

The anonymous sign-in page and its CSS become the deployment readiness smoke
check. WhiteNoise is an approved dependency only for production static-file
serving; it does not own uploads, media or application behaviour.

## ADR-015: Use a subordinate master instruction for repeated passes

**Status:** Accepted  
**Recorded:** 2026-07-22

### Context

Architecture, data-model, implementation, testing and runtime reviews repeatedly
need the same scope, ownership, security and change-control rules. Recreating
those instructions for each pass risks omissions and allows an external review
or supporting document to become an accidental second authority.

### Decision

Add `docs/MASTER_INSTRUCTION_PROMPT.md` as a reusable pass-start instruction. It
extracts the golden rule and high-value guardrails from the vertical slice,
requires the complete vertical slice to be read, and provides placeholders for
the current pass objective and deliverable.

The prompt is a supporting governance document outside the implementation-file
count. It adds no model, route, public function, dependency, workflow or product
behaviour. It cannot approve or redefine the implementation boundary. If it is
stale, incomplete or contradictory, `docs/VERTICAL_SLICE.md` wins and the prompt
is corrected. Its header records the synchronized vertical slice's SHA-256
fingerprint, with the date as supplementary metadata, so multiple revisions on
one day cannot be mistaken for one another.

The user's request on 2026-07-22 supplies the explicit approval and purpose for
this new file. Future approved vertical-slice changes must review the affected
prompt summary in the same documentation pass.

### Alternatives rejected

- Recreate an informal instruction from memory before every pass.
- Copy the complete vertical slice into a second document that could drift.
- Give external review feedback equal authority to the approved boundary.
- Put changing task objectives or progress evidence into the vertical slice.

### Consequences

Every pass starts with the same authority hierarchy, scope guardrails, owner
boundaries, security invariants and evidence discipline. The operator still has
to read the vertical slice for exact fields, functions, routes and tests; the
shorter prompt cannot replace it.

## ADR-016: Keep mutable implementation progress in a separate ledger

**Status:** Accepted  
**Recorded:** 2026-07-22

### Context

The implementation plan defines stable phases, dependencies, exit gates and
runtime checks, while phase State and Evidence change throughout delivery.
Keeping the frequently edited table inside the plan makes a stable execution
contract change whenever progress is recorded.

### Decision

Move the phase progress table to `docs/IMPLEMENTATION_PROGRESS.md`. The new
document owns only the existing State and Evidence values for phases defined in
`docs/IMPLEMENTATION_PLAN.md`. It cannot add an outcome, redefine or omit a phase,
weaken an exit gate, or use unevidenced completion status to change scope.

The progress ledger is an explicitly approved supporting governance document
outside the implementation-file maximum. The user's request on 2026-07-22
provides the reason and explicit approval for the new file. The vertical slice is
updated in the same change, completing the documentation part of the boundary
procedure without adding implementation responsibility.

### Alternatives rejected

- Continue mixing frequently changing status with the stable phase contract.
- Copy phase definitions and exit gates into the ledger, creating two owners.
- Treat a progress-table update as authority to introduce new work.

### Consequences

The implementation plan remains stable and reviewable while progress updates are
small and auditable. Every phase still uses the plan's state meanings, closure
record and exit gates, and the vertical slice remains the implementation
authority.

## ADR-017: Use canonical email addresses for account authentication

**Status:** Accepted
**Recorded:** 2026-07-27

### Context

The implemented account journey asked users to invent a separate username even
though the requested product experience is registration and sign-in with an
email address and password. The approved vertical slice previously prohibited
email authentication, so this change required an explicit boundary decision.
The user approved the change on 2026-07-27 and requested a small surgical slice.

### Decision

Keep Django's existing User model, default authentication backend, password
validation, sessions and routes. `AccountSignUpForm` validates an email address,
trims it and canonicalises the complete value to lowercase. The account service
stores that value in both Django's unique 150-character `username` field and its
`email` field. Sign-in labels the existing Django authentication field as Email
and applies the same canonicalisation before authentication.

The unique `username` column remains the database uniqueness authority, so two
case variants cannot create separate accounts. The application does not expose a
second public username, add a custom User model, add an authentication backend or
require a schema migration. Email is authentication data only: Stripe webhook
ownership continues to use immutable local account IDs or existing Stripe-ID
links and never selects an account by email.

### Alternatives rejected

- Keep a separate user-chosen username, because it contradicts the requested
  registration and sign-in experience.
- Add a custom User model or authentication backend, because the existing unique
  username field can safely own the canonical login identifier.
- Make Django's non-unique email field the sole database authority, because that
  would require a schema/manager change and introduce a case-variant race.
- Resolve Stripe ownership from the authentication email, because mutable or
  provider-supplied email is not an authoritative billing link.

### Consequences

Registration and sign-in display Email and Password, duplicate case variants are
rejected, and successful registration still creates one unverified Profile
atomically without starting a session. Authentication emails are private account
data and must not enter logs or public profile output. Existing supervised demo
fixtures may be replaced or updated because no production account migration is
part of this pre-assessment MVP change.

## ADR-018: Use an optional availability-start signal

**Status:** Accepted
**Recorded:** 2026-07-27

### Context

The implemented profile form exposed a raw `available_until` date/time. That
field communicated an expiry, produced browser date/time validation errors and
did not match the requested start-oriented choices or the requested `Free now`
control. Availability must also remain optional so it cannot prevent profile
completion or later staff verification. The user approved the replacement on
2026-07-27.

### Decision

Replace `Profile.available_until` with one nullable `available_from` timestamp.
Do not add a stored presence boolean, model, route, dependency or workflow.
`ProfileDetailsForm` presents a form-only `Free now` switch and one optional fixed
choice: `Today`, `Tomorrow`, `This week` or `As and when`. The switch, Today,
This week and As and when store the current submission time; Tomorrow stores
midnight at the start of the next day in the configured local timezone. An
unchecked switch with an empty choice clears the signal. The switch is input
convenience and is never stored as a second presence value.

`Profile.is_available_now(at_time)` is true only when `available_from` exists and
is no later than the supplied time. Discovery presents the ordinary optional
filter as a `Free now` switch and applies the same comparison. Availability is
not a profile-completion or staff-verification prerequisite.

The reviewed migration clears existing expiry values before renaming the column.
An old expiry must not silently become a future start and accidentally expose a
profile as currently available after that time.

### Alternatives rejected

- Keep `available_until` and only relabel it, because the stored meaning and UI
  would disagree.
- Store a second `free_now` boolean, because it could drift from the timestamp.
- Add a presence/history model, because the MVP needs only one current signal.
- Require availability during onboarding, because it is a later optional social
  choice rather than staff-verification evidence.

### Consequences

Users avoid raw date/time input and can add or clear availability later. The
relative options deliberately remain coarse: Today, This week and As and when
all start immediately, while Tomorrow becomes current at local midnight. A start
signal remains current until the owner clears or replaces it; no availability
history is stored. Tests must cover optional completion, conversion at the local
day boundary, clearing and the `Free now` discovery filter.

## ADR-019: Expose profile verification on the Django User permissions form

**Status:** Accepted
**Recorded:** 2026-07-27

### Context

Manual profile verification existed only as a bulk action on the separate
Profile changelist. Staff reviewing an account through Django's User page could
see Active, Staff status and Superuser status but had no nearby way to grant the
profile verification required for discovery. The resulting navigation made the
account appear active while the user continued to receive the verification gate
message. The user explicitly requested a verification control in that Permissions
section on 2026-07-27.

### Decision

Keep `Profile.is_verified`, `verified_at` and `verified_by` as the only durable
verification truth. In `kindlelise/admin.py`, replace Django's registered
`UserAdmin` with `KindleliseUserAdmin`, preserving Django's standard User admin
behaviour and adding one form-only `Profile verified` checkbox to the User change
page's Permissions fieldset.

Only a staff request already authorised to change the User and holding
`kindlelise.change_profile` may see and submit the checkbox. Checking it rechecks
the related Profile's non-empty display name and configured broad-area key, then
records the current staff reviewer and time. Unchecking it clears all three
verification fields. A missing or incomplete Profile cannot be verified. The
existing Profile list actions remain available and enforce the same state rules.

### Alternatives rejected

- Treat Active, Staff status or Superuser status as profile verification,
  because those Django account permissions have different security meanings.
- Add a second verification field to User, because it could drift from Profile.
- Add a custom admin route or public approval page, because Django's existing
  User change form can safely host the control.
- Remove the existing Profile bulk action, because it remains useful for staff
  reviewing several complete profiles.

### Consequences

Staff can approve a complete account from the User page they are already using,
while durable verification remains consistent and attributable. This adds no
model, migration, route, dependency or implementation file. Tests must prove
placement, successful verification and withdrawal, incomplete-profile refusal,
and omission of the control when Profile change permission is absent.

## ADR-020: Add one optional protected profile image

**Status:** Accepted
**Recorded:** 2026-07-27

### Context

The approved profile had no image field. The user explicitly requested a small
profile-image upload section above Display name on 2026-07-27. A direct media URL
would bypass the existing profile visibility and mutual-block rules, while an
unprocessed photograph could retain location or device metadata.

### Decision

Add one optional `Profile.profile_image` field and no separate media entity.
`ProfileDetailsForm` owns upload validation and presents the field first. It
accepts JPEG, PNG and WebP only, limited to 5 MB and 4,096 pixels on either side,
normalises the image through Pillow and saves no embedded metadata. Storage uses
a random name rather than the user's original filename.

Only the active owner or a viewer currently allowed to open that public profile
may read the image. A named authenticated application route calls a selector and
streams the file; missing, denied and unavailable images share one generic
not-found outcome. There is no direct media route. Replacing an image deletes the
superseded file only after the database transaction commits. Staff
admin does not provide an alternate image-upload path.

The image is optional presentation and is never verification evidence. Local
filesystem storage is accepted only for the supervised local assessment. Durable
production object storage, moderation, image history and automated retention are
deferred and must complete a later boundary change before public deployment.

### Alternatives rejected

- Serve `MEDIA_URL` directly, because it would bypass profile visibility and
  blocking decisions.
- Store image bytes in PostgreSQL, because it would enlarge ordinary profile
  queries and create unnecessary data responsibilities.
- Add a media model or processing service, because one bounded optional field is
  the smallest design for the requested journey.
- Preserve the original upload unchanged, because embedded metadata can disclose
  private device or location information.

### Consequences

This adds one Profile field and migration, Pillow dependency, selector, view and
named route. The profile form must use multipart encoding. Tests must prove field
order, validation and metadata removal, owner/authorised reads, generic denied
reads, and replacement cleanup.

## ADR-021: Store and filter multiple authorised discovery areas

**Status:** Accepted
**Recorded:** 2026-07-27

### Context

Discovery already calculates the exact broad areas available to each account but
the form accepts only one area per request. The user explicitly requested
multiple broad-area selection on 2026-07-27, alongside the existing multiple
interest filtering.

### Decision

Add `Profile.broad_areas` as a bounded list of configured stable keys while
retaining `broad_area` as a backwards-compatible primary value. The profile form
accepts one or more areas, stores the first as the primary value and stores the
full selection in `broad_areas`. Discovery accepts one or more selected keys,
refuses an empty, stale or unauthorised set and matches profiles whose saved areas
overlap that set.

Free accounts may search their saved areas and use at most two interest filters.
Premium accounts may additionally search configured nearby areas and use at most
five interest filters. Verification, blocking and all privacy exclusions remain
unchanged.

### Alternatives rejected

- Replace the legacy `broad_area` immediately, because a compatibility value keeps
  existing records and staff workflows understandable during the student MVP.
- Trust arbitrary submitted area keys, because client input cannot expand the
  areas calculated by policy.
- Add exact location or distance, because neither is needed for broad-area
  filtering and both remain outside the approved scope.

### Consequences

This adds one profile field and reviewed backfill migration, and updates the
profile form, policy, selector, service and presentation labels. Tests must prove
multi-area saving and filtering, free/premium limits, checkbox input and safe
refusal of empty or unauthorised selections.

## ADR-022: Fetch bounded public metadata only after an explicit action

**Status:** Accepted
**Recorded:** 2026-08-06

### Decision

The plan form may fetch a normal public HTTPS page only after the user selects
`Fetch details`. The fetcher rejects local/private targets, bounds redirects,
content types and response sizes, extracts an editable public-place suggestion,
normalises an optional image to metadata-free JPEG and returns a short-lived
signed token. The image is stored only when the validated plan form is submitted
and is served through the same plan-visibility decision as the plan itself.

The fetched page is a convenience input, not preserved evidence or venue safety
approval. Users can edit the suggested place or continue manually when fetching
fails.

## ADR-023: Publish eligible plans immediately

**Status:** Accepted
**Recorded:** 2026-08-06

### Decision

An active, verified owner creates an approved plan immediately. The owner becomes
the recorded approver for the database constraint; browser-supplied status and
approval fields remain ignored. An unlocked approved plan stays approved when
edited. Editing an unlocked legacy rejected plan activates it, while cancelled
plans remain terminal and the first successful join still locks all meeting
details except cancellation.

This supersedes ADR-005's manual plan-review workflow but not its public-place,
capacity, participation-history or first-join locking rules.
