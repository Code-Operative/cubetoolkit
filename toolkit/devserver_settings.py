import os.path
import logging
import logging.config

from toolkit.settings_common import *

APP_ROOT = '/home/ben/data/python/cube'

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = 'http://toolkit/media/'

# Enable Debug mode, add in Django toolbar:
DEBUG = True

# Django toolbar things:
INTERNAL_IPS = ('127.0.0.1',)
DEBUG_TOOLBAR_CONFIG = {'INTERCEPT_REDIRECTS': False, }

MIDDLEWARE_CLASSES = list(MIDDLEWARE_CLASSES)
MIDDLEWARE_CLASSES.append('debug_toolbar.middleware.DebugToolbarMiddleware')
INSTALLED_APPS = list(INSTALLED_APPS)
INSTALLED_APPS.append('debug_toolbar')

# Enable logging to the console:
logging.basicConfig(
    # level = logging.DEBUG,
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
)
