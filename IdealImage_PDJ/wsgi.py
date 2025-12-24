"""
WSGI config for IdealImage_PDJ project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/wsgi/
"""

import os
from decouple import config

from django.core.wsgi import get_wsgi_application

# Автоматически выбираем settings на основе DJANGO_ENV
# По умолчанию development, для production установите DJANGO_ENV=production в .env
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'IdealImage_PDJ.settings')

application = get_wsgi_application()