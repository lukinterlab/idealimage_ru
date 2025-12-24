"""
Middleware для отслеживания рекламы
"""
from django.utils.deprecation import MiddlewareMixin


class AdTrackingMiddleware(MiddlewareMixin):
    """
    Middleware для сохранения session_key для анонимных пользователей
    Это необходимо для отслеживания кликов и показов
    """
    
    def process_request(self, request):
        """
        Создаем сессию если её нет
        """
        if not request.session.session_key:
            request.session.create()
        
        # Сохраняем session_key в request для удобства
        request.ad_session_key = request.session.session_key
        
        return None
    
    def process_response(self, request, response):
        """
        Обработка ответа
        """
        # Здесь можно добавить логику для отслеживания
        # Например, логирование показов рекламы
        return response


class AdPermissionMiddleware(MiddlewareMixin):
    """
    Middleware для проверки доступа к страницам управления рекламой
    """
    
    def process_request(self, request):
        """
        Проверка доступа к /advertising/
        """
        if request.path.startswith('/advertising/'):
            # Если это API endpoints - пропускаем
            if '/api/' in request.path or '/click/' in request.path:
                return None
            
            # Для остальных страниц проверяем авторизацию
            if not request.user.is_authenticated:
                from django.shortcuts import redirect
                return redirect('Visitor:user-login')
            
            # Проверяем права (staff или маркетолог)
            is_staff = request.user.is_staff
            is_marketer = hasattr(request.user, 'profile') and request.user.profile.is_marketer
            
            if not (is_staff or is_marketer):
                from django.http import HttpResponseForbidden
                return HttpResponseForbidden(
                    '<h1>Доступ запрещен</h1>'
                    '<p>У вас нет прав для доступа к панели управления рекламой.</p>'
                )
        
        return None

