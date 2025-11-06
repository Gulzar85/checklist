from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView, ListView
from django.urls import reverse_lazy
from .models import Audit


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'core/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_audits'] = Audit.objects.count()
        context['recent_audits'] = Audit.objects.order_by('-created_at')[:5]
        return context


class AuditListView(LoginRequiredMixin, ListView):
    model = Audit
    template_name = 'core/audit_list.html'
    context_object_name = 'audits'
    paginate_by = 20


# Temporary placeholder views for other URLs
class AuditCreateView(LoginRequiredMixin, TemplateView):
    template_name = 'core/audit_create.html'


class AuditDetailView(LoginRequiredMixin, TemplateView):
    template_name = 'core/audit_detail.html'


class AuditUpdateView(LoginRequiredMixin, TemplateView):
    template_name = 'core/audit_update.html'