from django.contrib.auth.mixins import AccessMixin
from django.contrib import messages
from django.shortcuts import redirect
from django.core.cache import cache
from utilits.seo_utils import (
    generate_meta_description, generate_meta_keywords, get_og_image,
    generate_canonical_url, get_article_structured_data, get_website_structured_data
)
import json


class AuthorRequiredMixin(AccessMixin):
    """Доступ только для автора статьи"""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        
        post = self.get_object()
        
        # Проверяем права: автор статьи ИЛИ суперюзер
        if request.user != post.author and not request.user.is_superuser:
            messages.error(request, 'У вас нет прав для изменения этой статьи')
            return redirect('blog:blog')
        
        return super().dispatch(request, *args, **kwargs)


class AuthorOrModeratorMixin(AccessMixin):
    """Доступ для автора, модератора или суперюзера"""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        
        post = self.get_object()
        
        # Проверяем права:
        # - Автор статьи
        # - Модератор (если есть профиль)
        # - Суперюзер
        is_author = request.user == post.author
        is_moderator = hasattr(request.user, 'profile') and request.user.profile.is_moderator
        is_superuser = request.user.is_superuser
        
        if not (is_author or is_moderator or is_superuser):
            messages.error(request, 'У вас нет прав для этого действия')
            return redirect('blog:blog')
        
        return super().dispatch(request, *args, **kwargs)


class SEOContextMixin:
    """
    Миксин для добавления SEO-контекста во view
    Упрощает добавление мета-тегов и structured data
    """
    def get_seo_context(self, obj=None):
        """
        Генерирует SEO-контекст для объекта
        
        Args:
            obj: Объект статьи или None для общих страниц
        
        Returns:
            Dict с SEO данными
        """
        context = {}
        
        if obj:
            # SEO для конкретной статьи
            context['page_title'] = getattr(obj, 'meta_title', None) or obj.title
            context['page_description'] = generate_meta_description(
                obj.description or obj.content if hasattr(obj, 'content') else '',
                post=obj
            )
            context['meta_keywords'] = generate_meta_keywords(obj)
            context['canonical_url'] = generate_canonical_url(self.request, obj)
            context['og_image'] = get_og_image(obj)
            context['og_title'] = getattr(obj, 'og_title', None) or context['page_title']
            context['og_description'] = getattr(obj, 'og_description', None) or context['page_description']
            context['structured_data'] = json.dumps(get_article_structured_data(obj), ensure_ascii=False)
        else:
            # SEO для общих страниц (списки и т.д.)
            context['page_title'] = getattr(self, 'page_title', 'IdealImage.ru')
            context['page_description'] = getattr(self, 'page_description', 'Журнал о моде, красоте и здоровье')
            context['canonical_url'] = generate_canonical_url(self.request)
            context['og_image'] = get_og_image(None)
            context['structured_data'] = json.dumps(get_website_structured_data(), ensure_ascii=False)
        
        return context


class CacheMixin:
    """
    Миксин для удобного кэширования данных во views
    """
    cache_timeout = 300  # 5 минут по умолчанию
    
    def get_cached_data(self, cache_key, queryset_func, timeout=None):
        """
        Получает данные из кэша или выполняет запрос
        
        Args:
            cache_key: Ключ кэша
            queryset_func: Функция для получения данных если не в кэше
            timeout: Время жизни кэша (None = использовать self.cache_timeout)
        
        Returns:
            Данные из кэша или результат queryset_func
        
        Пример:
            categories = self.get_cached_data(
                'all_categories',
                lambda: Category.objects.all()
            )
        """
        timeout = timeout or self.cache_timeout
        
        data = cache.get(cache_key)
        if data is None:
            data = queryset_func()
            cache.set(cache_key, data, timeout)
        
        return data
    
    def invalidate_cache(self, *cache_keys):
        """
        Инвалидирует несколько ключей кэша
        
        Args:
            *cache_keys: Список ключей для удаления
        
        Пример:
            self.invalidate_cache('posts_list', 'authors_list')
        """
        if cache_keys:
            cache.delete_many(cache_keys)