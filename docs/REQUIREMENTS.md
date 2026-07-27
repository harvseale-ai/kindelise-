# Kindlelise Student MVP Requirements

> **Status: student-MVP requirements catalogue.** This document states observable
> outcomes for the scope approved in `docs/VERTICAL_SLICE.md`. It does not expand
> that scope. If the documents conflict, the vertical slice wins.

## 1. Requirement convention

Each requirement has one stable identifier and acceptance criteria that can be
demonstrated or tested through a public interface. Requirements describe required
outcomes; file and function ownership remains in `docs/VERTICAL_SLICE.md`.

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

Stripe supplies one optional Premium subscription. Ollama Cloud supplies one
optional edit suggestion for an unsent message draft.

The assessment uses supervised test accounts only. It does not implement age
verification and must not be presented as ready for unrestricted public use.

## 2. Accounts and profiles

### ACC-001 — Register an account and profile together

A visitor must be able to register with the minimum account credentials. A new
account must receive exactly one unverified profile.

Acceptance criteria:

- A valid registration creates both records.
- Successful registration redirects to the named sign-in route without starting
  an authenticated session.
- Registration uses one valid canonical lowercase email address, password and
  password confirmation. The same email occupies Django's unique username field
  and email field, without a custom User model or authentication backend.
- A failed registration leaves neither a partial account nor a partial profile.
- The new profile does not enter discovery before staff verification.
- Passwords are handled by Django authentication and are never stored as plain
  text by Kindlelise.

### ACC-002 — Sign in and sign out safely

A registered user must be able to sign in and end the current session.

Acceptance criteria:

- Successful sign-in rotates/authenticates the session through Django.
- A post-sign-in redirect is followed only when it is a safe local destination.
- An invalid sign-in does not reveal whether a supplied email is registered.
- The home route sends an authenticated verified account to discovery, an
  authenticated unverified account to its private account page and an
  unauthenticated visitor to sign-in.
- Sign-out accepts a CSRF-protected POST request and does not use an unprotected
  GET action.

### ACC-003 — Staff verification gates social features

Discovery, plans, direct messaging and Ollama editing must require an active
Django account and a currently staff-verified profile.

Acceptance criteria:

- An inactive or unverified account cannot use those features even by calling a
  route directly.
- An unverified account may still view and edit its own permitted profile fields.
- Paying for Premium does not bypass verification.
- Removing verification denies later social access without deleting existing
  plans, conversations or messages.

### ACC-004 — Staff control current verification

Authorised staff must be able to grant or remove current verification through
Django Admin.

Acceptance criteria:

- Verification records the responsible staff account and time.
- Each selected profile is rechecked before its state changes.
- The Django User change page includes `Profile verified` in Permissions only
  for staff who can change both the User and Profile; it applies the same rules
  and can also withdraw verification.
- An incomplete profile with an empty display name or a broad-area key absent
  from `KINDLELISE_AREAS` cannot be verified.
- Already-correct or otherwise ineligible records are skipped safely.
- The interface describes verification as a staff gate, not proof of identity,
  age, character or safety.

### ACC-005 — Edit the permitted profile fields

A signed-in account must be able to edit its own display name, short biography,
broad named area, controlled interests and optional availability-start choice.

Acceptance criteria:

- The account cannot edit another user's profile.
- Browser input cannot change verification or Stripe fields.
- Interests come from the staff-seeded vocabulary; users cannot create arbitrary
  interest names.
- A reviewed initial data migration seeds Coffee, Walking, Museums, Live music,
  Cinema, Food, Games and Study.
- Broad area accepts only a stable key configured in `settings.py`; arbitrary area
  text is rejected.
- No uploaded image, health, ethnicity, sexuality, weight, social-handle or
  private-home field is required or stored for the MVP.

### ACC-006 — Derive and clear current availability

The profile may show `Free now` from one optional calculated `available_from`
value.

Acceptance criteria:

- Profile completion and staff verification do not require availability.
- The profile form provides a form-only Free now switch and accepts only Today,
  Tomorrow, This week or As and when, or an empty choice to add it later/clear
  it. The switch is not stored as a second boolean.
- Today, This week and As and when start immediately; Tomorrow starts at local
  midnight on the next day.
- Availability is current once `available_from` has arrived and remains so until
  the owner clears or replaces it.
- No second online-status value or presence-history record is created.

## 3. Discovery

### DSC-001 — Show one broad-area profile grid

An eligible verified account must be able to browse eligible verified profiles in
permitted broad named areas.

Acceptance criteria:

- Every grid item represents a profile, not a plan, invitation or paid placement.
- Cards may show display name, broad area, controlled interests, verification and
  current availability.
- Discovery does not require swiping or mutual matching.
- The system does not collect or display coordinates, exact distance, direction
  or movement history.

### DSC-002 — Filter discovery with fixed limits

An eligible user must be able to filter by permitted broad area, controlled
interests and optional current availability.

Acceptance criteria:

- Free accounts use their current broad area and at most two interest filters.
- Current Premium accounts may use configured nearby broad areas and at most five
  interest filters.
- `settings.py` owns the stable area keys, display labels and nearby-area mapping
  used by profile and discovery forms.
- The `Free now` switch returns only profiles with an `available_from` value no
  later than the current time.
- Invalid or excessive filters produce a clear validation error and never expand
  the permitted result set.

### DSC-003 — Apply exclusions before returning results

Ineligible and blocked profiles must not enter presentation data.

Acceptance criteria:

- Inactive and unverified profiles are excluded.
- A block in either direction excludes both profiles from each other's results.
- Exclusions happen before rendering or pagination.
- The page does not reveal why a profile is absent or how many hidden results
  exist.

### DSC-004 — Open only an authorised public profile

An eligible verified user must be able to open an allowed profile from discovery.

Acceptance criteria:

- Missing, inactive, unverified or either-direction-blocked targets return the
  same safe unavailable response.
- An allowed profile exposes Message, Block and Report actions.
- The page never exposes exact location, private reports, Stripe identifiers or
  another account's private message data.

## 4. Plans and participation

### PLN-001 — Submit a public-place plan for review

An active verified user must be able to submit a plan containing a title,
description, established public place, public HTTPS evidence URL, future start
time and positive capacity.

Acceptance criteria:

- A newly submitted plan is Pending review regardless of browser-supplied state.
- The owner can see the pending plan; other ordinary users cannot.
- A malformed or non-HTTPS URL is rejected without fetching it.
- The application does not accept a private address, dropped map pin, payment
  link or personal social post as sufficient primary meeting evidence.

### PLN-002 — Review a plan manually

Authorised staff must be able to approve or reject an eligible pending plan after
manually opening its public URL outside Kindlelise.

Acceptance criteria:

- Approval records status, reviewer and review time.
- Staff recheck that the plan is pending, future and unlocked before changing it.
- Blind bulk updates skip locked, cancelled and otherwise ineligible plans.
- No webpage copy, URL substantiation, AI assessment or venue-safety guarantee is
  stored or claimed.

### PLN-003 — Show plans according to status and ownership

The plan list must show approved future plans publicly and the signed-in owner's
own pending, rejected or cancelled plans privately.

Acceptance criteria:

- Another owner's pending, rejected or cancelled plan is not returned.
- Rejected, cancelled, past and unapproved plans cannot accept joins.
- Cancelling an owned plan removes it from public lists and prevents future joins.
- Cancellation does not delete the plan or participation history.

### PLN-004 — Edit only before the first join

The owner must be able to edit a pending, approved or rejected plan before its
first successful join.

Acceptance criteria:

- A non-owner cannot edit the plan.
- Changing an approved plan's public place, public URL or start time before the
  first join returns it to Pending review.
- Saving an edited rejected plan resubmits it as Pending review.
- A cancelled plan is terminal and cannot be edited, approved or reactivated.
- The first successful join makes the entire plan read-only except cancellation.
- A direct request to edit a locked plan is rejected even if the interface hides
  the Edit action.

### PLN-005 — Join an approved plan safely

An active verified non-owner must be able to join an approved future uncancelled
plan while capacity remains.

Acceptance criteria:

- The owner cannot join their own plan.
- Capacity counts participant places only; the owner does not consume a place.
- Pending, rejected, cancelled, past or full plans reject joining.
- A successful first join creates/reactivates participation and locks the plan in
  the same transaction.
- Two simultaneous joins cannot exceed capacity.
- Joining is direct; no request, invitation or participation-offer state exists.

### PLN-006 — Leave and rejoin without deleting history

A current participant must be able to leave, and a former participant may rejoin
when every ordinary joining rule still passes.

Acceptance criteria:

- Leaving changes the existing participation to Left and records the departure
  time.
- Leaving does not delete participation or unlock the plan.
- Rejoining reuses the same participation row, records the latest join time and
  clears the departure time.
- A left participant cannot rejoin a full, past, cancelled or unapproved plan.

### PLN-007 — Limit participant disclosure

The plan detail page must expose the current joined count and the viewer's own
participation state without creating a public participant directory.

Acceptance criteria:

- Ordinary users do not receive a list of participant identities from the plan
  selector.
- The page shows only actions currently authorised for the viewer.
- The page explains that manual URL review does not guarantee venue safety or
  preserve the reviewed webpage.

## 5. Direct messaging

### MSG-001 — Start one direct conversation per pair

Two different active verified and mutually unblocked accounts must be able to
start or return to one direct conversation without swiping or matching.

Acceptance criteria:

- The same unordered account pair never retains two conversations.
- Simultaneous starts resolve to the database-authoritative existing pair.
- An account cannot start a conversation with itself.
- A blocked, inactive or unverified pair cannot start or continue messaging.

### MSG-002 — Read only an authorised conversation

A conversation member must be able to read chronological messages only while
both accounts remain active, verified and mutually unblocked.

Acceptance criteria:

- A non-member receives no conversation or message content.
- A block in either direction prevents later reading.
- Message bodies are rendered as escaped plain text.
- Missing and forbidden conversations use the same safe unavailable response
  where revealing the difference would leak private state.

### MSG-003 — Send a bounded plain-text message

An authorised conversation member must be able to submit a non-empty bounded
plain-text message through a CSRF-protected POST request.

Acceptance criteria:

- The sender is taken from the authenticated session, not browser-supplied ID.
- The server rechecks membership, verification and blocking immediately before
  saving.
- A successful send updates the conversation's recent-activity time.
- The user can send without JavaScript.

### MSG-004 — Show a private recent inbox

An eligible account must be able to see its permitted direct conversations in
recent-activity order.

Acceptance criteria:

- Only conversations containing the signed-in account are returned.
- Either-direction-blocked conversations are removed before names, previews or
  message text reach the template.
- The inbox has an understandable empty state.
- No group, album, advertisement or safety-circle row exists.

### MSG-005 — Keep messaging deliberately small

Acceptance criteria:

- Messages refresh through ordinary Django page requests.
- The MVP has no attachments, reactions, typing state, read receipts, WebSockets,
  sent-message editing, expiring media or group conversations.

## 6. Blocking and private reporting

### SAF-001 — Block another account immediately

An authenticated user must be able to block a different account from an allowed
profile or conversation context.

Acceptance criteria:

- Repeating the same directional block does not create duplicates.
- A block immediately removes both accounts from each other's discovery.
- A block immediately prevents both reading and sending in their conversation.
- The blocked account receives no notification and cannot see who blocked it.

### SAF-002 — Keep reporting available separately from contact

An authenticated user must be able to report a different account even when a
block prevents discovery or messaging.

Acceptance criteria:

- Report actions are visible from permitted profile, plan and conversation
  contexts.
- An eligible received message may open the same report route with message
  context.
- Reporting is never restricted to Premium accounts.
- The reported account is controlled by server context, not an editable form
  field.

### SAF-003 — Submit one private factual report

A report must contain a bounded category and factual description about a
different account and may contain at most one optional related object.

Acceptance criteria:

- A user cannot report themselves.
- A successful submission shows a private confirmation.
- The reported account cannot see the report, reporter, count or notification.
- Submission creates no finding, sanction, score, public warning or searchable
  accusation registry.
- Reports are available only to the reporter at submission and authorised staff
  through mapped interfaces.

### SAF-004 — Validate every optional report reference

Acceptance criteria:

- Both the reporter and reported account must be connected to a referenced plan as
  owner or participant.
- A referenced conversation must contain both accounts.
- A referenced message must belong to that conversation and have been visible to
  the reporter.
- At most one plan, conversation or message reference is accepted.
- An invalid or unrelated reference rejects the request without creating a
  partial report.

### SAF-005 — Do not claim a full moderation or emergency service

Acceptance criteria:

- The MVP has no moderation finding, sanction, appeal, evidence registry, report
  priority engine or emergency response workflow.
- A private report is described as information for authorised staff, not proof.

## 7. Stripe Premium subscription

### PAY-001 — Start one hosted annual Stripe subscription

An account must be able to start the configured Premium subscription through
Stripe-hosted Checkout.

Acceptance criteria:

- The Checkout session uses the single configured recurring price: GBP 499
  (£4.99) per year.
- An account with no recorded Stripe customer or subscription receives exactly
  30 trial days, with `payment_method_collection=if_required` and missing-payment-
  method end behaviour `create_invoice`; it is not required to enter payment
  details before the trial.
- Once an account has recorded Stripe history, any later eligible Checkout omits
  the trial. An active or trialing subscription is not duplicated and is managed
  through the hosted customer portal.
- At the end of the trial Stripe creates the first GBP 4.99 annual invoice. The
  hosted invoice/customer portal asks for payment, and a paid subscription
  renews yearly unless it is cancelled in the portal.
- It carries the immutable local user ID as `client_reference_id` and subscription
  metadata.
- Kindlelise does not render or store card or bank fields.
- Creating or returning from Checkout does not grant Premium access.

### PAY-002 — Resolve Stripe ownership without email

Acceptance criteria:

- Webhook ownership uses trusted local-ID metadata or an existing unique Stripe
  customer/subscription link.
- Email is never used to choose the Kindlelise account.
- A Stripe customer or subscription ID already linked to another account is
  rejected rather than reassigned.
- Customer and subscription identifiers are unique when present.

### PAY-003 — Accept only the supported signed webhook events

The system must verify the Stripe signature against the exact raw request body
before processing:

```text
checkout.session.completed
customer.subscription.updated
invoice.paid
customer.subscription.deleted
```

Acceptance criteria:

- Correctly signed unsupported event types receive a success acknowledgement,
  create no receipt and produce no subscription change.
- The raw webhook payload is not logged or retained in the minimal receipt.
- Checkout completion records identifiers only and never grants access.

### PAY-004 — Derive Premium from current provider state

Acceptance criteria:

- A verified `trialing` subscription update grants Premium only until its future
  trial end.
- An `active` subscription update without paid-invoice evidence does not grant or
  extend the annual Premium period.
- A verified `invoice.paid` for the linked configured price and active
  subscription grants Premium only until that invoice's future annual service-
  period end.
- Unpaid, `past_due`, `unpaid`, cancelled, missing or expired access denies
  Premium.
- A deletion event sets local status to Cancelled, clears `access_until` and
  updates the latest accepted provider-event time.
- A deletion event retains the recorded Stripe customer and subscription
  identifiers for event matching and customer-portal ownership.
- A browser return cannot override webhook-derived state.

### PAY-005 — Process Stripe events once and in order

Acceptance criteria:

- Each accepted supported Stripe event ID has one durable receipt.
- A duplicate processed event is harmless.
- An older event cannot overwrite newer accepted subscription state.
- A delayed paid-invoice event may extend `access_until` to its later paid
  service-period end only when it cannot revive a subscription already revoked
  by a newer deletion or ineligible state.
- Receipt and subscription changes either complete together or neither completes.
- Failed supported-event processing leaves no committed receipt or partial
  subscription update.
- No Stripe network request runs inside the database transaction that applies the
  event.

### PAY-006 — Limit Premium effects

Acceptance criteria:

- Current Premium allows configured nearby broad areas and up to five interest
  filters.
- Free access remains limited to the current broad area and two interest filters.
- Premium does not change verification, ranking, blocking, reporting, plan,
  messaging or safety permissions.
- Stripe payment is never presented as identity or age verification.

### PAY-007 — Open the hosted customer portal safely

An account with its own recorded Stripe customer ID must be able to open Stripe's
hosted portal for the post-trial invoice, cancellation and payment management.

Acceptance criteria:

- An account without a recorded customer ID receives a safe error.
- The application never guesses, borrows or accepts a browser-supplied customer
  ID.
- Checkout success, Checkout cancellation and portal-return destinations are
  constructed by the server from the named local account route and are never
  supplied by the browser.
- Cancellation access does not require a custom Kindlelise billing interface.

## 8. Ollama Cloud draft editing

### AI-001 — Offer two explicit editing goals

An authorised conversation member may request Fix grammar or Improve clarity for
the current unsent draft.

Acceptance criteria:

- Only those two fixed goals are accepted.
- The endpoint belongs to the current conversation and is not a general writing
  service.
- Non-members, unverified accounts and either-direction blocks prevent the
  provider call.

### AI-002 — Send only the minimum draft data

Acceptance criteria:

- Ollama Cloud receives only the bounded unsent draft and fixed goal.
- Kindlelise does not send profile data, recipient details, plan data, previous
  messages, sent messages or reports.
- Drafts and suggestions are absent from application logs.
- No durable AI-suggestion model or record is created.

### AI-003 — Keep the user in control of sending

Acceptance criteria:

- Empty or over-message-limit provider output is rejected.
- A suggestion does not replace the draft until the user accepts it.
- Accepted text passes through ordinary message validation again.
- The user manually presses Send; AI never sends automatically.
- Timeout, provider failure or invalid output preserves the original draft and
  shows a quiet error.

## 9. Privacy and security

### SEC-001 — Protect browser state changes

Acceptance criteria:

- Browser state-changing routes accept POST and require CSRF protection.
- The Stripe webhook is CSRF-exempt only because the raw body signature is
  verified.
- Server-side permissions are rechecked even when a template hides an action.

### SEC-002 — Keep secrets and private content out of logs

Acceptance criteria:

- Logs do not contain passwords, sessions, message bodies, report descriptions,
  raw Stripe payloads, provider secrets, Ollama drafts or suggestions.
- Secrets come from private environment configuration and are not rendered into
  templates or committed to source control.
- Provider errors shown to users do not expose payloads, secrets or another
  account's private state.

### SEC-003 — Escape user-written content

Acceptance criteria:

- Message bodies render as text rather than executable markup.
- Display names, biographies, plan text and report confirmations are escaped by
  ordinary template behaviour.
- A stored string containing markup cannot execute script when viewed.

### SEC-004 — Fail closed without destroying the user's input

Acceptance criteria:

- Missing verification, membership, ownership or valid Stripe authority never
  grants access.
- Invalid plan, message and report submissions show understandable errors without
  creating partial state.
- Ollama failure preserves the unsent draft.
- Restricted and missing objects use a generic response where the distinction
  would leak private information.

## 10. Data integrity and usable reads

### DAT-001 — Enforce core uniqueness and checks durably

Acceptance criteria:

- One profile and one platform subscription exist per Django account.
- Verified profiles require reviewer and review time; unverified profiles require
  both fields to be null.
- Interest names are unique.
- One participation exists per account and plan.
- Joined participation requires null `left_at`; left participation requires a
  departure time.
- Plan capacity is greater than zero.
- Approved plans require reviewer and approval time; non-approved plans require
  both fields to be null.
- Conversations contain two different lower-ID-first accounts and remain unique
  per unordered pair.
- Blocks are unique per ordered blocker/blocked pair and cannot target self.
- Reports cannot target their reporter and may populate at most one optional plan,
  conversation or message reference.
- Non-empty Stripe customer IDs, subscription IDs and event IDs are unique.

### DAT-002 — Support only the reads the MVP performs

Acceptance criteria:

- The database supports indexed reads for verified broad-area profiles, plan
  status/start time, current participation, recent conversations, chronological
  messages and report status/receipt time.
- Speculative indexes or denormalised fields are not required for acceptance.

## 11. Interface and accessibility

### UI-001 — Provide four primary destinations

The authenticated mobile shell must provide Discover, Plans, Messages and
Profile as its primary destinations.

Acceptance criteria:

- Detail and form pages use clear back/dismiss navigation.
- Sticky actions do not cover the last content row or device safe area.
- The interface does not reintroduce an Intentions, circles or group-chat
  destination.

### UI-002 — Keep important actions visible and understandable

Acceptance criteria:

- Applicable Edit, Join, Join again, Leave, Cancel, Message, Block, Report,
  Stripe and Ollama actions use plain labels.
- Destructive plan cancellation and blocking receive clear confirmation.
- Status is not communicated by colour alone.
- Empty, validation, offline, provider-failure and restricted states have useful
  text and a safe next action.

### UI-003 — Preserve original product identity

Acceptance criteria:

- The interface may reuse compact layout shapes from the supplied references.
- It does not copy third-party branding, icons, advertisements, sample content,
  sexual taxonomy, paid ranking or runtime behaviour.
- A reference screenshot cannot authorise a backend feature.

## 12. Explicitly deferred requirements

The following are not acceptance requirements for the student MVP and must not be
partially implemented without the approved boundary-change procedure:

- precise proximity, browser geolocation, distance ordering or location history;
- biometric, document, social-media or payment-based identity/age verification;
- automated URL retrieval, DNS analysis, URL substantiation or AI venue review;
- URL evidence versions, anchor decisions or immutable meeting artifacts;
- participation requests, offers or invitations;
- signals, thresholds, social circles or group conversations;
- blind corroboration, sealed safety experiences or safety circles;
- meeting check-ins, emergency workflows or continuous monitoring;
- moderation findings, sanctions, appeals or evidence registries;
- multiple subscription tiers, invoices, usage billing or custom payment forms;
- AI replies, translation, moderation, profiling or automatic sending;
- message attachments, media, external notifications, native apps or advertising;
- automated retention, deletion, privacy-rights or legal-hold workflows.

Historical requirement identifiers for those systems are superseded for this
implementation and must not be used as current acceptance criteria.

## 13. Completion rule

The MVP is complete only when the approved behavioural tests in
`docs/VERTICAL_SLICE.md` prove these outcomes through public interfaces. Passing
templates without server enforcement, provider calls without safe failure, or
admin actions without state rechecks do not satisfy the requirements.
