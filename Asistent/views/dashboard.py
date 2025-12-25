"""
Представления для админ-панели и метрик
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse, Http404
from django.views.decorators.http import require_POST
from django.db.models import Sum, Count, Q, F, ExpressionWrapper, DurationField, OuterRef, Subquery
from django.db.models.functions import Lower
from django.utils import timezone
from django.contrib import messages
from django.conf import settings
from django.urls import reverse
import logging
from urllib.parse import urlencode
import json

logger = logging.getLogger(__name__)

from ..models import *
from ..forms import ContentTaskForm
from Asistent.schedule.forms import AIScheduleForm, DjangoQScheduleForm
from Asistent.Test_Promot.forms import PromptTemplateForm
from ..analytics import AIMetricsDashboard
from ..dashboard_helpers import *
from datetime import date, timedelta, datetime
from django.core.paginator import Paginator
from django.core.serializers.json import DjangoJSONEncoder
from django.utils.dateparse import parse_date
from Asistent.formatting import render_markdown, MarkdownPreset
from Asistent.services.notifications import notify_user
from Asistent.services.task_actions import (
    take_task as take_task_action,
    cancel_task as cancel_task_action,
    approve_task as approve_task_action,
    reject_task as reject_task_action,
)
from Asistent.schedule.presets import AI_SCHEDULE_PRESETS
from Asistent.services import djangoq_monitor

SCHEDULE_STATUS_STYLES = {
    'success': {
        'label': 'Успешно',
        'badge_classes': 'bg-emerald-500/20 text-emerald-300',
    },
    'failed': {
        'label': 'Ошибка',
        'badge_classes': 'bg-rose-500/20 text-rose-300',
    },
    'running': {
        'label': 'Выполняется',
        'badge_classes': 'bg-amber-500/20 text-amber-300',
    },
    'pending': {
        'label': 'Ожидает',
        'badge_classes': 'bg-slate-500/20 text-slate-300',
    },
    'cancelled': {
        'label': 'Отменено',
        'badge_classes': 'bg-slate-500/20 text-slate-300',
    },
    'skipped': {
        'label': 'Пропущено',
        'badge_classes': 'bg-slate-500/20 text-slate-300',
    },
}

# ========================================================================
# ГЛАВНАЯ ПАНЕЛЬ УПРАВЛЕНИЯ AI
# ========================================================================

@login_required
@staff_member_required
def ai_dashboard(request):
    """Главная панель управления AI-ассистентом"""
    if not request.user.is_staff:
        messages.error(request, "Доступ запрещен")
        return redirect('home')
    
    # Получаем метрики через сервис
    dashboard_service = AIMetricsDashboard()
    metrics = dashboard_service.get_dashboard_metrics()
    
    # Задачи для текущего пользователя
    user_tasks = ContentTask.objects.filter(
        assigned_to=request.user,
        status__in=['available', 'active']
    ).order_by('-created_at')
    
    # Последние расписания
    recent_schedules = AISchedule.objects.filter(
        is_active=True
    ).order_by('-created_at')[:10]
    
    # Статистика по статусам заданий
    task_stats = {
        'total': ContentTask.objects.count(),
        'available': ContentTask.objects.filter(status='available').count(),
        'active': ContentTask.objects.filter(status='active').count(),
        'completed': ContentTask.objects.filter(status='completed').count(),
        'cancelled': ContentTask.objects.filter(status='cancelled').count(),
    }
    
    context = {
        'metrics': metrics,
        'user_tasks': user_tasks,
        'recent_schedules': recent_schedules,
        'task_stats': task_stats,
        'now': timezone.now(),
    }
    
    return render(request, 'Asistent/dashboard.html', context)


@login_required
@staff_member_required
def dashboard_metrics_api(request):
    """API для получения метрик дашборда (AJAX)"""
    dashboard_service = AIMetricsDashboard()
    metrics = dashboard_service.get_dashboard_metrics()
    
    return JsonResponse({
        'success': True,
        'metrics': metrics,
        'timestamp': timezone.now().isoformat(),
    })


@login_required
@staff_member_required
def dashboard_charts_data(request):
    """Данные для графиков дашборда"""
    # Данные за последние 30 дней
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=30)
    
    # Количество созданных статей по дням
    articles_data = []
    for i in range(30, -1, -1):
        current_date = end_date - timedelta(days=i)
        count = Post.objects.filter(
            created_at__date=current_date,
            author__username='ai_assistant'
        ).count()
        articles_data.append({
            'date': current_date.isoformat(),
            'count': count
        })
    
    # Статистика заданий
    tasks_data = {
        'total': ContentTask.objects.count(),
        'by_status': {
            'pending': ContentTask.objects.filter(status='pending').count(),
            'in_progress': ContentTask.objects.filter(status='in_progress').count(),
            'completed': ContentTask.objects.filter(status='completed').count(),
            'cancelled': ContentTask.objects.filter(status='cancelled').count(),
        }
    }
    
    return JsonResponse({
        'articles': articles_data,
        'tasks': tasks_data,
    })