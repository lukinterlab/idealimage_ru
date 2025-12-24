from django.urls import path
from . import views, api_views

app_name = 'donations'

urlpatterns = [
    # Основные страницы
    path('', views.donation_page, name='donation_page'),
    path('quick/', views.quick_donation, name='quick_donation'),
    
    # Обработка платежей
    path('process/<uuid:donation_id>/', views.process_payment, name='process_payment'),
    path('qr/<uuid:donation_id>/', views.show_qr, name='show_qr'),
    path('return/<uuid:donation_id>/', views.payment_return, name='payment_return'),
    path('status/<uuid:donation_id>/', views.donation_status, name='donation_status'),
    
    # Публичные страницы
    path('services/', views.services_page, name='services_page'),
    path('subscribe/premium/', views.subscribe_premium_page, name='subscribe_premium'),
    path('subscribe/ai/', views.subscribe_ai_page, name='subscribe_ai'),
    path('marathons/', views.marathons_catalog, name='marathons_catalog'),
    path('advertising/', views.advertising_marketplace, name='advertising_marketplace'),
    path('debug/', views.payment_debug, name='payment_debug'),
    path('list/', views.donation_list, name='donation_list'),
    
    # Страницы бонусов
    path('my-bonuses/', views.author_bonuses_page, name='author_bonuses'),
    path('admin/bonuses/', views.admin_bonuses_dashboard, name='admin_bonuses_dashboard'),
    path('admin/bonuses/registry/', views.payment_registry_page, name='payment_registry'),
    path('admin/penalty-reward/create/', views.penalty_reward_create, name='penalty_reward_create'),
    path('admin/penalty-reward/<int:pr_id>/edit/', views.penalty_reward_edit, name='penalty_reward_edit'),
    
    # API endpoints
    path('api/check-status/<uuid:donation_id>/', views.check_payment_status, name='check_payment_status'),
    path('api/author-stats/<int:author_id>/', api_views.api_author_stats, name='api_author_stats'),
    path('api/current-week/', api_views.api_current_week_stats, name='api_current_week_stats'),
    path('api/calculate-preview/', api_views.api_calculate_preview, name='api_calculate_preview'),
    path('api/mark-payment/', api_views.api_mark_payment, name='api_mark_payment'),
    path('api/add-penalty-reward/', api_views.api_add_penalty_reward, name='api_add_penalty_reward'),
    path('api/update-formula/', api_views.api_update_formula, name='api_update_formula'),
    path('api/generate-report/', api_views.api_generate_report, name='api_generate_report'),
    path('api/author-detail/<int:author_id>/', api_views.api_author_detail_stats, name='api_author_detail_stats'),
    path('api/bonuses/<int:bonus_id>/', views.api_bonus_details, name='api_bonus_details'),
    path('api/bonuses/list/', views.api_author_bonuses, name='api_author_bonuses'),
    
    # API для управления ролями и формулами
    path('api/roles/', api_views.api_roles_list, name='api_roles_list'),
    path('api/role/create/', api_views.api_role_create, name='api_role_create'),
    path('api/role/<int:role_id>/update/', api_views.api_role_update, name='api_role_update'),
    path('api/role/<int:role_id>/delete/', api_views.api_role_delete, name='api_role_delete'),
    path('api/formula/<int:role_id>/update/', api_views.api_formula_update, name='api_formula_update'),
    
    # API для управления штрафами/премиями
    path('api/penalties/', api_views.api_penalties_list, name='api_penalties_list'),
    path('api/penalty/create/', api_views.api_penalty_create, name='api_penalty_create'),
    path('api/penalty/<int:penalty_id>/update/', api_views.api_penalty_update, name='api_penalty_update'),
    path('api/penalty/<int:penalty_id>/delete/', api_views.api_penalty_delete, name='api_penalty_delete'),
    path('api/authors/', api_views.api_authors_list, name='api_authors_list'),
    
    # Webhooks
    path('webhook/yandex/', views.yandex_webhook, name='yandex_webhook'),
    path('webhook/sber/', views.sber_webhook, name='sber_webhook'),
]
