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

LOGGING['loggers']['core']['level'] = 'DEBUG'
LOGGING['handlers']['console']['class'] = 'logging.StreamHandler'
LOGGING['root']['level'] = 'DEBUG'