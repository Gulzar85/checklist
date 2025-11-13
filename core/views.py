from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Avg
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import ListView, TemplateView, View, DetailView

from .models import Restaurant, Audit, Section, Question, AuditSection, AuditQuestionResponse


def audit_results(request, audit_id):
    """Display audit results"""
    audit = get_object_or_404(Audit, id=audit_id)
    sections = AuditSection.objects.filter(audit=audit).select_related('section')

    # Get all responses for detailed view
    responses = AuditQuestionResponse.objects.filter(
        audit_section__audit=audit
    ).select_related('question', 'audit_section__section')

    context = {
        'audit': audit,
        'sections': sections,
        'responses': responses,
    }
    return render(request, 'core/audit_results.html', context)


class AuditDashboardView(LoginRequiredMixin, TemplateView):
    """Main dashboard - Login Required"""
    template_name = 'core/dashboard.html'
    login_url = '/accounts/login/'
    redirect_field_name = 'next'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Filter audits by current user if not admin/superuser
        if self.request.user.is_superuser or self.request.user.role == 'admin':
            recent_audits = Audit.objects.all().order_by('-audit_date')[:10]
            total_audits = Audit.objects.count()
            if total_audits > 0:
                avg_score = Audit.objects.aggregate(avg=Avg('total_percentage'))['avg'] or 0
            else:
                avg_score = 0
        else:
            recent_audits = Audit.objects.filter(auditor_name=self.request.user).order_by('-audit_date')[:10]
            total_audits = recent_audits.count()
            if total_audits > 0:
                avg_score = Audit.objects.filter(auditor_name=self.request.user).aggregate(
                    avg=Avg('total_percentage')
                )['avg'] or 0
            else:
                avg_score = 0

        restaurants = Restaurant.objects.all()

        context.update({
            'recent_audits': recent_audits,
            'restaurants': restaurants,
            'total_audits': total_audits,
            'avg_score': avg_score,
        })
        return context

@login_required
def create_audit(request):
    """Create new audit"""
    if request.method == 'POST':
        restaurant_id = request.POST.get('restaurant')
        audit_date = request.POST.get('audit_date')
        manager_name = request.POST.get('manager_name')
        # auditor_name = request.POST.get('auditor_name')

        restaurant = get_object_or_404(Restaurant, id=restaurant_id)

        audit = Audit.objects.create(
            restaurant=restaurant,
            audit_date=audit_date,
            manager_on_duty=manager_name,
            auditor_name=request.user
        )

        return redirect('core:audit_form', audit_id=audit.id)

    restaurants = Restaurant.objects.all()
    context = {
        'restaurants': restaurants,
        'today': timezone.now().date()
    }
    return render(request, 'core/create_audit.html', context)


class AuditListView(LoginRequiredMixin, ListView):
    """List all audits with user filtering - Login Required"""
    model = Audit
    template_name = 'core/audit_list.html'
    context_object_name = 'audits'
    paginate_by = 20
    ordering = ['-audit_date']
    login_url = '/accounts/login/'
    redirect_field_name = 'next'

    def get_queryset(self):
        queryset = super().get_queryset()

        # Filter by restaurant if provided
        restaurant_id = self.request.GET.get('restaurant')
        if restaurant_id:
            queryset = queryset.filter(restaurant_id=restaurant_id)

        # Filter by current user if not admin/superuser
        if not (self.request.user.is_superuser or self.request.user.role == 'admin'):
            queryset = queryset.filter(auditor_name=self.request.user)

        return queryset.select_related('restaurant', 'auditor_name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['restaurants'] = Restaurant.objects.all()

        # Add filter information
        restaurant_id = self.request.GET.get('restaurant')
        if restaurant_id:
            context['selected_restaurant'] = get_object_or_404(Restaurant, id=restaurant_id)

        return context

@login_required
def audit_form(request, audit_id):
    """Main audit form with section-wise questions"""
    audit = get_object_or_404(Audit, id=audit_id)
    sections = Section.objects.all().order_by('id')

    # Prepare section data with questions and responses
    section_data = []
    for section in sections:
        questions = section.question_set.all().order_by('order')
        section_questions = []

        for question in questions:
            # Get existing response if available
            try:
                response = AuditQuestionResponse.objects.get(
                    audit_section__audit=audit,
                    audit_section__section=section,
                    question=question
                )
                scored_points = float(response.scored_points)
                comments = response.comments
                needs_corrective_action = response.needs_corrective_action
            except AuditQuestionResponse.DoesNotExist:
                scored_points = 0
                comments = ''
                needs_corrective_action = False

            section_questions.append({
                'id': question.id,
                'text': question.question_text,
                'possible_points': float(question.possible_points),
                'is_critical': question.is_critical,
                'scored_points': scored_points,
                'comments': comments,
                'needs_corrective_action': needs_corrective_action
            })

        section_data.append({
            'section': section,
            'questions': section_questions
        })

    context = {
        'audit': audit,
        'section_data': section_data,
    }
    return render(request, 'core/audit_form.html', context)


@csrf_exempt
@login_required
def save_response(request):
    """Save question response via AJAX"""
    if request.method == 'POST':
        try:
            audit_id = request.POST.get('audit_id')
            section_id = request.POST.get('section_id')
            question_id = request.POST.get('question_id')
            scored_points = request.POST.get('scored_points', '0')
            comments = request.POST.get('comments', '')

            # Validate user access to audit
            if request.user.is_superuser or request.user.role == 'admin':
                audit = get_object_or_404(Audit, id=audit_id)
            else:
                audit = get_object_or_404(Audit, id=audit_id, auditor_name=request.user)

            # Convert to float, handle empty values
            try:
                scored_points = float(scored_points) if scored_points else 0.0
            except (ValueError, TypeError):
                scored_points = 0.0

            section = get_object_or_404(Section, id=section_id)
            question = get_object_or_404(Question, id=question_id)

            # Get or create audit section
            audit_section, created = AuditSection.objects.get_or_create(
                audit=audit,
                section=section
            )

            # Get or create response
            response, created = AuditQuestionResponse.objects.get_or_create(
                audit_section=audit_section,
                question=question,
                defaults={
                    'scored_points': scored_points,
                    'comments': comments
                }
            )

            if not created:
                response.scored_points = scored_points
                response.comments = comments
                response.save()

            # Calculate if corrective action is needed
            if question.is_critical and scored_points == 0:
                response.needs_corrective_action = True
            else:
                response.needs_corrective_action = False
            response.save()

            # MANUAL CALCULATION (Signals alternative)
            # Calculate section score
            audit_section.calculate_section_score()

            # Calculate audit totals with completion check
            audit.calculate_totals()

            return JsonResponse({
                'success': True,
                'message': 'Response saved successfully',
                'section_score': float(audit_section.scored_points),
                'section_percentage': float(audit_section.section_percentage),
                'total_score': float(audit.total_scored),
                'total_percentage': float(audit.total_percentage),
                'grade': audit.grade,
                'is_submitted': audit.is_submitted,
                'audit_status': audit.status,
                'progress_percentage': audit.get_progress_percentage()  # Add progress percentage
            })

        except Exception as e:
            import traceback
            print(f"Error in save_response: {str(e)}")
            print(traceback.format_exc())
            return JsonResponse({
                'success': False,
                'message': f'Error saving response: {str(e)}'
            })

    return JsonResponse({'success': False, 'message': 'Invalid request'})

@login_required
def submit_audit(request, audit_id):
    """Final submission of audit"""
    if request.method == 'POST':
        audit = get_object_or_404(Audit, id=audit_id)

        # Add any final validation here
        audit.save()  # This will trigger score calculations

        return JsonResponse({
            'success': True,
            'message': 'Audit submitted successfully',
            'total_score': float(audit.total_scored),
            'total_percentage': float(audit.total_percentage),
            'grade': audit.grade
        })

    return JsonResponse({'success': False, 'message': 'Invalid request'})

@login_required
def audit_progress(request, audit_id):
    """Get audit progress data"""
    audit = get_object_or_404(Audit, id=audit_id)
    sections = AuditSection.objects.filter(audit=audit).select_related('section')

    progress_data = []
    for section in sections:
        total_questions = Question.objects.filter(section=section.section).count()
        answered_questions = AuditQuestionResponse.objects.filter(
            audit_section=section
        ).count()

        progress_data.append({
            'section_name': section.section.name,
            'answered': answered_questions,
            'total': total_questions,
            'percentage': (answered_questions / total_questions * 100) if total_questions > 0 else 0,
            'section_score': float(section.scored_points),
            'section_percentage': float(section.section_percentage)
        })

    return JsonResponse({'progress': progress_data})


class RestaurantAuditsView(LoginRequiredMixin, ListView):
    """Restaurant audits view - Login Required"""
    template_name = 'core/restaurant_audits.html'
    context_object_name = 'audits'
    paginate_by = 10
    login_url = '/accounts/login/'
    redirect_field_name = 'next'

    def get_queryset(self):
        self.restaurant = get_object_or_404(Restaurant, pk=self.kwargs['restaurant_id'])

        # Filter audits by current user if not admin/superuser
        if self.request.user.is_superuser or self.request.user.role == 'admin':
            return Audit.objects.filter(restaurant=self.restaurant).select_related('auditor_name').order_by(
                '-audit_date')
        else:
            return Audit.objects.filter(
                restaurant=self.restaurant,
                auditor_name=self.request.user
            ).select_related('auditor_name').order_by('-audit_date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['restaurant'] = self.restaurant

        # Add statistics
        audits = self.get_queryset()
        context['total_audits'] = audits.count()
        if audits.exists():
            context['avg_score'] = audits.aggregate(avg=Avg('total_percentage'))['avg']
            context['latest_audit'] = audits.first()
            context['grade_a_count'] = audits.filter(grade='A').count()
        else:
            context['avg_score'] = 0
            context['latest_audit'] = None
            context['grade_a_count'] = 0

        # Add user permissions for template
        context['user_can_delete'] = self.request.user.is_superuser or self.request.user.role == 'admin'

        return context


class DeleteAuditView(LoginRequiredMixin, View):
    """Delete audit - Login Required"""
    login_url = '/accounts/login/'
    redirect_field_name = 'next'

    def post(self, request, audit_id):
        # Validate user access to audit
        if request.user.is_superuser or request.user.role == 'admin':
            audit = get_object_or_404(Audit, id=audit_id)
        else:
            audit = get_object_or_404(Audit, id=audit_id, auditor_name=request.user)

        restaurant_id = audit.restaurant.id
        audit_name = f"{audit.restaurant.name} - {audit.audit_date}"

        # Delete the audit
        audit.delete()

        messages.success(request, f"Audit '{audit_name}' has been deleted successfully.")

        # Redirect back to restaurant audits page
        return redirect('core:restaurant_audits', restaurant_id=restaurant_id)

    def get(self, request, audit_id):
        # For safety, only allow POST requests for deletion
        return redirect('core:dashboard')

