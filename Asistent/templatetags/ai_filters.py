"""
Template filters для AI-ассистента
"""
import re
from django import template
from django.utils.safestring import mark_safe
from django.urls import reverse

register = template.Library()


@register.filter(name='linkify_ai_message')
def linkify_ai_message(text):
    """
    Преобразует упоминания ID и названия в кликабельные ссылки
    
    Поддерживаемые паттерны:
    - post_id:123, comment_id:456, task_id:789, user_id:999
    - Автор: username → ссылка на профиль
    - Заголовок: название → подсветка
    - Категория: НАЗВАНИЕ → ссылка
    """
    if not text:
        return text
    
    result = text
    
    # ========================================================================
    # ПРИОРИТЕТ 0: ЦЕЛЫЙ БЛОК МОДЕРАЦИИ (Заголовок + Автор + Категория)
    # Обрабатываем ОДНИМ ЗАПРОСОМ к БД!
    # ========================================================================
    
    def linkify_moderation_block(match):
        """
        SMART обработка целого блока модерации
        Находит статью по заголовку и подтягивает все ссылки из неё
        """
        title = match.group(1).strip()
        author_username = match.group(2).strip()
        category_name = match.group(3).strip()
        
        try:
            from blog.models import Post
            
            # Ищем статью по заголовку
            clean_title = re.sub(r'[#\*\[\]🌟⭐\-]+', ' ', title).strip()
            clean_title = re.sub(r'\s+', ' ', clean_title)
            
            post = Post.objects.select_related('author__profile', 'category').filter(
                title__iexact=clean_title
            ).first()
            
            if not post:
                post = Post.objects.select_related('author__profile', 'category').filter(
                    title__icontains=clean_title[:20]
                ).first()
            
            if post:
                # СТАТЬЯ НАЙДЕНА! Берём все данные из неё!
                
                # Ссылка на статью
                title_link = f'<a href="/post/{post.slug}/" class="text-blue-400 hover:text-blue-300 underline font-bold inline-block px-2 py-1 bg-blue-500/20 rounded" target="_blank" title="Открыть статью">{title} 🔗</a>'
                
                # Ссылка на автора (из статьи!)
                if hasattr(post.author, 'profile'):
                    author_slug = post.author.profile.slug
                    author_link = f'<a href="/visitor/user/{author_slug}/" class="text-cyan-400 hover:text-cyan-300 underline font-semibold inline-block px-2 py-1 bg-cyan-500/20 rounded" target="_blank" title="Профиль автора">✍️ {author_username} ↗</a>'
                else:
                    author_link = f'<a href="/author/{author_username}/" class="text-cyan-400 hover:text-cyan-300 underline font-semibold inline-block px-2 py-1 bg-cyan-500/20 rounded" target="_blank" title="Статьи автора">✍️ {author_username} ↗</a>'
                
                # Ссылка на категорию (из статьи!)
                if post.category:
                    category_link = f'<a href="/category/{post.category.slug}/" class="text-purple-400 hover:text-purple-300 underline font-semibold inline-block px-2 py-1 bg-purple-500/20 rounded" target="_blank" title="Статьи категории">📂 {category_name} ↗</a>'
                else:
                    category_link = f'<span class="text-purple-300 font-semibold">{category_name}</span>'
                
                return f'Заголовок: {title_link}\nАвтор: {author_link}\nКатегория: {category_link}'
            
        except Exception as e:
            pass
        
        # Fallback - обрабатываем по отдельности (будет позже)
        return match.group(0)
    
    # Паттерн для блока: Заголовок + Автор + Категория (все вместе!)
    result = re.sub(
        r'Заголовок:\s+([^\n]+)\n\s*Автор:\s+([A-Za-z0-9_]+)\n\s*Категория:\s+([А-ЯЁA-Z][А-ЯЁA-Z\s]+)',
        linkify_moderation_block,
        result,
        flags=re.MULTILINE
    )
    
    # ========================================================================
    # ID в формате "entity_id:123" (на отдельной строке)
    # ========================================================================
    
    # Post ID в формате post_id:123 → прямая ссылка на публичную страницу
    def replace_post_id(match):
        post_id = match.group(1)
        try:
            from blog.models import Post
            post = Post.objects.filter(id=post_id).first()
            if post:
                return f'   <a href="/post/{post.slug}/" class="text-blue-400 hover:text-blue-300 underline font-semibold inline-block px-3 py-1 bg-blue-500/20 rounded" target="_blank" title="Открыть статью на сайте">📄 Статья: {post.title[:30]} ↗</a>'
            else:
                return f'   <span class="text-gray-400">post_id:{post_id} (не найдена)</span>'
        except:
            return f'   <a href="/admin/blog/post/{post_id}/change/" class="text-blue-400 hover:text-blue-300 underline font-semibold inline-block px-3 py-1 bg-blue-500/20 rounded" target="_blank" title="Открыть в админке">📄 Статья #{post_id} ↗</a>'
    
    result = re.sub(
        r'^\s*post_id[:：]\s*(\d+)\s*$',
        replace_post_id,
        result,
        flags=re.IGNORECASE | re.MULTILINE
    )
    
    # Comment ID
    result = re.sub(
        r'^\s*comment_id[:：]\s*(\d+)\s*$',
        r'   <a href="/admin/blog/comment/\1/change/" class="text-green-400 hover:text-green-300 underline font-semibold inline-block px-3 py-1 bg-green-500/20 rounded" target="_blank" title="Открыть комментарий">💬 Комментарий #\1 ↗</a>',
        result,
        flags=re.IGNORECASE | re.MULTILINE
    )
    
    # Task ID
    result = re.sub(
        r'^\s*task_id[:：]\s*(\d+)\s*$',
        r'   <a href="/asistent/admin-panel/content-task/\1/" class="text-purple-400 hover:text-purple-300 underline font-semibold inline-block px-3 py-1 bg-purple-500/20 rounded" target="_blank" title="Открыть задание">📋 Задание #\1 ↗</a>',
        result,
        flags=re.IGNORECASE | re.MULTILINE
    )
    
    # User ID
    result = re.sub(
        r'^\s*user_id[:：]\s*(\d+)\s*$',
        r'   <a href="/admin/auth/user/\1/change/" class="text-yellow-400 hover:text-yellow-300 underline font-semibold inline-block px-3 py-1 bg-yellow-500/20 rounded" target="_blank" title="Открыть пользователя">👤 Пользователь #\1 ↗</a>',
        result,
        flags=re.IGNORECASE | re.MULTILINE
    )
    
    # ========================================================================
    # ОТДЕЛЬНЫЕ ОБРАБОТКИ (только если НЕ в блоке модерации!)
    # ========================================================================
    
    # ПРИМЕЧАНИЕ: Если Заголовок/Автор/Категория уже обработаны в блоке модерации,
    # то эти паттерны их НЕ заменят (проверка на наличие <a href=)
    
    # Автор (только если ещё НЕ ссылка!)
    def linkify_author_standalone(match):
        """Обрабатывает автора только если он ещё НЕ ссылка"""
        full_match = match.group(0)
        # Если уже есть <a href= значит обработан в блоке
        if '<a href=' in full_match:
            return full_match
        
        username = match.group(1)
        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            user = User.objects.filter(username=username).first()
            
            if user and hasattr(user, 'profile'):
                profile_slug = user.profile.slug
                return f'Автор: <a href="/visitor/user/{profile_slug}/" class="text-cyan-400 hover:text-cyan-300 underline font-semibold inline-block px-2 py-1 bg-cyan-500/20 rounded" target="_blank" title="Профиль автора">✍️ {username} ↗</a>'
            else:
                return f'Автор: <a href="/author/{username}/" class="text-cyan-400 hover:text-cyan-300 underline font-semibold inline-block px-2 py-1 bg-cyan-500/20 rounded" target="_blank" title="Статьи автора">✍️ {username} ↗</a>'
        except:
            return f'Автор: <a href="/author/{username}/" class="text-cyan-400 hover:text-cyan-300 underline font-semibold inline-block px-2 py-1 bg-cyan-500/20 rounded" target="_blank" title="Статьи автора">✍️ {username} ↗</a>'
    
    # Применяем только к строкам без <a href=
    if '<a href=' not in result or result.count('Автор:') > result.count('Автор: <a href='):
        result = re.sub(
            r'Автор:\s+([A-Za-z0-9_]+)(?!\s*↗)',
            linkify_author_standalone,
            result
        )
    
    # Заголовок (только если ещё НЕ ссылка!)
    def linkify_title_standalone(match):
        """Обрабатывает заголовок только если он ещё НЕ ссылка"""
        full_match = match.group(0)
        if '<a href=' in full_match:
            return full_match
        
        title = match.group(1).strip()
        try:
            from blog.models import Post
            clean_title = re.sub(r'[#\*\[\]🌟⭐\-]+', ' ', title).strip()
            clean_title = re.sub(r'\s+', ' ', clean_title)
            
            post = Post.objects.filter(title__iexact=clean_title).first()
            if not post:
                post = Post.objects.filter(title__icontains=clean_title[:20]).first()
            
            if post:
                return f'Заголовок: <a href="/post/{post.slug}/" class="text-blue-400 hover:text-blue-300 underline font-bold inline-block px-2 py-1 bg-blue-500/20 rounded" target="_blank" title="Открыть статью">{title} 🔗</a>'
            else:
                return f'Заголовок: <span class="text-blue-300 font-bold">{title}</span>'
        except:
            return f'Заголовок: <span class="text-blue-300 font-bold">{title}</span>'
    
    if '<a href=' not in result or result.count('Заголовок:') > result.count('Заголовок: <a href='):
        result = re.sub(
            r'Заголовок:\s+([^\n]+)(?!\s*🔗)',
            linkify_title_standalone,
            result
        )
    
    # Категория (только если ещё НЕ ссылка!)
    def linkify_category_standalone(match):
        """Обрабатывает категорию только если она ещё НЕ ссылка"""
        full_match = match.group(0)
        if '<a href=' in full_match:
            return full_match
        
        category_name = match.group(1).strip()
        try:
            from blog.models import Category
            category = Category.objects.filter(title__iexact=category_name).first()
            if not category:
                category = Category.objects.filter(title__icontains=category_name[:15]).first()
            
            if category:
                return f'Категория: <a href="/category/{category.slug}/" class="text-purple-400 hover:text-purple-300 underline font-semibold inline-block px-2 py-1 bg-purple-500/20 rounded" target="_blank" title="Статьи категории">📂 {category_name} ↗</a>'
            else:
                return f'Категория: <span class="text-purple-300 font-semibold">{category_name}</span>'
        except:
            return f'Категория: <span class="text-purple-300 font-semibold">{category_name}</span>'
    
    if '<a href=' not in result or result.count('Категория:') > result.count('Категория: <a href='):
        result = re.sub(
            r'Категория:\s+([А-ЯЁA-Z][А-ЯЁA-Z\s]+?)(?=\n|$)(?!\s*↗)',
            linkify_category_standalone,
            result
        )
    
    # ========================================================================
    # СТАТУС: Запрашиваемый статус / статус публикации
    # ========================================================================
    
    # Подсвечиваем статусы
    result = re.sub(
        r'(?:статус|Статус):\s+(published|draft|pending|moderation)',
        lambda m: f'Статус: <span class="px-2 py-1 rounded bg-{"green" if m.group(1) == "published" else "yellow"}-500/30 text-{"green" if m.group(1) == "published" else "yellow"}-300 font-semibold">{m.group(1).upper()}</span>',
        result,
        flags=re.IGNORECASE
    )
    
    # ========================================================================
    # URL в сообщениях
    # ========================================================================
    
    # Преобразуем прямые URL в ссылки
    url_pattern = re.compile(r'(?<!href=")(https?://[^\s<>"]+)')
    result = url_pattern.sub(r'<a href="\1" class="text-blue-400 hover:text-blue-300 underline break-all" target="_blank">🔗 \1 ↗</a>', result)
    
    return mark_safe(result)


@register.filter(name='highlight_keywords')
def highlight_keywords(text, keywords):
    """
    Подсвечивает ключевые слова в тексте
    """
    if not text or not keywords:
        return text
    
    keywords_list = keywords.split(',')
    result = text
    
    for keyword in keywords_list:
        keyword = keyword.strip()
        if keyword:
            pattern = re.compile(f'({re.escape(keyword)})', re.IGNORECASE)
            result = pattern.sub(r'<span class="bg-yellow-500/30 text-yellow-200 px-1 rounded">\1</span>', result)
    
    return mark_safe(result)


@register.filter(name='format_ai_role')
def format_ai_role(role):
    """
    Форматирует роль AI для отображения
    """
    roles = {
        'user': 'Пользователь',
        'assistant': 'AI-Ассистент',
        'system': 'Система',
        'function': 'Функция',
    }
    return roles.get(role, role.title())


@register.filter(name='truncate_middle')
def truncate_middle(text, max_length=50):
    """
    Обрезает текст посередине (для длинных путей/ID)
    """
    if not text or len(text) <= max_length:
        return text
    
    half = max_length // 2 - 2
    return f"{text[:half]}...{text[-half:]}"

