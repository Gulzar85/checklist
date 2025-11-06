from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import User


class UserRegistrationForm(UserCreationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes to all fields
        for field_name, field in self.fields.items():
            if field_name == 'role':
                field.widget.attrs['class'] = 'form-select'
            else:
                field.widget.attrs['class'] = 'form-control'

            # Add placeholders
            if field_name == 'username':
                field.widget.attrs['placeholder'] = 'Enter username'
            elif field_name == 'email':
                field.widget.attrs['placeholder'] = 'Enter email'
            elif field_name == 'password1':
                field.widget.attrs['placeholder'] = 'Enter password'
            elif field_name == 'password2':
                field.widget.attrs['placeholder'] = 'Confirm password'
            elif field_name == 'designation':
                field.widget.attrs['placeholder'] = 'Enter designation'
            elif field_name == 'department':
                field.widget.attrs['placeholder'] = 'Enter department'
            elif field_name == 'phone_number':
                field.widget.attrs['placeholder'] = 'Enter phone number'

    class Meta:
        model = User
        fields = [
            'username', 'email', 'password1', 'password2',
            'role', 'designation', 'department', 'phone_number'
        ]


class CustomAuthenticationForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes to form fields
        self.fields['username'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Username',
            'autocomplete': 'username'
        })
        self.fields['password'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Password',
            'autocomplete': 'current-password'
        })