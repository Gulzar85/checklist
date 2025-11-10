from core.models import Restaurant, Audit
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Avg
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView, FormView, TemplateView
from django.contrib.auth.models import User
import secrets
import string

from .forms import UserProfileForm, UserRegistrationForm, CustomAuthenticationForm, CustomPasswordResetForm, \
    CustomSetPasswordForm
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


class CustomLogoutView(LogoutView):
    next_page = reverse_lazy('accounts:login')

    def dispatch(self, request, *args, **kwargs):
        messages.success(request, 'Successfully logged out!')
        return super().dispatch(request, *args, **kwargs)


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
        return super().form_valid(form)


class PasswordResetView(FormView):
    template_name = 'accounts/password_reset.html'
    form_class = CustomPasswordResetForm
    success_url = reverse_lazy('accounts:password_reset_done')

    def form_valid(self, form):
        username = form.cleaned_data['username']
        try:
            user = User.objects.get(username=username)

            # Generate a random password
            alphabet = string.ascii_letters + string.digits
            new_password = ''.join(secrets.choice(alphabet) for i in range(12))

            # Set the new password
            user.set_password(new_password)
            user.save()

            # Store the new password in session to display on the next page
            self.request.session['new_password'] = new_password
            self.request.session['reset_username'] = username

            messages.success(
                self.request,
                f"Password reset successful for user: {username}"
            )

        except User.DoesNotExist:
            form.add_error('username', 'User with this username does not exist.')
            return self.form_invalid(form)

        return super().form_valid(form)


class PasswordResetDoneView(TemplateView):
    template_name = 'accounts/password_reset_done.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['new_password'] = self.request.session.get('new_password', '')
        context['username'] = self.request.session.get('reset_username', '')

        # Clear the session data
        if 'new_password' in self.request.session:
            del self.request.session['new_password']
        if 'reset_username' in self.request.session:
            del self.request.session['reset_username']

        return context


class PasswordChangeView(LoginRequiredMixin, SuccessMessageMixin, FormView):
    template_name = 'accounts/password_change.html'
    form_class = CustomSetPasswordForm
    success_url = reverse_lazy('accounts:profile')
    success_message = "Password changed successfully!"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.save()
        return super().form_valid(form)
