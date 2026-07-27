# Kindlelise Student MVP Privacy Model

> **Status: student-project privacy design, not legal approval or a claim of UK
> GDPR compliance.** It describes the behaviour approved in
> `docs/VERTICAL_SLICE.md`. That document wins if the two conflict. Processing
> real users beyond a supervised assessment requires an appropriate legal review,
> privacy notice, retention schedule, rights process and operational controls.

## 1. Purpose and boundary

This document explains what personal data the Kindlelise student MVP uses, why it
uses it, who may see it and what the application must not do with it.

The implemented journey is deliberately small:

```text
account and profile
→ broad-area discovery
→ staff-reviewed public-place plan
→ participation
→ direct conversation and messages
→ optional block or private report
```

Stripe provides one no-card 30-day Premium trial followed by a GBP 4.99 yearly
subscription. Ollama Cloud may suggest an edit to one unsent message draft after
an explicit button press. Neither integration becomes an identity,
age-verification, moderation or profiling system.

Privacy is enforced by server-side queries and permissions. Hiding a field or
button in a template is never treated as access control.

## 2. Privacy rules for the MVP

1. Collect only fields mapped in the ten-model vertical slice.
2. Use broad named areas, never browser coordinates or distance history.
3. Exclude a profile before it enters discovery results when either account has
   blocked the other.
4. Show private conversations only to their two active, verified and mutually
   unblocked members.
5. Keep reports private and never treat submission as proof or a finding.
6. Send Ollama Cloud only the current unsent draft and one fixed editing goal.
7. Treat verified Stripe webhooks—not browser returns—as subscription authority.
8. Keep message bodies, report descriptions, credentials and provider payloads
   out of application logs.
9. Do not infer age, gender, sexuality, ethnicity, health, safety risk or intent.
10. Fail closed when verification, ownership, blocking or provider authority is
    missing or uncertain.

The assessment uses supervised test accounts only. The MVP does not implement age
verification and must not be presented as ready for unrestricted public use.

## 3. Data inventory and purpose

| Data | Why Kindlelise needs it | Normal visibility |
| --- | --- | --- |
| Canonical authentication email, Django password hash and session | Authentication and account ownership | Account owner and necessary Django authentication processes; password is never displayed. The email is stored in both Django's unique username field and email field but is not public profile data or Stripe ownership proof. |
| Display name and biography | A small public social profile | Eligible verified users who may open the profile. |
| Stable configured broad-area key and displayed label | Coarse discovery grouping | Eligible verified users; never presented as exact location. Arbitrary area text is rejected. |
| Controlled interests | Profile description and optional discovery filtering | Eligible verified users. |
| `availability_start`, `available_from` | Derive the coarse `Free now` display/filter | Eligible verified users after the start arrives; no separate presence history. |
| Verification state, reviewer and time | Gate discovery, plans and messaging | Account owner sees current state; authorised staff manage it. |
| Plan details and public URL | Describe one proposed public-place activity for staff review and participation | Owner and staff while pending; eligible users after approval. |
| Plan approval reviewer and time | Record the minimal staff decision | Authorised staff; users see the plan status, not internal staff details. |
| Participation state and times | Enforce capacity, joining, leaving and rejoining | The participant and necessary application processes; other users receive only the joined count. |
| Conversation membership | Authorise one direct conversation between two accounts | The two permitted members and necessary application processes. |
| Plain-text message body and sent time | Direct communication | The two permitted conversation members; ordinary staff screens do not provide a message browser. |
| Directional block | Remove both accounts from discovery and messaging | The blocker and application policy; the blocked account is not notified. |
| Private report and optional related object | Give authorised staff factual context about another account | Reporter at submission and authorised staff; never the reported account through ordinary interfaces. |
| Stripe customer/subscription identifiers, status and `access_until` | Maintain the smallest local premium-access projection | Account owner receives a simple access summary; authorised staff and billing code may inspect the projection. |
| Stripe event ID, type and provider time | Reject duplicate or older webhook events | Authorised staff and billing code; no raw payment payload is retained in the receipt. |
| Unsent draft and fixed edit goal | Request one optional grammar or clarity suggestion | Sent transiently to Ollama Cloud only after the user chooses the action. |

`settings.py` owns the fixed stable area keys, their display labels and the
explicit nearby-area mapping. A reviewed initial data migration seeds Coffee,
Walking, Museums, Live music, Cinema, Food, Games and Study. Forms reject
arbitrary area text and users cannot create free-text interests.

Kindlelise does not intentionally collect card details, bank details, biometric
templates, government identity documents, exact coordinates, movement history,
health information or private-home meeting locations in this slice.

## 4. Visibility and authority

| Actor | Permitted access |
| --- | --- |
| Unauthenticated visitor | Sign-up and sign-in pages only. |
| Signed-in but unverified account | Its own account/profile page and verification state. |
| Active verified account | Authorised discovery, public profiles, public plan pages, its own participation and its permitted direct conversations. |
| Reporter | The report form and a submission confirmation; there is no report directory or accusation history. |
| Reported account | No report content, count, reporter identity or report notification. |
| Authorised Django staff | Manual profile verification, manual plan review, private report review and minimal subscription operations required for the assessment. |
| Stripe | Data placed in hosted Checkout/Portal and the immutable local account reference required to return authoritative subscription events. |
| Ollama Cloud | One unsent draft and either `fix_grammar` or `improve_clarity`; no profile or conversation history. |

Being logged in is not enough for social access. Discovery, plans and messaging
require an active Django account and staff-verified profile. Premium access never
weakens verification, blocking, reporting or object-level permissions.

## 5. Profile, discovery and availability

- Discovery queries begin with active, verified profiles in permitted broad
  named areas.
- Either-direction blocks are removed before any result is returned to a view or
  template.
- Free accounts may filter their current broad area and at most two interests.
- Premium accounts may use configured nearby broad areas and at most five
  interests.
- The optional `Free now` filter checks only whether `available_from` exists and
  is no later than the current time.
- The account owner may choose a coarse relative availability start, replace it
  or clear it through profile editing. Availability is optional during profile
  completion and staff verification.
- The profile's Free now switch is form input only and updates the same start
  fields; it creates no stored presence boolean.
- No history row or duplicate presence boolean is created.
- No result contains coordinates, a distance, direction, movement, hidden-result
  count or paid ranking.

Display names and biographies are user-written public text. Forms should ask
users not to place phone numbers, home addresses, workplaces, financial details
or unnecessary sensitive information in them. The MVP does not claim to provide
automated sensitive-text detection.

## 6. Plans and manual URL review

A plan contains a title, description, established public place, public evidence
URL, start time and capacity. The application validates ordinary HTTPS form
syntax but does not fetch, scrape, archive, classify or send the URL to AI.

Authorised staff manually open the user-supplied public URL outside the
application and approve or reject the plan in Django Admin. The decision records
only reviewer, time and status. It does not preserve the external page or prove
that the place is safe.

Opening the URL contacts an independent website, whose operator may receive
ordinary browser request metadata. Staff should open only the submitted public
URL and must not append account IDs, report details or other Kindlelise data.

Pending and rejected plans are visible to their owner and authorised staff, not
to other ordinary users. Only approved future plans enter the public plan list.
The first successful join makes the entire plan read-only except cancellation.
Leaving and cancellation preserve the minimum participation history required by
the mapped workflow; they do not publish participant identities.

Plan forms must tell users not to submit private addresses, payment links,
personal posts or URLs containing credentials or personal tokens. Staff must not
copy private page content into approval fields because no such evidence store
exists in this MVP.

## 7. Direct messages and Ollama draft editing

One conversation exists per unordered pair of accounts. Every conversation read,
message send and AI-edit request rechecks membership, active verification and
blocking in both directions.

Messages are stored as bounded plain text and escaped when rendered. They do not
support attachments, reactions, read receipts, live delivery or group members.
Inbox and message content must not appear in third-party analytics, application
logs or external notification previews.

Ollama editing follows this exact boundary:

```text
authorised conversation
→ user enters an unsent draft
→ user chooses Fix grammar or Improve clarity
→ only draft + fixed goal go to Ollama Cloud
→ bounded suggestion returns
→ user accepts or rejects it
→ ordinary form validation runs again
→ user manually sends
```

The application does not send profiles, previous messages, reports or recipient
details to Ollama Cloud. It does not durably store the suggestion as a separate
record, automatically replace the draft or automatically send a message. Failure
preserves the original draft.

Provider terms, retention and training controls must be checked before using real
personal data. For assessment demonstrations, use non-sensitive test content.
The existence of a free provider plan is not a privacy guarantee.

## 8. Blocking and private reports

A block is directional storage with mutual product effect. Once recorded, both
accounts are removed from each other's discovery and cannot open or send direct
messages. The blocked account receives no notification and cannot see who
created the block.

A report:

- always identifies a reporter and a different reported account;
- contains a bounded category and factual description;
- may reference at most one server-validated plan, conversation or message;
- is available to authorised staff and is never shown to the reported account;
- creates no finding, sanction, public label, risk score or searchable accusation
  registry;
- does not notify the reported account.

The browser cannot supply an arbitrary trusted object reference. The server must
confirm that both accounts are connected to a plan as owner or participant, that a
conversation contains both accounts, and that a referenced message belongs to
that conversation and was visible to the reporter.

The report form should discourage home addresses, financial details, unrelated
third parties and unnecessary health or identity information. Because the MVP has
no specialist moderation or evidence system, live high-risk reporting must not be
claimed as an emergency service.

## 9. Stripe boundary

Stripe-hosted Checkout creates the subscription but does not require payment
details for an account's first 30-day trial. At trial end Stripe creates and
hosts the GBP 4.99 annual invoice; its hosted invoice and customer portal handle
payment and cancellation. Kindlelise never renders or stores card or bank fields.
Recorded Stripe history prevents a second trial, and a paid subscription renews
yearly unless cancelled through the hosted portal.

Checkout success, Checkout cancellation and portal-return destinations are built
by the server from the named local account route. The browser cannot supply them.

Checkout receives the immutable local user ID as `client_reference_id` and
subscription metadata. Kindlelise never assigns Stripe ownership from email.
Returning from Checkout grants no access. Only a verified, newer subscription
webhook may grant a future trial end, and only a verified paid-invoice webhook may
grant the paid annual service period. An active subscription status by itself is
not payment evidence. Deletion clears premium access.

The webhook accepts only `checkout.session.completed`,
`customer.subscription.updated`, `invoice.paid` and
`customer.subscription.deleted`. Unsupported signed event types receive a
success acknowledgement but create no receipt and no local subscription change.

The raw webhook body is used to verify Stripe's signature and must not be logged
or stored as the webhook receipt. The minimal receipt contains the Stripe event
ID, supported event type, provider time and processing time for duplicate and
ordering protection. Stripe identifiers already linked to another account are
rejected rather than reassigned.

Supported receipt creation and subscription changes are atomic; failure commits
neither. Subscription deletion sets status to cancelled, clears `access_until`,
updates the provider-event time and retains the customer and subscription IDs for
safe matching and portal ownership.

Stripe is a payment provider in this project. A successful payment does not prove
the payer's identity or age and must never be presented as verification.

## 10. Logging, secrets and transport

- Django passwords use Django's authentication and password-hashing facilities;
  application code never logs or returns them.
- Session cookies, CSRF protection, secure deployment settings and HTTPS are used
  according to the mapped configuration.
- Django, Stripe and Ollama secrets come from environment variables and never
  enter templates, source control or browser JavaScript.
- Logs may contain a short request outcome and non-sensitive internal identifier,
  but never message text, report descriptions, passwords, session values, raw
  Stripe payloads or Ollama drafts/suggestions.
- Provider errors shown to users are short and do not expose secrets, payloads or
  another account's existence.
- Missing and forbidden profiles, plans and conversations use the same safe
  not-found presentation where the distinction would disclose private state.

## 11. Retention, deletion and user controls

The student MVP does not implement a general privacy dashboard, automated
retention engine, data export, self-service account deletion or legal-hold
system. It must not claim that it does.

Implemented controls are limited to:

- editing the account's permitted profile fields;
- replacing or clearing current availability;
- leaving a plan while preserving the mapped participation row;
- cancelling an owned plan while preserving participation history;
- blocking another account;
- privately reporting another account;
- managing payment cancellation through Stripe's hosted portal;
- signing out of the current session.

Messages, reports, plans, participation, blocks, subscription projections and
webhook receipts otherwise remain durable in the MVP database. Assessment-data
cleanup, when authorised, is a documented manual administrator task outside the
public application. Expired availability and premium access stop having product
effect but are not described as automatically erased.

Before using real public data, the project needs a documented retention schedule,
account-closure process, access/correction/deletion request handling, backup
procedure and clear explanation of any records that must be retained.

## 12. Failure behaviour

- Missing or expired verification denies discovery, plans and messaging.
- A block or uncertain conversation membership denies reading, sending and AI
  editing without explaining another account's private state.
- Invalid discovery filters return understandable form errors and no expanded
  result set.
- Ollama failure preserves the original draft and sends nothing automatically.
- Stripe failure or a browser return leaves premium access unchanged until a
  verified trialing update or paid invoice establishes it.
- Duplicate or older Stripe events cannot overwrite newer accepted state.
- Invalid report references are rejected without creating a partial report.
- Failed plan review or an unavailable external URL does not publish the plan.

## 13. Explicitly deferred privacy systems

This MVP does not contain or claim:

- precise proximity processing, coordinate encryption or movement retention;
- biometric, document or payment-based age verification;
- blind corroboration, sealed experiences, matching tokens or safety circles;
- group conversations, pseudonymous support identities or safety check-ins;
- automated URL retrieval, stored webpage evidence or AI venue approval;
- moderation findings, sanctions, appeals or formal evidence custody;
- message attachments, media privacy or external notification delivery;
- automated privacy-rights workflows, deletion orchestration or audit-event
  models;
- advertising, paid ranking, behavioural analytics or AI training on user data.

These require separate approval, models, workflows, privacy analysis and
operational ownership. They cannot be inferred from this document or added while
implementing the 36-implementation-file vertical slice.

## 14. Student assessment checklist

Before demonstrating the MVP, verify that:

1. only active verified profiles enter discovery;
2. broad areas are used and no coordinates are collected;
3. the `Free now` filter uses only `available_from` values whose start has arrived;
4. either-direction blocking excludes discovery and conversation access;
5. pending/rejected plans stay private to their owner and staff;
6. plan pages show joined counts rather than participant identities;
7. messages are escaped and absent from logs;
8. reports are private, references are validated and the reported account is not
   notified;
9. Stripe Checkout cannot grant premium access, the trial requires no upfront
   card data and Kindlelise stores no card data;
10. Stripe deletion clears `access_until` and premium access;
11. Ollama receives only an explicitly submitted unsent draft and fixed goal;
12. AI failure preserves the original draft and never sends a message;
13. secrets and raw provider payloads are absent from logs and source control;
14. the interface makes no claim of legal compliance, guaranteed venue safety,
    emergency response, age verification or automatic deletion;
15. all deferred production privacy systems remain absent.
