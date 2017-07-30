
import os

DEBUG = True

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

INSTALLED_APPS = [
    'ghtorrent',
    'so',
    'pypi',
    'scraper',
]


USE_I18N = False
USE_L10N = False
USE_TZ = False
