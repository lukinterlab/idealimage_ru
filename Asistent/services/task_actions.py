from __future__ import annotations

from typing import Optional, Tuple

from django.contrib.auth.models import User
from django.utils import timezone

from Asistent.models import ContentTask, TaskAssignment
from Asistent.services.notifications import notify_user


def take_task(user: User, task: ContentTask) -> Tuple[bool, str]:
    """Попытка назначить задание автору."""
    can_take, reason = task.can_be_taken(user)
    if not can_take:
        return False, reason

    assignment, created = TaskAssignment.objects.get_or_create(
        task=task,
        author=user,
        defaults={'status': 'in_progress', 'taken_at': timezone.now()},
    )
    if not created and assignment.status == 'in_progress':
        return False, 'Задание уже у вас в работе'

    assignment.status = 'in_progress'
    assignment.taken_at = timezone.now()
    assignment.save()

    if task.status == 'available':
        task.status = 'active'
        task.save(update_fields=['status'])

    notify_user(
        recipient=user,
        notification_type='task_taken',
        title='Задание взято в работу',
        message=(
            f'Вы взяли задание "{task.title}".\n\n'
            f'Срок выполнения: {task.deadline.strftime("%d.%m.%Y %H:%M") if task.deadline else "—"}\n'
            f'Вознаграждение: {task.reward} руб.'
        ),
        related_task=task,
    )
    return True, ''


def cancel_task(task: ContentTask) -> int:
    """Отменяет активные назначения задания и уведомляет авторов."""
    assignments = TaskAssignment.objects.filter(task=task, status='in_progress')
    count = assignments.count()

    for assignment in assignments:
        assignment.status = 'rejected_by_author'
        assignment.rejection_reason = 'Задание отменено администратором'
        assignment.save(update_fields=['status', 'rejection_reason'])

        notify_user(
            recipient=assignment.author,
            notification_type='system',
            title='⚠️ Задание отменено',
            message=(
                f'Задание "{task.title}" отменено администратором.\n\n'
                'Приносим извинения за неудобства.'
            ),
            related_task=task,
        )

    task.status = 'cancelled'
    task.save(update_fields=['status'])
    return count


def approve_task(task: ContentTask, moderator: User) -> bool:
    """Одобряет выполнение задания и уведомляет автора."""
    if not task.approve(moderator):
        return False

    if task.assigned_to:
        notify_user(
            recipient=task.assigned_to,
            notification_type='task_approved',
            title='💰 Задание одобрено!',
            message=(
                f'Поздравляем! Ваше задание "{task.title}" одобрено.\n\n'
                f'Вам начислено: {task.reward} руб.'
            ),
            related_task=task,
            related_article=task.article,
        )
    return True


def reject_task(task: ContentTask, reason: str) -> bool:
    """Отклоняет выполнение задания и уведомляет автора."""
    if not task.reject(reason):
        return False

    if task.assigned_to:
        notify_user(
            recipient=task.assigned_to,
            notification_type='task_rejected',
            title='❌ Задание отклонено',
            message=(
                f'К сожалению, задание "{task.title}" отклонено.\n\nПричина:\n{reason}'
            ),
            related_task=task,
        )
    return True
