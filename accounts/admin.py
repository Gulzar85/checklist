# accounts/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from .models import User
from .admin_forms import CustomUserCreationForm, CustomUserChangeForm


class CustomUserAdmin(UserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = User

    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'designation', 'is_staff', 'is_active')
    list_filter = ('role', 'is_staff', 'is_active', 'date_joined')

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'email')}),
        (_('Professional info'), {'fields': ('role', 'designation', 'department', 'phone_number')}),
        (_('Permissions'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'username', 'email', 'password1', 'password2',
                'first_name', 'last_name', 'role', 'designation',
                'department', 'phone_number', 'is_staff', 'is_active'
            ),
        }),
    )

    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('username',)


admin.site.register(User, CustomUserAdmin)