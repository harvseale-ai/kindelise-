"""Store the eleven durable Kindelise entities and their database truth."""

# KEYWORD: model — the saved shape of one kind of information in the database.
# KEYWORD: constraint — a database rule that prevents an impossible or duplicate saved state.
# KEYWORD: choice — a short fixed list of values that a field is allowed to store.
# KEYWORD: foreign key — a saved link from one row to another saved row.
# KEYWORD: one-to-one — a saved link allowing exactly one related row on each side.
# KEYWORD: many-to-many — a saved link allowing several records on both sides, such as profiles and interests.
# KEYWORD: index — an extra database lookup structure that makes a common search faster.


from pathlib import Path
from uuid import uuid4

from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.db.models import F, Q
from django.utils import timezone


# WHY: Keeps the profile image upload path steps in one named place so they can be understood, checked, and reused.
def profile_image_upload_path(_profile, filename):
    """Return a non-identifying random path with the validated image suffix."""
    # WHY: Keeps only the already checked file ending and discards the visitor's original filename.
    suffix = Path(filename).suffix.lower()

    # WHY: Uses a random name so two uploads cannot overwrite each other or reveal account details.
    return f"profile-images/{uuid4().hex}{suffix}"


# WHY: Keeps the plan thumbnail upload path steps in one named place so they can be understood, checked, and reused.
def plan_thumbnail_upload_path(_plan, filename):
    """Return a non-identifying random path for one normalized plan thumbnail."""
    # WHY: Uses the same non-identifying, collision-resistant naming rule as profile images.
    suffix = Path(filename).suffix.lower()
    return f"plan-thumbnails/{uuid4().hex}{suffix}"


# WHY: Keeps the Interest information and its rules together so they stay consistent.
class Interest(models.Model):
    """Store the small staff-seeded interest vocabulary."""

    # WHY: Stores one short name and prevents staff creating the same interest twice.
    name = models.CharField(max_length=50, unique=True)

    # WHY: Gives staff pages and logs a short, readable name for this saved item.
    def __str__(self):
        """Return the controlled interest name in forms and staff screens."""
        return self.name


# WHY: Keeps the Profile information and its rules together so they stay consistent.
class Profile(models.Model):
    """Store public profile details, broad area and staff verification state."""

    # WHY: Keeps the permitted availability starting points in one clear list.
    class AvailabilityStart(models.TextChoices):
        TODAY = "today", "Today"
        TOMORROW = "tomorrow", "Tomorrow"
        THIS_WEEK = "this_week", "This week"
        AS_AND_WHEN = "as_and_when", "As and when"

    # WHY: Gives each account exactly one profile and removes that profile if its owning account is deleted.
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    # WHY: Stores only the upload location while the image bytes live in the configured media storage.
    profile_image = models.ImageField(
        upload_to=profile_image_upload_path,
        blank=True,
        default="",
    )
    # WHY: Keeps public text bounded so profile cards and pages stay usable.
    display_name = models.CharField(max_length=80, blank=True, default="")
    title_statement = models.CharField(max_length=120, blank=True, default="")
    biography = models.TextField(max_length=500, blank=True, default="")
    # WHY: Retains the first selected area for older code while broad_areas stores every current selection.
    broad_area = models.CharField(max_length=20, blank=True, default="")
    broad_areas = ArrayField(
        models.CharField(max_length=20),
        blank=True,
        default=list,
    )
    # WHY: Lets profiles select several controlled interests without copying interest names into each profile.
    interests = models.ManyToManyField(Interest, blank=True, related_name="profiles")
    availability_start = models.CharField(
        max_length=11,
        choices=AvailabilityStart.choices,
        blank=True,
        default="",
    )
    # WHY: Stores the real starting moment used by Free now filtering rather than calculating it on every visit.
    available_from = models.DateTimeField(null=True, blank=True)

    # WHY: Keeps the verification decision together with who made it and when.
    is_verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="profiles_verified",
    )

    # WHY: Keeps database or form rules beside the information they control.
    class Meta:
        # WHY: Enforces linked availability and verification fields even if code outside a form writes to the database.
        constraints = [
            # WHY: Prevents an availability label without a start time, or a start time without a label.
            models.CheckConstraint(
                condition=(
                    Q(availability_start="", available_from__isnull=True)
                    | (~Q(availability_start="") & Q(available_from__isnull=False))
                ),
                name="profile_availability_fields_match",
            ),
            # WHY: Prevents partial verification records such as verified with no reviewer or time.
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
        # WHY: Speeds the common discovery search for verified profiles in a broad area.
        indexes = [
            models.Index(
                fields=["is_verified", "broad_area"],
                name="profile_verified_area_idx",
            )
        ]

    # WHY: Answers whether is available now without repeating that decision in several places.
    def is_available_now(self, at_time):
        """Return true only after this profile's availability start has arrived.

        Inputs: a timezone-aware time used as the comparison point.
        Returns: whether available_from exists and is no later than that time.
        Changes: none.
        Privacy: does not expose or change the stored start time.
        """
        # WHY: A missing start means unavailable; a future start remains unavailable until it arrives.
        return self.available_from is not None and self.available_from <= at_time


# WHY: Keeps the Plan information and its rules together so they stay consistent.
class Plan(models.Model):
    """Store one public-place plan and its approval and first-join lock state."""

    # WHY: Keeps the permitted status values in one clear list so saved wording stays consistent.
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        CANCELLED = "cancelled", "Cancelled"

    # WHY: Preserves the plan and its history if account deletion is attempted, rather than silently losing it.
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_plans",
    )
    # WHY: Bounds every visitor-entered plan fact to keep storage and page layouts predictable.
    title = models.CharField(max_length=120)
    description = models.TextField(max_length=1_000)
    public_place = models.CharField(max_length=200)
    public_url = models.URLField(max_length=500)
    # WHY: Stores an optional server-checked public-place image separately from the browser-supplied URL.
    thumbnail_image = models.ImageField(
        upload_to=plan_thumbnail_upload_path,
        blank=True,
        default="",
    )
    starts_at = models.DateTimeField()
    capacity = models.PositiveIntegerField()
    # WHY: Limits the plan lifecycle to the four states understood by permissions and page labels.
    status = models.CharField(
        max_length=9,
        choices=Status.choices,
        default=Status.PENDING,
    )
    # WHY: Keeps approval evidence together with the approved state instead of storing an unexplained label.
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="plans_approved",
    )
    # WHY: Records the first join point after which the owner may no longer change meeting details.
    meeting_details_locked_at = models.DateTimeField(null=True, blank=True)

    # WHY: Records creation automatically for stable ordering and support checks.
    created_at = models.DateTimeField(auto_now_add=True)

    # WHY: Keeps database or form rules beside the information they control.
    class Meta:
        # WHY: Enforces capacity and approval consistency even when a write bypasses the normal form.
        constraints = [
            # WHY: Prevents a plan that can never accept a participant.
            models.CheckConstraint(
                condition=Q(capacity__gt=0),
                name="plan_capacity_greater_than_zero",
            ),
            # WHY: Requires reviewer and time only for approved plans and forbids them for every other state.
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
        # WHY: Speeds plan-list searches by lifecycle state and start time.
        indexes = [
            models.Index(
                fields=["status", "starts_at"],
                name="plan_status_starts_idx",
            )
        ]

    # WHY: Answers whether is open for joining without repeating that decision in several places.
    def is_open_for_joining(self, at_time):
        """Return true only when this plan is currently open for another join.

        Inputs: a timezone-aware time used to determine whether the plan is future.
        Returns: whether approval, time, terminal state and capacity permit a join.
        Changes: none; this method never creates participation.
        """
        # WHY: Only approved future plans may accept a new participant.
        if self.status != self.Status.APPROVED or self.starts_at <= at_time:
            return False

        # WHY: Counts only currently joined records because people who left no longer occupy capacity.
        joined_count = self.participations.filter(
            status=Participation.Status.JOINED
        ).count()
        return joined_count < self.capacity


# WHY: Keeps the Participation information and its rules together so they stay consistent.
class Participation(models.Model):
    """Store one account's joined or ended participation in one plan."""

    # WHY: Keeps the permitted status values in one clear list so saved wording stays consistent.
    class Status(models.TextChoices):
        JOINED = "joined", "Joined"
        LEFT = "left", "Left"

    # WHY: Protects both the plan and account links so participation history cannot become anonymous or detached.
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
    # WHY: Keeps one row across joining, leaving, and rejoining instead of creating duplicate history.
    status = models.CharField(
        max_length=6,
        choices=Status.choices,
        default=Status.JOINED,
    )
    # WHY: Records when the current joined period began and, when applicable, when it ended.
    joined_at = models.DateTimeField(default=timezone.now)
    left_at = models.DateTimeField(null=True, blank=True)

    # WHY: Keeps database or form rules beside the information they control.
    class Meta:
        # WHY: Ensures one account has only one historical participation row for a plan.
        constraints = [
            models.UniqueConstraint(
                fields=["plan", "user"],
                name="participation_plan_user_unique",
            ),
            # WHY: Requires a leaving time only when the participation is marked Left.
            models.CheckConstraint(
                condition=(
                    Q(status="joined", left_at__isnull=True)
                    | Q(status="left", left_at__isnull=False)
                ),
                name="participation_left_at_matches_status",
            ),
        ]
        # WHY: Speeds capacity counts by plan and account pages that load current participation.
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


# WHY: Keeps the Conversation information and its rules together so they stay consistent.
class Conversation(models.Model):
    """Store one direct conversation with the lower account ID first."""

    # WHY: Stores the lower account ID first so the same two people cannot form a reversed duplicate pair.
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
    # WHY: Records the latest activity so the inbox can show recently used conversations first.
    updated_at = models.DateTimeField(default=timezone.now)

    # WHY: Keeps database or form rules beside the information they control.
    class Meta:
        # WHY: Enforces two different people, a stable ordering, and one conversation per pair in the database.
        constraints = [
            # WHY: Prevents an account opening a direct conversation with itself.
            models.CheckConstraint(
                condition=~Q(first_user=F("second_user")),
                name="conversation_users_differ",
            ),
            # WHY: Forces one consistent account order for every pair.
            models.CheckConstraint(
                condition=Q(first_user__lt=F("second_user")),
                name="conversation_users_ordered",
            ),
            # WHY: Prevents two rows for the same ordered pair even during simultaneous requests.
            models.UniqueConstraint(
                fields=["first_user", "second_user"],
                name="conversation_pair_unique",
            ),
        ]
        # WHY: Speeds inbox searches for either side of a conversation ordered by latest activity.
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

    # WHY: Answers whether includes account without repeating that decision in several places.
    def includes_account(self, user):
        """Return true only when the supplied account is one conversation member.

        Inputs: a Django user that may or may not belong to the pair.
        Returns: whether its primary key equals either stored member ID.
        Changes: none.
        Privacy: returns only membership and never conversation content.
        """
        # WHY: Compares only saved account IDs and returns no message or other member details.
        return user is not None and user.pk in {
            self.first_user_id,
            self.second_user_id,
        }


# WHY: Keeps the Message information and its rules together so they stay consistent.
class Message(models.Model):
    """Store one bounded plain-text message inside a direct conversation."""

    # WHY: Protects the conversation and sender so stored words always keep their original context and author.
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
    # WHY: Keeps private message text bounded and records its sending time separately.
    body = models.TextField(max_length=1_000)
    sent_at = models.DateTimeField(default=timezone.now)

    # WHY: Keeps database or form rules beside the information they control.
    class Meta:
        # WHY: Speeds loading one conversation's messages in chronological order.
        indexes = [
            models.Index(
                fields=["conversation", "sent_at"],
                name="message_convo_sent_idx",
            )
        ]


# WHY: Keeps the Notification information and its rules together so they stay consistent.
class Notification(models.Model):
    """Store one unread/read alert for an incoming message or plan join."""

    # WHY: Keeps the permitted notification types in one clear list.
    class Kind(models.TextChoices):
        MESSAGE = "message", "Message"
        PLAN_JOIN = "plan_join", "Plan join"

    # WHY: Stores exactly which account may see this alert.
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="notifications",
    )
    kind = models.CharField(max_length=9, choices=Kind.choices)
    # WHY: Links an alert to either one message or one plan participation, never both.
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
    # WHY: Keeps creation and optional reading times so unread counts do not rely on browser state.
    created_at = models.DateTimeField(default=timezone.now)
    read_at = models.DateTimeField(null=True, blank=True)

    # WHY: Keeps database or form rules beside the information they control.
    class Meta:
        # WHY: Keeps the selected notification type matched to its one permitted source record.
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
        # WHY: Speeds the top-bar unread count and recent-notification list for one recipient.
        indexes = [
            models.Index(
                fields=["recipient", "read_at", "created_at"],
                name="notification_unread_idx",
            )
        ]


# WHY: Keeps the Block information and its rules together so they stay consistent.
class Block(models.Model):
    """Store one directional block between two different accounts."""

    # WHY: Uses directional links because one person's block must not claim the other person made the same choice.
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

    # WHY: Keeps database or form rules beside the information they control.
    class Meta:
        # WHY: Prevents self-blocks and repeated copies of the same directional block.
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


# WHY: Keeps the Report information and its rules together so they stay consistent.
class Report(models.Model):
    """Store one private statement with at most one optional context reference."""

    # WHY: Keeps the permitted report reasons in one clear list.
    class Category(models.TextChoices):
        HARASSMENT = "harassment", "Harassment"
        SPAM = "spam", "Spam"
        MISLEADING_PLAN = "misleading_plan", "Misleading plan"
        SAFETY_CONCERN = "safety_concern", "Safety concern"
        OTHER = "other", "Other"

    # WHY: Keeps the permitted status values in one clear list so saved wording stays consistent.
    class Status(models.TextChoices):
        RECEIVED = "received", "Received"
        REVIEWED = "reviewed", "Reviewed"

    # WHY: Protects both accounts so the original private report keeps clear ownership and subject.
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
    # WHY: Bounds the reporter's own statement while allowing enough space to explain the concern.
    description = models.TextField(max_length=2_000)

    # WHY: Stores at most one optional plan, conversation, or message that helps staff understand context.
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
    # WHY: Separates a newly received report from one staff have reviewed without changing the original statement.
    status = models.CharField(
        max_length=8,
        choices=Status.choices,
        default=Status.RECEIVED,
    )
    received_at = models.DateTimeField(default=timezone.now)

    # WHY: Keeps database or form rules beside the information they control.
    class Meta:
        # WHY: Prevents self-reporting and stops a single report pointing at several unrelated contexts.
        constraints = [
            # WHY: Permits zero or one context reference by requiring at least two context fields to be empty.
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
        # WHY: Speeds the staff queue ordered by report state and receiving time.
        indexes = [
            models.Index(
                fields=["status", "received_at"],
                name="report_status_received_idx",
            )
        ]


# WHY: Keeps the PlatformSubscription information and its rules together so they stay consistent.
class PlatformSubscription(models.Model):
    """Store the Stripe subscription state used for current Premium access."""

    # WHY: Gives each local account one subscription summary and protects it from accidental account deletion.
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="platform_subscription",
    )
    # WHY: Keeps Stripe's customer and subscription identities unique so billing cannot move between accounts.
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
    # WHY: Stores only the Stripe state and access end needed to decide Premium access locally.
    stripe_status = models.CharField(max_length=80, null=True, blank=True)
    access_until = models.DateTimeField(null=True, blank=True)
    # WHY: Records the latest accepted Stripe event time so older delayed notices cannot undo newer state.
    latest_provider_event_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    # WHY: Answers whether has premium access without repeating that decision in several places.
    def has_premium_access(self):
        """Return true only for an allowed Stripe state with future access time.

        Returns: whether status is active or trialing and access_until is future.
        Changes: none; checkout creation alone never changes this decision.
        Privacy: returns no Stripe identifier or billing data.
        """
        # WHY: Requires both an allowed Stripe state and a future access end; either one alone is insufficient.
        return (
            self.stripe_status in {"active", "trialing"}
            and self.access_until is not None
            and self.access_until > timezone.now()
        )


# WHY: Keeps the StripeWebhookReceipt information and its rules together so they stay consistent.
class StripeWebhookReceipt(models.Model):
    """Record one processed Stripe event so it cannot be processed twice."""

    # WHY: Makes every Stripe event ID unique so a repeated signed notice is processed only once.
    stripe_event_id = models.CharField(max_length=255, unique=True)

    # WHY: Keeps the notice type, Stripe creation time, and local completion time for ordered processing checks.
    event_type = models.CharField(max_length=80)
    provider_created_at = models.DateTimeField()
    processed_at = models.DateTimeField(null=True, blank=True)
