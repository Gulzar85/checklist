from django.db import transaction
from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver

from .models import AuditQuestionResponse, AuditSection, Audit, CorrectiveAction


@receiver(post_save, sender=AuditQuestionResponse)
@receiver(post_delete, sender=AuditQuestionResponse)
def update_scores_on_response_change(sender, instance, **kwargs):
    """
    جب سوال کے جواب میں تبدیلی ہو تو سیکشن اور آڈٹ کے اسکور اپڈیٹ ہوں
    """
    try:
        # Database transaction کے اندر حساب کتاب
        with transaction.atomic():
            # سیکشن کا اسکور اپڈیٹ کریں
            instance.audit_section.calculate_section_score()

            # آڈٹ کے کل اسکور اپڈیٹ کریں
            instance.audit_section.audit.calculate_totals()

    except Exception as e:
        # Error handling - production میں logging استعمال کریں
        print(f"Error updating scores: {e}")


@receiver(post_save, sender=AuditSection)
def update_audit_on_section_change(sender, instance, **kwargs):
    """
    جب سیکشن میں تبدیلی ہو تو آڈٹ کے کل اسکور اپڈیٹ ہوں
    """
    try:
        with transaction.atomic():
            instance.audit.calculate_totals()
    except Exception as e:
        print(f"Error updating audit totals: {e}")


@receiver(pre_save, sender=AuditQuestionResponse)
def validate_response_points(sender, instance, **kwargs):
    """
    سوال کے جواب کو سیو کرنے سے پہلے ویلیڈیشن
    """
    # اس بات کو یقینی بنائیں کہ حاصل شدہ پوائنٹس ممکنہ پوائنٹس سے زیادہ نہ ہوں
    if instance.scored_points > instance.question.possible_points:
        instance.scored_points = instance.question.possible_points

    # منفی پوائنٹس کی روک تھام
    if instance.scored_points < 0:
        instance.scored_points = 0


@receiver(post_save, sender=AuditQuestionResponse)
def auto_create_corrective_action(sender, instance, created, **kwargs):
    """
    اگر سوال کریٹیکل ہے اور اس میں فیل ہوا ہے تو خودکار کارروائی کا پلان بنائیں
    """
    if instance.question.is_critical and instance.scored_points == 0:
        # Check if corrective action already exists
        existing_action = CorrectiveAction.objects.filter(
            question_response=instance
        ).exists()

        if not existing_action:
            CorrectiveAction.objects.create(
                audit=instance.audit_section.audit,
                question_response=instance,
                description=f"Critical failure in: {instance.question.question_text}",
                risk_level='CRITICAL',
                assigned_to=instance.audit_section.audit.manager_on_duty,
                deadline=instance.audit_section.audit.audit_date,  # Immediate action
                comments="Automatically created due to critical failure"
            )


@receiver(post_save, sender=Audit)
def initialize_audit_sections(sender, instance, created, **kwargs):
    """
    نئے آڈٹ بنتے ہی تمام سیکشنز کو automatically شامل کریں
    """
    if created:
        from .models import Section
        sections = Section.objects.all()

        for section in sections:
            AuditSection.objects.create(
                audit=instance,
                section=section,
                scored_points=0,
                possible_points=0,
                section_percentage=0
            )


@receiver(post_save, sender=CorrectiveAction)
def update_completion_date(sender, instance, **kwargs):
    """
    جب کارروائی مکمل ہو تو تاریخ خودکار سیو ہو
    """
    if instance.completed and not instance.completion_date:
        from django.utils import timezone
        instance.completion_date = timezone.now().date()
        instance.save()
