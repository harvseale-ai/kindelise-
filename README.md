# Kindlelise

Kindlelise is a focused, server-rendered Django application for meeting
people around shared interests and arranging activities at established public
places. It combines staff-gated profiles, broad-area discovery, public plans,
direct messaging, private safety controls, Stripe Premium and an optional
Ollama-assisted draft editor in one deliberately small application.

> **Assessment boundary:** Kindlelise is designed for supervised test accounts.
> Staff verification controls access to product features; it is not proof of
> identity, age, character or safety. The MVP is not ready for unrestricted
> public use.

## Contents

- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Current Status And Deployment](#current-status-and-deployment)
- [Problem Statement](#problem-statement)
- [User Stories](#user-stories)
- [Current Solution](#current-solution)
- [Plain-Language Terms](#plain-language-terms)
- [Product Pages](#product-pages)
- [Architecture](#architecture)
- [Key Technical Decisions](#key-technical-decisions)
- [Data Structure And Flow](#data-structure-and-flow)
- [Key Features](#key-features)
- [Application Runtime And Routes](#application-runtime-and-routes)
- [Run Locally](#run-locally)
- [Environment Variables](#environment-variables)
- [Staff And Demonstration Setup](#staff-and-demonstration-setup)
- [Stripe Test-Mode Setup](#stripe-test-mode-setup)
- [Ollama Setup](#ollama-setup)
- [Deployment Guidance](#deployment-guidance)
- [Security And Privacy](#security-and-privacy)
- [Known Limitations](#known-limitations)
- [Verification And Test Coverage](#verification-and-test-coverage)
- [Assessment Fit](#assessment-fit)
- [AI Assistance](#ai-assistance)
- [Documentation Map](#documentation-map)
- [Submission Scope](#submission-scope)

## Prerequisites

Install the following before running the project:

- Python 3.12. The package explicitly supports `>=3.12,<3.13`.
- PostgreSQL. Kindlelise intentionally has no SQLite fallback.
- Git for cloning and version control.
- A modern browser for the responsive interface.
- Stripe CLI only for a real local test-mode webhook walkthrough.
- An Ollama API key only for the live Cloud-backed draft-editing feature.

Node.js, npm, a JavaScript framework and a local AI model are not required to
run the Django application.

## Quick Start

From the project root:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[test]'
cp .env.example .env
```

Create a PostgreSQL database and account that match the `POSTGRES_*` values in
`.env`. Replace every `replace_me` value, then load the environment and start
the application:

```bash
set -a
source .env
set +a

python manage.py migrate
python manage.py check
python manage.py runserver
```

Open [http://127.0.0.1:8000/](http://127.0.0.1:8000/). The first migration
sequence creates the schema and seeds the controlled interest list.

## Current Status And Deployment

The complete approved user journey runs locally against PostgreSQL:

```text
register or sign in
    -> complete a profile
    -> receive staff verification
    -> discover eligible profiles
    -> create, join or leave a public-place plan
    -> exchange direct messages
    -> block or privately report another account
    -> optionally manage Premium and edit an unsent draft
```

Repository: [github.com/harvseale-ai/kindelise-](https://github.com/harvseale-ai/kindelise-)

No public deployment URL or deployment process file is committed at the time of
this README update. The code includes Gunicorn, WhiteNoise, PostgreSQL
`DATABASE_URL` support and production security settings, but a deployed
assessment instance must still record its URL, process definition, managed
database, durable media choice and completed runtime checklist. This README does
not present a local server as a live deployment.

## Problem Statement

Meeting new people through an online service creates a difficult balance. Users
need enough information to find shared interests and organise an activity, but
an MVP should not collect precise location history, expose private participant
lists or pretend that automated checks prove identity or safety.

Kindlelise addresses that problem with a deliberately bounded interaction:

1. People create a small profile using broad named areas and controlled
   interests rather than coordinates.
2. Staff approve access only after the minimum profile details are complete.
3. Verified users discover one another and arrange activities at established
   public places.
4. Plans show public-place evidence, time and capacity without revealing a
   private attendee directory.
5. Direct messaging, blocking and private reporting provide a small interaction
   and safety loop.
6. Stripe and Ollama are narrow external integrations; neither service gains
   control over unrelated account, safety or messaging decisions.

Success means the supervised journey works, ownership is enforced on the server,
private data remains bounded and every important state change can be explained
and tested. It does not mean the service guarantees a venue, person or event is
safe.

## User Stories

| # | User story | Acceptance focus |
| ---: | --- | --- |
| 1 | As a new user, I want to register with my email and password so that I can create one account. | Canonical lowercase email, Django password validation and an initially unverified profile. |
| 2 | As a user, I want to edit my profile so that others can understand my interests and general availability. | Owner-only display name, title statement, biography, broad areas, interests, availability and protected image. |
| 3 | As staff, I want to verify only complete profiles so that social features have a clear access gate. | Permission-checked Admin actions, reviewer and timestamp, with safe withdrawal. |
| 4 | As a verified user, I want to filter profiles so that I can find people with compatible areas, interests and availability. | Broad-area, controlled-interest and Free now filters with block exclusion and Free/Premium limits. |
| 5 | As a verified user, I want to create a public-place plan so that others can decide whether to join. | Future time, positive capacity, HTTPS public evidence and optional explicitly fetched metadata. |
| 6 | As a participant, I want to join, leave and rejoin safely so that capacity and history remain correct. | Atomic capacity check, one participation row and a permanent first-join edit lock. |
| 7 | As a verified user, I want one direct conversation with another eligible user so that we can coordinate privately. | One unordered account pair, plain-text messages, current membership and mutual block checks. |
| 8 | As a user, I want to block or privately report another account so that I can close interaction and give staff relevant context. | Immediate mutual exclusion, private reports and at most one trusted plan/conversation/message reference. |
| 9 | As a user, I want optional Premium access so that I can use wider discovery filters. | Stripe-hosted annual payment and portal, webhook-authoritative bounded access, no local card form. |
| 10 | As a user, I want help editing an unsent message so that I can correct grammar or improve clarity without sending automatically. | Only draft plus fixed goal sent, original and suggestion compared, explicit acceptance and manual Send. |

## Current Solution

Kindlelise is one Django project with one application and a PostgreSQL database.
Django renders the HTML, validates forms, enforces authentication and CSRF,
applies policy checks, coordinates state changes through services and stores the
durable records through its ORM.

The browser receives semantic HTML and local CSS. A small local JavaScript file
handles colour themes, filter-panel interaction, plan metadata requests, the
Ollama suggestion comparison, connectivity feedback and five-second notification
dismissal. JavaScript never owns authentication, permissions, subscriptions or
message sending.

External services are limited to:

- Stripe Checkout and Customer Portal for the single £4.99 yearly product.
- Signed Stripe webhooks for the local Premium projection.
- Ollama for one explicit grammar or clarity edit of an unsent draft.
- An explicitly requested public HTTPS page for bounded plan place/thumbnail
  metadata.

## Plain-Language Terms

- **Broad area:** a configured label such as Central or North. It is not a
  coordinate, exact address or distance.
- **Staff verification:** a current permission to use discovery, plans and
  messaging after minimum profile review. It is not identity or age proof.
- **Available plan:** an approved future plan that may still accept participants.
- **First-join lock:** once anybody successfully joins, the owner can no longer
  edit the plan details, although the plan can still be cancelled.
- **Participation:** the retained joined/left state linking one account to one
  plan. Leaving does not delete its history.
- **Direct conversation:** the one private plain-text conversation permitted for
  an unordered pair of eligible accounts.
- **Block:** one user's instruction that closes discovery and direct messaging
  between both accounts. It does not stop private reporting.
- **Private report:** the reporter's statement for authorised staff. Submission
  does not prove wrongdoing or automatically impose a sanction.
- **Premium projection:** Kindlelise's minimal local record of verified Stripe
  state. Browser return pages never grant access.
- **Ollama suggestion:** a temporary edited version of an unsent draft. It is not
  stored or sent unless the user chooses it and later presses Send.

## Product Pages

The final interface is intentionally consistent across desktop and mobile. It
uses a sticky top bar, fixed icon navigation, black/grey surfaces, colour themes,
semantic forms, protected profile/plan images and notification pop-outs.

| Page | Route | Purpose |
| --- | --- | --- |
| How to use Kindlelise | `/guide/` | One-page explanation of profiles, discovery, plans, messages, safety and Premium. |
| Create account / sign in | `/sign-up/`, `/sign-in/` | Email/password authentication and supervised-use explanation. |
| Private profile | `/profile/` | Owner profile, plans, availability, Premium action and sign out. |
| Edit profile | `/account/profile/edit/` | Profile image and owner-editable profile fields. |
| Discover | `/discover/` | Square profile cards and bounded discovery filters. |
| Public profile | `/profiles/<id>/` | Eligible profile details, plans, Send Message and collapsed safety actions. |
| Plans | `/plans/` | Filterable plan cards with state, capacity and optional thumbnail. |
| Create/edit plan | `/plans/create/`, `/plans/<id>/edit/` | Branded plan form and explicit Fetch details action. |
| Plan detail | `/plans/<id>/` | Place, time, owner, capacity, participation and owner controls. |
| Messages | `/messages/` | Current permitted direct conversations. |
| Conversation | `/conversations/<id>/` | Plain-text thread, composer, safety controls and optional Ollama draft editor. |
| Private report | `/profiles/<id>/report/` | Bounded report form with trusted optional context. |

Current screenshots should be captured from the final deployed assessment
revision, not copied from design wireframes or another project. No screenshot or
Lighthouse asset is claimed by this README because none is currently committed.

## Architecture

```text
Browser
   |
   | HTTPS form submissions and page requests
   v
Django views  -> translate HTTP, build server-owned identities and URLs
   |
   +-> Forms      -> validate untrusted browser input
   +-> Policies   -> answer access questions
   +-> Selectors  -> return privacy-minimised read models
   +-> Services   -> own atomic workflows and provider calls
   +-> Models     -> enforce durable PostgreSQL truth
   |
   +-> Stripe hosted pages and signed webhooks
   +-> Ollama generate API for explicit unsent-draft edits
   +-> bounded HTTPS metadata fetch after explicit user action
```

Responsibility remains separated even though the project is small:

```text
Templates/CSS/JS = presentation and optional browser enhancement
Views            = HTTP methods, sessions, redirects and response types
Forms            = user-controlled value validation
Policies         = permission decisions
Selectors        = scoped database reads
Services         = transactions and external-provider workflows
Models           = constraints, indexes and durable state
Admin            = staff-only verification and review controls
```

## Key Technical Decisions

| Decision | Choice | Reason |
| --- | --- | --- |
| Application shape | One server-rendered Django app | The assessed journey is forms, permissions and relational state; a separate API or SPA would duplicate work. |
| Accounts | Django `User`, with canonical email stored as username and email | Retains Django authentication and uniqueness without a custom user model/backend. |
| Database | PostgreSQL only | Array-backed profile areas, relational constraints, row locking and production parity are part of the design. |
| Location | Configured broad areas | Supports useful discovery without exact coordinates, geolocation or location history. |
| Verification | Manual current staff state | Keeps the access decision explicit without claiming automated identity proof. |
| Plans | Established public place and HTTPS evidence URL | Gives users reviewable public context while avoiding private-address or map-pin workflows. |
| Plan publishing | Eligible verified owners create immediately available plans | Matches the current lightweight product; legacy pending/rejected states remain safely handled. |
| Plan capacity | Transactional join with `select_for_update` | Prevents concurrent joins from exceeding capacity. |
| Messaging | Refreshed server-rendered plain text | Avoids sockets, media and read-state complexity while preserving the core coordination journey. |
| Safety | Immediate block plus separate private report | Blocking closes interaction; reporting remains available and does not become a public accusation. |
| Billing | Stripe-hosted Checkout/Portal and signed webhooks | Card data never enters Kindlelise, and browser redirects cannot grant Premium. |
| AI editing | Explicit bounded Ollama request | Only a current unsent draft and fixed editing goal leave the application; no history or automatic send. |
| Static files | WhiteNoise compressed manifest storage | Supports a small production deployment without a separate static service. |
| Images | Normalised protected application files | Removes embedded metadata and checks access, while documenting the need for durable production storage. |

The rationale and rejected alternatives are recorded in
[`docs/DECISIONS.md`](docs/DECISIONS.md).

## Data Structure And Flow

### Core Data Structures

Kindlelise defines ten application models plus Django's existing `User` model.

| Model | Important fields | Responsibility |
| --- | --- | --- |
| `Profile` | user, image, display name, title statement, biography, broad areas, interests, availability, verification | One public/product profile for one account. |
| `Interest` | unique name | Staff-seeded controlled discovery vocabulary. |
| `Plan` | owner, place, public URL, thumbnail, time, capacity, status, approval and lock fields | One future public-place activity. |
| `Participation` | plan, user, joined/left state and timestamps | Current and historical membership without attendee-directory exposure. |
| `Conversation` | ordered first/second user and activity time | The unique unordered account-pair relationship. |
| `Message` | conversation, sender, body and sent time | One bounded plain-text message. |
| `Block` | blocker and blocked user | One directional record treated as mutual exclusion by policy. |
| `Report` | reporter, target, category, description, optional context and status | One private, non-adjudicative staff report. |
| `PlatformSubscription` | user, Stripe IDs/status, access end and event ordering | Minimal webhook-owned Premium projection. |
| `StripeWebhookReceipt` | event ID/type, provider time and processed time | Idempotency and successful-processing record. |

Important database rules include one profile/subscription per user, positive plan
capacity, consistent verification and approval fields, one participation per
user/plan, one ordered conversation per pair, no self-block/report, at most one
report context and unique Stripe identifiers/events.

### Account And Discovery Flow

```text
AccountSignUpForm validates canonical email + Django password rules
    -> service creates User and empty unverified Profile atomically
    -> owner completes permitted profile fields
    -> authorised staff verifies a complete profile
    -> policy grants discovery/plans/messages access
    -> DiscoveryFiltersForm applies server-calculated area/interest limits
    -> selector excludes inactive, unverified and either-direction-blocked users
    -> template renders only the scoped profile cards
```

Free accounts can use their saved broad areas and up to two interest filters.
Premium accounts may include explicitly configured nearby areas and up to five
interest filters. Premium never bypasses verification or a block.

### Plan And Participation Flow

```text
verified owner submits future plan details
    -> PlanDetailsForm validates bounds and normal HTTPS URL
    -> optional Fetch details performs one bounded protected metadata request
    -> service creates an immediately available plan
    -> another verified user opens the privacy-minimised detail
    -> transactional join locks the plan row and rechecks capacity
    -> first successful join permanently locks owner edits
    -> leave/rejoin updates the same Participation row
    -> owner cancellation is terminal and preserves history
```

Metadata fetching resolves only public/global HTTPS destinations, limits response
sizes/types and redirects, normalises a thumbnail and stores no fetched page.
The suggested place remains editable and the public page remains the source the
user should check.

### Messaging, Blocking And Reporting Flow

```text
eligible profile -> POST start conversation
    -> service sorts account IDs and returns/creates one pair
    -> GET conversation selects messages only for a current permitted member
    -> MessageDraftForm validates one non-empty plain-text body
    -> service rechecks eligibility and stores message + activity atomically

POST block -> directional Block row -> both accounts disappear from discovery/messages
GET/POST report -> trusted target/context resolution -> private Report row for staff
```

The reported account is not notified and cannot see the report. Blocking never
removes the reporter's ability to submit a private report.

### Stripe Flow

```text
POST account/premium/checkout
    -> server builds account return URLs
    -> Stripe-hosted annual subscription Checkout
    -> browser return changes no access
    -> POST stripe/webhook verifies the exact body and signature
    -> service resolves immutable account/customer/subscription identity
    -> unique receipt + ordered subscription projection commit atomically
    -> eligible paid invoice grants access until its verified period end

POST account/premium/portal
    -> owning account's stored customer ID
    -> validated Stripe-hosted portal URL
```

### Ollama Draft-Editing Flow

```text
authorised conversation + unsent draft
    -> choose Fix grammar or Improve clarity
    -> CSRF-protected conversation-bound POST
    -> form accepts only draft + fixed goal
    -> Ollama receives model, fixed instruction and draft
    -> bounded suggestion appears beside the original
    -> Keep original or Use suggestion
    -> ordinary form validation and separate manual Send
```

“Fix grammar” preserves wording and order while correcting language mechanics.
“Improve clarity” may restructure and remove repetition without inventing facts.

## Key Features

- Canonical email/password registration and sign-in using Django authentication.
- One owner-editable profile with title statement, biography, multiple broad
  areas, controlled interests and optional availability.
- Protected JPEG/PNG/WebP profile images, limited to 5 MB and 4,096 pixels per
  side, re-encoded without embedded metadata.
- Staff verification and withdrawal through Django Admin.
- Discovery filters with Free and Premium area/interest limits.
- Public profile cards using protected profile imagery.
- Immediately available future plans with capacity and participation states.
- Explicit public-place metadata and thumbnail assistance.
- Protected plan thumbnails and detailed plan pages.
- Atomic join, leave, rejoin, cancellation and first-join locking.
- One direct plain-text conversation per eligible account pair.
- Ollama grammar/clarity suggestions that never send automatically.
- Immediate blocking and private contextual reporting.
- Stripe-hosted annual Premium Checkout and customer portal.
- Webhook idempotency, event ordering and bounded Premium access.
- Responsive black/grey interface with optional blue, pink and green themes.
- Accessible labels, focus styles, skip link, semantic status/error regions and
  reduced-motion support.
- Sticky navigation, offline feedback and five-second pop-out notifications.
- One-page in-product guide at `/guide/`.

## Application Runtime And Routes

### Main Source Map

| File | Responsibility |
| --- | --- |
| [`config/settings.py`](config/settings.py) | Environment configuration, PostgreSQL, security, areas, Stripe and Ollama settings. |
| [`kindlelise/models.py`](kindlelise/models.py) | Ten durable entities, constraints, indexes and small state helpers. |
| [`kindlelise/forms.py`](kindlelise/forms.py) | Authentication, profile, discovery, plan, message, AI and report input validation. |
| [`kindlelise/policies.py`](kindlelise/policies.py) | Verification, visibility, plan, messaging and report permission decisions. |
| [`kindlelise/selectors.py`](kindlelise/selectors.py) | Privacy-scoped profile, plan, inbox and conversation reads. |
| [`kindlelise/services.py`](kindlelise/services.py) | Atomic account, profile, plan, messaging, safety and Stripe workflows. |
| [`kindlelise/plan_metadata.py`](kindlelise/plan_metadata.py) | Bounded HTTPS metadata fetch, SSRF controls and thumbnail normalisation. |
| [`kindlelise/ai_message_editor.py`](kindlelise/ai_message_editor.py) | Bounded Ollama request and response validation. |
| [`kindlelise/views.py`](kindlelise/views.py) | HTTP methods, forms, sessions, redirects, provider endpoints and templates. |
| [`kindlelise/admin.py`](kindlelise/admin.py) | Staff verification, legacy plan review and read-only sensitive records. |
| [`templates/`](templates/) | Server-rendered semantic pages. |
| [`static/app.css`](static/app.css) | Responsive design system and route-specific presentation. |
| [`static/app.js`](static/app.js) | Optional themes, filters, notifications, metadata and AI suggestion interactions. |
| [`tests/test_vertical_slice.py`](tests/test_vertical_slice.py) | End-to-end domain, HTTP, provider-boundary, security and performance tests. |

### Route And Method Summary

| Area | Routes | Methods and rules |
| --- | --- | --- |
| Public/auth | `/`, `/guide/`, `/sign-up/`, `/sign-in/` | Public GET; signup/sign-in accept validated POST. |
| Sign out | `/sign-out/` | POST and CSRF only. |
| Own profile | `/profile/`, `/account/`, `/account/profile/edit/` | Authenticated GET; profile edit accepts owner-only POST and image upload. |
| Discovery | `/discover/`, `/profiles/<id>/`, `/profiles/<id>/image/` | Verified access and privacy-scoped GET. |
| Plans | `/plans/`, `/plans/create/`, `/plans/<id>/`, `/plans/<id>/edit/` | Verified GET/POST with owner and state checks. |
| Plan actions | `/plans/fetch-details/`, `/plans/<id>/join/`, `/leave/`, `/cancel/` | POST and CSRF only; service rechecks current state. |
| Plan image | `/plans/<id>/image/` | Protected GET using the same plan visibility boundary. |
| Messages | `/messages/`, `/conversations/<id>/` | Verified, unblocked, member-scoped GET. |
| Message actions | profile conversation start, message send, suggestion endpoint | POST and CSRF only; no browser-supplied sender. |
| Safety | profile block and report routes | Block is POST-only; report uses GET/POST and server-resolved target/context. |
| Premium | account checkout and portal | Authenticated POST, then validated Stripe-hosted redirect. |
| Stripe | `/stripe/webhook/` | POST-only raw-body signature verification; no browser session required. |
| Staff | `/admin/` | Django staff authentication and model permissions. |

## Run Locally

### 1. Install The Project

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test]'
```

### 2. Configure PostgreSQL

Create a database, role and password with PostgreSQL tools or a graphical client.
Use the same values in `.env`:

```text
POSTGRES_DB=kindlelise
POSTGRES_USER=kindlelise
POSTGRES_PASSWORD=<local-password>
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
```

`DATABASE_URL` takes precedence when it is non-empty. Do not set it to a SQLite
URL; settings reject every non-PostgreSQL scheme.

### 3. Configure The Environment

```bash
cp .env.example .env
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Put the generated value in `DJANGO_SECRET_KEY`. Keep `.env` local and ignored by
Git. Use test-mode Stripe credentials and a revocable Ollama key for assessment.

### 4. Migrate And Start

```bash
set -a
source .env
set +a

python manage.py migrate
python manage.py createsuperuser  # required only for staff/admin review
python manage.py runserver 127.0.0.1:8000
```

### 5. Run The Verification Suite

```bash
set -a
source .env
set +a

python manage.py check
python manage.py makemigrations --check --dry-run
pytest -q
python manage.py collectstatic --dry-run --noinput --verbosity 0
```

## Environment Variables

Copy [`.env.example`](.env.example) and populate `.env`. Never place real
credentials in `.env.example`, source code, screenshots, commits or logs.

| Variable | Required | Purpose |
| --- | --- | --- |
| `DJANGO_SECRET_KEY` | Yes | Signs sessions and security-sensitive Django values. Use a long unique value. |
| `DJANGO_DEBUG` | Yes | `true` locally; `false` in a deployed environment. Invalid booleans fail startup. |
| `DJANGO_ALLOWED_HOSTS` | Yes | Comma-separated hostnames Django may serve. |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | Deployment | Comma-separated full trusted origins such as `https://example.com`. |
| `DATABASE_URL` | Deployment/optional locally | PostgreSQL URL; takes precedence over individual PostgreSQL fields. |
| `POSTGRES_DB` | Local without `DATABASE_URL` | Local PostgreSQL database name. |
| `POSTGRES_USER` | Local without `DATABASE_URL` | Local PostgreSQL role. |
| `POSTGRES_PASSWORD` | Local without `DATABASE_URL` | Local PostgreSQL password. |
| `POSTGRES_HOST` | Local without `DATABASE_URL` | PostgreSQL host, normally `localhost`. |
| `POSTGRES_PORT` | Local without `DATABASE_URL` | PostgreSQL port, normally `5432`. |
| `STRIPE_SECRET_KEY` | Premium | Server-side Stripe test/live key. |
| `STRIPE_WEBHOOK_SECRET` | Premium | Verifies the exact webhook body and Stripe signature. |
| `STRIPE_PRICE_ID` | Premium | The one configured recurring GBP £4.99 yearly price. |
| `OLLAMA_API_URL` | AI editor | Full Generate endpoint; example uses `https://ollama.com/api/generate`. |
| `OLLAMA_API_KEY` | Remote AI editor | Bearer credential for the Ollama Cloud endpoint. |
| `OLLAMA_MODEL` | AI editor | One pinned model name; example uses `gpt-oss:20b`. |
| `OLLAMA_TIMEOUT_SECONDS` | AI editor | Positive whole-number request timeout; defaults to 10 seconds. |

When `DJANGO_DEBUG=false`, settings automatically enable secure cookies, HTTPS
redirect, HSTS, forwarded-protocol handling, `nosniff`, same-origin referrer
policy and frame denial.

## Staff And Demonstration Setup

1. Create a superuser with `python manage.py createsuperuser`.
2. Register at least two normal supervised accounts through `/sign-up/`.
3. Complete each profile's display name and one or more configured broad areas.
4. Open `/admin/auth/user/<id>/change/` and use **Profile verified** in the
   Permissions section, or select profiles in Admin and run the verification
   action.
5. Keep staff accounts separate from demonstration users where possible.
6. Use the second account to prove discovery, join capacity, messaging, block and
   report behavior rather than editing database rows manually.

The controlled interests seeded by migration are Coffee, Walking, Museums, Live
music, Cinema, Food, Games and Study.

## Stripe Test-Mode Setup

Kindlelise expects one recurring price configured as GBP £4.99 per year.

1. Create or select the Stripe test-mode Product and yearly Price.
2. Put the test secret key and Price ID in `.env`.
3. Start Django, then run the Stripe CLI in another terminal:

```bash
stripe login
stripe listen --forward-to 127.0.0.1:8000/stripe/webhook/
```

4. Copy the listener's `whsec_...` signing secret into
   `STRIPE_WEBHOOK_SECRET` and restart Django so the environment is reloaded.
5. Use **Explore** on `/profile/`; payment occurs on Stripe's hosted page.
6. Confirm that the browser return alone grants nothing and the signed supported
   events update `PlatformSubscription` and `StripeWebhookReceipt`.
7. Use the profile action again to open the hosted Customer Portal after a Stripe
   customer is linked.

Handled events are `checkout.session.completed`,
`customer.subscription.created`, `customer.subscription.updated`, `invoice.paid`
and `customer.subscription.deleted`. Unsupported events return success without
changing access. Never use production card data for assessment testing.

## Ollama Setup

The default example uses Ollama Cloud's Generate API:

```text
OLLAMA_API_URL=https://ollama.com/api/generate
OLLAMA_API_KEY=<revocable-api-key>
OLLAMA_MODEL=gpt-oss:20b
OLLAMA_TIMEOUT_SECONDS=10
```

Restart Django after changing `.env`. Open a permitted conversation, write an
unsent draft, expand **Edit this unsent draft**, then choose **Fix grammar** or
**Improve clarity**. The comparison panel shows the original and suggestion;
the text box changes only after **Use suggestion**, and the message is still not
sent until **Send** is pressed.

The adapter also permits unauthenticated HTTP only for loopback hosts
(`127.0.0.1`, `localhost` or `::1`) so a local Ollama installation can be used
during development. Every remote host requires HTTPS and an API key. The project
uses its pinned `certifi` CA bundle for provider certificate validation.

## Deployment Guidance

The repository includes Heroku-compatible `requirements.txt`, `.python-version`
and `Procfile` files. Heroku installs the pinned production dependencies with
pip, uses the latest supported Python 3.12 patch, runs migrations during the
release phase and starts Gunicorn as the web process. A live URL is not committed.

### Required Production Configuration

```text
DJANGO_SECRET_KEY=<unique-production-secret>
DJANGO_DEBUG=false
DJANGO_ALLOWED_HOSTS=<deployed-hostname>
DJANGO_CSRF_TRUSTED_ORIGINS=https://<deployed-hostname>
DATABASE_URL=<managed-postgresql-url>
STRIPE_SECRET_KEY=<matching-environment-key>
STRIPE_WEBHOOK_SECRET=<deployed-endpoint-secret>
STRIPE_PRICE_ID=<matching-environment-price>
OLLAMA_API_URL=https://ollama.com/api/generate
OLLAMA_API_KEY=<revocable-production-key>
OLLAMA_MODEL=<pinned-supported-model>
```

The `Procfile` web command is:

```bash
gunicorn config.wsgi --log-file - --access-logfile -
```

The `Procfile` release phase runs:

```bash
python manage.py migrate --noinput
```

Heroku runs `python manage.py collectstatic --noinput` during the Python build.
Run `python manage.py check --deploy` as a separate pre-deployment verification
gate with the production environment values configured.

WhiteNoise serves static assets. Uploaded profile and plan images currently use
the local filesystem; Heroku-style ephemeral storage is not durable. A real
deployment therefore needs an approved durable private media backend before
image retention can be promised. Add the media decision through the documented
boundary-change process rather than silently claiming durable uploads exist.

After deployment, record the URL and immutable revision, run a home-route smoke
request, verify Admin, repeat the supervised user journey, exercise test-mode
Stripe and Ollama, inspect logs for unexpected failures and document rollback.

## Security And Privacy

- Django authentication hashes passwords and session/CSRF middleware protects
  account actions.
- Mutation routes use POST and CSRF; views never trust browser-supplied owner,
  sender, verification, approval or subscription identity.
- Policies fail closed when an account is inactive, incomplete, unverified or
  blocked.
- Selectors return the same generic hidden response for missing and forbidden
  private objects where existence would leak information.
- Templates use Django escaping and messages are stored/rendered as plain text.
- Profile images are type/size/dimension checked and re-encoded without metadata.
- Plan metadata uses explicit user action, global-address checks, pinned HTTPS
  connections, bounded content and signed short-lived thumbnail tokens.
- Capacity, uniqueness and state consistency are enforced by PostgreSQL as well
  as application code.
- Stripe webhook signatures use the exact raw body; unique receipts and provider
  times prevent duplicate or older events from rewriting access.
- Stripe ownership comes from immutable local IDs and linked provider IDs, never
  email. Kindlelise stores no card or bank details.
- Ollama receives only the bounded unsent draft, fixed instruction and model. It
  receives no profile, recipient, report, plan or previous conversation content.
- Provider errors are quiet, suggestions are not persisted and neither provider
  secrets nor private text should enter application logs.
- `.env` is ignored by Git; `.env.example` contains placeholders only.

## Known Limitations

- The project is for supervised assessment accounts and has no age-verification
  or production identity-proof system.
- Staff verification is an access gate, not a personal or venue safety guarantee.
- Broad areas intentionally replace precise distance/location behavior.
- Plan metadata can become outdated and does not prove an external venue is safe
  or legitimate; users must check the linked public page.
- Uploaded media uses local filesystem storage and lacks production retention,
  moderation and durable object storage.
- Messaging refreshes through normal page requests; there are no WebSockets,
  read receipts, typing indicators, group chats, reactions or attachments.
- Reports are statements for staff review, not findings, sanctions, appeals or an
  emergency-response system.
- Premium is one annual product. There is no tier catalogue, usage billing or
  local payment/cancellation form.
- Provider-backed features need reachable Stripe/Ollama services and correctly
  scoped credentials. Provider failure preserves safe local state but cannot
  supply the external feature.
- There is no background worker, automated reconciliation service, production
  alerting or long-term metrics pipeline.
- A public deployment URL, process file, durable media backend, final signed-in
  accessibility audit and current screenshot set are not yet committed.
- The archived production-scale material under `_achive/` is reference history,
  not part of the running application.

## Verification And Test Coverage

### Reproduce The Current Gates

From the project root with the test PostgreSQL database available:

```bash
set -a
source .env
set +a

python manage.py check
python manage.py makemigrations --check --dry-run
pytest -q
python manage.py collectstatic --dry-run --noinput --verbosity 0
python -m pip check
```

Run the independent Python ecosystem quality gates with:

```bash
ruff check config kindlelise tests
bandit -q -r config kindlelise -x kindlelise/migrations
coverage erase
coverage run -m pytest -q
coverage report
pip-audit --local --skip-editable
```

Ruff checks stable Python syntax, import and undefined-name rules. Bandit scans
application code for common security mistakes; generated migrations are excluded.
Coverage.py measures statements and branches and enforces the 80% project minimum
configured in `pyproject.toml`. pip-audit compares installed dependencies with the
Python Packaging Advisory Database. The editable Kindlelise package itself is
reported as skipped because it is local source rather than a published package;
its installed third-party dependencies are still audited.

For the production settings audit without changing `.env`:

```bash
set -a
source .env
set +a

DJANGO_DEBUG=false \
DJANGO_ALLOWED_HOSTS=example.test \
DJANGO_CSRF_TRUSTED_ORIGINS=https://example.test \
python manage.py check --deploy
```

Latest verified local results on **8 August 2026**:

| Gate | Result |
| --- | --- |
| Django system check | Passed with 0 issues |
| Django production deployment check | Passed with 0 issues using temporary production host settings |
| Migration drift check | Passed; no model changes detected |
| PostgreSQL pytest suite under Coverage.py | **117 tests passed in 88.36 seconds** |
| Coverage.py 7.15.4 | **83%** combined branch-aware report; passed the 80% minimum |
| Ruff 0.16.2 | Passed with no remaining findings in the configured rule set |
| Bandit 1.9.4 | Passed with no unsuppressed findings |
| pip-audit 2.10.1 | Passed; no known vulnerabilities found in installed dependencies |
| Static collection dry run | Passed |
| Python dependency consistency | Passed; no broken requirements found |
| Git whitespace check | Passed |
| Live Ollama Cloud synthetic grammar request | Passed and returned a bounded suggestion |
| Conversation-bound suggestion endpoint | Passed with HTTP 200 and a non-empty suggestion |

Passing tests prove the behaviors covered by the suite on the recorded
environment. They do not replace a final deployed browser, Stripe test-mode,
accessibility, media-persistence or rollback walkthrough.

The first dependency audit identified advisories against the previous Django,
pytest and pip versions. The verified environment now uses Django 5.2.16,
pytest 9.0.3 and pip 26.2.1, and the repeat audit reports no known
vulnerabilities. Three narrow Bandit false positives are documented beside the
relevant lines: a URL opened only after scheme/host/credential validation, a
public signing namespace, and an empty non-authentication sentinel.

### Test Coverage By Domain

The single vertical-slice suite covers:

- schema migrations, seeded interests, exact model inventory, constraints,
  indexes and deletion behavior;
- canonical email registration, sign-in/out, redirects, CSRF and transactional
  account/profile creation;
- profile field ownership, multiple areas, availability calculations and image
  normalisation/protection;
- staff permissions, profile verification/withdrawal and legacy plan review;
- Free/Premium discovery limits, filters, block exclusion and privacy-minimised
  public profiles;
- plan list/detail visibility, immediate creation, bounded metadata fetching,
  protected thumbnails, owner edits, joins, capacity, first-join locking, leave,
  rejoin and terminal cancellation;
- one direct conversation per pair, chronological escaped messages, no inbox
  previews, current permission checks and transactional message activity;
- immediate idempotent blocking and private report target/context validation;
- Stripe Checkout/Portal request shape, immutable ownership, exact webhook
  verification, idempotency, ordering, paid/trial/cancelled states and rollback;
- Ollama payload minimisation, separate grammar/clarity instructions,
  authorization, CSRF, timeout/malformed-output handling and manual send;
- accessible navigation/error associations and constant discovery, plan-list and
  inbox query counts from five to fifty visible rows.

External provider calls are replaced with controlled fakes in the automated
suite. The separate live Ollama smoke check uses synthetic non-personal text.

## Assessment Fit

Kindlelise demonstrates the expected full-stack outcomes:

- Django project configuration, URL routing, views, forms and templates;
- authentication, sessions, permissions, ownership and staff administration;
- PostgreSQL models, migrations, relationships, constraints, indexes and
  transactional concurrency controls;
- CRUD-style profile/plan workflows and retained state transitions;
- responsive, accessible and progressively enhanced frontend code;
- secure environment-based configuration and production-mode settings;
- two narrow third-party integrations with tested failure boundaries;
- automated tests covering normal journeys, invalid input, privacy, security,
  concurrency, provider behavior and performance query shape;
- documented setup, architecture, deployment requirements, limitations and
  verification evidence.

The strongest assessment claim is not that the MVP is production-complete. It is
that the approved product journey is intentionally bounded, implemented in a
small readable codebase and supported by reproducible evidence.

## AI Assistance

AI tools were used as a development assistant for code review, test suggestions,
documentation structure, debugging external integrations, accessibility checks
and wording improvements. Changes were inspected in the repository and verified
with the commands recorded above rather than accepted only because an AI tool
suggested them.

Ollama is also a visible product feature, but its authority is deliberately
small: it may suggest a grammar or clarity edit for one unsent draft. It cannot
read prior messages, choose a recipient, send a message, verify a profile,
approve a plan, grant Premium or make a safety decision.

## Documentation Map

| Document | Role |
| --- | --- |
| [`README.md`](README.md) | Main setup, product, architecture, testing and assessment handoff. |
| [`docs/VERTICAL_SLICE.md`](docs/VERTICAL_SLICE.md) | Authoritative MVP behavior and implementation boundary. |
| [`docs/DECISIONS.md`](docs/DECISIONS.md) | Architecture decisions, alternatives and consequences. |

Completed build plans, progress evidence, superseded design material and README
templates are retained under [`_achive/doc_old/`](_achive/doc_old/) for history.
They are not implementation authorities for the running MVP.

## Submission Scope

This README is the main project handoff for the submitted repository. The
running submission is the root Django project, `kindlelise` application,
templates, static assets, migrations and tests listed above. Secrets, local
`.env`, local database contents, generated static output, uploaded media, design
wireframes and archived production-scale experiments are not product source.

Before final submission, add the actual deployed URL and revision, capture
current screenshots from that revision, complete the deployed Stripe/Ollama and
accessibility walkthroughs, confirm durable media handling, and update the
verification evidence without weakening this README's stated limitations.
