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
        # Always show "Admin" for superusers
        role_display = "Admin" if self.is_superuser else self.get_role_display()
        return f"{self.username} - {role_display}"

    def get_absolute_url(self):
        # You can later make this dynamic per role if needed
        return reverse('auditor_detail', args=[str(self.id)])

    def is_admin(self):
        # Either explicit admin role or Django superuser flag
        return self.role == 'admin' or self.is_superuser

    def is_auditor(self):
        return self.role == 'auditor' and not self.is_superuser
