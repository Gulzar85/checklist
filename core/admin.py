from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Restaurant, Audit, Section, Question,
    AuditSection, AuditQuestionResponse, CorrectiveAction,
    AuditTemplate, TemplateSection
)


# ------------------------------
# Inline Admins
# ------------------------------

class QuestionInline(admin.TabularInline):
    model = Question
    extra = 1
    fields = ('question_text', 'possible_points', 'is_critical', 'order')
    ordering = ('order',)


class AuditSectionInline(admin.TabularInline):
    model = AuditSection
    extra = 0
    readonly_fields = ('scored_points', 'possible_points', 'section_percentage', 'has_critical_failure')
    can_delete = False
    show_change_link = True


class AuditQuestionResponseInline(admin.TabularInline):
    model = AuditQuestionResponse
    extra = 0
    fields = ('question', 'scored_points', 'comments', 'needs_corrective_action')
    readonly_fields = ('question',)
    show_change_link = True


class CorrectiveActionInline(admin.TabularInline):
    model = CorrectiveAction
    extra = 0
    fields = ('question_response', 'risk_level', 'assigned_to', 'deadline', 'completed')
    readonly_fields = ('question_response',)
    show_change_link = True


# ------------------------------
# Model Admins
# ------------------------------

@admin.register(Restaurant)
class RestaurantAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'city', 'country')
    search_fields = ('name', 'code', 'city')
    list_filter = ('city', 'country')
    ordering = ('name',)


@admin.register(Audit)
class AuditAdmin(admin.ModelAdmin):
    list_display = (
        'restaurant',
        'audit_date',
        'auditor_name',
        'grade_colored',
        'total_percentage',
        'has_critical_failure',
        'is_submitted',
    )
    list_filter = (
        'audit_date',
        'grade',
        'has_critical_failure',
        'is_submitted',
        'restaurant__city',
    )
    search_fields = (
        'restaurant__name',
        'restaurant__code',
        'auditor_name__username',
    )
    date_hierarchy = 'audit_date'
    readonly_fields = (
        'total_scored', 'total_possible', 'total_percentage',
        'grade', 'has_critical_failure', 'submitted_at',
        'previous_audit_date', 'previous_audit_score', 'previous_auditor',
    )
    inlines = [AuditSectionInline, CorrectiveActionInline]
    actions = ['recalculate_scores']
    ordering = ('-audit_date',)

    def grade_colored(self, obj):
        """Show grade with color."""
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


@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ('name', 'order')
    search_fields = ('name',)
    ordering = ('order',)
    inlines = [QuestionInline]


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = (
        'short_question',
        'section',
        'possible_points',
        'is_critical',
        'order',
    )
    list_filter = ('section', 'is_critical')
    search_fields = ('question_text', 'section__name')
    ordering = ('section', 'order')

    def short_question(self, obj):
        return (obj.question_text[:70] + '...') if len(obj.question_text) > 70 else obj.question_text
    short_question.short_description = "Question"


@admin.register(AuditSection)
class AuditSectionAdmin(admin.ModelAdmin):
    list_display = (
        'audit',
        'section',
        'scored_points',
        'possible_points',
        'section_percentage',
        'has_critical_failure',
    )
    list_filter = ('audit__audit_date', 'section')
    search_fields = ('audit__restaurant__name', 'section__name')
    readonly_fields = ('section_percentage', 'has_critical_failure')
    inlines = [AuditQuestionResponseInline]


@admin.register(AuditQuestionResponse)
class AuditQuestionResponseAdmin(admin.ModelAdmin):
    list_display = (
        'audit_section',
        'question',
        'scored_points',
        'needs_corrective_action',
        'is_critical_display',
    )
    list_filter = ('needs_corrective_action', 'question__is_critical')
    search_fields = ('question__question_text', 'audit_section__audit__restaurant__name')
    list_select_related = ('audit_section', 'question')

    def is_critical_display(self, obj):
        return obj.question.is_critical
    is_critical_display.boolean = True
    is_critical_display.short_description = "Critical?"


@admin.register(CorrectiveAction)
class CorrectiveActionAdmin(admin.ModelAdmin):
    list_display = (
        'audit',
        'question_response',
        'risk_level',
        'assigned_to',
        'deadline',
        'completed',
        'completion_date',
    )
    list_filter = ('risk_level', 'completed', 'deadline')
    search_fields = ('assigned_to', 'audit__restaurant__name')
    date_hierarchy = 'deadline'
    readonly_fields = ('created_at', 'updated_at')


@admin.register(AuditTemplate)
class AuditTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'version', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name',)
    inlines = []


@admin.register(TemplateSection)
class TemplateSectionAdmin(admin.ModelAdmin):
    list_display = ('template', 'section', 'order')
    ordering = ('template', 'order')
