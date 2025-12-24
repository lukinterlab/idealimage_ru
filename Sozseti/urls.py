"""
URLs для приложения Sozseti
"""
from django.urls import path
from .dashboard import views as dashboard_views

app_name = 'sozseti'

urlpatterns = [
    # Главный дашборд
    path('dashboard/', dashboard_views.DashboardOverview.as_view(), name='dashboard'),
    
    # Каналы
    path('channels/', dashboard_views.ChannelsList.as_view(), name='channels_list'),
    path('channel/<int:pk>/', dashboard_views.ChannelPerformance.as_view(), name='channel_detail'),
    
    # Календарь
    path('calendar/', dashboard_views.ContentCalendar.as_view(), name='calendar'),
    
    # Реклама
    path('advertising/', dashboard_views.AdvertisingDashboard.as_view(), name='advertising'),
    
    # AI-Агент
    path('ai-agent/', dashboard_views.AIAgentDashboard.as_view(), name='ai_agent'),
]

