import re

from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.db import models
from django.urls import reverse

mobile_validator = RegexValidator(
    regex=r'^03\d{2}-?\d{7}$',
    message='Enter a valid Pakistani mobile number, e.g. 0300-1234567'
)


class User(AbstractUser):
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('auditor', 'Auditor'),
    )

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='auditor')
    designation = models.CharField(max_length=100, blank=True, null=True)
    department = models.CharField(max_length=100, blank=True, null=True)
    phone_number = models.CharField(max_length=12, blank=True, null=True, validators=[mobile_validator], )

    def save(self, *args, **kwargs):
        if self.phone_number:
            # remove any non-digit characters
            digits = re.sub(r'\D', '', self.phone_number)
            # if valid length and starts with 03, format it
            if re.match(r'^03\d{9}$', digits):
                self.phone_number = f"{digits[:4]}-{digits[4:]}"
        super().save(*args, **kwargs)

    def __str__(self):
        # Decide display name
        full_name = " ".join(filter(None, [self.first_name, self.last_name])).strip()

        # Determine role/designation
        role_display = "Admin" if self.is_superuser else self.get_role_display()

        # Return format based on name availability
        if full_name:
            return f"{full_name}"
        else:
            return f"{self.username} - {role_display}"

    def get_full_name(self):
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        elif self.last_name:
            return self.last_name
        else:
            return self.username

    def get_absolute_url(self):
        # You can later make this dynamic per role if needed
        return reverse('auditor_detail', args=[str(self.id)])

    def is_admin(self):
        # Either explicit admin role or Django superuser flag
        return self.role == 'admin' or self.is_superuser

    def is_auditor(self):
        return self.role == 'auditor' and not self.is_superuser
