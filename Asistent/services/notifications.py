import logging
from typing import Iterable, Optional

from django.contrib.auth import get_user_model

from Asistent.models import AuthorNotification

logger = logging.getLogger(__name__)


def notify_user(
    *,
    recipient,
    title: str,
    message: str,
    notification_type: str = "system",
    related_article=None,
    related_task=None,
):
    """
    Создаёт единичное уведомление для пользователя.
    """
    try:
        return AuthorNotification.objects.create(
            recipient=recipient,
            notification_type=notification_type,
            title=title,
            message=message,
            related_article=related_article,
            related_task=related_task,
        )
    except Exception as exc:
        logger.error(
            "❌ notify_user: не удалось создать уведомление для пользователя %s — %s",
            getattr(recipient, "id", recipient),
            exc,
        )
        return None


def notify_users(
    *,
    recipients: Iterable,
    title: str,
    message: str,
    notification_type: str = "system",
    related_article=None,
    related_task=None,
) -> None:
    """
    Создаёт уведомления для нескольких пользователей.
    """
    for user in recipients:
        notify_user(
            recipient=user,
            title=title,
            message=message,
            notification_type=notification_type,
            related_article=related_article,
            related_task=related_task,
        )


def notify_authors_about_image(
    *,
    post,
    new_image_path: str,
    old_image_path: Optional[str],
    message: str,
    requested_by_id: Optional[int] = None,
) -> None:
    """
    Создаёт или обновляет уведомление о сгенерированном изображении поста.
    """

    AuthorNotification.objects.filter(
        related_article=post,
        message__contains="AI_GENERATED_IMAGE",
    ).delete()

    recipients = {post.author_id}
    if requested_by_id:
        recipients.add(requested_by_id)

    User = get_user_model()
    users = User.objects.filter(id__in=recipients)

    for user in users:
        notify_user(
            recipient=user,
            notification_type="system",
            title="🎨 AI сгенерировал новое изображение",
            message=(
                f"AI_GENERATED_IMAGE:{new_image_path}\n"
                f"OLD_IMAGE:{old_image_path or 'none'}\n"
                f"PROMPT:{message or 'auto'}"
            ),
            related_article=post,
        )


def notify_author_error(*, post, error_message: str) -> None:
    """
    Создаёт уведомление об ошибке для автора статьи.
    """
    notify_user(
        recipient=post.author,
        notification_type="system",
        title="Ошибка генерации изображения",
        message=f"AI_IMAGE_ERROR:{error_message}",
        related_article=post,
    )


def bulk_notify_users(
    *,
    users: Iterable,
    title: str,
    message: str,
    metadata: Optional[dict] = None,
) -> None:
    """
    Утилита для массовой отправки уведомлений пользователям.
    """
    notification_type = metadata.get("type", "system") if metadata else "system"
    related_article = metadata.get("related_article") if metadata else None
    related_task = metadata.get("related_task") if metadata else None

    notify_users(
        recipients=users,
        title=title,
        message=message,
        notification_type=notification_type,
        related_article=related_article,
        related_task=related_task,
    )

