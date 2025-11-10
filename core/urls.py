# urls.py
from django.urls import path

from . import views
from .views import RestaurantAuditsView, AuditDashboardView, AuditListView, DeleteAuditView

app_name = 'core'

urlpatterns = [
    # Dashboard and Management
    path('', AuditDashboardView.as_view(), name='dashboard'),
    path('audit/create/', views.create_audit, name='create_audit'),
    path('audit/list/', AuditListView.as_view(), name='audit_list'),
    path('audit/<int:audit_id>/delete/', DeleteAuditView.as_view(), name='delete_audit'),
    path('restaurant/<int:restaurant_id>/audits/', RestaurantAuditsView.as_view(), name='restaurant_audits'),

    # Audit Forms and Actions
    path('audit/<int:audit_id>/form/', views.audit_form, name='audit_form'),
    path('audit/save-response/', views.save_response, name='save_response'),
    path('audit/<int:audit_id>/submit/', views.submit_audit, name='submit_audit'),
    path('audit/<int:audit_id>/results/', views.audit_results, name='audit_results'),
    path('audit/<int:audit_id>/progress/', views.audit_progress, name='audit_progress'),  # AJAX Data
]
