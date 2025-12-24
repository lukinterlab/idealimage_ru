"""
Настройки для ПРОДАКШЕНА (DEBUG = False)
Максимальная безопасность, производительность, скрытие ошибок
"""
from .base import *

# DEBUG режим - скрываем ошибки
DEBUG = config('DEBUG', default=False, cast=bool)

# Whitenoise для раздачи статики с компрессией (только в prod)
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Security настройки для продакшена (включены только если DEBUG=False)
if not DEBUG:
    SECURE_SSL_REDIRECT = True  # Перенаправление на HTTPS
    SECURE_HSTS_SECONDS = 31536000  # 1 год HSTS
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_CONTENT_TYPE_NOSNIFF = True  # Защита от MIME-sniffing
    SECURE_BROWSER_XSS_FILTER = True  # XSS защита в браузере
    X_FRAME_OPTIONS = 'SAMEORIGIN'  # Защита от clickjacking (SAMEORIGIN для iframe видео)
    CSRF_COOKIE_SECURE = True  # CSRF cookie только через HTTPS
    CSRF_TRUSTED_ORIGINS = ['https://idealimage.ru']  # Доверенные origin для CSRF
    SESSION_COOKIE_SECURE = True  # HTTPS only для сессий

# Уровень логирования - только важное в prod
LOGGING['loggers']['django']['level'] = 'WARNING'  # Только предупреждения и ошибки
LOGGING['loggers']['django.request']['level'] = 'ERROR'  # Только ошибки запросов
LOGGING['loggers']['Asistent']['level'] = 'INFO'  # AI логи оставляем INFO

