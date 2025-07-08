from .base import *

# Debug settings
DEBUG = False

# Add debug toolbar
INSTALLED_APPS += ['debug_toolbar']
MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']

# Debug toolbar settings
INTERNAL_IPS = [
    '127.0.0.1',
    'localhost',
]

# Email backend for development
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Database settings for development
# DATABASES['default']['OPTIONS'] = {
#     'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
#     'charset': 'utf8mb4',
# }

# Cache settings for development
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}

# Development specific logging
# LOGGING['handlers']['console']['level'] = 'DEBUG'
# LOGGING['loggers']['django']['level'] = 'DEBUG'