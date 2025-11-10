from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.core.validators import RegexValidator
from .models import User

from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.core.validators import RegexValidator
from .models import User


class UserRegistrationForm(UserCreationForm):
    # Custom fields with McDonald's styling
    first_name = forms.CharField(
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your first name'
        })
    )

    last_name = forms.CharField(
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your last name'
        })
    )

    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email address'
        })
    )

    designation = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., Quality Auditor'
        })
    )

    department = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., Quality Assurance'
        })
    )

    phone_number = forms.CharField(
        max_length=12,
        required=False,
        validators=[RegexValidator(
            regex=r'^03\d{2}-?\d{7}$',
            message='Enter a valid Pakistani mobile number (e.g., 0300-1234567)'
        )],
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '0300-1234567'
        })
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Add Bootstrap classes and placeholders to all fields
        for field_name, field in self.fields.items():
            # Add form-control class to most fields
            if field_name in ['username', 'email', 'password1', 'password2',
                              'first_name', 'last_name', 'designation', 'department', 'phone_number']:
                field.widget.attrs['class'] = 'form-control'

            # Set specific placeholders - FIXED: Don't use field.label.lower() as it might be None
            if field_name == 'username':
                field.widget.attrs['placeholder'] = 'Choose a username'
            elif field_name == 'email':
                field.widget.attrs['placeholder'] = 'your.email@mcdonalds.com'
            elif field_name == 'password1':
                field.widget.attrs['placeholder'] = 'Create a strong password'
            elif field_name == 'password2':
                field.widget.attrs['placeholder'] = 'Confirm your password'
            elif field_name == 'first_name':
                field.widget.attrs['placeholder'] = 'Enter your first name'
            elif field_name == 'last_name':
                field.widget.attrs['placeholder'] = 'Enter your last name'
            elif field_name == 'designation':
                field.widget.attrs['placeholder'] = 'Quality Auditor'
            elif field_name == 'department':
                field.widget.attrs['placeholder'] = 'Quality Assurance'
            elif field_name == 'phone_number':
                field.widget.attrs['placeholder'] = '0300-1234567'

        # Remove help text
        self.fields['username'].help_text = ''
        self.fields['password1'].help_text = ''
        self.fields['password2'].help_text = ''

    class Meta:
        model = User
        fields = [
            'username', 'email', 'password1', 'password2',
            'first_name', 'last_name', 'designation', 'department', 'phone_number'
        ]

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("This email is already registered.")
        return email

    def clean_phone_number(self):
        phone_number = self.cleaned_data.get('phone_number')
        if phone_number and User.objects.filter(phone_number=phone_number).exists():
            raise forms.ValidationError("This phone number is already registered.")
        return phone_number


class CustomAuthenticationForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Add McDonald's styling to form fields
        self.fields['username'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Enter your username',
            'autocomplete': 'username'
        })

        self.fields['password'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Enter your password',
            'autocomplete': 'current-password'
        })


class UserProfileForm(forms.ModelForm):
    # Custom fields with improved styling
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'your.email@mcdonalds.com'
        })
    )

    designation = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Quality Auditor'
        })
    )

    department = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Quality Assurance'
        })
    )

    phone_number = forms.CharField(
        max_length=12,
        required=False,
        validators=[RegexValidator(
            regex=r'^03\d{2}-?\d{7}$',
            message='Enter a valid Pakistani mobile number (e.g., 0300-1234567)'
        )],
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '0300-1234567'
        })
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Add Bootstrap classes to all fields
        for field_name, field in self.fields.items():
            if field_name not in ['role']:  # Role is handled separately
                field.widget.attrs['class'] = 'form-control'

            # Add specific placeholders
            if field_name == 'username':
                field.widget.attrs['placeholder'] = 'Enter username'
            elif field_name == 'first_name':
                field.widget.attrs['placeholder'] = 'Enter first name'
            elif field_name == 'last_name':
                field.widget.attrs['placeholder'] = 'Enter last name'

    class Meta:
        model = User
        fields = [
            'username', 'email', 'first_name', 'last_name',
            'designation', 'department', 'phone_number'
        ]

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("This email is already registered.")
        return email

    def clean_phone_number(self):
        phone_number = self.cleaned_data.get('phone_number')
        if phone_number and User.objects.filter(phone_number=phone_number).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("This phone number is already registered.")
        return phone_number


class UserProfileForm(forms.ModelForm):
    # Custom fields with improved styling
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'your.email@mcdonalds.com'
        })
    )

    designation = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Quality Auditor'
        })
    )

    department = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Quality Assurance'
        })
    )

    phone_number = forms.CharField(
        max_length=12,
        required=False,
        validators=[RegexValidator(
            regex=r'^03\d{2}-?\d{7}$',
            message='Enter a valid Pakistani mobile number (e.g., 0300-1234567)'
        )],
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '0300-1234567'
        })
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Add Bootstrap classes to all fields
        for field_name, field in self.fields.items():
            if field_name not in ['role']:  # Role is handled separately
                field.widget.attrs['class'] = 'form-control'

            # Add specific placeholders
            if field_name == 'username':
                field.widget.attrs['placeholder'] = 'Enter username'
            elif field_name == 'first_name':
                field.widget.attrs['placeholder'] = 'Enter first name'
            elif field_name == 'last_name':
                field.widget.attrs['placeholder'] = 'Enter last name'

    class Meta:
        model = User
        fields = [
            'username', 'email', 'first_name', 'last_name',
            'designation', 'department', 'phone_number'
        ]

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("This email is already registered.")
        return email

    def clean_phone_number(self):
        phone_number = self.cleaned_data.get('phone_number')
        if phone_number and User.objects.filter(phone_number=phone_number).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("This phone number is already registered.")
        return phone_number