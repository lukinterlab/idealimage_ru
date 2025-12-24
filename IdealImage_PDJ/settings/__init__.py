"""
Settings для IdealImage.ru
Автоматически выбирает нужный режим на основе DJANGO_SETTINGS_MODULE или DEBUG
"""
import os
from decouple import config

# Определяем режим работы
# Можно переключить через переменную окружения: DJANGO_ENV=production
DJANGO_ENV = config('DJANGO_ENV', default='development')

if DJANGO_ENV == 'production':
    from .production import *
else:
    from .development import *

