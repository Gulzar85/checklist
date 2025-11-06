from django.contrib import admin
from .models import *

@admin.register(Restaurant)
class RestaurantAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'address', 'city']
    search_fields = ['name', 'code']
    list_filter = ['city']

@admin.register(Audit)
class AuditAdmin(admin.ModelAdmin):
    list_display = ['restaurant', 'audit_date', 'auditor_name', 'total_percentage', 'grade']
    list_filter = ['audit_date', 'grade', 'restaurant']
    search_fields = ['restaurant__name', 'auditor_name']
    date_hierarchy = 'audit_date'

@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ['name']


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['question_text', 'section', 'possible_points', 'is_critical']
    list_filter = ['section', 'is_critical']
    search_fields = ['question_text']

@admin.register(AuditSection)
class AuditSectionAdmin(admin.ModelAdmin):
    list_display = ['audit', 'section', 'scored_points', 'possible_points', 'section_percentage']
    list_filter = ['audit__audit_date', 'section']

@admin.register(AuditQuestionResponse)
class AuditQuestionResponseAdmin(admin.ModelAdmin):
    list_display = ['audit_section', 'question', 'scored_points', 'needs_corrective_action']
    list_filter = ['needs_corrective_action']

@admin.register(CorrectiveAction)
class CorrectiveActionAdmin(admin.ModelAdmin):
    list_display = ['audit', 'risk_level', 'assigned_to', 'deadline', 'completed']
    list_filter = ['risk_level', 'completed', 'deadline']