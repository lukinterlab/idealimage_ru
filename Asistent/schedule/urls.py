"""
URL-маршруты для системы расписаний.
Префикс: /schedules/ (рекомендуется подключать в главном urls.py)
"""
from django.urls import path
from . import views

app_name = 'schedule'

urlpatterns = [
    # Дашборд
    path('', views.schedule_dashboard, name='schedule_dashboard'),
    
    # Список расписаний
    path('list/', views.schedule_list, name='schedule_list'),
    
    # Управление расписаниями
    path('create/', views.schedule_create, name='schedule_create'),
    path('<int:schedule_id>/', views.schedule_detail, name='schedule_detail'),
    path('<int:schedule_id>/edit/', views.schedule_edit, name='schedule_edit'),
    path('<int:schedule_id>/delete/', views.schedule_delete, name='schedule_delete'),
    path('<int:schedule_id>/toggle/', views.schedule_toggle, name='schedule_toggle'),
    path('<int:schedule_id>/run/', views.schedule_run_now, name='schedule_run_now'),
    
    # Специальные действия
    path('horoscopes/run-all/', views.run_all_horoscopes, name='run_all_horoscopes'),
]

