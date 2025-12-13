from .base import *

# -----------------------------------------
# Production Settings
# -----------------------------------------
DEBUG = False

# Always pull ALLOWED_HOSTS from your .env
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='qaauditchecklist.pythonanywhere.com', cast=lambda v: [s.strip() for s in v.split(',')])

# Example: configure secure headers
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True

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

CORS_ALLOW_ALL_ORIGINS = False  # Never use True in production!
CORS_ALLOW_CREDENTIALS = True

# Power BI specific origins
CORS_ALLOWED_ORIGINS = [
    "https://app.powerbi.com",
    "https://*.powerbi.com",
    "https://auditchecklist.pythonanywhere.com",  # Your domain
    "https://www.auditchecklist.pythonanywhere.com",
]

# Additional Microsoft/Power BI domains that might be needed
CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^https://\w+\.powerbi\.com$",
    r"^https://\w+\.analysis\.windows\.net$",  # Power BI service
    r"^https://\w+\.microsoftonline\.com$",  # Microsoft auth
    r"^https://\w+\.microsoft\.com$",
]

# CSRF settings for production
CSRF_TRUSTED_ORIGINS = [
    'https://auditchecklist.pythonanywhere.com',
    'https://www.auditchecklist.pythonanywhere.com',
]