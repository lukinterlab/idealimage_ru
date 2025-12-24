"""
ВСЯ логика модерации в одном файле.

Упрощённая версия без сложных конвейеров и правил.
Простые функции проверки статей и комментариев.
"""
import re
import logging
from django.utils.html import strip_tags
from .models import ArticleModerationSettings, CommentModerationSettings, ModerationLog

logger = logging.getLogger(__name__)


# ============================================================================
# МОДЕРАЦИЯ СТАТЕЙ
# ============================================================================

def moderate_article(post):
    """
    Проверка статьи по активным настройкам.
    
    Args:
        post: Объект статьи (blog.Post)
    
    Returns:
        tuple: (passed: bool, problems: list[str])
    """
    settings = ArticleModerationSettings.objects.filter(is_active=True).first()
    
    if not settings:
        logger.warning("Нет активных настроек модерации статей")
        return True, []  # Нет настроек = пропускаем всё
    
    problems = []
    
    # 1. Проверка заголовка
    if settings.check_title:
        title = strip_tags(post.title or "").strip()
        if not title:
            problems.append("❌ Заголовок отсутствует")
        elif len(title) < settings.min_title_length:
            problems.append(
                f"❌ Заголовок слишком короткий: {len(title)} из {settings.min_title_length} символов"
            )
    
    # 2. Проверка изображения
    if settings.check_image:
        has_image = bool(getattr(post, 'kartinka', None))
        has_video = bool(getattr(post, 'video_url', None))
        if not has_image and not has_video:
            problems.append("❌ Отсутствует изображение или видео")
    
    # 3. Проверка категории
    if settings.check_category:
        if not getattr(post, 'category', None):
            problems.append("❌ Не выбрана категория")
    
    # 4. Проверка длины текста
    if settings.check_length:
        content = strip_tags(post.content or "")
        words = content.split()
        word_count = len(words)
        
        if word_count < settings.min_words:
            problems.append(
                f"❌ Недостаточно слов: {word_count} из {settings.min_words}"
            )
    
    # 5. Простая проверка на мат
    if settings.check_profanity:
        bad_words = ['хрен', 'чёрт', 'дурак', 'идиот', 'мат']
        content_lower = strip_tags(post.content or "").lower()
        title_lower = strip_tags(post.title or "").lower()
        
        for word in bad_words:
            if word in content_lower or word in title_lower:
                problems.append(f"❌ Обнаружен мат или грубое слово: {word}")
                break
    
    passed = len(problems) == 0
    
    # Логируем результат
    try:
        ModerationLog.objects.create(
            content_type='article',
            object_id=post.id,
            passed=passed,
            problems="\n".join(problems),
            moderator=None  # Автоматическая проверка
        )
    except Exception as e:
        logger.error(f"Ошибка записи лога модерации статьи #{post.id}: {e}")
    
    return passed, problems


def check_article(post, save=True):
    """
    Проверить статью и обновить её статус.
    
    Args:
        post: Объект статьи
        save: Сохранить изменения автоматически
    
    Returns:
        bool: True если пройдена, False если отклонена
    """
    passed, problems = moderate_article(post)
    
    if not passed:
        # Отклонена
        post.status = 'draft'
        if hasattr(post, 'moderation_status'):
            post.moderation_status = 'rejected'
        if hasattr(post, 'ai_moderation_notes'):
            post.ai_moderation_notes = "\n".join(problems)
        
        logger.info(f"Статья #{post.id} отклонена модерацией: {len(problems)} проблем")
    else:
        # Одобрена
        if hasattr(post, 'moderation_status'):
            post.moderation_status = 'approved'
        if hasattr(post, 'ai_moderation_notes'):
            post.ai_moderation_notes = "✅ Модерация пройдена успешно"
        
        logger.info(f"Статья #{post.id} одобрена модерацией")
    
    if save:
        post._skip_auto_moderation = True  # Флаг чтобы избежать рекурсии
        post.save()
    
    return passed


# ============================================================================
# МОДЕРАЦИЯ КОММЕНТАРИЕВ
# ============================================================================

def moderate_comment(comment):
    """
    Проверка комментария по активным настройкам.
    
    Args:
        comment: Объект комментария (blog.Comment)
    
    Returns:
        tuple: (passed: bool, problems: list[str])
    """
    settings = CommentModerationSettings.objects.filter(is_active=True).first()
    
    if not settings:
        logger.warning("Нет активных настроек модерации комментариев")
        return True, []  # Нет настроек = пропускаем всё
    
    problems = []
    
    # Получаем текст
    content = getattr(comment, 'content', None) or getattr(comment, 'text', "")
    text = strip_tags(content)
    text_lower = text.lower()
    
    # 1. Проверка на ссылки
    if settings.block_urls:
        if re.search(r'https?://|www\.', content, re.IGNORECASE):
            problems.append("❌ Содержит ссылки (URL)")
    
    # 2. Проверка на HTML
    if settings.block_html:
        if '<' in content and '>' in content:
            # Простая проверка наличия HTML-тегов
            if re.search(r'<[^>]+>', content):
                problems.append("❌ Содержит HTML-теги")
    
    # 3. Проверка длины
    if settings.block_short:
        if len(text) < settings.min_length:
            problems.append(
                f"❌ Слишком короткий: {len(text)} из {settings.min_length} символов"
            )
    
    # 4. Проверка запрещённых слов
    if settings.forbidden_words:
        words = [w.strip().lower() for w in settings.forbidden_words.split(',') if w.strip()]
        for word in words:
            if word in text_lower:
                problems.append(f"❌ Запрещённое слово: {word}")
                break
    
    # 5. Простая проверка спама
    if settings.check_spam:
        spam_words = [
            'купить', 'купи', 'казино', 'ставки', 'скидка',
            'промокод', 'заработок', 'кредит', 'займ'
        ]
        for word in spam_words:
            if word in text_lower:
                problems.append(f"❌ Спам-слово: {word}")
                break
    
    passed = len(problems) == 0
    
    # Логируем результат
    try:
        ModerationLog.objects.create(
            content_type='comment',
            object_id=comment.id if comment.id else 0,
            passed=passed,
            problems="\n".join(problems),
            moderator=None  # Автоматическая проверка
        )
    except Exception as e:
        logger.error(f"Ошибка записи лога модерации комментария: {e}")
    
    return passed, problems


def check_comment(comment, save=True):
    """
    Проверить комментарий и обновить его статус.
    
    Args:
        comment: Объект комментария
        save: Сохранить изменения автоматически
    
    Returns:
        bool: True если пройден, False если заблокирован
    """
    passed, problems = moderate_comment(comment)
    
    # Устанавливаем активность
    comment.active = passed
    
    # Сохраняем причины блокировки если есть
    if not passed and hasattr(comment, 'moderation_notes'):
        comment.moderation_notes = "\n".join(problems)
    
    # Флаг что модерация уже выполнена
    comment._ai_moderation_processed = True
    
    if passed:
        logger.debug(f"Комментарий #{comment.id} одобрен модерацией")
    else:
        logger.info(f"Комментарий #{comment.id} заблокирован: {len(problems)} проблем")
    
    if save and comment.id:
        comment.save()
    
    return passed


# ============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================================

def get_article_statistics():
    """
    Статистика модерации статей.
    
    Returns:
        dict: Статистика по проверкам статей
    """
    from django.db.models import Count
    
    logs = ModerationLog.objects.filter(content_type='article')
    
    return {
        'total': logs.count(),
        'passed': logs.filter(passed=True).count(),
        'rejected': logs.filter(passed=False).count(),
    }


def get_comment_statistics():
    """
    Статистика модерации комментариев.
    
    Returns:
        dict: Статистика по проверкам комментариев
    """
    from django.db.models import Count
    
    logs = ModerationLog.objects.filter(content_type='comment')
    
    return {
        'total': logs.count(),
        'passed': logs.filter(passed=True).count(),
        'rejected': logs.filter(passed=False).count(),
    }


def get_moderation_statistics():
    """
    Общая статистика модерации.
    
    Returns:
        dict: Полная статистика
    """
    return {
        'articles': get_article_statistics(),
        'comments': get_comment_statistics(),
    }

