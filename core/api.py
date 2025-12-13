from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q, Avg, Count
from .models import Restaurant, Audit, Section, Question, CorrectiveAction
from .serializers import (
    RestaurantSerializer, AuditSerializer, SectionSerializer,
    QuestionSerializer, CorrectiveActionSerializer, AuditCreateSerializer
)


class RestaurantViewSet(viewsets.ModelViewSet):
    queryset = Restaurant.objects.all()
    serializer_class = RestaurantSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser or getattr(user, 'role', None) == 'admin':
            return Restaurant.objects.all()
        return Restaurant.objects.filter(
            Q(audit__auditor_name=user) |
            Q(audit__manager_on_duty__icontains=user.get_full_name())
        ).distinct()


class AuditViewSet(viewsets.ModelViewSet):
    serializer_class = AuditSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = Audit.objects.select_related('restaurant', 'auditor_name')

        if not (user.is_superuser or getattr(user, 'role', None) == 'admin'):
            qs = qs.filter(auditor_name=user)

        return qs.order_by('-audit_date')

    def get_serializer_class(self):
        if self.action == 'create':
            return AuditCreateSerializer
        return AuditSerializer

    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        audit = self.get_object()
        if audit.submit_audit():
            return Response({'status': 'audit submitted'})
        return Response({'error': 'Submission failed'}, status=400)

    @action(detail=False)
    def statistics(self, request):
        user = request.user
        qs = Audit.objects.all()

        if not (user.is_superuser or getattr(user, 'role', None) == 'admin'):
            qs = qs.filter(auditor_name=user)

        stats = qs.aggregate(
            total_audits=Count('id'),
            avg_score=Avg('total_percentage'),
            submitted_count=Count('id', filter=Q(is_submitted=True))
        )
        return Response(stats)


class SectionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Section.objects.prefetch_related('questions').all()
    serializer_class = SectionSerializer
    permission_classes = [permissions.IsAuthenticated]


class CorrectiveActionViewSet(viewsets.ModelViewSet):
    queryset = CorrectiveAction.objects.all()
    serializer_class = CorrectiveActionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = CorrectiveAction.objects.select_related('audit', 'question_response')

        if not (user.is_superuser or getattr(user, 'role', None) == 'admin'):
            qs = qs.filter(audit__auditor_name=user)

        return qs