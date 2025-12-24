"""
URL конфигурация для advertising
"""
from django.urls import path
from . import views

app_name = 'advertising'

urlpatterns = [
    # Главный дашборд
    path('', views.advertising_dashboard, name='dashboard'),
    
    # Редирект кликов
    path('click/banner/<int:banner_id>/', views.banner_click_redirect, name='banner_click'),
    path('click/context/<int:context_ad_id>/', views.context_click_redirect, name='context_click'),
    path('click/insertion/<int:insertion_id>/', views.insertion_click_redirect, name='insertion_click'),
    
    # AJAX endpoints
    path('api/track/impression/', views.track_impression, name='track_impression'),
    path('api/banner/<int:banner_id>/', views.banner_detail_api, name='banner_detail_api'),
    path('api/popup-status/', views.popup_status_api, name='popup_status_api'),
    path('api/popup-toggle-test/', views.popup_toggle_test_api, name='popup_toggle_test_api'),
    
    # API для расписания
    path('api/schedule/<int:schedule_id>/', views.schedule_detail_api, name='schedule_detail_api'),
    path('api/schedule/create/', views.schedule_create_api, name='schedule_create_api'),
    path('api/schedule/<int:schedule_id>/update/', views.schedule_update_api, name='schedule_update_api'),
    path('api/schedule/<int:schedule_id>/toggle/', views.schedule_toggle_api, name='schedule_toggle_api'),
    path('api/schedule/<int:schedule_id>/delete/', views.schedule_delete_api, name='schedule_delete_api'),
    
    # Управление баннерами
    path('banners/', views.banners_manage, name='banners_manage'),
    path('banners/create/', views.banner_create, name='banner_create'),
    path('banners/<int:banner_id>/edit/', views.banner_edit, name='banner_edit'),
    path('banners/<int:banner_id>/delete/', views.banner_delete, name='banner_delete'),
    path('banners/<int:banner_id>/update-preview/', views.banner_update_preview, name='banner_update_preview'),
    
    # Управление контекстной рекламой
    path('context/', views.context_ads_manage, name='context_ads_manage'),
    path('context/create/', views.context_ad_create, name='context_ad_create'),
    path('context/<int:ad_id>/edit/', views.context_ad_edit, name='context_ad_edit'),
    path('context/<int:ad_id>/delete/', views.context_ad_delete, name='context_ad_delete'),
    
    # Управление кампаниями
    path('campaigns/', views.campaigns_list, name='campaigns_list'),
    path('campaigns/create/', views.campaign_create, name='campaign_create'),
    path('campaigns/<int:campaign_id>/', views.campaign_detail, name='campaign_detail'),
    path('campaigns/<int:campaign_id>/edit/', views.campaign_edit, name='campaign_edit'),
    
    # Управление рекламодателями
    path('advertisers/', views.advertisers_list, name='advertisers_list'),
    path('advertisers/create/', views.advertiser_create, name='advertiser_create'),
    path('advertisers/<int:advertiser_id>/', views.advertiser_detail, name='advertiser_detail'),
    
    # Аналитика
    path('analytics/', views.analytics_dashboard, name='analytics'),
    path('analytics/export/', views.analytics_export, name='analytics_export'),
    
    # AI рекомендации
    path('recommendations/', views.ai_recommendations, name='recommendations'),
    path('recommendations/<int:rec_id>/apply/', views.apply_recommendation, name='apply_recommendation'),
    
    # Журнал действий
    path('action-log/', views.action_log_view, name='action_log'),
    path('action-log/<int:log_id>/revert/', views.revert_action, name='revert_action'),
    path('action-log/<int:log_id>/replay/', views.replay_action, name='replay_action'),
    
    # Внешние скрипты
    path('external-scripts/', views.external_scripts_list, name='external_scripts_list'),
    path('external-scripts/create/', views.external_script_create, name='external_script_create'),
    path('external-scripts/<int:script_id>/', views.external_script_detail, name='external_script_detail'),
    path('external-scripts/<int:script_id>/edit/', views.external_script_edit, name='external_script_edit'),
    path('external-scripts/<int:script_id>/delete/', views.external_script_delete, name='external_script_delete'),
    path('external-scripts/<int:script_id>/toggle/', views.external_script_toggle, name='external_script_toggle'),
    
    # Ads.txt
    path('ads-txt/', views.ads_txt_manage, name='ads_txt_manage'),
    path('ads-txt/update/', views.ads_txt_update, name='ads_txt_update'),
]

