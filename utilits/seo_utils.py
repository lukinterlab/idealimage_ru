"""
SEO утилиты для генерации мета-тегов и структурированных данных
"""
import re
from django.utils.html import strip_tags
from django.utils.text import Truncator
from django.conf import settings


def generate_meta_description(content, max_length=160, post=None):
    """
    Генерирует мета-описание из контента
    Приоритет: post.meta_description > content
    
    Args:
        content: Контент статьи
        max_length: Максимальная длина
        post: Объект статьи (опционально)
    """
    # Приоритет 1: Используем AI-сгенерированное описание если есть
    if post and hasattr(post, 'meta_description') and post.meta_description:
        return post.meta_description[:max_length]
    
    # Приоритет 2: Генерируем из контента
    if not content:
        return "Читайте интересные статьи о моде, красоте и здоровье на IdealImage.ru"
    
    # Убираем HTML теги
    clean_content = strip_tags(content)
    
    # Убираем лишние пробелы и переносы строк
    clean_content = re.sub(r'\s+', ' ', clean_content).strip()
    
    # Обрезаем до нужной длины
    if len(clean_content) <= max_length:
        return clean_content
    
    # Ищем последний пробел перед лимитом
    truncated = Truncator(clean_content).chars(max_length - 3)
    last_space = truncated.rfind(' ')
    
    if last_space > max_length * 0.8:  # Если пробел не слишком далеко
        return truncated[:last_space] + '...'
    
    return truncated + '...'


def generate_meta_keywords(post):
    """
    Генерирует ключевые слова для статьи
    Приоритет: post.focus_keyword > tags > category
    """
    keywords = []
    
    # Приоритет 1: AI-выбранное главное ключевое слово
    if hasattr(post, 'focus_keyword') and post.focus_keyword:
        keywords.append(post.focus_keyword)
    
    # Приоритет 2: Теги статьи
    if hasattr(post, 'tags') and post.tags.exists():
        keywords.extend([tag.name for tag in post.tags.all()[:5]])
    
    # Приоритет 3: Категория
    if hasattr(post, 'category') and post.category:
        keywords.append(post.category.title)
    
    # Добавляем базовые ключевые слова если места еще есть
    base_keywords = ['мода', 'красота', 'здоровье', 'стиль', 'идеальный образ']
    for keyword in base_keywords:
        if len(keywords) < 10 and keyword not in keywords:
            keywords.append(keyword)
    
    return ', '.join(keywords[:10])  # Максимум 10 ключевых слов


def get_og_image(post):
    """
    Получает изображение для Open Graph
    Приоритет: og_preview > kartinka > дефолтное изображение
    """
    # Приоритет 1: OG-превью (оптимизированное для соцсетей)
    if post and hasattr(post, 'og_preview') and post.og_preview:
        return f"{settings.SITE_URL}{post.og_preview.url}"
    
    # Приоритет 2: Основное изображение
    if post and hasattr(post, 'kartinka') and post.kartinka:
        # Проверяем что это не видео
        if not any(post.kartinka.name.lower().endswith(ext) for ext in ['.mp4', '.webm', '.mov', '.avi']):
            return f"{settings.SITE_URL}{post.kartinka.url}"
    
    # Дефолтное изображение
    return f"{settings.SITE_URL}/static/new/img/logo/11.jpg"


def generate_canonical_url(request, post=None):
    """
    Генерирует канонический URL
    """
    if post and hasattr(post, 'get_absolute_url'):
        return f"{settings.SITE_URL}{post.get_absolute_url()}"
    
    return f"{settings.SITE_URL}{request.path}"


def get_article_structured_data(post):
    """
    Генерирует структурированные данные для статьи в формате JSON-LD
    Использует AI-сгенерированные SEO данные если доступны
    Теперь с детальными схемами Person (автор) и Organization (издатель)
    """
    from django.utils import timezone
    
    # Используем AI-сгенерированные данные если есть
    title = getattr(post, 'meta_title', None) or post.title
    description = generate_meta_description(post.description or post.content, post=post)
    
    # Получаем детальную информацию об авторе
    author_data = get_person_structured_data(post.author)
    # Убираем @context из автора, т.к. он уже есть в родительском объекте
    if author_data and "@context" in author_data:
        del author_data["@context"]
    
    # Получаем детальную информацию об организации (издателе)
    publisher_data = get_organization_structured_data()
    # Убираем @context из издателя
    if publisher_data and "@context" in publisher_data:
        del publisher_data["@context"]
    
    structured_data = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": title,
        "description": description,
        "image": get_og_image(post),
        "datePublished": post.created.isoformat(),
        "dateModified": post.updated.isoformat(),
        "author": author_data or {
            "@type": "Person",
            "name": post.author.get_full_name() or post.author.username
        },
        "publisher": publisher_data or {
            "@type": "Organization",
            "name": "IdealImage.ru",
            "logo": {
                "@type": "ImageObject",
                "url": f"{settings.SITE_URL}/static/new/img/logo/11.jpg"
            }
        },
        "mainEntityOfPage": {
            "@type": "WebPage",
            "@id": f"{settings.SITE_URL}{post.get_absolute_url()}"
        }
    }
    
    # Добавляем видео если есть
    if hasattr(post, 'video_url') and post.video_url:
        video_data = get_video_structured_data(post)
        if video_data and "@context" in video_data:
            del video_data["@context"]
        structured_data["video"] = video_data
    
    # Добавляем рейтинг на основе лайков и реальных оценок
    if hasattr(post, 'get_average_rating') and hasattr(post, 'get_ratings_count'):
        avg_rating = post.get_average_rating()
        ratings_count = post.get_ratings_count()
        if ratings_count > 0 and avg_rating > 0:
            structured_data["aggregateRating"] = {
                "@type": "AggregateRating",
                "ratingValue": avg_rating,
                "ratingCount": ratings_count,
                "bestRating": 5,
                "worstRating": 1
            }
    elif hasattr(post, 'get_likes_count'):
        # Fallback: используем лайки если нет рейтингов
        likes_count = post.get_likes_count()
        if likes_count > 0:
            # Простая формула: лайки влияют на рейтинг
            rating = min(5.0, 3.0 + (likes_count / 20))  # От 3.0 до 5.0
            structured_data["aggregateRating"] = {
                "@type": "AggregateRating",
                "ratingValue": round(rating, 1),
                "ratingCount": likes_count,
                "bestRating": 5,
                "worstRating": 1
            }
    
    # Добавляем взаимодействие (engagement)
    if hasattr(post, 'views') and post.views > 0:
        structured_data["interactionStatistic"] = {
            "@type": "InteractionCounter",
            "interactionType": "https://schema.org/ReadAction",
            "userInteractionCount": post.views
        }
    
    # Добавляем комментарии (если есть)
    if hasattr(post, 'comments'):
        comments_count = post.comments.filter(active=True).count() if hasattr(post.comments, 'filter') else 0
        if comments_count > 0:
            structured_data["commentCount"] = comments_count
    
    # Добавляем категорию если есть
    if hasattr(post, 'category') and post.category:
        structured_data["articleSection"] = post.category.title
    
    # Добавляем ключевые слова
    structured_data["keywords"] = generate_meta_keywords(post)
    
    # Добавляем язык статьи
    structured_data["inLanguage"] = "ru-RU"
    
    return structured_data


def get_video_structured_data(post):
    """
    Генерирует VideoObject structured data для статей с видео
    
    Args:
        post: Объект статьи с video_url
    
    Returns:
        Dict с VideoObject schema
    """
    if not hasattr(post, 'video_url') or not post.video_url:
        return None
    
    return {
        "@context": "https://schema.org",
        "@type": "VideoObject",
        "name": post.title,
        "description": post.description or generate_meta_description(post.content, post=post),
        "thumbnailUrl": get_og_image(post),
        "contentUrl": post.video_url,
        "embedUrl": post.video_url,
        "uploadDate": post.created.isoformat(),
        "duration": "PT5M",  # Примерная длительность, можно добавить поле в модель
    }


def get_website_structured_data():
    """
    Генерирует структурированные данные для сайта
    """
    return {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": "IdealImage.ru",
        "description": "Журнал о моде, красоте и здоровье. Советы по стилю, уходу за собой и здоровому образу жизни.",
        "url": settings.SITE_URL,
        "potentialAction": {
            "@type": "SearchAction",
            "target": f"{settings.SITE_URL}/search/?query={{search_term_string}}",
            "query-input": "required name=search_term_string"
        }
    }


def get_breadcrumb_structured_data(breadcrumbs):
    """
    Генерирует структурированные данные для хлебных крошек
    """
    if not breadcrumbs:
        return None
    
    structured_data = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": []
    }
    
    for i, (name, url) in enumerate(breadcrumbs, 1):
        structured_data["itemListElement"].append({
            "@type": "ListItem",
            "position": i,
            "name": name,
            "item": f"{settings.SITE_URL}{url}"
        })
    
    return structured_data


def get_person_structured_data(author):
    """
    Генерирует детальные структурированные данные для автора (Person schema)
    
    Args:
        author: Объект User (автор статьи)
    
    Returns:
        Dict с Person schema или None
    """
    if not author:
        return None
    
    person_data = {
        "@context": "https://schema.org",
        "@type": "Person",
        "name": author.get_full_name() or author.username,
    }
    
    # Добавляем URL профиля автора
    if hasattr(author, 'profile'):
        profile = author.profile
        person_data["url"] = f"{settings.SITE_URL}/visitor/profile/{profile.slug}/"
        
        # Добавляем изображение (аватар)
        if hasattr(profile, 'avatar') and profile.avatar:
            person_data["image"] = {
                "@type": "ImageObject",
                "url": f"{settings.SITE_URL}{profile.avatar.url}",
                "caption": f"Фото автора {author.get_full_name() or author.username}"
            }
        
        # Добавляем описание (биография)
        if hasattr(profile, 'bio') and profile.bio:
            person_data["description"] = profile.bio[:200]
        
        # Добавляем специализацию
        if hasattr(profile, 'spez') and profile.spez:
            person_data["jobTitle"] = profile.spez
        
        # Добавляем социальные сети
        social_profiles = []
        if hasattr(profile, 'telegram') and profile.telegram:
            social_profiles.append(f"https://t.me/{profile.telegram.lstrip('@')}")
        if hasattr(profile, 'vk') and profile.vk:
            social_profiles.append(profile.vk)
        if hasattr(profile, 'instagram') and profile.instagram:
            social_profiles.append(f"https://instagram.com/{profile.instagram.lstrip('@')}")
        
        if social_profiles:
            person_data["sameAs"] = social_profiles
    else:
        person_data["url"] = f"{settings.SITE_URL}/author/{author.username}/"
    
    # Добавляем email (если публичный)
    if author.email and not author.email.endswith('@idealimage.ru'):
        person_data["email"] = author.email
    
    return person_data


def get_organization_structured_data():
    """
    Генерирует детальные структурированные данные для организации (сайта)
    Organization schema для IdealImage.ru
    
    Returns:
        Dict с Organization schema
    """
    organization_data = {
        "@context": "https://schema.org",
        "@type": "Organization",
        "name": "IdealImage.ru",
        "alternateName": "Идеальный Образ",
        "url": settings.SITE_URL,
        "logo": {
            "@type": "ImageObject",
            "url": f"{settings.SITE_URL}/static/new/img/logo/11.jpg",
            "width": 600,
            "height": 60
        },
        "description": "Онлайн журнал о моде, красоте и здоровье. Экспертные советы по стилю, уходу за собой, макияжу, прическам и здоровому образу жизни.",
        "foundingDate": "2020",
        "slogan": "Ваш гид в мире моды и красоты",
        
        # Контактная информация
        "contactPoint": {
            "@type": "ContactPoint",
            "contactType": "customer support",
            "email": "idealimage.orel@gmail.com",
            "availableLanguage": ["Russian"]
        },
        
        # Социальные сети
        "sameAs": [
            "https://t.me/ideal_image_ru",
            "https://t.me/fizkult_hello_beauty",
            "https://t.me/eat_love_live",
            "https://t.me/the_best_hairstyles",
            "https://t.me/KOSICHKI_GIRLS",
            "https://t.me/Fashion_Couture_ru"
        ],
        
        # Области деятельности
        "areaServed": "RU",
        "knowsAbout": [
            "Мода",
            "Красота",
            "Здоровье",
            "Макияж",
            "Прически",
            "Стиль",
            "Уход за собой"
        ]
    }
    
    return organization_data


def get_webpage_structured_data(page_title, page_description, page_url, breadcrumbs=None):
    """
    Генерирует структурированные данные для веб-страницы (WebPage schema)
    
    Args:
        page_title: Заголовок страницы
        page_description: Описание страницы
        page_url: URL страницы
        breadcrumbs: Хлебные крошки (опционально)
    
    Returns:
        Dict с WebPage schema
    """
    webpage_data = {
        "@context": "https://schema.org",
        "@type": "WebPage",
        "name": page_title,
        "description": page_description,
        "url": page_url,
        "inLanguage": "ru-RU",
        "isPartOf": {
            "@type": "WebSite",
            "name": "IdealImage.ru",
            "url": settings.SITE_URL
        }
    }
    
    # Добавляем breadcrumbs если есть
    if breadcrumbs:
        webpage_data["breadcrumb"] = {
            "@type": "BreadcrumbList",
            "itemListElement": [
                {
                    "@type": "ListItem",
                    "position": i,
                    "name": name,
                    "item": f"{settings.SITE_URL}{url}"
                }
                for i, (name, url) in enumerate(breadcrumbs, 1)
            ]
        }
    
    return webpage_data