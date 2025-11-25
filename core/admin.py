import csv

from django.contrib import admin
from django.db.models import Avg
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import path
from django.utils import timezone
from django.utils.html import format_html

from .models import (
    Restaurant, Audit, Section, Question,
    AuditSection, AuditQuestionResponse, CorrectiveAction
)


class ExportCsvMixin:
    def export_as_csv(self, request, queryset):
        meta = self.model._meta
        field_names = [field.name for field in meta.fields]

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename={meta}.csv'
        writer = csv.writer(response)

        writer.writerow(field_names)
        for obj in queryset:
            writer.writerow([getattr(obj, field) for field in field_names])

        return response

    export_as_csv.short_description = "Export Selected as CSV"


@admin.register(Restaurant)
class RestaurantAdmin(admin.ModelAdmin, ExportCsvMixin):
    list_display = ('code', 'name', 'city', 'country', 'audit_count', 'latest_audit_date')
    search_fields = ('name', 'code', 'city', 'address')
    list_filter = ('city', 'country')
    ordering = ('name',)
    actions = ['export_as_csv']

    def audit_count(self, obj):
        return obj.audit_set.count()

    audit_count.short_description = 'Audits'

    def latest_audit_date(self, obj):
        latest = obj.audit_set.order_by('-audit_date').first()
        return latest.audit_date if latest else 'No audits'

    latest_audit_date.short_description = 'Latest Audit'


@admin.register(Audit)
class AuditAdmin(admin.ModelAdmin, ExportCsvMixin):
    list_display = (
        'restaurant', 'audit_date', 'auditor_name',
        'grade_colored', 'total_percentage', 'has_critical_failure',
        'is_submitted', 'submitted_at'
    )
    list_filter = (
        'audit_date', 'grade', 'has_critical_failure',
        'is_submitted', 'restaurant__city',
    )
    search_fields = (
        'restaurant__name', 'restaurant__code',
        'auditor_name__username', 'manager_on_duty'
    )
    date_hierarchy = 'audit_date'
    readonly_fields = (
        'total_scored', 'total_possible', 'total_percentage',
        'grade', 'has_critical_failure', 'submitted_at',
        'previous_audit_date', 'previous_audit_score', 'previous_auditor',
        'created_at', 'updated_at'
    )
    inlines = []
    actions = ['recalculate_scores', 'export_as_csv']
    ordering = ('-audit_date',)

    def grade_colored(self, obj):
        color_map = {'A': 'green', 'B': 'blue', 'C': 'orange', 'F': 'red'}
        color = color_map.get(obj.grade, 'black')
        return format_html('<b style="color:{};">{}</b>', color, obj.grade or '-')

    grade_colored.short_description = "Grade"

    @admin.action(description="Recalculate all totals and grades")
    def recalculate_scores(self, request, queryset):
        count = 0
        for audit in queryset:
            if audit.calculate_totals():
                count += 1
        self.message_user(request, f"✅ Recalculated totals for {count} audit(s).")

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('audit-stats/', self.admin_site.admin_view(self.audit_stats), name='audit_stats'),
        ]
        return custom_urls + urls

    def audit_stats(self, request):
        context = {
            'title': 'Audit Statistics',
            'total_audits': Audit.objects.count(),
            'submitted_audits': Audit.objects.filter(is_submitted=True).count(),
            'avg_score': Audit.objects.filter(is_submitted=True).aggregate(avg=Avg('total_percentage'))['avg'],
            'critical_failures': Audit.objects.filter(has_critical_failure=True).count(),
        }
        return render(request, 'admin/audit_stats.html', context)


@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ('name', 'order', 'question_count')
    search_fields = ('name', 'description')
    ordering = ('order',)
    inlines = []

    def question_count(self, obj):
        return obj.question_set.count()

    question_count.short_description = 'Questions'


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = (
        'short_question', 'section', 'possible_points',
        'is_critical', 'order', 'critical_failure_condition_preview'
    )
    list_filter = ('section', 'is_critical')
    search_fields = ('question_text', 'section__name')
    ordering = ('section', 'order')
    list_editable = ('order', 'is_critical')

    def short_question(self, obj):
        return (obj.question_text[:70] + '...') if len(obj.question_text) > 70 else obj.question_text

    short_question.short_description = "Question"

    def critical_failure_condition_preview(self, obj):
        return obj.critical_failure_condition[:50] + '...' if obj.critical_failure_condition else '-'

    critical_failure_condition_preview.short_description = "Failure Condition"


@admin.register(AuditSection)
class AuditSectionAdmin(admin.ModelAdmin):
    list_display = (
        'audit', 'section', 'scored_points', 'possible_points',
        'section_percentage', 'has_critical_failure', 'progress_percentage_display'
    )
    list_filter = ('audit__audit_date', 'section')
    search_fields = ('audit__restaurant__name', 'section__name')
    readonly_fields = ('section_percentage', 'has_critical_failure')

    def progress_percentage_display(self, obj):
        return f"{obj.progress_percentage:.1f}%"

    progress_percentage_display.short_description = "Progress"


@admin.register(AuditQuestionResponse)
class AuditQuestionResponseAdmin(admin.ModelAdmin):
    list_display = (
        'audit_section', 'short_question', 'scored_points',
        'needs_corrective_action', 'is_critical_display', 'has_comments'
    )
    list_filter = ('needs_corrective_action', 'question__is_critical')
    search_fields = ('question__question_text', 'audit_section__audit__restaurant__name')
    list_select_related = ('audit_section', 'question')

    def short_question(self, obj):
        return obj.question.question_text[:50] + '...' if len(
            obj.question.question_text) > 50 else obj.question.question_text

    short_question.short_description = "Question"

    def is_critical_display(self, obj):
        return obj.question.is_critical

    is_critical_display.boolean = True
    is_critical_display.short_description = "Critical?"

    def has_comments(self, obj):
        return bool(obj.comments and obj.comments.strip())

    has_comments.boolean = True
    has_comments.short_description = "Has Comments"


@admin.register(CorrectiveAction)
class CorrectiveActionAdmin(admin.ModelAdmin, ExportCsvMixin):
    list_display = (
        'audit', 'short_description', 'risk_level_colored',
        'assigned_to', 'deadline', 'completed', 'completion_date',
        'days_until_deadline'
    )
    list_filter = ('risk_level', 'completed', 'deadline', 'audit__restaurant__city')
    search_fields = ('assigned_to', 'audit__restaurant__name', 'description')
    date_hierarchy = 'deadline'
    readonly_fields = ('created_at', 'updated_at')
    actions = ['mark_completed', 'export_as_csv']
    list_editable = ('completed',)

    def short_description(self, obj):
        return obj.description[:50] + '...' if len(obj.description) > 50 else obj.description

    short_description.short_description = "Description"

    def risk_level_colored(self, obj):
        color_map = {
            'LOW': 'green', 'MEDIUM': 'orange',
            'HIGH': 'red', 'CRITICAL': 'darkred'
        }
        color = color_map.get(obj.risk_level, 'black')
        return format_html('<b style="color:{};">{}</b>', color, obj.get_risk_level_display())

    risk_level_colored.short_description = "Risk Level"

    def days_until_deadline(self, obj):
        if obj.completed:
            return "Completed"
        delta = obj.deadline - timezone.now().date()
        if delta.days < 0:
            return format_html('<b style="color:red;">Overdue by {} days</b>', abs(delta.days))
        elif delta.days == 0:
            return "Due today"
        else:
            return f"{delta.days} days"

    days_until_deadline.short_description = "Status"

    @admin.action(description="Mark selected as completed")
    def mark_completed(self, request, queryset):
        updated = queryset.update(completed=True, completion_date=timezone.now().date())
        self.message_user(request, f"✅ Marked {updated} corrective action(s) as completed.")
