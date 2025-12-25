"""
Представления для работы с расписаниями и Django-Q
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.contrib import messages
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

from ..models import *
from Asistent.schedule.models import AISchedule, AIScheduleRun
from Asistent.schedule.forms import AIScheduleForm, DjangoQScheduleForm
from Asistent.schedule.services import PromptGenerationWorkflow
from Asistent.schedule.context import ScheduleContext
from Asistent.services.djangoq_monitor import DjangoQMonitor
from Asistent.services.content_generation import UnifiedContentGenerationService


# ========================================================================
# РАБОТА С РАСПИСАНИЯМИ И DJANGO-Q
# ========================================================================

@login_required
@staff_member_required
def schedules_dashboard(request):
    """Панель управления расписаниями"""
    schedules = AISchedule.objects.all().order_by('-created_at')
    
    # Статистика по расписаниям
    stats = {
        'total': schedules.count(),
        'active': schedules.filter(is_active=True).count(),
        'inactive': schedules.filter(is_active=False).count(),
        'failed_recently': schedules.filter(
            last_run__gte=timezone.now() - timedelta(days=1),
            runs__status='failed'
        ).distinct().count(),
    }
    
    # Мониторинг Django-Q
    q_monitor = DjangoQMonitor()
    q_stats = q_monitor.get_cluster_stats()
    
    context = {
        'schedules': schedules,
        'stats': stats,
        'q_stats': q_stats,
    }
    
    return render(request, 'Asistent/schedules_dashboard.html', context)


@login_required
@staff_member_required
def create_schedule(request):
    """Создание нового расписания"""
    if request.method == 'POST':
        form = AIScheduleForm(request.POST)
        if form.is_valid():
            schedule = form.save()
            messages.success(request, f"Расписание '{schedule.name}' успешно создано")
            return redirect('schedules_dashboard')
    else:
        form = AIScheduleForm()
    
    context = {
        'form': form,
    }
    
    return render(request, 'Asistent/create_schedule.html', context)


@login_required
@staff_member_required
def edit_schedule(request, schedule_id):
    """Редактирование расписания"""
    schedule = get_object_or_404(AISchedule, id=schedule_id)
    
    if request.method == 'POST':
        form = AIScheduleForm(request.POST, instance=schedule)
        if form.is_valid():
            schedule = form.save()
            messages.success(request, f"Расписание '{schedule.name}' успешно обновлено")
            return redirect('schedules_dashboard')
    else:
        form = AIScheduleForm(instance=schedule)
    
    context = {
        'form': form,
        'schedule': schedule,
    }
    
    return render(request, 'Asistent/edit_schedule.html', context)


@login_required
@staff_member_required
def schedule_detail(request, schedule_id):
    """Детали расписания"""
    schedule = get_object_or_404(AISchedule, id=schedule_id)
    
    # Запуски расписания
    runs = AIScheduleRun.objects.filter(schedule=schedule).order_by('-started_at')[:20]
    
    context = {
        'schedule': schedule,
        'runs': runs,
    }
    
    return render(request, 'Asistent/schedule_detail.html', context)


@login_required
@staff_member_required
@require_POST
def toggle_schedule(request, schedule_id):
    """Вкл/выкл расписание"""
    schedule = get_object_or_404(AISchedule, id=schedule_id)
    
    schedule.is_active = not schedule.is_active
    schedule.save()
    
    status = "активировано" if schedule.is_active else "деактивировано"
    messages.success(request, f"Расписание '{schedule.name}' {status}")
    
    return JsonResponse({
        'success': True,
        'is_active': schedule.is_active,
        'message': f"Расписание {status}"
    })


@login_required
@staff_member_required
@require_POST
def run_schedule_now(request, schedule_id):
    """Запуск расписания немедленно"""
    schedule = get_object_or_404(AISchedule, id=schedule_id)
    
    try:
        # Создаем контекст выполнения
        context = ScheduleContext(schedule, run=None)
        
        # Запускаем workflow
        workflow = PromptGenerationWorkflow(schedule, context)
        result = workflow.run(timezone.now())
        
        if result['success']:
            messages.success(request, f"Расписание '{schedule.name}' выполнено успешно: {result.get('created_count', 0)} статей создано")
        else:
            messages.error(request, f"Ошибка выполнения расписания '{schedule.name}': {result.get('error', 'Неизвестная ошибка')}")
        
        return JsonResponse(result)
        
    except Exception as e:
        logger.error(f"Error running schedule {schedule_id}: {e}")
        error_msg = f"Ошибка выполнения расписания: {str(e)}"
        messages.error(request, error_msg)
        
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
@staff_member_required
def djangoq_monitor_api(request):
    """API для мониторинга Django-Q"""
    monitor = DjangoQMonitor()
    stats = monitor.get_cluster_stats()
    
    return JsonResponse({
        'success': True,
        'stats': stats,
        'timestamp': timezone.now().isoformat(),
    })


@login_required
@staff_member_required
def schedules_api_list(request):
    """API список расписаний"""
    schedules = AISchedule.objects.all().order_by('-created_at')
    
    schedules_data = []
    for schedule in schedules:
        # Получаем статус последнего запуска
        last_run = schedule.runs.order_by('-started_at').first()
        last_run_status = last_run.status if last_run else None
        
        schedules_data.append({
            'id': schedule.id,
            'name': schedule.name,
            'is_active': schedule.is_active,
            'schedule_kind': schedule.schedule_kind,
            'posting_frequency': schedule.posting_frequency,
            'last_run': schedule.last_run.isoformat() if schedule.last_run else None,
            'next_run': schedule.next_run.isoformat() if schedule.next_run else None,
            'last_run_status': last_run_status,
            'current_run_count': schedule.current_run_count,
            'max_runs': schedule.max_runs,
        })
    
    return JsonResponse({
        'success': True,
        'schedules': schedules_data,
    })


@login_required
@staff_member_required
@require_POST
def delete_schedule(request, schedule_id):
    """Удаление расписания"""
    schedule = get_object_or_404(AISchedule, id=schedule_id)
    schedule_name = schedule.name
    schedule.delete()
    
    messages.success(request, f"Расписание '{schedule_name}' успешно удалено")
    
    return JsonResponse({
        'success': True,
        'message': f"Расписание '{schedule_name}' удалено"
    })


@login_required
@staff_member_required
def schedule_runs_api(request, schedule_id):
    """API для получения запусков расписания"""
    schedule = get_object_or_404(AISchedule, id=schedule_id)
    runs = AIScheduleRun.objects.filter(schedule=schedule).order_by('-started_at')[:50]
    
    runs_data = []
    for run in runs:
        runs_data.append({
            'id': run.id,
            'started_at': run.started_at.isoformat() if run.started_at else None,
            'finished_at': run.finished_at.isoformat() if run.finished_at else None,
            'status': run.status,
            'result': run.result,
            'error_message': run.error_message,
            'created_posts_count': run.created_posts.count() if hasattr(run, 'created_posts') else 0,
        })
    
    return JsonResponse({
        'success': True,
        'runs': runs_data,
    })