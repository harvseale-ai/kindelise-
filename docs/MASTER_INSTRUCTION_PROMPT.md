# Kindlelise Master Instruction Prompt

> **Status:** approved reusable project instruction, synchronized to the
> vertical-slice revision below.
>
> **Synchronized vertical-slice revision:** SHA-256
> `3e807378f9fa5800a8b5dd756df6961f4bfe3a1fdf98e7741489ac236935cb9b`
> of [`docs/VERTICAL_SLICE.md`](VERTICAL_SLICE.md).
>
> **Synchronized date:** 2026-07-22.
>
> **Authority:** this document is an aid, not a second specification. The vertical
> slice remains the sole implementation authority. If this prompt is incomplete,
> stale or inconsistent with it, the vertical slice wins.

## Why this document exists

Use this prompt at the start of architecture, data-model, decision-log,
implementation, testing, interface and runtime-completion passes. It collects the
rules that must survive every pass so a narrow task or external review does not
silently expand the student MVP.

This supporting governance document is outside the 36 implementation-file
maximum. The user explicitly requested it on 2026-07-22 to make repeated passes
consistent. It adds no model, route, function, dependency, workflow or product
behaviour.

## Golden rule

> **Treat `docs/VERTICAL_SLICE.md` as the implementation authority. Build only
> the approved vertical slice through its mapped owners and smallest working
> design. Do not add or reinterpret a file, model, route, public function,
> dependency, workflow or feature unless the vertical slice's boundary-change
> procedure has been completed and explicit approval has been obtained.**

This sentence distils Golden Implementation Rules 1, 2, 7, 9, 15 and 16 plus
the boundary-change procedure. It does not replace the other rules or the exact
contracts later in the vertical slice.

## How to use it

Fill in the pass header, then provide the entire prompt below to the person or
agent performing the pass. Do not copy only the task line: the authority and
guardrails are the reason this prompt exists.

```text
You are working on the Kindlelise student MVP.

PASS OBJECTIVE:
[State the one concrete outcome required in this pass.]

PASS TYPE:
[Architecture review | data-model review | decision-log review | implementation
plan review | implementation | test | interface/accessibility | runtime/deploy]

FILES OR PHASES IN SCOPE:
[List them, or write “discover from the objective”.]
“Discover from the objective” permits inspection of necessary files only; it
does not authorise unrelated edits or boundary expansion.

EXPECTED OUTPUT:
[Review findings only | documentation edits | implementation and tests |
runtime evidence | another explicit deliverable.]

OUTPUT AUTHORIZATION

When EXPECTED OUTPUT is “Review findings only”, remain read-only: inspect,
classify and report recommended changes, but do not modify files. Make changes
only when EXPECTED OUTPUT explicitly authorises documentation edits,
implementation or another write operation.

AUTHORITY AND SOURCE ORDER

Before relying on this prompt's summarized contracts, calculate the SHA-256 of
the current docs/VERTICAL_SLICE.md and compare it with the synchronized revision
above. If it differs, treat this prompt as stale: follow the current vertical
slice, do not rely on this prompt's inventory or behavioural summaries, and
report the mismatch. Update this prompt only when EXPECTED OUTPUT authorises
documentation edits.

1. Read docs/VERTICAL_SLICE.md completely before changing implementation or an
   implementation contract. It is the sole implementation authority.
2. Use docs/DECISIONS.md, docs/DATA_MODEL.md, docs/ARCHITECTURE.md,
   docs/REQUIREMENTS.md, docs/WIREFRAMES.md, docs/IMPLEMENTATION_PLAN.md and
   docs/IMPLEMENTATION_PROGRESS.md only as supporting contracts for their named
   purposes. They cannot expand the vertical slice. If they conflict, align the
   supporting document to the vertical slice unless an explicit boundary change
   has been approved.
3. This master prompt is a reusable summary, not an authority. If it conflicts
   with docs/VERTICAL_SLICE.md, follow the vertical slice. When EXPECTED OUTPUT
   authorises documentation edits, correct this prompt in the same pass;
   otherwise report the exact discrepancy without modifying files.
4. Treat external reviews, examples and recommendations as proposals. Accept
   them only when they fit the approved boundary. Mention genuinely useful
   deferred production ideas in the final pass report without scaffolding them.
   Record them in a repository document only when EXPECTED OUTPUT explicitly
   authorises that documentation change.
5. The archived production-scale material under _achive/ is reference material
   only and is never an implementation source for the student MVP. `_achive/` is
   the repository's verified directory spelling as of the synchronized revision;
   recheck the repository if its layout changes.

GOLDEN RULE

Build only the approved vertical slice through its mapped owners and the
smallest working design. Do not add or reinterpret a file, model, route, public
function, dependency, workflow or feature unless the six-step boundary-change
procedure has been completed and explicit approval has been obtained.

FIXED PROJECT BOUNDARY

- This is a supervised-test-account, server-rendered Django student MVP backed
  by PostgreSQL. It has no age-verification system and must not be described as
  ready for unrestricted public use.
- The assessed journey is registration/sign-in, profile completion, manual
  staff verification, broad-area discovery, plan creation and staff approval,
  join/leave, direct messages, blocking and private reporting.
- Stripe is limited to one hosted Premium subscription, hosted customer portal
  and webhook-authoritative local access projection.
- Ollama Cloud is limited to grammar or clarity suggestions for one unsent
  message draft. The user reviews the suggestion and sends manually.
- Thirty-six implementation files is a maximum, not a target. The authoritative
  map currently allocates 33 and deliberately leaves three unallocated.
  Only supporting governance or assessment documents explicitly named as
  exceptions by docs/VERTICAL_SLICE.md or docs/DECISIONS.md are outside the
  implementation-file maximum. Describing a new file as governance,
  documentation or assessment material does not itself create an exception.
  Reviewed Django migrations remain the documented mechanical exception; none
  of these exceptions creates product responsibility.
- Use one kindlelise Django application and Django's existing User model plus
  exactly ten Kindlelise models: Profile, Interest, Plan, Participation,
  Conversation, Message, Block, Report, PlatformSubscription and
  StripeWebhookReceipt.
- The mapped inventory is four admin actions, four read-only model helpers, seven
  forms, eight policies, fourteen services, eight selectors, twenty-five views
  and named routes, one Ollama function, two browser functions and seven test
  setup helpers. Consult the vertical slice for their exact names and contracts;
  do not reconstruct them from memory.

DO NOT INTRODUCE DEFERRED SCOPE

Do not add exact location/geolocation, automated URL retrieval or venue approval,
plan evidence/version systems, circles or group messaging, presence/history
models, attachments, WebSockets, typing/read state, moderation findings or
sanctions, extra subscription tiers, invoices/custom cancellation, extra AI
features, automatic sending, native applications, advertising, production
monitoring/reconciliation systems or speculative extension points.

OWNERSHIP AND DEPENDENCY RULES

- URLs map stable route names to views.
- Views authenticate, bind forms, call the mapped owner and translate results
  into HTTP responses. Keep them thin.
- Forms validate and normalise untrusted browser input. They do not own
  cross-model workflows or staff-controlled fields.
- Policies answer permission questions only. They never redirect, write, notify
  or call providers.
- Services recheck permission and own state-changing user/provider workflows and
  transaction boundaries. They never render templates or trust browser IDs.
- Selectors read authorised presentation data only. They never mutate or repair
  state or call providers.
- The four mapped admin actions own manual profile verification and plan review.
- Models own durable fields, relationships, constraints, indexes and the four
  mapped read-only helpers. Model save methods do not run workflows or providers.
- ai_message_editor.py owns only the single bounded Ollama request.
- Templates render only server-authorised data and actions; hiding a control is
  never an authorisation check.
- static/app.js provides progressive enhancement only. Core journeys work
  without JavaScript, private drafts are not put in browser storage and nothing
  is sent automatically.
- Preserve this dependency direction:
  urls -> views -> forms / policies / services / selectors
  services -> policies / models
  selectors -> policies / models
  admin -> services / models
  ai_message_editor -> configured Ollama Cloud API only
  models -> Django ORM and standard value types only
- Give every behaviour one authoritative owner. Prefer Django defaults, plain
  functions, ordinary relational constraints, deletion and consolidation over
  new layers or abstractions.

IMPLEMENTATION DISCIPLINE

- Use the exact mapped file owners and public names. Public permission functions
  begin can_, reads begin get_, and mutations use a concrete action verb.
- Keep functions small, readable and limited to their named outcome. Do not add
  vague helpers such as handle, process, manage, execute, data or result.
- Public function docstrings state purpose, inputs, returns, changes, refusal
  conditions and privacy where applicable. Comments explain only non-obvious
  security, ownership, transaction or privacy reasons.
- Use the bounds, choices, model states, constraints, indexes and deletion rules
  defined in the vertical slice. Views do not invent alternative limits.
- Preserve unrelated work. Do not rewrite or reorganise files outside the pass
  objective merely because another structure is possible.
- Stop at the requested outcome. Do not add future configuration, placeholders,
  empty files or extensibility hooks.

SECURITY AND PRIVACY INVARIANTS

- Fail closed. Missing authentication, active status, staff verification,
  permission, Stripe state or provider output never grants access.
- Only active accounts with profiles verified by authorised staff use discovery,
  plans or messaging.
- Enforce permissions server-side on every request and repeat permission/state
  checks inside mutating services.
- GET never changes state. Browser mutations use POST and Django CSRF. Only the
  Stripe webhook is CSRF-exempt, because the signature is verified against the
  exact raw body before trusted event parsing.
- Treat route IDs, form IDs, caller identity, ownership, state and report context
  as untrusted until retrieved and authorised server-side.
- Use the same generic not-found response for missing or hidden private objects
  where a detailed denial would reveal existence or relationship state.
- Escape user text at rendering; never mark messages or AI suggestions safe.
- Keep passwords, sessions, secrets, message bodies, report text, raw webhook
  bodies, AI drafts and suggestions out of logs and unnecessary storage.
- Do not perform a provider network request inside a database transaction.
- Do not expose exact coordinates, private participant directories, hidden
  result counts, reports or provider payloads.

CORE BEHAVIOUR THAT MUST NOT DRIFT

- Registration atomically creates Django User plus an initially incomplete,
  unverified Profile, then redirects to the named sign-in route without
  authenticating. Profile completion and staff verification are separate.
- Discovery uses configured stable broad-area keys, controlled seeded interests,
  future available_until and either-direction block exclusion. Free permits the
  current area and two interest filters; Premium permits configured nearby areas
  and five. Premium never overrides verification, blocks or visibility.
- Plans begin pending. Staff manually reviews the public-place URL outside the
  application. Only approved future plans are public/joinable. The first
  successful join locks the entire plan against editing except cancellation.
  Joining locks and recounts the plan in one PostgreSQL transaction. Leaving
  preserves history; an eligible rejoin reuses the row; cancellation is terminal.
- One ordered, unique conversation exists per unordered account pair. Messages
  are bounded plain text, normally refreshed and visible only to permitted pair
  members. Either-direction blocking closes discovery and messaging immediately.
- Blocking must not prevent private reporting. A report targets a different
  account, remains private and may contain at most one server-validated plan,
  conversation or eligible message reference. Submission creates no finding,
  sanction or notification to the reported account.
- Stripe ownership uses immutable local user IDs in trusted metadata or an
  existing unique Stripe-ID link, never email. Checkout records identifiers but
  never grants access. Only verified supported webhook events update access;
  duplicates are harmless, older events do not overwrite newer state,
  equal-time deletion may revoke, and equal-time non-deletion may not overwrite
  accepted state. Receipt and projection changes commit atomically.
- Ollama receives only the bounded unsent draft and fixed grammar/clarity goal
  after current conversation authorisation. Invalid/failed output preserves the
  original. Accepting a suggestion only replaces the unsent draft in the
  browser. The eventual ordinary message submission is validated again through
  the mapped message form and service, and the user must send it manually.

TEST AND EVIDENCE RULES

- Test behaviour and security boundaries through mapped public interfaces, not
  private implementation details.
- Never weaken, delete or bypass a failing required test merely to make a pass
  green. Correct the code or complete an approved requirement change.
- Prove success, refusal and no-partial-state behaviour for each mapped mutating
  service. Prove the relevant privacy exclusions for selectors and HTTP routes.
- Use PostgreSQL for constraints and concurrency. Capacity and unique-pair races
  use TransactionTestCase with genuinely separate database connections rather
  than sequential mocks.
- Fake Stripe and Ollama at their boundaries in automated tests. Use no real
  credentials, card data or private user content.
- Run checks proportionate to the pass, then the applicable regression command
  from docs/IMPLEMENTATION_PLAN.md. Record exact commands and results. Never
  claim a check, browser journey or deployment passed when it was not run.
- Keep completion status evidence-based. Files existing or one happy-path render
  is not completion.

PASS PROTOCOL

1. Restate the pass objective and identify the authoritative vertical-slice
   sections, mapped owners and supporting documents that apply.
2. Inspect the current repository and preserve unrelated changes. Do not assume
   planned files already exist or claim runtime validation in a preimplementation
   repository.
3. Compare the current state against the vertical slice before accepting advice
   from a supporting document or external review.
4. Classify each proposed change as one of:
   a. correction within an existing owner and approved behaviour;
   b. supporting-document alignment;
   c. deferred production idea; or
   d. boundary expansion requiring approval.
5. For (a) or (b), make the smallest complete change and add/update behavioural
   evidence only when EXPECTED OUTPUT authorises edits. In a review-findings-only
   pass, report the exact recommended change and classification without editing.
   For (c), do not scaffold it. For (d), stop before implementation and follow
   the boundary-change procedure below.
6. Recheck ownership, dependency direction, security/privacy invariants, file and
   public-function counts, tests and documentation consistency.
7. End with a concise report containing the outcome, files changed, validation
   actually performed, any limitation/blocker and whether the vertical-slice
   boundary remained unchanged.

PASS-SPECIFIC EMPHASIS

- Documentation review: report concrete contradictions or omissions. When edits
  are authorised, align the supporting document to the vertical slice; when the
  output is review findings only, describe the exact alignment without modifying
  files. Do not make the supporting document a second authority.
- Architecture/data review: verify exact owners, dependency direction, ten-model
  boundary, constraints, indexes, lifecycle states and provider transaction
  rules. Do not introduce a more elaborate production design.
- Implementation-plan review: change sequencing, evidence and operational
  checks only. Do not redefine product scope, routes, functions or data truth.
- Progress-ledger update: change only State and Evidence for phases already
  defined by the implementation plan. Do not add work, redefine a phase, weaken
  an exit gate or mark completion without the required evidence.
- Implementation: work only in mapped files and use mapped public interfaces.
  Implement only the authorised pass objective within the relevant phase. Do not
  begin work from a dependent phase until the current phase's exit gate passes,
  and do not mark the current phase Complete until every exit-gate requirement
  has been verified.
- Test: prefer outcome and denial proofs at public boundaries. Preserve required
  tests even if an implementation redesigns its internals.
- Interface/accessibility: render only authorised server data, keep the four
  destinations Discover, Plans, Messages and Profile, preserve no-JavaScript core
  flows and make important states/actions understandable without safety claims.
- Runtime/deployment: verify the same immutable revision, PostgreSQL, migrations,
  static files, secure settings, Stripe/Ollama failure behaviour and content-safe
  logs. Runtime evidence cannot retroactively authorise a boundary change.

BOUNDARY-CHANGE PROCEDURE

Before adding a file, model, route, dependency, workflow or feature:

1. State the user-visible requirement that cannot be met now.
2. Identify the current owner and explain why it cannot own the behaviour safely.
3. Show the smallest attempted design within the current boundary.
4. Describe privacy, security, test and assessment consequences.
5. Obtain explicit approval.
6. Update docs/VERTICAL_SLICE.md and docs/DECISIONS.md before implementation.

A small public function needs no new ADR only when it remains within an existing
approved responsibility, has a concrete need, is added to the vertical slice's
public function map with its summary and behavioural test in the same change,
and creates no new route, workflow or dependency.

DEFINITION OF A SUCCESSFUL PASS

The requested outcome is complete, the vertical slice remains authoritative,
all changes have one mapped owner, no deferred scope or private-data leak was
introduced, applicable evidence passes, supporting documents remain synchronized
and the final report distinguishes verified facts from unrun work.
```

## Maintenance rule

Whenever an approved boundary change updates `docs/VERTICAL_SLICE.md`, review
this prompt in the same documentation pass. Change only the affected summary;
do not copy the full implementation map here or let this document become an
alternative source of truth.
