"""
Middleware для отлова и обработки 404 ошибок
Логирует, уведомляет и автоматически создает редиректы
"""
import logging
import re
from typing import Any, Dict, List, Optional

from django.core.cache import cache
from django.http import HttpResponsePermanentRedirect, HttpResponseRedirect
from django.urls import reverse
from django.utils import timezone

from Asistent.services.yandex_webmaster import (
    get_yandex_webmaster_client,
    YandexWebmasterClient,
)
from blog.models import Post

logger = logging.getLogger(__name__)

SUSPICIOUS_404_PATTERNS = [
    re.compile(r'^/wp[-_]', re.IGNORECASE),
    re.compile(r'^/wp-admin', re.IGNORECASE),
    re.compile(r'^/wp-includes', re.IGNORECASE),
    re.compile(r'^/wp-content', re.IGNORECASE),
    re.compile(r'^/wordpress', re.IGNORECASE),
    re.compile(r'\.php\d*$', re.IGNORECASE),
    re.compile(r'^/sites/all/', re.IGNORECASE),
    re.compile(r'^/elfinder', re.IGNORECASE),
    re.compile(r'^/0e[0-9a-f]{4,32}\.txt$', re.IGNORECASE),
]


class Smart404Middleware:
    """
    Умный middleware для обработки 404 ошибок:
    1. Логирует все 404
    2. Пытается найти похожую страницу
    3. Создает автоматические редиректы
    4. Отправляет уведомления в Telegram
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.telegram_bot_token = None
        self.admin_telegram_id = None
        
        try:
            from django.conf import settings
            self.telegram_bot_token = getattr(settings, 'TELEGRAM_BOT_TOKEN', None)
            self.admin_telegram_id = getattr(settings, 'ADMIN_TELEGRAM_ID', None)
        except:
            pass
    
    def __call__(self, request):
        response = self.get_response(request)
        
        # Обрабатываем только 404 ошибки
        if response.status_code == 404:
            return self.handle_404(request, response)
        
        return response
    
    def handle_404(self, request, response):
        """Обработка 404 ошибки"""
        path = request.path

        if self._should_skip_logging(path):
            return response
        
        # Логируем 404
        logger.warning(f"404 Error: {path} | Referrer: {request.META.get('HTTP_REFERER', 'N/A')}")
        
        # Сохраняем в кэш для статистики
        cache_key = f"404_log_{path}"
        count = cache.get(cache_key, 0) + 1
        cache.set(cache_key, count, 3600 * 24)  # 24 часа
        
        # Если много запросов к одной странице - отправляем alert
        if count == 5:
            self.send_404_alert(path, count)
        
        # Пытаемся найти похожую страницу и сделать редирект
        redirect_url = self.find_similar_page(path)
        if redirect_url:
            logger.info(f"Auto-redirect 404: {path} -> {redirect_url}")
            return HttpResponsePermanentRedirect(redirect_url)
        
        # Возвращаем оригинальный 404
        return response
    
    def _should_skip_logging(self, path: str) -> bool:
        """Возвращает True, если 404 нужно полностью игнорировать"""
        for pattern in SUSPICIOUS_404_PATTERNS:
            if pattern.search(path):
                return True
        return False
    
    def find_similar_page(self, path):
        """
        Пытается найти похожую страницу для редиректа
        
        Examples:
            /post/my-slug/ -> /blog/post/my-slug/
            /post/tags/test/ -> /blog/post/tags/test/
        """
        # Старые URL постов -> новые URL блога
        if path.startswith('/post/'):
            new_path = path.replace('/post/', '/blog/post/', 1)
            
            # Проверяем существует ли страница
            if self.url_exists(new_path):
                return new_path
        
        # Пытаемся найти пост по slug
        if '/post/' in path:
            slug = path.rstrip('/').split('/')[-1]
            # ИСПРАВЛЕНО: Убираем дефисы в начале и конце slug
            original_slug = slug
            slug = slug.strip('-').strip('$')
            
            # Если slug начинался с дефиса - делаем редирект 301 на исправленный URL
            if original_slug.startswith('-') and slug != original_slug:
                try:
                    post = Post.objects.filter(slug=slug, status='published').first()
                    if post:
                        # Редирект 301 на правильный URL
                        from django.http import HttpResponsePermanentRedirect
                        return HttpResponsePermanentRedirect(post.get_absolute_url())
                except:
                    pass
            
            # Обычный поиск по исправленному slug
            try:
                post = Post.objects.filter(slug=slug, status='published').first()
                if post:
                    return post.get_absolute_url()
            except:
                pass
        
        return None
    
    def url_exists(self, path):
        """Проверка существования URL"""
        from django.urls import resolve
        from django.urls.exceptions import Resolver404
        
        try:
            resolve(path)
            return True
        except Resolver404:
            return False
    
    def send_404_alert(self, path, count):
        """Отправка алерта о частых 404 ошибках"""
        if not self.telegram_bot_token or not self.admin_telegram_id:
            return
        
        message = f"""⚠️ <b>АЛЕРТ: Частые 404 ошибки</b>

<b>URL:</b> {path}
<b>Количество:</b> {count} запросов за час
<b>Время:</b> {timezone.now().strftime('%d.%m.%Y %H:%M')}

<i>Проверьте эту страницу!</i>"""
        
        try:
            from Asistent.services.telegram_client import get_telegram_client

            client = get_telegram_client()
            if not client.send_message(self.admin_telegram_id, message, parse_mode='HTML'):
                logger.error("Failed to send 404 alert via Telegram API")
        except Exception as e:
            logger.error(f"Failed to send 404 alert: {e}")


class YandexWebmasterIntegration:
    """
    Интеграция с Яндекс.Вебмастер через общий сервис-клиент.
    """

    def __init__(self, client: Optional[YandexWebmasterClient] = None) -> None:
        self.client = client or get_yandex_webmaster_client()

    def remove_url_from_search(self, url: str) -> Dict[str, Any]:
        """
        Добавляет URL в очередь переобхода Яндекс.Вебмастер.
        """
        return self.client.enqueue_recrawl(url)

    def get_404_urls(self) -> List[str]:
        """
        Возвращает список URL с ошибкой 404 из Яндекс.Вебмастер.
        """
        return self.client.fetch_404_urls()

