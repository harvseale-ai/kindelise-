"""Read visible plan lists and authorised plan details."""

from django.db.models import Count, Q
from django.utils import timezone

from kindlelise.models import Participation, Plan
from kindlelise.policies import can_access_discovery_plans_and_messages

# =============================================================================
# PLAN READS
# Loads visible plan cards and one authorised plan-detail summary.
# =============================================================================


# WHY: Finds the plans for plan list information in one place so callers receive the same result.
def get_plans_for_plan_list(user, *, completed=False):
    """Return current plans, or completed plans relevant to the signed-in account.

    Inputs: the server-known signed-in account and a server-chosen completed flag.
    Returns: an ordered Plan queryset containing only list-visible records.
    Changes: none.
    Refuses: every ineligible account with an empty queryset.
    Privacy: completed plans are limited to plans the account hosted or joined.
    """
    # WHY: Ineligible accounts receive no plan rows rather than partial plan information.
    if not can_access_discovery_plans_and_messages(user):
        return Plan.objects.none()

    # WHY: Uses one current time for every future-plan comparison in this list.
    current_time = timezone.now()

    # WHY: Builds the shared card information once before choosing the current or completed list.
    plans = (
        Plan.objects.select_related("owner")
        # WHY: Counts current participants in the same query without returning their identities.
        .annotate(
            joined_count=Count(
                "participations",
                filter=Q(participations__status=Participation.Status.JOINED),
            )
        )
    )
    if completed:
        # WHY: Treats an approved plan as done once its start time has passed, without adding a second saved status.
        joined_plan_ids = Participation.objects.filter(
            user=user,
            status=Participation.Status.JOINED,
        ).values("plan_id")
        return (
            plans.filter(
                status=Plan.Status.APPROVED,
                starts_at__lte=current_time,
            )
            # WHY: Keeps history personal by showing only plans this account hosted or stayed joined to.
            .filter(Q(owner=user) | Q(pk__in=joined_plan_ids))
            .order_by("-starts_at", "-created_at", "-pk")
        )

    # WHY: Shows future approved plans to everyone while preserving all owner-only review and cancelled states.
    return (
        plans.filter(
            Q(status=Plan.Status.APPROVED, starts_at__gt=current_time)
            | Q(
                owner=user,
                status__in=(
                    Plan.Status.PENDING,
                    Plan.Status.REJECTED,
                    Plan.Status.CANCELLED,
                ),
            )
        )
        # WHY: Orders by meeting time, then creation and row ID for a stable card grid.
        .order_by("starts_at", "created_at", "pk")
    )


# WHY: Finds the plan page if viewer is allowed information in one place so callers receive the same result.
def get_plan_page_if_viewer_is_allowed(viewer, plan_id):
    """Return one visible plan with joined count and the viewer's own state.

    Inputs: the server-known viewer and an untrusted route plan ID.
    Returns: a privacy-minimised plan summary, or none for absence or refusal.
    Changes: none.
    Refuses: ineligible viewers and plans hidden by state or ownership.
    Privacy: returns no participant identity or directory.
    """
    # WHY: Requires the same current account gate as the plan list before looking up a target.
    if not can_access_discovery_plans_and_messages(viewer):
        return None

    # WHY: Uses one current time to decide whether an approved plan is still public.
    current_time = timezone.now()

    # WHY: Loads owner display details and the joined count without loading a participant list.
    plan = (
        Plan.objects.select_related("owner", "owner__profile")
        .annotate(
            joined_count=Count(
                "participations",
                filter=Q(participations__status=Participation.Status.JOINED),
            )
        )
        .filter(pk=plan_id)
        .first()
    )
    # WHY: Missing plan IDs use the same no-result path as hidden plan states.
    if plan is None:
        return None
    # WHY: Reads this viewer's own participation before deciding whether a past plan remains visible to them.
    viewer_participation_status = (
        Participation.objects.filter(
            plan=plan,
            user=viewer,
        )
        .values_list("status", flat=True)
        .first()
    )
    # WHY: A plan is public only while approved and still in the future.
    is_public = plan.status == Plan.Status.APPROVED and plan.starts_at > current_time
    # WHY: A completed plan remains visible only to its owner or someone who stayed joined to it.
    is_completed_for_viewer = (
        plan.status == Plan.Status.APPROVED
        and plan.starts_at <= current_time
        and viewer_participation_status == Participation.Status.JOINED
    )
    if plan.owner_id != viewer.pk and not (is_public or is_completed_for_viewer):
        return None

    # WHY: Returns only this viewer's own participation state, never another participant's identity.
    return {
        "plan": plan,
        "joined_count": plan.joined_count,
        "viewer_participation_status": viewer_participation_status,
    }
