import logging
from django.db import transaction
from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.utils import timezone

from .models import AuditQuestionResponse, AuditSection, Audit, CorrectiveAction

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------
# 1️⃣  Update audit & section scores when responses change
# ---------------------------------------------------------------------
@receiver([post_save, post_delete], sender=AuditQuestionResponse)
def update_scores_on_response_change(sender, instance, **kwargs):
    """
    جب سوال کے جواب میں تبدیلی ہو تو سیکشن اور آڈٹ کے اسکور اپڈیٹ ہوں
    """
    try:
        with transaction.atomic():
            instance.audit_section.calculate_section_score()
            instance.audit_section.audit.calculate_totals()
            logger.debug(
                "Updated scores after response change: audit=%s section=%s",
                instance.audit_section.audit.id,
                instance.audit_section.section.id,
            )
    except Exception:
        logger.exception(
            "Error updating scores for AuditQuestionResponse id=%s", instance.id
        )


# ---------------------------------------------------------------------
# 2️⃣  Update audit totals when a section changes
# ---------------------------------------------------------------------
@receiver(post_save, sender=AuditSection)
def update_audit_on_section_change(sender, instance, **kwargs):
    """
    جب سیکشن میں تبدیلی ہو تو آڈٹ کے کل اسکور اپڈیٹ ہوں
    """
    try:
        with transaction.atomic():
            instance.audit.calculate_totals()
            logger.debug(
                "Recalculated totals for audit id=%s after section update",
                instance.audit.id,
            )
    except Exception:
        logger.exception("Error updating audit totals for section id=%s", instance.id)


# ---------------------------------------------------------------------
# 3️⃣  Validate response before save
# ---------------------------------------------------------------------
@receiver(pre_save, sender=AuditQuestionResponse)
def validate_response_points(sender, instance, **kwargs):
    """
    سوال کے جواب کو سیو کرنے سے پہلے ویلیڈیشن
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
            instance.scored_points,
            max_points,
            getattr(instance, "id", None),
        )
        instance.scored_points = max_points

    if instance.scored_points < 0:
        logger.info(
            "Negative scored_points detected (%s) — resetting to 0 for response id=%s",
            instance.scored_points,
            getattr(instance, "id", None),
        )
        instance.scored_points = 0


# ---------------------------------------------------------------------
# 4️⃣  Automatically create corrective actions for critical failures
# ---------------------------------------------------------------------
@receiver(post_save, sender=AuditQuestionResponse)
def auto_create_corrective_action(sender, instance, created, **kwargs):
    """
    اگر سوال کریٹیکل ہے اور اس میں فیل ہوا ہے تو خودکار کارروائی کا پلان بنائیں
    """
    try:
        if instance.question.is_critical and instance.scored_points == 0:
            exists = CorrectiveAction.objects.filter(
                question_response=instance
            ).exists()

            if not exists:
                CorrectiveAction.objects.create(
                    audit=instance.audit_section.audit,
                    question_response=instance,
                    description=f"Critical failure in: {instance.question.question_text}",
                    risk_level="CRITICAL",
                    assigned_to=instance.audit_section.audit.manager_on_duty,
                    deadline=instance.audit_section.audit.audit_date,
                    comments="Automatically created due to critical failure",
                )
                logger.warning(
                    "Auto-created corrective action for critical failure (audit=%s, question=%s)",
                    instance.audit_section.audit.id,
                    instance.question.id,
                )
    except Exception:
        logger.exception(
            "Error creating corrective action for AuditQuestionResponse id=%s",
            instance.id,
        )


# ---------------------------------------------------------------------
# 5️⃣  Update completion date automatically when action marked complete
# ---------------------------------------------------------------------
@receiver(post_save, sender=CorrectiveAction)
def update_completion_date(sender, instance, **kwargs):
    """
    جب کارروائی مکمل ہو تو تاریخ خودکار سیو ہو
    """
    try:
        if instance.completed and not instance.completion_date:
            # avoid infinite recursion by using update()
            CorrectiveAction.objects.filter(pk=instance.pk).update(
                completion_date=timezone.now().date()
            )
            logger.info(
                "Set completion_date for corrective action id=%s",
                instance.id,
            )
    except Exception:
        logger.exception(
            "Error setting completion_date for corrective action id=%s",
            instance.id,
        )
