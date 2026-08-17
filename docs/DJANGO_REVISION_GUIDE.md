# Kindelise Django Revision Guide

## The 30-second explanation

Kindelise is one Django **project** containing one custom Django **app**. The
`config` folder starts and configures the website. The `kindlelise` folder owns
the product itself: accounts, profiles, discovery, plans, messages, safety and
Premium. Django receives a web address, finds its view, checks the submitted
form and permissions, reads or changes the database, and renders an HTML
template. This server-rendered structure keeps private decisions on the server
and avoids maintaining a separate front-end application and API.

The main request path is:

`browser → config/urls.py → kindlelise/urls.py → view → form/policy/selector/service → model → template → browser`

- A **view** coordinates one page or action.
- A **form** checks information supplied by a user.
- A **policy** answers whether an action is allowed.
- A **selector** reads only the permitted database information.
- A **service** makes an important database change.
- A **model** describes stored information and database rules.
- A **template** turns the result into HTML.

## Files that start and configure Django

| File | What it does and why it matters |
| --- | --- |
| `manage.py` | Django's local command entry point. Commands such as `runserver`, `migrate`, `createsuperuser` and `check` all start here. It points Django at `config.settings`. |
| `config/settings.py` | The central configuration: installed apps, middleware, templates, database, security, static files, Cloudinary, Stripe and Ollama settings. Environment variables keep passwords and production values out of Git. |
| `config/urls.py` | The website's top-level address map. It sends `/admin/` to Django Admin and all other addresses to the Kindelise app. |
| `config/wsgi.py` | Gives a traditional web server the callable used to run Django. Gunicorn uses this on Heroku. |
| `config/asgi.py` | Provides Django's newer asynchronous server entry point. It is retained even though this app currently uses normal request-and-response pages. |
| `config/__init__.py` | Marks `config` as an importable Python package. It intentionally contains no product behaviour. |
| `.env.example` | Lists the environment variables a developer or host must supply without containing real secrets. |
| `requirements.txt` | Lists deployable Python packages in the format Heroku expects. |
| `pyproject.toml` | Holds project metadata and settings for development tools such as pytest and Ruff. |
| `Procfile` | Tells Heroku to start Gunicorn with `config.wsgi`. |

## The Kindelise application files

| File | What it does and why Kindelise uses it |
| --- | --- |
| `kindlelise/apps.py` | Registers the `kindlelise` app with Django. Django uses this while loading models, migrations and Admin configuration. |
| `kindlelise/urls.py` | Maps every product address to the view that owns it. Named routes let templates create links without repeating hard-coded URLs. |
| `kindlelise/models.py` | Defines the database structure for interests, profiles, plans, participation, conversations, messages, notifications, blocks, reports and subscriptions. Relationships and database constraints protect the data even if two requests happen together. |
| `kindlelise/forms.py` | Checks and cleans sign-up, profile, discovery, plan, message and report input. Keeping validation here gives the user clear errors before a service attempts to save anything. |
| `kindlelise/policies.py` | Holds yes-or-no permission rules for verification, discovery, profiles, plans, messages and reports. Central rules prevent pages from quietly making different privacy decisions. |
| `kindlelise/selectors/` | Groups the larger database reads by accounts, discovery, plans, messages, and safety. Each selector applies visibility and blocking rules before returning page data, making accidental private-data exposure less likely. |
| `kindlelise/admin.py` | Configures Django Admin for authorised staff. Staff can verify profiles, review plans and reports, and inspect subscription records without building a second staff website. |
| `kindlelise/context_processors.py` | Adds the unread-notification count to every rendered page, allowing the shared top bar to show one consistent badge. |
| `kindlelise/plan_metadata.py` | Safely reads a public-place URL and extracts a place name and image. It limits addresses, redirects, content types and download size because the server is fetching an outside website. |
| `kindlelise/ai_message_editor.py` | Sends only an unsent draft and the chosen editing goal to Ollama. It keeps the optional writing aid separate from sending or storing the message. |
| `kindlelise/__init__.py` | Marks the folder as an importable Python package. |

## Why views and services are split into folders

The original `views.py` and `services.py` became difficult to scan. They were
split by feature without changing the app or its behaviour. This keeps one
connected Django app while giving each workflow a clear home.

| File | Responsibility |
| --- | --- |
| `views/accounts.py` | Home, guide, notifications, sign-up, sign-in, sign-out, private profile editing and protected profile images. |
| `views/discovery.py` | Discovery results and other people's public profile pages. |
| `views/plans.py` | Plan lists, metadata fetching, creation, images, details, editing, joining, leaving and cancellation. |
| `views/messages.py` | Inbox, conversations, message sending and unsent-draft suggestions. |
| `views/safety.py` | Blocking and private reporting pages and actions. |
| `views/billing.py` | Stripe Checkout, customer portal and signed webhook endpoints. |
| `views/common.py` | Small display and safe-redirect helpers shared by more than one view. |
| `views/__init__.py` | Makes the split view package available from one familiar import location and preserves the public view names. |
| `services/accounts.py` | Creates accounts and profiles together, saves profile edits and marks notifications read. |
| `services/plans.py` | Safely changes plans and participation, including capacity locking and owner notifications. |
| `services/messages.py` | Creates one conversation per pair and saves messages with recipient notifications. |
| `services/safety.py` | Saves blocks and private reports while preserving the correct relationships. |
| `services/billing.py` | Creates Stripe-hosted Checkout and account-management sessions. Card details never pass through Kindelise. |
| `services/stripe_events.py` | Turns verified Stripe events into local Premium access and records processed events so repeats are harmless. |
| `services/__init__.py` | Marks the services folder as a Python package. |

## Database history, pages and browser files

| Files | Purpose |
| --- | --- |
| `migrations/0001_initial.py` | Creates the first database structure. |
| `migrations/0002` to `0008` | Record later changes: starter interests, availability, images, title statements, multiple broad areas and notifications. Migrations must remain because Django uses the full ordered history to build a new database correctly. |
| `templates/base.html` | Shared HTML shell containing the header, navigation, notifications and page blocks. Every product page inherits the same structure. |
| `templates/account.html` | Handles both the signed-in account and permitted public-profile presentation. |
| `templates/discover.html` | Discovery filters and profile cards. |
| `templates/plan.html` | Plan list, create, edit and detail modes; shared so plan presentation remains consistent. |
| `templates/inbox.html` and `conversation.html` | Conversation list, message history, composer and writing suggestion panel. |
| `templates/notifications.html` | Recent activity and the mark-as-read action. |
| `templates/report.html` | Private reporting form. |
| `templates/guide.html` | Plain-language product guide. |
| `templates/admin/.../change_form.html` | Adds the custom verification control to Django's profile Admin page. |
| `static/app.css` | The shared responsive visual system. One stylesheet keeps colours, spacing, cards and forms consistent. |
| `static/app.js` | Small browser behaviours such as filters, notifications, plan metadata previews, colour themes and draft suggestions. Important decisions still happen on the server. |

## Quality and study files

| File | Why it exists |
| --- | --- |
| `tests/test_accounts.py` | Checks registration, sign-in, profiles and staff controls. |
| `tests/test_discovery.py` | Checks discovery filters, visibility and profile access. |
| `tests/test_plans.py` | Checks plan pages, editing, participation, capacity and metadata. |
| `tests/test_messages.py` | Checks conversations, messages, notifications and draft suggestions. |
| `tests/test_safety.py` | Checks blocking and private reports. |
| `tests/test_billing.py` | Checks Stripe Checkout, webhooks and Premium access. |
| `tests/conftest.py` | Shared pytest setup used before tests run. |
| `README.md` | Main product, setup, architecture, testing and deployment guide. |
| `docs/DECISIONS.md` | Records the reasons behind important technical choices. |
| `docs/MANUAL_TESTING.md` | Records browser checks and their results. |
| `docs/RUNTIME.md` | Source for the clickable runtime flowcharts. |
| `tools/build-runtime-explorer.mjs` | Checks the flowchart links and generates `runtime-explorer.html`. This is a study tool, not part of the live app. |

## Why one custom Django app was the right choice

Profiles, discovery, plans, messages, notifications and safety all depend on
the same users, verification state, blocking rules and permissions. Splitting
them into several Django apps now would create extra imports and migrations
without creating truly independent products. Kindelise therefore keeps one
custom app but separates views and services by feature. This gives simple
Django configuration and an understandable code layout at the same time.

## Presentation points to remember

1. Django is responsible for routing, forms, authentication, database access,
   templates, security middleware and Admin.
2. Permission decisions remain on the server; CSS and JavaScript only improve
   presentation and interaction.
3. Reads are placed in selectors, permission questions in policies, and
   important writes in services so each responsibility is easy to find.
4. PostgreSQL constraints and transactions support the Python checks, especially
   for plan capacity, participation and unique conversations.
5. Stripe, Ollama and Cloudinary have small, defined boundaries. Kindelise sends
   only what each service needs and checks returned information before trusting it.
6. The app is server-rendered because its main challenge is safe connected data,
   not a highly interactive separate front end.
