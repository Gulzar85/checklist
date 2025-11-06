from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView

from .forms import UserRegistrationForm, UserLoginForm
from .models import User


class CustomLoginView(LoginView):
    template_name = 'accounts/login.html'
    form_class = UserLoginForm

    def get_success_url(self):
        return reverse_lazy('core:dashboard')


class UserRegistrationView(CreateView):
    model = User
    form_class = UserRegistrationForm
    template_name = 'accounts/register.html'
    success_url = reverse_lazy('core:dashboard')

    def form_valid(self, form):
        user = form.save(commit=False)
        user.save()

        # Log the new user in immediately
        login(self.request, user)
        messages.success(self.request, "Registration successful. Welcome!")

        return redirect(self.get_success_url())


@login_required
def dashboard(request):
    return render(request, 'accounts/dashboard.html')
