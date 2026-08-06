# Kindlelise Student MVP Safety Model

> **Archived:** historical supporting document. Current behaviour is governed by
> `docs/VERTICAL_SLICE.md` and `docs/DECISIONS.md`.

> **Status: student-project safety design, not a guarantee of physical safety, an
> emergency service or a production safeguarding operation.** It describes only
> controls approved in `docs/VERTICAL_SLICE.md`. That document wins if the two
> conflict.

## 1. Purpose and limits

Kindlelise helps verified accounts discover one another, coordinate public-place
plans and communicate directly. Those activities can create risks including
unwanted contact, impersonation, location exposure, misleading meeting details,
harassment and unsafe user-written content.

The student MVP reduces those risks through a small set of understandable
controls:

```text
manual profile verification
→ broad-area discovery
→ staff-reviewed public-place plan
→ first-join plan lock
→ authorised direct messages
→ immediate blocking
→ private reporting
```

These controls reduce opportunities for misuse. They do not prove a person's
identity, age, intentions or safety; guarantee that a venue or activity is safe;
monitor a meeting; verify that people met; or provide emergency help.

The assessment uses supervised test accounts only. It does not implement age
verification and must not be presented as ready for unrestricted public use.

## 2. Safety principles

1. **Be honest about authority.** Staff verification, plan approval, reports,
   Stripe events and AI suggestions each mean only what their owning workflow can
   establish.
2. **Use coarse location.** Discovery uses configured stable broad-area keys and
   labels and never requires arbitrary area text, coordinates or movement history.
3. **Anchor plans publicly.** A meeting proposal identifies an independently
   established public place or organised activity through a public URL.
4. **Prevent meeting-detail substitution.** The first successful join makes the
   whole plan read-only except cancellation.
5. **Recheck before acting.** Verification, ownership, membership, capacity and
   blocks are enforced on the server at the time of the action.
6. **Give users an immediate boundary.** A block removes discovery visibility and
   direct-message access in both directions without notifying the other account.
7. **Keep reports private and non-adjudicative.** A report provides staff context;
   it is not proof, a public review or an automatic sanction.
8. **Do not sell safety.** Premium never weakens or improves verification,
   blocking, reporting or object-level permissions.
9. **Minimise provider disclosure.** Stripe receives billing data through hosted
   pages; Ollama receives only an explicitly submitted unsent draft and fixed
   editing goal.
10. **Fail closed.** Missing or uncertain authority never grants social, billing
    or AI access.

## 3. Main hazards and current controls

| Hazard | MVP control | Honest limitation |
| --- | --- | --- |
| Disposable or unreviewed profiles enter social features | Staff-controlled profile verification gates discovery, plans, messaging and AI editing. | Verification is manual and is not proof of legal identity, age, good character or safety. |
| Exact location is exposed or inferred | Profiles store a broad named area only; discovery shows no coordinates, distance or direction. | A broad area still reveals approximate location and should not be described as anonymous. |
| A user proposes a private or unestablished meeting place | Plans require a named public place/activity and public HTTPS evidence URL; staff manually review it. | Staff review does not preserve the webpage, inspect the physical venue or guarantee safety. |
| Meeting details change after acceptance | Sensitive pre-join changes return an approved plan to review; the first join locks the whole plan. | Cancellation remains possible, and Kindlelise does not monitor external webpage changes. |
| Too many people join | Joining locks and recounts the plan before accepting participation. | This controls application capacity only; it does not count people outside Kindlelise. |
| Unwanted or abusive contact | Only active verified unblocked accounts may message; either user can block. | Direct messaging does not require matching, so users must retain clear Block and Report controls. |
| A blocked conversation leaks through the inbox | Either-direction-blocked conversations are excluded before names, previews or messages reach the template. | The historical database rows remain; blocking is an access rule, not automatic erasure. |
| User-written markup executes | Messages and other user-written fields render as escaped text. | Escaping prevents script execution; it does not make hostile language safe or true. |
| A report becomes a public accusation | Reports are private, server-contextual and visible only through authorised paths. | The MVP has no formal finding, sanction, appeal or investigative evidence system. |
| AI changes meaning or sends unwanted text | Ollama editing is draft-only, uses two fixed goals, requires acceptance and never sends automatically. | A suggestion can still be poor; the user must review it before sending. |
| Payment is mistaken for trust | Stripe is used only for one hosted Premium subscription. | Payment does not prove identity or age and grants no safety privilege. |

## 4. Manual profile verification

Anyone may register and complete their own permitted profile fields, but only an
active account with a currently staff-verified profile may use discovery, plans,
direct messaging or Ollama editing.

Authorised staff may verify or remove verification through mapped Django Admin
actions. Each selected profile is rechecked individually; staff actions do not
blindly update every selected row. Verification records the reviewer and time.

The interface must use truthful language:

> Staff have approved this profile to use the student MVP.

It must not claim:

> Kindlelise has proved this person's identity, age or safety.

The MVP does not collect verification photographs, biometric templates,
government documents or social-media proof.

## 5. Discovery and availability

Discovery contains active verified profiles in permitted broad named areas.
Either-direction blocks are applied before a profile enters the result set.
`settings.py` owns the approved stable area keys, labels and nearby-area mapping.
Profile and discovery forms reject arbitrary area text.

The user may filter controlled interests and current availability. `Free now`
means only that the profile owner's optional `available_from` start has arrived
and has not been cleared. It must not imply that the person is physically at a particular
place, has agreed to meet, is actively watching the application or is permanently
available.

Free and Premium discovery limits affect area choices and interest-filter count
only. Neither tier may reveal exact distance, direction, hidden-result counts or
blocked profiles.

A reviewed data migration seeds Coffee, Walking, Museums, Live music, Cinema,
Food, Games and Study. Ordinary users cannot create free-text interests.

## 6. Public-place plans

### 6.1 Required meeting information

A plan contains a title, description, established public place, public HTTPS
evidence URL, start time and capacity. A dropped map pin, residential address,
payment link or personal social post is not sufficient primary evidence of the
meeting place or activity.

Kindlelise has no plan ticket sale, attendance payment, host payout or private
home-meeting workflow. Stripe Premium is a platform subscription and is unrelated
to plan participation.

### 6.2 Manual review authority

New plans are Pending review. Authorised staff manually open the public URL
outside the application and approve or reject the plan in Django Admin. Staff
must recheck that each selected plan is pending, future and unlocked.

The stored approval contains only status, reviewer and time. Kindlelise does not:

- fetch or follow the URL on the server;
- preserve the reviewed webpage;
- create a URL substantiation or formal meeting-anchor decision;
- send the URL to AI;
- guarantee that the venue, organiser, activity or other participant is safe; or
- guarantee that the external page will not later change.

The plan page must explain this limitation in plain language.

### 6.3 Publication, joining and locking

Only approved future plans enter the public plan list and accept joins. The owner
cannot join their own plan. Rejected, cancelled, past, unapproved and full plans
reject joining.

Joining is direct; there are no requests, offers or invitations. The join service
locks the plan row, recounts current participation and rechecks every condition in
one transaction. This prevents simultaneous requests from exceeding application
capacity.

The first successful join permanently records the plan lock. After that the whole
plan is read-only except cancellation. Before the first join, changing an
approved plan's public place, URL or start time returns it to Pending review.
Saving an edited rejected plan also resubmits it as Pending review. Cancelled plans
are terminal and cannot be edited, approved or reactivated. Capacity counts
participant places only and excludes the owner.

A participant may leave without deleting their participation row or unlocking
the plan. An eligible former participant may rejoin using that same row. The plan
page shows joined count, not a public participant directory.

The owner may cancel, which removes the plan from public lists and future joins
without deleting it or its participation history.

## 7. Direct-message safety

One direct conversation exists per unordered pair of different accounts. Starting
a conversation requires two active verified accounts and no block in either
direction. No swipe, mutual match or contact request is required.

Every conversation open, message send and Ollama request rechecks:

- the requester belongs to the conversation;
- both accounts remain active and verified; and
- neither account has blocked the other.

Messages are bounded plain text, escaped during rendering and refreshed through
ordinary Django page requests. The MVP has no media, attachments, reactions,
typing state, read receipts, live sockets, sent-message editing, disappearing
messages or group conversation.

Message bodies and inbox previews must not appear in application logs, external
analytics or third-party notification previews.

## 8. Blocking

A block stores one directional choice but has mutual product effect:

```text
block
→ remove each profile from the other's discovery
→ deny opening their direct conversation
→ deny sending further messages
→ send no notification to the blocked account
```

The server applies the block even if a stale page still displays a Message
button. Repeating the same block must not create duplicate state. The blocked
account cannot inspect who blocked it.

Blocking does not delete prior plans, participation, conversations or messages.
It must not prevent the blocker from submitting a valid private report.

## 9. Private reporting

The MVP exposes Report from permitted profile, plan and conversation contexts. An
eligible received message may provide message-specific context through the same
report route. Reporting is never Premium-only.

A report:

- identifies an authenticated reporter and different reported account;
- contains a bounded category and factual description;
- may reference at most one server-validated plan, conversation or message;
- remains unavailable to the reported account and unrelated ordinary users;
- sends no report notification to the reported account; and
- creates no finding, sanction, warning, rating, review, risk score or allegation
  count.

The server must reject arbitrary or unrelated references. A plan reference must
connect both accounts as owner or participant. A conversation must contain both.
A message must belong to that conversation and have been visible to the reporter.

Submission confirmation should say:

> Your report was submitted privately to authorised staff. A report is context
> for review and does not by itself prove wrongdoing.

The report form should ask for necessary factual context and discourage home
addresses, financial details, unrelated third parties and unnecessary sensitive
information.

## 10. Staff report boundary

Authorised staff may inspect private reports in ordinary Django Admin and mark
their small status as Received or Reviewed. The report remains a user statement.

The MVP does not implement:

- investigation cases or evidence custody;
- priority or risk-scoring queues;
- formal findings or policy-breach decisions;
- temporary restrictions or automatic suspensions;
- sanctions, reasons or appeals;
- police, emergency-service or safeguarding referrals; or
- immutable moderation audit records.

Staff must not imply that Reviewed means true, corroborated, resolved or safe.
If the project is demonstrated with reports, use non-sensitive test content.

## 11. Ollama message-editing boundary

Ollama editing is available only inside an authorised direct conversation and
only after the user chooses Fix grammar or Improve clarity.

```text
current unsent draft + fixed goal
→ Ollama Cloud
→ bounded suggestion
→ user keeps original or accepts suggestion
→ ordinary validation runs again
→ user manually sends
```

Kindlelise must not send the recipient's profile, previous messages, sent
messages, reports or plan information. Empty or oversized output is rejected.
Timeout, invalid output or provider failure preserves the original draft and
sends nothing.

The provider may still produce inaccurate, offensive or meaning-changing text.
The interface must describe the output as a suggestion and keep the user
responsible for reviewing and sending it. The provider's Free plan is not a
safety, privacy, uptime or price guarantee.

## 12. Stripe boundary

Stripe-hosted Checkout, invoices and the hosted customer portal own payment
collection and management for one Premium subscription: one no-card 30-day trial
per local account followed by GBP 4.99 yearly. Kindlelise stores a minimal
subscription projection and no card or bank details.

The server constructs Checkout success, Checkout cancellation and portal-return
destinations from the named local account route. The browser cannot supply them.

Returning from Checkout does not grant Premium. Only a verified trialing update
with a future trial end grants trial access; active status alone does not prove
payment. Only a verified paid invoice for the linked configured price and active
subscription grants its bounded paid annual period. Unpaid, past-due and expired
states deny access, and deletion clears access. Premium affects configured broad-
area choices and interest-filter count only.

Each accepted supported event ID receives one durable receipt. Correctly signed
unsupported events are acknowledged without a receipt or state change. Failed
supported processing commits neither a receipt nor a partial subscription update.
Deletion sets status to cancelled, clears `access_until`, advances the provider
event time and retains the Stripe identifiers for safe matching and portal access.

Stripe payment must never be described or used as:

- age or identity verification;
- evidence that an account is safe;
- permission to bypass a block or staff verification;
- priority for reports; or
- paid placement in discovery.

## 13. Safety language

Use language that matches the system's authority:

| Allowed | Not allowed |
| --- | --- |
| “Staff reviewed the public place and URL.” | “This meeting is safe.” |
| “This profile may use the student MVP.” | “This person's identity and age are verified.” |
| “Free now is a user-set signal.” | “This person is currently at this location.” |
| “Your report was submitted privately.” | “Kindlelise confirmed what happened.” |
| “AI suggested an edit.” | “AI made this message safe or accurate.” |
| “Premium access is active until this date.” | “Premium members are more trustworthy.” |

The interface must not promise monitoring, intervention, guaranteed response
times, emergency assistance or legal compliance that the project cannot provide.

## 14. Failure behaviour

- Missing or removed verification denies discovery, plans, messaging and AI
  editing without deleting historical records.
- A blocked or uncertain conversation returns no messages and makes no Ollama
  request.
- A stale plan page cannot bypass current status, capacity, ownership or lock
  checks.
- A failed or unavailable manual URL review leaves the plan unpublished.
- Invalid report context creates no partial report and exposes no hidden object.
- Ollama failure preserves the original unsent draft and never sends a message.
- Stripe failure or a browser return leaves Premium unchanged until an
  authoritative webhook arrives.
- Missing and forbidden objects use the same safe unavailable response when the
  distinction would expose another account's state.

## 15. Explicitly deferred safety systems

The following are not implemented protections and must not be promised or
partially added without an approved boundary change:

- biometric, document or payment-based age/identity verification;
- exact proximity, continuous location or movement monitoring;
- immutable meeting artifacts, plan versions or participant-specific contracts;
- meeting check-ins, welfare prompts or “everything as expected” responses;
- emergency contacts, urgent-help routing or live incident intervention;
- blind corroboration, sealed experiences, subject matching or safety circles;
- pseudonymous peer support or private safety notifications;
- formal moderation cases, evidence preservation, findings, sanctions or appeals;
- automated report scoring, coordinated-abuse detection or account suspension;
- media moderation, disappearing attachments or group safety tools; and
- automated URL, venue or organiser safety assessment.

Historical safety designs remain future research only. They do not authorise a
model, route, service, notification or user promise in the 36-implementation-file
vertical slice.

## 16. Student assessment checklist

Before demonstrating the MVP, prove that:

1. unverified and inactive accounts cannot use social features;
2. staff verification does not claim identity or age proof;
3. discovery uses broad areas and excludes either-direction blocks;
4. Free now is derived only from an `available_from` start that has arrived;
5. only manually approved future plans enter the public list;
6. staff approval makes no preserved-evidence or venue-safety claim;
7. concurrent joins cannot exceed capacity;
8. the first successful join makes the entire plan read-only except cancellation;
9. leaving preserves history and cannot unlock the plan;
10. conversation access and sending recheck verification and blocks;
11. user-written messages render as escaped plain text;
12. blocking immediately removes discovery and message access without notifying
    the other account;
13. reports remain private, references are relevant and no finding is created;
14. Ollama receives only an explicitly submitted unsent draft and fixed goal;
15. AI never sends automatically and failure preserves the draft;
16. Stripe payment grants no safety authority or verification;
17. Premium never weakens safety rules; and
18. deferred safety systems remain absent and unclaimed.
