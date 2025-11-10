from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Sum
from django.utils import timezone
User = get_user_model()


class Restaurant(models.Model):
    code = models.CharField(max_length=50, unique=True, verbose_name="Restaurant Code")
    name = models.CharField(max_length=255, verbose_name="Restaurant Name")
    address = models.CharField(max_length=255, verbose_name="Address")
    city = models.CharField(max_length=100, verbose_name="City")
    country = models.CharField(max_length=50, default="Pakistan", verbose_name="Country")

    class Meta:
        verbose_name = "Restaurant"
        verbose_name_plural = "Restaurants"

    def __str__(self):
        return f"{self.name} ({self.code})"


class Audit(models.Model):
    GRADE_CHOICES = [
        ('A', 'A (96.0 - 100)'),
        ('B', 'B (90.0 - 95.9)'),
        ('C', 'C (80.0 - 89.9)'),
        ('F', 'F (Less than 80)'),
    ]
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, verbose_name="Restaurant")
    audit_date = models.DateField(verbose_name="Audit Date")
    manager_on_duty = models.CharField(max_length=255, verbose_name="Manager On Duty")
    auditor_name = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Auditor", related_name='audits')
    auditor_signature = models.TextField(blank=True, verbose_name="Auditor Signature")
    auditee_signature = models.TextField(blank=True, verbose_name="Auditee Signature")

    # Calculated scores
    total_scored = models.DecimalField(max_digits=8, decimal_places=2, default=0, verbose_name="Total Score")
    total_possible = models.DecimalField(max_digits=8, decimal_places=2, default=0, verbose_name="Total Possible Score")
    total_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name="Total Percentage")
    grade = models.CharField(max_length=1, choices=GRADE_CHOICES, blank=True, verbose_name="Grade")

    # Previous audit info
    previous_audit_date = models.DateField(null=True, blank=True, verbose_name="Previous Audit Date")
    previous_audit_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True,
                                               verbose_name="Previous Audit Score")
    previous_auditor = models.CharField(max_length=255, blank=True, verbose_name="Previous Auditor Name")

    # Status fields
    is_completed = models.BooleanField(default=False, verbose_name="Audit Completed")
    is_submitted = models.BooleanField(default=False, verbose_name="Audit Submitted")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    submitted_at = models.DateTimeField(null=True, blank=True, verbose_name="Submitted At")
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="Completed At")

    class Meta:
        verbose_name = "Audit"
        verbose_name_plural = "Audits"
        ordering = ['-audit_date']
        indexes = [
            models.Index(fields=['restaurant', 'audit_date']),
            models.Index(fields=['auditor_name', 'audit_date']),
            models.Index(fields=['grade']),
            models.Index(fields=['is_completed']),
        ]

    def __str__(self):
        return f"{self.restaurant.name} - {self.audit_date} - {self.grade}"

    def save(self, *args, **kwargs):
        """Save method with automatic timestamp updates"""
        # Set submitted_at when audit is first submitted
        if self.is_submitted and not self.submitted_at:
            self.submitted_at = timezone.now()

        # Set completed_at when audit is first completed
        if self.is_completed and not self.completed_at:
            self.completed_at = timezone.now()

        super().save(*args, **kwargs)

    def calculate_totals(self):
        """کل اسکور کا حساب لگاتا ہے"""
        try:
            sections = self.auditsection_set.all()

            total_scored = sum(float(section.scored_points) for section in sections)
            total_possible = sum(float(section.possible_points) for section in sections)

            self.total_scored = total_scored
            self.total_possible = total_possible

            # فیصد کیلکولیشن
            if total_possible > 0:
                percentage = (total_scored / total_possible) * 100
                self.total_percentage = round(percentage, 2)
            else:
                self.total_percentage = 0

            # گریڈ کیلکولیشن
            if self.total_percentage >= 96:
                self.grade = 'A'
            elif self.total_percentage >= 90:
                self.grade = 'B'
            elif self.total_percentage >= 80:
                self.grade = 'C'
            else:
                self.grade = 'F'

            self.save()

        except Exception as e:
            print(f"Error calculating audit totals: {e}")


class Section(models.Model):
    name = models.CharField(max_length=50, verbose_name="Section Name")
    description = models.TextField(blank=True, verbose_name="Description")
    order = models.IntegerField(default=0, verbose_name="Order")

    class Meta:
        verbose_name = "Section"
        verbose_name_plural = "Sections"
        ordering = ['order']

    def __str__(self):
        return f"{self.name}"


class Question(models.Model):
    section = models.ForeignKey(Section, on_delete=models.CASCADE, verbose_name="Section")
    question_text = models.TextField(verbose_name="Question")
    possible_points = models.DecimalField(max_digits=6, decimal_places=2, verbose_name="Possible Points")
    is_critical = models.BooleanField(default=False, verbose_name="Critical?")
    critical_failure_condition = models.TextField(blank=True, verbose_name="Critical Failure Condition")
    order = models.IntegerField(default=0, verbose_name="Order")

    class Meta:
        verbose_name = "Question"
        verbose_name_plural = "Questions"
        ordering = ['section', 'order']

    def __str__(self):
        return f"{self.section.name} - {self.question_text[:50]}..."


class AuditSection(models.Model):
    audit = models.ForeignKey(Audit, on_delete=models.CASCADE, verbose_name="Audit")
    section = models.ForeignKey(Section, on_delete=models.CASCADE, verbose_name="Section")
    scored_points = models.DecimalField(max_digits=6, decimal_places=2, default=0, verbose_name="Scored Points")
    possible_points = models.DecimalField(max_digits=6, decimal_places=2, default=0, verbose_name="Possible Points")
    section_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0,
                                             verbose_name="Section Percentage")
    has_critical_failure = models.BooleanField(default=False, verbose_name="Critical Failure?")

    class Meta:
        verbose_name = "Audit Section"
        verbose_name_plural = "Audit Sections"
        unique_together = ['audit', 'section']
        ordering = ['audit', 'section']

    def __str__(self):
        return f"{self.audit} - {self.section.name}"

    def calculate_section_score(self):
        """سیکشن کا اسکور کیلکولیٹ کرتا ہے"""
        try:
            responses = self.auditquestionresponse_set.all()

            # ممکنہ پوائنٹس کا مجموعہ
            total_possible = responses.aggregate(
                total=Sum('question__possible_points')
            )['total'] or 0

            # حاصل شدہ پوائنٹس کا مجموعہ
            total_scored = responses.aggregate(
                total=Sum('scored_points')
            )['total'] or 0

            self.possible_points = total_possible
            self.scored_points = total_scored

            # کریٹیکل فیلئرز چیک کریں
            critical_failures = responses.filter(
                question__is_critical=True,
                scored_points=0
            ).exists()

            self.has_critical_failure = critical_failures

            # اگر کریٹیکل فیل ہے تو فیصد 0
            if self.has_critical_failure:
                self.section_percentage = 0
            else:
                self.section_percentage = (total_scored / total_possible * 100) if total_possible > 0 else 0

            self.save()

        except Exception as e:
            print(f"Error calculating section score: {e}")


class AuditQuestionResponse(models.Model):
    audit_section = models.ForeignKey(AuditSection, on_delete=models.CASCADE, verbose_name="Audit Section")
    question = models.ForeignKey(Question, on_delete=models.CASCADE, verbose_name="Question")
    scored_points = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name="Scored Points"
    )
    comments = models.TextField(blank=True, verbose_name="Comments")
    needs_corrective_action = models.BooleanField(default=False, verbose_name="Needs Corrective Action?")

    class Meta:
        verbose_name = "Question Response"
        verbose_name_plural = "Question Responses"
        unique_together = ['audit_section', 'question']

    def __str__(self):
        return f"{self.audit_section} - {self.question.question_text[:30]}"

    def save(self, *args, **kwargs):
        # Ensure scored points don't exceed possible points
        if self.scored_points > self.question.possible_points:
            self.scored_points = self.question.possible_points

        super().save(*args, **kwargs)

        # Update section score
        self.audit_section.calculate_section_score()

        # Update audit totals
        self.audit_section.audit.calculate_totals()


class CorrectiveAction(models.Model):
    RISK_LEVELS = [
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('CRITICAL', 'Critical'),
    ]

    audit = models.ForeignKey(Audit, on_delete=models.CASCADE, verbose_name="Audit")
    question_response = models.ForeignKey(AuditQuestionResponse, on_delete=models.CASCADE,
                                          verbose_name="Question Response")
    description = models.TextField(verbose_name="Description")
    risk_level = models.CharField(max_length=10, choices=RISK_LEVELS, verbose_name="Risk Level")
    assigned_to = models.CharField(max_length=255, verbose_name="Assigned To")
    deadline = models.DateField(verbose_name="Deadline")
    completed = models.BooleanField(default=False, verbose_name="Completed?")
    completion_date = models.DateField(null=True, blank=True, verbose_name="Completion Date")
    comments = models.TextField(blank=True, verbose_name="Comments")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Corrective Action"
        verbose_name_plural = "Corrective Actions"

    def __str__(self):
        return f"{self.audit} - {self.get_risk_level_display()}"


class AuditTemplate(models.Model):
    name = models.CharField(max_length=255, verbose_name="Audit Template")
    version = models.CharField(max_length=50, default="1.0", verbose_name="Version")
    is_active = models.BooleanField(default=True, verbose_name="Active?")
    sections = models.ManyToManyField(Section, through='TemplateSection')

    class Meta:
        verbose_name = "Audit Template"
        verbose_name_plural = "Audit Templates"

    def __str__(self):
        return f"{self.name} v{self.version}"


class TemplateSection(models.Model):
    template = models.ForeignKey(AuditTemplate, on_delete=models.CASCADE)
    section = models.ForeignKey(Section, on_delete=models.CASCADE)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order']
