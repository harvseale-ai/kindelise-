# Kindelise Technical Decision Log

This document explains the main technical choices behind the finished Kindelise
application. The README describes what the application does. The code and tests
show the final working behaviour.

Each decision records the problem, the chosen approach and why that approach was
kept. Old build instructions and progress notes are not included here.

## ADR-001: Use one Django application

**Status:** Accepted

### Decision

Keep the product code inside one custom Django application named `kindlelise`.
Split large view and service files into small folders based on their purpose.

### Why

Profiles, discovery, plans, messages, reports, payments and notifications depend
on the same users and permission rules. Separate Django applications would add
more imports, settings and migrations without making this project clearer.

### Result

- `config/` owns the project settings and top-level URLs.
- `kindlelise/` owns the product models, forms and behaviour.
- `kindlelise/views/` translates web requests into page responses.
- `kindlelise/services/` owns changes that must be saved safely.
- `kindlelise/selectors/` groups page reads by accounts, discovery, plans, messages, and safety.
- `kindlelise/policies.py` answers permission questions.

## ADR-002: Use Django accounts with email sign-in

**Status:** Accepted

### Decision

Use Django's existing `User` model. Store the cleaned email address as both the
username and email value so people sign in with one clear identifier.

### Why

Django already provides password hashing, sessions, permissions and password
checks. A custom account model would add risk without improving the required
journey.

### Result

- Email matching is case-insensitive.
- Duplicate email addresses are rejected.
- Registration creates an unverified profile.
- Registration and sign-in remain separate actions.
- Passwords are never stored as plain text.

## ADR-003: Use PostgreSQL and database rules

**Status:** Accepted

### Decision

Use PostgreSQL locally and in production. Keep important rules in the database
as well as in forms and services.

### Why

The application needs reliable relationships, selected-area arrays, unique
records and safe plan-capacity updates. Using the same database locally and on
Heroku also reduces deployment surprises.

### Result

The database prevents duplicate profiles, duplicate plan participation,
duplicate conversations, self-blocking and invalid record states. Transactions
and row locks protect changes that could happen at the same time.

## ADR-004: Use broad areas and manual verification

**Status:** Accepted

### Decision

Let profiles choose one or more broad areas. Require staff verification before a
profile can use discovery, plans or direct messaging.

### Why

Broad areas support useful discovery without storing exact coordinates,
distance or location history. Manual verification provides a simple access gate
without claiming automated identity proof.

### Result

- Exact locations are never shown.
- Discovery uses only configured broad areas.
- Staff can grant or remove verification in Django Admin.
- Verification is described as access approval, not a safety guarantee.
- Profiles can use simple availability choices without calendar tracking.
- The Free now filter checks that availability has started.

## ADR-005: Create plans for established public places

**Status:** Accepted

### Decision

Require a title, description, established public place, normal HTTPS information
page, future start time and positive capacity. Eligible plans become available
as soon as they are created.

### Why

A public information page gives people something they can check before
attending. Immediate publishing keeps the product simple. Old pending and
rejected records are still handled safely for existing data.

### Result

- Private addresses are not part of the plan form.
- Owners can edit unlocked plans.
- Owners can cancel their plans.
- Past plans appear under Done where relevant.
- Cancelled plans remain visible as history.

## ADR-006: Protect plan capacity during joining

**Status:** Accepted

### Decision

Check plan state, time, capacity and current participation again when a person
joins or leaves. Lock the plan row while a join is saved.

### Why

Two people may press Join at nearly the same time. A page-level count alone could
allow both requests into the last place.

### Result

The database-backed transaction allows only the available number of places.
Leaving keeps participation history, and an eligible person may later rejoin.
The owner cannot join their own plan.

## ADR-007: Fetch plan metadata only after a button press

**Status:** Accepted

### Decision

Fetch a public place name and thumbnail only after the owner enters a URL and
presses Fetch details. Validate the address before making the outside request.

### Why

Automatic fetching on every form change would be surprising and could contact
unsafe or private network addresses.

### Result

- Only ordinary public HTTPS addresses are accepted.
- Private and local network targets are refused.
- Downloads have strict time and size limits.
- Images are checked and re-encoded.
- The owner can still enter the public place manually.

## ADR-008: Use refreshed plain-text messaging

**Status:** Accepted

### Decision

Allow one direct conversation for each permitted pair of verified accounts.
Store escaped plain-text messages and refresh them through normal page requests.

### Why

The product needs private coordination, not a full live-chat system. WebSockets,
attachments, read receipts and typing indicators would add more data and moving
parts.

### Result

- Only the two participants can open a conversation.
- Blocking closes access immediately.
- Message bodies are never placed in logs.
- The inbox shows people and activity times, not private message previews.
- Incoming messages and activity on owned plans create private notifications.
- The top bar shows an unread count without needing a background worker.

## ADR-009: Separate blocking from reporting

**Status:** Accepted

### Decision

Make blocking immediate. Keep reporting as a separate private statement for
staff review.

### Why

Blocking is a personal boundary and should take effect at once. A report is not
proof of wrongdoing and should not become a public accusation or automatic
punishment.

### Result

- Either block direction removes discovery and messaging access.
- A blocked account can still be reported privately.
- Reports contain a bounded category and description.
- Optional plan, conversation or message context is checked by the server.

## ADR-010: Let Stripe control Premium payment state

**Status:** Accepted

### Decision

Use Stripe-hosted Checkout and the Stripe customer portal. Grant or remove paid
access only from verified Stripe webhook events.

### Why

Kindelise should not collect card details. A browser returning from Checkout does
not prove that payment succeeded.

### Result

- Stripe owns card entry and subscription management.
- Signed webhook events update local Premium access.
- Duplicate and older events cannot overwrite newer state.
- The yearly price and currency are checked before paid access is granted.
- Failed event handling rolls back safely.

## ADR-011: Limit Ollama to an unsent draft

**Status:** Accepted

### Decision

Send only the current unsent draft and one fixed goal to Ollama. The allowed
goals are Fix grammar and Improve clarity.

### Why

The writing helper does not need profile details, previous messages, recipient
information or permission to send anything.

### Result

- Draft length is limited before the request.
- Grammar and clarity use different instructions.
- Suggestions are not saved automatically.
- The person chooses whether to use the suggestion.
- Provider failure leaves the original draft unchanged.

## ADR-012: Validate and protect uploaded images

**Status:** Accepted

### Decision

Check image type, file size and dimensions. Re-encode accepted images before
saving them. Use Cloudinary when it is configured and local storage during local
development.

### Why

Uploaded files cannot be trusted. Re-encoding removes hidden metadata and makes
the stored image format predictable. Cloudinary provides durable production
storage that survives Heroku restarts.

### Result

Profile images and fetched plan thumbnails are served through application rules.
Replacing an image removes the old stored file where possible.

## ADR-013: Use WhiteNoise for fixed site files

**Status:** Accepted

### Decision

Use WhiteNoise to serve collected CSS, JavaScript and Django Admin files in the
deployed application.

### Why

The project does not need a separate static-file server. WhiteNoise works with
Django and Heroku while keeping deployment small.

### Result

`collectstatic` creates compressed files with versioned names. Browsers receive
the latest assets after a deployment without committing generated `staticfiles/`
output.

## ADR-014: Keep privacy decisions on the server

**Status:** Accepted

### Decision

Derive owners, senders, recipients, payment identities and permission decisions
from the signed-in account and saved server data. Do not trust hidden form values
for authority.

### Why

Browser fields can be changed by the person making a request. Private data can
also leak when error messages explain too much.

### Result

- Forms accept only fields the person is allowed to change.
- Missing and forbidden private records share quiet responses where needed.
- CSRF protection is required for changes.
- Secrets, messages, reports and draft text stay out of logs.
- Provider failures do not grant access or remove safe local state.

## ADR-015: Keep the interface server-rendered

**Status:** Accepted

### Decision

Render pages with Django templates and use a small JavaScript file only for
progressive improvements such as filters, metadata fetching, notifications and
the draft editor.

### Why

The main journeys are forms, permissions and saved relational data. A separate
browser application and API would duplicate validation and access rules.

### Result

Core pages work through normal links and forms. JavaScript improves selected
interactions without becoming a second source of product rules.
