from core.models import Restaurant, Audit
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView
from django.db.models import Avg
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic import CreateView
from django.views.generic import UpdateView

from .forms import UserProfileForm
from .forms import UserRegistrationForm, CustomAuthenticationForm
from .models import User


class CustomLoginView(LoginView):
    template_name = 'accounts/login.html'
    form_class = CustomAuthenticationForm
    redirect_authenticated_user = True

    def get_success_url(self):
        return reverse_lazy('core:dashboard')

    def form_invalid(self, form):
        messages.error(self.request, 'Invalid username or password. Please try again.')
        return super().form_invalid(form)


class UserRegistrationView(CreateView):
    model = User
    form_class = UserRegistrationForm
    template_name = 'accounts/register.html'
    success_url = reverse_lazy('accounts:login')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Account created successfully! You can now login.')
        return response

    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)


def dashboard(request):
    return render(request, 'accounts/dashboard.html')


class UserProfileView(LoginRequiredMixin, UpdateView):
    model = User
    form_class = UserProfileForm
    template_name = 'accounts/profile.html'
    success_url = reverse_lazy('accounts:profile')

    def get_object(self):
        return self.request.user

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # User statistics
        user_audits = Audit.objects.filter(auditor_name=user)
        context['total_audits'] = user_audits.count()
        context['average_score'] = user_audits.aggregate(avg=Avg('total_percentage'))['avg'] or 0
        context['restaurant_count'] = Restaurant.objects.filter(
            audit__auditor_name=user
        ).distinct().count()
        context['grade_a_count'] = user_audits.filter(grade='A').count()

        # Recent activity (simplified)
        context['recent_activity'] = user_audits.select_related('restaurant').order_by('-created_at')[:5]

        return context

    def form_valid(self, form):
        messages.success(self.request, 'Profile updated successfully!')
        return super(

        ).form_valid(form)
