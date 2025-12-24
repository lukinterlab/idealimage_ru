from django.urls import path, include

from .views import *

try:
    from Asistent import views as asistent_views
    asistent_enabled = True
except ImportError:
    asistent_enabled = False

app_name = 'Visitor'

urlpatterns = [
    path('adminka/', adminka, name='adminka'),
    path('user/edit/', ProfileUpdateView.as_view(), name='profile_edit'),
    path('user/<str:slug>/', ProfileView.as_view(), name='profile_detail'),
    path('my-comments/', AuthorCommentsView.as_view(), name='author_comments'),
    path('register/', UserRegisterView.as_view(), name='user-register'),
    path('login/', UserLoginView.as_view(), name='user-login'),
    path('logout/', UserLogoutView.as_view(), name='user-logout'),
    path('feedback/', FeedbackCreateView.as_view(), name='feedback'),
    
    # Новые маршруты для системы ролей и личного кабинета
    path('cabinet/', PersonalCabinetView.as_view(), name='personal_cabinet'),
    path('apply-role/', RoleApplicationCreateView.as_view(), name='apply_role'),
    path('role-instructions/<str:role>/', role_instructions, name='role_instructions'),
    path('subscribe/<int:author_id>/', toggle_subscription, name='toggle_subscription'),
    path('like/<int:post_id>/', toggle_like, name='toggle_like'),
    
    # AI-задания для авторов (перенесено из Asistent)
    path('tasks/take/<int:task_id>/', take_task, name='take_task'),
    path('tasks/reject/<int:task_id>/', reject_task_by_author, name='reject_task'),
    path('assignments/<int:assignment_id>/submit/', submit_task_assignment, name='submit_assignment'),
    path('notifications/', notifications_list, name='notifications'),
    path('notifications/<int:notification_id>/read/', mark_notification_read, name='mark_notification_read'),
    path('balance/', balance_history, name='balance_history'),
    
    # Панель администратора
    path('superuser/dashboard/', SuperuserDashboardView.as_view(), name='superuser_dashboard'),
    path('superuser/process-application/<int:application_id>/', process_role_application, name='process_role_application'),
    path('superuser/view-cabinet/<int:user_id>/', view_user_cabinet, name='view_user_cabinet'),
    
    # API для динамической загрузки контента профиля
    path('api/profile/<int:user_id>/comments/', profile_comments_api, name='profile_comments_api'),
    path('api/profile/<int:user_id>/favorites/', profile_favorites_api, name='profile_favorites_api'),
    path('api/profile/<int:user_id>/bookmarks/', profile_bookmarks_api, name='profile_bookmarks_api'),
    
    # Модерация комментариев
    path('comment/<int:comment_id>/edit/', edit_comment, name='edit_comment'),
    path('comment/<int:comment_id>/delete/', delete_comment, name='delete_comment'),
    
    # Cookie Consent (GDPR/РФ)
    path('api/cookie-consent/', save_cookie_consent, name='save_cookie_consent'),
]

# AI-Ассистент: Интегрированные маршруты (если доступен)
if asistent_enabled:
    urlpatterns += [
        # Управление заданиями
        path('superuser/ai/task/<int:task_id>/approve/', asistent_views.approve_task, name='ai_approve_task'),
        path('superuser/ai/task/<int:task_id>/reject/', asistent_views.reject_task, name='ai_reject_task'),
        
        # Расписания AI
        path('superuser/ai/schedules/', asistent_views.ai_schedules, name='ai_schedules'),
        path('superuser/ai/schedule/<int:schedule_id>/run/', asistent_views.run_ai_schedule, name='ai_run_schedule'),
        
        # Календарь заданий
        path('superuser/ai/calendar/', asistent_views.task_calendar, name='task_calendar'),
    ]