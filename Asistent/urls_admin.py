"""
URL маршруты для админ-функций AI-Ассистента
Интегрированы в панель суперюзера: /visitor/superuser/ai/
"""
from django.urls import path
from . import views

app_name = 'asistent_admin'

urlpatterns = [
    # Dashboard метрик AI
    path('dashboard/', views.ai_dashboard, name='dashboard'),
    
    # Управление заданиями
    path('task/<int:task_id>/approve/', views.approve_task, name='approve_task'),
    path('task/<int:task_id>/reject/', views.reject_task, name='reject_task'),
    path('task/create/', views.create_task, name='create_task'),
    path('tasks/calendar/', views.task_calendar, name='task_calendar'),
    
    # Управление AI-расписаниями
    path('schedules/', views.ai_schedules, name='ai_schedules'),
    path('schedule/create/', views.create_ai_schedule, name='create_ai_schedule'),
    path('schedule/<int:schedule_id>/run/', views.run_ai_schedule, name='run_ai_schedule'),
    path('schedule/<int:schedule_id>/run-now/', views.run_schedule_now, name='run_schedule'),
    
    # Критерии модерации
    path('criteria/', views.moderation_criteria, name='moderation_criteria'),
]

