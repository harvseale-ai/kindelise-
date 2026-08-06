# Kindlelise

Kindlelise is a student-scale, server-rendered Django MVP for discovering
staff-verified profiles in broad named areas, arranging approved public-place
plans, direct messaging, blocking and private reporting.

## Current status

The student MVP vertical slice is implemented locally. Exact completion state,
test evidence and remaining runtime work are kept in the progress ledger. The
older production-scale scaffold under `_achive/` and supporting documents under
`doc_old/` are historical references only, not implementation sources.

The authoritative scope is [docs/VERTICAL_SLICE.md](docs/VERTICAL_SLICE.md). The
ordered build and runtime gates are in
[docs/IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md).
Mutable phase State and Evidence are recorded separately in
[docs/IMPLEMENTATION_PROGRESS.md](docs/IMPLEMENTATION_PROGRESS.md).
Use [docs/MASTER_INSTRUCTION_PROMPT.md](docs/MASTER_INSTRUCTION_PROMPT.md) at the
start of repeated review, implementation, test and runtime passes; it summarizes
the guardrails but never replaces the vertical slice.

## Approved MVP boundary

- Email/password authentication through Django; Stripe ownership still uses
  immutable local account and Stripe identifiers rather than email.
- One initially incomplete, unverified profile per registered account.
- Manual staff verification before discovery, plans or messaging.
- Broad configured area keys and controlled interests; no coordinates, PostGIS
  or location history.
- Public-place plans with manual URL review, capacity-safe participation and a
  first-join edit lock.
- One plain-text direct conversation per account pair.
- Directional blocks and private, non-adjudicative reports.
- One Stripe-hosted Premium subscription projection.
- One explicit Ollama Cloud grammar or clarity suggestion for an unsent draft.

This slice is designed for supervised test accounts. It has no age-verification
system and must not be presented as ready for unrestricted public use.

## Implementation shape

The approved implementation is one Django application backed by PostgreSQL. The
36-file limit is a maximum; 33 slots are mapped and normal generated migrations
are documented mechanical exceptions. Do not recreate the archived REST API,
native iOS client, precise proximity system or automated face verification in
the student MVP.

Setup, migration, seeded-interest, Stripe CLI, Ollama Cloud and test commands
are added only when their owning implementation phase exists and has been
verified.

## Local setup

Prerequisites are Python 3.12 and PostgreSQL. The application has no SQLite
fallback.

```text
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[test]'
cp .env.example .env
```

Generate a long local Django secret, replace every `replace_me` value in `.env`,
and create the PostgreSQL database/account named by the `POSTGRES_*` settings.
Load the file into the current shell before using Django:

```text
set -a
source .env
set +a
python manage.py check
python manage.py collectstatic --noinput
```

`DATABASE_URL` takes precedence when present, including on Heroku. Application
secrets, Stripe identifiers and Ollama credentials must remain in environment
configuration and must not be committed or logged.

## Authentication and assessment limits

The MVP uses Django email/password authentication. Registration canonicalises the
email to lowercase and stores it in Django's unique username field as well as its
email field. The email never proves Stripe ownership. Registration creates an
initially incomplete, unverified profile; authorised staff verification is
required before discovery, plans or messaging.

The assessment uses supervised test accounts only. Kindlelise does not implement
age or identity verification, does not guarantee venue safety and must not be
presented as ready for unrestricted public use.

## Fixed assessment areas

`config/settings.py` stores stable area keys for Central, North, South, East and
West plus the explicitly approved nearby-area mapping. No exact coordinates,
browser geolocation or distance ordering belong to this MVP.
