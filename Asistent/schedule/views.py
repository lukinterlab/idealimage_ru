"""
Views для управления расписаниями AI.
Централизованное управление всеми расписаниями через веб-интерфейс.
"""
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db.models import Q, Count
from django.utils import timezone
from datetime import timedelta

from .models import AISchedule, AIScheduleRun
from Asistent.schedule.forms import AIScheduleForm
from .tasks import run_specific_schedule, generate_all_horoscopes
from Asistent.models import PromptTemplate
from blog.models import Category, Post

logger = logging.getLogger(__name__)


@staff_member_required
def schedule_dashboard(request):
    """
    Главный дашборд расписаний с группировкой и статистикой.
    """
    # Группировка по категориям промптов
    schedules_by_category = {}
    all_schedules = AISchedule.objects.select_related('prompt_template', 'category').all()
    
    for schedule in all_schedules:
        category_key = schedule.prompt_template.category if schedule.prompt_template else 'other'
        if category_key not in schedules_by_category:
            schedules_by_category[category_key] = []
        schedules_by_category[category_key].append(schedule)
    
    # Статистика за сегодня
    today = timezone.now().date()
    posts_today = Post.objects.filter(
        created__date=today,
        author__username='ai_assistant'
    ).count()
    
    # Статистика по расписаниям
    active_count = AISchedule.objects.filter(is_active=True).count()
    total_runs_today = AIScheduleRun.objects.filter(
        started_at__date=today
    ).count()
    
    # Гороскопы
    horoscope_schedules = AISchedule.objects.filter(
        prompt_template__category='horoscope',
        is_active=True
    ).count()
    
    context = {
        'schedules_by_category': schedules_by_category,
        'posts_today': posts_today,
        'total_schedules': AISchedule.objects.count(),
        'active_schedules': active_count,
        'total_runs_today': total_runs_today,
        'horoscope_schedules': horoscope_schedules,
        'page_title': 'Дашборд расписаний AI - IdealImage.ru',
        'page_description': 'Центральная панель управления расписаниями AI-генерации контента',
    }
    
    return render(request, 'Asistent/schedule/dashboard.html', context)


@staff_member_required
def schedule_list(request):
    """
    Список всех расписаний с фильтрацией и поиском.
    """
    # Фильтры
    search = request.GET.get('search', '')
    category = request.GET.get('category', '')
    is_active = request.GET.get('is_active', '')
    strategy_type = request.GET.get('strategy_type', '')
    
    schedules = AISchedule.objects.select_related('prompt_template', 'category').all()
    
    if search:
        schedules = schedules.filter(
            Q(name__icontains=search) |
            Q(tags__icontains=search)
        )
    
    if category:
        schedules = schedules.filter(category_id=category)
    
    if is_active == 'true':
        schedules = schedules.filter(is_active=True)
    elif is_active == 'false':
        schedules = schedules.filter(is_active=False)
    
    if strategy_type:
        schedules = schedules.filter(strategy_type=strategy_type)
    
    schedules = schedules.order_by('-created_at')
    
    context = {
        'schedules': schedules,
        'categories': Category.objects.all(),
        'search': search,
        'category': category,
        'is_active': is_active,
        'strategy_type': strategy_type,
        'page_title': 'Список расписаний - IdealImage.ru',
        'page_description': 'Список всех расписаний AI-генерации с фильтрацией и поиском',
    }
    
    return render(request, 'Asistent/schedule/list.html', context)


@staff_member_required
def schedule_create(request):
    """
    Создание нового расписания с улучшенной формой.
    """
    import json
    from django.conf import settings
    from django.urls import reverse
    from django.core.serializers.json import DjangoJSONEncoder
    from Asistent.schedule.presets import AI_SCHEDULE_PRESETS
    
    if request.method == 'POST':
        form = AIScheduleForm(request.POST)
        if form.is_valid():
            schedule = form.save()
            messages.success(request, f'Расписание "{schedule.name}" создано!')
            return redirect('schedule:schedule_detail', schedule_id=schedule.id)
    else:
        form = AIScheduleForm()
    
    # Пресеты расписаний
    def _build_global_schedule_presets():
        presets = []
        for preset in AI_SCHEDULE_PRESETS:
            item = preset.copy()
            item.pop('pipeline_slug', None)
            item.pop('pipeline_id', None)
            presets.append(item)
        return presets
    
    global_presets = _build_global_schedule_presets()
    
    context = {
        'form': form,
        'schedule': None,
        'is_edit': False,
        'prompt_templates': PromptTemplate.objects.filter(is_active=True),
        'categories': Category.objects.all(),
        'schedule_presets': global_presets,
        'schedule_presets_json': json.dumps(global_presets, ensure_ascii=False, cls=DjangoJSONEncoder),
        'schedule_preview_url': reverse('asistent:schedule_preview'),
        'schedule_load_limit': getattr(settings, 'AISCHEDULE_MAX_ITEMS_PER_HOUR', 30),
        'page_title': 'Создание расписания - IdealImage.ru',
        'page_description': 'Создание нового расписания автоматической генерации контента',
    }
    
    return render(request, 'Asistent/schedule/create.html', context)


@staff_member_required
def schedule_edit(request, schedule_id):
    """
    Редактирование расписания.
    """
    import json
    from django.conf import settings
    from django.urls import reverse
    from django.core.serializers.json import DjangoJSONEncoder
    from Asistent.schedule.presets import AI_SCHEDULE_PRESETS
    
    schedule = get_object_or_404(AISchedule, id=schedule_id)
    
    if request.method == 'POST':
        form = AIScheduleForm(request.POST, instance=schedule)
        if form.is_valid():
            schedule = form.save()
            messages.success(request, f'Расписание "{schedule.name}" обновлено!')
            return redirect('schedule:schedule_detail', schedule_id=schedule.id)
    else:
        form = AIScheduleForm(instance=schedule)
    
    # Пресеты расписаний
    def _build_global_schedule_presets():
        presets = []
        for preset in AI_SCHEDULE_PRESETS:
            item = preset.copy()
            item.pop('pipeline_slug', None)
            item.pop('pipeline_id', None)
            presets.append(item)
        return presets
    
    global_presets = _build_global_schedule_presets()
    
    context = {
        'form': form,
        'schedule': schedule,
        'is_edit': True,
        'prompt_templates': PromptTemplate.objects.filter(is_active=True),
        'categories': Category.objects.all(),
        'schedule_presets': global_presets,
        'schedule_presets_json': json.dumps(global_presets, ensure_ascii=False, cls=DjangoJSONEncoder),
        'schedule_preview_url': reverse('asistent:schedule_preview'),
        'schedule_load_limit': getattr(settings, 'AISCHEDULE_MAX_ITEMS_PER_HOUR', 30),
        'page_title': f'Редактирование: {schedule.name} - IdealImage.ru',
        'page_description': f'Редактирование расписания AI "{schedule.name}"',
    }
    
    return render(request, 'Asistent/schedule/create.html', context)


@staff_member_required
def schedule_detail(request, schedule_id):
    """
    Детальная страница расписания с управлением.
    """
    schedule = get_object_or_404(AISchedule, id=schedule_id)
    
    # Последние запуски
    recent_runs = AIScheduleRun.objects.filter(
        schedule=schedule
    ).order_by('-started_at')[:10]
    
    # Статистика
    total_runs = AIScheduleRun.objects.filter(schedule=schedule).count()
    successful_runs = AIScheduleRun.objects.filter(
        schedule=schedule,
        status='completed'
    ).count()
    
    context = {
        'schedule': schedule,
        'recent_runs': recent_runs,
        'total_runs': total_runs,
        'successful_runs': successful_runs,
        'page_title': f'{schedule.name} - IdealImage.ru',
        'page_description': f'Детальная информация о расписании "{schedule.name}"',
    }
    
    return render(request, 'Asistent/schedule/detail.html', context)


@staff_member_required
@require_POST
def schedule_toggle(request, schedule_id):
    """
    Включение/выключение расписания.
    """
    schedule = get_object_or_404(AISchedule, id=schedule_id)
    schedule.is_active = not schedule.is_active
    schedule.save(update_fields=['is_active', 'updated_at'])
    
    status = 'включено' if schedule.is_active else 'выключено'
    messages.success(request, f'Расписание "{schedule.name}" {status}!')
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'is_active': schedule.is_active,
            'message': f'Расписание {status}'
        })
    
    return redirect('schedule:schedule_detail', schedule_id=schedule_id)


@staff_member_required
@require_POST
def schedule_run_now(request, schedule_id):
    """
    Ручной запуск расписания.
    """
    schedule = get_object_or_404(AISchedule, id=schedule_id)
    
    from django_q.tasks import async_task
    task_id = async_task(
        'Asistent.schedule.tasks.run_specific_schedule',
        schedule_id,
        task_name=f'schedule:{schedule_id}'
    )
    
    messages.success(
        request,
        f'🚀 Задача запущена! Task ID: {task_id}'
    )
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'task_id': task_id,
            'message': 'Задача запущена'
        })
    
    return redirect('schedule:schedule_detail', schedule_id=schedule_id)


@staff_member_required
@require_POST
def schedule_delete(request, schedule_id):
    """
    Удаление расписания.
    """
    schedule = get_object_or_404(AISchedule, id=schedule_id)
    schedule_name = schedule.name
    schedule.delete()
    
    messages.success(request, f'Расписание "{schedule_name}" удалено!')
    return redirect('schedule:schedule_list')


@staff_member_required
@require_POST
def run_all_horoscopes(request):
    """
    Запуск всех гороскопов через интерфейс.
    """
    from django_q.tasks import async_task
    
    task_id = async_task(
        'Asistent.schedule.tasks.generate_all_horoscopes',
        task_name='all_horoscopes_batch'
    )
    
    messages.success(
        request,
        f'🚀 Запущена генерация всех 12 гороскопов! Task ID: {task_id}'
    )
    
    return redirect('schedule:schedule_dashboard')

