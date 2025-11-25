from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .api import RestaurantViewSet, AuditViewSet, SectionViewSet, CorrectiveActionViewSet

app_name = 'core'

# Initialize router
router = DefaultRouter()
router.register(r'restaurants', RestaurantViewSet, basename='restaurant')
router.register(r'audits', AuditViewSet, basename='audit')
router.register(r'sections', SectionViewSet, basename='section')
router.register(r'corrective-actions', CorrectiveActionViewSet, basename='correctiveaction')

urlpatterns = [
    # Dashboard
    path('', views.AuditDashboardView.as_view(), name='dashboard'),

    # API
    path('api/', include(router.urls)),

    # Audit CRUD
    path('audit/create/', views.create_audit, name='create_audit'),
    path('audit/list/', views.AuditListView.as_view(), name='audit_list'),
    path('audit/<int:audit_id>/delete/', views.DeleteAuditView.as_view(), name='delete_audit'),

    # Restaurant Views
    path('restaurants/', views.RestaurantListView.as_view(), name='restaurant_list'),
    path('restaurant/<int:restaurant_id>/audits/', views.RestaurantAuditsView.as_view(), name='restaurant_audits'),

    # Audit Details & Workflow
    path('audit/<int:audit_id>/form/', views.audit_form, name='audit_form'),
    path('audit/<int:audit_id>/detail/', views.audit_detail, name='audit_detail'),
    path('audit/<int:audit_id>/results/', views.audit_results, name='audit_results'),

    # AJAX / API Endpoints
    path('audit/save-response/', views.save_response, name='save_response'),
    path('audit/<int:audit_id>/submit/', views.submit_audit, name='submit_audit'),
    path('audit/<int:audit_id>/progress/', views.audit_progress, name='audit_progress'),

    # Reports
    path('reports/overview/', views.reports_overview, name='reports_overview'),
    path('reports/restaurant-performance/', views.restaurant_performance_report, name='restaurant_performance_report'),

    # Corrective Actions
    path('corrective-actions/', views.corrective_action_list, name='action_list'),
    path('corrective-actions/dashboard/', views.corrective_action_dashboard, name='corrective_action_dashboard'),
    path('corrective-actions/create/<int:response_id>/', views.create_corrective_action, name='corrective_action_create'),
    path('corrective-actions/<int:pk>/', views.CorrectiveActionDetailView.as_view(), name='corrective_action_detail'),
    path('corrective-actions/<int:pk>/update/', views.CorrectiveActionUpdateView.as_view(), name='corrective_action_update'),
    path('corrective-actions/<int:pk>/delete/', views.CorrectiveActionDeleteView.as_view(), name='corrective_action_delete'),
    path('corrective-actions/<int:pk>/complete/', views.mark_action_completed, name='corrective_action_mark_completed'),

    # Export
    path('export/audits/csv/', views.export_audits_csv, name='export_audits_csv'),

    # API Endpoints
    path('api/statistics/', views.api_audit_statistics, name='api_audit_statistics'),
    path('api/restaurants/', views.api_restaurant_list, name='api_restaurant_list'),
]