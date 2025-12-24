"""
Кастомный sitemap view с поддержкой Google Image Sitemap
Включает кэширование для оптимальной производительности
"""
from django.http import HttpResponse, Http404
from django.template import loader
from django.contrib.sites.shortcuts import get_current_site
from django.core.cache import cache
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


def image_sitemap(request, sitemaps, section=None):
    """
    Sitemap view с поддержкой image:image тегов для Google Images
    С кэшированием на 1 час для production
    """
    # Пытаемся получить из кэша (только в production)
    cache_key = f"sitemap_image_{section if section else 'all'}"
    if not settings.DEBUG:
        cached_response = cache.get(cache_key)
        if cached_response:
            return cached_response
    
    if section is not None:
        if section not in sitemaps:
            raise Http404("No sitemap available for section: %r" % section)
        maps = [sitemaps[section]]
    else:
        maps = sitemaps.values()
    
    urls = []
    
    for site_class in maps:
        try:
            # Инициализируем класс sitemap
            if callable(site_class):
                site = site_class()
            else:
                site = site_class
            
            # Получаем все items из sitemap
            items = site.items()
            
            # Получаем protocol и domain
            protocol = site.get_protocol() if hasattr(site, 'get_protocol') else 'https'
            current_site = get_current_site(request)
            domain = current_site.domain
            
            for item in items:
                # Получаем location для item
                if hasattr(site, 'location'):
                    location_path = site.location(item)
                else:
                    location_path = item.get_absolute_url() if hasattr(item, 'get_absolute_url') else str(item)
                
                loc = f"{protocol}://{domain}{location_path}"
                
                def resolve_attr(obj, name):
                    if not hasattr(obj, name):
                        return None
                    attr = getattr(obj, name)
                    try:
                        return attr(item) if callable(attr) else attr
                    except TypeError:
                        logger.warning("Sitemap attribute %s raised TypeError for %s", name, item, exc_info=True)
                        return None

                lastmod = resolve_attr(site, 'lastmod')
                changefreq = resolve_attr(site, 'changefreq')
                priority = resolve_attr(site, 'priority')

                # Нормализуем значения changefreq и priority
                if callable(changefreq):
                    try:
                        changefreq = changefreq(item)
                    except TypeError:
                        logger.warning("Callable changefreq failed for %s", item, exc_info=True)
                        changefreq = None

                if callable(priority):
                    try:
                        priority = priority(item)
                    except TypeError:
                        logger.warning("Callable priority failed for %s", item, exc_info=True)
                        priority = None

                # Приводим priority к строке, если это число
                if priority is not None:
                    try:
                        priority = "{0:.1f}".format(float(priority))
                    except (TypeError, ValueError):
                        priority = str(priority)

                url_info = {
                    'item': item,
                    'location': loc,
                    'lastmod': lastmod,
                    'changefreq': changefreq,
                    'priority': str(priority) if priority is not None else None,
                }
                
                # Добавляем изображения если метод images() существует
                if hasattr(site, 'images'):
                    try:
                        images = site.images(item)
                        if images:
                            url_info['images'] = images
                    except Exception as e:
                        logger.warning(f"Error getting images for {loc}: {e}")
                
                urls.append(url_info)
                
        except Exception as e:
            logger.error(f"Error processing sitemap {site.__class__.__name__}: {e}", exc_info=True)
            continue
    
    # Используем кастомный template
    template = loader.get_template('sitemap.xml')
    context = {
        'urlset': urls,
    }
    
    response = HttpResponse(template.render(context, request), content_type='application/xml; charset=utf-8')
    
    # Кэшируем на 1 час в production
    # Для очистки кэша после публикации новой статьи используйте:
    # from django.core.cache import cache
    # cache.delete('sitemap_image_all')
    if not settings.DEBUG:
        cache.set(cache_key, response, 3600)  # 3600 секунд = 1 час
    
    return response

