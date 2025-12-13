import logging

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.utils import timezone

from .models import AuditQuestionResponse, AuditSection, Audit, CorrectiveAction

logger = logging.getLogger(__name__)


@receiver([post_save, post_delete], sender=AuditQuestionResponse)
def update_scores_on_response_change(sender, instance, **kwargs):
    """
    Update section and audit scores when responses change
    """
    try:
        with transaction.atomic():
            # Use select_for_update to prevent race conditions
            audit_section = AuditSection.objects.select_for_update().get(
                id=instance.audit_section.id
            )
            audit_section.calculate_section_score()

            audit = Audit.objects.select_for_update().get(
                id=audit_section.audit.id
            )
            audit.calculate_totals()

            logger.info(
                "Updated scores for audit=%s section=%s",
                audit.id, audit_section.section.id
            )
    except Exception as e:
        logger.error(
            "Error updating scores for AuditQuestionResponse id=%s: %s",
            instance.id, str(e)
        )


@receiver(pre_save, sender=AuditQuestionResponse)
def validate_response_points(sender, instance, **kwargs):
    """
    Validate response points before save
    """
    if not instance.question:
        logger.warning(
            "AuditQuestionResponse pre_save triggered without question (id=%s)",
            getattr(instance, "id", None),
        )
        return

    max_points = instance.question.possible_points
    if instance.scored_points > max_points:
        logger.info(
            "Adjusted scored_points from %s to %s for response id=%s",
            instance.scored_points, max_points, getattr(instance, "id", None),
        )
        instance.scored_points = max_points

    if instance.scored_points < 0:
        logger.info(
            "Negative scored_points detected (%s) — resetting to 0 for response id=%s",
            instance.scored_points, getattr(instance, "id", None),
        )
        instance.scored_points = 0

'''
@receiver(post_save, sender=AuditQuestionResponse)
def auto_create_corrective_action(sender, instance, created, **kwargs):
    """
    Automatically create corrective actions for critical failures
    """
    try:
        if instance.question.is_critical and instance.scored_points == 0:
            exists = CorrectiveAction.objects.filter(
                question_response=instance
            ).exists()

            if not exists:
                corrective_action = CorrectiveAction.objects.create(
                    audit=instance.audit_section.audit,
                    question_response=instance,
                    description=f"Critical failure in: {instance.question.question_text}",
                    risk_level="CRITICAL",
                    assigned_to=instance.audit_section.audit.manager_on_duty,
                    deadline=timezone.now().date(),
                    comments="Automatically created due to critical failure",
                )

                # Send email notification for critical failure
                send_critical_failure_notification(corrective_action)

                logger.warning(
                    "Auto-created corrective action for critical failure (audit=%s, question=%s)",
                    instance.audit_section.audit.id, instance.question.id,
                )
    except Exception as e:
        logger.error(
            "Error creating corrective action for AuditQuestionResponse id=%s: %s",
            instance.id, str(e)
        )

@receiver(post_save, sender=CorrectiveAction)
def update_completion_date(sender, instance, **kwargs):
    """
    Update completion date automatically when action marked complete
    """
    try:
        if instance.completed and not instance.completion_date:
            # Use update to avoid recursion
            CorrectiveAction.objects.filter(pk=instance.pk).update(
                completion_date=timezone.now().date()
            )
            logger.info("Set completion_date for corrective action id=%s", instance.id)

            # Send completion notification
            if getattr(settings, 'SEND_EMAIL_NOTIFICATIONS', False):
                send_corrective_action_completion_notification(instance)

    except Exception as e:
        logger.error(
            "Error setting completion_date for corrective action id=%s: %s",
            instance.id, str(e)
        )
'''

@receiver(post_save, sender=Audit)
def update_previous_audit_info(sender, instance, created, **kwargs):
    """
    Update previous audit information when audit is created
    """
    if created:
        try:
            instance.update_previous_audit_info()
        except Exception as e:
            logger.error("Error updating previous audit info: %s", str(e))

'''
def send_critical_failure_notification(corrective_action):
    """
    Send email notification for critical failures
    """
    if not getattr(settings, 'SEND_EMAIL_NOTIFICATIONS', False):
        return

    try:
        subject = f"CRITICAL FAILURE: {corrective_action.audit.restaurant.name}"
        message = f"""
        A critical failure has been detected:

        Restaurant: {corrective_action.audit.restaurant.name}
        Audit Date: {corrective_action.audit.audit_date}
        Question: {corrective_action.question_response.question.question_text}
        Assigned To: {corrective_action.assigned_to}
        Deadline: {corrective_action.deadline}

        Please take immediate action.
        """

        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [settings.ADMIN_EMAIL],
            fail_silently=True,
        )
    except Exception as e:
        logger.error("Error sending critical failure notification: %s", str(e))


def send_corrective_action_completion_notification(corrective_action):
    """
    Send email notification when corrective action is completed
    """
    try:
        subject = f"Corrective Action Completed: {corrective_action.audit.restaurant.name}"
        message = f"""
        Corrective action has been completed:

        Restaurant: {corrective_action.audit.restaurant.name}
        Description: {corrective_action.description}
        Completed By: {corrective_action.assigned_to}
        Completion Date: {corrective_action.completion_date}
        """

        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [settings.ADMIN_EMAIL],
            fail_silently=True,
        )
    except Exception as e:
        logger.error("Error sending completion notification: %s", str(e))

'''

@receiver(post_delete, sender=CorrectiveAction)
def update_on_corrective_action_delete(sender, instance, **kwargs):
    """
    Signal handler to update related fields when a CorrectiveAction is deleted.
    This ensures updates happen even if delete happens outside the view.
    """
    try:
        question_response = instance.question_response
        audit = instance.audit

        # --- Update needs_corrective_action on QuestionResponse ---
        if question_response:
            other_actions_exist = CorrectiveAction.objects.filter(
                question_response=question_response
            ).exclude(id=instance.id).exists()

            if not other_actions_exist:
                question_response.needs_corrective_action = False
                question_response.save(update_fields=['needs_corrective_action'])

                logger.debug(
                    "Signal: Updated AuditQuestionResponse id=%s after CorrectiveAction delete",
                    question_response.id
                )

        # --- Update audit critical failure status ---
        if audit and question_response and getattr(question_response.question, "is_critical", False):

            critical_actions_exist = CorrectiveAction.objects.filter(
                audit=audit,
                question_response__question__is_critical=True
            ).exclude(id=instance.id).exists()

            critical_sections_exist = audit.auditsection_set.filter(
                has_critical_failure=True
            ).exists()

            new_status = critical_actions_exist or critical_sections_exist

            if audit.has_critical_failure != new_status:
                audit.has_critical_failure = new_status

                if new_status:
                    audit.grade = 'F'
                else:
                    # Ensure total_percentage is usable as float
                    audit.grade = audit.calculate_normal_grade(float(audit.total_percentage or 0))

                audit.save(update_fields=['has_critical_failure', 'grade'])

                logger.debug(
                    "Signal: Updated Audit id=%s critical status to %s",
                    audit.id, new_status
                )

    except Exception as e:
        logger.exception("Error in post_delete signal for CorrectiveAction: %s", str(e))
