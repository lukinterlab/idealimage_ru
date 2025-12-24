"""
Утилиты для работы с системой лайков
"""
from django.db import transaction
from .models_likes import Like


def convert_anonymous_likes_to_user(session_key, user):
    """
    Конвертирует анонимные лайки в лайки зарегистрированного пользователя
    
    Args:
        session_key: ключ сессии анонимного пользователя
        user: объект пользователя Django
        
    Returns:
        dict: словарь со статистикой конвертации
            {
                'converted': int,  # количество конвертированных лайков
                'skipped': int,    # количество пропущенных (дубликаты)
                'deleted': int     # количество удаленных анонимных лайков
            }
    """
    if not session_key or not user or not user.is_authenticated:
        return {'converted': 0, 'skipped': 0, 'deleted': 0}
    
    converted = 0
    skipped = 0
    deleted = 0
    
    with transaction.atomic():
        # Получаем все анонимные лайки этой сессии
        anonymous_likes = Like.objects.filter(
            user__isnull=True,
            session_key=session_key
        )
        
        for anonymous_like in anonymous_likes:
            # Проверяем, есть ли уже лайк от этого пользователя на этот пост
            existing_like = Like.objects.filter(
                user=user,
                post=anonymous_like.post
            ).first()
            
            if existing_like:
                # Если пользователь уже лайкнул этот пост, удаляем анонимный лайк
                anonymous_like.delete()
                skipped += 1
            else:
                # Конвертируем анонимный лайк в лайк пользователя
                anonymous_like.user = user
                anonymous_like.session_key = None
                anonymous_like.save()
                converted += 1
    
    return {
        'converted': converted,
        'skipped': skipped,
        'deleted': skipped  # skipped лайки были удалены
    }


def get_anonymous_likes_count(session_key):
    """
    Получить количество анонимных лайков для данной сессии
    
    Args:
        session_key: ключ сессии
        
    Returns:
        int: количество лайков
    """
    if not session_key:
        return 0
    
    return Like.objects.filter(
        user__isnull=True,
        session_key=session_key
    ).count()


def merge_anonymous_and_user_likes(session_key, user):
    """
    Объединяет анонимные лайки с лайками пользователя при входе
    Приоритет отдается лайкам пользователя
    
    Args:
        session_key: ключ сессии анонимного пользователя
        user: объект пользователя Django
        
    Returns:
        dict: статистика объединения
    """
    if not session_key or not user or not user.is_authenticated:
        return {'merged': 0, 'deleted': 0}
    
    merged = 0
    deleted = 0
    
    with transaction.atomic():
        # Получаем все анонимные лайки
        anonymous_likes = Like.objects.filter(
            user__isnull=True,
            session_key=session_key
        )
        
        for anon_like in anonymous_likes:
            # Проверяем, есть ли лайк пользователя на этот же пост
            user_like = Like.objects.filter(
                user=user,
                post=anon_like.post
            ).first()
            
            if user_like:
                # Если есть лайк пользователя, удаляем анонимный
                anon_like.delete()
                deleted += 1
            else:
                # Если нет, конвертируем анонимный в лайк пользователя
                anon_like.user = user
                anon_like.session_key = None
                anon_like.save()
                merged += 1
    
    return {'merged': merged, 'deleted': deleted}

