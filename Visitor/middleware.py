"""
Middleware для автоматического продления сессии
"""
from django.utils import timezone
from datetime import timedelta


class SessionRefreshMiddleware:
    """
    Автоматически продлевает сессию пользователя при каждом запросе
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            # Продлеваем сессию на 1 год при каждой активности
            request.session.set_expiry(31536000)
        
        response = self.get_response(request)
        return response

