from django.contrib.auth import views as auth_views
from django.urls import path

from .views import (
    CustomLoginView,
    UserRegistrationView,
    UserProfileView,
    CustomLogoutView,
    PasswordResetView,
    PasswordResetDoneView,
    PasswordChangeView
)

app_name = 'accounts'

urlpatterns = [
    path('login/', CustomLoginView.as_view(), name='login'),
    path('register/', UserRegistrationView.as_view(), name='register'),
    path('profile/', UserProfileView.as_view(), name='profile'),
    path('logout/', CustomLogoutView.as_view(), name='logout'),

    # Password management
    path('password/reset/', PasswordResetView.as_view(), name='password_reset'),
    path('password/reset/done/', PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('password/change/', PasswordChangeView.as_view(), name='password_change'),
]