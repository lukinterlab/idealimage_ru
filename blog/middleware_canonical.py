"""
Middleware для автоматического добавления canonical URL
и обработки GET-параметров
"""
import logging
from django.utils.deprecation import MiddlewareMixin
from django.http import HttpResponsePermanentRedirect

logger = logging.getLogger(__name__)


class CanonicalURLMiddleware(MiddlewareMixin):
    """
    Middleware для обработки canonical URLs и незначащих GET-параметров
    
    Действия:
    1. Удаляет незначащие GET-параметры с редиректом 301
    2. Добавляет canonical URL в контекст для шаблонов
    3. Логирует дубли страниц
    """
    
    # GET-параметры, которые не влияют на содержимое страницы
    INSIGNIFICANT_PARAMS = [
        'next',
        'from',
        'utm_source',
        'utm_medium', 
        'utm_campaign',
        'utm_content',
        'utm_term',
        'fbclid',
        'gclid',
        'yclid',
        '_openstat',
        'ref',
        'referer',
        'source',
    ]
    
    # Исключения - URL где GET-параметры значащие
    EXCLUDED_PATHS = [
        '/admin/',
        '/search/',
        '/api/',
        '/ckeditor/',
    ]
    
    def process_request(self, request):
        """
        Обработка входящего запроса
        
        Если есть незначащие GET-параметры - делаем 301 редирект на чистый URL
        """
        # Пропускаем исключённые пути
        for excluded in self.EXCLUDED_PATHS:
            if request.path.startswith(excluded):
                return None
        
        # Проверяем наличие незначащих параметров
        query_params = request.GET.copy()
        has_insignificant = False
        
        for param in self.INSIGNIFICANT_PARAMS:
            if param in query_params:
                has_insignificant = True
                del query_params[param]
        
        # Если были незначащие параметры - редирект
        if has_insignificant:
            canonical_url = request.path
            
            # Если остались значащие параметры - добавляем их
            if query_params:
                canonical_url += '?' + query_params.urlencode()
            
            logger.info(f"Canonical redirect: {request.get_full_path()} -> {canonical_url}")
            
            # 301 редирект на canonical URL
            return HttpResponsePermanentRedirect(canonical_url)
        
        return None
    
    def process_template_response(self, request, response):
        """
        Добавляем canonical URL в контекст для шаблонов
        """
        if hasattr(response, 'context_data'):
            # Формируем полный canonical URL
            canonical_path = request.path
            
            # Удаляем незначащие параметры из query string
            query_params = request.GET.copy()
            for param in self.INSIGNIFICANT_PARAMS:
                query_params.pop(param, None)
            
            if query_params:
                canonical_path += '?' + query_params.urlencode()
            
            # Полный URL с доменом
            from django.conf import settings
            site_url = getattr(settings, 'SITE_URL', 'https://idealimage.ru')
            canonical_url = site_url + canonical_path
            
            # Добавляем в контекст
            if response.context_data is None:
                response.context_data = {}
            
            response.context_data['canonical_url'] = canonical_url
        
        return response


class DuplicateURLDetector:
    """
    Детектор дублей URL для мониторинга
    """
    
    @staticmethod
    def detect_duplicates_in_database():
        """
        Поиск дублей в базе данных
        
        Returns:
            List словарей с информацией о дублях
        """
        from blog.models import Post
        from django.db.models import Count
        
        # Посты с одинаковыми slug (не должно быть, но проверяем)
        duplicate_slugs = Post.objects.values('slug').annotate(
            count=Count('id')
        ).filter(count__gt=1)
        
        duplicates = []
        for dup in duplicate_slugs:
            posts = Post.objects.filter(slug=dup['slug']).values(
                'id', 'title', 'slug', 'status', 'created'
            )
            duplicates.append({
                'slug': dup['slug'],
                'count': dup['count'],
                'posts': list(posts)
            })
        
        return duplicates
    
    @staticmethod
    def find_similar_urls(url):
        """
        Поиск похожих URL (возможных дублей)
        
        Args:
            url: URL для проверки
        
        Returns:
            List похожих URL
        """
        from blog.models import Post
        import re
        
        # Извлекаем slug из URL
        match = re.search(r'/post/([^/?]+)', url)
        if not match:
            return []
        
        slug = match.group(1)
        
        # Ищем посты с таким slug
        posts = Post.objects.filter(slug=slug)
        
        similar_urls = []
        for post in posts:
            similar_urls.append({
                'url': f"https://idealimage.ru{post.get_absolute_url()}",
                'title': post.title,
                'status': post.status
            })
        
        return similar_urls

