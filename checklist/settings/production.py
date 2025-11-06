from .base import *

# -----------------------------------------
# Production Settings
# -----------------------------------------
DEBUG = False

# Always pull ALLOWED_HOSTS from your .env
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='yourdomain.com', cast=lambda v: [s.strip() for s in v.split(',')])

# Example: configure secure headers
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# Whitenoise already set up in base.py
# For caching or CDN, configure STATICFILES_STORAGE:
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Example: real email backend
# EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
# EMAIL_HOST = config('EMAIL_HOST')
# EMAIL_PORT = config('EMAIL_PORT', cast=int)
# EMAIL_HOST_USER = config('EMAIL_HOST_USER')
# EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD')
# EMAIL_USE_TLS = True
