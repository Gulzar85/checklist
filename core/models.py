from __future__ import annotations

import logging
from datetime import timedelta
from decimal import Decimal, InvalidOperation
from typing import Optional, ClassVar

from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.db.models import Q, UniqueConstraint, CheckConstraint
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)
User = get_user_model()


class Restaurant(models.Model):
    """Restaurant model representing audit locations"""

    code = models.CharField(
        max_length=50,
        unique=True,
        verbose_name=_("Restaurant Code"),
        help_text=_("Unique identifier for the restaurant")
    )
    name = models.CharField(
        max_length=255,
        verbose_name=_("Restaurant Name"),
        help_text=_("Official name of the restaurant")
    )
    address = models.CharField(
        max_length=255,
        verbose_name=_("Address"),
        help_text=_("Street address of the restaurant")
    )
    city = models.CharField(
        max_length=100,
        verbose_name=_("City"),
        help_text=_("City where the restaurant is located")
    )
    country = models.CharField(
        max_length=50,
        default="Pakistan",
        verbose_name=_("Country"),
        help_text=_("Country where the restaurant is located")
    )

    class Meta:
        verbose_name = _("Restaurant")
        verbose_name_plural = _("Restaurants")
        ordering = ['name']
        indexes = [
            models.Index(fields=['city']),
            models.Index(fields=['country']),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"

    def get_absolute_url(self) -> str:
        return reverse('core:restaurant_audits', kwargs={'restaurant_id': self.pk})

    @property
    def latest_audit(self) -> Optional['Audit']:
        """Return the most recent submitted audit for this restaurant"""
        return self.audit_set.filter(is_submitted=True).order_by('-audit_date').first()

    @property
    def submitted_audit_count(self) -> int:  # RENAMED
        """Return count of submitted audits"""
        return self.audit_set.filter(is_submitted=True).count()

    @property
    def submitted_average_score(self) -> Optional[Decimal]:  # RENAMED
        """Return average score of submitted audits"""
        result = self.audit_set.filter(is_submitted=True).aggregate(
            avg_score=models.Avg('total_percentage')
        )
        return result['avg_score']


class Section(models.Model):
    """Audit sections/categories"""

    name = models.CharField(
        max_length=50,
        verbose_name=_("Section Name"),
        help_text=_("Name of the audit section")
    )
    description = models.TextField(
        blank=True,
        verbose_name=_("Description"),
        help_text=_("Detailed description of the section")
    )
    order = models.IntegerField(
        default=0,
        verbose_name=_("Order"),
        help_text=_("Display order for sections")
    )

    class Meta:
        verbose_name = _("Section")
        verbose_name_plural = _("Sections")
        ordering = ['order']
        indexes = [
            models.Index(fields=['order']),
        ]

    def __str__(self) -> str:
        return f"{self.name}"

    @property
    def question_count(self) -> int:
        """Return number of questions in this section"""
        return self.questions.count()  # CHANGED from question_set to questions


class Question(models.Model):
    """Audit questions with scoring criteria"""

    section = models.ForeignKey(
        Section,
        on_delete=models.CASCADE,
        verbose_name=_("Section"),
        related_name='questions'
    )
    question_text = models.TextField(
        verbose_name=_("Question"),
        help_text=_("The audit question text")
    )
    possible_points = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        verbose_name=_("Possible Points"),
        validators=[MinValueValidator(0)],
        help_text=_("Maximum points achievable for this question")
    )
    is_critical = models.BooleanField(
        default=False,
        verbose_name=_("Critical?"),
        help_text=_("Whether this is a critical question (zero score fails entire audit)")
    )
    critical_failure_condition = models.TextField(
        blank=True,
        verbose_name=_("Critical Failure Condition"),
        help_text=_("Description of what constitutes a critical failure")
    )
    order = models.IntegerField(
        default=0,
        verbose_name=_("Order"),
        help_text=_("Display order within section")
    )

    class Meta:
        verbose_name = _("Question")
        verbose_name_plural = _("Questions")
        ordering = ['section', 'order']
        constraints = [
            CheckConstraint(
                check=Q(possible_points__gte=0),
                name='question_possible_points_non_negative'
            ),
        ]
        indexes = [
            models.Index(fields=['section', 'order']),
            models.Index(fields=['is_critical']),
        ]

    def __str__(self) -> str:
        return f"{self.section.name} - {self.question_text[:50]}..."

    def clean(self):
        """Validate model data"""
        from django.core.exceptions import ValidationError

        if self.is_critical and not self.critical_failure_condition:
            raise ValidationError({
                'critical_failure_condition': _(
                    "Critical failure condition is required for critical questions."
                )
            })


class Audit(models.Model):
    """Main audit model representing a single audit instance"""

    GRADE_CHOICES: ClassVar[list[tuple[str, str]]] = [
        ('A', _('A (96.0 - 100)')),
        ('B', _('B (90.0 - 95.9)')),
        ('C', _('C (80.0 - 89.9)')),
        ('F', _('F (Less than 80)')),
    ]

    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        verbose_name=_("Restaurant")
    )
    audit_date = models.DateField(
        verbose_name=_("Audit Date"),
        help_text=_("Date when the audit was conducted")
    )
    manager_on_duty = models.CharField(
        max_length=255,
        verbose_name=_("Manager On Duty"),
        help_text=_("Name of the manager present during audit")
    )
    auditor_name = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name=_("Auditor"),
        related_name='audits'
    )
    auditor_signature = models.TextField(
        blank=True,
        verbose_name=_("Auditor Signature"),
        help_text=_("Digital signature of the auditor")
    )
    auditee_signature = models.TextField(
        blank=True,
        verbose_name=_("Auditee Signature"),
        help_text=_("Digital signature of the auditee")
    )

    # Calculated scores
    total_scored = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_("Total Score"),
        validators=[MinValueValidator(0)]
    )
    total_possible = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_("Total Possible Score"),
        validators=[MinValueValidator(0)]
    )
    total_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_("Total Percentage"),
        validators=[MinValueValidator(0)]
    )
    grade = models.CharField(
        max_length=1,
        choices=GRADE_CHOICES,
        blank=True,
        verbose_name=_("Grade")
    )

    # Critical failure flag
    has_critical_failure = models.BooleanField(
        default=False,
        verbose_name=_("Has Critical Failure?")
    )

    # Previous audit info
    previous_audit_date = models.DateField(
        null=True,
        blank=True,
        verbose_name=_("Previous Audit Date")
    )
    previous_audit_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_("Previous Audit Score")
    )
    previous_auditor = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("Previous Auditor Name")
    )

    # Status field
    is_submitted = models.BooleanField(
        default=False,
        verbose_name=_("Audit Submitted")
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    submitted_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Submitted At")
    )

    class Meta:
        verbose_name = _("Audit")
        verbose_name_plural = _("Audits")
        ordering = ['-audit_date']
        indexes = [
            models.Index(fields=['restaurant', 'audit_date']),
            models.Index(fields=['auditor_name', 'audit_date']),
            models.Index(fields=['grade']),
            models.Index(fields=['is_submitted']),
            models.Index(fields=['has_critical_failure']),
            models.Index(fields=['created_at']),
            models.Index(fields=['submitted_at']),
        ]
        constraints = [
            CheckConstraint(
                check=Q(total_scored__gte=0),
                name='audit_total_scored_non_negative'
            ),
            CheckConstraint(
                check=Q(total_possible__gte=0),
                name='audit_total_possible_non_negative'
            ),
            CheckConstraint(
                check=Q(total_percentage__gte=0),
                name='audit_total_percentage_non_negative'
            ),
            CheckConstraint(
                check=Q(total_percentage__lte=100),
                name='audit_total_percentage_max_100'
            ),
        ]

    def __str__(self) -> str:
        return f"{self.restaurant.name} - {self.audit_date} - {self.grade}"

    def save(self, *args, **kwargs) -> None:
        """Save method with automatic timestamp updates"""
        if self.is_submitted and not self.submitted_at:
            self.submitted_at = timezone.now()

        # Auto-update previous audit info if not set
        if not self.previous_audit_date and self.is_submitted:
            self.update_previous_audit_info()

        super().save(*args, **kwargs)

    def calculate_totals(self) -> bool:
        """
        Calculate totals for the audit using Decimal to avoid float precision issues.
        Also sets has_critical_failure and grade accordingly.

        Returns:
            bool: True on success, False on failure
        """
        try:
            # Prefetch audit sections and their responses to reduce queries
            sections = self.auditsection_set.select_related('section').prefetch_related(
                'auditquestionresponse_set__question'
            ).all()

            total_scored = Decimal('0.00')
            total_possible = Decimal('0.00')

            for section in sections:
                # scored_points and possible_points are DecimalFields already; ensure Decimal
                try:
                    section_scored = Decimal(section.scored_points or Decimal('0.00'))
                except (InvalidOperation, TypeError):
                    logger.warning("Invalid scored_points on AuditSection id=%s. Coercing to 0.", section.pk)
                    section_scored = Decimal('0.00')

                try:
                    section_possible = Decimal(section.possible_points or Decimal('0.00'))
                except (InvalidOperation, TypeError):
                    logger.warning("Invalid possible_points on AuditSection id=%s. Coercing to 0.", section.pk)
                    section_possible = Decimal('0.00')

                total_scored += section_scored
                total_possible += section_possible

            # Avoid assigning floats; use Decimal
            self.total_scored = total_scored
            self.total_possible = total_possible

            # Critical failures check - any section flagged
            self.has_critical_failure = any(
                bool(section.has_critical_failure) for section in sections
            )

            # Percentage calculation
            if total_possible > Decimal('0.00'):
                percentage = (total_scored / total_possible) * Decimal('100')
                # Normalize to 2 decimal places
                self.total_percentage = percentage.quantize(Decimal('0.01'))
            else:
                self.total_percentage = Decimal('0.00')

            # Grade
            if self.has_critical_failure:
                self.grade = 'F'
            else:
                self.grade = self.calculate_normal_grade(float(self.total_percentage))

            # Save only relevant fields
            update_fields = [
                'total_scored', 'total_possible', 'total_percentage',
                'grade', 'has_critical_failure', 'updated_at'
            ]

            try:
                self.save(update_fields=update_fields)
            except Exception:
                logger.exception(
                    "update_fields save failed when saving totals for Audit id=%s; falling back to full save.",
                    self.pk
                )
                super().save()

            return True

        except Exception as e:
            logger.exception("Error calculating audit totals for Audit id=%s", self.pk)
            return False

    def calculate_normal_grade(self, percentage: float) -> str:
        """Normal grading without critical failure consideration"""
        try:
            if percentage >= 96:
                return 'A'
            elif percentage >= 90:
                return 'B'
            elif percentage >= 80:
                return 'C'
            else:
                return 'F'
        except Exception:
            logger.exception(
                "Error while calculating normal grade for Audit id=%s with percentage=%s",
                self.pk, percentage
            )
            return 'F'

    def get_previous_audit(self) -> Optional['Audit']:
        """Return the last submitted audit for this restaurant before current audit_date"""
        try:
            return Audit.objects.filter(
                restaurant=self.restaurant,
                audit_date__lt=self.audit_date,
                is_submitted=True
            ).order_by('-audit_date').first()
        except Exception:
            logger.exception("Error getting previous audit for Audit id=%s", self.pk)
            return None

    def update_previous_audit_info(self) -> None:
        """Update previous audit metadata on this audit"""
        try:
            previous_audit = self.get_previous_audit()
            if previous_audit:
                prev_auditor_obj = previous_audit.auditor_name
                # Safe retrieval of name
                prev_auditor_name = ""
                try:
                    get_full_name = getattr(prev_auditor_obj, "get_full_name", None)
                    if callable(get_full_name):
                        prev_auditor_name = get_full_name() or getattr(prev_auditor_obj, "username", "")
                    else:
                        prev_auditor_name = getattr(prev_auditor_obj, "username", "") or str(prev_auditor_obj)
                except Exception:
                    logger.exception(
                        "Error getting previous auditor name for previous audit id=%s",
                        previous_audit.pk
                    )
                    prev_auditor_name = getattr(prev_auditor_obj, "username", "") or ""

                self.previous_audit_date = previous_audit.audit_date
                self.previous_audit_score = previous_audit.total_percentage
                self.previous_auditor = prev_auditor_name

                try:
                    self.save(update_fields=[
                        'previous_audit_date', 'previous_audit_score',
                        'previous_auditor', 'updated_at'
                    ])
                except Exception:
                    logger.exception("Failed updating previous audit info for Audit id=%s", self.pk)

        except Exception:
            logger.exception("Error updating previous audit info for Audit id=%s", self.pk)

    def get_progress_percentage(self) -> float:
        """
        Return overall audit completion percentage.

        A question is considered answered if:
        - there's a response with scored_points > 0 OR non-empty comments.
        """
        try:
            total_questions = 0
            answered_questions = 0

            # Fetch sections and prefetch questions + responses to reduce queries
            sections = self.auditsection_set.select_related('section').all()

            # Build mapping to avoid repeated DB hits
            for audit_section in sections:
                # All questions in this section - FIXED: use 'questions' instead of 'question_set'
                questions = list(audit_section.section.questions.all().only('id', 'possible_points'))  # CHANGED

                q_ids = [q.id for q in questions]
                section_total = len(questions)
                total_questions += section_total
                if section_total == 0:
                    continue

                # Responses in this audit_section
                responses = AuditQuestionResponse.objects.filter(
                    audit_section=audit_section,
                    question__in=q_ids
                ).select_related('question')

                # Map question id -> response for quick lookup
                responded_q_ids = set()
                for response in responses:
                    # Safe checks: comments may be None
                    comments = (response.comments or "").strip()
                    try:
                        scored = Decimal(response.scored_points or Decimal('0.00'))
                    except (InvalidOperation, TypeError):
                        scored = Decimal('0.00')
                        logger.warning(
                            "Invalid scored_points on AuditQuestionResponse id=%s; coerced to 0.",
                            response.pk
                        )

                    if scored > Decimal('0.00') or comments:
                        responded_q_ids.add(response.question_id)

                # answered_questions increases by number of responded question ids
                answered_questions += len(responded_q_ids)

            if total_questions > 0:
                percentage = (Decimal(answered_questions) / Decimal(total_questions)) * Decimal('100')
                # Convert to float for compatibility with existing code paths
                percent_float = float(percentage.quantize(Decimal('0.01')))
                logger.debug(
                    "Audit %s progress: %d/%d = %.2f%%",
                    self.pk, answered_questions, total_questions, percent_float
                )
                return percent_float

            return 0.0

        except Exception:
            logger.exception("Error calculating progress for Audit id=%s", self.pk)
            return 0.0

    def get_section_stats(self) -> list[dict]:
        """Return detailed section stats for the audit"""
        try:
            # Prefetch responses and related questions for efficiency
            sections = self.auditsection_set.select_related('section').prefetch_related(
                'auditquestionresponse_set__question'
            ).all()
            stats = []

            for audit_section in sections:
                responses = list(audit_section.auditquestionresponse_set.all())
                answered = sum(
                    1 for r in responses
                    if (r.scored_points and Decimal(r.scored_points) > Decimal('0.00'))
                    or (r.comments or "").strip()
                )
                total = len(responses)
                section_data = {
                    'section_name': audit_section.section.name,
                    'answered': answered,
                    'total': total,
                    'section_score': float(audit_section.scored_points or Decimal('0.00')),
                    'section_percentage': float(audit_section.section_percentage or Decimal('0.00')),
                    'has_critical_failure': audit_section.has_critical_failure,
                }
                stats.append(section_data)

            return stats
        except Exception:
            logger.exception("Error getting section stats for Audit id=%s", self.pk)
            return []

    @transaction.atomic
    def submit_audit(self) -> bool:
        """Calculate totals, update previous audit info and mark as submitted"""
        try:
            # Calculate final totals; if it fails, abort submission
            if not self.calculate_totals():
                logger.error("calculate_totals failed during submit for Audit id=%s", self.pk)
                return False

            # Update previous audit info
            try:
                self.update_previous_audit_info()
            except Exception:
                logger.exception("update_previous_audit_info failed during submit for Audit id=%s", self.pk)

            # Mark as submitted
            self.is_submitted = True
            self.submitted_at = timezone.now()
            self.save(update_fields=['is_submitted', 'submitted_at', 'updated_at'])
            return True
        except Exception:
            logger.exception("Error submitting audit id=%s", self.pk)
            return False

    @property
    def status(self) -> str:
        """Human readable status"""
        if self.is_submitted:
            if self.has_critical_failure:
                return _("Submitted - FAILED (Critical Issues)")
            else:
                return _(f"Submitted - {self.grade}")
        elif self.get_progress_percentage() > 0:
            return _("In Progress")
        else:
            return _("Not Started")

    @property
    def can_be_submitted(self) -> bool:
        """Whether audit can be submitted. Keep simple: not already submitted and some progress exists"""
        if self.is_submitted:
            return False
        progress = self.get_progress_percentage()
        # Allow submission if at least some questions are answered (adapt threshold as needed)
        return progress > 0.0

    @property
    def duration(self) -> Optional[timedelta]:
        """Return timedelta for audit duration; None if not started"""
        if self.created_at and self.submitted_at:
            return self.submitted_at - self.created_at
        elif self.created_at:
            return timezone.now() - self.created_at
        return None

    def get_absolute_url(self) -> str:
        """Return the audit results URL"""
        return reverse('core:audit_results', kwargs={'audit_id': self.pk})

    @property
    def grade_with_reason(self) -> dict:
        """Return grade with reason and metadata"""
        if self.has_critical_failure:
            return {
                'grade': 'F',
                'reason': _('Critical failure detected'),
                'percentage': float(self.total_percentage or Decimal('0.00')),
                'is_critical_failure': True
            }
        else:
            return {
                'grade': self.grade,
                'reason': _('Based on percentage score'),
                'percentage': float(self.total_percentage or Decimal('0.00')),
                'is_critical_failure': False
            }

    @property
    def status_description(self) -> str:
        """Detailed status description for UI"""
        if self.is_submitted:
            if self.has_critical_failure:
                return _(f"Submitted - FAILED (Critical Issues) - Score: {self.total_percentage}%")
            else:
                return _(f"Submitted - {self.grade} - Score: {self.total_percentage}%")
        elif self.get_progress_percentage() > 0:
            return _(f"In Progress - {self.get_progress_percentage():.1f}% complete")
        else:
            return _("Not Started")


class AuditSection(models.Model):
    """Intermediate model linking audits to sections with calculated scores"""

    audit = models.ForeignKey(
        Audit,
        on_delete=models.CASCADE,
        verbose_name=_("Audit")
    )
    section = models.ForeignKey(
        Section,
        on_delete=models.CASCADE,
        verbose_name=_("Section")
    )
    scored_points = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_("Scored Points"),
        validators=[MinValueValidator(0)]
    )
    possible_points = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_("Possible Points"),
        validators=[MinValueValidator(0)]
    )
    section_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_("Section Percentage")
    )
    has_critical_failure = models.BooleanField(
        default=False,
        verbose_name=_("Critical Failure?")
    )

    class Meta:
        verbose_name = _("Audit Section")
        verbose_name_plural = _("Audit Sections")
        constraints = [
            UniqueConstraint(
                fields=['audit', 'section'],
                name='unique_audit_section'
            ),
            CheckConstraint(
                check=Q(scored_points__gte=0),
                name='auditsection_scored_non_negative'
            ),
            CheckConstraint(
                check=Q(possible_points__gte=0),
                name='auditsection_possible_non_negative'
            ),
            CheckConstraint(
                check=Q(section_percentage__gte=0),
                name='auditsection_percentage_non_negative'
            ),
            CheckConstraint(
                check=Q(section_percentage__lte=100),
                name='auditsection_percentage_max_100'
            ),
        ]
        indexes = [
            models.Index(fields=['audit', 'section']),
            models.Index(fields=['has_critical_failure']),
        ]

    def __str__(self) -> str:
        return f"{self.audit} - {self.section.name}"

    def calculate_section_score(self) -> None:
        """Calculate section-level scores and update audit totals"""
        try:
            # Prefetch responses with related question
            responses = list(self.auditquestionresponse_set.select_related('question').all())

            total_possible = Decimal('0.00')
            total_scored = Decimal('0.00')

            for response in responses:
                try:
                    q_possible = Decimal(response.question.possible_points or Decimal('0.00'))
                except (InvalidOperation, TypeError):
                    logger.warning(
                        "Invalid possible_points on Question id=%s. Coercing to 0.",
                        getattr(response.question, 'id', None)
                    )
                    q_possible = Decimal('0.00')
                try:
                    scored = Decimal(response.scored_points or Decimal('0.00'))
                except (InvalidOperation, TypeError):
                    logger.warning(
                        "Invalid scored_points on Response id=%s. Coercing to 0.",
                        getattr(response, 'id', None)
                    )
                    scored = Decimal('0.00')

                total_possible += q_possible
                total_scored += scored

            self.possible_points = total_possible
            self.scored_points = total_scored

            # Critical failures check: any critical question with scored_points == 0
            critical_failures = any(
                (getattr(r, 'question', None) and
                 getattr(r.question, 'is_critical', False) and
                 (Decimal(r.scored_points or Decimal('0.00')) == Decimal('0.00')))
                for r in responses
            )
            self.has_critical_failure = bool(critical_failures)

            if total_possible > Decimal('0.00'):
                percentage = (total_scored / total_possible) * Decimal('100')
                self.section_percentage = percentage.quantize(Decimal('0.01'))
            else:
                self.section_percentage = Decimal('0.00')

            # Save minimal fields
            update_fields = [
                'possible_points', 'scored_points',
                'section_percentage', 'has_critical_failure'
            ]

            try:
                self.save(update_fields=update_fields)
            except Exception:
                logger.exception(
                    "update_fields save failed for AuditSection id=%s; falling back to full save.",
                    self.pk
                )
                super().save()

            # Update audit totals once per section update
            try:
                # calculate_totals already calls save(update_fields=...), so it should be efficient
                self.audit.calculate_totals()
            except Exception:
                logger.exception("Failed to update audit totals from AuditSection id=%s", self.pk)

        except Exception:
            logger.exception("Error calculating section score for AuditSection id=%s", self.pk)

    @property
    def progress_percentage(self) -> float:
        """Section progress: fraction of questions answered for the section"""
        try:
            # FIXED: use 'questions' instead of 'question_set'
            total_questions = self.section.questions.count()  # CHANGED
            if total_questions == 0:
                return 0.0

            answered_questions = 0
            responses = AuditQuestionResponse.objects.filter(
                audit_section=self
            ).select_related('question')

            for response in responses:
                comments = (response.comments or "").strip()
                try:
                    scored = Decimal(response.scored_points or Decimal('0.00'))
                except (InvalidOperation, TypeError):
                    logger.warning(
                        "Invalid scored_points on AuditQuestionResponse id=%s; coerced to 0.",
                        response.pk
                    )
                    scored = Decimal('0.00')

                if scored > Decimal('0.00') or comments:
                    answered_questions += 1

            percentage = (Decimal(answered_questions) / Decimal(total_questions)) * Decimal('100')
            percent_float = float(percentage.quantize(Decimal('0.01')))
            logger.debug(
                "Section %s progress: %d/%d = %.2f%%",
                self.section.name, answered_questions, total_questions, percent_float
            )
            return percent_float

        except Exception:
            logger.exception("Error calculating section progress for AuditSection id=%s", self.pk)
            return 0.0

class AuditQuestionResponse(models.Model):
    """Individual question responses within an audit"""

    audit_section = models.ForeignKey(
        AuditSection,
        on_delete=models.CASCADE,
        verbose_name=_("Audit Section")
    )
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        verbose_name=_("Question")
    )
    scored_points = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(0)],
        verbose_name=_("Scored Points")
    )
    comments = models.TextField(
        blank=True,
        verbose_name=_("Comments"),
        help_text=_("Additional comments or observations")
    )
    needs_corrective_action = models.BooleanField(
        default=False,
        verbose_name=_("Needs Corrective Action?")
    )

    class Meta:
        verbose_name = _("Question Response")
        verbose_name_plural = _("Question Responses")
        constraints = [
            UniqueConstraint(
                fields=['audit_section', 'question'],
                name='unique_audit_section_question'
            ),
        ]
        indexes = [
            models.Index(fields=['audit_section', 'question']),
            models.Index(fields=['needs_corrective_action']),
        ]

    def __str__(self) -> str:
        return f"{self.audit_section} - {self.question.question_text[:30]}"

    def save(self, *args, **kwargs) -> None:
        # Ensure scored points don't exceed possible points and log issues
        try:
            if (self.question and
                    self.scored_points is not None and
                    self.question.possible_points is not None):

                try:
                    # Coerce to Decimal and compare
                    if Decimal(self.scored_points) > Decimal(self.question.possible_points):
                        logger.debug(
                            "Scored points (%s) exceed possible points (%s) for question id=%s. Clamping.",
                            self.scored_points, self.question.possible_points,
                            getattr(self.question, 'id', None)
                        )
                        self.scored_points = Decimal(self.question.possible_points)
                except (InvalidOperation, TypeError):
                    logger.warning(
                        "Invalid numeric values when validating scored_points for AuditQuestionResponse id=%s",
                        getattr(self, 'id', None)
                    )

            super().save(*args, **kwargs)

            # Update section scores (this will trigger audit totals update)
            try:
                self.audit_section.calculate_section_score()
            except Exception:
                logger.exception(
                    "Failed to calculate_section_score after saving AuditQuestionResponse id=%s",
                    getattr(self, 'id', None)
                )

        except Exception:
            logger.exception(
                "Error saving AuditQuestionResponse (AuditSection id: %s, Question id: %s)",
                getattr(self.audit_section, 'id', None),
                getattr(self.question, 'id', None)
            )
            # Re-raise so calling code is aware if needed
            raise

    @property
    def is_answered(self) -> bool:
        """Return whether the question is 'answered'"""
        try:
            return bool((self.comments or "").strip()) or (
                    Decimal(self.scored_points or Decimal('0.00')) > Decimal('0.00')
            )
        except Exception:
            logger.exception("Error checking is_answered for AuditQuestionResponse id=%s", self.pk)
            return False

    @property
    def is_critical_failure(self) -> bool:
        """Return True when this is a critical question and scored_points == 0"""
        try:
            return bool(
                self.question.is_critical and
                Decimal(self.scored_points or Decimal('0.00')) == Decimal('0.00')
            )
        except Exception:
            logger.exception("Error checking is_critical_failure for AuditQuestionResponse id=%s", self.pk)
            return False


class CorrectiveAction(models.Model):
    """Corrective actions for identified issues"""

    RISK_LEVELS: ClassVar[list[tuple[str, str]]] = [
        ('LOW', _('Low')),
        ('MEDIUM', _('Medium')),
        ('HIGH', _('High')),
        ('CRITICAL', _('Critical')),
    ]

    audit = models.ForeignKey(
        Audit,
        on_delete=models.CASCADE,
        verbose_name=_("Audit")
    )
    question_response = models.ForeignKey(
        AuditQuestionResponse,
        on_delete=models.CASCADE,
        verbose_name=_("Question Response")
    )
    description = models.TextField(
        verbose_name=_("Description"),
        help_text=_("Detailed description of the corrective action needed")
    )
    risk_level = models.CharField(
        max_length=10,
        choices=RISK_LEVELS,
        verbose_name=_("Risk Level")
    )
    assigned_to = models.CharField(
        max_length=255,
        verbose_name=_("Assigned To"),
        help_text=_("Person responsible for completing the action")
    )
    deadline = models.DateField(
        verbose_name=_("Deadline"),
        help_text=_("Target completion date")
    )
    completed = models.BooleanField(
        default=False,
        verbose_name=_("Completed?")
    )
    completion_date = models.DateField(
        null=True,
        blank=True,
        verbose_name=_("Completion Date")
    )
    comments = models.TextField(
        blank=True,
        verbose_name=_("Comments"),
        help_text=_("Additional comments or progress notes")
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Corrective Action")
        verbose_name_plural = _("Corrective Actions")
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['audit']),
            models.Index(fields=['risk_level']),
            models.Index(fields=['completed']),
            models.Index(fields=['deadline']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self) -> str:
        return f"{self.audit} - {self.get_risk_level_display()}"

    def save(self, *args, **kwargs) -> None:
        try:
            # If completed but no completion_date, set it
            if self.completed and not self.completion_date:
                self.completion_date = timezone.now().date()
            # If not completed but has completion_date, clear it
            elif not self.completed and self.completion_date:
                self.completion_date = None

            super().save(*args, **kwargs)
        except Exception:
            logger.exception("Error saving CorrectiveAction id=%s", getattr(self, 'id', None))
            raise

    def get_absolute_url(self) -> str:
        """Return URL for corrective action detail view"""
        return reverse('core:corrective_action_detail', kwargs={'pk': self.pk})

    @property
    def is_overdue(self) -> bool:
        """Check if corrective action is overdue"""
        if self.completed:
            return False
        return self.deadline < timezone.now().date()

    @property
    def days_remaining(self) -> Optional[int]:
        """Calculate days remaining until deadline"""
        if self.completed:
            return None
        today = timezone.now().date()
        return (self.deadline - today).days
