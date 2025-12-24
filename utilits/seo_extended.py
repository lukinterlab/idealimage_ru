"""
🚀 Расширенные Schema.org разметки для Rich Results Google
HowTo, Recipe, Review и другие продвинутые схемы
"""
import json
from django.conf import settings
from django.utils.html import strip_tags


def generate_howto_schema(title, description, steps, total_time=None):
    """
    Генерирует HowTo schema для инструкций
    
    Args:
        title: Заголовок инструкции
        description: Описание
        steps: Список шагов [{'name': '...', 'text': '...', 'image': '...'}, ...]
        total_time: Общее время выполнения (например, "PT30M")
    
    Returns:
        Dict с HowTo schema
    """
    schema = {
        "@context": "https://schema.org",
        "@type": "HowTo",
        "name": title,
        "description": description,
        "step": []
    }
    
    for i, step in enumerate(steps, 1):
        step_data = {
            "@type": "HowToStep",
            "position": i,
            "name": step.get('name', f'Шаг {i}'),
            "text": step.get('text', ''),
        }
        
        if step.get('image'):
            step_data["image"] = f"{settings.SITE_URL}{step['image']}"
        
        if step.get('url'):
            step_data["url"] = step['url']
        
        schema["step"].append(step_data)
    
    if total_time:
        schema["totalTime"] = total_time
    
    return schema


def generate_recipe_schema(recipe_name, description, ingredients, instructions, 
                           prep_time=None, cook_time=None, total_time=None,
                           recipe_yield=None, nutrition=None, image=None):
    """
    Генерирует Recipe schema для рецептов красоты/здоровья
    
    Args:
        recipe_name: Название рецепта
        description: Описание
        ingredients: Список ингредиентов ['ингредиент 1', 'ингредиент 2', ...]
        instructions: Список инструкций ['шаг 1', 'шаг 2', ...]
        prep_time: Время подготовки (например, "PT15M")
        cook_time: Время приготовления (например, "PT30M")
        total_time: Общее время (например, "PT45M")
        recipe_yield: Количество порций (например, "4 порции")
        nutrition: Dict с питательной ценностью
        image: URL изображения рецепта
    
    Returns:
        Dict с Recipe schema
    """
    schema = {
        "@context": "https://schema.org",
        "@type": "Recipe",
        "name": recipe_name,
        "description": description,
        "recipeIngredient": ingredients,
        "recipeInstructions": []
    }
    
    # Инструкции
    for i, instruction in enumerate(instructions, 1):
        schema["recipeInstructions"].append({
            "@type": "HowToStep",
            "position": i,
            "text": instruction
        })
    
    # Время
    if prep_time:
        schema["prepTime"] = prep_time
    if cook_time:
        schema["cookTime"] = cook_time
    if total_time:
        schema["totalTime"] = total_time
    
    # Количество порций
    if recipe_yield:
        schema["recipeYield"] = recipe_yield
    
    # Изображение
    if image:
        if not image.startswith('http'):
            image = f"{settings.SITE_URL}{image}"
        schema["image"] = image
    
    # Питательная ценность
    if nutrition:
        schema["nutrition"] = {
            "@type": "NutritionInformation",
            **nutrition
        }
    
    # Автор и издатель
    schema["author"] = {
        "@type": "Organization",
        "name": "IdealImage.ru"
    }
    
    schema["publisher"] = {
        "@type": "Organization",
        "name": "IdealImage.ru",
        "logo": {
            "@type": "ImageObject",
            "url": f"{settings.SITE_URL}/static/new/img/logo/11.jpg"
        }
    }
    
    return schema


def generate_review_schema(item_name, review_body, rating_value, rating_max=5,
                           author_name=None, date_published=None, image=None):
    """
    Генерирует Review schema для обзоров продуктов
    
    Args:
        item_name: Название продукта
        review_body: Текст обзора
        rating_value: Оценка (1-5)
        rating_max: Максимальная оценка (по умолчанию 5)
        author_name: Имя автора обзора
        date_published: Дата публикации (ISO format)
        image: URL изображения продукта
    
    Returns:
        Dict с Review schema
    """
    schema = {
        "@context": "https://schema.org",
        "@type": "Review",
        "itemReviewed": {
            "@type": "Product",
            "name": item_name
        },
        "reviewBody": review_body,
        "reviewRating": {
            "@type": "Rating",
            "ratingValue": rating_value,
            "bestRating": rating_max,
            "worstRating": 1
        }
    }
    
    if author_name:
        schema["author"] = {
            "@type": "Person",
            "name": author_name
        }
    
    if date_published:
        schema["datePublished"] = date_published
    
    if image:
        if not image.startswith('http'):
            image = f"{settings.SITE_URL}{image}"
        schema["itemReviewed"]["image"] = image
    
    return schema


def generate_video_schema_extended(video_url, name, description, thumbnail_url,
                                   upload_date, duration=None, embed_url=None):
    """
    Расширенная VideoObject schema с дополнительными полями
    
    Args:
        video_url: URL видео
        name: Название видео
        description: Описание
        thumbnail_url: URL превью
        upload_date: Дата загрузки (ISO format)
        duration: Длительность (например, "PT5M30S")
        embed_url: URL для встраивания
    
    Returns:
        Dict с VideoObject schema
    """
    schema = {
        "@context": "https://schema.org",
        "@type": "VideoObject",
        "name": name,
        "description": description,
        "thumbnailUrl": thumbnail_url if thumbnail_url.startswith('http') else f"{settings.SITE_URL}{thumbnail_url}",
        "contentUrl": video_url,
        "uploadDate": upload_date
    }
    
    if duration:
        schema["duration"] = duration
    
    if embed_url:
        schema["embedUrl"] = embed_url
    else:
        schema["embedUrl"] = video_url
    
    # Автор и издатель
    schema["author"] = {
        "@type": "Organization",
        "name": "IdealImage.ru"
    }
    
    schema["publisher"] = {
        "@type": "Organization",
        "name": "IdealImage.ru",
        "logo": {
            "@type": "ImageObject",
            "url": f"{settings.SITE_URL}/static/new/img/logo/11.jpg"
        }
    }
    
    return schema


def generate_itemlist_schema(name, description, items, item_type="ItemList"):
    """
    Генерирует ItemList schema для списков (топ-10, лучшие и т.д.)
    
    Args:
        name: Название списка
        description: Описание
        items: Список элементов [{'name': '...', 'url': '...', 'image': '...'}, ...]
        item_type: Тип списка ("ItemList", "BreadcrumbList")
    
    Returns:
        Dict с ItemList schema
    """
    schema = {
        "@context": "https://schema.org",
        "@type": item_type,
        "name": name,
        "description": description,
        "itemListElement": []
    }
    
    for i, item in enumerate(items, 1):
        item_data = {
            "@type": "ListItem",
            "position": i,
            "name": item.get('name', ''),
        }
        
        if item.get('url'):
            url = item['url']
            if not url.startswith('http'):
                url = f"{settings.SITE_URL}{url}"
            item_data["item"] = url
        
        if item.get('image'):
            image = item['image']
            if not image.startswith('http'):
                image = f"{settings.SITE_URL}{image}"
            item_data["image"] = image
        
        schema["itemListElement"].append(item_data)
    
    return schema


def schema_to_json_ld(schema_dict):
    """
    Конвертирует словарь Schema.org в JSON-LD строку
    
    Args:
        schema_dict: Словарь с данными Schema.org
    
    Returns:
        JSON-LD строка для вставки в <script type="application/ld+json">
    """
    return json.dumps(schema_dict, ensure_ascii=False, indent=2)

