from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    # Audit Forms
    path('audit/<int:audit_id>/form/', views.audit_form, name='audit_form'),
    path('audit/save-response/', views.save_response, name='save_response'),
    path('audit/<int:audit_id>/submit/', views.submit_audit, name='submit_audit'),
    path('audit/<int:audit_id>/progress/', views.audit_progress, name='audit_progress'),
    path('audit/<int:audit_id>/results/', views.audit_results, name='audit_results'),

    # Dashboard and Management
    path('', views.audit_dashboard, name='dashboard'),
    path('audit/create/', views.create_audit, name='create_audit'),
    path('audit/list/', views.audit_list, name='audit_list'),
]