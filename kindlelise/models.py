"""Store the eleven durable Kindlelise entities and their database truth."""

from pathlib import Path
from uuid import uuid4

from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.db.models import F, Q
from django.utils import timezone


def profile_image_upload_path(_profile, filename):
    """Return a non-identifying random path with the validated image suffix."""
    suffix = Path(filename).suffix.lower()
    return f"profile-images/{uuid4().hex}{suffix}"


def plan_thumbnail_upload_path(_plan, filename):
    """Return a non-identifying random path for one normalized plan thumbnail."""
    suffix = Path(filename).suffix.lower()
    return f"plan-thumbnails/{uuid4().hex}{suffix}"


class Interest(models.Model):
    """Store the small staff-seeded interest vocabulary."""

    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        """Return the controlled interest name in forms and staff screens."""
        return self.name


class Profile(models.Model):
    """Store public profile details, broad area and staff verification state."""

    class AvailabilityStart(models.TextChoices):
        TODAY = "today", "Today"
        TOMORROW = "tomorrow", "Tomorrow"
        THIS_WEEK = "this_week", "This week"
        AS_AND_WHEN = "as_and_when", "As and when"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    profile_image = models.ImageField(
        upload_to=profile_image_upload_path,
        blank=True,
        default="",
    )
    display_name = models.CharField(max_length=80, blank=True, default="")
    title_statement = models.CharField(max_length=120, blank=True, default="")
    biography = models.TextField(max_length=500, blank=True, default="")
    broad_area = models.CharField(max_length=20, blank=True, default="")
    broad_areas = ArrayField(
        models.CharField(max_length=20),
        blank=True,
        default=list,
    )
    interests = models.ManyToManyField(Interest, blank=True, related_name="profiles")
    availability_start = models.CharField(
        max_length=11,
        choices=AvailabilityStart.choices,
        blank=True,
        default="",
    )
    available_from = models.DateTimeField(null=True, blank=True)
    is_verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="profiles_verified",
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(availability_start="", available_from__isnull=True)
                    | (~Q(availability_start="") & Q(available_from__isnull=False))
                ),
                name="profile_availability_fields_match",
            ),
            models.CheckConstraint(
                condition=(
                    Q(
                        is_verified=True,
                        verified_at__isnull=False,
                        verified_by__isnull=False,
                    )
                    | Q(
                        is_verified=False,
                        verified_at__isnull=True,
                        verified_by__isnull=True,
                    )
                ),
                name="profile_verification_fields_match",
            )
        ]
        indexes = [
            models.Index(
                fields=["is_verified", "broad_area"],
                name="profile_verified_area_idx",
            )
        ]

    def is_available_now(self, at_time):
        """Return true only after this profile's availability start has arrived.

        Inputs: a timezone-aware time used as the comparison point.
        Returns: whether available_from exists and is no later than that time.
        Changes: none.
        Privacy: does not expose or change the stored start time.
        """
        return self.available_from is not None and self.available_from <= at_time


class Plan(models.Model):
    """Store one public-place plan and its approval and first-join lock state."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        CANCELLED = "cancelled", "Cancelled"

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_plans",
    )
    title = models.CharField(max_length=120)
    description = models.TextField(max_length=1_000)
    public_place = models.CharField(max_length=200)
    public_url = models.URLField(max_length=500)
    thumbnail_image = models.ImageField(
        upload_to=plan_thumbnail_upload_path,
        blank=True,
        default="",
    )
    starts_at = models.DateTimeField()
    capacity = models.PositiveIntegerField()
    status = models.CharField(
        max_length=9,
        choices=Status.choices,
        default=Status.PENDING,
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="plans_approved",
    )
    meeting_details_locked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(capacity__gt=0),
                name="plan_capacity_greater_than_zero",
            ),
            models.CheckConstraint(
                condition=(
                    Q(
                        status="approved",
                        approved_at__isnull=False,
                        approved_by__isnull=False,
                    )
                    | (
                        ~Q(status="approved")
                        & Q(approved_at__isnull=True, approved_by__isnull=True)
                    )
                ),
                name="plan_approval_fields_match",
            ),
        ]
        indexes = [
            models.Index(
                fields=["status", "starts_at"],
                name="plan_status_starts_idx",
            )
        ]

    def is_open_for_joining(self, at_time):
        """Return true only when this plan is currently open for another join.

        Inputs: a timezone-aware time used to determine whether the plan is future.
        Returns: whether approval, time, terminal state and capacity permit a join.
        Changes: none; this method never creates participation.
        """
        if self.status != self.Status.APPROVED or self.starts_at <= at_time:
            return False
        joined_count = self.participations.filter(
            status=Participation.Status.JOINED
        ).count()
        return joined_count < self.capacity


class Participation(models.Model):
    """Store one account's joined or ended participation in one plan."""

    class Status(models.TextChoices):
        JOINED = "joined", "Joined"
        LEFT = "left", "Left"

    plan = models.ForeignKey(
        Plan,
        on_delete=models.PROTECT,
        related_name="participations",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="plan_participations",
    )
    status = models.CharField(
        max_length=6,
        choices=Status.choices,
        default=Status.JOINED,
    )
    joined_at = models.DateTimeField(default=timezone.now)
    left_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["plan", "user"],
                name="participation_plan_user_unique",
            ),
            models.CheckConstraint(
                condition=(
                    Q(status="joined", left_at__isnull=True)
                    | Q(status="left", left_at__isnull=False)
                ),
                name="participation_left_at_matches_status",
            ),
        ]
        indexes = [
            models.Index(
                fields=["plan", "status"],
                name="particip_plan_status_idx",
            ),
            models.Index(
                fields=["user", "status"],
                name="particip_user_status_idx",
            ),
        ]


class Conversation(models.Model):
    """Store one direct conversation with the lower account ID first."""

    first_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="conversations_as_first_user",
    )
    second_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="conversations_as_second_user",
    )
    updated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=~Q(first_user=F("second_user")),
                name="conversation_users_differ",
            ),
            models.CheckConstraint(
                condition=Q(first_user__lt=F("second_user")),
                name="conversation_users_ordered",
            ),
            models.UniqueConstraint(
                fields=["first_user", "second_user"],
                name="conversation_pair_unique",
            ),
        ]
        indexes = [
            models.Index(
                fields=["first_user", "updated_at"],
                name="conv_first_updated_idx",
            ),
            models.Index(
                fields=["second_user", "updated_at"],
                name="conv_second_updated_idx",
            ),
        ]

    def includes_account(self, user):
        """Return true only when the supplied account is one conversation member.

        Inputs: a Django user that may or may not belong to the pair.
        Returns: whether its primary key equals either stored member ID.
        Changes: none.
        Privacy: returns only membership and never conversation content.
        """
        return user is not None and user.pk in {
            self.first_user_id,
            self.second_user_id,
        }


class Message(models.Model):
    """Store one bounded plain-text message inside a direct conversation."""

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.PROTECT,
        related_name="messages",
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="sent_messages",
    )
    body = models.TextField(max_length=1_000)
    sent_at = models.DateTimeField(default=timezone.now)

    class Meta:
        indexes = [
            models.Index(
                fields=["conversation", "sent_at"],
                name="message_convo_sent_idx",
            )
        ]


class Notification(models.Model):
    """Store one unread/read alert for an incoming message or plan join."""

    class Kind(models.TextChoices):
        MESSAGE = "message", "Message"
        PLAN_JOIN = "plan_join", "Plan join"

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="notifications",
    )
    kind = models.CharField(max_length=9, choices=Kind.choices)
    message = models.ForeignKey(
        Message,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="notifications",
    )
    participation = models.ForeignKey(
        Participation,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="notifications",
    )
    created_at = models.DateTimeField(default=timezone.now)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(
                        kind="message",
                        message__isnull=False,
                        participation__isnull=True,
                    )
                    | Q(
                        kind="plan_join",
                        message__isnull=True,
                        participation__isnull=False,
                    )
                ),
                name="notification_context_matches_kind",
            )
        ]
        indexes = [
            models.Index(
                fields=["recipient", "read_at", "created_at"],
                name="notification_unread_idx",
            )
        ]


class Block(models.Model):
    """Store one directional block between two different accounts."""

    blocker = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="blocks_created",
    )
    blocked_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="blocks_received",
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=~Q(blocker=F("blocked_user")),
                name="block_users_differ",
            ),
            models.UniqueConstraint(
                fields=["blocker", "blocked_user"],
                name="block_direction_unique",
            ),
        ]


class Report(models.Model):
    """Store one private statement with at most one optional context reference."""

    class Category(models.TextChoices):
        HARASSMENT = "harassment", "Harassment"
        SPAM = "spam", "Spam"
        MISLEADING_PLAN = "misleading_plan", "Misleading plan"
        SAFETY_CONCERN = "safety_concern", "Safety concern"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        RECEIVED = "received", "Received"
        REVIEWED = "reviewed", "Reviewed"

    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="reports_submitted",
    )
    reported_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="reports_received",
    )
    category = models.CharField(max_length=15, choices=Category.choices)
    description = models.TextField(max_length=2_000)
    reported_plan = models.ForeignKey(
        Plan,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="reports",
    )
    reported_conversation = models.ForeignKey(
        Conversation,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="reports",
    )
    reported_message = models.ForeignKey(
        Message,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="reports",
    )
    status = models.CharField(
        max_length=8,
        choices=Status.choices,
        default=Status.RECEIVED,
    )
    received_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=~Q(reporter=F("reported_user")),
                name="report_users_differ",
            ),
            models.CheckConstraint(
                condition=(
                    Q(
                        reported_plan__isnull=True,
                        reported_conversation__isnull=True,
                    )
                    | Q(
                        reported_plan__isnull=True,
                        reported_message__isnull=True,
                    )
                    | Q(
                        reported_conversation__isnull=True,
                        reported_message__isnull=True,
                    )
                ),
                name="report_at_most_one_context",
            ),
        ]
        indexes = [
            models.Index(
                fields=["status", "received_at"],
                name="report_status_received_idx",
            )
        ]


class PlatformSubscription(models.Model):
    """Store the Stripe subscription state used for current Premium access."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="platform_subscription",
    )
    stripe_customer_id = models.CharField(
        max_length=255,
        unique=True,
        null=True,
        blank=True,
    )
    stripe_subscription_id = models.CharField(
        max_length=255,
        unique=True,
        null=True,
        blank=True,
    )
    stripe_status = models.CharField(max_length=80, null=True, blank=True)
    access_until = models.DateTimeField(null=True, blank=True)
    latest_provider_event_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def has_premium_access(self):
        """Return true only for an allowed Stripe state with future access time.

        Returns: whether status is active or trialing and access_until is future.
        Changes: none; checkout creation alone never changes this decision.
        Privacy: returns no Stripe identifier or billing data.
        """
        return (
            self.stripe_status in {"active", "trialing"}
            and self.access_until is not None
            and self.access_until > timezone.now()
        )


class StripeWebhookReceipt(models.Model):
    """Record one processed Stripe event so it cannot be processed twice."""

    stripe_event_id = models.CharField(max_length=255, unique=True)
    event_type = models.CharField(max_length=80)
    provider_created_at = models.DateTimeField()
    processed_at = models.DateTimeField(null=True, blank=True)
