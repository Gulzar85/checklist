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

    # Timestamps
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
            self.grade = self.calculate_grade(self.total_percentage)

            # If all sections are completed, mark audit as completed
            total_sections = sections.count()
            completed_sections = sections.filter(is_completed=True).count()

            if total_sections > 0 and completed_sections == total_sections:
                self.is_completed = True
            else:
                self.is_completed = False

            self.save(update_fields=[
                'total_scored', 'total_possible', 'total_percentage',
                'grade', 'is_completed', 'updated_at'
            ])

            return True

        except Exception as e:
            print(f"Error calculating audit totals: {e}")
            return False

    def calculate_grade(self, percentage):
        """گریڈ کا حساب لگاتا ہے"""
        if percentage >= 96:
            return 'A'
        elif percentage >= 90:
            return 'B'
        elif percentage >= 80:
            return 'C'
        else:
            return 'F'

    def get_previous_audit(self):
        """پچھلا آڈٹ حاصل کرتا ہے"""
        try:
            return Audit.objects.filter(
                restaurant=self.restaurant,
                audit_date__lt=self.audit_date,
                is_completed=True
            ).order_by('-audit_date').first()
        except Exception as e:
            print(f"Error getting previous audit: {e}")
            return None

    def update_previous_audit_info(self):
        """پچھلے آڈٹ کی معلومات اپڈیٹ کرتا ہے"""
        previous_audit = self.get_previous_audit()
        if previous_audit:
            self.previous_audit_date = previous_audit.audit_date
            self.previous_audit_score = previous_audit.total_percentage
            self.previous_auditor = previous_audit.auditor_name.get_full_name() or previous_audit.auditor_name.username
            self.save(update_fields=[
                'previous_audit_date', 'previous_audit_score',
                'previous_auditor', 'updated_at'
            ])

    def get_progress_percentage(self):
        """آڈٹ کی ترقی کا فیصد حاصل کرتا ہے"""
        try:
            total_questions = 0
            answered_questions = 0

            for section in self.auditsection_set.all():
                section_questions = section.auditquestionresponse_set.count()
                answered_section_questions = section.auditquestionresponse_set.exclude(
                    scored_points=0
                ).count()

                total_questions += section_questions
                answered_questions += answered_section_questions

            if total_questions > 0:
                return (answered_questions / total_questions) * 100
            return 0
        except Exception as e:
            print(f"Error calculating progress: {e}")
            return 0

    def get_section_stats(self):
        """سیکشن کی تفصیلی معلومات حاصل کرتا ہے"""
        try:
            sections = self.auditsection_set.select_related('section').all()
            stats = []

            for audit_section in sections:
                section_data = {
                    'section_name': audit_section.section.name,
                    'answered': audit_section.auditquestionresponse_set.exclude(scored_points=0).count(),
                    'total': audit_section.auditquestionresponse_set.count(),
                    'section_score': float(audit_section.scored_points),
                    'section_percentage': float(audit_section.section_percentage),
                    'is_completed': audit_section.is_completed
                }
                stats.append(section_data)

            return stats
        except Exception as e:
            print(f"Error getting section stats: {e}")
            return []

    def submit_audit(self):
        """آڈٹ جمع کرتا ہے"""
        try:
            # Calculate final totals
            self.calculate_totals()

            # Update previous audit info
            self.update_previous_audit_info()

            # Mark as submitted and completed
            self.is_submitted = True
            self.is_completed = True
            self.submitted_at = timezone.now()
            self.completed_at = timezone.now()

            self.save(update_fields=[
                'is_submitted', 'is_completed', 'submitted_at',
                'completed_at', 'updated_at'
            ])

            return True
        except Exception as e:
            print(f"Error submitting audit: {e}")
            return False

    @property
    def status(self):
        """آڈٹ کی حالت حاصل کرتا ہے"""
        if self.is_completed and self.is_submitted:
            return "Completed"
        elif self.is_completed:
            return "Ready for Submission"
        elif self.get_progress_percentage() > 0:
            return "In Progress"
        else:
            return "Not Started"

    @property
    def can_be_submitted(self):
        """چیک کرتا ہے کہ آیا آڈٹ جمع کیا جا سکتا ہے"""
        return self.is_completed and not self.is_submitted

    @property
    def duration(self):
        """آڈٹ کی مدت حاصل کرتی ہے"""
        if self.created_at and self.completed_at:
            return self.completed_at - self.created_at
        elif self.created_at:
            return timezone.now() - self.created_at
        return None

    def get_absolute_url(self):
        """آڈٹ کا URL حاصل کرتا ہے"""
        from django.urls import reverse
        return reverse('core:audit_results', kwargs={'pk': self.pk})

    def check_completion_status(self):
        """Check karta hai ke audit complete hua hai ya nahi"""
        try:
            # Agar koi section nahi hai to incomplete
            sections = self.auditsection_set.all()
            if not sections.exists():
                self.is_completed = False
                return

            # Har section ke liye check karein
            all_sections_completed = all(section.is_completed for section in sections)

            # All questions answered check (optional - agar aap chahein)
            total_questions = AuditQuestionResponse.objects.filter(
                audit_section__audit=self
            ).count()

            answered_questions = AuditQuestionResponse.objects.filter(
                audit_section__audit=self
            ).exclude(scored_points=0).count()

            # Agar saare sections complete hain aur koi question unanswered nahi hai
            if all_sections_completed and total_questions > 0 and answered_questions == total_questions:
                self.is_completed = True
            else:
                self.is_completed = False

        except Exception as e:
            print(f"Error checking completion status: {e}")
            self.is_completed = False


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
    is_completed = models.BooleanField(default=False)

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

            if total_possible > 0:
                percentage = (total_scored / total_possible) * 100
                self.section_percentage = round(percentage, 2)
            else:
                self.section_percentage = 0

            # Completion status check
            total_questions = responses.count()
            answered_questions = responses.exclude(scored_points=0).count()
            self.is_completed = (total_questions > 0 and answered_questions == total_questions)

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
