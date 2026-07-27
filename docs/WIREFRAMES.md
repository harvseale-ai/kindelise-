# Kindlelise Student MVP Mobile Wireframe Contract

## 1. Purpose and authority

This document defines the mobile page layout for the approved Kindlelise student
MVP. The supplied Grindr screenshots remain a **structural reference** for compact
headers, dense grids, horizontal chips, long sectioned forms, fixed actions,
inbox rows, account drawers and strong empty states.

The existing wireframe shapes are intentionally retained. Content changes only
where an older Kindlelise feature no longer exists or an approved MVP feature was
missing. Kindlelise does not copy Grindr branding, icons, photographs, sample
content, sexual taxonomy, advertisements, paid ranking or runtime behaviour.

> **Status: student MVP wireframe contract.** This document may define
> presentation only for behaviour approved in `docs/VERTICAL_SLICE.md`. It cannot
> add models, routes, services or features. If the documents conflict,
> `docs/VERTICAL_SLICE.md` wins.

## 2. Product represented by these pages

```text
Verified user
├── profile
├── discovery grid
├── plan
│   └── participation
├── direct conversation
│   └── message
├── block
├── private report
└── premium subscription
```

Ollama Cloud editing is an explicit action on one unsent direct-message draft. It
is not a durable entity and cannot edit or send an existing message.

These are assessment screens for supervised test accounts. The MVP does not
implement age verification and is not presented as ready for unrestricted public
use.

The pages use these fixed meanings:

- A **profile** represents one verified account, not permanent availability.
- Discovery shows verified profiles in permitted broad named areas.
- A **plan** is one staff-reviewed public-place activity.
- A **participation** records joining, leaving and permitted rejoining.
- A **conversation** is direct communication between exactly two accounts.
- A **report** is a private statement, not a finding or proof of wrongdoing.
- Premium expands area choices and interest-filter count only.

## 3. Reference-use boundary

Several supplied screenshots are alternate tabs or scroll positions of one page.
They are visual references rather than Kindlelise screens.

| Capture | Reference shape retained | Kindlelise MVP use |
| --- | --- | --- |
| 01–02 | Tabbed empty-state page | Empty-state and compact-tab grammar only; no taps or views. |
| 03–04–11 | Long edit form | Sticky header and grouped profile rows; no photo, health or sexual fields. |
| 05 | Filtered empty page | Plan-list empty state. |
| 06–08–14 | Own/other profile | Profile information hierarchy and fixed actions; no profile media. |
| 09 | Inbox | Direct-conversation rows only. |
| 10 | Account drawer | Account, verification, premium and sign-out controls. |
| 12–13 | Plan comparison | Premium-information panel shape only; no copied products or claims. |
| 15–16 | Dense grid and filters | Verified-profile discovery grid and broad-area/interest filters. |

The inline reference images are not repository assets. If redacted originals are
later retained, they must be labelled third-party layout references rather than
Kindlelise designs.

## 4. Shared mobile shell

### 4.1 Page frame

```text
┌─────────────────────────────────┐
│ system safe area                │
├─────────────────────────────────┤
│ page header / contextual action │
├─────────────────────────────────┤
│ optional tabs or filter chips   │
├─────────────────────────────────┤
│                                 │
│ scrollable page content         │
│                                 │
├─────────────────────────────────┤
│ optional sticky primary action  │
├─────────────────────────────────┤
│ four-item bottom navigation     │
└─────────────────────────────────┘
```

The visual direction remains dark and compact, with raised dark surfaces, strong
primary text, quieter supporting text, rounded chips and an original Kindlelise
accent system. Exact source colours, icons and trade dress are excluded.

### 4.2 Shared behaviour

- Respect device safe areas and the on-screen keyboard.
- Keep bottom navigation stable on primary destinations only.
- Use back/dismiss navigation on detail and creation pages.
- Never let a sticky action cover the final row.
- Express selection through text, shape or icon as well as colour.
- Give every icon an accessible name and every control a suitable touch target.
- Design loading, empty, error, offline, blocked and restricted states.
- Keep message drafts, reports and private data out of external previews.
- Treat server permission as authoritative; hiding a button is not enforcement.

## 5. Primary navigation

The obsolete Intentions destination is removed. The existing compact bottom-bar
shape is retained with four implemented destinations:

| Position | Destination | Purpose |
| ---: | --- | --- |
| 1 | Discover | Verified-profile grid in permitted broad areas. |
| 2 | Plans | Approved future plans and the user's own plan states. |
| 3 | Messages | Direct conversations only. |
| 4 | Profile | Own account, profile editing, verification and premium. |

```text
[ Discover ]    [ Plans ]    [ Messages ]    [ Profile ]
```

Block and report actions remain contextual on profiles, plans and conversations.
They are never premium-only.

## 6. Sign-up and sign-in

### 6.1 Sign-up

```text
┌─────────────────────────────────┐
│            Kindlelise           │
├─────────────────────────────────┤
│ Create an account               │
│                                 │
│ Email                           │
│ [_____________________________] │
│ Password                        │
│ [_____________________________] │
│ Confirm password                │
│ [_____________________________] │
│                                 │
│          [Create account]       │
│ Already registered? Sign in     │
└─────────────────────────────────┘
```

Successful registration creates an unverified profile. Copy explains that staff
verification is required before discovery, plans or messages become available.

### 6.2 Sign-in

```text
┌─────────────────────────────────┐
│            Kindlelise           │
├─────────────────────────────────┤
│ Sign in                         │
│                                 │
│ Email                           │
│ [_____________________________] │
│ Password                        │
│ [_____________________________] │
│                                 │
│               [Sign in]         │
│ Need an account? Create one     │
└─────────────────────────────────┘
```

Errors do not reveal whether a particular email is registered. Registration and
sign-in canonicalise the supplied email to lowercase through Django authentication.

## 7. Own account and profile editing

### 7.1 Own account/profile

Reference shape: captures 06, 10 and 14.

```text
┌─────────────────────────────────┐
│ Profile                  [edit] │
│                                 │
│       profile summary           │
│       display name              │
│       broad area                │
├─────────────────────────────────┤
│ Verification: Pending/Verified  │
│ Availability: Free now/Not set  │
│ Interests                       │
│ [interest] [interest]           │
│ About                           │
│ biography text                  │
├─────────────────────────────────┤
│ My plans                     [>]│
│ Premium                      [>]│
│ [Sign out]                      │
├─────────────────────────────────┤
│ Discover  Plans  Messages  Profile│
└─────────────────────────────────┘
```

There is no profile image, dark-profile mode, contact-preference model, safety
centre or blocked-accounts management page in this MVP.

Sign out is a CSRF-protected POST action. It is displayed as a button even when
the visual treatment is intentionally quiet.

### 7.2 Edit profile

The long sectioned-form shape is retained while removed fields are replaced with
approved profile fields.

```text
┌─────────────────────────────────┐
│ [back]       Edit profile       │
├─────────────────────────────────┤
│ Display name              0/…   │
│ Biography                 0/…   │
│ Broad area                   [>]│
│ Interests                    [>]│
├─────────────────────────────────┤
│ AVAILABILITY                    │
│ Free now                    [●] │
│ Available from              [>] │
│ Today · Tomorrow · This week    │
│ As and when · Add later         │
├─────────────────────────────────┤
│ ACCOUNT                         │
│ Verification status             │
│ Premium status               [>]│
├─────────────────────────────────┤
│              [Save changes]     │
└─────────────────────────────────┘
```

The form never exposes staff verification or Stripe fields as editable input.
Availability is optional during profile completion. The fixed relative choice is
converted to one `available_from` start; there is no separate stored switch.

## 8. Public profile

Reference shape: captures 07–08. The large upper panel is retained as a profile
identity surface rather than an uploaded image.

```text
┌─────────────────────────────────┐
│ [close]            [••• actions]│
│                                 │
│       profile identity          │
│       display name              │
│       broad area                │
│                                 │
├─────────────────────────────────┤
│ Display name        [verified]  │
│ Broad area                      │
│ [interest] [interest] [interest]│
│                                 │
│ About                           │
│ biography text                  │
│ Free now, when start arrived    │
│                                 │
│ [ Message ] [ Block ] [ Report ]│
└─────────────────────────────────┘
```

Rules:

- Do not show exact distance, coordinates or movement.
- Messaging requires no swipe or mutual match.
- Block and report remain reachable even though their server rules differ.
- Do not expose health, sexual, ethnicity, weight, private-home, social-handle or
  profile-view fields.

## 9. Discovery grid and filters

### 9.1 Discovery grid

Reference shape: captures 15–16. The dense three-column shape is deliberately
retained; every cell is now the same implemented object type: a verified profile.

```text
┌─────────────────────────────────┐
│ [profile] [ Discover profiles ] │
│ [filters] [Area] [Interests] →  │
├──────────┬──────────┬───────────┤
│ profile  │ profile  │ profile   │
│ card     │ card     │ card      │
├──────────┼──────────┼───────────┤
│ profile  │ profile  │ profile   │
│ card     │ card     │ card      │
├──────────┼──────────┼───────────┤
│ profile  │ profile  │ profile   │
│ card     │ card     │ card      │
├──────────┴──────────┴───────────┤
│ Discover  Plans  Messages  Profile│
└─────────────────────────────────┘
```

Each card may show display name, broad area, permitted interests, current
available-now state and verification. There are no plan cards, invitation cards,
distance bands, paid placement or hidden-result counts.

### 9.2 Filter sheet

The existing compact bottom-sheet shape is retained with only implemented fields.

```text
┌─────────────────────────────────┐
│ Filters                   Clear │
│ Broad area                  [>] │
│ Interests                   [>] │
│ Free now                    [●] │
│                                 │
│            [Apply filters]      │
└─────────────────────────────────┘
```

Free accounts can use their current broad area and at most two interests. Premium
accounts can use configured nearby named areas and at most five interests.
Premium never changes verification or mutual-block exclusions.
Area controls show labels from the stable keys and nearby mapping owned by
`settings.py`; they do not accept arbitrary area text. The interest control uses
Coffee, Walking, Museums, Live music, Cinema, Food, Games and Study from the
reviewed initial data migration.

## 10. Plan list

Reference shape: capture 05.

```text
┌─────────────────────────────────┐
│ Plans                    [+ New]│
│ [Upcoming] [My plans]         → │
├─────────────────────────────────┤
│ plan cards or strong empty state│
│                                 │
│ “No approved plans available”  │
│ [Create a plan]                 │
├─────────────────────────────────┤
│ Discover  Plans  Messages  Profile│
└─────────────────────────────────┘
```

Upcoming contains approved future plans. My plans may also show the owner's
pending, rejected and cancelled plans. Plans do not appear in the profile grid.

## 11. Plan creation and editing

The established long-form shape is retained with the single manual-review model.

```text
┌─────────────────────────────────┐
│ [back]       Create plan        │
├─────────────────────────────────┤
│ Plan title                      │
│ Description                     │
│ Public place                    │
│ Public evidence URL             │
│ Start date and time             │
│ Capacity                        │
│                                 │
│ Review notice: staff will open  │
│ the URL and check the place.    │
│                                 │
│       [Submit for review]       │
└─────────────────────────────────┘
```

The page has no technical URL status, supporting source, navigation source,
automated anchor decision, versioned evidence or originating circle.

Plan states shown in plain language:

```text
Pending review
Approved
Rejected
Cancelled
Past (derived from start time)
```

Changing an approved plan's public URL, public place or start time before anybody
joins returns it to Pending review. After the first successful join, the entire
plan is read-only except cancellation.

## 12. Plan detail and participation

The existing plan-detail card shape is retained with direct join controls.

```text
┌─────────────────────────────────┐
│ [back] Plan       [Edit] [•••]  │
├─────────────────────────────────┤
│ title and owner                 │
│ description                     │
│ established public place        │
│ date and time                   │
│ public evidence URL      [Open] │
│ capacity / joined count         │
│ status                          │
│                                 │
│ [Join plan]                     │
│ or [Join again] / [Leave plan]  │
│ owner: [Cancel plan]            │
│ [Report owner]                  │
└─────────────────────────────────┘
```

`Edit` is visible only to the owner before the first successful join. It opens the
same long-form shape with the heading `Edit plan` and action `Save changes`. The
owner cannot join their own plan. A participant who previously left sees `Join
again` only when the ordinary joining rules still pass. After the first join,
show:

> This plan can no longer be edited because someone has joined.

Pending and rejected unlocked plans may show Edit; saving a rejected plan
resubmits it as Pending review. Cancelled plans never show Edit and cannot be
reactivated. Capacity counts participant places only, so the owner does not consume
a place.

Manual-review explanation:

> Staff manually reviewed the public place and URL. Kindlelise does not preserve
> the reviewed webpage, prove that the venue is safe or guarantee that the page
> has not changed.

There are no request, invitation or participation-offer states.

Cancellation opens a short confirmation before the CSRF-protected POST. It
explains that the plan will disappear from public plan lists and cannot accept
future joins, while existing participation history is retained.

## 13. Inbox

Reference shape: capture 09. The row density remains; obsolete conversation tabs
and circle rows are removed.

```text
┌─────────────────────────────────┐
│ Messages                        │
│ [Recent]                        │
├─────────────────────────────────┤
│ name    safe preview       time │
│         direct message      (2) │
├─────────────────────────────────┤
│ name    safe preview       time │
│         direct message          │
├─────────────────────────────────┤
│ ...                             │
├─────────────────────────────────┤
│ Discover  Plans  Messages  Profile│
└─────────────────────────────────┘
```

Only mutually unblocked direct conversations render. There are no group, social-
circle, album, advertisement or safety-discussion rows.

## 14. Direct conversation and AI draft editing

### 14.1 Conversation

```text
┌─────────────────────────────────┐
│ [back] Display name       [•••] │
├─────────────────────────────────┤
│ received message          [•••]│
│                    sent message │
│ received message          [•••]│
│                                 │
│                                 │
├─────────────────────────────────┤
│ Message draft…                 │
│ [Fix grammar] [Improve clarity]│
│                       [Send]    │
└─────────────────────────────────┘
```

Every read and send rechecks membership, active verification and mutual blocking.
The conversation actions menu contains Block and Report. The contextual menu on
an eligible received message contains `Report this message`; it opens the existing
report page with that message offered as server-validated context. It does not
create another route or expose an arbitrary message identifier field.

### 14.2 AI suggestion state

The AI action belongs to this conversation and never becomes a general writing
endpoint.

```text
┌─────────────────────────────────┐
│ Edit unsent draft              │
├─────────────────────────────────┤
│ Only this unsent draft goes to │
│ Ollama Cloud. No profile or    │
│ previous messages are included.│
│                                 │
│ Original draft                 │
│ [original text______________]  │
│                                 │
│ Suggested draft                │
│ [suggested text_____________]  │
│                                 │
│ [Keep original] [Use suggestion]│
└─────────────────────────────────┘
```

- AI buttons request a suggestion only; they never send a message.
- Empty or over-message-limit output is rejected.
- Failure preserves the original draft.
- Accepted text returns to the ordinary composer and is validated again.
- The user presses Send manually.

## 15. Block flow

The block control opens a focused confirmation while preserving the existing
rounded modal/action-sheet grammar.

```text
┌─────────────────────────────────┐
│ Block this user?                │
├─────────────────────────────────┤
│ Blocking removes both users    │
│ from each other's discovery and│
│ stops direct messages.         │
│                                 │
│ [Cancel]              [Block]  │
└─────────────────────────────────┘
```

The server rechecks the target. The blocked account receives no notification.

## 16. Private report flow

```text
┌─────────────────────────────────┐
│ [back]      Report user         │
├─────────────────────────────────┤
│ Category                    [>] │
│ Description                    │
│ [____________________________] │
│ [____________________________] │
│                                 │
│ Optional related item          │
│ [This plan / conversation /    │
│  message, when available]      │
│                                 │
│ This report is private. It does│
│ not by itself prove wrongdoing.│
│                                 │
│       [Submit private report]  │
└─────────────────────────────────┘
```

The related item comes from server-approved page context. The user cannot enter
an arbitrary object ID. Both accounts must be connected to a referenced plan as
owner or participant. A conversation must contain both accounts. A referenced
message must belong to that conversation and have been visible to the reporter.

### 16.1 Report confirmation

The same report-page shape renders a small completion state after a successful
submission:

```text
┌─────────────────────────────────┐
│          Report received        │
├─────────────────────────────────┤
│ Your report was submitted       │
│ privately to authorised staff.  │
│ The reported user is not told.  │
│                                 │
│             [Return]            │
└─────────────────────────────────┘
```

## 17. Stripe premium panel

The account-drawer and comparison-card shapes are adapted to the one implemented
subscription, without copied product names or card fields.

This is a panel or rendering mode inside the existing account page and
`account.html`; it is not a separate route or template.

```text
┌─────────────────────────────────┐
│ [back]          Premium         │
├─────────────────────────────────┤
│ 30 days free                    │
│ Then £4.99 for one year         │
│ Renews yearly unless cancelled  │
│ No payment details upfront      │
│                                 │
│ Status: Free/Trial/Payment due/ │
│         Premium                 │
│ Access until: date, if active   │
│                                 │
│ Premium includes:              │
│ • configured nearby broad areas│
│ • up to five interest filters  │
│                                 │
│ It does not change verification│
│ blocking or reporting rules.   │
│                                 │
│ [Start 30-day trial]            │
│ or [Pay £4.99 for one year]     │
│ or [Manage subscription]        │
└─────────────────────────────────┘
```

Only the action appropriate to the server-derived state is rendered. `Start
30-day trial` is available only before that local account has recorded Stripe
history. `Pay £4.99 for one year` or `Manage subscription` opens Stripe's hosted
invoice/customer-portal surface after the trial; a second trial is never offered.

Checkout, post-trial payment and subscription management open Stripe-hosted
pages. Kindlelise never renders or stores card fields, and returning from Checkout
does not itself prove premium access. Stripe creates the first annual invoice when
the no-card trial ends. The interface does not promise an email notification
unless the applicable Stripe email setting is enabled.

Checkout success, Checkout cancellation and portal-return destinations are built
by the server from the named account route. No browser field or query parameter
chooses those destinations.

After a Checkout return, the account page may show `Waiting for Stripe
confirmation` while access remains Free. A verified trialing webhook changes the
display to Trial; only a verified paid invoice changes an ended trial to paid
Premium. An active subscription status without paid-invoice evidence cannot do
so. Accounts with a recorded Stripe customer may use Manage subscription even
when current premium access is inactive.

## 18. Empty, error and restricted states

Every list/detail family keeps the strong centred-state grammar from the supplied
references.

| State | Plain-language presentation | Safe next action |
| --- | --- | --- |
| Unverified | “Your profile is waiting for staff verification.” | Return to Profile. |
| Empty discovery | “No profiles match these area and interest filters.” | Clear filters. |
| Empty plans | “No approved plans are available.” | Create a plan. |
| Empty inbox | “No direct conversations yet.” | Return to Discover. |
| Blocked/restricted | Generic unavailable state; do not reveal the reason. | Return safely. |
| Provider failure | Preserve form/draft and show a short retry message. | Retry manually. |
| Offline | Preserve unsent browser input where safe. | Retry when connected. |

Restricted and missing records use the same presentation where revealing the
difference would leak account, plan or conversation existence.

## 19. Accessibility

- Use semantic headings, labels and ordinary form controls.
- Maintain logical focus order and return focus after modal closure.
- Announce validation errors and AI suggestion arrival without moving focus
  unexpectedly.
- Never depend on colour alone for verification, plan or subscription state.
- Keep touch controls large enough and sticky actions clear of device safe areas.
- Ensure message bubbles and secondary text meet contrast requirements.
- Provide text labels for Block, Report, Stripe and AI actions.
- Respect reduced-motion preferences.

## 20. Layer ownership shown by the wireframes

The student MVP uses one Django application. Page behaviour follows the existing
file responsibilities rather than obsolete production domains.

| File | Owns |
| --- | --- |
| `models.py` | Stores durable data and database constraints. |
| `forms.py` | Validates untrusted user input. |
| `policies.py` | Answers server-side permission questions. |
| `services.py` | Changes saved state and owns transactions. |
| `selectors.py` | Reads authorised page data without changing it. |
| `views.py` | Translates HTTP requests and responses. |
| `admin.py` | Performs staff verification—including the User Permissions checkbox—and manual plan review. |
| `ai_message_editor.py` | Requests one bounded unsent-draft suggestion. |

Templates display only values returned by authorised views/selectors. They do not
re-create policy decisions.

## 21. Explicit exclusions

These wireframes do not authorise:

- private signals, threshold opportunities, invitations or social circles;
- group conversations, safety circles, blind matching or meeting check-ins;
- sealed meet artifacts, plan version lineages or participation offers;
- automated URL fetching, substantiation, anchor decisions or preserved pages;
- profile images, albums, expiring media or dark-profile modes;
- exact coordinates, distance bands, direction or movement history;
- plan cards or private invitations inside the discovery profile grid;
- message attachments, reactions, read receipts, live delivery or editing sent
  messages;
- health, sexual, ethnicity, weight, private-home or external-social fields;
- ads, boosts, paid rank, multiple subscription tiers or inline card collection;
- AI access to conversation history, profiles or automatic sending;
- arbitrary report reference IDs or reports visible to the reported account.

A random map pin, private address, payment link or personal post cannot establish
the plan's public place during staff review.

## 22. Acceptance checklist

A student MVP screen is acceptable only if it:

1. retains the established compact mobile shapes without copying source branding;
2. exposes only the four implemented primary destinations;
3. shows only verified profile cards in broad-area discovery;
4. limits filters to broad area, interests and optional available-now state;
5. contains no uploaded-image or dark-profile control;
6. shows the single public URL and honest manual-review limitation on plans;
7. uses Join, Join again, Leave and confirmed Cancel without invitations or
   participation offers;
8. makes the entire plan read-only after the first successful join;
9. exposes owner editing only before the first join;
10. renders direct conversations only and rechecks mutual blocks;
11. keeps Ollama editing conversation-bound, draft-only and manually accepted;
12. makes Block and private Report plainly reachable, including an eligible
    message-specific report action;
13. uses only server-approved report references and shows private confirmation;
14. presents one 30-day trial followed by a Stripe-hosted GBP 4.99 yearly
    Premium subscription, without a repeat trial;
15. explains that premium never weakens verification, blocking or reporting;
16. treats the premium comparison as an account-page mode, not a new route;
17. includes loading, empty, error, offline and restricted states;
18. remains within `docs/VERTICAL_SLICE.md` and adds no backend behaviour.
