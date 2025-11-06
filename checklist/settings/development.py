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

# Optional: log SQL queries for debugging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {'class': 'logging.StreamHandler'},
    },
    'root': {
        'handlers': ['console'],
        'level': 'DEBUG',
    },
}
