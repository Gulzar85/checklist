from django.contrib.auth.views import LogoutView
from django.urls import path

from .views import CustomLoginView, UserRegistrationView, dashboard

app_name = 'accounts'

urlpatterns = [
    path('login/', CustomLoginView.as_view(), name='login'),
    path('register/', UserRegistrationView.as_view(), name='register'),
    path('dashboard/', dashboard, name='dashboard'),
    path('logout/', LogoutView.as_view(next_page='accounts:login'), name='logout'),
]
