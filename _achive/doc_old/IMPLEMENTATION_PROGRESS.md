# Kindlelise Student MVP Implementation Progress

> **Archived:** retained as historical implementation evidence. Its phase states
> are no longer the current project-status source.

> **Authority:** [`docs/VERTICAL_SLICE.md`](../../docs/VERTICAL_SLICE.md) remains the
> implementation boundary. [`docs/IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md)
> defines the approved phases, dependencies, exit gates and evidence requirements.
> This document records progress only and cannot introduce or redefine work.

This supporting progress ledger is outside the 36 implementation-file maximum.
The user explicitly approved its creation on 2026-07-22 so frequently changing
status and evidence remain separate from the stable implementation plan.

## Progress summary

Update only the State and Evidence columns while implementing. Do not use this
table to introduce new work. Use the state meanings and phase-closure record from
the implementation plan, and do not mark a phase Complete until every applicable
exit-gate requirement has verified evidence.

| Phase | Outcome | State | Evidence |
| ---: | --- | --- | --- |
| 0 | Project skeleton and local configuration | Complete | [Phase 0 closure](#phase-0-closure-evidence) |
| 1 | PostgreSQL models, constraints, indexes and seed data | Complete | [Phase 1 closure](#phase-1-closure-evidence) |
| 2A | Account/profile forms, policy, services and selector | Complete | [Phase 2A closure](#phase-2a-closure-evidence) |
| 2B | Discovery/availability form, policies and selectors | Complete | [Phase 2B closure](#phase-2b-closure-evidence) |
| 2C | Plan/participation form, policies, services and selectors | Complete | [Phase 2C closure](#phase-2c-closure-evidence) |
| 2D | Conversation/message form, policy, services and selectors | Complete | [Phase 2D closure](#phase-2d-closure-evidence) |
| 2E | Block/report form, policy, services and selector | Complete | [Phase 2E closure](#phase-2e-closure-evidence) |
| 3 | Staff verification and plan approval | Complete | [Phase 3 closure](#phase-3-closure-evidence) |
| 4 | Account and profile journey | Complete | [Phase 4 closure](#phase-4-closure-evidence) and [email-auth amendment](#phase-4-email-authentication-amendment-evidence) |
| 5 | Discovery and availability | Complete | [Phase 5 closure](#phase-5-closure-evidence) |
| 6 | Plans and participation | Complete | [Phase 6 closure](#phase-6-closure-evidence) |
| 7 | Direct messaging | Complete | [Phase 7 closure](#phase-7-closure-evidence) |
| 8 | Blocking and private reporting | Complete | [Phase 8 closure](#phase-8-closure-evidence) |
| 9 | Stripe Premium | In progress | [Phase 9 partial evidence](#phase-9-partial-evidence) |
| 10 | Ollama draft editing | Complete | [Phase 10 closure](#phase-10-closure-evidence) |
| 11 | Interface, accessibility, performance and failure states | In progress | [Phase 11 partial evidence](#phase-11-partial-evidence) |
| 12 | Heroku runtime and final assessment pass | Not started | — |

### Reusable implementation-pass starter

```text
Before acting, read docs/MASTER_INSTRUCTION_PROMPT.md completely and perform its
Vertical Slice SHA-256 check. Follow its Golden Rule and every Golden
Implementation Rule explicitly for this entire pass.

Implement and test only the phase pasted below. Do not begin a dependent phase.
After every pass, update its Evidence cell with the actual commands, results and
verified work completed; never use only “done” as evidence. Mark its State
Complete only after every exit-gate requirement passes; otherwise record the
truthful current state and partial evidence.

PASS OBJECTIVE:
```

## Phase closure evidence

### Phase 0 closure evidence

```text
Commit or immutable revision:
Phase 0 mapped-file SHA-256 manifest
8c31ded9b65d21939c62db8b708f0ae09835d0e4a81fa6fce3ea61046af1acfd

The digest above is the SHA-256 of these `shasum -a 256` manifest lines in the
retained order:
d046461df51ab6bdc8a9e4452f07ccce06d268a1e89fba1eb2299ec83aa0066f  .gitignore
9dfc8e22923368cd91fcd1bc810d027935d31a8c33dd00ab51d1567f89ece159  .env.example
07c47c5a5cd7561cb3dae2d3a937000ce224cfbc0abe08a6157dadbdb06d1400  README.md
77d20b60ec86f7056889bdb0b83a3ef927fc9c3c6f5dc71c5fa4caea0864f683  manage.py
21401b9084fc5c27838510b90f7854686e7396d4490f6b5e64967e449c32cafc  pyproject.toml
e7651e74705f8f726d33613d6b789a23601dddba3b687a08b25e19ec2af017ed  config/__init__.py
2d36ca3278416779a6ed74d5ae1c39ab4b7a3fe60748b7b4796ad63b8b590fe7  config/settings.py
8a861e114066507013f75ae9509e2c11daa0f183bf24324db742c66bd18d2901  config/urls.py
ff714c9df875154fd500c54b41eec2589ee33fcc0debe84d5bda6731adb5158e  config/asgi.py
fa292dec67ccd6fc82743083ea32f19d799c809343d75febade278a4995f0e61  config/wsgi.py
861512e0fbdbee058418dc73f14188e54972a95b2ea24308de3a3c9c9197123d  kindlelise/__init__.py
e588a12facfa6b02d5bf98aa41069ad755f6387f02462c3e552d466984306697  kindlelise/apps.py
80f8a28207863462787020eedec7f05095f2b3f014d849575da5eb4315368ffa  kindlelise/migrations/__init__.py

Environment and PostgreSQL database:
Darwin 25.3.0 arm64; Python 3.12.8; Django 5.2.15; psycopg 3.3.4.
PostgreSQL is the only configured database engine. Separate POSTGRES_* settings
and a PostgreSQL DATABASE_URL with sslmode were verified without connecting.

Focused command and result:
python manage.py check && python manage.py collectstatic --noinput
Passed: zero Django issues; 127 static files present and 354 post-processed.

Full regression command and result:
Not applicable. tests/test_vertical_slice.py is first created in Phase 1.

Manual success proof:
Pinned runtime/test dependencies installed into a fresh ignored .venv with no
broken requirements. Django Admin resolves at /admin/. ASGI and WSGI applications
import successfully. Fixed area and nearby-area settings match the vertical slice.
Production deployment checks pass with DEBUG=false and environment-owned secret.

Failure/security proof:
Missing DJANGO_SECRET_KEY and a non-PostgreSQL DATABASE_URL both fail closed.
The Phase 0 mapped-file scan found no working-secret patterns. No application
route placeholder, SQLite fallback or provider call was introduced.

Known limitations:
No local psql executable was available, so no live PostgreSQL connection was
claimed. Phase 0 has no domain schema; models, migrations and regression tests
belong to Phase 1. Application routes belong to Phase 4.

Rollback or reset used/tested:
A fresh ignored .venv was built from pyproject.toml. Ignored staticfiles output
was regenerated with collectstatic; both generated locations are disposable.

Reviewer:
Codex

Date:
2026-07-22
```

### Phase 1 closure evidence

```text
Commit or immutable revision:
Phase 1 mapped-file SHA-256 manifest
d3f227595d8860c8b2e47d3bbf1d9bbfc42306994b19e1966074818543213fca

The digest above is the SHA-256 of these `shasum -a 256` manifest lines in the
retained order:
a9c91cc6eb655da95afacc9e102571d3e24ffe69aefc81e940bc8bcc8c74385a  kindlelise/models.py
c9083adda11bfc20a47c786b0dd1d1b68fb50d073f613b4a06dfe4295bcab9f8  kindlelise/migrations/0001_initial.py
c9c21fb15d92158f7574e97c6cd150f0330adecdf8ee80153966d1eccd708ac0  kindlelise/migrations/0002_seed_initial_interests.py
01583be355f297ee707813e2347b95e33a6cd74935556cd8d5efa163c082ef03  tests/conftest.py
dd180cd26601e89635141134b59c9c11c9e65b8142c729297537857462c08ac5  tests/test_vertical_slice.py

Environment and PostgreSQL database:
Darwin 25.3.0 arm64; Python 3.12.8; Django 5.2.15; psycopg 3.3.4;
PostgreSQL 17.10 (Homebrew). Both database runs used fresh isolated temporary
clusters, a PostgreSQL-only Django connection and disposable test databases.

Focused command and result:
python manage.py makemigrations --check --dry-run && python manage.py migrate
&& pytest -q tests/test_vertical_slice.py -k
"constraint or index or migration or interest"
Passed on a fresh PostgreSQL database: no model changes, all Django and
Kindlelise migrations applied, 11 tests passed and 1 was deselected.

Full regression command and result:
pytest -q tests/test_vertical_slice.py && python manage.py check
Passed: 12 tests passed; Django system check reported zero issues. A separate
python -m compileall -q config kindlelise tests command also passed.

Manual success proof:
The reviewed schema migration contains exactly the ten approved models, four
read-only helpers, all mapped uniqueness/check constraints, all eight mapped
non-unique indexes and every explicit foreign-key deletion rule. The automatic
profile-interest join table is used. The model-inventory test queries Django's
application registry, so an accidental additional model fails the assertion.
Fresh migration output contained exactly Cinema, Coffee, Food, Games, Live
music, Museums, Study and Walking.

Failure/security proof:
PostgreSQL rejected inconsistent verification, approval and participation
states, zero capacity, self/duplicate conversations, self/duplicate blocks,
self reports, reports with multiple contexts, duplicate Stripe identifiers and
duplicate webhook event IDs. Tests also proved lower-ID conversation ordering,
the four read-only helper decisions and the explicit deletion contracts. No
provider workflow, HTTP adapter, view, template or deferred entity was added.

Known limitations:
Cross-row and actor-dependent rules remain assigned to the approved policies and
services in later phases. This phase does not claim those workflows. Homebrew
PostgreSQL was installed for verification, but no persistent database service
was enabled; both temporary verification servers were stopped after testing.

Rollback or reset used/tested:
On the first fresh PostgreSQL cluster, migrate kindlelise 0001 reversed the data
migration and produced zero Interest rows. migrate kindlelise 0002 reapplied it
and restored exactly the eight approved names. The temporary server then stopped.

Reviewer:
Codex

Date:
2026-07-22
```

### Phase 2A closure evidence

```text
Commit or immutable revision:
Phase 2A mapped-file SHA-256 manifest
a283c7e680cac21fc107a562befdecd7ba072f15ffb7594a7f1e78b141387709

The digest above is the SHA-256 of these `shasum -a 256` manifest lines in the
retained order:
2bf761015abc3c76582eaf0d8cf04ba68b0070df39ba0ba63d7715ae14e46751  kindlelise/forms.py
6707febde63a5c530398235d72be337ce255eeef7b43bd1372b5ad0992a11650  kindlelise/policies.py
5fa236ab0b6805f35e72027c4073645cc0479a587eaaea231e31862fcc59005b  kindlelise/services.py
66abe29b042befcae01c3c64bd27a850ab1b062784cf6c32c73bb1dede8663c5  kindlelise/selectors.py
864b8e3e3a8afb44aae877208fe5ff93102280b8cf0effabe3cebabe92e22660  tests/test_vertical_slice.py

Environment and PostgreSQL database:
Darwin 25.3.0 arm64; Python 3.12.8; Django 5.2.15; psycopg 3.3.4;
PostgreSQL 17.10 (Homebrew). Final validation used a fresh isolated temporary
cluster, a PostgreSQL-only Django connection and a disposable test database.

Focused command and result:
.venv/bin/python manage.py makemigrations --check --dry-run &&
.venv/bin/python manage.py migrate --noinput &&
.venv/bin/pytest -q tests/test_vertical_slice.py -k "account or profile"
Passed: no model changes, all migrations applied, 9 tests passed and 11 were
deselected.

Full regression command and result:
.venv/bin/pytest -q tests/test_vertical_slice.py &&
.venv/bin/python manage.py check
Passed: all 20 tests passed and Django reported zero issues. The separate
.venv/bin/python -m compileall -q kindlelise tests command also passed.

Manual success proof:
AccountSignUpForm exposes only username, password and confirmation and uses
Django's username/password validation. ProfileDetailsForm exposes exactly five
editable fields, reloads configured stable area choices and selects existing
controlled interests. The access policy fails closed. Registration creates User
and empty unverified Profile together. Profile updates are owner-derived and
whitelisted. The account selector returns only the signed-in account's minimal
username, own profile/plans and identifier-free subscription summary.

Failure/security proof:
Tests rejected duplicate and invalid usernames, weak and mismatched passwords,
empty or oversized profile names, oversized biography, unknown area and unknown
interest. A synthetic profile-write failure rolled back the new account. Profile
updates refused anonymous, inactive and missing-profile accounts; ignored user,
verification and subscription injection fields; left another profile unchanged;
and replaced then cleared availability and interests. Policy tests denied every
missing, inactive or unverified state. Selector tests denied anonymous, inactive
and missing-profile callers and exposed no reports, webhook receipts or raw
Stripe identifiers. Username authentication succeeded while email did not.

Known limitations:
HTTP registration/sign-in/profile pages belong to Phase 4, staff verification
belongs to Phase 3 and discovery filters belong to Phase 2B. No page, admin
action, provider call or dependent-phase workflow is claimed in this phase.

Availability amendment (2026-07-27): ADR-018 replaces the raw expiry input with
an optional start choice and a derived `Free now` state. Profile completion and
staff verification do not require availability. Current implementation evidence
is recorded with the Phase 5/runtime amendment below; the historical commands in
this closure remain the evidence actually run at the time.

Rollback or reset used/tested:
No schema change was introduced, so migration reversal was not applicable. The
required registration rollback was exercised by forcing Profile creation to fail;
the enclosing transaction left neither the account nor profile. The temporary
PostgreSQL server was stopped after validation.

Reviewer:
Codex

Date:
2026-07-22
```

### Phase 2B closure evidence

```text
Commit or immutable revision:
Phase 2B mapped-file SHA-256 manifest
7deb51d5146a2ae445e94b25dd8aa57ba7582c3309be29a0ab57c67584c8b4cc

The digest above is the SHA-256 of these `shasum -a 256` manifest lines in the
retained order:
443f8c6d17d8a1a19265a1e384ec728ae6c5508576b073e760e652fab58e9301  kindlelise/forms.py
a0446f0c5e5787fe230849231e9d46369a4c4bf1a7ba1ad4bcba73290507ccf3  kindlelise/policies.py
ac4c27fe3cc7737ca3fb9e01e406852262792e9ddaa66eda6933d63dd0b1bc93  kindlelise/selectors.py
6f9ec7d68bd8a79fde07e556c05b47e3c742fbdb3c7a85d1b75dc7ac77e1aa99  tests/test_vertical_slice.py

Environment and PostgreSQL database:
Darwin 25.3.0 arm64; Python 3.12.8; Django 5.2.15; psycopg 3.3.4;
PostgreSQL 17.10 (Homebrew). Final validation used a fresh isolated temporary
cluster, a PostgreSQL-only Django connection and a disposable test database.

Focused command and result:
.venv/bin/python manage.py makemigrations --check --dry-run &&
.venv/bin/python manage.py migrate --noinput &&
.venv/bin/pytest -q tests/test_vertical_slice.py -k
"discovery or availability or premium_limit"
Passed: no model changes, all migrations applied, 5 tests passed and 19 were
deselected.

Full regression command and result:
.venv/bin/pytest -q tests/test_vertical_slice.py &&
.venv/bin/python manage.py check
Passed: all 24 tests passed and Django reported zero issues. The separate
.venv/bin/python -m compileall -q kindlelise tests command also passed.

Manual success proof:
DiscoveryFiltersForm accepts only server-calculated area choices, existing
controlled interests and the optional available-now flag, enforcing the current
Free or Premium interest limit. The policies derive Free current-area/two-filter
and Premium configured-nearby/five-filter access without bypassing eligibility
or blocks. Discovery selectors return ordered, prefiltered profiles and use the
same no-result outcome for missing or refused profile-page targets.

Failure/security proof:
Tests rejected unknown areas/interests, a Free nearby-area request and excessive
Free or Premium interests before selection. Selectors rechecked a now-expired
Premium projection and refused its previously valid nearby-area filter. Discovery
excluded self, inactive and unverified accounts, wrong areas/interests, expired
or missing availability when requested, and blocks in both directions. Direct
profile lookup returned the same None result for missing, inactive, unverified,
blocked and ineligible-viewer cases. Premium never weakened these exclusions.

Known limitations:
The discovery HTTP page and rendering belong to Phase 5. Stripe projection
updates belong to Phase 9; this phase reads only the existing local projection.
No view, template, provider call, pagination or dependent-phase workflow is
claimed here.

Rollback or reset used/tested:
This phase is read-only and introduced no schema migration, so application-data
rollback and migration reversal were not applicable. The disposable PostgreSQL
database was recreated from migrations, and the temporary server was stopped
after validation.

Reviewer:
Codex

Date:
2026-07-22
```

### Phase 2C closure evidence

```text
Commit or immutable revision:
Phase 2C mapped-file SHA-256 manifest
277b2f6c21e82816e6b1eaecd56678c478e99702e53c84525992b76bad453e5a

The digest above is the SHA-256 of these `shasum -a 256` manifest lines in the
retained order:
3a8ef137c6e418bcac0bc2e38d3bb2ccc3a14d0896a2bcf2f071864a85b20607  kindlelise/forms.py
70e7f83c36da148f1d3be8d7b166a80ced64e452d996ea50722760cd3f179b9b  kindlelise/policies.py
707b408359d3cd90c4f461965fedd3ad8ee97a0a8c9d3fa397e31d49dcd9d057  kindlelise/services.py
95b033b26786e6285c3607fdb06de3f694d7c2fb0ff68eb7396a8b10803d9349  kindlelise/selectors.py
e1da48187cbb38b4693f180eaf1afcbda4ec6b0ef8233e65b80edbc0beb2d66e  tests/test_vertical_slice.py

Environment and PostgreSQL database:
Darwin 25.3.0 arm64; Python 3.12.8; Django 5.2.15; psycopg 3.3.4;
PostgreSQL 17.10 (Homebrew). Final validation used a fresh isolated temporary
cluster, a PostgreSQL-only Django connection and disposable test databases.

Focused command and result:
.venv/bin/python manage.py makemigrations --check --dry-run &&
.venv/bin/python manage.py migrate --noinput &&
.venv/bin/pytest -q tests/test_vertical_slice.py -k
"plan or participation or capacity or join or leave or cancel"
Passed: no model changes, all migrations applied, 15 tests passed and 22 were
deselected. The TransactionTestCase used two separate PostgreSQL connections;
exactly one concurrent final-capacity join succeeded and one was refused.

Full regression command and result:
.venv/bin/pytest -q tests/test_vertical_slice.py &&
.venv/bin/python manage.py check
Passed cleanly: all 37 tests passed and Django reported zero issues. Separate
.venv/bin/python -m compileall -q kindlelise tests and pytest --collect-only -q
commands also passed, collecting exactly 37 tests.

Manual success proof:
PlanDetailsForm exposes only six bounded plan fields, requires a future time and
HTTPS URL, and performs no remote fetch. Creation forces pending unapproved
state. Owner edits lock and recheck current state; changes to each of public
place, public URL and start time reset approval, every saved rejected plan is
resubmitted, and first join makes all edits read-only. Join locks and recounts
the plan in one transaction, creates or reactivates one participation, refreshes
join history and preserves the first lock. Leave and cancellation retain
historical rows. Selectors expose
only approved future plans or owner-only states and return counts/own state
without a participant directory.

Failure/security proof:
Tests rejected invalid content bounds, non-HTTPS evidence, past time and zero
capacity. Creation ignored injected owner, status, approval and lock fields.
Unverified users and non-owners were refused; locked and cancelled plans could
not be edited; owners, past/unapproved/cancelled/full plans and current members
could not join. Leave refused an outsider, an unverified participant and an
inactive participant while preserving both joined rows, null departure times
and the plan lock. Cancellation refused a non-owner and an unverified owner
without changing plan or participation state; successful cancellation remained
terminal, hid public access and preserved the plan, lock and participations.
Missing/hidden plan lookup used one no-result outcome, and another owner's
private states never entered list results.

Known limitations:
Staff approval belongs to Phase 3 and the plan HTTP journey belongs to Phase 6.
This phase adds no view, URL, template, admin action, remote-provider call or
dependent-phase workflow. A public HTTPS URL remains staff-reviewed evidence,
not a claim that the venue is safe or that the remote page is immutable.

Rollback or reset used/tested:
No schema change was introduced, so migration reversal was not applicable. All
five state-changing services run atomically; refusal tests confirmed no partial
edit or extra participation, and the live concurrency test confirmed no
capacity overrun. Worker connections and the disposable PostgreSQL server were
closed after validation.

Reviewer:
Codex

Date:
2026-07-22
```

### Phase 2D closure evidence

```text
Commit or immutable revision:
Phase 2D mapped-file SHA-256 manifest
e10613be77ee340062439586d9d4a23bdc9f5d25e910c21816414777e9bd09e8

The digest above is the SHA-256 of these `shasum -a 256` manifest lines in the
retained order:
6e504c7d4a97609e81d860d95624b6ccc6849549c205e65ad0a15253cdd6f866  kindlelise/forms.py
d83df386c98d137fd6b8ae02f55dc8be68cf8a0b884e3bbeeb481b6f4e793962  kindlelise/policies.py
374ba716a6a6c9cf02cabfb3f84df151c3f5161dc229f0aa960166d461102c21  kindlelise/services.py
0bf0e55910c0152ce2b52f72ac95477e2a4f544b0e5db27dcb3e81ab2e86e003  kindlelise/selectors.py
a480dda678fcc09c242434201bd97ba79fff6490cfe0c8e1fbc16d9972fa231d  tests/test_vertical_slice.py

Environment and PostgreSQL database:
Darwin 25.3.0 arm64; Python 3.12.8; Django 5.2.15; psycopg 3.3.4;
PostgreSQL 17.10 (Homebrew). Final validation used a fresh isolated temporary
cluster, a PostgreSQL-only Django connection and disposable test databases.

Focused command and result:
.venv/bin/python manage.py makemigrations --check --dry-run &&
.venv/bin/python manage.py migrate --noinput &&
.venv/bin/pytest -q tests/test_vertical_slice.py -k "conversation or message"
Passed: no model changes, all migrations applied, 10 tests passed and 36 were
deselected. The TransactionTestCase used two separate PostgreSQL connections;
both simultaneous starts returned the same single ordered conversation row.

Full regression command and result:
.venv/bin/pytest -q tests/test_vertical_slice.py &&
.venv/bin/python manage.py check
Passed cleanly: all 46 tests passed and Django reported zero issues. Separate
.venv/bin/python -m compileall -q kindlelise tests and pytest --collect-only -q
commands also passed, collecting exactly 46 tests.

Manual success proof:
MessageDraftForm exposes one stripped plain-text field and enforces the 1,000-
character bound. The policy requires two distinct active verified accounts with
no block in either direction. Conversation creation stores the lower account ID
first, returns an existing pair after a uniqueness conflict and survives a real
simultaneous-start race. Sending reloads and locks the conversation, rechecks
membership and current pair permission, stores unmarked plain text and updates
recent activity atomically. The inbox returns only the signed-in member's current
permitted pairs in activity order. Conversation detail returns chronological
messages only after the same eligibility, membership and block checks.

Failure/security proof:
Tests rejected empty and oversized drafts; self, anonymous, inactive, unverified
and either-direction-blocked messaging pairs; and conversation creation for every
refused pair without adding a row. Message sending refused an outsider and
current unverified, inactive or blocked pair without storing text or changing
the activity time. A forced activity-update failure rolled back the preceding
message insert. Inbox selection removed unrelated, blocked, inactive and
unverified pairs before presentation. Missing, non-member and later-blocked
conversation reads all returned the same no-result outcome. HTML-like text stayed
ordinary stored text and was escaped only at the demonstrated rendering boundary.

Known limitations:
The inbox/conversation HTTP journey and templates belong to Phase 7. The mapped
block mutation belongs to Phase 2E and Ollama draft editing belongs to Phase 10.
This phase adds no route, view, template, provider call, group/live messaging,
attachment, reaction, read receipt or dependent-phase workflow.

Rollback or reset used/tested:
No schema change was introduced, so migration reversal was not applicable. The
conversation uniqueness conflict rolled back its failed insert before retrieving
the authoritative pair. A synthetic second-write failure proved message and
activity updates roll back together. Worker connections and the disposable
PostgreSQL server were closed after validation.

Reviewer:
Codex

Date:
2026-07-22
```

### Phase 2E closure evidence

```text
Commit or immutable revision:
Phase 2E mapped-file SHA-256 manifest
9efc881265771df16c30f8d594c6093e71e94184a653bab1ae52ffd9269e9868

The digest above is the SHA-256 of these `shasum -a 256` manifest lines in the
retained order:
ed1d8acff09bb52da215790dfc190d45fa62e8d16413be88288b1e42ef3b305d  kindlelise/forms.py
442386afd6a50b08dcea53133004ba758229364bca91cdd623a90dda659f3d2c  kindlelise/policies.py
4a1bf995683bc7d7f552a69b0a475b7aea4ec8835223d4b68df6f144ad0affb2  kindlelise/services.py
03918369124e47028c6dbe3580dd3588760d8f9af82f77c18959fbfb4ca7166e  kindlelise/selectors.py
4a9c6efcb4a5daeeefe4ebe390dafa5362b9fd3d3bc4296efeddabb9a5468f7a  tests/test_vertical_slice.py

Environment and PostgreSQL database:
Darwin arm64; Python 3.12.8; Django 5.2.15; psycopg 3.3.4;
PostgreSQL 17.10 (Homebrew). Final validation used a fresh isolated temporary
cluster, a PostgreSQL-only Django connection and disposable test databases.

Focused command and result:
.venv/bin/python manage.py makemigrations --check --dry-run;
.venv/bin/python manage.py migrate --noinput;
.venv/bin/pytest -q tests/test_vertical_slice.py -k "block or report"
Passed: no model changes, all migrations applied, 10 tests passed and 43 were
deselected.

Full regression command and result:
.venv/bin/pytest -q tests/test_vertical_slice.py &&
.venv/bin/python manage.py check
Passed cleanly: all 53 tests passed and Django reported zero issues. Separate
.venv/bin/python -m compileall -q kindlelise tests and pytest --collect-only -q
commands also passed, collecting exactly 53 tests.

Manual success proof:
PrivateReportForm exposes only category and description and enforces the mapped
choices and 2,000-character bound. The report policy permits an authenticated
account to report a different account even after either-direction blocking. The
block service is idempotent and immediately closes discovery, profile and both
directions of direct-message access. The report-target selector still resolves a
different target after a block without exposing a report or denial reason. The
report service stores received, server-owned reports with zero or one validated
plan, conversation or message reference and forces reporter, target and status.

Failure/security proof:
Tests rejected empty, oversized and unknown report form values; anonymous and
self block/report attempts; missing block targets; missing and self report-target
profiles; multiple report contexts; and plan, conversation and message contexts
unrelated to the reported account. Every refusal left Block or Report counts
unchanged. Tests also proved repeated blocks create one row, browser-style
authority injection is ignored, blocked users cannot read names or messages, and
the reported user's account summary exposes no report data.

Known limitations:
Block/report HTTP routes, templates and submission confirmation belong to Phase
8. Staff report visibility belongs to Phase 3. This phase adds no view, URL,
template, notification, unblock workflow, finding, sanction or moderation system.

Rollback or reset used/tested:
No schema change was introduced, so migration reversal was not applicable. A
fresh database was migrated from zero; invalid-context and permission refusals
proved no partial Block or Report write. The disposable PostgreSQL server was
stopped after validation.

Reviewer:
Codex

Date:
2026-07-27
```

### Phase 4 email-authentication amendment evidence

```text
Approved boundary change:
On 2026-07-27 the user explicitly replaced public username registration/sign-in
with email and password. ADR-017 records the requirement, smallest design,
privacy/security consequences and rejected alternatives. The authoritative
vertical-slice SHA-256 is now
ee1df331b6a965f8481a5530d867406de3199bbd935b1db23a4be17e32448e37,
and the Master Instruction Prompt is synchronized to that exact revision.

Changed-owner SHA-256 manifest:
81a4b62cbd409f6d3dc7bd231210a87d625977c8208a0ef451ea818829b3446b

The digest above is the SHA-256 of these manifest lines in retained order:
370beb618e60f30a2e9261725b85fba703698e51e0d286bf7fc86d575e0afec5  kindlelise/forms.py
f9d8fff2b1589b16858fb919049a0259df87e58a4c598f6582486978a7596b04  kindlelise/services.py
d57af817a7dda421804c4ebd3c9c167d39792ca86f8f3f620303ebe5149f2d3f  kindlelise/selectors.py
a4da6e5284907d691afda1c12e1908c5564e124b857ad237e4ac96123e7f07c3  kindlelise/views.py
a1fdeeb41e7a9f07be185ec93581d8f5eda172dc8cf76b7991b06626d8ebd91b  templates/account.html
a027d2d8bbb5378fb9662bbb5145b04984f704eb878616f6235e158f461f814c  tests/test_vertical_slice.py
ee1df331b6a965f8481a5530d867406de3199bbd935b1db23a4be17e32448e37  docs/VERTICAL_SLICE.md
5d7001de42d2415d1e8ce4323c03d7595d8d65715945db64194546c6a905b0dc  docs/DECISIONS.md
3b6907944e3c233567717cdba67d03f5abc5869520968c22e078cb0a466473d8  docs/MASTER_INSTRUCTION_PROMPT.md

Implementation result:
AccountSignUpForm now accepts one valid email and Django-validated password pair,
canonicalises the complete email to lowercase and rejects case-variant
duplicates. create_account_and_profile() stores the same canonical value in
Django's unique username field and email field while atomically creating the
unverified Profile. The existing AuthenticationForm is labelled Email and its
submitted credential is canonicalised before normal Django authentication. The
private account summary/page displays Email. No custom User model, authentication
backend, route, dependency or schema migration was added. Stripe ownership still
uses immutable local IDs and existing unique Stripe-ID links, never email.

Focused command and result:
.venv/bin/pytest -q tests/test_vertical_slice.py -k
"account_sign_up or registration_http or sign_in_http or
duplicate_or_invalid_account or account_and_profile_creation or account_summary"
Passed on PostgreSQL: 6 tests passed and 97 were deselected.

Full regression and checks:
.venv/bin/pytest -q
Passed on PostgreSQL: all 103 tests passed in 78.89 seconds.
`manage.py makemigrations --check --dry-run` reported no changes;
`manage.py check`, compileall and git diff --check passed. A localhost smoke GET
to the restarted app returned 200 and confirmed the Email-labelled sign-in field.

Runtime demonstration:
The disposable verified demo account was updated to demo@kindlelise.test with the
existing test-only password, and the Django development server was restarted on
http://127.0.0.1:8000/. This is synthetic local data only.

Reviewer:
Codex

Date:
2026-07-27
```

### Phase 3 closure evidence

```text
Commit or immutable revision:
Phase 3 mapped-file SHA-256 manifest
463f229ee0aeb7a0f977f22711aa235d5b2dd6aa3e1e92683df7ac266df23b84

The digest above is the SHA-256 of these `shasum -a 256` manifest lines in the
retained order:
5bee513eebe88370db52dcfa8bae5ff71b377216f318698bcb11c21fc5413c3c  kindlelise/admin.py
6aec6270a602912429e49959b92520061401ce0e83d8b0b1d71c1ca4d551fc21  tests/test_vertical_slice.py

Environment and PostgreSQL database:
Darwin arm64; Python 3.12.8; Django 5.2.15; psycopg 3.3.4;
PostgreSQL 17.10 (Homebrew). Final validation used a fresh isolated temporary
cluster, a PostgreSQL-only Django connection and disposable test databases.

Focused command and result:
.venv/bin/python manage.py makemigrations --check --dry-run;
.venv/bin/python manage.py migrate --noinput;
.venv/bin/pytest -q tests/test_vertical_slice.py -k
"admin or staff or verification or approval"
Passed: no model changes, all migrations applied, 12 tests passed and 47 were
deselected.

Full regression command and result:
.venv/bin/pytest -q tests/test_vertical_slice.py &&
.venv/bin/python manage.py check
Passed cleanly: all 59 tests passed and Django reported zero issues. Separate
.venv/bin/python -m compileall -q kindlelise tests and pytest --collect-only -q
commands also passed, collecting exactly 59 tests.

Manual success proof:
All ten approved Kindlelise models are registered with ordinary Django Admin.
Profile and Plan review fields are read-only in forms and change only through the
four mapped actions. Each action requires normal Django change permission, locks
and rechecks selected rows, changes eligible rows individually and reports exact
changed/skipped counts. Verification records staff/time only for complete profiles
with configured areas. Removal clears all verification fields without deleting
records. Approval records staff/time only for pending future unlocked plans after
the named manual URL check; rejection changes only pending unlocked plans.

Failure/security proof:
Tests refused non-staff accounts and staff accounts without Django change
permission before mutation. Verification skipped empty or whitespace-only names,
unknown broad areas and already verified rows. Approval skipped past, locked,
cancelled, rejected, already approved, non-HTTPS and empty-place plans. Rejection
skipped locked and every non-pending state while correctly allowing pending past
plans to be rejected. Existing reviewer/time values, plans and profile records
remained unchanged on skipped or refused paths. Provider projections and webhook
receipt identity are staff-visible but read-only; report statements are not
rewritable through their admin form.

Known limitations:
This phase exposes only ordinary Django Admin controls. The account/profile HTTP
journey belongs to Phase 4 and plan pages belong to Phase 6. Staff still inspect
the submitted public URL manually outside Kindlelise; approval stores no webpage,
substantiation, private review note, identity claim or venue-safety guarantee.

Rollback or reset used/tested:
No schema change was introduced, so migration reversal was not applicable. A
fresh database was migrated from zero; permission and ineligible-state tests
proved no partial profile or plan transition. The disposable PostgreSQL server
was stopped after validation.

Reviewer:
Codex

Date:
2026-07-27
```

Phase 3 User-admin verification amendment (2026-07-27): ADR-019 adds a
`Profile verified` checkbox to Django's User change Permissions section while
retaining the Profile bulk actions. The control is omitted unless the staff
account has Profile change permission, and forged submission without that
permission is ignored. Checking a complete profile records reviewer/time;
unchecking clears all verification fields; incomplete profiles receive a bound
form error. Focused PostgreSQL evidence passed 6 tests with 105 deselected. The
full regression passed 111 tests in 80.07 seconds. No model, migration, route,
dependency or implementation file was added.

### Phase 4 closure evidence

```text
Commit or immutable revision:
Phase 4 mapped-file SHA-256 manifest
53a04f6deedf9400ae34b1d437c6d625cea07fdf342dd51f8ca6d03b5d011ee0

The digest above is the SHA-256 of these `shasum -a 256` manifest lines in the
retained order:
d017b3b22e896fbd92572ab1d3273ebb8a94b50df438655424d094808644b841  kindlelise/views.py
cec0d85af602a0d4b8e71f195b53aa49f1ae1ef105560fe7e1ad5537089cf96c  kindlelise/urls.py
e34b5427470f424255d24f55e3d992ad5248c2091093a677050d78c0e755438e  config/urls.py
c228b4870cb89599434ebb6070f3d81cc76a10e755501b3d90ae02e721040342  templates/base.html
df129e899368d69c2c6c21e2785c936e6eebd0077e2d3990675b9857713bdd62  templates/account.html
cbae2c3f8b8879ae4a4f6cc4ddc6fecbaa0bca37874d33f501fee98c13a3a40b  static/app.css
ff22f2a1b71d42df0d5e96039ad315348f64099572830ddc24157c60767d80f1  tests/test_vertical_slice.py

Environment and PostgreSQL database:
Darwin arm64; Python 3.12.8; Django 5.2.15; psycopg 3.3.4;
PostgreSQL 17.10 (Homebrew). Final validation used a fresh isolated temporary
cluster, a PostgreSQL-only Django connection and disposable test databases.

Focused command and result:
.venv/bin/python manage.py makemigrations --check --dry-run;
.venv/bin/python manage.py migrate --noinput;
.venv/bin/python manage.py collectstatic --noinput;
.venv/bin/pytest -q tests/test_vertical_slice.py -k
"registration or sign_in or sign_out or account or profile"
Passed: no model changes, all migrations applied, one new static source was
collected and 357 assets were post-processed, then 20 tests passed and 45 were
deselected. The first focused attempt exposed a stale WhiteNoise manifest and
failed five renders at the shared static lookup; rebuilding collected assets and
rerunning the unchanged HTTP tests resolved all five failures.

Full regression command and result:
.venv/bin/pytest -q tests/test_vertical_slice.py &&
.venv/bin/python manage.py check
Passed cleanly: all 65 tests passed and Django reported zero issues. Separate
.venv/bin/python -m compileall -q config kindlelise tests, git diff --check and
pytest --collect-only -q commands also passed, collecting exactly 65 tests.

Manual success proof:
The six Phase 4 route owners render through the shared accessible account shell.
Registration accepts username/password only, creates the atomic unverified pair
and leaves the browser anonymous. Django sign-in rotates the session, retains a
safe same-site destination and refuses an external destination. The home route
redirects anonymous, active unverified and active verified states to sign-in,
private account and the approved local discovery destination respectively. The
private account shows only the selector-owned account/profile/plan/subscription
summary and explains unverified state without making an identity or safety claim.
Profile editing binds the five mapped fields and supports setting, replacing and
clearing availability. Sign-out is presented only as a POST form with CSRF.

Failure/security proof:
HTTP tests proved mismatched registration creates neither account nor profile;
unknown usernames and correct credentials for inactive accounts receive the same
generic sign-in error; external `next` values return to the local home route; an
anonymous private-page request redirects to named sign-in; another profile and
reports/provider identifiers do not enter the account response; injected owner,
verification and Stripe fields do not change authority; and another profile
remains unchanged. GET sign-out returned 405, missing-CSRF POST returned 403 and
left the authenticated session intact, and valid-CSRF POST ended authentication.

Known limitations:
The discovery route/page and four-destination primary navigation belong to Phase
5 and later page phases. This phase proves only the verified home redirect to the
approved local `/discover/` destination; it does not implement or claim the
destination page. Plan actions and Premium provider controls likewise remain in
their mapped later phases. The interface remains for supervised test accounts and
does not implement age or identity verification.

Rollback or reset used/tested:
No schema change was introduced, so migration reversal was not applicable. The
ignored collected-static output was safely regenerated after its stale manifest
was detected. Invalid registration/profile submissions and refused authentication
or CSRF requests preserved account, profile and session state as mapped. The
disposable PostgreSQL server was stopped after validation.

Reviewer:
Codex

Date:
2026-07-27
```

### Phase 5 closure evidence

```text
Commit or immutable revision:
Phase 5 mapped-file SHA-256 manifest
a53bf1a31f6600f0f8d4a476c70ab83058af8d082b98e1efbe9beaf9af3d29cc

The digest above is the SHA-256 of these `shasum -a 256` manifest lines in the
retained order:
fd54b8e24c724c90bf64c72c252d9b333041d86988fe9b8d152e5f4b384bcaac  templates/discover.html
79f6c637229bd233d9bb68e2acda6bc7ffd0958cfad606aca9afa7bfb85a28fd  templates/account.html
ed1d8acff09bb52da215790dfc190d45fa62e8d16413be88288b1e42ef3b305d  kindlelise/forms.py
442386afd6a50b08dcea53133004ba758229364bca91cdd623a90dda659f3d2c  kindlelise/policies.py
03918369124e47028c6dbe3580dd3588760d8f9af82f77c18959fbfb4ca7166e  kindlelise/selectors.py
2495c89817f5863eb14333d86d77f8bf24f2272743f8ede23d45e3dbae86954e  kindlelise/views.py
3f75426b03d927e81e3857b5ff5b0125984e67efe1749f3e58a148b3323fb0e0  kindlelise/urls.py
559e1878fb84b21e961843be240476db2131b8c3e581f2b4a4a21b02a504df14  tests/test_vertical_slice.py

Environment and PostgreSQL database:
Darwin arm64; Python 3.12.8; Django 5.2.15; psycopg 3.3.4;
PostgreSQL 17.10 (Homebrew). Final validation used a fresh isolated temporary
cluster, a PostgreSQL-only Django connection and disposable test databases.

Focused command and result:
.venv/bin/python manage.py makemigrations --check --dry-run;
.venv/bin/python manage.py migrate --noinput;
.venv/bin/pytest -q tests/test_vertical_slice.py -k
"discovery or availability or premium_limit"
Passed: no model changes, all migrations applied, 11 tests passed and 58 were
deselected.

Full regression command and result:
.venv/bin/pytest -q tests/test_vertical_slice.py &&
.venv/bin/python manage.py check
Passed cleanly: all 69 tests passed and Django reported zero issues. Separate
.venv/bin/python -m compileall -q config kindlelise tests, git diff --check and
pytest --collect-only -q commands also passed, collecting exactly 69 tests.

Manual success proof:
The named discovery route defaults to the verified account's configured current
area and binds only the mapped broad-area, controlled-interest and available-now
filters. Free presentation permits one current area and two interests; a current
Premium projection permits configured nearby areas and five interests. Only the
selector-returned profiles become cards, with broad-area labels, escaped display
text, controlled interests and derived current availability. The named profile
route uses the authorised selector and the existing authoritative account-template
public mode to show only display name, broad area, interests, biography and the
derived availability decision. The home redirect now reverses the implemented
named discovery route rather than its Phase 4 provisional local path.

Failure/security proof:
HTTP tests redirected anonymous discovery requests to named sign-in and
unverified requests to the private account with one generic verification-needed
message. POST received 405 on both read-only routes. Free nearby-area and
three-interest requests produced bound errors and no profiles; Premium accepted a
configured nearby area with five interests and rejected six. The original
expiry-based availability proof was superseded by the ADR-018 amendment below.
Rendered discovery excluded self, inactive, unverified, wrong-area and both
directions of block before presentation. Missing, inactive, unverified and both
blocked target directions returned exactly the same 404 body. Public biography
HTML was escaped, and login username plus Stripe identifier never entered the
profile response. No exact coordinates, distance value, exclusion reason or
hidden-result count was rendered.

Known limitations:
Direct-message, block and report actions on the public profile belong to Phases 7
and 8 and are not prematurely linked to absent routes. `account.html` is included
in this manifest because the authoritative vertical-slice template contract owns
the public-profile mode even though the supporting Phase 5 file list omitted it.
Stripe event updates remain Phase 9; discovery reads only the already-approved
local projection. Broader visual polish and four-destination navigation remain
Phase 11.

Rollback or reset used/tested:
Phase 5 is read-only and introduced no schema migration, so application-data
rollback and migration reversal were not applicable. Invalid filters, eligibility
failures and hidden-profile requests changed no records. The disposable
PostgreSQL server was stopped after validation.

Reviewer:
Codex

Date:
2026-07-27
```

Phase 5 availability amendment (2026-07-27): the approved ADR-018 change replaced
the raw expiry input with a profile-side `Free now` switch, optional Today,
Tomorrow, This week and As and when start choices, plus a visible `Free now`
discovery switch. Migration
`0003_profile_availability_start` cleared legacy expiry values before renaming
the timestamp and adding the start-choice consistency constraint. Focused
PostgreSQL evidence passed 9 tests with 99 deselected; the full regression passed
108 tests in 78.12 seconds. `manage.py makemigrations --check --dry-run`, Django
system checks, compileall and `git diff --check` also passed. The development
database migration applied successfully and the local server was restarted.

### Phase 6 closure evidence

```text
Commit or immutable revision:
Phase 6 mapped-file SHA-256 manifest
c0f79005f47d71fd2fb12a39fae4ef0e09ed7c7c7ad111e8aebb5a8993c39817

The digest above is the SHA-256 of these `shasum -a 256` manifest lines in the
retained order:
3fb1121e3d9a6274a67bba866805ea51b72c4389d18e7ccc58709c228dd59289  templates/plan.html
ed1d8acff09bb52da215790dfc190d45fa62e8d16413be88288b1e42ef3b305d  kindlelise/forms.py
581130ac31cb92477d79a918f67e6e954cfbdc4cada9f8405dc5c12e8d95283f  kindlelise/policies.py
f56952810f409c8017013b25e9652f57560060f362d4d8731e615996968833a1  kindlelise/services.py
03918369124e47028c6dbe3580dd3588760d8f9af82f77c18959fbfb4ca7166e  kindlelise/selectors.py
c3dff7e04be5f089624e2344232ac978b767797d47d81a0086b194a34c0d1a2b  kindlelise/views.py
a19884adbc83870fb3b8c33d8585c0155bdc7f1cb2f1871f3aedfd926ebe64ce  kindlelise/urls.py
5d5fc6ce748150abc204022335a4290e2c27b4e6a1f1373e6dbcfe6f9317acce  tests/test_vertical_slice.py

Environment and PostgreSQL database:
Darwin arm64; Python 3.12.8; Django 5.2.15; psycopg 3.3.4;
PostgreSQL 17.10 (Homebrew). Final validation used a fresh isolated temporary
cluster, a PostgreSQL-only Django connection and disposable test databases.

Focused command and result:
.venv/bin/python manage.py makemigrations --check --dry-run;
.venv/bin/python manage.py migrate --noinput;
.venv/bin/pytest -q tests/test_vertical_slice.py -k
"plan or participation or capacity or join or leave or cancel"
Passed: no model changes, all migrations applied from zero, then 24 tests passed
and 51 were deselected. The retained TransactionTestCase used separate PostgreSQL
connections and proved that simultaneous final-slot joins create exactly one
joined participation without exceeding capacity. Two preliminary browser-test
runs exposed and corrected a genuine unchanged-datetime microsecond comparison
edge case, then corrected the test fixture to submit Django's rendered London
local time; the final focused gate above was reproduced cleanly.

Full regression command and result:
.venv/bin/pytest -q && .venv/bin/python manage.py check
Passed cleanly on PostgreSQL: all 75 tests passed and Django reported zero issues.
Separate compileall, git diff --check, PostgreSQL migration-drift and pytest
--collect-only commands passed, collecting exactly 75 tests.

Manual success proof:
Seven named plan routes now provide the mapped list, create, detail, edit, join,
leave and cancel journey through one plan template. A verified owner creates only
a pending plan; own pending, rejected and cancelled states remain private while
approved future plans are list-visible. Before the first join, title, description
and capacity edits preserve approval, a genuine public place, URL or start-time
change clears review evidence and returns the plan to pending, and any rejected
edit resubmits pending. Detail presentation shows the public owner display name,
place, time, joined count, capacity and only the viewer's participation state.
The first non-owner join permanently locks meeting details. Leave changes the
same participation to historical left state, rejoin reuses that row, and owner
cancellation is terminal while retaining the plan, lock and participations.

Failure/security proof:
HTTP tests redirected anonymous and currently unverified accounts through the
approved generic paths and proved durable access rechecking after staff removes
verification, even when a request-side profile relation was cached. Browser
owner, approval, status and lock injection was ignored. Invalid non-HTTPS plan
input wrote nothing. Missing, hidden, non-owner, locked and cancelled object
edits shared the same 404 body. Read routes rejected POST, mutation routes rejected
GET, and a join without CSRF returned 403 without a participation write. Owners,
already-joined accounts, full plans and ineligible states were refused without
capacity or history corruption. Participant usernames and directories never
entered plan detail responses.

Known limitations:
Plan report actions belong to Phase 8 and are not prematurely linked. Direct
messaging belongs to Phase 7, Stripe controls to Phase 9 and broader interface
polish/navigation to Phase 11. Staff still inspect submitted HTTPS URLs manually
outside Kindlelise; the page explains that approval neither preserves the remote
webpage nor proves venue safety or future URL immutability.

Rollback or reset used/tested:
No schema change was introduced, so migration reversal was not applicable. All
plan mutations use the existing atomic services; refusal and concurrency tests
proved no partial edit, duplicate participation or capacity overrun. The
disposable PostgreSQL server was stopped after validation.

Reviewer:
Codex

Date:
2026-07-27
```

### Phase 7 closure evidence

```text
Commit or immutable revision:
Phase 7 mapped-file SHA-256 manifest
08deffa072961853be0545102f9f033c6cd4494eb54431f92734f27fffbca346

The digest above is the SHA-256 of these `shasum -a 256` manifest lines in the
retained order:
3ac173998ad7874df4ac04dea75c4db523089f431aefd21818cb73a8c01052df  templates/inbox.html
46ed529f645a88e6f1b44e04c51dbc52f47c1fac8b5b9f27be6ffc9a6576c41d  templates/conversation.html
f9a9e5988bfeafd86ee060e99ba2ad537f5a26e16ca8d049d761625a51c6960b  templates/account.html
ed1d8acff09bb52da215790dfc190d45fa62e8d16413be88288b1e42ef3b305d  kindlelise/forms.py
581130ac31cb92477d79a918f67e6e954cfbdc4cada9f8405dc5c12e8d95283f  kindlelise/policies.py
f56952810f409c8017013b25e9652f57560060f362d4d8731e615996968833a1  kindlelise/services.py
7835055c0f12fd8eacd666ad379f5f273aa0f0e06ecab20a3384c0a0f9cd30e0  kindlelise/selectors.py
20ece6268ed79043ee76aa29730071ed824346e547e87153211d4dfb3627a99d  kindlelise/views.py
149717e33cdb9812a98454964e664efac99c6358904fb70064c737f60d1a583a  kindlelise/urls.py
85466858c08f15a8aa31abc68c2fc5c06a513c10b465e60177c9c6f390573e14  tests/test_vertical_slice.py

`templates/account.html` is included because the authoritative vertical-slice
profile-page contract owns the Message action that begins this Phase 7 journey,
although the supporting implementation-plan file list omitted that mapped owner.

Environment and PostgreSQL database:
Darwin arm64; Python 3.12.8; Django 5.2.15; psycopg 3.3.4;
PostgreSQL 17.10 (Homebrew). Final validation used a fresh isolated temporary
cluster, a PostgreSQL-only Django connection and disposable test databases.

Focused command and result:
.venv/bin/python manage.py makemigrations --check --dry-run;
.venv/bin/python manage.py migrate --noinput;
.venv/bin/pytest -q tests/test_vertical_slice.py -k
"conversation or message"
Passed: no model changes, all migrations applied from zero, then 14 tests passed
and 65 were deselected. The retained TransactionTestCase used separate PostgreSQL
connections and proved simultaneous starts return one database-authoritative
ordered conversation. The inbox selector proof also accessed both member profile
names in exactly two queries regardless of conversation count.

Full regression command and result:
.venv/bin/pytest -q && .venv/bin/python manage.py check
Passed cleanly on PostgreSQL: all 79 tests passed and Django reported zero issues.
Separate compileall, git diff --check and pytest --collect-only commands passed,
collecting exactly 79 tests.

Manual success proof:
A permitted public profile now presents a CSRF-protected Message action. Its POST
route starts or returns the pair's one lower-ID-first conversation and redirects
to the named conversation detail. The private inbox lists only selector-returned
pairs in recent-activity order, with the other account's authorised display name
and no message preview. Conversation detail shows the other display name and
chronological plain-text messages. Its ordinary form sends a bounded draft without
JavaScript, uses the authenticated session as sender, updates recent activity and
redirects back so the normal refreshed page shows the stored message.

Failure/security proof:
HTTP tests proved missing CSRF creates neither conversation nor message; GET is
refused on all mutation routes and POST is refused on read routes. Browser sender
and recipient injection cannot override the authenticated sender or route-selected
authorised profile. Empty drafts re-render bound errors without a write. Message
markup is stored as plain text and escaped in the response. The tested private
body was absent from captured application logs. Anonymous callers redirect to
sign-in and currently unverified callers redirect to their account. Missing,
unrelated and either-direction-blocked conversations share one 404 body and expose
no pair name or message. Blocked, inactive, unverified and unrelated pairs remain
excluded before inbox presentation; a refused send leaves message count unchanged.

Known limitations:
Block and report controls and their HTTP mutations belong to Phase 8 and are not
prematurely rendered. Ollama draft editing belongs to Phase 10. Attachments,
previews, read receipts, reactions, typing state, WebSockets, sent-message editing
and group conversations remain deliberately absent. The four-destination primary
navigation and broader presentation polish remain Phase 11.

Rollback or reset used/tested:
No schema change was introduced, so migration reversal was not applicable.
Conversation uniqueness is database-enforced and its service conflict path returns
the authoritative pair. Sending remains one atomic message/activity update; prior
failure proofs plus the Phase 7 HTTP refusals confirm no partial state. The
disposable PostgreSQL server was stopped after validation.

Reviewer:
Codex

Date:
2026-07-27
```

### Phase 8 closure evidence

```text
Commit or immutable revision:
Phase 8 mapped-file SHA-256 manifest
4b7546e91ff44b594863e5a061750740d6035ce562b6f2f641daa6cf38968e59

The digest above is the SHA-256 of these `shasum -a 256` manifest lines in the
retained order:
42cd222bbcb3aa5e84c9989164870b416f1f0117c280c0b1863ff1387425676b  templates/account.html
c0180bf9ff1f9b69c5a945f5d2e4d1bcc1b941ffcd21e31d0c3b215da95cabf8  templates/plan.html
204fc928c7eeca2f125846d33c6e4aa82e72ec5c168620cf80266c1c380320b3  templates/conversation.html
52ee2ba310444281aaca16c1d1b1d63f2e6301f2ca8521057b5132d45711c9b2  templates/report.html
ed1d8acff09bb52da215790dfc190d45fa62e8d16413be88288b1e42ef3b305d  kindlelise/forms.py
581130ac31cb92477d79a918f67e6e954cfbdc4cada9f8405dc5c12e8d95283f  kindlelise/policies.py
f56952810f409c8017013b25e9652f57560060f362d4d8731e615996968833a1  kindlelise/services.py
93f15a79553e5c02783eb072f1f1a2b438097e07ee2fbe436ee50fce8467dbbf  kindlelise/selectors.py
1db608564ee74bd5e60377766f100f718a1f007503789ec5ba7d54a73ff36719  kindlelise/views.py
7e21cfbd924a98fba94ad9357604ae04083b1bd5d2f0d202c950ec5f7a32c2f1  kindlelise/urls.py
3032a8fa543304b2c5a01b262323c72e19d79b5ce9cd9d080e6253c94086013f  tests/test_vertical_slice.py

Environment and PostgreSQL database:
Darwin arm64; Python 3.12.8; Django 5.2.15; psycopg 3.3.4;
PostgreSQL 17.10 (Homebrew). Final validation used a fresh isolated temporary
cluster, a PostgreSQL-only Django connection and disposable test databases.

Focused command and result:
.venv/bin/python manage.py makemigrations --check --dry-run;
.venv/bin/python manage.py migrate --noinput;
.venv/bin/pytest -q tests/test_vertical_slice.py -k "block or report"
Passed: no model changes, all migrations applied from zero, then 14 tests passed
and 69 were deselected. The first focused run passed every implementation check
but exposed one overbroad test assertion that rejected the harmless word `report`
anywhere in shared account HTML; it was narrowed to the actual private description,
confirmation and reporter identity, and the final focused gate reproduced cleanly.

Full regression command and result:
.venv/bin/pytest -q && .venv/bin/python manage.py check
Passed cleanly on PostgreSQL: all 83 tests passed and Django reported zero issues.
Separate compileall, git diff --check and pytest --collect-only commands passed,
collecting exactly 83 tests.

Manual success proof:
Permitted profile and conversation pages now present a short confirmation before
the named POST-only block action. One directional row closes both directions of
discovery, inbox and conversation access and redirects the blocker away without
notifying the other account. Private report actions appear on permitted profiles,
plan details, conversations and eligible received messages. The one report route
renders a bounded category/description form, carries only selector-validated page
context in hidden fields, calls the existing service for a second relationship
check and renders a small private confirmation without returning the report.
Plan context is offered when the viewer has participation history; conversation
and received-message context identify the current permitted pair without exposing
or accepting an editable reported account.

Failure/security proof:
Missing CSRF created neither block nor report, GET was refused on blocking, and
browser reporter, target, status and arbitrary model fields could not override
server authority. Missing/self targets and malformed, unrelated, own-message or
unknown contexts returned the same generic report 404 and added no partial row.
Valid plan, conversation and received-message references populated exactly one
context field. An existing block still allowed a context-free private report,
while discovery and message selectors remained closed. Successful submission
forced received status, exposed neither the description nor reporter identity to
the target, emitted no report notification and kept the private description out
of captured logs. Confirmation copy states that a report is not proof, a finding
or a sanction and that Kindlelise is not an emergency service.

Known limitations:
There is deliberately no user-facing report directory, block-management page,
moderation finding, sanction, appeal, priority engine or emergency workflow.
Stripe Premium belongs to Phase 9, Ollama draft editing to Phase 10 and broader
navigation/interface polish to Phase 11. Reports remain ordinary Django Admin
records for authorised staff review under the already completed Phase 3 controls.

Rollback or reset used/tested:
No schema change was introduced, so migration reversal was not applicable. Block
creation and report submission use the existing atomic services. Idempotency,
invalid-context, missing-CSRF and relationship-change proofs confirm no duplicate
block or partial private report. The disposable PostgreSQL server was stopped
after validation.

Reviewer:
Codex

Date:
2026-07-27
```

### Phase 9 partial evidence

```text
Commit or immutable revision:
Phase 9 mapped-file SHA-256 manifest
a8fff4512d88fe94c662cfdcfb6a650255e8f7a963c11473292d8e9356034b6b

The digest above is the SHA-256 of these `shasum -a 256` manifest lines in the
retained order:
2d36ca3278416779a6ed74d5ae1c39ab4b7a3fe60748b7b4796ad63b8b590fe7  config/settings.py
89acc7df46b06a8bcb3297a8f2c5c900199c640aa9dcdfbbf48a1d587994bef1  kindlelise/services.py
2e711393aa78641a85556b4f46a9e8bbf5318f3d75879d8266c5b6b5c9523f71  kindlelise/views.py
3d17716229a1f7e0774f3c7d642e18dcfd5357726ae625a5f0cd8606bd96bc7f  kindlelise/urls.py
9bbfb290ecac566cd40fb5e13251cf671618ba2b88505fb8cfd0d3b22cb62962  templates/account.html
01583be355f297ee707813e2347b95e33a6cd74935556cd8d5efa163c082ef03  tests/conftest.py
9ed1fac514fd75688fb7ef643af56fa18aa5dde6ff262db687075442f94b5d3a  tests/test_vertical_slice.py

Environment and PostgreSQL database:
Darwin arm64; Python 3.12.8; Django 5.2.15; psycopg 3.3.4; Stripe Python
15.3.0; PostgreSQL 17.10 (Homebrew). Final automated validation used a fresh
isolated temporary cluster, a PostgreSQL-only Django connection and disposable
test databases.

Focused command and result:
.venv/bin/python manage.py makemigrations --check --dry-run;
.venv/bin/python manage.py migrate --noinput;
.venv/bin/pytest -q tests/test_vertical_slice.py -k
"stripe or premium or webhook or checkout or portal"
Passed: no model changes, all migrations applied from zero, then 15 tests passed
and 80 were deselected.

Full regression command and result:
.venv/bin/pytest -q && .venv/bin/python manage.py check
Passed cleanly on PostgreSQL: all 95 tests passed and Django reported zero issues.
Separate compileall, git diff --check and pytest --collect-only commands passed,
collecting exactly 95 tests.

Manual success proof:
Not yet available. Phase 9's separate supervised Stripe test-mode Checkout,
webhook receipt, account display and portal-return walkthrough could not run
because STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET and STRIPE_PRICE_ID were not
configured in this execution environment. No production credential was used.

Failure/security proof:
Checkout uses only the configured yearly price, one immutable local user ID and
server-built account URLs. The first eligible session uses one 30-day no-card
trial and a post-trial hosted invoice; recorded Stripe history removes the trial,
and active or trialing state prevents another Checkout. Portal creation uses only
the signed-in account's linked customer ID. Browser return and Checkout completion
grant no access. Verified synthetic webhooks proved immutable-ID ownership,
configured-price and active-subscription checks, trial and annual access bounds,
unpaid and past-due denial, deletion, duplicate and provider-time ordering, and
safe delayed paid invoices. Conflicting IDs, email-only ownership, wrong prices,
unpaid invoices and invalid signatures committed no access. Unsupported events
created no receipt; a supported projection failure returned 500 and rolled back
both receipt and subscription changes. Raw webhook markers and secrets remained
absent from captured logs. Account output exposed no Stripe identifiers or private
report content, and Premium changed only the configured discovery limits.

Known limitations:
The required supervised Stripe test-mode pass remains open, so Phase 9 is In
progress rather than Complete. Stripe owns invoice delivery and hosted payment;
Kindlelise does not promise an email unless the applicable Stripe setting is
enabled. There is deliberately no local card form, second trial, tier catalogue,
usage billing or email-based Stripe ownership.

Rollback or reset used/tested:
No schema change was introduced, so migration reversal was not applicable.
Duplicate delivery and failed-processing tests proved idempotent receipt handling
and atomic rollback with no partial Premium projection. The disposable PostgreSQL
server was stopped after validation.

Reviewer:
Codex

Date:
2026-07-27
```

### Phase 10 closure evidence

```text
Commit or immutable revision:
Phase 10 mapped-file SHA-256 manifest
9185e7831b694172c157a1a82b33f635435a32cdc69bf9d4d261cdcc5c6ea6c2

The digest above is the SHA-256 of these `shasum -a 256` manifest lines in the
retained order:
d36b72979c858f575dc85ed8916e0aeffcfbcfa8729da262616d49a1cd6fd0a1  kindlelise/ai_message_editor.py
206441dd272abde9cd55519d9a67713b748158725589b1288941c756aa126a86  kindlelise/forms.py
eec374468c188148de6ab4b23c087b8bb3ac2b55357603d3372e7ec7f948466c  kindlelise/views.py
61c8ab622dd99632254c974031c2462a0f5e7645c3a5f222f1addc1f66423664  kindlelise/urls.py
00bd4f9f755bb3295f4bd4117ea83f8e3ce791cc48f030b40ef16096dd8fadeb  static/app.js
9460bf85d758aeda189b0ab8070a13abd2c76cac75f55275a4ed172dc5e3a74f  templates/conversation.html
f8d018a2e29b89d069a00efbef63df07ebe297e990beec7df173e4d53838e96b  tests/conftest.py
5a4a58827680483f48914c485cad5d0fcad13da3154bf2f549b651bb7debe460  tests/test_vertical_slice.py

Environment and PostgreSQL database:
Darwin arm64; Python 3.12.8; Django 5.2.15; psycopg 3.3.4; Node.js available
for JavaScript verification; PostgreSQL 17.10 (Homebrew). Final validation used
a fresh isolated temporary cluster, a PostgreSQL-only Django connection and
disposable test databases. All Ollama responses were synthetic boundary fakes.

Focused command and result:
.venv/bin/pytest -q tests/test_vertical_slice.py -k
"ollama or draft or suggestion"
Passed on PostgreSQL: 7 tests passed and 94 were deselected. The first focused
run exposed only a stale WhiteNoise manifest for the newly mapped app.js asset;
collectstatic rebuilt the manifest, and the corrected gate passed cleanly.

Full regression command and result:
.venv/bin/python manage.py makemigrations --check --dry-run;
.venv/bin/python manage.py migrate --noinput;
.venv/bin/pytest -q;
.venv/bin/python manage.py check;
.venv/bin/python manage.py collectstatic --noinput
Passed: no model changes, all migrations applied from zero, all 101 tests passed,
Django reported zero issues, and all 129 static source files were present with
360 post-processed outputs. Separate compileall, node --check, git diff --check
and pytest --collect-only commands passed, collecting exactly 101 tests.

Manual success proof:
The authorised conversation renders two type=button editing actions, a disclosure
that only the current draft and selected goal leave Kindlelise, a hidden original
and suggestion comparison, explicit Keep original and Use suggestion choices,
and the separate ordinary Send message button. A Node.js DOM/fetch harness loaded
the real app.js and proved that showing or keeping a suggestion leaves the text
box unchanged, only Use suggestion replaces it, and the request function makes
one POST to the conversation-bound suggestion route. It invoked no send action.

Failure/security proof:
MessageEditRequestForm accepted only fix_grammar or improve_clarity and a non-empty
1,000-character draft. Invalid input, missing/unverified/non-member accounts,
missing conversations and both block directions prevented the Ollama owner call.
CSRF was required. The provider boundary accepted only an HTTPS endpoint without
embedded credentials, used the configured short timeout and sent exactly model,
bounded draft, fixed instruction and stream=false with the key only in the bearer
header. Timeout, malformed JSON, incomplete, empty and oversized output returned
no suggestion. The view returned a quiet error and created no Message. Success
also created no Message; the accepted synthetic suggestion was stored only after
a separate ordinary message-form POST. Synthetic drafts, suggestions and keys
were absent from captured logs, and no AI record or model was added.

Known limitations:
No real Ollama Cloud credential, endpoint or model was configured, so live network
reachability, provider model availability and real timeout behaviour were not
claimed. The implementation plan assigns those checks to the final runtime pass.
Assessment use should remain limited to non-sensitive supervised test content;
provider terms, retention and training controls still require review before real
personal data is used.

Rollback or reset used/tested:
No schema or durable-state change was introduced, so migration reversal was not
applicable. Refusal, invalid-output and provider-failure tests proved that no
Message or separate suggestion record remained. The disposable PostgreSQL server
was stopped after validation.

Reviewer:
Codex

Date:
2026-07-27
```

### Phase 11 partial evidence

```text
Commit or immutable revision:
Phase 11 changed-file SHA-256 manifest
b5d1c3b8983aef92538feb2efb5c8b74a39ae42ef975b251bfe4407532b11f9b

The digest above is the SHA-256 of these `shasum -a 256` manifest lines in the
retained order:
6791fa00b84865ee99cf6855170c1891c2900d2bd1e937723b0daf3deb9887e3  templates/base.html
e4692a234508a7900814302980a64c921c6ddb98c62e7ff7c017c9385952c5c0  templates/discover.html
2e96cd77135367990ed4ed95651d286cf9f2b85571fb8a9a023e8594765e211e  templates/account.html
f29f293042d7690eeb680fb6d59dd308f0414085e48cd9d137b54089f80b0c9c  templates/plan.html
e3b0d1772402e8f9c1267bf810b4922b3b45613a822d013936140f3de0804ab1  templates/inbox.html
231c067091ed5a479cf384d76c92051ee03725be00b42ffb87c8d7324e9c0ac3  templates/conversation.html
02c0c7f7e4225df8e206b230b6860df7ba8779a451128f5bac898addcc6fa021  templates/report.html
b24667ee8781aed053897be0730c86b03e28d55b14681186e9e336f09ddcdb1a  static/app.css
9174206441e0d05ae00b391026b00708048503acd511c62ba0ed8e0c85d75ff9  static/app.js
8163727398b4e110c40b31af9c052a0349466674b68d62e3098ae4011869abb4  kindlelise/models.py
5966728cc724520fce9ba482327755324c4868b16e529b5f5a45d7c894400d22  tests/test_vertical_slice.py

Environment and PostgreSQL database:
Darwin arm64; Python 3.12.8; Django 5.2.15; PostgreSQL 17.10 (Homebrew);
Chrome 150.0.7871.182; Lighthouse 13.4.1. Validation used a disposable local
PostgreSQL-only cluster. Performance measurements used DEBUG=false, warmed page
code, 50 relevant rows per measured page and no provider calls.

Focused command and result:
.venv/bin/pytest -q tests/test_vertical_slice.py -k
"authenticated_interface or list_page_query_counts"
Passed on PostgreSQL: 2 tests passed and 101 were deselected. The interface test
proved the four primary links and current-page state, skip link, offline status
region, alert summary, aria-invalid and Django error association. The query test
proved constant discovery, plan-list and inbox counts from 5 to 50 visible rows.

Full regression command and result:
.venv/bin/pytest -q;
.venv/bin/python manage.py makemigrations --check --dry-run;
.venv/bin/python manage.py check;
.venv/bin/python manage.py collectstatic --noinput
Passed cleanly on PostgreSQL: all 103 tests passed in 77.51 seconds; no model
changes were detected; Django reported zero issues; and 129 static source files
were present with 360 post-processed outputs. Separate compileall, node --check,
git diff --check and pytest --collect-only commands passed, collecting exactly
103 tests. One discarded overlapping regression attempt collided on the same
disposable test database; it was not counted as product evidence, and the clean
single-run result above is authoritative.

Performance/query result:
On a 50-profile, 50-approved-plan and 50-direct-conversation fixture, captured
query counts were constant from 5 to 50 visible rows: discovery 12, plan list 5
and inbox 5. Across 20 warmed authenticated GETs with DEBUG=false, discovery was
6.88 ms median / 7.40 ms p95, plan list 4.22 ms / 4.47 ms and inbox 5.82 ms /
6.46 ms. Every result was below the 200 ms median and 500 ms p95 budgets.

Browser/interface proof:
Trusted local Chrome loaded synthetic signed-in empty discovery, populated
discovery, plan detail and profile-edit form states at exact 320 and 1,440 CSS-
pixel viewports. For every captured page, document scrollWidth equalled
clientWidth, so there was no two-dimensional page scrolling; each authenticated
page exposed Discover, Plans, Messages and Profile in that order. The shared
shell supplies visible focus styles, 44-pixel-or-larger controls, safe-area bottom
padding, reduced-motion handling, semantic status/error regions and a no-storage
offline notice. The dark responsive presentation uses textual state labels and
does not depend on colour alone. A public sign-in Lighthouse accessibility audit
scored 100.

Failure/security proof:
Empty discovery, plan, inbox and conversation states provide plain next actions;
restricted routes retain their generic server responses; form errors remain next
to labelled fields and have an alert summary; and the browser offline notice
does not store private text. The AI loading and provider-failure states preserve
the original draft, and existing Stripe/Ollama refusal tests remained green.
Core account, plan, message, block and report HTTP flows remained green without
JavaScript. User text is rendered through normal escaped Django output.

Known limitations:
Phase 11 remains In progress. Its Phase 9 prerequisite is still In progress
because the supervised Stripe test-mode walkthrough lacks configured Stripe test
credentials. The complete manual keyboard-only and screen-reader-label journey,
200% zoom review and representative signed-in Lighthouse audits have not been
claimed. A transient Lighthouse process was not given an authenticated session
after the execution safety boundary refused exposing a private cookie to fetched
third-party code; the public score is therefore the only accepted Lighthouse
score in this record.

Rollback or reset used/tested:
No schema or durable product-state change was introduced, so migration reversal
was not applicable. Browser and performance fixtures used synthetic records in a
disposable local database. The disposable PostgreSQL server was stopped after
validation.

Reviewer:
Codex

Date:
2026-07-27
```
