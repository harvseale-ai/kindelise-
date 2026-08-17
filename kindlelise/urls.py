"""Map the implemented Kindelise product routes to their approved views."""

# KEYWORD: route — a web address connected to the page code that should answer it.
# KEYWORD: path — Django's helper for joining one address pattern to one view function.
# KEYWORD: name — a stable label used to build links without writing the address again.

# WHY: Keeps every public application address beside the page function responsible for it.
from django.urls import path

from kindlelise.views import accounts, billing, discovery, messages, plans, safety

# =============================================================================
# APPLICATION PAGE ROUTES
# Connects each Kindelise address to the page or action responsible for it.
# =============================================================================

# KEYWORD: urlpatterns — the list Django reads from top to bottom when matching an address.
# WHY: Gives each page and action one stable name so templates do not need to repeat raw addresses.
urlpatterns = [
    # -------------------------------------------------------------------------
    # ENTRY, GUIDE, AND NOTIFICATIONS
    # -------------------------------------------------------------------------

    # WHY: Groups general help, notification, and account-entry pages before signed-in product pages.
    # WHY: The empty address is the first page visitors reach at the site root.
    # Code route: kindlelise/urls.py > kindlelise/views/accounts.py (home_page) > redirect to the permitted starting page.
    path("", accounts.home_page, name="home"),
    # WHY: Keeps the plain-language app guide at a short address that can be linked from the top bar.
    # Code route: kindlelise/urls.py > kindlelise/views/accounts.py (app_guide_page) > templates/guide.html.
    path("guide/", accounts.app_guide_page, name="guide"),
    # WHY: Shows the signed-in person's message and plan activity in one place.
    # Code route: kindlelise/urls.py > kindlelise/views/accounts.py (notifications_page) > kindlelise/selectors/accounts.py > templates/notifications.html.
    path("notifications/", accounts.notifications_page, name="notifications"),
    # WHY: Separates the action that marks alerts read from the page that merely displays them.
    # Code route: kindlelise/urls.py > kindlelise/views/accounts.py (mark_notifications_read) > kindlelise/services/accounts.py > redirect to notifications.
    path(
        "notifications/read/",
        accounts.mark_notifications_read,
        name="notifications_read",
    ),
    # WHY: Keeps creating an account separate from signing into an existing one.
    # Code route: kindlelise/urls.py > kindlelise/views/accounts.py (sign_up_page) > kindlelise/forms.py > kindlelise/services/accounts.py > templates/account.html.
    path("sign-up/", accounts.sign_up_page, name="sign_up"),
    # WHY: Gives Django's sign-in form one predictable address for successful and failed attempts.
    # Code route: kindlelise/urls.py > kindlelise/views/accounts.py (sign_in_page) > Django AuthenticationForm > templates/account.html.
    path("sign-in/", accounts.sign_in_page, name="sign_in"),
    # WHY: Uses its own action address so signing out is deliberate rather than caused by opening a page.
    # Code route: kindlelise/urls.py > kindlelise/views/accounts.py (sign_out_user) > Django logout > redirect to sign-in.
    path("sign-out/", accounts.sign_out_user, name="sign_out"),

    # -------------------------------------------------------------------------
    # ACCOUNT, PROFILES, AND DISCOVERY
    # -------------------------------------------------------------------------

    # WHY: Keeps the signed-in owner's account and editing addresses together.
    # WHY: `/account/` is the main address for the signed-in person's private account page.
    # Code route: kindlelise/urls.py > kindlelise/views/accounts.py (account_page) > kindlelise/selectors/accounts.py > templates/account.html.
    path("account/", accounts.account_page, name="account"),
    # WHY: `/profile/` keeps the familiar shorter link while showing the same private account page.
    # Code route: kindlelise/urls.py > kindlelise/views/accounts.py (account_page) > kindlelise/selectors/accounts.py > templates/account.html.
    path("profile/", accounts.account_page, name="profile"),
    # WHY: Profile changes use a separate address so viewing never accidentally saves form data.
    # Code route: kindlelise/urls.py > kindlelise/views/accounts.py (edit_profile_page) > kindlelise/forms.py > kindlelise/services/accounts.py > templates/account.html.
    path("account/profile/edit/", accounts.edit_profile_page, name="profile_edit"),
    # WHY: Opens the searchable list of people who meet the current privacy and access rules.
    # Code route: kindlelise/urls.py > kindlelise/views/discovery.py (discovery_page) > kindlelise/forms.py > kindlelise/selectors/discovery.py > templates/discover.html.
    path("discover/", discovery.discovery_page, name="discover"),
    # KEYWORD: <int:profile_id> — accepts a whole number from the address and passes it to the view as `profile_id`.
    # WHY: One shared pattern can display any permitted public profile without defining a route per person.
    # Code route: kindlelise/urls.py > kindlelise/views/discovery.py (profile_page) > kindlelise/selectors/discovery.py > templates/account.html.
    path(
        "profiles/<int:profile_id>/",
        discovery.profile_page,
        name="profile_detail",
    ),
    # WHY: Serves the selected person's stored image through account and privacy checks rather than exposing storage directly.
    # Code route: kindlelise/urls.py > kindlelise/views/accounts.py (profile_image_file) > kindlelise/selectors/discovery.py > protected image response.
    path(
        "profiles/<int:profile_id>/image/",
        accounts.profile_image_file,
        name="profile_image",
    ),

    # -------------------------------------------------------------------------
    # PLANS
    # -------------------------------------------------------------------------

    # WHY: Keeps plan listing, creation, images, details, and state-changing actions under /plans/.
    # WHY: The shortest plan address shows the collection before any one plan is selected.
    # Code route: kindlelise/urls.py > kindlelise/views/plans.py (plan_list_page) > kindlelise/selectors/plans.py > templates/plan.html.
    path("plans/", plans.plan_list_page, name="plan_list"),
    # WHY: Creation has its own form address so it cannot be mistaken for an existing plan number.
    # Code route: kindlelise/urls.py > kindlelise/views/plans.py (create_plan_page) > kindlelise/forms.py > kindlelise/services/plans.py > templates/plan.html.
    path("plans/create/", plans.create_plan_page, name="plan_create"),
    # WHY: Gives the create form a small server action for checking a public URL and returning place details.
    # Code route: kindlelise/urls.py > kindlelise/views/plans.py (request_plan_metadata) > kindlelise/forms.py > kindlelise/plan_metadata.py > JSON response.
    path(
        "plans/fetch-details/",
        plans.request_plan_metadata,
        name="plan_metadata_fetch",
    ),
    # KEYWORD: <int:plan_id> — turns the plan number in the address into the `plan_id` given to the view.
    # WHY: Keeps thumbnail delivery behind the same plan rules used by the rest of the site.
    # Code route: kindlelise/urls.py > kindlelise/views/plans.py (plan_thumbnail_file) > kindlelise/selectors/plans.py > protected image response.
    path(
        "plans/<int:plan_id>/image/",
        plans.plan_thumbnail_file,
        name="plan_thumbnail",
    ),
    # WHY: Shows one plan selected by its saved number.
    # Code route: kindlelise/urls.py > kindlelise/views/plans.py (plan_detail_page) > kindlelise/selectors/plans.py > templates/plan.html.
    path("plans/<int:plan_id>/", plans.plan_detail_page, name="plan_detail"),
    # WHY: Keeps editing separate from viewing and lets the view enforce owner and first-join rules.
    # Code route: kindlelise/urls.py > kindlelise/views/plans.py (edit_plan_page) > kindlelise/forms.py > kindlelise/services/plans.py > templates/plan.html.
    path("plans/<int:plan_id>/edit/", plans.edit_plan_page, name="plan_edit"),
    # WHY: Each plan-changing action has a clear address so permissions are checked again before saving.
    # Code route: kindlelise/urls.py > kindlelise/views/plans.py (join_plan) > kindlelise/selectors/plans.py > kindlelise/services/plans.py > redirect to plan detail.
    path("plans/<int:plan_id>/join/", plans.join_plan, name="plan_join"),
    # WHY: Leaving is separate from joining so participation history is changed in only the intended direction.
    # Code route: kindlelise/urls.py > kindlelise/views/plans.py (leave_plan) > kindlelise/selectors/plans.py > kindlelise/services/plans.py > redirect to plan detail.
    path("plans/<int:plan_id>/leave/", plans.leave_plan, name="plan_leave"),
    # WHY: Cancellation has its own owner-only action and cannot be confused with editing plan details.
    # Code route: kindlelise/urls.py > kindlelise/views/plans.py (cancel_plan) > kindlelise/selectors/plans.py > kindlelise/services/plans.py > redirect to plan detail.
    path("plans/<int:plan_id>/cancel/", plans.cancel_plan, name="plan_cancel"),

    # -------------------------------------------------------------------------
    # MESSAGES
    # -------------------------------------------------------------------------

    # WHY: Keeps the inbox, one conversation, starting a conversation, and sending under clear addresses.
    # WHY: The inbox lists permitted conversations without needing to open their private messages first.
    # Code route: kindlelise/urls.py > kindlelise/views/messages.py (inbox_page) > kindlelise/selectors/messages.py > templates/inbox.html.
    path("messages/", messages.inbox_page, name="inbox"),
    # KEYWORD: <int:conversation_id> — supplies the saved conversation number to the view for membership checks.
    # WHY: Displays one conversation only after confirming the signed-in person belongs to it.
    # Code route: kindlelise/urls.py > kindlelise/views/messages.py (conversation_page) > kindlelise/selectors/messages.py > templates/conversation.html.
    path(
        "conversations/<int:conversation_id>/",
        messages.conversation_page,
        name="conversation_detail",
    ),
    # WHY: Starts or reuses the one private conversation allowed between the signed-in person and this profile.
    # Code route: kindlelise/urls.py > kindlelise/views/messages.py (start_direct_conversation) > kindlelise/selectors/messages.py > kindlelise/services/messages.py > redirect to conversation.
    path(
        "profiles/<int:profile_id>/conversation/start/",
        messages.start_direct_conversation,
        name="direct_conversation_start",
    ),
    # WHY: Sending uses a separate action so simply refreshing the conversation page cannot resend a message.
    # Code route: kindlelise/urls.py > kindlelise/views/messages.py (send_conversation_message) > kindlelise/selectors/messages.py > kindlelise/services/messages.py > redirect to conversation.
    path(
        "conversations/<int:conversation_id>/messages/send/",
        messages.send_conversation_message,
        name="conversation_message_send",
    ),
    # WHY: Sends only the unsent draft and chosen editing goal to the writing helper without storing a new message.
    # Code route: kindlelise/urls.py > kindlelise/views/messages.py (request_conversation_message_edit_suggestion) > kindlelise/forms.py > kindlelise/ai_message_editor.py > JSON response.
    path(
        "conversations/<int:conversation_id>/message-edit-suggestion/",
        messages.request_conversation_message_edit_suggestion,
        name="conversation_message_edit_suggestion",
    ),

    # -------------------------------------------------------------------------
    # BLOCKING AND REPORTING
    # -------------------------------------------------------------------------

    # WHY: Keeps private blocking and reporting actions attached to the affected profile address.
    # WHY: The profile number identifies exactly who the signed-in person wants to block.
    # Code route: kindlelise/urls.py > kindlelise/views/safety.py (block_profile_from_discovery_and_messages) > kindlelise/selectors/safety.py > kindlelise/services/safety.py > redirect to discovery.
    path(
        "profiles/<int:profile_id>/block/",
        safety.block_profile_from_discovery_and_messages,
        name="profile_block_messages_and_discovery",
    ),
    # WHY: Opens the private report form with the reported account already fixed by the server address.
    # Code route: kindlelise/urls.py > kindlelise/views/safety.py (report_user_page) > kindlelise/selectors/safety.py > kindlelise/forms.py > kindlelise/services/safety.py > templates/report.html.
    path(
        "profiles/<int:profile_id>/report/",
        safety.report_user_page,
        name="report_create",
    ),

    # -------------------------------------------------------------------------
    # PREMIUM AND STRIPE
    # -------------------------------------------------------------------------

    # WHY: Keeps Premium checkout and subscription management attached to the signed-in account.
    # WHY: Starts Stripe's hosted payment page without collecting payment details inside Kindelise.
    # Code route: kindlelise/urls.py > kindlelise/views/billing.py (start_premium_subscription_checkout) > kindlelise/services/billing.py > Stripe Checkout redirect.
    path(
        "account/premium/checkout/",
        billing.start_premium_subscription_checkout,
        name="premium_subscription_checkout",
    ),

    # WHY: Opens Stripe's hosted management page for an account that already has a linked customer.
    # Code route: kindlelise/urls.py > kindlelise/views/billing.py (open_premium_subscription_portal) > kindlelise/services/billing.py > Stripe customer portal redirect.
    path(
        "account/premium/portal/",
        billing.open_premium_subscription_portal,
        name="premium_subscription_portal",
    ),
    # KEYWORD: webhook — a fixed address Stripe calls after a payment or subscription change.
    # WHY: Gives Stripe one fixed address where its signed notices can update local Premium access.
    # Code route: kindlelise/urls.py > kindlelise/views/billing.py (receive_and_verify_stripe_webhook) > kindlelise/services/stripe_events.py > HTTP response to Stripe.
    path(
        "stripe/webhook/",
        billing.receive_and_verify_stripe_webhook,
        name="stripe_webhook",
    ),
]
