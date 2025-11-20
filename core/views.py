import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import Avg
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import ListView, TemplateView, View

from .models import (
    Restaurant, Audit, Section, Question,
    AuditSection, AuditQuestionResponse
)

logger = logging.getLogger(__name__)


# ------------------------------
# Audit Results View
# ------------------------------
@login_required
def audit_results(request, audit_id):
    """Display audit results"""
    audit = get_object_or_404(Audit, id=audit_id)
    sections = AuditSection.objects.filter(audit=audit).select_related('section')
    responses = AuditQuestionResponse.objects.filter(
        audit_section__audit=audit
    ).select_related('question', 'audit_section__section')

    # Check if this is a fresh submission
    show_success_modal = request.session.pop('show_audit_success', False)

    context = {
        'audit': audit,
        'sections': sections,
        'responses': responses,
        'has_critical_failure': audit.has_critical_failure,
        'status_description': audit.status_description,
        'show_success_modal': show_success_modal,
    }
    return render(request, 'core/audit_results.html', context)


# ------------------------------
# Dashboard
# ------------------------------
class AuditDashboardView(LoginRequiredMixin, TemplateView):
    """Main dashboard - Login Required"""
    template_name = 'core/dashboard.html'
    login_url = '/accounts/login/'
    redirect_field_name = 'next'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        try:
            if user.is_superuser or getattr(user, 'role', None) == 'admin':
                recent_audits = Audit.objects.select_related('restaurant', 'auditor_name').order_by('-audit_date')[:10]
                total_audits = Audit.objects.count()
                avg_score = Audit.objects.aggregate(avg=Avg('total_percentage'))['avg'] or 0
            else:
                recent_audits = Audit.objects.filter(auditor_name=user).select_related('restaurant').order_by(
                    '-audit_date')[:10]
                total_audits = recent_audits.count()
                avg_score = recent_audits.aggregate(avg=Avg('total_percentage'))['avg'] or 0

            context.update({
                'recent_audits': recent_audits,
                'restaurants': Restaurant.objects.all(),
                'total_audits': total_audits,
                'avg_score': round(avg_score, 2),
            })
        except Exception:
            logger.exception("Error preparing dashboard context for user id=%s", user.id)
            context.update({'recent_audits': [], 'restaurants': [], 'total_audits': 0, 'avg_score': 0})

        return context


# ------------------------------
# Create New Audit
# ------------------------------
@login_required
def create_audit(request):
    """Create a new audit"""
    if request.method == 'POST':
        try:
            restaurant_id = request.POST.get('restaurant')
            audit_date = request.POST.get('audit_date')
            manager_name = request.POST.get('manager_name')

            restaurant = get_object_or_404(Restaurant, id=restaurant_id)

            with transaction.atomic():
                audit = Audit.objects.create(
                    restaurant=restaurant,
                    audit_date=audit_date,
                    manager_on_duty=manager_name,
                    auditor_name=request.user
                )
                for section in Section.objects.all():
                    AuditSection.objects.create(audit=audit, section=section)

            return redirect('core:audit_form', audit_id=audit.id)

        except Exception:
            logger.exception("Error creating audit for user id=%s", request.user.id)
            messages.error(request, "Error creating audit. Please try again.")

    return render(request, 'core/create_audit.html', {
        'restaurants': Restaurant.objects.all(),
        'today': timezone.now().date()
    })


# ------------------------------
# List Audits
# ------------------------------
class AuditListView(LoginRequiredMixin, ListView):
    """List all audits with user filtering"""
    model = Audit
    template_name = 'core/audit_list.html'
    context_object_name = 'audits'
    paginate_by = 20
    ordering = ['-audit_date']

    def get_queryset(self):
        user = self.request.user
        qs = Audit.objects.select_related('restaurant', 'auditor_name')

        # Filtering
        restaurant_id = self.request.GET.get('restaurant')
        if restaurant_id:
            qs = qs.filter(restaurant_id=restaurant_id)

        if (val := self.request.GET.get('is_submitted')) in ['true', 'false']:
            qs = qs.filter(is_submitted=(val == 'true'))

        if (val := self.request.GET.get('has_critical_failure')) in ['true', 'false']:
            qs = qs.filter(has_critical_failure=(val == 'true'))

        if not (user.is_superuser or getattr(user, 'role', None) == 'admin'):
            qs = qs.filter(auditor_name=user)

        return qs.order_by('-audit_date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Get base queryset for statistics
        base_qs = Audit.objects.all()
        if not (user.is_superuser or getattr(user, 'role', None) == 'admin'):
            base_qs = base_qs.filter(auditor_name=user)

        # Apply the same filters as get_queryset for accurate counts
        filtered_qs = base_qs
        restaurant_id = self.request.GET.get('restaurant')
        if restaurant_id:
            filtered_qs = filtered_qs.filter(restaurant_id=restaurant_id)

        if (val := self.request.GET.get('is_submitted')) in ['true', 'false']:
            filtered_qs = filtered_qs.filter(is_submitted=(val == 'true'))

        if (val := self.request.GET.get('has_critical_failure')) in ['true', 'false']:
            filtered_qs = filtered_qs.filter(has_critical_failure=(val == 'true'))

        # Calculate statistics
        total_audits = filtered_qs.count()
        submitted_count = filtered_qs.filter(is_submitted=True).count()
        in_progress_count = filtered_qs.filter(is_submitted=False).count()
        critical_failure_count = filtered_qs.filter(has_critical_failure=True).count()

        context.update({
            'restaurants': Restaurant.objects.all(),
            'selected_restaurant': self.request.GET.get('restaurant'),
            'is_submitted_filter': self.request.GET.get('is_submitted'),
            'critical_failure_filter': self.request.GET.get('has_critical_failure'),
            'submitted_count': submitted_count,
            'in_progress_count': in_progress_count,
            'critical_failure_count': critical_failure_count,
            'total_audits': total_audits,
        })
        return context

# ------------------------------
# Audit Form View
# ------------------------------
@login_required
def audit_form(request, audit_id):
    """Main audit form with sections and questions"""
    audit = get_object_or_404(Audit, id=audit_id)

    if not (request.user.is_superuser or getattr(request.user, 'role', None) == 'admin'):
        if audit.auditor_name != request.user:
            messages.error(request, "You don't have permission to access this audit.")
            return redirect('core:dashboard')

    section_data = []
    for section in Section.objects.all().order_by('order'):
        audit_section, _ = AuditSection.objects.get_or_create(audit=audit, section=section)
        questions = section.question_set.all().order_by('order')

        q_data = []
        for q in questions:
            response = AuditQuestionResponse.objects.filter(audit_section=audit_section, question=q).first()
            q_data.append({
                'id': q.id,
                'text': q.question_text,
                'possible_points': float(q.possible_points),
                'is_critical': q.is_critical,
                'scored_points': float(response.scored_points) if response else 0.0,
                'comments': response.comments if response else '',
                'needs_corrective_action': response.needs_corrective_action if response else False,
                'response_id': response.id if response else None,
            })

        section_data.append({
            'section': section,
            'audit_section': audit_section,
            'questions': q_data,
            'section_score': float(audit_section.scored_points),
            'section_percentage': float(audit_section.section_percentage),
            'has_critical_failure': audit_section.has_critical_failure,
            'progress_percentage': audit_section.progress_percentage,
        })

    context = {
        'audit': audit,
        'section_data': section_data,
        'progress_percentage': audit.get_progress_percentage(),
        'can_be_submitted': audit.can_be_submitted,
        'status_description': audit.status_description,
    }
    return render(request, 'core/audit_form.html', context)


# ------------------------------
# Save Response (AJAX)
# ------------------------------
@csrf_exempt
@login_required
@transaction.atomic
def save_response(request):
    """Save question response via AJAX safely"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request'}, status=400)

    try:
        audit_id = request.POST.get('audit_id')
        section_id = request.POST.get('section_id')
        question_id = request.POST.get('question_id')
        comments = request.POST.get('comments', '')
        needs_action = request.POST.get('needs_corrective_action', 'false') == 'true'
        scored_points = request.POST.get('scored_points') or '0'

        try:
            scored_points = float(scored_points)
        except (TypeError, ValueError):
            scored_points = 0.0

        # Validate audit ownership
        user = request.user
        audit_qs = Audit.objects.all()
        if not (user.is_superuser or getattr(user, 'role', None) == 'admin'):
            audit_qs = audit_qs.filter(auditor_name=user)

        audit = get_object_or_404(audit_qs, id=audit_id)
        section = get_object_or_404(Section, id=section_id)
        question = get_object_or_404(Question, id=question_id)

        audit_section, _ = AuditSection.objects.get_or_create(audit=audit, section=section)
        response, created = AuditQuestionResponse.objects.get_or_create(
            audit_section=audit_section,
            question=question,
            defaults={'scored_points': scored_points, 'comments': comments, 'needs_corrective_action': needs_action}
        )

        if not created:
            response.scored_points = scored_points
            response.comments = comments
            response.needs_corrective_action = needs_action
            response.save()

        # Critical questions automatically need corrective action
        if question.is_critical and scored_points == 0:
            response.needs_corrective_action = True
            response.save()

        audit_section.calculate_section_score()
        audit.calculate_totals()

        return JsonResponse({
            'success': True,
            'message': 'Response saved successfully',
            'section_score': float(audit_section.scored_points),
            'section_percentage': float(audit_section.section_percentage),
            'section_has_critical_failure': audit_section.has_critical_failure,
            'total_score': float(audit.total_scored),
            'total_percentage': float(audit.total_percentage),
            'grade': audit.grade,
            'audit_status': audit.status,
            'progress_percentage': audit.get_progress_percentage(),
            'status_description': audit.status_description,
            'grade_with_reason': audit.grade_with_reason,
        })

    except Exception:
        logger.exception("Error saving response (user id=%s)", request.user.id)
        return JsonResponse({'success': False, 'message': 'Internal server error'}, status=500)


# ------------------------------
# Submit Audit
# ------------------------------
@login_required
@transaction.atomic
def submit_audit(request, audit_id):
    """Submit an audit"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request'}, status=400)

    try:
        user = request.user
        audit_qs = Audit.objects.all()
        if not (user.is_superuser or getattr(user, 'role', None) == 'admin'):
            audit_qs = audit_qs.filter(auditor_name=user)

        audit = get_object_or_404(audit_qs, id=audit_id)

        if not audit.can_be_submitted:
            return JsonResponse({'success': False, 'message': 'Audit not complete enough to submit.'})

        success = audit.submit_audit()
        if not success:
            return JsonResponse({'success': False, 'message': 'Error submitting audit.'})

        # Set session flag to show success modal on results page
        request.session['show_audit_success'] = True

        return JsonResponse({
            'success': True,
            'message': 'Audit submitted successfully.',
            'grade': audit.grade,
            'total_percentage': float(audit.total_percentage),
            'status_description': audit.status_description,
            'submitted_at': audit.submitted_at.strftime('%Y-%m-%d %H:%M:%S') if audit.submitted_at else None,
            'redirect_url': reverse('core:audit_results', kwargs={'audit_id': audit.id})
        })

    except Exception:
        logger.exception("Error submitting audit id=%s", audit_id)
        return JsonResponse({'success': False, 'message': 'Internal server error'}, status=500)

# ------------------------------
# Audit Progress
# ------------------------------
@login_required
def audit_progress(request, audit_id):
    """Return audit progress summary"""
    try:
        user = request.user
        audit_qs = Audit.objects.all()
        if not (user.is_superuser or getattr(user, 'role', None) == 'admin'):
            audit_qs = audit_qs.filter(auditor_name=user)
        audit = get_object_or_404(audit_qs, id=audit_id)

        sections = AuditSection.objects.filter(audit=audit).select_related('section')

        progress_data = []
        total_questions = answered_questions = 0

        for section in sections:
            qs = Question.objects.filter(section=section.section)
            total_q = qs.count()
            total_questions += total_q

            answered_q = AuditQuestionResponse.objects.filter(audit_section=section).exclude(
                scored_points__isnull=True, comments__exact=''
            ).count()
            answered_questions += answered_q

            section_percentage = (answered_q / total_q * 100) if total_q > 0 else 0
            progress_data.append({
                'section_name': section.section.name,
                'answered': answered_q,
                'total': total_q,
                'percentage': section_percentage,
                'section_score': float(section.scored_points),
                'section_percentage': float(section.section_percentage),
                'has_critical_failure': section.has_critical_failure,
                'progress_percentage': section.progress_percentage,
            })

        overall_progress = (answered_questions / total_questions * 100) if total_questions > 0 else 0
        return JsonResponse({
            'progress': progress_data,
            'overall_progress': overall_progress,
            'total_questions': total_questions,
            'answered_questions': answered_questions,
            'total_score': float(audit.total_scored),
            'total_percentage': float(audit.total_percentage),
            'grade': audit.grade,
            'status': audit.status,
            'can_be_submitted': audit.can_be_submitted,
        })

    except Exception:
        logger.exception("Error calculating progress for audit id=%s", audit_id)
        return JsonResponse({'error': 'Internal server error'}, status=500)


# ------------------------------
# Restaurant Audits
# ------------------------------
class RestaurantAuditsView(LoginRequiredMixin, ListView):
    """Restaurant audits list"""
    template_name = 'core/restaurant_audits.html'
    context_object_name = 'audits'
    paginate_by = 10

    def get_queryset(self):
        self.restaurant = get_object_or_404(Restaurant, pk=self.kwargs['restaurant_id'])
        qs = Audit.objects.filter(restaurant=self.restaurant).select_related('auditor_name').order_by('-audit_date')
        if not (self.request.user.is_superuser or getattr(self.request.user, 'role', None) == 'admin'):
            qs = qs.filter(auditor_name=self.request.user)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        audits = self.get_queryset()
        context.update({
            'restaurant': self.restaurant,
            'total_audits': audits.count(),
            'avg_score': audits.aggregate(avg=Avg('total_percentage'))['avg'] or 0,
            'latest_audit': audits.first(),
            'grade_a_count': audits.filter(grade='A').count(),
            'submitted_audits': audits.filter(is_submitted=True).count(),
            'critical_failure_audits': audits.filter(has_critical_failure=True).count(),
            'user_can_delete': self.request.user.is_superuser or getattr(self.request.user, 'role', None) == 'admin',
        })
        return context


# ------------------------------
# Delete Audit
# ------------------------------
class DeleteAuditView(LoginRequiredMixin, View):
    """Delete audit safely"""

    def post(self, request, audit_id):
        user = request.user
        qs = Audit.objects.all()
        if not (user.is_superuser or getattr(user, 'role', None) == 'admin'):
            qs = qs.filter(auditor_name=user)

        audit = get_object_or_404(qs, id=audit_id)
        restaurant_id = audit.restaurant.id
        audit_name = f"{audit.restaurant.name} - {audit.audit_date}"

        try:
            audit.delete()
            messages.success(request, f"Audit '{audit_name}' deleted successfully.")
            logger.info("Audit deleted by user %s: %s", user.id, audit_name)
        except Exception:
            logger.exception("Error deleting audit id=%s", audit_id)
            messages.error(request, "Error deleting audit.")

        return redirect('core:restaurant_audits', restaurant_id=restaurant_id)

    def get(self, request, audit_id):
        messages.warning(request, "Deletion must be via POST request.")
        return redirect('core:dashboard')


# ------------------------------
# Audit Detail
# ------------------------------
@login_required
def audit_detail(request, audit_id):
    """Detailed audit view with all responses"""
    user = request.user
    qs = Audit.objects.all()
    if not (user.is_superuser or getattr(user, 'role', None) == 'admin'):
        qs = qs.filter(auditor_name=user)

    audit = get_object_or_404(qs, id=audit_id)
    sections = AuditSection.objects.filter(audit=audit).select_related('section')
    responses = AuditQuestionResponse.objects.filter(
        audit_section__audit=audit
    ).select_related('question', 'audit_section__section')

    return render(request, 'core/audit_detail.html', {
        'audit': audit,
        'sections': sections,
        'responses': responses,
        'grade_info': audit.grade_with_reason,
        'status_description': audit.status_description,
    })
