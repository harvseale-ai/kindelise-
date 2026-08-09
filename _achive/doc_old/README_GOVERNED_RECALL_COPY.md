# GovernedRecall Access Console

## Contents

- [Prerequisites](#prerequisites)
- [Quick Start Commands](#quick-start-commands)
- [Live Deployment](#live-deployment)
- [Problem Statement](#problem-statement)
- [User Stories](#user-stories)
- [Current Solution](#current-solution)
- [Plain-Language Terms](#plain-language-terms)
- [Product Screenshots](#product-screenshots)
- [Architecture](#architecture)
- [Key Technical Decisions](#key-technical-decisions)
- [Data Structure And Flow](#data-structure-and-flow)
- [Key Features](#key-features)
- [Existing Node.js Runtime](#existing-nodejs-runtime)
- [Run Locally](#run-locally)
- [Environment Summary](#environment-summary)
- [Deploy Django To Heroku](#deploy-django-to-heroku)
- [Deploy GRapi To Heroku](#deploy-grapi-to-heroku)
- [Known Limitations And Current Scope](#known-limitations-and-current-scope)
- [Verification And Test Coverage](#verification-and-test-coverage)
- [Assessment Fit](#assessment-fit)
- [AI Assistance](#ai-assistance)
- [Submission Scope](#submission-scope)

## Prerequisites

Install these tools before using the quick-start commands:

- Python 3.12 and `pip` for the Django application.
- Node.js 18 or later and npm for the GRapi runtime.
- Git for cloning and version control.
- SQLite for the minimal local Django setup, or PostgreSQL for deployment and GRapi persistence.
- A local or hosted Ollama-compatible endpoint for model-backed GRapi and AssistGR lanes.
- The Stripe CLI only when testing webhook-driven billing locally.
- The Heroku CLI only when reproducing the deployment steps.

## Quick Start Commands

From the project root, use two terminal windows:

```bash
# Terminal 1: run the GRapi Node.js runtime
cd GRapi
cp .env.example .env
npm install
npm start
```

```bash
# Terminal 2: run the Django access console
cp .env.example .env
python3 -m pip install -r requirements.txt
python3 manage.py migrate
python3 manage.py runserver
```

Then open:

```text
http://127.0.0.1:8000/
```

GovernedRecall Access Console is a full-stack Django website connected to the existing GRapi Node.js service. The website gives users account, billing, console, chat, and history pages.

GRapi already generates a draft, checks it, rewrites it when permitted, and decides what text may be displayed. Django adds accounts, access control, protected pages, saved user history, admin inspection, tests, and setup instructions.

## Live Deployment

- **GovernedRecall web application:** [governedrecall-0a7c8a02fc50.herokuapp.com](https://governedrecall-0a7c8a02fc50.herokuapp.com/)
- **Public GRapi health endpoint:** [governedrecall-grapi-e7dbc813cde0.herokuapp.com/api/health](https://governedrecall-grapi-e7dbc813cde0.herokuapp.com/api/health)
- **Agile user-story board:** [GovernedRecall GitHub Project](https://github.com/users/harvseale-ai/projects/4)

The health endpoint is intentionally public for platform checks. GRapi operational routes require the configured shared bearer secret in hosted deployments.

## Problem Statement

AI-generated text can sound confident even when it is weakly supported, has drifted from the user's request, or has turned limited context into an unjustified claim. That becomes risky when the output is copied into a decision, record, recommendation, or customer-facing response. A normal chat interface makes generation easy, but it does not give the user a clear checkpoint between "the model produced text" and "this text is permitted to be shown."

The repository's normative source-to-authority boundary is defined in the [Epistemic Authority Invariant](EPISTEMIC-INVARIANT.md). It is an enforcement target: the current runtime still has known gaps documented there, so the invariant must not be read as a claim that every reachable path is already closed.

GovernedRecall provides that checkpoint. A user submits a request, GRapi generates and checks a draft, and then either returns text that may be displayed, tries a limited rewrite and checks again, or returns a safe fallback. The page shows the status, reason, rewrite attempts, and a saved local record. It does not show blocked drafts as answers that the user can reuse.

The project is solving three connected problems:

1. **Output control:** generated text must pass GRapi's full check sequence before it is shown as governed output.
2. **User understanding:** AssistGR labels product help, clarification, check help, safe fallback, and governed output as different response types so ordinary guidance does not look approved.
3. **Account-level review:** signed-in users need a private history of what they submitted and what GRapi returned. A saved record cannot override GRapi's decision.

The intended user loop is deliberately small:

```text
Submit a draft
    -> GRapi generates and checks a candidate
    -> inspect the outcome and reason
    -> ask AssistGR what happened
    -> keep or delete the saved local record
```

Success therefore means more than generating a response. The interface must keep blocked text hidden, explain that product access is not output approval, show each user only their own records, and show why GRapi returned its result. Payment, saved history, recall, and memory cannot approve output.

## User Stories

Development is organized around the ten user stories in the [GovernedRecall GitHub Project](https://github.com/users/harvseale-ai/projects/4). The project board remains the source of truth for current status; the table below records the user need and the acceptance focus implemented and tested in this repository.

| Issue | User story | Acceptance focus |
| --- | --- | --- |
| [#1](https://github.com/harvseale-ai/governed-recall/issues/1) | As a new visitor, I want to create an account, so that I can access my own GovernedRecall console. | Validate signup fields, create the account and profile together, start without paid access, and show the account state clearly. |
| [#2](https://github.com/harvseale-ai/governed-recall/issues/2) | As a registered user, I want to log in and log out securely, so that only I can access my console and saved records. | Accept valid credentials, end the session on logout, redirect anonymous users, and keep authenticated navigation accurate. |
| [#3](https://github.com/harvseale-ai/governed-recall/issues/3) | As a logged-in user, I want to see whether my account has active access, so that I know whether I can run governed checks. | Show unpaid or active state consistently and prevent unpaid users from running the paid governed-check action. |
| [#4](https://github.com/harvseale-ai/governed-recall/issues/4) | As an unpaid user, I want a clear path to activate access, so that I can use the governed output-check feature. | Present the billing pre-step, keep checkout POST-only, handle Stripe return routes, and activate local product access without implying output approval. |
| [#5](https://github.com/harvseale-ai/governed-recall/issues/5) | As an active user, I want to submit AI-generated or source text for a governed check, so that GRapi can decide whether the response can be shown. | Validate input, require active access, call GRapi, require the governed-output response type for Check draft, and never save product-help chat as a governed check. |
| [#6](https://github.com/harvseale-ai/governed-recall/issues/6) | As an active user, I want to see the governed-check result clearly, so that I understand whether the output was allowed, blocked, or needs review. | Show the status and reason, display only text GRapi marked for display or an explicit safe fallback, and keep blocked or review-only drafts off the result page. |
| [#7](https://github.com/harvseale-ai/governed-recall/issues/7) | As a user, I want to see my saved governed-check history, so that I can review previous checks and outcomes. | List only the current user's governed receipts, link to result pages, exclude chat-only messages, and keep history separate from recent chats. |
| [#8](https://github.com/harvseale-ai/governed-recall/issues/8) | As a user, I want to delete my own saved governed-check records, so that I can manage my local account history. | Require confirmation and POST, enforce ownership, reject cross-user access, and make clear that deletion affects local history only. |
| [#9](https://github.com/harvseale-ai/governed-recall/issues/9) | As a user, I want to ask AssistGR questions about GovernedRecall and my current workflow, so that I can understand the product without confusing chat with governed-output approval. | Save each user's chat threads, label every response type, ask for clarification when needed, and save a governed-check record only when both governed-output markers match. |
| [#10](https://github.com/harvseale-ai/governed-recall/issues/10) | As the developer, I want the project documented, tested, deployed, and cleanly submitted, so that the assessor can verify the full-stack requirements without guessing. | Document setup, architecture, environment variables, deployment, automated checks, learning outcomes, and repository hygiene without committing secrets. |

## Current Solution

This project is a Django web application called GovernedRecall Access Console. Users can register, log in, activate access, and use a protected console to check whether a draft AI response is safe to show. Users can also see and manage local history for their previous checks and AssistGR conversations.

The application uses a hybrid architecture:

- Django handles user accounts, login, access status, protected pages, saved check history, AssistGR chats, forms, admin pages, and deployment.
- GRapi generates drafts, checks how closely they follow the request and supplied sources, attempts permitted rewrites, runs OutputPermission, controls recalled context, exports audit data, and saves its runtime records.
- When Django needs a governed result, it sends a JSON request to GRapi instead of repeating GRapi's rules in Python.
- Django stores account, access, chat, and saved-check records. It cannot make or replace GRapi's governed-output decision.

## Plain-Language Terms

- **GRapi runtime:** the running Node.js service that generates, checks, rewrites, and returns governed results.
- **Local receipt:** a `GovernedCheck` row saved for the signed-in user. It records what was submitted and what GRapi returned, but it cannot change that result.
- **AssistGR lane:** the response type returned by AssistGR, such as product help, clarification, check help, safe fallback, or governed output.
- **OutputPermission:** GRapi's final check for whether governed output may be displayed.
- **Authority:** the service or check that is allowed to make a specific decision. In this project, GRapi and OutputPermission decide whether governed output may be shown; payment and Django history do not.

## Product Screenshots

### Public Access Console

The public product guide introduces GovernedRecall, GRapi, AssistGR, pricing, and local check receipts before account creation.

![GovernedRecall public access console with product navigation, account actions, suggested questions, and a product-guide prompt.](readme-assets/product-public-access-console.png)

### Governed Console Workspace

The authenticated workspace combines governed-check submission, AssistGR guidance, recent chats, and a details panel that shows the GRapi result.

![GovernedRecall console workspace with navigation, governed-check composer, AssistGR action, and runtime outcome details.](readme-assets/product-governed-console.png)

### GRapi API-Key Records

The GRapi screen shows the signed-in user's API-key names, masked prefixes, active or revoked status, and create/revoke controls. It never displays a stored raw secret. The visible masked prefixes are dummy demonstration records.

![GovernedRecall GRapi API-key screen showing masked demonstration key records, project, creation date, billing tier, status, and revoke actions.](readme-assets/product-grapi-api-keys.png)

## Architecture

```text
Django Access Console -> sends governed requests to the GRapi Node.js service
Django Admin          -> reads local account, access, and history records
GRapi                 -> generates, checks, rewrites, and saves governed results
```

```text
Django = pages, accounts, access state, saved AssistGR chats, local check records, and admin inspection
GRapi = generation, request/source checks, recall, OutputPermission, audit data, and GRapi database records
Stripe = payment status only
```

Which system decides what:

```text
Stripe can activate product access.
Django saves account state, access state, AssistGR chats, and local check records.
GRapi decides how governed output is generated and checked.
OutputPermission makes the final decision about whether governed output may be displayed.
```

Important limits:

```text
Payment access is not output approval.
Django history is not GRapi's audit history and cannot change it.
Saved AssistGR messages help continue a chat; they are not proof, source evidence, or approved memory.
The application never writes to memory automatically. Payment, recall, and saved history cannot approve a memory write.
```

Keeping the checks in GRapi means another application could call the same service without copying the rules out of Django.

## Key Technical Decisions

The project keeps important decisions on the server and renders normal HTML pages instead of building a large browser application.

| Decision | Choice | Why |
| --- | --- | --- |
| Web application | Django views, forms, ORM, templates, and authentication | The product mainly handles accounts, forms, and saved records. Django already provides login, ownership checks, CSRF protection, validation, migrations, sessions, and admin tools. |
| Governance service | One HTTP client connects Django to the existing GRapi Node.js service | Generation, request/source checks, rewrites, recall, OutputPermission, and audit code stay in one service and can be tested without duplicating the rules in Django. |
| Browser rendering | Server-rendered HTML with local CSS and small local JavaScript files | The pages remain accessible and usable without a single-page application. JavaScript improves icons, theme, layout controls, and mobile navigation but does not own account or check data. |
| SVG versus Canvas | Local Lucide SVG icons loaded into semantic HTML; no Canvas UI | The product displays text, forms, tables, status details, and controls. SVG stays sharp, follows the theme colour, has accessible markup, and has a local fallback. Canvas would make keyboard use, text selection, responsive layout, and HTML validation harder without helping this interface. |
| Database | PostgreSQL in deployment, with Django's configured local database fallback for development | Accounts, access passes, saved checks, threads, messages, and key records must be linked to the correct user and deleted predictably. PostgreSQL keeps this data outside Heroku dynos, whose local files may disappear. |
| Application data | Real model and database records; no built-in product demo-data mode | The application runs against its real models. Tests replace only external services such as Stripe, GRapi HTTP, Ollama, and database connections so errors can be reproduced reliably. |
| Public product guide | Prewritten local answers before sign-in | Visitors can learn what the product does without calling a model, saving a chat, or exposing an unauthenticated model endpoint. A real runtime request requires authentication. |
| Service request | JSON-only requests to `/api/assistgr/governed-response` | Django sends only named, supported fields. Both services can reject missing, extra, or malformed data clearly. |
| Display selection | Check `display_status`, `final_allowed`, response type, and response policy before rendering | A successful HTTP response or an `allowed`-looking status is not enough to display hidden draft text. |
| Check history | Save input, displayed output, status, reason, check ID, and a payload copy | Users can review what happened. Deleting this local record does not delete or rewrite GRapi's own database or audit data. |
| API keys | One-time raw reveal followed by hash-and-prefix storage | Users can identify and revoke local key records without the application retaining recoverable raw secrets. The application refuses to reveal a new key when cookie-based sessions are configured. |
| UI state | Selected check in the URL and notification count in the session | "New check" opens a clean workspace, a selected result has a link that can be reopened, and temporary screen state does not need another database table. |

## Data Structure And Flow

The implementation map for a new developer is:

| File or area | Responsibility |
| --- | --- |
| [`console/forms.py`](console/forms.py) | Defines one required text field with a 5,000-character limit. |
| [`console/views.py`](console/views.py) | Checks access and ownership, selects the fields sent to GRapi, saves records, and passes named values to templates. |
| [`console/services.py`](console/services.py) | Sends HTTP requests to GRapi, chooses text GRapi marked for display, and extracts fields for the saved local check. |
| [`console/models.py`](console/models.py) | Defines saved checks, chat threads/messages, ownership validation, and hash-only API-key metadata. |
| [`billing/views.py`](billing/views.py) and [`billing/services.py`](billing/services.py) | Keep the read-only billing page, POST checkout, signed webhook activation, and Stripe request code separate. |
| [`GRapi/src/server/assistgr-governed-response-handler.js`](GRapi/src/server/assistgr-governed-response-handler.js) | Validates the request, selects an AssistGR response type, and runs the full governed-output check when required. |
| [`GRapi/src/`](GRapi/src/) | Contains model clients, request/source checks, governance rules, rewrites, OutputPermission, recall, database stores, and audit exports. |
| [`templates/`](templates/) and [`static/`](static/) | Render the fields selected by Django and provide responsive CSS plus small browser interactions. |

### Core Data Structures

The data model is intentionally split by responsibility:

| Structure | Important fields | What it stores and what it cannot do |
| --- | --- | --- |
| `UserProfile` | user, role, created timestamp | Adds local role information to an account. It cannot grant staff status, product access, or output approval. |
| `AccessPass` | user, status, provider, provider references, timestamps | One local product-access record per user. It never stores output permission or governance status. |
| `GovernedCheck` | user, origin, input text, display output, result status, reason code, GRapi check ID, response payload copy | Saves what the user submitted and what GRapi returned. Named fields support history lists and summaries. The saved payload cannot approve output or change GRapi. |
| `AssistGRThread` | user, optional linked check, title, timestamps | Groups saved chat messages. Normal chats stay separate from the one Q&A thread that may be linked to a saved check. |
| `AssistGRMessage` | thread, user, role, content, response-type metadata, optional governed-check link | Saves visible user and assistant messages plus their response label. A message is not approved memory or source evidence. |
| `GRapiAPIKey` | user, name, project, key prefix, SHA-256 hash, tier, revocation timestamp | Saves enough information to identify and revoke a local key record. The raw key is never saved, and these records do not authenticate requests to the deployed GRapi service. |

Model validation and user-filtered queries prevent one user's checks, chats, and keys from being linked to another user. One-to-one, cascade, and `SET_NULL` rules define exactly what happens when a linked record is deleted.

### Governed Check Request Flow

The main paid check flow is:

```text
Browser form
    -> GovernedCheckForm validates one required input_text (maximum 5,000 characters)
    -> handle_governed_check_submission checks the user's active AccessPass
    -> run_governed_check adds force_governed_output=true
    -> post_grapi sends JSON to /api/assistgr/governed-response
    -> GRapi accepts only the supported request fields
    -> GRapi generates a draft through the configured model client
    -> a request-following check measures whether the draft moved away from the user's request
    -> a source check records the first allowed or blocked result
    -> blocked drafts may enter the limited rewrite-and-check-again loop
    -> OutputPermission produces the final display decision
    -> GRapi returns response type, display status, result, reason, check ID, and rewrite-attempt details
    -> get_display_output selects only displayable or explicit safe-fallback text
    -> normalize_grapi_response extracts fields for the saved local check
    -> GovernedCheck is saved for the current user
    -> browser redirects to /console/?check=<local-id>
```

The smallest request payload is:

```json
{
  "input_text": "..."
}
```

The Django HTTP client may add only these fields:

| Optional field | Used for |
| --- | --- |
| `thread_display_context` | Up to 16 recent visible AssistGR messages, with each message limited to 1,000 characters. |
| `check_context` | Selected saved-check fields used to answer a check-help question. |
| `force_governed_output=true` | Tells GRapi that the paid Check draft action must return the governed-output response type. |

`check_context` and `force_governed_output` cannot be used together, and GRapi rejects a request that contains both. Django never lets a user send `allowed`, `final_allowed`, OutputPermission, recall, memory, writeback, or GRapi check-ID values as commands that could approve output.

The response is consumed in two layers:

1. `get_display_output()` accepts only `display_status="displayable"` with no explicit denial, or an explicit `safe_fallback`. One special clarification rule may use the final clarification text when GRapi labels it `safe_clarification`.
2. `normalize_grapi_response()` extracts `result_status`, `reason_code`, `grapi_output_check_id`, and the original payload copy for the saved local check. It never creates approval fields.

When a request fails, Django retries once. HTTP failures become a generic `GRapiError`. Invalid JSON and JSON values that are not objects are rejected immediately. URLs, headers, secrets, and provider error details are never shown to the user.

### AssistGR Response Types And Saved Chat Flow

AssistGR uses the same endpoint, but ordinary help messages do not run the full governed-output check:

```text
User message
    -> recent display-safe messages are selected (maximum 16; 1,000 characters each)
    -> GRapi validates input and context
    -> fixed rules or the interaction router select a response type
    -> small talk / product help / clarification / check help return labelled help without OutputPermission
    -> governed-output intent enters the full generation and OutputPermission check sequence
    -> Django stores the user and assistant messages atomically
    -> a GovernedCheck is saved only when both governed-output markers match
```

The two required markers are:

```text
interaction_mode = governed_output
response_policy = governed_output_permission
```

If either marker is missing or different, Django saves only the chat messages. Context sent with the next message includes visible user text and assistant messages marked `displayable` or `safe_fallback`. It excludes raw payloads, hidden drafts, check IDs, prompts, recall, memory, writeback, and approval fields.

Check help works differently. `build_check_context()` copies only the saved-check ID, status, reason, timestamp, input text, displayed text, display policy, rewrite count, and reason summary. The answer saves one user message and one assistant message in the check-linked thread. It never creates a second `GovernedCheck` or changes the original saved check.

### Billing And API-Key Flow

```text
GET /billing/info/
    -> render-only Free/Paid/API explanation
POST /billing/checkout/
    -> Stripe Checkout session creation
signed Stripe webhook
    -> activate or update the user's AccessPass
```

The success and cancellation pages only report return state. They do not activate access. Development activation is POST-only and available only when `DEBUG` is true. Payment changes product access; it does not change a GRapi output decision.

For local API-key records:

```text
generate grapi_ secret
    -> store prefix + SHA-256 hash
    -> keep raw secret in a server-side session for one reveal
    -> pop it on first display
    -> later show masked prefix only
    -> record revoked_at when the owner revokes the key
```

### Rendering Flow

The browser receives named fields selected by Django, not the full model response:

```text
user-scoped ORM query
    -> Django view selects the fields needed by the page
    -> template renders semantic HTML
    -> local CSS controls responsive desktop/mobile layout
    -> icons.js hydrates data-lucide placeholders with local SVG
    -> small layout and theme scripts improve controls without storing account or check data
```

Important rendering guards include:

- A fresh `/console/` request sets `details_check=None`, so the details rail does not inherit the previous result.
- `/console/?check=<id>` loads the selected saved check only when it belongs to the current user.
- Result and history pages render named status, reason, check-ID, and display fields. They never use `pprint` or show the raw payload.
- AssistGR renders `message.content` plus its response-type label, not hidden response-payload fields.
- Blocked drafts, prompts, full GRapi responses, internal source-check data, OutputPermission details, recalled context, memory, writeback, and source-truth fields are excluded from user-facing templates.
- JavaScript loads icons, changes the theme, resizes or collapses panels, closes rename menus, and opens mobile navigation. The server still checks access, ownership, database writes, and display permission.

## Key Features

- User Registration and Login: visitors can create an account, log in, log out, and see their current access state.
- Paid Access Gate: users start as unpaid, then activate access through a Stripe checkout or manual development-mode confirmation.
- Protected Console: logged-in users can access a console, but only active users can run governed checks.
- Governed Output Check: active users submit a draft AI response and receive an allowed/blocked result, a reason, and an optional safer rewrite.
- Saved History: each governed check is saved against the logged-in user so they can review previous inputs, displayed outputs, statuses, reasons, check IDs, and timestamps.
- Check Management: users can view and delete their own saved check records. This deletion does not change GRapi data.
- AssistGR Console: every signed-in account can ask product, clarification, and check-help questions and keep saved chats. Paid access remains required for the Check draft action that forces the governed-output response type.
- API Key Metadata: users can create local GRapi API-key records that store only hashed keys and short prefixes after creation.
- Neon PostgreSQL Database: Django can use Neon/Postgres for its local account, access, history, and thread records.
- Admin Review: Django admin can inspect local users, access passes, saved checks, and API-key metadata. Admin users cannot use these pages to approve GRapi output.
- Responsive Interface: pages use semantic HTML, accessible forms, clear messages, and custom CSS suitable for desktop and mobile.
- Testing: the project includes tests for signup, login, paid/unpaid access, billing webhooks, protected console behaviour, saved history, AssistGR response types and access rules, API-key handling, and frontend accessibility.

## Existing Node.js Runtime

GRapi is a Node.js HTTP service, not a NestJS application. It provides the governed-check and AssistGR routes called by Django.

For a plain-language flowchart showing how each route and source file is used, read [`GRapi/RUNTIME.md`](GRapi/RUNTIME.md).

Django-facing GRapi route:

```text
POST /api/assistgr/governed-response
= AssistGR governed response route. GRapi owns generation, checking, transform sequencing, and final governed response payloads.
```

GRapi also provides routes for output checks, audit exports, recall, memory-write review, draft generation, governed rewrites, review feedback, learning review, and health checks. Their rules stay in GRapi and are not repeated in Django.

GRapi internally generates, checks, transforms, and returns the final governed result. Django stores only a local account-history receipt.

GRapi performs the checks and returns the result. Django shows and saves that result, but it cannot mark an AI suggestion as trusted, approve output, approve memory, or replace GRapi's decision.

## Run Locally

Create Django environment settings:

```bash
cp .env.example .env
```

For Stripe test billing, fill in `STRIPE_SECRET_KEY`, `STRIPE_PUBLISHABLE_KEY`,
`STRIPE_PRICE_ID`, and `STRIPE_WEBHOOK_SECRET`. The Checkout success page is
only a return page; paid access is activated by the Stripe webhook. In local
development, forward Stripe events to Django:

```bash
stripe listen --forward-to localhost:8000/billing/webhook/
```

Run GRapi:

```bash
cd GRapi
cp .env.example .env
npm install
npm start
```

GRapi reads its local environment settings to connect to PostgreSQL/Neon and Ollama when a request needs those services.

Run GRapi tests:

```bash
cd GRapi
npm run lint
npm test
```

There is no root `package.json`; run GRapi commands from `GRapi/`.

Run Django:

```bash
python3 -m pip install -r requirements.txt
python3 manage.py migrate
python3 manage.py runserver
```

Install the development quality tools, then run Django lint, checks, and tests:

```bash
python3 -m pip install -r requirements-dev.txt
python3 -m ruff check .
python3 manage.py check
python3 manage.py test
```

## Environment Summary

Use the root `.env.example` for Django and `GRapi/.env.example` for GRapi. Never commit populated `.env` files or production secret values.

### Django Environment

| Variable | Purpose |
| --- | --- |
| `DJANGO_SECRET_KEY` | Signs Django sessions and security-sensitive values. Production requires a long random value. |
| `DJANGO_DEBUG` | Enables local debug behavior. Set to `False` in production. |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated hostnames Django may serve. |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | Comma-separated HTTPS origins trusted for deployed POST requests. |
| `DJANGO_SECURE_SSL_REDIRECT` | Redirects HTTP requests to HTTPS. |
| `DJANGO_SESSION_COOKIE_SECURE` | Sends the session cookie over HTTPS only. |
| `DJANGO_CSRF_COOKIE_SECURE` | Sends the CSRF cookie over HTTPS only. |
| `DJANGO_SECURE_HSTS_SECONDS` | Enables HTTP Strict Transport Security for the configured duration. |
| `DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS` | Applies HSTS to subdomains. |
| `DJANGO_SECURE_HSTS_PRELOAD` | Adds the HSTS preload directive. |
| `DJANGO_SECURE_REFERRER_POLICY` | Configures Django's `Referrer-Policy` header. |
| `DJANGO_USE_X_FORWARDED_PROTO` | Trusts Heroku's forwarded HTTPS protocol header. |
| `DATABASE_URL` | Django account, access, thread, and local-receipt database. SQLite is the local fallback; deployment uses PostgreSQL. |
| `GRAPI_BASE_URL` | HTTPS base URL of the separately deployed GRapi service. |
| `GRAPI_API_KEY` | Outbound bearer secret; it must equal GRapi's `GRAPI_SHARED_SECRET`. |
| `GRAPI_TIMEOUT_SECONDS` | Timeout for Django-to-GRapi requests. |
| `STRIPE_SECRET_KEY` | Server-side Stripe API credential. |
| `STRIPE_PUBLISHABLE_KEY` | Public Stripe key kept with the other Stripe settings. |
| `STRIPE_WEBHOOK_SECRET` | Verifies Stripe webhook signatures. |
| `STRIPE_PRICE_ID` | Stripe price used when creating checkout sessions. |

### GRapi Environment

| Variable | Purpose |
| --- | --- |
| `PORT` | HTTP port. Heroku supplies this automatically. Local GRapi defaults to `3123`. |
| `DATABASE_URL` | PostgreSQL connection used by release migrations and saved GRapi records. Hosted URLs must select SSL, for example with `sslmode=require`. |
| `DATABASE_SSL_REJECT_UNAUTHORIZED` | Controls PostgreSQL certificate verification after SSL is selected. It defaults to verification and should be set to `false` only when the database provider requires it. |
| `GRAPI_SHARED_SECRET` | Bearer secret required by operational routes. It must equal Django's `GRAPI_API_KEY`. |
| `OLLAMA_BASE_URL` | Base URL of the local or hosted Ollama-compatible model service. |
| `OLLAMA_MODEL` | Model name used by generation and AssistGR lanes. |
| `OLLAMA_API_KEY` | Optional bearer key required by hosted Ollama services. It is not needed for an unsecured local Ollama endpoint. |
| `OLLAMA_TIMEOUT_MS` | Optional model-request timeout in milliseconds. |

For production-style deployments, set `DJANGO_DEBUG=False`, use a long random `DJANGO_SECRET_KEY`, configure real hosts and CSRF origins, use production database and Stripe values, and enable the secure cookie, HTTPS, and HSTS settings documented in `.env.example`.

## Deploy Django To Heroku

The root `.python-version` keeps Heroku on the same Python 3.12 major version used for local verification. The root `Procfile` runs Django migrations during Heroku's release phase and serves the web app with Gunicorn.

Before deploying, add these Config Vars in the Heroku app's **Settings** page. Replace `<app-name>` with the app's actual Heroku name and generate a private secret with the command below. Never commit the generated value.

```bash
python3 -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

```text
DJANGO_SECRET_KEY=<generated-private-value>
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=<app-name>.herokuapp.com
DJANGO_CSRF_TRUSTED_ORIGINS=https://<app-name>.herokuapp.com
DJANGO_USE_X_FORWARDED_PROTO=True
```

Attach Heroku Postgres so Heroku provides `DATABASE_URL`. Do not use the SQLite fallback in production because files stored inside a Heroku dyno may disappear when the dyno restarts or is replaced.

Heroku runs `collectstatic` during the build. Keep that enabled: WhiteNoise serves the collected local CSS and JavaScript in production. A missing `DJANGO_SECRET_KEY` or `DJANGO_ALLOWED_HOSTS` intentionally fails the build rather than starting Django with unsafe production settings.

This Heroku web process deploys the Django console only. Governed checks and AssistGR requests require `GRAPI_BASE_URL` to point to a separately deployed GRapi service over HTTPS; `127.0.0.1:3123` works only on the local machine and cannot reach another Heroku dyno. Stripe checkout also requires the real Stripe settings listed above.

## Deploy GRapi To Heroku

GRapi lives in the `GRapi/` subtree and is deployed as a separate Node.js Heroku application. Its [`Procfile`](GRapi/Procfile) declares:

```text
release: npm run migrate
web: npm start
```

The release command applies PostgreSQL migrations before the new web release becomes available. The web process starts the HTTP runtime from `src/server.js`.

Create the app and its Git remote once, or reuse an existing GRapi app:

```bash
heroku create <grapi-app-name> --region eu
heroku git:remote --app <grapi-app-name> --remote heroku-grapi
```

Attach PostgreSQL. Heroku normally exposes the promoted attachment as `DATABASE_URL`:

```bash
heroku addons:create heroku-postgresql:essential-0 --app <grapi-app-name>
heroku pg:info --app <grapi-app-name>
```

If Heroku creates only a colour-named attachment URL, promote that attachment so `DATABASE_URL` is populated. The final PostgreSQL connection must use encrypted transport; configure the provider URL with `sslmode=require`. Keep certificate verification enabled unless the database provider specifically requires `DATABASE_SSL_REJECT_UNAUTHORIZED=false`.

Generate one private shared password for communication between Django and GRapi, then configure the hosted model endpoint. Do not commit these values:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"

heroku config:set \
  GRAPI_SHARED_SECRET=<generated-shared-secret> \
  OLLAMA_BASE_URL=<hosted-ollama-url> \
  OLLAMA_MODEL=<hosted-model-name> \
  OLLAMA_API_KEY=<hosted-ollama-api-key> \
  --app <grapi-app-name>
```

Deploy only the GRapi subtree. Heroku then detects the subtree's `package.json`, runs the release migration, and starts the web process:

```bash
git subtree push --prefix GRapi heroku-grapi main
```

Verify the release and public health endpoint:

```bash
heroku ps --app <grapi-app-name>
heroku logs --tail --app <grapi-app-name>
curl https://<grapi-app-name>.herokuapp.com/api/health
```

Finally, point Django at GRapi and use the same shared secret on both sides:

```bash
heroku config:set \
  GRAPI_BASE_URL=https://<grapi-app-name>.herokuapp.com \
  GRAPI_API_KEY=<generated-shared-secret> \
  --app <django-app-name>
```

`GRAPI_SHARED_SECRET` controls which clients may call GRapi's protected routes. It does not approve output; OutputPermission still makes the final display decision.

## Known Limitations And Current Scope

- The API-key page creates demonstration key records that belong to the signed-in user. It reveals each raw key once, then stores only its hash and prefix. These records do not currently authenticate public API consumers; hosted Django-to-GRapi requests use the separate shared password.
- Stripe changes local product access only. Payment does not approve generated output or change a GRapi runtime decision.
- Requests that generate AI text require a reachable local or hosted Ollama-compatible service. Hosted Ollama and Stripe work only when their external services and credentials are configured correctly.
- Selecting information for recall does not approve output and does not permit it to be written to memory. A separate review must approve any memory write.
- Saved local checks help users review what they submitted and what GRapi returned. They are not GRapi audit records, and deleting one does not change or delete GRapi history.
- Lighthouse scores are point-in-time measurements and can change with browser, network, authentication state, route, and deployment conditions.

## Verification And Test Coverage

### Reproduce The Automated Checks

Run the Django quality and regression gates from the repository root:

```bash
python3 -m pip install -r requirements-dev.txt
python3 -m ruff check .
python3 manage.py makemigrations --check --dry-run
python3 manage.py check
python3 manage.py collectstatic --dry-run --noinput --verbosity 0
python3 manage.py test
```

Run the GRapi quality and regression gates from the Node.js runtime directory:

```bash
cd GRapi
npm install
npm run lint
npm test
npm audit
```

Latest verified results, run locally on **13 July 2026**:

| Gate | Result |
| --- | --- |
| Ruff Python static analysis | Passed with 0 errors |
| Django system check | Passed with 0 issues |
| Django regression suite | 260 tests passed |
| Django migration drift check | No model changes missing migrations |
| Django static collection dry run | Passed |
| ESLint JavaScript static analysis | Passed with 0 errors and 0 warnings |
| GRapi Node.js regression suite | 775 tests passed |
| npm dependency audit | 0 vulnerabilities |

Ruff checks application and test code for import, syntax, undefined-name, and error-prone Python issues. Generated Django migrations are excluded from Ruff because they are framework-generated history; migration drift checks and Django tests cover their integration.

### Django Test Coverage

The Django suite contains **260 tests** across three application-level suites.

#### Accounts: 28 Tests

The accounts suite covers:

- Named account routes and protected-route login redirects, including preservation of the requested `next` destination.
- The global template shell, local static assets, CSP-tolerant script loading, accessible landmarks, navigation, status messages, and POST/CSRF logout.
- Public product-guide questions for GRapi, AssistGR, pricing, and saved checks using fixed local answers without GRapi calls, database writes, memory, or output approval.
- Public pricing cards, the sign-in dialog, local product explanations, and the rule that a user must sign in before making a GRapi request.
- Allowed signup fields, required email, duplicate username detection, and case-insensitive duplicate email rejection.
- Saving the user and profile together, including removal of the new user if profile creation fails.
- Login rendering, invalid credentials, successful redirects, and checks that authentication pages never claim to approve output.

#### Billing: 36 Tests

The billing suite covers:

- `AccessPass` defaults, active/unpaid/cancelled behavior, one access record per user, deletion with the user, and confirmation that the model has no output-approval fields.
- Read-only billing admin pages and the small set of supported billing URLs.
- The render-only billing information page, Free/Paid/API cards, responsive plan CSS, correct local links, active-access state, and absence of GET checkout links.
- POST-only Stripe checkout, storage of Stripe session IDs only, malformed checkout responses, and user-safe error copy that hides settings, secrets, exceptions, and tracebacks.
- Stripe checkout payload construction, optional customer email handling, and required secret/price/webhook configuration.
- Signed webhook processing, invalid-signature rejection, supported event filtering, paid/no-payment-required activation, and rejection of unpaid, non-subscription, missing-user, or unknown-user events.
- Success and cancellation return pages as render-only status pages that never activate access directly.
- Development activation as POST-only and `DEBUG`-gated.
- Repeated checks that billing changes product access only and never creates governed output, AssistGR history, a GRapi key, OutputPermission, recalled context, or a memory write.

#### Console: 196 Tests

The console suite covers:

- One required source-text form field with a 5,000-character limit and no user-controlled approval fields.
- Models and migrations for saved checks, AssistGR threads/messages, one Q&A thread per check, separate JSON defaults, user ownership, deletion behavior, and hash/prefix-only API-key records.
- Model validation against cross-user thread, message, check, and linked-Q&A relationships.
- Read-only admin pages that hide key hashes and do not allow saved checks or key records to be edited.
- Active-access checks for governed drafts, while signed-in free users may still use AssistGR product and check help.
- The main governed-check flow, required governed-output response type, saved local checks, generic GRapi errors, history notifications, and check selection through the URL.
- Fresh/new-check state, selected-check state, result-page return links, cross-user selection rejection, and preservation of saved history and latest-check Q&A.
- History, result, and deletion pages that load only the current user's checks; GET shows confirmation, POST deletes the local row, and no GRapi record is changed.
- Display rules for safe fallbacks, blocked/hidden/unknown statuses, `final_allowed=False`, hidden drafts, prompts, source-check data, full payloads, and approval fields.
- Selection and saving of AssistGR response types: governed output, AI-bounded response, pinned product response, clarification, check help, and safe fallback.
- AssistGR thread creation, navigation, POST-only rename/delete, user ownership, separate check-Q&A threads, title limits, all-or-nothing saving, and limits on prior messages sent to GRapi.
- Check-help fields, one Q&A thread per check, message-only saving, exclusion of the raw payload, protection of the original check, and rollback after an error.
- Django's GRapi HTTP client: JSON requests, optional bearer secret, configured timeout, one retry, generic errors without chained provider details, rejection of invalid JSON, and exact checks for governed-output mode and policy.
- Selection of display text and extraction of saved fields without creating approval, audit, recall, memory, or writeback values.
- GRapi API-key creation and revocation: active-access requirement, one-time raw reveal, hash/prefix-only storage, server-side-session requirement, refusal under signed-cookie sessions, current-user filtering, and safe repeated revocation.
- Canonical named routes, anonymous redirects, POST-only mutation routes, removal of the legacy AssistGR route, and no hidden development activation in production UI.
- Templates, CSS, and browser scripts for responsive layout, accessible controls, icon fallback, pointer-event cleanup, panel toggles, local assets, clear copy, and removal of raw backend or GRapi details from user pages.

### GRapi Test Coverage

The GRapi suite contains **775 Node.js tests** covering its decisions, routes, model clients, and database code.

#### Governance And OutputPermission

- Governance rules, the matrix that lists which component may make each decision, saved decision data, review rules, and compatible review results.
- Required OutputPermission data and checks, allowed/blocked decisions, limited rewrites, rules that rewrites must preserve, nudge event codes, and governed-reading drafts.
- Checks that output follows the request and supplied source, records showing how each draft was produced, and quality-nudge details.

#### AssistGR Lanes

- Response classification, the initial response structure, product information, and the code that selects an AssistGR response type.
- Small talk, product help, clarification, check help, and governed-response behavior.
- Labels and field checks that stop help or pinned responses from looking like governed-output permission.
- Governed-response routes, safe fallbacks, and removal of fields that could be mistaken for approval.

#### Recall And Writeback

- Rules for selecting recalled information, retrieval, the context that may be sent to the model, recall routes, and recall audit events.
- Memory-write review routes and separate checks for selecting recalled information, approving a memory write, and displaying output.

#### Persistence Audit And Review

- Opening and closing database clients, migrations, which error is reported when cleanup also fails, and database save/read routes.
- Saved output checks and rewrite events, audit exports, learning details calculated from saved data, and records showing how each draft was produced.
- Learning-review and review-feedback routes, with tests confirming that review notes cannot approve runtime output.

#### Runtime Routes Authentication And Model Adapters

- Health and protected service routes, output-check routes, draft generation, governed rewrites, and generation from saved checks.
- Constant-time shared-secret bearer validation for protected routes while keeping the health endpoint public.
- Environment loading, JSON schema validation, and selection of the correct route handler.
- Ollama requests, hosted `OLLAMA_API_KEY` authorization, model-service failures, and the data passed to and returned from model clients.

Exact test counts can change as focused cases are added or split; command output is the source of truth. Passing suites prove the behavior covered by these tests, not every production condition or third-party service guarantee.

### Browser Validation And Lighthouse

Rendered pages were checked with the W3C HTML validator rather than by submitting unrendered Django templates. The reviewed home, console, history, AssistGR, GRapi, settings, and billing pages pass the final HTML/CSS validation pass. This includes heading structure, valid `datetime` values, permitted ARIA use, labelled controls, decorative icon behavior, and local static-asset loading.

The latest supplied **mobile Lighthouse audit** of the console reported:

| Lighthouse category | Score |
| --- | ---: |
| Performance | 100 |
| Accessibility | 100 |
| Best Practices | 100 |
| SEO | 90 |

Measured performance metrics from that run:

| Metric | Result |
| --- | ---: |
| First Contentful Paint | 1.4 s |
| Largest Contentful Paint | 1.4 s |
| Speed Index | 1.4 s |
| Total Blocking Time | 0 ms |
| Cumulative Layout Shift | 0 |

#### Validation Evidence

The screenshots below record the supplied mobile Lighthouse audit and the successful W3C CSS validation result.

**Mobile Lighthouse audit**

<img src="readme-assets/lighthouse-mobile-audit.png" alt="Mobile Lighthouse report showing Performance 100, Accessibility 100, Best Practices 100, SEO 90, First Contentful Paint 1.4 seconds, Largest Contentful Paint 1.4 seconds, Total Blocking Time 0 milliseconds, and Cumulative Layout Shift 0." width="720">

**W3C CSS validation**

![W3C CSS Validator result showing no errors for CSS Level 3 and SVG.](readme-assets/w3c-css-validation.png)

Lighthouse values are point-in-time estimates and can vary by machine, network, authentication state, browser version, and deployed environment. The SEO score reflects an authenticated application console rather than a public marketing page. Re-run Lighthouse against the intended public and authenticated routes before each production release.

## Assessment Fit

This project meets the full-stack assessment by delivering a Django application with authentication, access control, custom models, database-backed records, admin management, form validation, responsive pages, automated tests, secure environment-variable configuration, deployment notes, and a short record of how AI tools supported the build.

## AI Assistance

AI tools supported implementation and review by suggesting review questions, finding places where one component might wrongly make another component's decision, proposing tests, and improving code, wording, and accessibility. Every final change was applied to the local repository and checked with the Django and GRapi commands listed above.

## Submission Scope

This README is the main document for the submitted repository. Detailed GRapi rules and evidence remain next to the code that uses them: source files, migrations, JSON schemas, and automated tests.
