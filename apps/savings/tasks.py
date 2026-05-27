import logging

from celery import shared_task

from .autosave import process_goal_autosave
from .models import SavingsGoal

logger = logging.getLogger(__name__)


@shared_task
def run_savings_goal_autosave():
    """Periodic task: apply weekly / round-up / smart-save rules for all active goals."""
    qs = SavingsGoal.objects.filter(status=SavingsGoal.Status.ACTIVE).select_related('owner')
    for goal in qs.iterator(chunk_size=100):
        try:
            process_goal_autosave(goal)
        except Exception:
            logger.exception('run_savings_goal_autosave failed for goal %s', goal.id)
