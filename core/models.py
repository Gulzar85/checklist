from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator

User = get_user_model()

class Restaurant(models.Model):
    code = models.CharField(max_length=50, verbose_name="Restaurant Code")
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
        ('A', 'A'),
        ('B', 'B'),
        ('C', 'C'),
        ('F', 'F'),
    ]

    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, verbose_name="Restaurant")
    audit_date = models.DateField(verbose_name="Audit Date")
    manager_on_duty = models.CharField(max_length=255, verbose_name="Manager On Duty")
    auditor_name = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Auditor Name")
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

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Audit"
        verbose_name_plural = "Audits"
        ordering = ['-audit_date']

    def __str__(self):
        return f"{self.restaurant.name} - {self.audit_date} - {self.grade}"

    def calculate_totals(self):
        sections = self.auditsection_set.all()
        total_scored = sum(section.scored_points for section in sections)
        total_possible = sum(section.possible_points for section in sections)

        self.total_scored = total_scored
        self.total_possible = total_possible
        self.total_percentage = (total_scored / total_possible * 100) if total_possible > 0 else 0

        # Grade calculation
        if self.total_percentage >= 96:
            self.grade = 'A'
        elif self.total_percentage >= 90:
            self.grade = 'B'
        elif self.total_percentage >= 80:
            self.grade = 'C'
        else:
            self.grade = 'F'

        self.save()


class Section(models.Model):
    name = models.CharField(max_length=50, verbose_name="Section Name")
    description = models.TextField(blank=True, verbose_name="Description")
    order = models.IntegerField(default=0, verbose_name="Order")

    class Meta:
        verbose_name = "Section"
        verbose_name_plural = "Sections"
        ordering = ['order']

    def __str__(self):
        return self.get_name_display()


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
        return f"{self.section.get_name_display()} - {self.question_text[:50]}..."


class AuditSection(models.Model):
    audit = models.ForeignKey(Audit, on_delete=models.CASCADE, verbose_name="Audit")
    section = models.ForeignKey(Section, on_delete=models.CASCADE, verbose_name="Section")
    scored_points = models.DecimalField(max_digits=6, decimal_places=2, default=0, verbose_name="Scored Points")
    possible_points = models.DecimalField(max_digits=6, decimal_places=2, default=0, verbose_name="Possible Points")
    section_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name="Section Percentage")
    has_critical_failure = models.BooleanField(default=False, verbose_name="Critical Failure?")

    class Meta:
        verbose_name = "Audit Section"
        verbose_name_plural = "Audit Sections"
        unique_together = ['audit', 'section']

    def __str__(self):
        return f"{self.audit} - {self.section.get_name_display()}"

    def calculate_section_score(self):
        responses = self.auditquestionresponse_set.filter(question__section=self.section)

        self.possible_points = sum(response.question.possible_points for response in responses)
        self.scored_points = sum(response.scored_points for response in responses)

        # Check for critical failures
        critical_failures = responses.filter(
            question__is_critical=True,
            scored_points=0
        )
        self.has_critical_failure = critical_failures.exists()

        # If critical failure, section percentage is 0
        if self.has_critical_failure:
            self.section_percentage = 0
        else:
            self.section_percentage = (
                    self.scored_points / self.possible_points * 100) if self.possible_points > 0 else 0

        self.save()


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
    question_response = models.ForeignKey(AuditQuestionResponse, on_delete=models.CASCADE, verbose_name="Question Response")
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
