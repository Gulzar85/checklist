from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.contrib.auth import password_validation
from django.utils.translation import gettext_lazy as _
from .models import User

class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ('username', 'email', 'role', 'designation', 'department', 'phone_number')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Remove the help text that might confuse admins
        self.fields['password1'].help_text = ''
        self.fields['password2'].help_text = ''

    def save(self, commit=True):
        user = super().save(commit=False)
        # Password is automatically handled by UserCreationForm
        if commit:
            user.save()
        return user

class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = User
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Remove the password field help text
        password = self.fields.get('password')
        if password:
            password.help_text = password.help_text.replace(
                '../password/',
                ''
            )