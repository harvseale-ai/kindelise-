# Kindlelise 36-File Vertical Slice

## 1. Purpose

This document is the implementation boundary for a student-scale Kindlelise MVP.
It describes the smallest system that can be built, tested, demonstrated and
explained clearly within the project period.

The assessed journey is:

```text
register or sign in
→ complete a profile
→ receive manual staff verification
→ appear in a broad-area discovery grid
→ create an immediately available plan
→ join or leave a plan
→ exchange direct messages
→ block or privately report another account
```

Two required external integrations remain deliberately narrow:

- Stripe provides one premium subscription through hosted Checkout and the
  hosted customer portal.
- Ollama Cloud suggests grammar or clarity edits for one unsent message draft.

The production-scale architecture remains useful future-work material. It is not
an implementation source for this vertical slice.

### Assessment position

The implementation should be defended in these terms:

> Kindlelise deliberately replaces production-scale location, meeting-evidence
> and workflow systems with broad areas, manual profile verification and bounded
> public-place metadata assistance. Stripe and
> Ollama Cloud are narrow integrations. The implemented journey is small enough
> to test fully and explain line by line, while production hardening is recorded
> as future work.

The assessment uses supervised test accounts only. This MVP does not implement
age verification and must not be presented as ready for unrestricted public use.

## 2. Golden implementation rules

1. **No file expansion without approval.** A new file requires a written reason,
   the rejected existing owners and explicit approval before it is created.
2. **Control responsibility expansion.** A new model, route, dependency, workflow
   or file requires a documented reason and approval. A small public function may
   be added without a formal decision only when it stays inside an existing
   approved responsibility and enters this function map in the same change.
3. **Use the simplest working design.** Prefer Django defaults, plain functions
   and ordinary relational constraints over frameworks or abstractions.
4. **Keep every function small.** Each function must use the smallest practical
   amount of code needed to perform its named job. Expansion requires an
   explanation.
5. **Keep the code human-readable.** Names should describe behaviour in ordinary
   language. Cleverness is not a design goal.
6. **Comments must add understanding.** Comment security decisions, ownership,
   non-obvious conditions and reasons. Do not add a comment beside every obvious
   line or merely restate the syntax.
7. **No unapproved feature expansion.** Build only the journey fixed here.
8. **No dependency without a demonstrated need.** Use Django or the standard
   library when they already solve the problem adequately.
9. **One authoritative owner per behaviour.** Views translate HTTP requests, forms validate
   user input, policies answer permission questions, services own user/provider
   workflows, mapped admin actions and the mapped User-admin verification
   control own staff review, selectors read state and models enforce durable
   truth.
10. **Fail closed.** Missing verification, permission, Stripe state or provider
    response must never grant access.
11. **Keep private data out of logs.** Never log message bodies, report text,
    passwords, secrets, webhook payloads or AI drafts.
12. **Test behaviour, not implementation detail.** Tests should prove outcomes
    and security boundaries through public interfaces.
13. **Do not weaken a failing test to make it pass.** Correct the code or document
    and approve a changed requirement.
14. **Prefer deletion and consolidation.** Before adding code, check whether an
    existing responsibility can be made clearer or unnecessary code removed.
15. **Keep documentation synchronized.** Approved boundary changes update this
    file and `docs/DECISIONS.md` in the same change.
16. **Stop at the requested outcome.** Do not add speculative flexibility,
    configuration or extension points.

## 3. Included product behaviour

### Accounts and profiles

- Django authentication, password hashing, sessions and CSRF protection.
- Email address and password are the only MVP authentication credentials. The
  registration form trims and canonicalises the email address to lowercase, then
  stores that same value in Django User's unique `username` field and `email`
  field. Sign-in canonicalises the supplied email in the same way before using
  Django authentication. This keeps Django's existing User model and unique
  account identifier without a custom authentication backend or migration.
- One profile per account.
- A display name, short biography, broad named area and controlled interests.
- One optional owner-uploaded profile image. The form accepts only JPEG, PNG or
  WebP files up to 5 MB and 4,096 pixels on either side, normalises the image and
  removes embedded metadata before storage. The image is presentation only: it
  is not identity, age, character or safety evidence. An authenticated,
  access-controlled application route serves it; no direct media route exists.
  Local filesystem storage is sufficient only for this supervised assessment.
  Durable production object storage, moderation and retention automation remain
  outside this slice.
- Optional `available_from` for a small user-set availability-start indication.
  Profile completion and staff verification never require it. The profile form
  offers a form-only `Free now` switch plus `Today`, `Tomorrow`, `This week` and
  `As and when`: the switch, Today, This week and As and when start at the
  submission time, while Tomorrow starts at local midnight. The user may clear
  the signal later. The switch is input convenience, not a stored boolean.
- Staff-controlled `is_verified`, `verified_at` and `verified_by` fields.
- Authorised staff may set or remove that profile verification either through
  the Profile list actions or a `Profile verified` checkbox in the related
  Django User change page's Permissions section. Both entry points enforce the
  same profile-completion and reviewer/time rules.
- Only active, verified accounts may use discovery, plans or messaging.

### Discovery

- A simple grid of verified profiles in permitted broad named areas.
- `config/settings.py` owns the approved stable area keys, display labels and
  nearby-area mapping. Forms store stable keys rather than free-text area names.
- Optional filtering by the reviewed data migration's initial interest vocabulary:
  Coffee, Walking, Museums, Live music, Cinema, Food, Games and Study.
- An optional `Free now` switch filtering to profiles whose `available_from`
  exists and is no later than the current time.
- Mutual block exclusion before a profile enters the result set.
- Free accounts: any combination of their saved broad areas and at most two
  interest filters.
- Premium accounts: any combination of saved and configured nearby
  named areas, plus at most five interest filters.
- Premium never overrides verification, blocking or visibility rules.

The student assessment uses this deliberately generic configuration:

```python
KINDLELISE_AREAS = {
    "central": "Central",
    "north": "North",
    "south": "South",
    "east": "East",
    "west": "West",
}

KINDLELISE_NEARBY_AREAS = {
    "central": ["north", "south", "east", "west"],
    "north": ["central"],
    "south": ["central"],
    "east": ["central"],
    "west": ["central"],
}
```

Changing these assessment labels is configuration, not a new feature, provided
the stable-key and explicit-nearby-map rules remain unchanged.

### Plans

- A verified user creates an immediately available plan with a title,
  description, established public place, public information URL, start time and
  capacity.
- An explicit `Fetch details` action may suggest an editable public place and one
  protected normalised thumbnail from the public HTTPS page.
- The URL must identify an independently established public place or organised
  activity. A dropped map pin, residential address, payment link or personal
  social post cannot be approved as the primary meeting evidence.
- Kindlelise does not preserve the fetched page, prove that the venue is safe or
  guarantee that the external page will not later change.
- Only approved future plans appear in the public plan list and accept joins.
- The first successful join makes the entire plan read-only except cancellation.
- Participants can leave; owners can cancel.
- Historical participation rows remain; current membership ends through state.

### Direct messaging

- One conversation per unordered pair of accounts.
- Plain-text messages refreshed through normal Django page requests.
- No media, reactions, read receipts, live sockets or group conversations.
- A mutual block check applies when opening and sending in a conversation.

### Blocking and private reporting

- A user can block another user from a profile or conversation.
- A report button is visible on profile, plan and conversation pages.
- A report always identifies the reported user and may reference one plan,
  conversation or message for staff context.
- Reports are private to the reporter and authorised staff.
- A report does not itself create a finding, accusation registry or sanction.

### Stripe premium subscription

- One subscription product and one configured recurring Stripe price of GBP 499
  (£4.99) per year.
- Each local account may receive one 30-day Premium trial. Trial eligibility is
  exhausted once that account has a recorded Stripe customer or subscription;
  cancelling and starting again never creates a second trial.
- Stripe-hosted Checkout starts the subscription with
  `payment_method_collection=if_required`, `trial_period_days=30` and
  `trial_settings.end_behavior.missing_payment_method=create_invoice` for a
  trial-eligible account. This does not require payment details before the trial.
- A later eligible Checkout for an account with Stripe history uses the same
  annual price without another trial. An existing `active` or `trialing`
  subscription cannot be duplicated and is managed through the portal instead.
- At trial end Stripe creates the first GBP 4.99 annual invoice. Stripe's hosted
  invoice and customer-portal surfaces request and manage payment; Kindlelise
  does not render a local card form or promise that an email is sent unless the
  applicable Stripe email setting is enabled.
- The paid subscription renews yearly at GBP 4.99 unless it is cancelled through
  Stripe's hosted customer portal.
- Stripe's hosted customer portal handles cancellation and payment management.
- A verified webhook is authoritative for local premium access.
- Only `checkout.session.completed`, `customer.subscription.updated`,
  `invoice.paid` and `customer.subscription.deleted` are handled.
- Checkout completion records the Stripe customer and subscription identifiers;
  a trialing update grants trial access, a paid invoice grants the paid service
  period, and subscription deletion removes access.
- Checkout includes the immutable local user ID as `client_reference_id` and as
  `kindlelise_user_id` in subscription metadata. Webhooks resolve ownership from
  those trusted identifiers or an existing unique Stripe-ID link, never email.
- `checkout.session.completed` records identifiers only and never grants premium.
- `customer.subscription.updated` grants Premium only for `trialing` with a
  future trial end stored as `access_until`. An `active` status without a
  verified paid invoice is not payment evidence and cannot extend access.
- `invoice.paid` grants Premium only for the linked configured annual price, an
  `active` subscription and a future paid service-period end stored as
  `access_until`. An unpaid, `past_due`, `unpaid`, expired or otherwise
  ineligible state denies Premium.
- No card or bank details are stored by Kindlelise.

### Ollama Cloud message editing

- The user explicitly chooses “Fix grammar” or “Improve clarity”.
- The suggestion endpoint belongs to one conversation URL and requires current
  conversation membership, active verification and no block in either direction.
- Only the current unsent draft and fixed goal are sent to Ollama Cloud.
- No profile, conversation history, report or sent message is supplied.
- The returned suggestion replaces nothing until the user accepts it.
- A suggestion must be non-empty and no longer than the ordinary message limit;
  otherwise it is rejected and the original draft remains unchanged.
- An accepted suggestion passes through `MessageDraftForm` again before sending
  and is always rendered as plain text.
- The user must manually send the final draft.
- Provider failure preserves the original draft and shows a quiet error.

## 4. Explicitly deferred

The following are future work and must not enter the MVP without approval:

- Exact coordinates, browser geolocation, distance ordering or location history.
- Automated URL fetching, DNS checks, URL substantiation or AI venue approval.
- Plan URLs as separate records, anchor decisions or evidence version binding.
- Plan version lineages, immutable meet artifacts or participation offers.
- Social-circle thresholds, invitations, group messaging or safety circles.
- Presence as a separate model; the profile field is sufficient for the MVP.
- Verification history as a separate model.
- Message attachments, live delivery, typing state or read receipts.
- Moderation findings, sanctions, appeals or evidence registries.
- Multiple subscription tiers, usage billing or custom payment/cancellation UI.
- AI reply generation, translation, moderation or automatic sending.
- Native mobile applications and third-party advertising.

## 5. Implementation-file limit and exact structure

Thirty-six implementation files is a **maximum boundary**, not a target that must
be filled. Unused files may stay absent until their mapped responsibility is
implemented. Supporting governance and assessment documents are outside this
implementation-file count. Django-generated schema migrations and the reviewed
initial-interest data migration are separate mechanical exceptions; they do not
authorise new product responsibilities. The current map uses 34 of the permitted
36 implementation-file slots; the remaining two are deliberately unallocated.

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
18  kindlelise/plan_metadata.py
19  kindlelise/selectors.py
20  kindlelise/views.py
21  kindlelise/urls.py
22  kindlelise/ai_message_editor.py
23  kindlelise/migrations/__init__.py
24  templates/base.html
25  templates/discover.html
26  templates/account.html
27  templates/plan.html
28  templates/inbox.html
29  templates/conversation.html
30  templates/report.html
31  static/app.css
32  static/app.js
33  tests/conftest.py
34  tests/test_vertical_slice.py
```

Dependency direction:

```text
urls → views → forms / policies / services / selectors
services → policies / models
selectors → policies / models
admin → services / models
ai_message_editor → configured Ollama Cloud API only
models → Django ORM and standard value types only
```

Models must not import views, forms, selectors, services or provider clients.

## 6. Small durable model

The MVP uses ten Kindlelise models plus Django's existing `User` model:

| Entity | Durable purpose |
| --- | --- |
| `Profile` | Public identity, broad area, verification, availability and interests for one Django user. |
| `Interest` | Staff-seeded controlled discovery vocabulary. |
| `Plan` | One available public-place activity with an optional protected thumbnail and lockable meeting details. |
| `Participation` | One user's current or ended participation in one plan. |
| `Conversation` | The unique unordered relationship between two users. |
| `Message` | One plain-text message sent inside a conversation. |
| `Block` | One directional block; policy treats either direction as exclusion. |
| `Report` | A private user statement about another user with an optional plan, conversation or message reference. |
| `PlatformSubscription` | Minimal local projection of one Stripe subscription. |
| `StripeWebhookReceipt` | Unique processed Stripe event ID and ordering timestamp. |

Django's existing `User` supplies the eleventh durable entity; Kindlelise must not
create a replacement account model for this slice.

The `Profile.interests` relation uses Django's automatic many-to-many join table.
No `ProfileInterest` model is needed because the relationship has no additional
behaviour.

### Essential fields and states

| Entity | Essential fields |
| --- | --- |
| `Profile` | `user`, optional `profile_image`, `display_name`, `title_statement`, `biography`, `broad_area`, `broad_areas`, `interests`, `available_from`, `is_verified`, `verified_at`, `verified_by` |
| `Interest` | `name` |
| `Plan` | `owner`, `title`, `description`, `public_place`, `public_url`, optional `thumbnail_image`, `starts_at`, `capacity`, `status`, `approved_at`, `approved_by`, `meeting_details_locked_at`, `created_at` |
| `Participation` | `plan`, `user`, `status[joined\|left]`, `joined_at`, `left_at` |
| `Conversation` | `first_user`, `second_user`, `updated_at` |
| `Message` | `conversation`, `sender`, `body`, `sent_at` |
| `Block` | `blocker`, `blocked_user` |
| `Report` | `reporter`, `reported_user`, `category`, `description`, one optional plan/conversation/message FK, `status[received\|reviewed]`, `received_at` |
| `PlatformSubscription` | `user`, nullable `stripe_customer_id`, nullable `stripe_subscription_id`, nullable `stripe_status`, nullable `access_until`, nullable `latest_provider_event_at`, `updated_at` |
| `StripeWebhookReceipt` | `stripe_event_id`, `event_type`, `provider_created_at`, nullable `processed_at` set only after the subscription update succeeds |

Safe model defaults are `Profile.is_verified = false`, `Plan.status = pending`,
new `Participation.status = joined` and `Report.status = received`. A plan is past
when `starts_at` is no later than the current time; `past` is derived and is not a
stored plan status.

Registration creates the required one-to-one profile before profile completion.
That new unverified row may therefore have empty `display_name` and `broad_area`
values. `ProfileDetailsForm` requires a non-empty display name and a configured
broad-area key when the account completes or updates the profile, and staff
verification refuses a profile until both values are valid. Availability remains
optional and may be added after profile completion or verification. Empty profile
values are an onboarding state only and never make an account eligible for social
features.

### Exact input and provider-value bounds

Models and forms reuse these limits; views do not invent different limits:

| Value | Maximum or approved choices |
| --- | --- |
| Authentication email | Valid email address, canonical lowercase, at most 150 characters because Django's unique `username` field stores the same value |
| Profile display name | 80 characters |
| Profile biography | 500 characters |
| Profile image | Optional JPEG, PNG or WebP; 5 MB and 4,096 pixels per side maximum; embedded metadata removed |
| Broad-area key | 20 characters and present in `KINDLELISE_AREAS` |
| Interest name | 50 characters and seeded/staff-controlled |
| Plan title | 120 characters |
| Plan description | 1,000 characters |
| Plan public-place name | 200 characters |
| Plan public URL | 500 characters, normal HTTPS URL |
| Message or Ollama suggestion | 1,000 characters |
| Report category | `harassment`, `spam`, `misleading_plan`, `safety_concern` or `other` |
| Report description | 2,000 characters |
| Stripe customer, subscription or event ID | 255 characters |
| Stripe event type or subscription status | 80 characters |

Passwords use Django's configured validators rather than a duplicate local
length rule. A plan URL is still approved only by staff after manual inspection;
passing the URL field validation does not establish a safe public meeting place.

## 7. Essential constraints and indexes

Database constraints must enforce:

- One profile and one platform subscription per user.
- A verified profile requires both `verified_at` and `verified_by`; an unverified
  profile requires both fields to be null.
- Unique interest names.
- One participation per user and plan.
- Joined participation requires null `left_at`; left participation requires a
  populated `left_at`.
- A plan capacity greater than zero.
- An approved plan requires both `approved_at` and `approved_by`; every other
  plan state requires both fields to be null.
- A conversation has two different users, with the lower account ID stored first.
- One conversation per ordered pair of account IDs.
- One directional block per blocker and blocked user, with no self-block.
- A report cannot target its reporter.
- At most one of a report's optional plan, conversation or message references is
  populated.
- Stripe customer IDs, subscription IDs and webhook event IDs are unique when
  present.

Foreign-key deletion behaviour is explicit: profile ownership cascades;
referenced staff reviewer accounts use `PROTECT` and are deactivated instead of
deleted; plan ownership, participation, conversations, messages, reports and
subscription ownership use `PROTECT`; block account references cascade; optional
report context uses `PROTECT`. These choices prevent routine account or staff
deletion from silently removing retained history.

Indexes are limited to reads that the MVP actually performs:

- `Profile(is_verified, broad_area)`.
- `Plan(status, starts_at)`.
- `Participation(plan, status)` and `Participation(user, status)`.
- `Conversation(first_user, updated_at)`.
- `Conversation(second_user, updated_at)`.
- `Message(conversation, sent_at)`.
- `Report(status, received_at)`.

Application invariants must enforce:

- Social features require an active user and verified profile.
- Staff verification requires a completed profile with a non-empty display name
  and a broad-area key currently present in `KINDLELISE_AREAS`.
- Discovery uses broad named areas only and excludes either-direction blocks.
- Unapproved, rejected, cancelled or past plans cannot be joined.
- Plan owners cannot join their own plans.
- Plan capacity counts participant places and does not include the owner.
- A message sender must be one of the conversation's two users; the service
  enforces this because a portable cross-table database check is unavailable.
- The first successful join sets `meeting_details_locked_at` in the same database
  transaction; after that the entire plan is read-only except cancellation.
- Joining locks the plan row with `select_for_update()`, recounts joined
  participation, rechecks capacity, creates or reactivates participation and sets
  `meeting_details_locked_at` when this is the first join.
- A user who left may rejoin only while the plan remains approved, future,
  uncancelled and below capacity. Rejoining updates the existing row with
  `joined_at` set to the latest successful join time and `left_at` set to `null`.
- An unlocked approved plan stays approved when edited.
- A rejected unlocked legacy plan may be edited; saving activates it.
- A cancelled plan is terminal: it cannot be edited, approved or reactivated.
- Leaving ends current participation without deleting its row.
- Cancelling hides a plan, prevents future joins and clears the current approval
  fields without deleting participation history.
- Reports remain invisible to the reported user and ordinary users.
- A report's optional reference is server-validated and may identify at most one
  plan, conversation or message.
- A referenced plan requires both the reporter and reported user to be connected
  to it as owner or participant. A referenced conversation must contain both
  accounts. A referenced message must belong to that two-account conversation and
  have been visible to the reporter.
- Stripe signatures are verified before parsing trusted event data.
- Stripe ownership comes from `client_reference_id`, `kindlelise_user_id`
  metadata or an existing unique Stripe-ID link; customer email is never used.
- A Stripe customer or subscription ID already linked to another account is
  rejected rather than reassigned.
- The configured Stripe price is one GBP 499 yearly recurring price. A first
  completed subscription Checkout may apply exactly 30 trial days without
  upfront payment details; any later Checkout for that local account omits the
  trial, and an existing active or trialing subscription is not duplicated.
- Duplicate Stripe events are harmless because the event ID is unique.
- Older Stripe events cannot overwrite a newer accepted subscription state.
- Because Stripe delivers related event types asynchronously, a delayed
  `invoice.paid` may extend `access_until` to its later paid service-period end
  only while the linked subscription remains active and has not been revoked or
  made ineligible by a newer event. It never rewinds status or revives a
  cancelled subscription.
- `checkout.session.completed` stores identifiers only. A newer
  `customer.subscription.updated` supplies status but grants or extends access
  only for a trialing period. A verified `invoice.paid` supplies the paid annual
  service-period end; `customer.subscription.deleted` removes access.
- Subscription deletion retains the stored Stripe customer and subscription IDs
  for safe event matching and customer-portal ownership.
- Premium access requires a webhook-authorised `trialing` or paid `active` state
  and `access_until` later than the current time. An active subscription update
  alone, or an unpaid, past-due or expired invoice, cannot grant a paid year.
- Stripe event receipt and subscription updates occur in one short database
  transaction: lock or create receipt, reject a processed event, compare provider
  time, update subscription, then mark the receipt processed. No Stripe network
  request occurs inside that transaction.
- If Stripe processing fails, that transaction rolls back both changes, so no
  failed receipt remains committed. A committed receipt always has
  `processed_at`, although the field is nullable while the atomic workflow is in
  progress.
- A signature-valid unsupported Stripe event is acknowledged without storing a
  receipt or changing subscription state.
- Ollama Cloud failure never changes or sends the user's draft.

## 8. Planned public function map

The functions listed here are the planned public application functions. A small
function discovered during implementation may be added when it stays inside an
existing approved file responsibility, has a concrete need and is added to this
map with tests in the same change. It must not create an alternative workflow.

### Naming and comment contract

Every public name must describe its observable job without requiring the reader
to know an architectural abbreviation:

- Start permission questions with `can_` and name the exact action being decided.
- Start read operations with `get_` and name the exact records or page data
  returned.
- Start state-changing operations with a direct verb such as `create`, `update`,
  `join`, `leave`, `cancel`, `send`, `block` or `submit`.
- Include an important condition in the name when omitting it would mislead the
  reader, such as `approved`, `verified`, `unblocked`, `owned` or `unsent`.
- Use the same product words everywhere: account, profile, discovery grid, plan,
  participation, direct conversation, message, block, private report, premium
  access and staff review.
- Do not use vague public names such as `handle`, `process`, `manage`, `execute`,
  `helper`, `data`, `item`, `thing`, `result` or `context` without naming the
  specific subject.

Every public function must have a short plain-language docstring stating:

```text
Purpose: the one outcome this function owns.
Inputs: what each argument represents and whether it is already validated.
Returns: the concrete value or decision returned.
Changes: the database or external state changed, or “none”.
Refuses: the important conditions that cause denial or safe failure.
Privacy: any private value that must not be returned, stored or logged.
```

Omit a label only when it genuinely does not apply. Add an inline comment before
a non-obvious security, transaction or privacy decision to explain **why** it is
needed. Do not place repetitive comments beside self-explanatory assignments.

For every callable below, the sentence after the em dash is the required summary
comment. Use it as the opening docstring sentence when the function is written;
the longer docstring then fills the applicable labels above. A future
implementation must not replace it with vague text such as “handles a user” or
“processes data”.

Django-required hook names such as `clean()`, `save()` and `__str__()` are the
only naming exception. Keep the framework's exact name and use the class name and
docstring to explain the specific job. Do not override a hook unless declarative
fields, constraints or an already mapped service cannot do the job more simply.

### `kindlelise/admin.py`

- `KindleliseUserAdmin` — Extend Django's existing User change page with a
  form-only `Profile verified` checkbox in Permissions. Show and accept the
  control only for staff who have both Django User change permission and
  Kindlelise Profile change permission. On save, recheck that the related
  profile has a non-empty display name and configured broad-area key before
  verification; record the requesting staff account/time when checked and clear
  all three verification fields when unchecked. Do not add a custom admin URL,
  duplicate verification field or alternative public workflow.

- `verify_selected_profiles_for_discovery_plans_and_messages(model_admin, request, profiles)` —
  Recheck each selected profile, verify only currently unverified profiles with a
  non-empty display name and configured broad-area key for discovery, plans and
  direct messages, and record the staff account and time.
- `remove_verification_from_selected_profiles(model_admin, request, profiles)` —
  Recheck each selected profile and withdraw only current verification so policies
  deny discovery, plan and messaging access without deleting existing records.
- `approve_selected_plans_after_manual_url_check(model_admin, request, plans)` —
  Recheck every selected plan and approve only pending future unlocked plans whose
  URL and public place the staff member manually checked, recording reviewer/time.
- `reject_selected_plans(model_admin, request, plans)` — Recheck every selected
  plan and reject only pending unlocked plans so they stay
  out of discovery, without deleting them or exposing private staff notes.

Ordinary `ModelAdmin` registrations provide list, filter and read views for
profiles, interests, plans, reports, subscriptions and webhook receipts. The
User Permissions checkbox uses a private admin-bound form only; no custom admin
URL or public review form is added.

Admin actions iterate through selected records and recheck each state; they never
blindly call `queryset.update()`. They skip already locked, cancelled or otherwise
ineligible records and tell staff how many were changed or skipped.

### `kindlelise/models.py`

Model classes:

- `Profile` — Stores public profile details, broad area and whether staff has
  verified the account.
- `Interest` — Stores the small staff-seeded interest vocabulary.
- `Plan` — Stores the single editable plan and its approval/lock state.
- `Participation` — Stores joined or ended participation.
- `Conversation` — Stores two accounts once, with the lower account ID first.
- `Message` — Stores one bounded plain-text message; templates escape it when
  rendering.
- `Block` — Stores a directional block.
- `Report` — Stores a private statement and at most one optional plan,
  conversation or message reference.
- `PlatformSubscription` — Stores the Stripe subscription status used to decide
  current premium access.
- `StripeWebhookReceipt` — Records one processed Stripe event so it cannot be
  processed twice.

Readable model helpers:

- `Profile.is_available_now(at_time)` — Return `True` only when the profile has an
  `available_from` time no later than the supplied timezone-aware time; never
  change the stored availability.
- `Plan.is_open_for_joining(at_time)` — Return `True` only when the plan is
  approved, starts after the supplied time, is not cancelled and has spare
  capacity; never create participation here.
- `Conversation.includes_account(user)` — Return `True` only when the supplied
  account is exactly the conversation's first or second account.
- `PlatformSubscription.has_premium_access()` — Return `True` only for the local
  Stripe states `active` or `trialing` when `access_until` is later than the
  current time; checkout creation alone never grants premium access.

Model `save()` methods must not run workflows, call providers or silently change
unrelated fields.

Each staff-visible model may implement Django's standard `__str__()` method to
return a short safe label such as display name, plan title or masked Stripe event
ID. A report label must never include its private description.

### `kindlelise/forms.py`

Form classes:

- `AccountSignUpForm` — Validates one canonical lowercase email address, password
  and password confirmation using Django's password rules. It rejects an email
  already stored in Django's unique `username` field; the service stores the same
  canonical value in both `username` and `email`.
- `ProfileDetailsForm` — Validates and metadata-strips the optional bounded
  profile image before display name, biography, broad area, optional form-only
  `Free now` switch, availability-start choice and selected interests.
  It accepts only configured stable area keys, converts the switch or four fixed
  relative choices to one timezone-aware `available_from` value, permits a
  missing/cleared choice and never exposes verification fields.
- `DiscoveryFiltersForm` — Validates one or more selected authorised broad areas,
  interest filters and an
  optional `Free now` filter, applying the caller's free or premium area and
  interest limits. Current availability is derived from `available_from`; the
  form does not create a second stored availability value.
- `PlanDetailsForm` — Validates plan content and a normal HTTPS public URL; it does
  not fetch or approve the URL.
- `PlanMetadataRequestForm` — Validates the normal public HTTPS URL accepted by
  the explicit metadata-fetch action.
- `MessageDraftForm` — Validates one bounded non-empty plain-text draft.
- `MessageEditRequestForm` — Accepts only `fix_grammar` or `improve_clarity` for an
  unsent bounded draft.
- `PrivateReportForm` — Validates category and bounded factual description while
  keeping reporter and target fields server-controlled.

### `kindlelise/policies.py`

- `can_access_discovery_plans_and_messages(user)` — Return `True` only for an
  authenticated, active account with a staff-verified profile; return `False`
  without changing the account for every other case.
- `can_show_profile_in_discovery_grid(viewer, profile)` — Return `True` only when
  the viewer may use discovery, the profile is active and verified, its broad area
  is permitted and neither account has blocked the other.
- `can_view_profile_page(viewer, profile)` — Return `True` only when both accounts
  may use the product and neither account has blocked the other; reveal no denial
  reason to the viewer.
- `can_create_plan(user)` — Return `True` only when the account is active and
  verified and may therefore create an available public-place plan.
- `can_join_approved_plan(user, plan, at_time)` — Return `True` only for an active
  verified non-owner joining an approved future plan with spare capacity who is
  not already in `joined` state. No row and an existing `left` row are both
  eligible inputs; the service decides whether to create or reactivate the row.
- `can_start_or_continue_direct_messages(sender, recipient)` — Return `True` only
  when both different accounts are active and verified and neither has blocked
  the other.
- `can_report_another_user(reporter, reported_user)` — Return `True` for an
  authenticated reporter targeting a different account, even when a block stops
  discovery or messaging.
- `get_allowed_discovery_areas_and_interest_limit(user)` — Return the exact broad
  areas and maximum interest-filter count allowed by the account's current free or
  premium state, without weakening verification or block exclusions.

Policy functions return decisions only. They do not redirect, write, send,
notify or call Stripe or Ollama.

### `kindlelise/services.py`

- `create_account_and_profile(new_account_details)` — Create one Django account
  and its empty unverified profile in one transaction so neither record remains if
  creation of the other fails.
- `update_signed_in_user_profile(user, profile_changes)` — Update only
  the signed-in account's optional profile image, display name, biography, broad
  area, availability and interests; remove a replaced image after commit and
  never accept verification or subscription fields from the browser.
- `create_available_plan(owner, plan_details)` — Create an approved plan owned by
  the verified account, record the owner as approver and ignore browser-supplied
  status or approval values.
- `update_owned_plan_before_first_join(owner, plan, plan_changes)` — Edit an
  owned pending, approved or rejected plan only before its first successful join;
  after that refuse every edit except the separately mapped cancellation workflow.
  Keep approved plans available, activate a saved legacy rejected plan and refuse
  every cancelled plan edit.
- `join_approved_plan_and_lock_meeting_details(user, plan)` — Lock the plan row
  with `select_for_update()`, recount joined participants, recheck every joining
  rule, then create or reactivate participation and set the first-join lock in one
  transaction. On rejoin, replace `joined_at` with the latest join time and clear
  `left_at`.
- `leave_plan_and_keep_participation_history(user, plan)` — Mark current
  participation as left with a departure time, preserving the row and the plan's
  first-join read-only state.
- `cancel_owned_plan_and_hide_it_from_discovery(owner, plan)` — Cancel and remove
  an owned plan from discovery and future joins, clear its current approval
  fields, and preserve the plan and every participation row.
- `find_or_start_direct_conversation(user, other_user)` — Store the lower account
  ID first and return the pair's single conversation only after rechecking active,
  verified and mutual-block rules.
- `send_direct_message(sender, conversation, message_text)` — Recheck
  conversation membership and mutual-block state, then store one bounded plain-
  text message and update the conversation time without marking the text safe.
- `block_user_from_discovery_and_messages(blocker, blocked_user)` — Create the
  directional block once so both accounts immediately disappear from each other's
  discovery and can no longer open or send direct messages.
- `submit_private_report_about_user(reporter, reported_user, report_details, *, reported_plan=None, reported_conversation=None, reported_message=None)` — Create
  one private report about a different account with at most one reference. Verify
  both accounts are connected to a referenced plan as owner or participant, a
  conversation includes both accounts, and a message belonged to that conversation
  and was visible to the reporter; never notify the reported user.
- `start_stripe_subscription_checkout(user, success_url, cancel_url)` — Create
  one Stripe-hosted subscription Checkout session for the configured premium
  GBP 499 yearly price, set the immutable local user ID in
  `client_reference_id` and subscription metadata, and apply exactly 30 trial
  days with payment-method collection only if required and missing-payment-method
  invoice creation only when the account has no recorded Stripe history. Omit
  the trial for any later eligible Checkout, refuse a duplicate active or
  trialing subscription, accept only success and cancellation URLs already
  constructed by the view from the named local account route, and return its URL
  without granting premium access locally.
- `open_stripe_customer_portal(user, return_url)` — Create a hosted portal session
  for the account's known Stripe customer and return its URL; refuse safely when
  the account has no recorded Stripe customer ID. Accept only the return URL
  already constructed by the view from the named local account route.
- `update_premium_access_from_verified_stripe_event(stripe_event)` — Ignore
  duplicates and prevent older or ambiguous equal-time events from restoring
  access; never select an account by email. In one short transaction, lock or
  create the receipt, confirm Stripe IDs are not linked to another account, update
  identifiers only for checkout completion without advancing the subscription-
  state cursor, grant trial access only from an eligible trialing subscription
  update, grant a paid annual period only from a paid invoice for the linked
  configured price and active subscription, allow an equal-time deletion to
  revoke access, refuse an equal-time non-deletion from overwriting accepted
  state, and permit a delayed paid invoice to extend only a still-active,
  non-revoked subscription to its later paid service-period end, then mark a
  safely handled receipt processed. Store no card data and make no Stripe network
  call in the transaction.

Services receive validated values, enforce policy again and change state. They do
not render templates or trust IDs supplied by a browser.

### `kindlelise/selectors.py`

- `get_profiles_for_discovery_grid(viewer, selected_filters)` — Return the
  verified profiles in the viewer's selected allowed broad areas that match the permitted
  interest filters and, when `Free now` is requested, have an `available_from`
  time no later than now. Exclude either-direction blocks before returning any
  row.
- `get_profile_page_if_viewer_is_allowed(viewer, profile_id)` — Return one
  profile only when `can_view_profile_page()` allows it; otherwise return no
  result without revealing whether the profile exists or why it was hidden.
- `get_profile_image_if_viewer_is_allowed(viewer, profile_id)` — Return an image-
  bearing profile to its active owner or to a viewer permitted by
  `can_view_profile_page()`; otherwise use the same no-result outcome for missing
  files, missing profiles and denied access.
- `get_report_target_profile_if_reporter_is_allowed(reporter, profile_id)` —
  Return one target profile only when `can_report_another_user()` allows the
  authenticated reporter to report that different account. Do not apply
  discovery or messaging visibility, because an existing block must not suppress
  reporting; return no result for a missing or refused target.
- `get_plans_for_plan_list(user)` — Return approved future plans plus the signed-in
  user's own pending, rejected or cancelled plans, never including another
  owner's unapproved plan.
- `get_plan_page_if_viewer_is_allowed(viewer, plan_id)` — Return one allowed plan
  with its current participation count and the viewer's participation state, or
  no result when the plan is not visible to that viewer.
- `get_signed_in_user_account_summary(user)` — Return the account's own profile,
  plans and subscription summary for its private account page without returning
  private reports or Stripe webhook payloads.
- `get_unblocked_conversations_for_inbox(user)` — Return permitted direct
  conversations containing the account, ordered by recent activity after removing
  every conversation whose other account is blocked in either direction.
- `get_messages_if_user_can_open_conversation(user, conversation_id)` — Return
  the conversation and chronological messages only when the account is a member
  and neither member has blocked the other; otherwise reveal no messages.

Selectors only read. They do not change database records, repair state or call
Stripe or Ollama.

### `kindlelise/views.py`

- `home_page(request)` — Redirect an authenticated verified account to discovery,
  an authenticated unverified account to its private account page and an
  unauthenticated visitor to sign-in without changing product data.
- `sign_up_page(request)` — Validate `AccountSignUpForm`, then call
  `create_account_and_profile()` once; on success redirect to the named sign-in
  route without starting an authenticated session, and redisplay field errors
  without creating a partial account.
- `sign_in_page(request)` — Authenticate with Django, rotate the session safely
  and accept only a local safe redirect destination.
- `sign_out_user(request)` — End the current Django session only through a valid
  CSRF-protected POST request.
- `account_page(request)` — Call `get_signed_in_user_account_summary()` and show
  the signed-in user's private account page without accepting another account ID.
- `edit_profile_page(request)` — Validate `ProfileDetailsForm`, then call
  `update_signed_in_user_profile()` for the signed-in owner; never bind staff-only
  verification or Stripe fields.
- `discovery_page(request)` — Validate `DiscoveryFiltersForm`, call
  `get_profiles_for_discovery_grid()` and render only the profiles returned by the
  selector. The available-now choice is an ordinary optional filter and never a
  separate presence record.
- `profile_page(request, profile_id)` — Call
  `get_profile_page_if_viewer_is_allowed()` and render message, block and report
  actions only for the returned profile; use the same not-found response for every
  denied or missing profile.
- `profile_image_file(request, profile_id)` — Stream the stored profile image only
  after `get_profile_image_if_viewer_is_allowed()` returns it, with one generic
  not-found response for every missing or denied case.
- `plan_list_page(request)` — Call `get_plans_for_plan_list()` and show approved
  future plans plus the signed-in account's own plan states without exposing other
  owners' pending plans.
- `create_plan_page(request)` — Validate `PlanDetailsForm`, verify any signed
  fetched-thumbnail token, then call `create_available_plan()`.
- `plan_detail_page(request, plan_id)` — Call
  `get_plan_page_if_viewer_is_allowed()` and show only its returned plan and
  server-authorised actions.
- `edit_plan_page(request, plan_id)` — Validate `PlanDetailsForm`, then call
  `update_owned_plan_before_first_join()`; redisplay a clear error when the caller
  is not the owner or the first join has made the entire plan read-only.
- `join_plan(request, plan_id)` — Call
  `join_approved_plan_and_lock_meeting_details()` only through CSRF-protected POST
  and show a safe error when any joining condition changes.
- `leave_plan(request, plan_id)` — Call
  `leave_plan_and_keep_participation_history()` only through CSRF-protected POST,
  without deleting the participation record.
- `cancel_plan(request, plan_id)` — Call
  `cancel_owned_plan_and_hide_it_from_discovery()` only for the owner through
  CSRF-protected POST.
- `inbox_page(request)` — Call `get_unblocked_conversations_for_inbox()` and
  render only its returned conversations; never display blocked conversation
  previews or message text from a hidden conversation.
- `conversation_page(request, conversation_id)` — Call
  `get_messages_if_user_can_open_conversation()` and escape every returned message
  when rendering it.
- `start_direct_conversation(request, profile_id)` — Call
  `find_or_start_direct_conversation()` through CSRF-protected POST and redirect to
  the one conversation returned for the pair.
- `send_conversation_message(request, conversation_id)` — Validate
  `MessageDraftForm`, then call `send_direct_message()` through CSRF-protected POST;
  never trust a sender ID supplied by the browser.
- `request_conversation_message_edit_suggestion(request, conversation_id)` —
  Call `get_messages_if_user_can_open_conversation()` to confirm membership,
  active verification and no mutual block, validate `MessageEditRequestForm`, then
  call `get_edited_message_draft_suggestion()`. Pass no returned conversation
  history to Ollama and preserve the original draft on failure.
- `block_profile_from_discovery_and_messages(request, profile_id)` — Call
  `block_user_from_discovery_and_messages()` through POST and leave the interaction
  page without notifying the blocked account.
- `report_user_page(request, profile_id)` — Show and submit a private report form
  with `PrivateReportForm`. Resolve the route's `profile_id` through
  `get_report_target_profile_if_reporter_is_allowed()` and use the same generic
  not-found response for a missing or refused target. Treat an optional context
  type and ID as untrusted, retrieve a plan, conversation or message through the
  existing reporter-scoped selector for that context, then call
  `submit_private_report_about_user()` with at most one validated reference;
  never reveal the report to the reported account.
- `start_premium_subscription_checkout(request)` — Call
  `start_stripe_subscription_checkout()` through POST with success and cancellation
  URLs built server-side from the named account route, then redirect only to the
  Stripe-hosted URL returned by the service; do not grant access here or accept a
  browser-supplied destination.
- `open_premium_subscription_portal(request)` — Call
  `open_stripe_customer_portal()` through POST with a return URL built server-side
  from the named account route, then redirect only to its returned Stripe-hosted
  URL; never accept a browser-supplied destination.
- `receive_and_verify_stripe_webhook(request)` — Verify the raw-body signature,
  accept only supported events, then call
  `update_premium_access_from_verified_stripe_event()` without logging the raw
  payload or treating a browser session as authentication. Return `400` for an
  invalid signature or malformed signed JSON; return `200` for a valid unsupported,
  duplicate, stale, safely refused equal-time or successfully applied event; and
  return `500` only when supported processing rolls back and Stripe should retry.

Views stay thin: authenticate, parse through a form, call one owner and translate
the result into an HTTP response.

### `kindlelise/urls.py`

Each named route maps to exactly one view:

| Route name | View function |
| --- | --- |
| `home` | `home_page` |
| `sign_up` | `sign_up_page` |
| `sign_in` | `sign_in_page` |
| `sign_out` | `sign_out_user` |
| `account` | `account_page` |
| `profile_edit` | `edit_profile_page` |
| `discover` | `discovery_page` |
| `profile_detail` | `profile_page` |
| `profile_image` | `profile_image_file` |
| `plan_list` | `plan_list_page` |
| `plan_create` | `create_plan_page` |
| `plan_metadata_fetch` | `request_plan_metadata` |
| `plan_thumbnail` | `plan_thumbnail_file` |
| `plan_detail` | `plan_detail_page` |
| `plan_edit` | `edit_plan_page` |
| `plan_join` | `join_plan` |
| `plan_leave` | `leave_plan` |
| `plan_cancel` | `cancel_plan` |
| `inbox` | `inbox_page` |
| `conversation_detail` | `conversation_page` |
| `direct_conversation_start` | `start_direct_conversation` |
| `conversation_message_send` | `send_conversation_message` |
| `conversation_message_edit_suggestion` | `request_conversation_message_edit_suggestion` |
| `profile_block_messages_and_discovery` | `block_profile_from_discovery_and_messages` |
| `report_create` | `report_user_page` |
| `premium_subscription_checkout` | `start_premium_subscription_checkout` |
| `premium_subscription_portal` | `open_premium_subscription_portal` |
| `stripe_webhook` | `receive_and_verify_stripe_webhook` |

State-changing browser routes accept POST only. The Stripe webhook is CSRF-exempt
only because its Stripe signature is verified against the exact raw request body.
The AI route path is
`/conversations/<conversation_id>/message-edit-suggestion/`; it is not a general
writing endpoint.

### `kindlelise/ai_message_editor.py`

- `get_edited_message_draft_suggestion(draft, editing_goal)` — Send only the
  unsent draft within its character limit and one fixed editing goal to the
  configured Ollama Cloud API; return non-empty plain text no longer than the
  ordinary message limit, or `None` after invalid output or a short timeout,
  without storing, logging or automatically sending either draft.

The function calls the configured Ollama Cloud API URL with Python's standard
HTTP client or one small approved HTTP dependency, `OLLAMA_API_KEY` from server
configuration and one pinned model name. The document does not assume an official
SDK. The function must not log prompts, retry indefinitely, store suggestions or
send messages. The Free plan is an operational convenience, not a code guarantee.

## 9. Purpose contract for every file

### 01–05: root files

#### 01 — `.gitignore`

Ignore secrets, local databases, Python caches, test output and editor files. It
contains patterns only and no product behaviour.

#### 02 — `.env.example`

List safe placeholder names for Django, database, Stripe and Ollama Cloud
configuration. Never contain a working secret, customer ID or webhook payload.

#### 03 — `README.md`

Explain local setup, migrations, seeded interests, profile verification, test commands,
fixed broad-area configuration, email authentication, Stripe CLI use, Ollama
Cloud setup, supervised-test-account limits and the demonstration journey. It must
describe the implemented system, not promise deferred production features.

#### 04 — `manage.py`

Provide Django's standard management-command entry point only.

#### 05 — `pyproject.toml`

Pin the smallest required runtime and test dependencies: Django, Pillow for
bounded profile-image validation and metadata removal, database driver, Stripe
SDK, WhiteNoise for production static-file serving, one small general HTTP
dependency only if the standard library is not clear enough, Gunicorn and pytest
tooling. Do not add architectural frameworks.

### 06–10: project configuration

#### 06 — `config/__init__.py`

Mark the project package. No startup effects or environment loading.

#### 07 — `config/settings.py`

Own installed apps, middleware, templates, WhiteNoise static-file serving,
database configuration,
secure production flags, the fixed `KINDLELISE_AREAS` vocabulary and
`KINDLELISE_NEARBY_AREAS` mapping, Stripe settings, Ollama Cloud settings and
bounded provider timeouts. Area keys are stable stored values and labels are
display text. Secrets come from environment variables and private content is
excluded from logging.

#### 08 — `config/urls.py`

Mount Django Admin and authentication/application routes. Do not mount a direct
media-serving route; the application route authorises each profile-image read.

#### 09 — `config/asgi.py`

Expose the standard ASGI application. No WebSocket feature is implemented.

#### 10 — `config/wsgi.py`

Expose the standard WSGI application used by Gunicorn on Heroku, the current
assessment deployment target.

### 11–22: application files

#### 11 — `kindlelise/__init__.py`

Mark the package without provider setup or import side effects.

#### 12 — `kindlelise/apps.py`

Define `KindleliseConfig` with application metadata only. Do not register signal-
driven workflows.

#### 13 — `kindlelise/admin.py`

Own ordinary staff screens, the four mapped verification/plan actions and the
mapped related-profile verification checkbox on Django's User Permissions
section. Staff may review reports and subscription projections but must not edit
webhook receipt identity or expose report text to users.

#### 14 — `kindlelise/models.py`

Own the ten Kindlelise model classes, fields, relationships, constraints, indexes
and four read-only helpers mapped above. It must not contain HTTP, provider calls,
multi-step workflows or any deferred entity.

#### 15 — `kindlelise/forms.py`

Own the eight mapped form classes. Forms validate and normalise untrusted browser
input but do not save cross-model workflows or expose staff-controlled fields.

#### 16 — `kindlelise/policies.py`

Own the eight mapped permission functions. Every rule is server-side, deny-by-
default and independent of template visibility.

#### 17 — `kindlelise/services.py`

Own the fourteen mapped state-changing workflows. Use short transactions for
database work; no network call may run inside a database transaction.

#### 18 — `kindlelise/plan_metadata.py`

Own bounded public HTTPS retrieval, metadata extraction, image normalisation and
short-lived signed thumbnail tokens. Refuse private network targets and keep all
provider reads outside database transactions.

#### 19 — `kindlelise/selectors.py`

Own the nine mapped read operations. Apply each selector's mapped authorisation
before presentation. Discovery and messaging selectors enforce block exclusions;
the report-target selector deliberately does not, because blocking cannot suppress
private reporting.

#### 20 — `kindlelise/views.py`

Own the twenty-eight mapped HTTP adapters. Use login protection, POST for changes,
CSRF protection, generic not-found responses where disclosure matters and Django
messages for understandable feedback.

#### 21 — `kindlelise/urls.py`

Own the named route table only. Route names remain stable for templates and tests.

#### 22 — `kindlelise/ai_message_editor.py`

Own the single Ollama Cloud draft-editing function and no other AI feature.

#### 23 — `kindlelise/migrations/__init__.py`

Mark the migration package. Generated migrations reflect only approved model
changes and are reviewed before use. One reviewed initial data migration seeds
Coffee, Walking, Museums, Live music, Cinema, Food, Games and Study so a fresh
installation has the controlled vocabulary without manual setup.

### 24–30: templates

#### 24 — `templates/base.html`

Provide accessible page shell, navigation, flash messages, CSRF-aware POST forms
and static assets. Never infer authorisation from which controls are hidden.

#### 25 — `templates/discover.html`

Render the broad-area profile grid, multi-area and interest filters, optional
available-now filter, empty state and free/premium limit explanation. Never show
coordinates or hidden counts.

#### 26 — `templates/account.html`

Render own account/profile editing, verification state, availability, plans and
premium controls. The same file may render a safe read-only public profile mode
to avoid adding another template. It also renders the small sign-up and sign-in
modes so authentication does not require another template file. The premium
comparison is an account-page panel or mode, not a separate public route.

#### 27 — `templates/plan.html`

Render plan list, create/edit form and detail mode. Clearly show pending approval,
the owner-only edit action before the first join, the first-join read-only state,
join, eligible rejoin, leave, confirmed cancellation and report actions.

#### 28 — `templates/inbox.html`

Render the current user's permitted direct conversations and empty state.

#### 29 — `templates/conversation.html`

Render escaped messages, draft form, explicit AI editing controls, manual send,
block and report buttons. An eligible received message may expose a small
`Report this message` action that opens the existing report route with that
message as server-validated context. JavaScript enhancement must not be required
to send or report.

#### 30 — `templates/report.html`

Render a short private-report form, confidentiality explanation and confirmation.
Do not show other reports or imply that submission proves wrongdoing.

### 31–32: static assets

#### 31 — `static/app.css`

Provide one responsive, accessible visual system for grids, forms, messages,
states and buttons. Copy layout principles from references, not brand assets or
identical trade dress.

#### 32 — `static/app.js`

Progressively enhance AI draft suggestions, explicit plan metadata fetching,
colour themes and transient notifications. Preserve the original draft on error,
never send automatically and avoid storing private text in browser storage.

Approved browser functions:

- `readSavedColourTheme()` — Read only a recognised presentation theme from
  local storage and otherwise return the black default.
- `applyColourTheme(theme)` — Apply one recognised presentation theme without
  changing product data.

- `requestMessageDraftEditSuggestion(conversationId, draft, editingGoal)` — Send
  the conversation ID, current unsent draft and fixed goal to the conversation-
  bound Django view using CSRF.
- `showMessageDraftEditSuggestion(originalDraft, suggestedDraft)` — Show both
  choices and replace the text box only after the user accepts the suggestion.
- `requestPlanMetadata(fetchUrl, publicUrl, csrfToken)` — Request bounded public
  place and thumbnail suggestions only after the user selects `Fetch details`.

Each browser function receives a one-sentence comment explaining that it must
preserve the original draft and must never submit the message automatically.

### 33–34: tests

#### 33 — `tests/conftest.py`

Provide small factories/fixtures for users, verified profiles, interests, plans,
conversations, Stripe events and a fake Ollama response. Fixtures must not bypass
the public workflow being tested unless setup itself is not the subject.

Approved test setup helpers:

- `create_test_user()` — Create an active Django user with supplied safe defaults.
- `create_verified_test_profile()` — Create a profile whose staff verification
  fields are internally consistent.
- `create_test_interest()` — Create one controlled interest.
- `create_test_plan()` — Create a plan in the explicitly requested state.
- `create_test_conversation()` — Create one correctly ordered account pair.
- `build_stripe_test_event()` — Build one supported or deliberately unsupported
  event without containing real Stripe data.
- `replace_ollama_request_with_fake()` — Prevent a network call and return the
  exact success, timeout or failure requested by the test.

#### 34 — `tests/test_vertical_slice.py`

Contain approximately 30–40 strong behavioural tests, grouped by journey:

Test functions use `test_<condition>_<expected_outcome>`, for example
`test_unverified_profile_is_absent_from_discovery_grid`. The name must state the
starting condition and observable outcome; avoid numbered or vague names such as
`test_user`, `test_plan_2` or `test_it_works`.

```text
Accounts and discovery
- registration creates an unverified profile
- successful registration redirects to sign-in without authenticating the new
  account
- staff cannot verify a profile until its display name and configured broad area
  are complete
- the User Permissions verification checkbox is shown only with both User and
  Profile change permission, applies the same completeness rule, records the
  reviewer/time and can withdraw verification consistently
- sign-in and sign-out use Django authentication safely
- registration and sign-in use one canonical email address through Django
  authentication, while Stripe ownership continues to use immutable local IDs
- unverified or inactive users cannot access discovery, plans or messages
- the home page sends verified accounts to discovery, unverified accounts to their
  account page and unauthenticated visitors to sign-in
- discovery uses broad areas and excludes mutual blocks
- profile and filter forms accept configured stable area keys and reject arbitrary
  area text
- the reviewed initial data migration creates the eight fixed interests once
- availability is optional during profile completion; the form-only `Free now`
  switch and four fixed start choices calculate one `available_from` value from
  the current local date/time without storing a duplicate boolean
- the optional `Free now` filter returns only profiles whose `available_from`
  exists and has arrived
- free and premium interest/area limits differ without weakening safety

Plans
- eligible creation produces an immediately available plan
- fetched metadata is bounded, explicit, editable and never treated as safety evidence
- rejected unlocked legacy plans may be edited and saving activates them
- cancelled plans cannot be edited, approved or reactivated
- unapproved, past, full or cancelled plans cannot be joined
- capacity counts participant places only and does not include the owner
- two simultaneous joins cannot exceed capacity because the plan row is locked
- the first join makes the entire plan read-only except cancellation
- editing an unlocked available plan keeps it available
- participation is unique; leave preserves its row
- a valid rejoin updates the existing row, latest `joined_at` and null `left_at`
- owner cancellation removes a plan from discovery

Messaging and reporting
- storing the lower account ID first produces one conversation per account pair
- only members can read a conversation
- active, verified and mutually unblocked users can send bounded plain text that
  is escaped only when rendered
- a block prevents both reading and sending
- the report button submits a private report with at most one validated plan,
  conversation or message reference
- the report-target selector still resolves a different account after either
  direction blocks discovery or messaging, without exposing it through those
  interaction selectors
- both accounts must be connected to a referenced plan as owner or participant
- unrelated plan, conversation and message references are rejected
- a referenced message must belong to the two-account conversation and have been
  visible to the reporter
- reported users and unrelated users cannot see reports

Profile images
- the image field appears before display name and remains optional
- non-image, unsupported, oversized and over-dimension uploads are rejected
- accepted images have embedded metadata removed before storage
- only the active owner or a viewer currently allowed to open that profile can
  read the image; anonymous, blocked, unverified and missing targets share safe
  refusal behaviour
- replacing an image removes the superseded stored file after commit

Database constraints
- verified and unverified profiles require the matching reviewer/time nullability
- approved and non-approved plans require the matching approval-field nullability
- joined and left participation require the matching `left_at` nullability
- reports permit zero or one optional context reference, never more

Stripe
- invalid signatures are rejected before processing
- unsupported signed events create no receipt and do not change access
- duplicate event IDs are harmless
- Checkout uses the configured GBP 499 yearly price; a first eligible Checkout
  applies exactly 30 trial days, does not require upfront payment details and
  creates the annual invoice when the trial ends without a payment method
- the same local account never receives a second trial, and an active or trialing
  subscription cannot be duplicated
- checkout stores customer/subscription IDs but never grants premium
- checkout and subscription metadata map to immutable local user ID, never email
- Stripe IDs already linked to another account are rejected
- a trialing update grants Premium only until its future trial end
- an active subscription update without a paid invoice never grants or extends a
  paid annual period
- a verified paid invoice for the linked configured price and active subscription
  grants Premium only until its future annual service-period end
- an unpaid, past-due, unpaid-status, expired or missing `access_until` state
  denies Premium
- deletion sets local status to cancelled, clears `access_until`, retains Stripe
  identifiers and updates `latest_provider_event_at`
- an older event cannot overwrite newer accepted state
- a delayed paid invoice may extend a still-active, non-revoked subscription to
  its later service-period end but cannot rewind status or revive cancellation
- checkout completion does not advance the subscription-state ordering cursor;
  equal-time deletion may revoke access and equal-time non-deletion cannot
  overwrite an already accepted subscription state
- webhook responses are `400` for invalid signature/malformed signed JSON, `200`
  for safely handled or unsupported events and `500` for rolled-back supported
  processing that Stripe should retry
- failed supported-event processing commits neither a receipt nor a subscription
  update

Ollama Cloud
- only the unsent draft and fixed goal are sent
- a non-member, unverified account or either-direction block prevents the AI call
- unsupported goals are rejected before a provider call
- empty or over-message-limit output is rejected
- an accepted suggestion is validated again before manual sending
- timeout or provider failure preserves the original draft
- secrets and draft text are absent from logs

Journey
- verified user discovers a profile, creates an approved plan, joins,
  messages, blocks and reports using the normal public interfaces
```

When PostgreSQL is the assessment database, the simultaneous-join test uses a
Django `TransactionTestCase` and separate database connections so it genuinely
proves the `select_for_update()` capacity boundary rather than simulating two
sequential requests.

Removed feature tests must disappear with the removed feature; no placeholder
test should assert a production-scale design that is not implemented.

### Supporting governance documents outside the implementation-file count

#### `docs/VERTICAL_SLICE.md`

This authoritative boundary: scope, ownership, public function map, constraints,
tests and change process.

#### `doc_old/WIREFRAMES.md` (archived reference)

Map the reference screenshots into original Kindlelise pages and states. It may
describe navigation and visible controls but cannot create backend requirements
outside this document.

#### `docs/DECISIONS.md`

Record approved decisions with date, reason, alternatives and consequences.
Record rejected expansion requests too, so removed complexity does not return by
accident.

#### `docs/IMPLEMENTATION_PLAN.md`

Define the approved build sequence, phase dependencies, exit gates, runtime
verification and assessment-evidence requirements. It cannot change scope or
claim completion without the evidence required by the vertical slice.

#### `docs/IMPLEMENTATION_PROGRESS.md`

Record only the mutable State and Evidence values for the phases defined by the
implementation plan. It is a supporting governance document outside the
implementation-file count. It cannot add work, redefine a phase, weaken an exit
gate or claim completion without the plan's required evidence.

#### `docs/MASTER_INSTRUCTION_PROMPT.md`

Provide one reusable pass-start instruction derived from this vertical slice so
architecture, data-model, decision, implementation, test, interface and runtime
passes apply the same authority and guardrails. It is a supporting governance
document outside the implementation-file count, not a second specification. It
cannot approve a boundary change, and this vertical slice wins if the prompt is
stale, incomplete or inconsistent.

## 10. Main route flow

```text
GET/POST sign-up → unverified profile → staff verification
GET discover → broad-area profiles → GET profile
POST conversation/start → GET conversation → POST message/send
GET/POST plan/create → available plan → GET plan
POST plan/join → make entire plan read-only → POST plan/leave or owner cancel
POST profile/block
GET/POST report/create
POST subscription/checkout → Stripe hosted page
POST subscription/portal → Stripe hosted portal
POST stripe/webhook → verified local premium projection
POST conversation/<id>/message-edit-suggestion → authorisation → Ollama suggestion
→ user chooses → ordinary message validation → manual send
```

## 11. Fastest build order

1. Django setup, authentication and profile editing.
2. Staff verification and seeded interests.
3. Broad-area discovery and block exclusion.
4. Plans, manual approval, join locking, leave and cancel.
5. Direct conversation and refreshed plain-text messages.
6. Block and private report flows, including visible report buttons.
7. Stripe Checkout, webhook projection and customer portal.
8. Ollama Cloud draft editing.
9. Behavioural tests, accessibility and demonstration polish.

Each stage must work before the next integration is added.

## 12. Future production work

If Kindlelise progresses beyond assessment, future design may revisit:

- Privacy-preserving proximity calculations instead of broad named areas.
- Versioned URL evidence, safe server retrieval and formal anchor decisions.
- Immutable accepted meeting artifacts and multi-region capacity coordination.
- Threshold-activated circles and separately isolated safety corroboration.
- Moderation findings, sanctions, appeals, retention and subject-access processes.
- Stripe event reconciliation, monitoring and operational recovery procedures.
- AI provider governance, consent records and additional privacy review.

Future work is not partially scaffolded in the student MVP.

## 13. Boundary-change procedure

Before adding a file, model, route, dependency, workflow or feature:

1. State the user-visible requirement that cannot be met now.
2. Identify the current owner and explain why it cannot own the behaviour safely.
3. Show the smallest attempted design within the current boundary.
4. Describe privacy, security, test and assessment consequences.
5. Obtain explicit approval.
6. Update this document and `docs/DECISIONS.md` before implementation.

Without all six steps, the 36 implementation-file boundary and function map remain
authoritative.

A small public function inside an existing approved responsibility does not need a
formal architecture decision. State its concrete need, keep it in the current
owner, add its name/comment and behavioural test to this document in the same
change, and confirm that it introduces no new route, workflow or dependency.
