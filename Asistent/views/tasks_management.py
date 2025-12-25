"""
Представления для управления заданиями авторов
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.contrib import messages
import logging

logger = logging.getLogger(__name__)

from ..models import ContentTask, AITask
from ..forms import ContentTaskForm
from Asistent.services.notifications import notify_user
from Asistent.services.task_actions import (
    take_task as take_task_action,
    cancel_task as cancel_task_action,
    approve_task as approve_task_action,
    reject_task as reject_task_action,
)
from Asistent.services.content_generation import CommandParserService


# ========================================================================
# УПРАВЛЕНИЕ ЗАДАНИЯМИ АВТОРОВ
# ========================================================================

@login_required
def tasks_list(request):
    """Список заданий для текущего пользователя"""
    user_tasks = ContentTask.objects.filter(assigned_to=request.user).order_by('-created_at')
    
    # Фильтрация по статусу если указан
    status_filter = request.GET.get('status')
    if status_filter:
        user_tasks = user_tasks.filter(status=status_filter)
    
    # Пагинация
    from django.core.paginator import Paginator
    paginator = Paginator(user_tasks, 10)  # 10 заданий на страницу
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'status_filter': status_filter,
    }
    
    return render(request, 'Asistent/tasks_list.html', context)


@login_required
@staff_member_required
def admin_tasks_list(request):
    """Список всех заданий (для админов)"""
    all_tasks = ContentTask.objects.all().order_by('-created_at')
    
    # Фильтрация
    status_filter = request.GET.get('status')
    assignee_filter = request.GET.get('assignee')
    
    if status_filter:
        all_tasks = all_tasks.filter(status=status_filter)
    if assignee_filter:
        all_tasks = all_tasks.filter(assigned_to_id=assignee_filter)
    
    # Получаем всех пользователей для фильтра
    from django.contrib.auth.models import User
    all_users = User.objects.filter(is_active=True)
    
    # Пагинация
    from django.core.paginator import Paginator
    paginator = Paginator(all_tasks, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'status_filter': status_filter,
        'assignee_filter': assignee_filter,
        'all_users': all_users,
    }
    
    return render(request, 'Asistent/admin_tasks_list.html', context)


@login_required
def task_detail(request, task_id):
    """Детали задания"""
    task = get_object_or_404(ContentTask, id=task_id)
    
    # Проверяем права доступа
    if request.user != task.assigned_to and not request.user.is_staff:
        messages.error(request, "У вас нет доступа к этому заданию")
        return redirect('tasks_list')
    
    context = {
        'task': task,
    }
    
    return render(request, 'Asistent/task_detail.html', context)


@login_required
@require_POST
def take_task(request, task_id):
    """Взять задание в работу"""
    try:
        result = take_task_action(task_id, request.user)
        if result['success']:
            messages.success(request, "Задание успешно взято в работу")
        else:
            messages.error(request, result.get('error', 'Не удалось взять задание'))
        
        return JsonResponse(result)
    except Exception as e:
        logger.error(f"Error taking task {task_id}: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
@require_POST
def cancel_task(request, task_id):
    """Отменить задание"""
    try:
        result = cancel_task_action(task_id, request.user)
        if result['success']:
            messages.success(request, "Задание успешно отменено")
        else:
            messages.error(request, result.get('error', 'Не удалось отменить задание'))
        
        return JsonResponse(result)
    except Exception as e:
        logger.error(f"Error cancelling task {task_id}: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
@staff_member_required
@require_POST
def approve_task(request, task_id):
    """Одобрить задание"""
    try:
        result = approve_task_action(task_id, request.user)
        if result['success']:
            messages.success(request, "Задание успешно одобрено")
        else:
            messages.error(request, result.get('error', 'Не удалось одобрить задание'))
        
        return JsonResponse(result)
    except Exception as e:
        logger.error(f"Error approving task {task_id}: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
@staff_member_required
@require_POST
def reject_task(request, task_id):
    """Отклонить задание"""
    try:
        result = reject_task_action(task_id, request.user)
        if result['success']:
            messages.success(request, "Задание успешно отклонено")
        else:
            messages.error(request, result.get('error', 'Не удалось отклонить задание'))
        
        return JsonResponse(result)
    except Exception as e:
        logger.error(f"Error rejecting task {task_id}: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
@staff_member_required
def create_task(request):
    """Создание нового задания"""
    if request.method == 'POST':
        form = ContentTaskForm(request.POST)
        if form.is_valid():
            task = form.save(commit=False)
            task.created_by = request.user
            task.save()
            
            # Уведомляем назначенного пользователя
            if task.assigned_to:
                notify_user(
                    user=task.assigned_to,
                    title="Новое задание",
                    message=f"Вам назначено новое задание: {task.title}",
                    task=task
                )
            
            messages.success(request, "Задание успешно создано")
            return redirect('admin_tasks_list')
    else:
        form = ContentTaskForm()
    
    context = {
        'form': form,
    }
    
    return render(request, 'Asistent/create_task.html', context)


@login_required
@staff_member_required
def ai_command_interface(request):
    """Интерфейс для AI-команд администратора"""
    if request.method == 'POST':
        command_text = request.POST.get('command', '').strip()
        if command_text:
            parser_service = CommandParserService()
            result = parser_service.parse_and_execute(command_text, request.user)
            
            if result['success']:
                messages.success(request, f"Команда выполнена: {result.get('title', 'Операция завершена')}")
            else:
                messages.error(request, f"Ошибка выполнения команды: {result.get('error', 'Неизвестная ошибка')}")
            
            return redirect('ai_command_interface')
    
    # История команд (последние 10)
    recent_tasks = AITask.objects.filter(created_by=request.user).order_by('-created_at')[:10]
    
    context = {
        'recent_tasks': recent_tasks,
    }
    
    return render(request, 'Asistent/ai_command_interface.html', context)