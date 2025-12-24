"""
Schema.org structured data (JSON-LD) генераторы
для SEO-оптимизации под Google Rich Results
"""
import json
from django.conf import settings
from django.utils.html import strip_tags


def generate_organization_schema():
    """
    Schema.org Organization для главной страницы
    Улучшает отображение в Knowledge Graph
    """
    return {
        "@context": "https://schema.org",
        "@type": "Organization",
        "name": "IdealImage.ru",
        "url": settings.SITE_URL,
        "logo": f"{settings.SITE_URL}/static/new/img/favicon/favicon-180x180.png",
        "description": "Блог о моде, красоте, здоровье и стиле жизни",
        "sameAs": [
            "https://t.me/ideal_image_ru",
            "https://dzen.ru/id/6030d91da3b2834e3d1872ce",
        ],
        "contactPoint": {
            "@type": "ContactPoint",
            "contactType": "customer service",
            "url": f"{settings.SITE_URL}/visitor/profile/",
        }
    }


def generate_website_schema():
    """
    Schema.org WebSite с SearchAction
    Добавляет поисковую строку в результаты Google
    """
    return {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": "IdealImage.ru",
        "url": settings.SITE_URL,
        "potentialAction": {
            "@type": "SearchAction",
            "target": {
                "@type": "EntryPoint",
                "urlTemplate": f"{settings.SITE_URL}/blog/?search={{search_term_string}}"
            },
            "query-input": "required name=search_term_string"
        }
    }


def generate_article_schema(post, request=None):
    """
    Schema.org Article для постов блога
    Улучшает отображение в Google News и поиске
    
    Args:
        post: Объект Post
        request: HTTP request (опционально)
    """
    # Базовые данные
    article_url = f"{settings.SITE_URL}{post.get_absolute_url()}"
    
    # Изображение
    if post.kartinka:
        image_url = f"{settings.SITE_URL}{post.kartinka.url}"
    else:
        # Fallback изображение
        image_url = f"{settings.SITE_URL}/static/new/img/favicon/favicon-180x180.png"
    
    # Описание
    description = post.description if post.description else strip_tags(post.content)[:300]
    
    # Автор
    author_name = post.author.get_full_name() if post.author else "IdealImage.ru"
    author_url = f"{settings.SITE_URL}/blog/author/{post.author.username}/" if post.author else settings.SITE_URL
    
    schema = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": post.title,
        "description": description,
        "image": image_url,
        "datePublished": post.created.isoformat(),
        "dateModified": post.updated.isoformat(),
        "author": {
            "@type": "Person",
            "name": author_name,
            "url": author_url
        },
        "publisher": {
            "@type": "Organization",
            "name": "IdealImage.ru",
            "logo": {
                "@type": "ImageObject",
                "url": f"{settings.SITE_URL}/static/new/img/favicon/favicon-180x180.png"
            }
        },
        "mainEntityOfPage": {
            "@type": "WebPage",
            "@id": article_url
        }
    }
    
    # Добавляем категорию как articleSection
    if post.category:
        schema["articleSection"] = post.category.title
    
    # Добавляем теги как keywords
    if post.tags.exists():
        schema["keywords"] = ", ".join([tag.name for tag in post.tags.all()])
    
    # Добавляем количество слов
    word_count = len(strip_tags(post.content).split())
    if word_count > 0:
        schema["wordCount"] = word_count
    
    return schema


def generate_breadcrumb_schema(breadcrumbs):
    """
    Schema.org BreadcrumbList для навигации
    Отображает хлебные крошки в результатах поиска
    
    Args:
        breadcrumbs: Список словарей [{'name': 'Главная', 'url': '/'}, ...]
    """
    items = []
    for index, crumb in enumerate(breadcrumbs, start=1):
        items.append({
            "@type": "ListItem",
            "position": index,
            "name": crumb['name'],
            "item": f"{settings.SITE_URL}{crumb['url']}" if crumb.get('url') else None
        })
    
    return {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": items
    }


def generate_person_schema(profile):
    """
    Schema.org Person для профилей авторов
    
    Args:
        profile: Объект Profile
    """
    user = profile.user
    
    schema = {
        "@context": "https://schema.org",
        "@type": "Person",
        "name": user.get_full_name() or user.username,
        "url": f"{settings.SITE_URL}/visitor/profile/{user.username}/",
    }
    
    # Добавляем аватар если есть
    if profile.avatar:
        schema["image"] = f"{settings.SITE_URL}{profile.avatar.url}"
    
    # Добавляем описание
    if profile.bio:
        schema["description"] = profile.bio
    
    # Добавляем социальные сети
    social_links = []
    if hasattr(profile, 'telegram') and profile.telegram:
        social_links.append(profile.telegram)
    if hasattr(profile, 'vk') and profile.vk:
        social_links.append(profile.vk)
    
    if social_links:
        schema["sameAs"] = social_links
    
    return schema


def generate_blog_posting_schema(post):
    """
    Schema.org BlogPosting (расширенная версия Article)
    Специально для блог-постов
    """
    schema = generate_article_schema(post)
    schema["@type"] = "BlogPosting"
    
    # Добавляем специфичные для блога поля
    if hasattr(post, 'views') and post.views:
        schema["interactionStatistic"] = {
            "@type": "InteractionCounter",
            "interactionType": "https://schema.org/ReadAction",
            "userInteractionCount": post.views
        }
    
    # Добавляем комментарии если есть
    if post.comments.exists():
        schema["commentCount"] = post.comments.count()
        schema["comment"] = [{
            "@type": "Comment",
            "author": {
                "@type": "Person",
                "name": comment.author.get_full_name() or comment.author.username
            },
            "dateCreated": comment.created.isoformat(),
            "text": strip_tags(comment.content)[:200]
        } for comment in post.comments.all()[:5]]  # Первые 5 комментариев
    
    return schema


def generate_faq_schema(questions):
    """
    Schema.org FAQPage для страниц с вопросами-ответами
    
    Args:
        questions: Список словарей [{'question': '...', 'answer': '...'}, ...]
    """
    return {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [{
            "@type": "Question",
            "name": q['question'],
            "acceptedAnswer": {
                "@type": "Answer",
                "text": q['answer']
            }
        } for q in questions]
    }


def schema_to_json(schema_dict):
    """
    Конвертирует словарь Schema.org в JSON-LD строку
    
    Args:
        schema_dict: Словарь с данными Schema.org
    
    Returns:
        JSON-LD строка для вставки в <script type="application/ld+json">
    """
    return json.dumps(schema_dict, ensure_ascii=False, indent=2)

