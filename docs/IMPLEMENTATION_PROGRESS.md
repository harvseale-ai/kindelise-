# Kindlelise Student MVP Implementation Progress

> **Authority:** [`docs/VERTICAL_SLICE.md`](VERTICAL_SLICE.md) remains the
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
| 3 | Staff verification and plan approval | Not started | — |
| 4 | Account and profile journey | Not started | — |
| 5 | Discovery and availability | Not started | — |
| 6 | Plans and participation | Not started | — |
| 7 | Direct messaging | Not started | — |
| 8 | Blocking and private reporting | Not started | — |
| 9 | Stripe Premium | Not started | — |
| 10 | Ollama draft editing | Not started | — |
| 11 | Interface, accessibility, performance and failure states | Not started | — |
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
