"""Map the implemented Kindlelise product routes to their approved views."""

from django.urls import path

from kindlelise import views

urlpatterns = [
    path("", views.home_page, name="home"),
    path("sign-up/", views.sign_up_page, name="sign_up"),
    path("sign-in/", views.sign_in_page, name="sign_in"),
    path("sign-out/", views.sign_out_user, name="sign_out"),
    path("account/", views.account_page, name="account"),
    path("account/profile/edit/", views.edit_profile_page, name="profile_edit"),
    path("discover/", views.discovery_page, name="discover"),
    path("profiles/<int:profile_id>/", views.profile_page, name="profile_detail"),
    path(
        "profiles/<int:profile_id>/image/",
        views.profile_image_file,
        name="profile_image",
    ),
    path("plans/", views.plan_list_page, name="plan_list"),
    path("plans/create/", views.create_plan_page, name="plan_create"),
    path(
        "plans/fetch-details/",
        views.request_plan_metadata,
        name="plan_metadata_fetch",
    ),
    path(
        "plans/<int:plan_id>/image/",
        views.plan_thumbnail_file,
        name="plan_thumbnail",
    ),
    path("plans/<int:plan_id>/", views.plan_detail_page, name="plan_detail"),
    path("plans/<int:plan_id>/edit/", views.edit_plan_page, name="plan_edit"),
    path("plans/<int:plan_id>/join/", views.join_plan, name="plan_join"),
    path("plans/<int:plan_id>/leave/", views.leave_plan, name="plan_leave"),
    path("plans/<int:plan_id>/cancel/", views.cancel_plan, name="plan_cancel"),
    path("messages/", views.inbox_page, name="inbox"),
    path(
        "conversations/<int:conversation_id>/",
        views.conversation_page,
        name="conversation_detail",
    ),
    path(
        "profiles/<int:profile_id>/conversation/start/",
        views.start_direct_conversation,
        name="direct_conversation_start",
    ),
    path(
        "conversations/<int:conversation_id>/messages/send/",
        views.send_conversation_message,
        name="conversation_message_send",
    ),
    path(
        "conversations/<int:conversation_id>/message-edit-suggestion/",
        views.request_conversation_message_edit_suggestion,
        name="conversation_message_edit_suggestion",
    ),
    path(
        "profiles/<int:profile_id>/block/",
        views.block_profile_from_discovery_and_messages,
        name="profile_block_messages_and_discovery",
    ),
    path(
        "profiles/<int:profile_id>/report/",
        views.report_user_page,
        name="report_create",
    ),
    path(
        "account/premium/checkout/",
        views.start_premium_subscription_checkout,
        name="premium_subscription_checkout",
    ),
    path(
        "account/premium/portal/",
        views.open_premium_subscription_portal,
        name="premium_subscription_portal",
    ),
    path(
        "stripe/webhook/",
        views.receive_and_verify_stripe_webhook,
        name="stripe_webhook",
    ),
]
