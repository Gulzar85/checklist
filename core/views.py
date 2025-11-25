import csv
import logging
from datetime import timedelta
from decimal import Decimal, InvalidOperation
from typing import Any, Dict

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import Avg, Count, Max, Q
from django.http import JsonResponse, HttpResponse, HttpRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.views.generic import DetailView, UpdateView, DeleteView, ListView, TemplateView, View

from .models import (
    Restaurant, Audit, Section, Question,
    AuditSection, AuditQuestionResponse, CorrectiveAction
)

logger = logging.getLogger(__name__)


class AuditDashboardView(LoginRequiredMixin, TemplateView):
    """Enhanced main dashboard with comprehensive statistics"""
    template_name = 'core/dashboard.html'
    login_url = '/accounts/login/'
    redirect_field_name = 'next'

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        user = self.request.user

        try:
            # Base querysets with performance optimizations
            if user.is_superuser or getattr(user, 'role', None) == 'admin':
                # Admin - all data
                recent_audits = Audit.objects.select_related(
                    'restaurant', 'auditor_name'
                ).order_by('-audit_date')[:10]
                total_audits = Audit.objects.count()
                avg_score = Audit.objects.aggregate(
                    avg=Avg('total_percentage')
                )['avg'] or Decimal('0.00')
                restaurants = Restaurant.objects.annotate(
                    audit_count=Count('audit')
                ).order_by('name')

                # Corrective Actions - Admin view
                corrective_actions = CorrectiveAction.objects.all()
                total_corrective_actions = corrective_actions.count()
                completed_corrective_actions = corrective_actions.filter(completed=True).count()
                pending_corrective_actions = corrective_actions.filter(completed=False).count()
                overdue_corrective_actions = corrective_actions.filter(
                    completed=False,
                    deadline__lt=timezone.now().date()
                ).count()
                critical_corrective_actions = corrective_actions.filter(risk_level='CRITICAL').count()

                # Admin-specific statistics
                submitted_count = Audit.objects.filter(is_submitted=True).count()
                in_progress_count = Audit.objects.filter(is_submitted=False).count()
                critical_count = Audit.objects.filter(has_critical_failure=True).count()
                active_locations = Restaurant.objects.filter(
                    audit__isnull=False
                ).distinct().count()
                cities_count = Restaurant.objects.values('city').distinct().count()

                # User-specific stats for admin view
                user_audit_count = Audit.objects.filter(auditor_name=user).count()
                user_avg_score = Audit.objects.filter(auditor_name=user).aggregate(
                    avg=Avg('total_percentage')
                )['avg'] or Decimal('0.00')
                user_restaurants = Restaurant.objects.filter(
                    audit__auditor_name=user
                ).distinct().count()

            else:
                # Regular user - only their data
                recent_audits = Audit.objects.filter(
                    auditor_name=user
                ).select_related('restaurant').order_by('-audit_date')[:10]
                total_audits = Audit.objects.filter(auditor_name=user).count()
                avg_score = Audit.objects.filter(auditor_name=user).aggregate(
                    avg=Avg('total_percentage')
                )['avg'] or Decimal('0.00')
                restaurants = Restaurant.objects.filter(
                    audit__auditor_name=user
                ).distinct().annotate(
                    audit_count=Count('audit')
                ).order_by('name')

                # Corrective Actions - User view (only their audits)
                corrective_actions = CorrectiveAction.objects.filter(audit__auditor_name=user)
                total_corrective_actions = corrective_actions.count()
                completed_corrective_actions = corrective_actions.filter(completed=True).count()
                pending_corrective_actions = corrective_actions.filter(completed=False).count()
                overdue_corrective_actions = corrective_actions.filter(
                    completed=False,
                    deadline__lt=timezone.now().date()
                ).count()
                critical_corrective_actions = corrective_actions.filter(risk_level='CRITICAL').count()

                # User-specific statistics
                submitted_count = Audit.objects.filter(
                    auditor_name=user, is_submitted=True
                ).count()
                in_progress_count = Audit.objects.filter(
                    auditor_name=user, is_submitted=False
                ).count()
                critical_count = Audit.objects.filter(
                    auditor_name=user, has_critical_failure=True
                ).count()
                active_locations = restaurants.count()
                cities_count = restaurants.values('city').distinct().count()

                # User stats (same as above for consistency)
                user_audit_count = total_audits
                user_avg_score = avg_score
                user_restaurants = active_locations

            # Grade distribution calculation
            grade_distribution = []
            for grade in ['A', 'B', 'C', 'F']:
                if user.is_superuser or getattr(user, 'role', None) == 'admin':
                    count = Audit.objects.filter(grade=grade).count()
                    avg_grade_score = Audit.objects.filter(grade=grade).aggregate(
                        avg=Avg('total_percentage')
                    )['avg'] or Decimal('0.00')
                else:
                    count = Audit.objects.filter(
                        auditor_name=user, grade=grade
                    ).count()
                    avg_grade_score = Audit.objects.filter(
                        auditor_name=user, grade=grade
                    ).aggregate(
                        avg=Avg('total_percentage')
                    )['avg'] or Decimal('0.00')

                if total_audits > 0:
                    percentage = (count / total_audits) * 100
                else:
                    percentage = 0

                grade_distribution.append({
                    'grade': grade,
                    'count': count,
                    'percentage': percentage,
                    'avg_score': avg_grade_score
                })

            # Corrective Actions completion percentage
            if total_corrective_actions > 0:
                corrective_completion_percentage = (completed_corrective_actions / total_corrective_actions) * 100
            else:
                corrective_completion_percentage = 0

            # Risk level distribution for corrective actions
            corrective_risk_distribution = []
            for risk_level, display_name in CorrectiveAction.RISK_LEVELS:
                if user.is_superuser or getattr(user, 'role', None) == 'admin':
                    count = CorrectiveAction.objects.filter(risk_level=risk_level).count()
                else:
                    count = CorrectiveAction.objects.filter(
                        risk_level=risk_level,
                        audit__auditor_name=user
                    ).count()

                if total_corrective_actions > 0:
                    percentage = (count / total_corrective_actions) * 100
                else:
                    percentage = 0

                corrective_risk_distribution.append({
                    'level': risk_level,
                    'display_name': display_name,
                    'count': count,
                    'percentage': percentage
                })

            # Recent corrective actions
            if user.is_superuser or getattr(user, 'role', None) == 'admin':
                recent_corrective_actions = CorrectiveAction.objects.select_related(
                    'audit', 'audit__restaurant'
                ).order_by('-created_at')[:5]
            else:
                recent_corrective_actions = CorrectiveAction.objects.filter(
                    audit__auditor_name=user
                ).select_related('audit', 'audit__restaurant').order_by('-created_at')[:5]

            # Additional calculated statistics
            overdue_count = overdue_corrective_actions
            resolved_count = completed_corrective_actions
            storage_used = min(int((total_audits / 1000) * 100), 100)

            context.update({
                'recent_audits': recent_audits,
                'restaurants': restaurants,
                'total_audits': total_audits,
                'avg_score': round(float(avg_score), 2),
                'submitted_count': submitted_count,
                'in_progress_count': in_progress_count,
                'critical_count': critical_count,
                'active_locations': active_locations,
                'cities_count': cities_count,
                'overdue_count': overdue_count,
                'resolved_count': resolved_count,
                'storage_used': storage_used,
                'user_audit_count': user_audit_count,
                'user_avg_score': round(float(user_avg_score), 2),
                'user_restaurants': user_restaurants,
                'grade_distribution': grade_distribution,

                # Corrective Actions Data
                'total_corrective_actions': total_corrective_actions,
                'completed_corrective_actions': completed_corrective_actions,
                'pending_corrective_actions': pending_corrective_actions,
                'overdue_corrective_actions': overdue_corrective_actions,
                'critical_corrective_actions': critical_corrective_actions,
                'corrective_completion_percentage': round(corrective_completion_percentage, 1),
                'corrective_risk_distribution': corrective_risk_distribution,
                'recent_corrective_actions': recent_corrective_actions,
                'today': timezone.now().date(),
            })

        except Exception as e:
            logger.exception("Error preparing dashboard context for user id=%s", user.id)
            # Provide safe default values
            context.update({
                'recent_audits': [],
                'restaurants': [],
                'total_audits': 0,
                'avg_score': 0,
                'submitted_count': 0,
                'in_progress_count': 0,
                'critical_count': 0,
                'active_locations': 0,
                'cities_count': 0,
                'overdue_count': 0,
                'resolved_count': 0,
                'storage_used': 0,
                'user_audit_count': 0,
                'user_avg_score': 0,
                'user_restaurants': 0,
                'grade_distribution': [],

                # Corrective Actions Defaults
                'total_corrective_actions': 0,
                'completed_corrective_actions': 0,
                'pending_corrective_actions': 0,
                'overdue_corrective_actions': 0,
                'critical_corrective_actions': 0,
                'corrective_completion_percentage': 0,
                'corrective_risk_distribution': [],
                'recent_corrective_actions': [],
                'today': timezone.now().date(),
            })

        return context


@login_required
def create_audit(request: HttpRequest):
    """Create a new audit"""
    if request.method == 'POST':
        try:
            restaurant_id = request.POST.get('restaurant')
            audit_date = request.POST.get('audit_date')
            manager_name = request.POST.get('manager_name')

            if not all([restaurant_id, audit_date, manager_name]):
                messages.error(request, "All fields are required.")
                return render(request, 'core/create_audit.html', {
                    'restaurants': Restaurant.objects.all(),
                    'today': timezone.now().date()
                })

            restaurant = get_object_or_404(Restaurant, id=restaurant_id)

            with transaction.atomic():
                audit = Audit.objects.create(
                    restaurant=restaurant,
                    audit_date=audit_date,
                    manager_on_duty=manager_name,
                    auditor_name=request.user
                )

                # Create audit sections for all sections
                sections = Section.objects.all()
                for section in sections:
                    AuditSection.objects.create(audit=audit, section=section)

            messages.success(request, "Audit created successfully!")
            return redirect('core:audit_form', audit_id=audit.id)

        except Exception as e:
            logger.exception("Error creating audit for user id=%s", request.user.id)
            messages.error(request, "Error creating audit. Please try again.")

    return render(request, 'core/create_audit.html', {
        'restaurants': Restaurant.objects.all(),
        'today': timezone.now().date()
    })


class AuditListView(LoginRequiredMixin, ListView):
    """Enhanced list view with filtering and statistics"""
    model = Audit
    template_name = 'core/audit_list.html'
    context_object_name = 'audits'
    paginate_by = 20
    ordering = ['-audit_date']

    def get_queryset(self):
        user = self.request.user
        qs = Audit.objects.select_related('restaurant', 'auditor_name')

        # Apply user-based filtering
        if not (user.is_superuser or getattr(user, 'role', None) == 'admin'):
            qs = qs.filter(auditor_name=user)

        # Apply filters
        restaurant_id = self.request.GET.get('restaurant')
        if restaurant_id:
            qs = qs.filter(restaurant_id=restaurant_id)

        if (val := self.request.GET.get('is_submitted')) in ['true', 'false']:
            qs = qs.filter(is_submitted=(val == 'true'))

        if (val := self.request.GET.get('has_critical_failure')) in ['true', 'false']:
            qs = qs.filter(has_critical_failure=(val == 'true'))

        if (val := self.request.GET.get('grade')):
            qs = qs.filter(grade=val)

        # Date range filtering
        start_date = self.request.GET.get('start_date')
        end_date = self.request.GET.get('end_date')
        if start_date:
            qs = qs.filter(audit_date__gte=start_date)
        if end_date:
            qs = qs.filter(audit_date__lte=end_date)

        return qs.order_by('-audit_date')

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
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

        # Calculate comprehensive statistics
        total_audits = filtered_qs.count()
        submitted_count = filtered_qs.filter(is_submitted=True).count()
        in_progress_count = filtered_qs.filter(is_submitted=False).count()
        critical_failure_count = filtered_qs.filter(has_critical_failure=True).count()

        # Grade distribution
        grade_distribution = filtered_qs.values('grade').annotate(
            count=Count('id')
        ).order_by('grade')

        context.update({
            'restaurants': Restaurant.objects.all(),
            'selected_restaurant': self.request.GET.get('restaurant'),
            'is_submitted_filter': self.request.GET.get('is_submitted'),
            'critical_failure_filter': self.request.GET.get('has_critical_failure'),
            'grade_filter': self.request.GET.get('grade'),
            'start_date_filter': self.request.GET.get('start_date'),
            'end_date_filter': self.request.GET.get('end_date'),
            'submitted_count': submitted_count,
            'in_progress_count': in_progress_count,
            'critical_failure_count': critical_failure_count,
            'total_audits': total_audits,
            'grade_distribution': grade_distribution,
        })
        return context


@login_required
def audit_form(request: HttpRequest, audit_id: int):
    """Enhanced audit form with better performance and error handling"""
    audit = get_object_or_404(Audit, id=audit_id)

    # Permission check
    if not (request.user.is_superuser or getattr(request.user, 'role', None) == 'admin'):
        if audit.auditor_name != request.user:
            messages.error(request, "You don't have permission to access this audit.")
            return redirect('core:dashboard')

    if audit.is_submitted:
        messages.warning(request, "This audit has been submitted and is read-only.")

    try:
        # Optimized query with prefetching - FIXED: use 'questions' instead of 'question_set'
        sections = Section.objects.prefetch_related(
            'questions'  # CHANGED from 'question_set' to 'questions'
        ).all().order_by('order')

        section_data = []
        for section in sections:
            audit_section, created = AuditSection.objects.get_or_create(
                audit=audit,
                section=section
            )

            # Get or create responses for all questions in this section
            questions = section.questions.all().order_by('order')  # CHANGED from question_set to questions
            q_data = []

            for question in questions:
                response, response_created = AuditQuestionResponse.objects.get_or_create(
                    audit_section=audit_section,
                    question=question,
                    defaults={
                        'scored_points': Decimal('0.00'),
                        'comments': '',
                        'needs_corrective_action': False
                    }
                )

                q_data.append({
                    'id': question.id,
                    'text': question.question_text,
                    'possible_points': float(question.possible_points),
                    'is_critical': question.is_critical,
                    'critical_failure_condition': question.critical_failure_condition,
                    'scored_points': float(response.scored_points),
                    'comments': response.comments,
                    'needs_corrective_action': response.needs_corrective_action,
                    'response_id': response.id,
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

    except Exception as e:
        logger.exception("Error loading audit form for audit id=%s", audit_id)
        messages.error(request, "Error loading audit form. Please try again.")
        return redirect('core:dashboard')

@csrf_exempt
@login_required
@transaction.atomic
def save_response(request: HttpRequest):
    """Enhanced save response with better error handling and validation"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=405)

    try:
        audit_id = request.POST.get('audit_id')
        section_id = request.POST.get('section_id')
        question_id = request.POST.get('question_id')
        comments = request.POST.get('comments', '').strip()
        needs_action = request.POST.get('needs_corrective_action', 'false') == 'true'
        scored_points = request.POST.get('scored_points') or '0'

        # Validate required fields
        if not all([audit_id, section_id, question_id]):
            return JsonResponse({
                'success': False,
                'message': 'Missing required fields'
            }, status=400)

        # Validate numeric input
        try:
            scored_points = Decimal(scored_points)
            if scored_points < 0:
                raise ValueError("Score cannot be negative")
        except (InvalidOperation, ValueError) as e:
            return JsonResponse({
                'success': False,
                'message': 'Invalid score value'
            }, status=400)

        # Validate audit ownership and existence
        user = request.user
        audit_qs = Audit.objects.select_related('restaurant')
        if not (user.is_superuser or getattr(user, 'role', None) == 'admin'):
            audit_qs = audit_qs.filter(auditor_name=user)

        audit = get_object_or_404(audit_qs, id=audit_id)

        # Check if audit is submitted (read-only)
        if audit.is_submitted:
            return JsonResponse({
                'success': False,
                'message': 'Cannot modify submitted audit'
            }, status=403)

        section = get_object_or_404(Section, id=section_id)
        question = get_object_or_404(Question, id=question_id)

        # Get or create audit section and response
        audit_section, _ = AuditSection.objects.get_or_create(
            audit=audit,
            section=section
        )

        response, created = AuditQuestionResponse.objects.get_or_create(
            audit_section=audit_section,
            question=question,
            defaults={
                'scored_points': scored_points,
                'comments': comments,
                'needs_corrective_action': needs_action
            }
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

        # Recalculate scores
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
            'has_critical_failure': audit.has_critical_failure,
        })

    except Exception as e:
        logger.exception("Error saving response (user id=%s)", request.user.id)
        return JsonResponse({
            'success': False,
            'message': 'Internal server error'
        }, status=500)


@login_required
@transaction.atomic
def submit_audit(request: HttpRequest, audit_id: int):
    """Enhanced audit submission with comprehensive validation"""
    if request.method != 'POST':
        return JsonResponse({
            'success': False,
            'message': 'Invalid request method'
        }, status=405)

    try:
        user = request.user
        audit_qs = Audit.objects.select_related('restaurant')
        if not (user.is_superuser or getattr(user, 'role', None) == 'admin'):
            audit_qs = audit_qs.filter(auditor_name=user)

        audit = get_object_or_404(audit_qs, id=audit_id)

        # Validate audit state
        if audit.is_submitted:
            return JsonResponse({
                'success': False,
                'message': 'Audit is already submitted.'
            })

        if not audit.can_be_submitted:
            progress = audit.get_progress_percentage()
            return JsonResponse({
                'success': False,
                'message': f'Audit not complete enough to submit. Progress: {progress:.1f}%'
            })

        # Perform submission
        success = audit.submit_audit()
        if not success:
            return JsonResponse({
                'success': False,
                'message': 'Error submitting audit. Please try again.'
            })

        # Set session flag to show success modal on results page
        request.session['show_audit_success'] = True

        # Log the submission
        logger.info(
            "Audit submitted by user %s: %s",
            user.id,
            audit_id
        )

        return JsonResponse({
            'success': True,
            'message': 'Audit submitted successfully.',
            'grade': audit.grade,
            'total_percentage': float(audit.total_percentage),
            'total_score': float(audit.total_scored),
            'status_description': audit.status_description,
            'has_critical_failure': audit.has_critical_failure,
            'submitted_at': audit.submitted_at.strftime('%Y-%m-%d %H:%M:%S') if audit.submitted_at else None,
            'redirect_url': reverse('core:audit_results', kwargs={'audit_id': audit.id})
        })

    except Exception as e:
        logger.exception("Error submitting audit id=%s", audit_id)
        return JsonResponse({
            'success': False,
            'message': 'Internal server error during submission'
        }, status=500)


@login_required
def audit_results(request: HttpRequest, audit_id: int):
    """Enhanced audit results with comprehensive data"""
    audit = get_object_or_404(Audit, id=audit_id)

    # Permission check
    if not (request.user.is_superuser or getattr(request.user, 'role', None) == 'admin'):
        if audit.auditor_name != request.user:
            messages.error(request, "You don't have permission to view this audit.")
            return redirect('core:dashboard')

    try:
        # Optimized queries with prefetching
        sections = AuditSection.objects.filter(
            audit=audit
        ).select_related('section').prefetch_related(
            'auditquestionresponse_set__question'
        ).order_by('section__order')

        responses = AuditQuestionResponse.objects.filter(
            audit_section__audit=audit
        ).select_related(
            'question',
            'audit_section__section'
        ).order_by('question__order')

        # Check if this is a fresh submission
        show_success_modal = request.session.pop('show_audit_success', False)

        # Get corrective actions for this audit
        corrective_actions = CorrectiveAction.objects.filter(
            audit=audit
        ).select_related('question_response__question')

        context = {
            'audit': audit,
            'sections': sections,
            'responses': responses,
            'corrective_actions': corrective_actions,
            'has_critical_failure': audit.has_critical_failure,
            'status_description': audit.status_description,
            'show_success_modal': show_success_modal,
        }
        return render(request, 'core/audit_results.html', context)

    except Exception as e:
        logger.exception("Error loading audit results for audit id=%s", audit_id)
        messages.error(request, "Error loading audit results. Please try again.")
        return redirect('core:audit_list')


@login_required
def audit_detail(request: HttpRequest, audit_id: int):
    """Enhanced detailed audit view"""
    user = request.user
    qs = Audit.objects.select_related('restaurant')
    if not (user.is_superuser or getattr(user, 'role', None) == 'admin'):
        qs = qs.filter(auditor_name=user)

    audit = get_object_or_404(qs, id=audit_id)

    try:
        sections = AuditSection.objects.filter(
            audit=audit
        ).select_related('section').order_by('section__order')

        responses = AuditQuestionResponse.objects.filter(
            audit_section__audit=audit
        ).select_related(
            'question',
            'audit_section__section'
        ).order_by('audit_section__section__order', 'question__order')

        corrective_actions = CorrectiveAction.objects.filter(
            audit=audit
        ).select_related('question_response__question')

        return render(request, 'core/audit_detail.html', {
            'audit': audit,
            'sections': sections,
            'responses': responses,
            'corrective_actions': corrective_actions,
            'grade_info': audit.grade_with_reason,
            'status_description': audit.status_description,
        })

    except Exception as e:
        logger.exception("Error loading audit detail for audit id=%s", audit_id)
        messages.error(request, "Error loading audit details. Please try again.")
        return redirect('core:audit_list')


@login_required
def audit_progress(request: HttpRequest, audit_id: int):
    """Enhanced audit progress summary with optimized queries"""
    try:
        user = request.user
        audit_qs = Audit.objects.select_related('restaurant')
        if not (user.is_superuser or getattr(user, 'role', None) == 'admin'):
            audit_qs = audit_qs.filter(auditor_name=user)

        audit = get_object_or_404(audit_qs, id=audit_id)

        # Get sections with optimized queries
        sections = AuditSection.objects.filter(
            audit=audit
        ).select_related('section').prefetch_related(
            'auditquestionresponse_set'
        )

        progress_data = []
        total_questions = 0
        answered_questions = 0

        for section in sections:
            # Get questions for this section
            questions = Question.objects.filter(section=section.section)
            total_q = questions.count()
            total_questions += total_q

            # Get responses for this section
            responses = AuditQuestionResponse.objects.filter(
                audit_section=section
            )

            # Count answered questions (has score or comments)
            answered_q = sum(
                1 for r in responses
                if (r.scored_points and Decimal(r.scored_points) > Decimal('0.00'))
                or (r.comments and r.comments.strip())
            )
            answered_questions += answered_q

            section_percentage = (answered_q / total_q * 100) if total_q > 0 else 0

            progress_data.append({
                'section_id': section.section.id,
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
            'has_critical_failure': audit.has_critical_failure,
        })

    except Exception as e:
        logger.exception("Error calculating progress for audit id=%s", audit_id)
        return JsonResponse({
            'error': 'Internal server error'
        }, status=500)


class RestaurantAuditsView(LoginRequiredMixin, ListView):
    """Enhanced restaurant audits list with comprehensive statistics"""
    template_name = 'core/restaurant_audits.html'
    context_object_name = 'audits'
    paginate_by = 10

    def get_queryset(self):
        self.restaurant = get_object_or_404(Restaurant, pk=self.kwargs['restaurant_id'])
        qs = Audit.objects.filter(
            restaurant=self.restaurant
        ).select_related('auditor_name').order_by('-audit_date')

        if not (self.request.user.is_superuser or getattr(self.request.user, 'role', None) == 'admin'):
            qs = qs.filter(auditor_name=self.request.user)

        return qs

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        audits = self.get_queryset()

        # Comprehensive statistics
        audit_stats = audits.aggregate(
            total=Count('id'),
            avg_score=Avg('total_percentage'),
            submitted=Count('id', filter=Q(is_submitted=True)),
            critical_failures=Count('id', filter=Q(has_critical_failure=True)),
            grade_a=Count('id', filter=Q(grade='A')),
            grade_b=Count('id', filter=Q(grade='B')),
            grade_c=Count('id', filter=Q(grade='C')),
            grade_f=Count('id', filter=Q(grade='F')),
        )

        context.update({
            'restaurant': self.restaurant,
            'total_audits': audit_stats['total'],
            'avg_score': audit_stats['avg_score'] or 0,
            'latest_audit': audits.first(),
            'grade_a_count': audit_stats['grade_a'],
            'grade_b_count': audit_stats['grade_b'],
            'grade_c_count': audit_stats['grade_c'],
            'grade_f_count': audit_stats['grade_f'],
            'submitted_audits': audit_stats['submitted'],
            'critical_failure_audits': audit_stats['critical_failures'],
            'user_can_delete': self.request.user.is_superuser or getattr(self.request.user, 'role', None) == 'admin',
        })
        return context


class DeleteAuditView(LoginRequiredMixin, View):
    """Enhanced audit deletion with comprehensive checks"""

    def post(self, request: HttpRequest, audit_id: int):
        user = request.user
        qs = Audit.objects.select_related('restaurant')

        if not (user.is_superuser or getattr(user, 'role', None) == 'admin'):
            qs = qs.filter(auditor_name=user)

        audit = get_object_or_404(qs, id=audit_id)
        restaurant_id = audit.restaurant.id
        audit_name = f"{audit.restaurant.name} - {audit.audit_date}"

        try:
            with transaction.atomic():
                # Log deletion attempt
                logger.info(
                    "Attempting to delete audit by user %s: %s",
                    user.id,
                    audit_name
                )

                audit.delete()
                messages.success(
                    request,
                    f"Audit '{audit_name}' deleted successfully."
                )

                logger.info(
                    "Audit deleted successfully by user %s: %s",
                    user.id,
                    audit_name
                )

        except Exception as e:
            logger.exception("Error deleting audit id=%s", audit_id)
            messages.error(
                request,
                "Error deleting audit. Please try again."
            )

        return redirect('core:restaurant_audits', restaurant_id=restaurant_id)

    def get(self, request: HttpRequest, audit_id: int):
        messages.warning(request, "Deletion must be via POST request.")
        return redirect('core:dashboard')


@login_required
def reports_overview(request: HttpRequest):
    """Comprehensive reports overview with enhanced statistics"""
    try:
        user = request.user
        thirty_days_ago = timezone.now().date() - timedelta(days=30)

        # Base querysets with permissions
        if user.is_superuser or getattr(user, 'role', None) == 'admin':
            audit_qs = Audit.objects.filter(is_submitted=True)
            corrective_qs = CorrectiveAction.objects.all()
        else:
            audit_qs = Audit.objects.filter(is_submitted=True, auditor_name=user)
            corrective_qs = CorrectiveAction.objects.filter(audit__auditor_name=user)

        # Recent statistics
        recent_audits = audit_qs.filter(audit_date__gte=thirty_days_ago)
        total_audits = audit_qs.count()
        avg_score = audit_qs.aggregate(avg=Avg('total_percentage'))['avg'] or Decimal('0.00')

        # Grade distribution - ONLY ACTUAL DATA
        grade_distribution = []

        for grade in ['A', 'B', 'C', 'F']:
            if user.is_superuser or getattr(user, 'role', None) == 'admin':
                count = Audit.objects.filter(grade=grade, is_submitted=True).count()
                # Actual average of audits with this grade
                actual_avg_grade_score = Audit.objects.filter(
                    grade=grade,
                    is_submitted=True
                ).aggregate(avg=Avg('total_percentage'))['avg'] or Decimal('0.00')
            else:
                count = Audit.objects.filter(
                    grade=grade,
                    is_submitted=True,
                    auditor_name=user
                ).count()
                actual_avg_grade_score = Audit.objects.filter(
                    grade=grade,
                    is_submitted=True,
                    auditor_name=user
                ).aggregate(avg=Avg('total_percentage'))['avg'] or Decimal('0.00')

            if total_audits > 0:
                percentage = (count / total_audits) * 100
            else:
                percentage = 0

            grade_distribution.append({
                'grade': grade,
                'count': count,
                'percentage': round(percentage, 1),
                'avg_score': round(float(actual_avg_grade_score), 1),
            })

        # Critical failures
        critical_failures = audit_qs.filter(has_critical_failure=True).count()

        # Corrective actions
        overdue_actions = corrective_qs.filter(
            completed=False,
            deadline__lt=timezone.now().date()
        ).count()

        pending_actions = corrective_qs.filter(completed=False).count()
        completed_actions = corrective_qs.filter(completed=True).count()

        # Top performing restaurants - USER-SPECIFIC - FIXED ANNOTATION
        if user.is_superuser or getattr(user, 'role', None) == 'admin':
            restaurant_base_qs = Restaurant.objects.annotate(
                restaurant_audit_count=Count('audit', filter=Q(audit__is_submitted=True)),  # CHANGED
                avg_score=Avg('audit__total_percentage', filter=Q(audit__is_submitted=True)),
                last_audit_date=Max('audit__audit_date', filter=Q(audit__is_submitted=True))
            ).filter(restaurant_audit_count__gt=0)  # CHANGED
        else:
            restaurant_base_qs = Restaurant.objects.annotate(
                restaurant_audit_count=Count('audit', filter=Q(audit__is_submitted=True, audit__auditor_name=user)),  # CHANGED
                avg_score=Avg('audit__total_percentage', filter=Q(audit__is_submitted=True, audit__auditor_name=user)),
                last_audit_date=Max('audit__audit_date', filter=Q(audit__is_submitted=True, audit__auditor_name=user))
            ).filter(restaurant_audit_count__gt=0)  # CHANGED

        top_restaurants = restaurant_base_qs.order_by('-avg_score')[:10]

        # City performance - USER-SPECIFIC
        if user.is_superuser or getattr(user, 'role', None) == 'admin':
            city_performance = Audit.objects.filter(
                is_submitted=True
            ).values('restaurant__city').annotate(
                avg_score=Avg('total_percentage'),
                audit_count=Count('id'),
                restaurant_count=Count('restaurant', distinct=True),
                grade_a_count=Count('id', filter=Q(grade='A')),
                grade_b_count=Count('id', filter=Q(grade='B')),
                grade_c_count=Count('id', filter=Q(grade='C')),
                grade_f_count=Count('id', filter=Q(grade='F'))
            ).order_by('-avg_score')
        else:
            city_performance = Audit.objects.filter(
                is_submitted=True,
                auditor_name=user
            ).values('restaurant__city').annotate(
                avg_score=Avg('total_percentage'),
                audit_count=Count('id'),
                restaurant_count=Count('restaurant', distinct=True),
                grade_a_count=Count('id', filter=Q(grade='A')),
                grade_b_count=Count('id', filter=Q(grade='B')),
                grade_c_count=Count('id', filter=Q(grade='C')),
                grade_f_count=Count('id', filter=Q(grade='F'))
            ).order_by('-avg_score')

        # Format city performance data
        formatted_city_performance = []
        for city in city_performance:
            formatted_city_performance.append({
                'city': city['restaurant__city'],
                'avg_score': round(float(city['avg_score'] or 0), 1),
                'audit_count': city['audit_count'],
                'restaurant_count': city['restaurant_count'],
                'grade_a_count': city['grade_a_count'],
                'grade_b_count': city['grade_b_count'],
                'grade_c_count': city['grade_c_count'],
                'grade_f_count': city['grade_f_count'],
            })

        context = {
            'total_audits': total_audits,
            'recent_audits_count': recent_audits.count(),
            'avg_score': round(float(avg_score), 1),
            'grade_distribution': grade_distribution,
            'critical_failures': critical_failures,
            'overdue_actions': overdue_actions,
            'pending_actions': pending_actions,
            'completed_actions': completed_actions,
            'top_restaurants': top_restaurants,
            'city_performance': formatted_city_performance,
            'user_is_admin': user.is_superuser or getattr(user, 'role', None) == 'admin',
            'today': timezone.now().date(),
        }

        return render(request, 'core/reports_overview.html', context)

    except Exception as e:
        logger.exception("Error generating reports overview: %s", str(e))
        messages.error(request, "Error generating reports. Please try again.")
        return render(request, 'core/reports_overview.html', {'error': str(e)})

@login_required
def restaurant_performance_report(request: HttpRequest):
    """Enhanced restaurant performance comparison report"""
    try:
        user = request.user

        # First, get the base restaurant queryset
        if user.is_superuser or getattr(user, 'role', None) == 'admin':
            # Admin - all restaurants that have submitted audits
            restaurant_qs = Restaurant.objects.filter(
                audit__is_submitted=True
            ).distinct()
        else:
            # Regular user - only restaurants they have audited
            restaurant_qs = Restaurant.objects.filter(
                audit__is_submitted=True,
                audit__auditor_name=user
            ).distinct()

        # Now annotate with user-specific statistics - FIXED ANNOTATIONS
        if user.is_superuser or getattr(user, 'role', None) == 'admin':
            restaurant_qs = restaurant_qs.annotate(
                total_audits=Count('audit', filter=Q(audit__is_submitted=True)),  # CHANGED
                avg_score=Avg('audit__total_percentage', filter=Q(audit__is_submitted=True)),
                last_audit_date=Max('audit__audit_date', filter=Q(audit__is_submitted=True)),
                critical_failures=Count('audit', filter=Q(audit__has_critical_failure=True, audit__is_submitted=True)),
                grade_a_count=Count('audit', filter=Q(audit__grade='A', audit__is_submitted=True)),
                grade_b_count=Count('audit', filter=Q(audit__grade='B', audit__is_submitted=True)),
                grade_c_count=Count('audit', filter=Q(audit__grade='C', audit__is_submitted=True)),
                grade_f_count=Count('audit', filter=Q(audit__grade='F', audit__is_submitted=True)),
            )
        else:
            restaurant_qs = restaurant_qs.annotate(
                total_audits=Count('audit', filter=Q(audit__is_submitted=True, audit__auditor_name=user)),  # CHANGED
                avg_score=Avg('audit__total_percentage', filter=Q(audit__is_submitted=True, audit__auditor_name=user)),
                last_audit_date=Max('audit__audit_date', filter=Q(audit__is_submitted=True, audit__auditor_name=user)),
                critical_failures=Count('audit', filter=Q(audit__has_critical_failure=True, audit__is_submitted=True,
                                                          audit__auditor_name=user)),
                grade_a_count=Count('audit',
                                    filter=Q(audit__grade='A', audit__is_submitted=True, audit__auditor_name=user)),
                grade_b_count=Count('audit',
                                    filter=Q(audit__grade='B', audit__is_submitted=True, audit__auditor_name=user)),
                grade_c_count=Count('audit',
                                    filter=Q(audit__grade='C', audit__is_submitted=True, audit__auditor_name=user)),
                grade_f_count=Count('audit',
                                    filter=Q(audit__grade='F', audit__is_submitted=True, audit__auditor_name=user)),
            )

        # Sort options
        sort_by = request.GET.get('sort', '-avg_score')
        valid_sorts = ['-avg_score', 'avg_score', '-total_audits', 'total_audits', '-last_audit_date']
        if sort_by not in valid_sorts:
            sort_by = '-avg_score'

        restaurants = restaurant_qs.order_by(sort_by)

        # City-wise performance - SIMPLIFIED APPROACH
        city_performance = []
        if user.is_superuser or getattr(user, 'role', None) == 'admin':
            cities = Restaurant.objects.values_list('city', flat=True).distinct().order_by('city')
            for city in cities:
                # Get audits for this city
                city_audits = Audit.objects.filter(
                    restaurant__city=city,
                    is_submitted=True
                )
                if city_audits.exists():
                    city_stats = city_audits.aggregate(
                        avg_score=Avg('total_percentage'),
                        audit_count=Count('id'),
                        restaurant_count=Count('restaurant', distinct=True),
                        grade_a_count=Count('id', filter=Q(grade='A')),
                        grade_b_count=Count('id', filter=Q(grade='B')),
                        grade_c_count=Count('id', filter=Q(grade='C')),
                        grade_f_count=Count('id', filter=Q(grade='F'))
                    )

                    city_performance.append({
                        'city': city,
                        'avg_score': round(float(city_stats['avg_score'] or 0), 2),
                        'audit_count': city_stats['audit_count'] or 0,
                        'restaurant_count': city_stats['restaurant_count'] or 0,
                        'grade_a_count': city_stats['grade_a_count'] or 0,
                        'grade_b_count': city_stats['grade_b_count'] or 0,
                        'grade_c_count': city_stats['grade_c_count'] or 0,
                        'grade_f_count': city_stats['grade_f_count'] or 0,
                    })
        else:
            cities = Restaurant.objects.filter(
                audit__auditor_name=user
            ).values_list('city', flat=True).distinct().order_by('city')

            for city in cities:
                # Get user's audits for this city
                city_audits = Audit.objects.filter(
                    restaurant__city=city,
                    is_submitted=True,
                    auditor_name=user
                )
                if city_audits.exists():
                    city_stats = city_audits.aggregate(
                        avg_score=Avg('total_percentage'),
                        audit_count=Count('id'),
                        restaurant_count=Count('restaurant', distinct=True),
                        grade_a_count=Count('id', filter=Q(grade='A')),
                        grade_b_count=Count('id', filter=Q(grade='B')),
                        grade_c_count=Count('id', filter=Q(grade='C')),
                        grade_f_count=Count('id', filter=Q(grade='F'))
                    )

                    city_performance.append({
                        'city': city,
                        'avg_score': round(float(city_stats['avg_score'] or 0), 2),
                        'audit_count': city_stats['audit_count'] or 0,
                        'restaurant_count': city_stats['restaurant_count'] or 0,
                        'grade_a_count': city_stats['grade_a_count'] or 0,
                        'grade_b_count': city_stats['grade_b_count'] or 0,
                        'grade_c_count': city_stats['grade_c_count'] or 0,
                        'grade_f_count': city_stats['grade_f_count'] or 0,
                    })

        # Sort city performance by average score
        city_performance.sort(key=lambda x: x['avg_score'], reverse=True)

        context = {
            'restaurants': restaurants,
            'city_performance': city_performance,
            'current_sort': sort_by,
            'total_restaurants': restaurants.count(),
            'user_is_admin': user.is_superuser or getattr(user, 'role', None) == 'admin',
        }

        return render(request, 'core/restaurant_performance_report.html', context)

    except Exception as e:
        logger.exception("Error generating restaurant performance report: %s", str(e))
        messages.error(request, "Error generating performance report. Please try again.")
        return render(request, 'core/restaurant_performance_report.html', {'error': str(e)})

@login_required
def corrective_action_list(request: HttpRequest):
    """List and manage corrective actions"""
    try:
        user = request.user

        # Base queryset with proper related fields
        corrective_actions = CorrectiveAction.objects.select_related(
            'audit',
            'audit__restaurant',
            'question_response',
            'question_response__question'
        ).all()

        # Apply user filtering
        if not (user.is_superuser or getattr(user, 'role', None) == 'admin'):
            corrective_actions = corrective_actions.filter(audit__auditor_name=user)

        # Filtering
        risk_level = request.GET.get('risk_level')
        if risk_level:
            corrective_actions = corrective_actions.filter(risk_level=risk_level)

        completed = request.GET.get('completed')
        if completed == 'true':
            corrective_actions = corrective_actions.filter(completed=True)
        elif completed == 'false':
            corrective_actions = corrective_actions.filter(completed=False)

        overdue = request.GET.get('overdue')
        if overdue == 'true':
            corrective_actions = corrective_actions.filter(
                completed=False,
                deadline__lt=timezone.now().date()
            )

        # Statistics - Use multiple queries instead of complex aggregates
        base_stats_qs = CorrectiveAction.objects.all()

        # Apply user filtering to stats queryset
        if not (user.is_superuser or getattr(user, 'role', None) == 'admin'):
            base_stats_qs = base_stats_qs.filter(audit__auditor_name=user)

        # Apply the same filters to stats
        if risk_level:
            base_stats_qs = base_stats_qs.filter(risk_level=risk_level)

        if completed == 'true':
            base_stats_qs = base_stats_qs.filter(completed=True)
        elif completed == 'false':
            base_stats_qs = base_stats_qs.filter(completed=False)

        if overdue == 'true':
            base_stats_qs = base_stats_qs.filter(
                completed=False,
                deadline__lt=timezone.now().date()
            )

        # Calculate statistics using separate queries
        stats = {
            'total': base_stats_qs.count(),
            'completed': base_stats_qs.filter(completed=True).count(),
            'overdue': base_stats_qs.filter(completed=False, deadline__lt=timezone.now().date()).count(),
            'critical': base_stats_qs.filter(risk_level='CRITICAL').count(),
            'high': base_stats_qs.filter(risk_level='HIGH').count(),
            'medium': base_stats_qs.filter(risk_level='MEDIUM').count(),
            'low': base_stats_qs.filter(risk_level='LOW').count(),
            'pending': base_stats_qs.filter(completed=False).count(),
        }

        # Calculate completion percentage
        if stats['total'] > 0:
            completion_percentage = (stats['completed'] / stats['total']) * 100
        else:
            completion_percentage = 0

        context = {
            'corrective_actions': corrective_actions.order_by('-created_at'),
            'stats': stats,
            'completion_percentage': round(completion_percentage, 1),
            'risk_level_filter': risk_level,
            'completed_filter': completed,
            'overdue_filter': overdue,
            'user_is_admin': user.is_superuser or getattr(user, 'role', None) == 'admin',
            'today': timezone.now().date(),
            'risk_levels': ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'],
        }

        return render(request, 'corrective_actions/actions_list.html', context)

    except Exception as e:
        logger.exception("Error loading corrective actions for user %s: %s", request.user.id, str(e))
        messages.error(request, "Error loading corrective actions. Please try again.")
        return render(request, 'corrective_actions/actions_list.html', {
            'corrective_actions': [],
            'stats': {
                'total': 0,
                'completed': 0,
                'overdue': 0,
                'critical': 0,
                'high': 0,
                'medium': 0,
                'low': 0,
                'pending': 0,
            },
            'completion_percentage': 0,
            'risk_level_filter': None,
            'completed_filter': None,
            'overdue_filter': None,
            'user_is_admin': False,
            'today': timezone.now().date(),
            'risk_levels': ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'],
        })


class CorrectiveActionDetailView(LoginRequiredMixin, DetailView):
    """View corrective action details"""
    model = CorrectiveAction
    template_name = 'corrective_actions/action_detail.html'
    context_object_name = 'action'

    def get_queryset(self):
        user = self.request.user
        qs = CorrectiveAction.objects.select_related(
            'audit',
            'audit__restaurant',
            'question_response',
            'question_response__question'
        )

        if not (user.is_superuser or getattr(user, 'role', None) == 'admin'):
            qs = qs.filter(audit__auditor_name=user)

        return qs

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context['today'] = timezone.now().date()
        context['user_is_admin'] = self.request.user.is_superuser or getattr(self.request.user, 'role', None) == 'admin'
        return context


@login_required
def create_corrective_action(request: HttpRequest, response_id: int):
    """Create a new corrective action from question response"""
    try:
        user = request.user

        # Get the question response
        response_qs = AuditQuestionResponse.objects.select_related(
            'audit_section__audit',
            'question'
        )

        if not (user.is_superuser or getattr(user, 'role', None) == 'admin'):
            response_qs = response_qs.filter(audit_section__audit__auditor_name=user)

        question_response = get_object_or_404(response_qs, id=response_id)

        if request.method == 'POST':
            try:
                with transaction.atomic():
                    corrective_action = CorrectiveAction.objects.create(
                        audit=question_response.audit_section.audit,
                        question_response=question_response,
                        description=request.POST.get('description', ''),
                        risk_level=request.POST.get('risk_level', 'MEDIUM'),
                        assigned_to=request.POST.get('assigned_to', ''),
                        deadline=request.POST.get('deadline'),
                        comments=request.POST.get('comments', '')
                    )

                    # Update the question response to mark it as needing corrective action
                    question_response.needs_corrective_action = True
                    question_response.save()

                    messages.success(request, 'Corrective action created successfully!')
                    return redirect('corrective_actions:action_detail', pk=corrective_action.id)

            except Exception as e:
                logger.exception("Error creating corrective action: %s", str(e))
                messages.error(request, 'Error creating corrective action. Please try again.')

        context = {
            'question_response': question_response,
            'risk_levels': CorrectiveAction.RISK_LEVELS,
            'today': timezone.now().date(),
        }

        return render(request, 'corrective_actions/action_create.html', context)

    except Exception as e:
        logger.exception("Error loading corrective action creation form: %s", str(e))
        messages.error(request, 'Error loading form. Please try again.')
        return redirect('core:dashboard')


class CorrectiveActionUpdateView(LoginRequiredMixin, UpdateView):
    """Update corrective action"""
    model = CorrectiveAction
    template_name = 'corrective_actions/action_update.html'
    fields = ['description', 'risk_level', 'assigned_to', 'deadline', 'completed', 'comments']
    success_url = reverse_lazy('core:action_list')

    def get_queryset(self):
        user = self.request.user
        qs = CorrectiveAction.objects.select_related('audit')

        if not (user.is_superuser or getattr(user, 'role', None) == 'admin'):
            qs = qs.filter(audit__auditor_name=user)

        return qs

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context['risk_levels'] = CorrectiveAction.RISK_LEVELS
        context['today'] = timezone.now().date()
        return context

    def form_valid(self, form):
        # Set completion date if marked as completed
        if form.cleaned_data['completed'] and not self.object.completion_date:
            form.instance.completion_date = timezone.now().date()

        # Clear completion date if marked as not completed
        if not form.cleaned_data['completed'] and self.object.completion_date:
            form.instance.completion_date = None

        messages.success(self.request, 'Corrective action updated successfully!')
        return super().form_valid(form)


class CorrectiveActionDeleteView(LoginRequiredMixin, DeleteView):
    """Delete corrective action"""
    model = CorrectiveAction
    template_name = 'corrective_actions/action_confirm_delete.html'
    success_url = reverse_lazy('core:action_list')

    def get_queryset(self):
        user = self.request.user
        qs = CorrectiveAction.objects.select_related('audit')

        if not (user.is_superuser or getattr(user, 'role', None) == 'admin'):
            qs = qs.filter(audit__auditor_name=user)

        return qs

    def delete(self, request: HttpRequest, *args: Any, **kwargs: Any):
        messages.success(self.request, 'Corrective action deleted successfully!')
        return super().delete(request, *args, **kwargs)


@login_required
@require_http_methods(["POST"])
def mark_action_completed(request: HttpRequest, pk: int):
    """Mark corrective action as completed via AJAX"""
    try:
        user = request.user
        qs = CorrectiveAction.objects.select_related('audit')

        if not (user.is_superuser or getattr(user, 'role', None) == 'admin'):
            qs = qs.filter(audit__auditor_name=user)

        corrective_action = get_object_or_404(qs, id=pk)

        with transaction.atomic():
            corrective_action.completed = True
            corrective_action.completion_date = timezone.now().date()
            corrective_action.save()

        return JsonResponse({
            'success': True,
            'message': 'Corrective action marked as completed!',
            'completion_date': corrective_action.completion_date.strftime('%Y-%m-%d')
        })

    except Exception as e:
        logger.exception("Error marking corrective action as completed: %s", str(e))
        return JsonResponse({
            'success': False,
            'message': 'Error updating corrective action.'
        }, status=500)


@login_required
def corrective_action_dashboard(request: HttpRequest):
    """Corrective actions dashboard with overview"""
    try:
        user = request.user

        # Base queryset
        if user.is_superuser or getattr(user, 'role', None) == 'admin':
            actions_qs = CorrectiveAction.objects.all()
        else:
            actions_qs = CorrectiveAction.objects.filter(audit__auditor_name=user)

        # Overall statistics
        total_actions = actions_qs.count()
        completed_actions = actions_qs.filter(completed=True).count()
        overdue_actions = actions_qs.filter(completed=False, deadline__lt=timezone.now().date()).count()
        pending_actions = actions_qs.filter(completed=False).count()

        # Risk level distribution
        risk_distribution = []
        for risk_level, display_name in CorrectiveAction.RISK_LEVELS:
            count = actions_qs.filter(risk_level=risk_level).count()
            risk_distribution.append({
                'level': risk_level,
                'display_name': display_name,
                'count': count,
                'percentage': (count / total_actions * 100) if total_actions > 0 else 0
            })

        # Recent actions
        recent_actions = actions_qs.select_related(
            'audit', 'audit__restaurant'
        ).order_by('-created_at')[:10]

        # Upcoming deadlines (next 7 days)
        upcoming_deadline = timezone.now().date() + timedelta(days=7)
        upcoming_actions = actions_qs.filter(
            completed=False,
            deadline__gte=timezone.now().date(),
            deadline__lte=upcoming_deadline
        ).select_related('audit', 'audit__restaurant').order_by('deadline')[:10]

        context = {
            'total_actions': total_actions,
            'completed_actions': completed_actions,
            'overdue_actions': overdue_actions,
            'pending_actions': pending_actions,
            'completion_rate': (completed_actions / total_actions * 100) if total_actions > 0 else 0,
            'risk_distribution': risk_distribution,
            'recent_actions': recent_actions,
            'upcoming_actions': upcoming_actions,
            'today': timezone.now().date(),
            'user_is_admin': user.is_superuser or getattr(user, 'role', None) == 'admin',
        }

        return render(request, 'corrective_actions/dashboard.html', context)

    except Exception as e:
        logger.exception("Error loading corrective actions dashboard: %s", str(e))
        messages.error(request, 'Error loading dashboard. Please try again.')
        return render(request, 'corrective_actions/dashboard.html', {
            'total_actions': 0,
            'completed_actions': 0,
            'overdue_actions': 0,
            'pending_actions': 0,
            'completion_rate': 0,
            'risk_distribution': [],
            'recent_actions': [],
            'upcoming_actions': [],
            'today': timezone.now().date(),
            'user_is_admin': False,
        })


@login_required
def export_audits_csv(request: HttpRequest):
    """Export audits to CSV"""
    try:
        user = request.user
        audits = Audit.objects.select_related('restaurant', 'auditor_name').filter(is_submitted=True)

        if not (user.is_superuser or getattr(user, 'role', None) == 'admin'):
            audits = audits.filter(auditor_name=user)

        response = HttpResponse(
            content_type='text/csv',
            headers={'Content-Disposition': 'attachment; filename="audits_export.csv"'},
        )

        writer = csv.writer(response)
        writer.writerow([
            'Restaurant', 'Code', 'Audit Date', 'Auditor', 'Manager',
            'Total Score', 'Total Possible', 'Percentage', 'Grade',
            'Critical Failure', 'Submitted', 'Submitted At'
        ])

        for audit in audits:
            writer.writerow([
                audit.restaurant.name,
                audit.restaurant.code,
                audit.audit_date,
                audit.auditor_name.get_full_name() or audit.auditor_name.username,
                audit.manager_on_duty,
                audit.total_scored,
                audit.total_possible,
                audit.total_percentage,
                audit.grade,
                'Yes' if audit.has_critical_failure else 'No',
                'Yes' if audit.is_submitted else 'No',
                audit.submitted_at.strftime('%Y-%m-%d %H:%M:%S') if audit.submitted_at else ''
            ])

        return response

    except Exception as e:
        logger.exception("Error exporting audits to CSV: %s", str(e))
        messages.error(request, "Error exporting data. Please try again.")
        return redirect('core:audit_list')


# API Views for AJAX endpoints

@login_required
@require_http_methods(["GET"])
def api_audit_statistics(request: HttpRequest):
    """API endpoint for audit statistics"""
    try:
        user = request.user
        thirty_days_ago = timezone.now().date() - timedelta(days=30)

        audit_qs = Audit.objects.filter(is_submitted=True)
        if not (user.is_superuser or getattr(user, 'role', None) == 'admin'):
            audit_qs = audit_qs.filter(auditor_name=user)

        stats = audit_qs.aggregate(
            total_audits=Count('id'),
            avg_score=Avg('total_percentage'),
            recent_audits=Count('id', filter=Q(audit_date__gte=thirty_days_ago)),
            critical_failures=Count('id', filter=Q(has_critical_failure=True)),
        )

        return JsonResponse({
            'success': True,
            'data': {
                'total_audits': stats['total_audits'],
                'avg_score': float(stats['avg_score']) if stats['avg_score'] else 0,
                'recent_audits': stats['recent_audits'],
                'critical_failures': stats['critical_failures'],
            }
        })

    except Exception as e:
        logger.exception("Error generating API statistics: %s", str(e))
        return JsonResponse({
            'success': False,
            'error': 'Internal server error'
        }, status=500)


@login_required
@require_http_methods(["GET"])
def api_restaurant_list(request: HttpRequest):
    """API endpoint for restaurant list"""
    try:
        user = request.user
        restaurants = Restaurant.objects.annotate(
            restaurant_audit_count=Count('audit', filter=Q(audit__is_submitted=True)),  # CHANGED
            avg_score=Avg('audit__total_percentage', filter=Q(audit__is_submitted=True)),
            last_audit=Max('audit__audit_date', filter=Q(audit__is_submitted=True))
        ).order_by('name')

        if not (user.is_superuser or getattr(user, 'role', None) == 'admin'):
            restaurants = restaurants.filter(audit__auditor_name=user).distinct()

        restaurant_data = []
        for restaurant in restaurants:
            restaurant_data.append({
                'id': restaurant.id,
                'name': restaurant.name,
                'code': restaurant.code,
                'city': restaurant.city,
                'audit_count': restaurant.restaurant_audit_count,  # CHANGED
                'avg_score': float(restaurant.avg_score) if restaurant.avg_score else 0,
                'last_audit': restaurant.last_audit.isoformat() if restaurant.last_audit else None
            })

        return JsonResponse({
            'success': True,
            'data': restaurant_data
        })

    except Exception as e:
        logger.exception("Error generating restaurant list API: %s", str(e))
        return JsonResponse({
            'success': False,
            'error': 'Internal server error'
        }, status=500)

class RestaurantListView(LoginRequiredMixin, ListView):
    """Enhanced restaurant list view for navbar"""
    model = Restaurant
    template_name = 'core/restaurant_list.html'
    context_object_name = 'restaurants'
    paginate_by = 20

    def get_queryset(self):
        user = self.request.user

        # Base queryset
        qs = Restaurant.objects.all()

        # For non-admin users, only show restaurants they have audited
        if not (user.is_superuser or getattr(user, 'role', None) == 'admin'):
            qs = qs.filter(audit__auditor_name=user).distinct()

        # Now add user-specific annotations - USE DIFFERENT FIELD NAMES
        if user.is_superuser or getattr(user, 'role', None) == 'admin':
            # Admin sees all submitted audits
            qs = qs.annotate(
                total_audits=Count('audit', filter=Q(audit__is_submitted=True)),
                avg_score=Avg('audit__total_percentage', filter=Q(audit__is_submitted=True)),
                latest_audit_date=Max('audit__audit_date', filter=Q(audit__is_submitted=True)),
                critical_audits_count=Count('audit', filter=Q(audit__has_critical_failure=True, audit__is_submitted=True)),
                grade_a_count=Count('audit', filter=Q(audit__grade='A', audit__is_submitted=True)),
                grade_b_count=Count('audit', filter=Q(audit__grade='B', audit__is_submitted=True)),
                grade_c_count=Count('audit', filter=Q(audit__grade='C', audit__is_submitted=True)),
                grade_f_count=Count('audit', filter=Q(audit__grade='F', audit__is_submitted=True))
            )
        else:
            # Regular user sees only their own submitted audits
            qs = qs.annotate(
                total_audits=Count('audit', filter=Q(audit__is_submitted=True, audit__auditor_name=user)),
                avg_score=Avg('audit__total_percentage', filter=Q(audit__is_submitted=True, audit__auditor_name=user)),
                latest_audit_date=Max('audit__audit_date',
                                      filter=Q(audit__is_submitted=True, audit__auditor_name=user)),
                critical_audits_count=Count('audit', filter=Q(audit__has_critical_failure=True, audit__is_submitted=True,
                                                        audit__auditor_name=user)),
                grade_a_count=Count('audit',
                                    filter=Q(audit__grade='A', audit__is_submitted=True, audit__auditor_name=user)),
                grade_b_count=Count('audit',
                                    filter=Q(audit__grade='B', audit__is_submitted=True, audit__auditor_name=user)),
                grade_c_count=Count('audit',
                                    filter=Q(audit__grade='C', audit__is_submitted=True, audit__auditor_name=user)),
                grade_f_count=Count('audit',
                                    filter=Q(audit__grade='F', audit__is_submitted=True, audit__auditor_name=user))
            )

        return qs.order_by('name')

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Get unique cities for filter
        if user.is_superuser or getattr(user, 'role', None) == 'admin':
            cities = Restaurant.objects.values_list('city', flat=True).distinct().order_by('city')
        else:
            cities = Restaurant.objects.filter(
                audit__auditor_name=user
            ).values_list('city', flat=True).distinct().order_by('city')

        context['cities'] = cities

        # Get major cities with USER-SPECIFIC audit statistics
        major_cities_data = []
        for city in cities:
            if user.is_superuser or getattr(user, 'role', None) == 'admin':
                # Admin - all restaurants in city
                restaurant_count = Restaurant.objects.filter(city=city).count()

                # All audits in this city
                city_audit_stats = Audit.objects.filter(
                    restaurant__city=city,
                    is_submitted=True
                ).aggregate(
                    total_audits=Count('id'),
                    avg_score=Avg('total_percentage'),
                    critical_audits=Count('id', filter=Q(has_critical_failure=True)),
                    grade_a_count=Count('id', filter=Q(grade='A')),
                    grade_b_count=Count('id', filter=Q(grade='B')),
                    grade_c_count=Count('id', filter=Q(grade='C')),
                    grade_f_count=Count('id', filter=Q(grade='F'))
                )
            else:
                # Regular user - only their restaurants in city
                restaurant_count = Restaurant.objects.filter(
                    city=city,
                    audit__auditor_name=user
                ).distinct().count()

                # Only user's audits in this city
                city_audit_stats = Audit.objects.filter(
                    restaurant__city=city,
                    is_submitted=True,
                    auditor_name=user
                ).aggregate(
                    total_audits=Count('id'),
                    avg_score=Avg('total_percentage'),
                    critical_audits=Count('id', filter=Q(has_critical_failure=True)),
                    grade_a_count=Count('id', filter=Q(grade='A')),
                    grade_b_count=Count('id', filter=Q(grade='B')),
                    grade_c_count=Count('id', filter=Q(grade='C')),
                    grade_f_count=Count('id', filter=Q(grade='F'))
                )

            major_cities_data.append({
                'name': city,
                'restaurant_count': restaurant_count,
                'total_audits': city_audit_stats['total_audits'] or 0,
                'avg_score': round(float(city_audit_stats['avg_score'] or 0), 2),
                'critical_audits': city_audit_stats['critical_audits'] or 0,
                'grade_a_count': city_audit_stats['grade_a_count'] or 0,
                'grade_b_count': city_audit_stats['grade_b_count'] or 0,
                'grade_c_count': city_audit_stats['grade_c_count'] or 0,
                'grade_f_count': city_audit_stats['grade_f_count'] or 0,
            })

        context['major_cities'] = major_cities_data

        # Add comprehensive statistics (USER-SPECIFIC)
        restaurants_qs = self.get_queryset()
        context['total_restaurants'] = restaurants_qs.count()

        # User-specific audit statistics
        if user.is_superuser or getattr(user, 'role', None) == 'admin':
            audit_qs = Audit.objects.filter(is_submitted=True)
        else:
            audit_qs = Audit.objects.filter(is_submitted=True, auditor_name=user)

        context['total_audits'] = audit_qs.count()

        # Calculate overall statistics (USER-SPECIFIC)
        overall_stats = audit_qs.aggregate(
            avg_score=Avg('total_percentage'),
            critical_count=Count('id', filter=Q(has_critical_failure=True)),
            grade_a_count=Count('id', filter=Q(grade='A')),
            grade_b_count=Count('id', filter=Q(grade='B')),
            grade_c_count=Count('id', filter=Q(grade='C')),
            grade_f_count=Count('id', filter=Q(grade='F'))
        )

        context['overall_avg_score'] = round(float(overall_stats['avg_score'] or 0), 2)
        context['critical_audits_count'] = overall_stats['critical_count'] or 0
        context['grade_a_count'] = overall_stats['grade_a_count'] or 0
        context['grade_b_count'] = overall_stats['grade_b_count'] or 0
        context['grade_c_count'] = overall_stats['grade_c_count'] or 0
        context['grade_f_count'] = overall_stats['grade_f_count'] or 0

        # Add user-specific context
        context['user_is_admin'] = user.is_superuser or getattr(user, 'role', None) == 'admin'

        # Add performance metrics
        if restaurants_qs.exists():
            # Use the annotated field name instead of the property
            context['restaurants_with_audits'] = restaurants_qs.filter(total_audits__gt=0).count()
            context['restaurants_without_audits'] = restaurants_qs.filter(total_audits=0).count()

            # Top performing restaurants (by average score) - USER FILTERED
            top_performers = restaurants_qs.filter(
                total_audits__gt=0,
                avg_score__isnull=False
            ).order_by('-avg_score')[:5]
            context['top_performers'] = top_performers

            # Restaurants needing attention (no audits or low scores) - USER FILTERED
            attention_needed = restaurants_qs.filter(
                Q(total_audits=0) | Q(avg_score__lt=80)
            ).order_by('avg_score')[:5]
            context['attention_needed'] = attention_needed

        return context