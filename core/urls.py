from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.DashboardView.as_view(), name='dashboard'),
    path('audits/', views.AuditListView.as_view(), name='audit_list'),
    path('audits/create/', views.AuditCreateView.as_view(), name='audit_create'),
    path('audits/<int:pk>/', views.AuditDetailView.as_view(), name='audit_detail'),
    path('audits/<int:pk>/update/', views.AuditUpdateView.as_view(), name='audit_update'),
]