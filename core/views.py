from django.contrib.auth.decorators import login_required
from django.db import models
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from .models import Audit, Restaurant, Section, Question, AuditSection, AuditQuestionResponse


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

@login_required
def audit_dashboard(request):
    """Main dashboard"""
    recent_audits = Audit.objects.all().order_by('-audit_date')[:10]
    restaurants = Restaurant.objects.all()

    # Calculate some statistics
    total_audits = Audit.objects.count()
    if total_audits > 0:
        avg_score = Audit.objects.aggregate(avg=models.Avg('total_percentage'))['avg'] or 0
    else:
        avg_score = 0

    context = {
        'recent_audits': recent_audits,
        'restaurants': restaurants,
        'total_audits': total_audits,
        'avg_score': avg_score,
    }
    return render(request, 'core/dashboard.html', context)


def create_audit(request):
    """Create new audit"""
    if request.method == 'POST':
        restaurant_id = request.POST.get('restaurant')
        audit_date = request.POST.get('audit_date')
        manager_name = request.POST.get('manager_name')
        #auditor_name = request.POST.get('auditor_name')

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


def audit_list(request):
    """List all audits"""
    audits = Audit.objects.all().order_by('-audit_date')

    context = {
        'audits': audits
    }
    return render(request, 'core/audit_list.html', context)


# views.py
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
def save_response(request):
    """Save question response via AJAX"""
    if request.method == 'POST':
        try:
            audit_id = request.POST.get('audit_id')
            section_id = request.POST.get('section_id')
            question_id = request.POST.get('question_id')
            scored_points = request.POST.get('scored_points', '0')
            comments = request.POST.get('comments', '')

            # Convert to float, handle empty values
            try:
                scored_points = float(scored_points) if scored_points else 0.0
            except (ValueError, TypeError):
                scored_points = 0.0

            audit = get_object_or_404(Audit, id=audit_id)
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

            # Refresh section scores
            audit_section.calculate_section_score()
            audit.calculate_totals()

            return JsonResponse({
                'success': True,
                'message': 'Response saved successfully',
                'section_score': float(audit_section.scored_points),
                'section_percentage': float(audit_section.section_percentage)
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
