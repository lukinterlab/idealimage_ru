"""
Модуль для отправки уведомлений в Telegram
"""
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

from Asistent.services.telegram_client import get_telegram_client


def send_telegram_notification(telegram_id, message):
    """
    Отправка уведомления в Telegram
    
    Args:
        telegram_id: Telegram ID пользователя
        message: Текст сообщения
    
    Returns:
        bool: True если сообщение отправлено успешно, False в противном случае
    """
    if not telegram_id:
        logger.warning("Telegram ID не указан")
        return False
    
    client = get_telegram_client()

    if client.send_message(str(telegram_id), message, parse_mode='HTML'):
        logger.info(f"Уведомление успешно отправлено пользователю {telegram_id}")
        return True

    logger.error("Ошибка отправки уведомления пользователю %s", telegram_id)
    return False


def notify_author_new_comment(author_profile, post, comment):
    """
    Уведомление автора о новом комментарии к его статье
    
    Args:
        author_profile: Профиль автора
        post: Статья
        comment: Комментарий
    """
    if not author_profile.telegram_id:
        return False
    
    message = f"""
📝 <b>Новый комментарий к вашей статье!</b>

Статья: {post.title}
Автор комментария: {comment.author_comment}
Комментарий: {comment.content[:100]}{'...' if len(comment.content) > 100 else ''}

Перейти к статье: {settings.SITE_URL}/blog/{post.slug}/
"""
    
    return send_telegram_notification(author_profile.telegram_id, message)


def notify_author_new_like(author_profile, post, user):
    """
    Уведомление автора о новом лайке его статьи
    
    Args:
        author_profile: Профиль автора
        post: Статья
        user: Пользователь, поставивший лайк
    """
    if not author_profile.telegram_id:
        return False
    
    message = f"""
❤️ <b>Вашу статью лайкнули!</b>

Статья: {post.title}
Лайк от: {user.username}

Перейти к статье: {settings.SITE_URL}/blog/{post.slug}/
"""
    
    return send_telegram_notification(author_profile.telegram_id, message)


def notify_author_new_donation(author_profile, donation):
    """
    Уведомление автора о новом донате
    
    Args:
        author_profile: Профиль автора
        donation: Донат
    """
    if not author_profile.telegram_id:
        return False
    
    donor_name = donation.user.username if donation.user and not donation.is_anonymous else 'Анонимный читатель'
    
    message = f"""
💰 <b>Новый донат!</b>

Сумма: {donation.amount} руб.
От: {donor_name}
{f'Сообщение: {donation.message}' if donation.message else ''}

Спасибо за ваше творчество! 🎉
"""
    
    return send_telegram_notification(author_profile.telegram_id, message)


def notify_author_statistics(author_profile, stats):
    """
    Отправка ежедневной статистики автору
    
    Args:
        author_profile: Профиль автора
        stats: Словарь со статистикой
    """
    if not author_profile.telegram_id:
        return False
    
    message = f"""
📊 <b>Ваша статистика за сегодня:</b>

Новые просмотры: {stats.get('views', 0)}
Новые лайки: {stats.get('likes', 0)}
Новые комментарии: {stats.get('comments', 0)}
Полученные донаты: {stats.get('donations', 0)} руб.

Всего статей: {stats.get('total_posts', 0)}
Всего подписчиков: {stats.get('subscribers', 0)}

Продолжайте в том же духе! 💪
"""
    
    return send_telegram_notification(author_profile.telegram_id, message)


def notify_user_role_granted(user_profile, role_name):
    """
    Уведомление пользователя о присвоении роли
    
    Args:
        user_profile: Профиль пользователя
        role_name: Название роли
    """
    if not user_profile.telegram_id:
        return False
    
    message = f"""
🎉 <b>Поздравляем!</b>

Вам присвоена роль: <b>{role_name}</b>

Теперь у вас есть доступ к новым возможностям на сайте!

Перейти в личный кабинет: {settings.SITE_URL}/visitor/cabinet/
"""
    
    return send_telegram_notification(user_profile.telegram_id, message)


def notify_user_role_rejected(user_profile, role_name, reason=''):
    """
    Уведомление пользователя об отклонении заявки на роль
    
    Args:
        user_profile: Профиль пользователя
        role_name: Название роли
        reason: Причина отклонения
    """
    if not user_profile.telegram_id:
        return False
    
    message = f"""
❌ <b>Ваша заявка отклонена</b>

Роль: {role_name}
{f'Причина: {reason}' if reason else ''}

Вы можете подать заявку повторно позже.

Перейти в личный кабинет: {settings.SITE_URL}/visitor/cabinet/
"""
    
    return send_telegram_notification(user_profile.telegram_id, message)

