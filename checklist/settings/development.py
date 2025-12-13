from .base import *

# -----------------------------------------
# Development Settings
# -----------------------------------------
DEBUG = True

# Allow your local addresses
ALLOWED_HOSTS = ['localhost', '127.0.0.1']

# Optional: enable Django Debug Toolbar if you use it
# INSTALLED_APPS += ['debug_toolbar']
# MIDDLEWARE.insert(0, 'debug_toolbar.middleware.DebugToolbarMiddleware')

# Show emails in console during development
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# CORS settings for development
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True

CSRF_TRUSTED_ORIGINS = [
    'http://localhost:8000',
    'http://127.0.0.1:8000',
]