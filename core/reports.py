import logging
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count, Q, F
from django.utils import timezone
from datetime import timedelta
from .models import Audit, Restaurant, CorrectiveAction

logger = logging.getLogger(__name__)


@login_required
def reports_overview(request):
    """Comprehensive reports overview"""
    try:
        user = request.user
        thirty_days_ago = timezone.now().date() - timedelta(days=30)

        # Base querysets
        audit_qs = Audit.objects.filter(is_submitted=True)
        corrective_qs = CorrectiveAction.objects.all()

        if not (user.is_superuser or getattr(user, 'role', None) == 'admin'):
            audit_qs = audit_qs.filter(auditor_name=user)
            corrective_qs = corrective_qs.filter(audit__auditor_name=user)

        # Recent statistics
        recent_audits = audit_qs.filter(audit_date__gte=thirty_days_ago)
        total_audits = audit_qs.count()
        avg_score = audit_qs.aggregate(avg=Avg('total_percentage'))['avg'] or 0

        # Grade distribution
        grade_distribution = audit_qs.values('grade').annotate(
            count=Count('id'),
            percentage=Avg('total_percentage')
        ).order_by('grade')

        # Critical failures
        critical_failures = audit_qs.filter(has_critical_failure=True).count()

        # Corrective actions
        overdue_actions = corrective_qs.filter(
            completed=False,
            deadline__lt=timezone.now().date()
        ).count()

        pending_actions = corrective_qs.filter(completed=False).count()

        # Top performing restaurants
        top_restaurants = Restaurant.objects.annotate(
            audit_count=Count('audit'),
            avg_score=Avg('audit__total_percentage'),
            last_audit_date=Max('audit__audit_date')
        ).filter(audit_count__gt=0).order_by('-avg_score')[:10]

        context = {
            'total_audits': total_audits,
            'recent_audits_count': recent_audits.count(),
            'avg_score': round(avg_score, 2),
            'grade_distribution': grade_distribution,
            'critical_failures': critical_failures,
            'overdue_actions': overdue_actions,
            'pending_actions': pending_actions,
            'top_restaurants': top_restaurants,
        }

        return render(request, 'core/reports_overview.html', context)

    except Exception as e:
        logger.error("Error generating reports overview: %s", str(e))
        return render(request, 'core/reports_overview.html', {'error': str(e)})


@login_required
def restaurant_performance_report(request):
    """Restaurant performance comparison report"""
    try:
        user = request.user

        restaurant_qs = Restaurant.objects.annotate(
            total_audits=Count('audit', filter=Q(audit__is_submitted=True)),
            avg_score=Avg('audit__total_percentage', filter=Q(audit__is_submitted=True)),
            last_audit_date=Max('audit__audit_date', filter=Q(audit__is_submitted=True)),
            critical_failures=Count('audit', filter=Q(audit__has_critical_failure=True)),
            grade_a_count=Count('audit', filter=Q(audit__grade='A')),
        ).filter(total_audits__gt=0)

        if not (user.is_superuser or getattr(user, 'role', None) == 'admin'):
            restaurant_qs = restaurant_qs.filter(audit__auditor_name=user)

        # Sort by average score descending
        restaurants = restaurant_qs.order_by('-avg_score')

        # City-wise performance
        city_performance = Restaurant.objects.filter(
            audit__is_submitted=True
        ).values('city').annotate(
            avg_score=Avg('audit__total_percentage'),
            audit_count=Count('audit'),
            restaurant_count=Count('id', distinct=True)
        ).order_by('-avg_score')

        context = {
            'restaurants': restaurants,
            'city_performance': city_performance,
        }

        return render(request, 'core/restaurant_performance_report.html', context)

    except Exception as e:
        logger.error("Error generating restaurant performance report: %s", str(e))
        return render(request, 'core/restaurant_performance_report.html', {'error': str(e)})