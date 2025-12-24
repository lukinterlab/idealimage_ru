"""
Middleware для 301 редиректов старых категорий после миграций
"""

from django.http import HttpResponsePermanentRedirect


class CategoryRedirectMiddleware:
    """
    301 редиректы для старых URL категорий после миграций
    
    Использование: добавить в settings.py MIDDLEWARE:
    'blog.middleware.CategoryRedirectMiddleware',
    """
    
    # Словарь редиректов: старый_url -> новый_url
    # Основан на миграциях категорий от 15.10.2025
    REDIRECTS = {
        # Миграция 1 и 2 → ИДЕАЛЬНЫЙ ОБРАЗ (ID=2, slug: idealnyj-obraz)
        '/blog/category/bezuprechnyj-mejk/': '/blog/category/idealnyj-obraz/',
        '/blog/category/bezuprechnyj-meik/': '/blog/category/idealnyj-obraz/',
        '/blog/category/shikarnaya-prichyoska/': '/blog/category/idealnyj-obraz/',
        '/blog/category/shikarnaya-prichjoska/': '/blog/category/idealnyj-obraz/',
        
        # Миграция 3 и 4 → ПСИХОЛОГИЯ (ID=14, slug: chto-to-pro-psihologiyu)
        '/blog/category/psihologiya-39/': '/blog/category/chto-to-pro-psihologiyu/',
        '/blog/category/psihologiya-duplicate/': '/blog/category/chto-to-pro-psihologiyu/',
        '/blog/category/studencheskaya-magiya/': '/blog/category/chto-to-pro-psihologiyu/',
        '/blog/category/studenchiskaya-magiya/': '/blog/category/chto-to-pro-psihologiyu/',
        
        # Миграция 5, 6, 8 → Малыши и Мамы (ID=38, slug: malyishi-i-mamyi)
        '/blog/category/ya-mamochka/': '/blog/category/malyishi-i-mamyi/',
        '/blog/category/ja-mamochka/': '/blog/category/malyishi-i-mamyi/',
        '/blog/category/devochki-kosichki/': '/blog/category/malyishi-i-mamyi/',
        '/blog/category/lapochki-malyshki/': '/blog/category/malyishi-i-mamyi/',
        '/blog/category/lapochki-malyishki/': '/blog/category/malyishi-i-mamyi/',
        
        # Миграция 7 → ЕШЬ ЛЮБИ МОЛИСЬ (ID=3, slug: esh-zhivi-lyubi-molis)
        '/blog/category/lakomka/': '/blog/category/esh-zhivi-lyubi-molis/',
        
        # Миграция 9 и 10 → Интеллектуальные Прогнозы (ID=37, slug: predskazaniya)
        '/blog/category/taro-karty-v-zhizni/': '/blog/category/predskazaniya/',
        '/blog/category/taro-karty/': '/blog/category/predskazaniya/',
        '/blog/category/matrica-sudby/': '/blog/category/predskazaniya/',
        '/blog/category/matritsa-sudby/': '/blog/category/predskazaniya/',
    }
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        """
        Проверяет запрошенный путь и выполняет 301 редирект если нужно
        """
        # Нормализуем путь (убираем trailing slash для проверки)
        path = request.path.rstrip('/')
        path_with_slash = path + '/'
        
        # Проверяем оба варианта (с и без trailing slash)
        if path in self.REDIRECTS:
            return HttpResponsePermanentRedirect(self.REDIRECTS[path])
        elif path_with_slash in self.REDIRECTS:
            return HttpResponsePermanentRedirect(self.REDIRECTS[path_with_slash])
        
        response = self.get_response(request)
        return response

