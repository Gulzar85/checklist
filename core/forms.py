from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .models import Audit, Restaurant
from .models import CorrectiveAction


class McDonaldDateInput(forms.DateInput):
    input_type = 'date'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.attrs.update({
            'class': 'form-control',
            'style': 'border-color: #DA291C;'
        })


class McDonaldSelect(forms.Select):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.attrs.update({
            'class': 'form-select',
            'style': 'border-color: #DA291C;'
        })


class CreateAuditForm(forms.ModelForm):
    class Meta:
        model = Audit
        fields = ['restaurant', 'audit_date', 'manager_on_duty']
        widgets = {
            'restaurant': McDonaldSelect(),
            'audit_date': McDonaldDateInput(),
            'manager_on_duty': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter manager name',
                'style': 'border-color: #DA291C;'
            }),
        }

    def clean_audit_date(self):
        audit_date = self.cleaned_data['audit_date']
        if audit_date > timezone.now().date():
            raise ValidationError("Audit date cannot be in the future.")
        return audit_date

    def clean(self):
        cleaned_data = super().clean()
        restaurant = cleaned_data.get('restaurant')
        audit_date = cleaned_data.get('audit_date')

        if restaurant and audit_date:
            # Check for existing audit on same date for same restaurant
            existing = Audit.objects.filter(
                restaurant=restaurant,
                audit_date=audit_date
            ).exists()

            if existing:
                raise ValidationError(
                    f"An audit for {restaurant.name} on {audit_date} already exists."
                )
        return cleaned_data


class CorrectiveActionForm(forms.ModelForm):
    class Meta:
        model = CorrectiveAction
        fields = ['audit', 'question_response','description', 'risk_level', 'assigned_to', 'deadline', 'completed', 'comments']
        widgets = {
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'style': 'border-color: #DA291C;'
            }),
            'risk_level': McDonaldSelect(),
            'assigned_to': forms.TextInput(attrs={
                'class': 'form-control',
                'style': 'border-color: #DA291C;'
            }),
            'deadline': McDonaldDateInput(),
            'comments': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'style': 'border-color: #DA291C;'
            }),
        }

    def clean_deadline(self):
        deadline = self.cleaned_data['deadline']
        if deadline < timezone.now().date():
            raise ValidationError("Deadline cannot be in the past.")
        return deadline


class RestaurantFilterForm(forms.Form):
    city = forms.ChoiceField(required=False, widget=McDonaldSelect())
    is_active = forms.BooleanField(required=False, initial=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Dynamically set city choices
        cities = Restaurant.objects.values_list('city', flat=True).distinct()
        self.fields['city'].choices = [('', 'All Cities')] + [(city, city) for city in cities]

