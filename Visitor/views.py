from django.views.generic import *
from django.shortcuts import render, redirect, get_object_or_404
from django.db import transaction
from django.urls import reverse_lazy
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.utils import timezone
from django.db.models import Count, Q, Sum
from django.contrib.auth import get_user_model
from .models import *
from .models import Like as VisitorLike  # Старая модель (не используется)
from .forms import *
from blog.models import Post, Comment
from blog.models_likes import Like, Bookmark  # Основные модели лайков и закладок
from blog.forms import CommentForm
from utilits.email import send_contact_email_message
from utilits.utils import get_client_ip
from django.core.paginator import Paginator
from django.http import HttpResponseRedirect, JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
import logging
import json

# Импорт API функций для профиля
from .profile_api_views import profile_comments_api, profile_favorites_api, profile_bookmarks_api

from Asistent.models import (
    ContentTask,
    TaskAssignment,
    AuthorTaskRejection,
    AuthorNotification,
    AuthorBalance,
)
from Asistent.services.task_actions import take_task as take_task_action

logger = logging.getLogger(__name__)

User = get_user_model()


# Список ВСЕх статей
def adminka(request):
    posts = Post.objects.all()                             ##.select_related('user')
    context = {
        'posts': posts,
    }

    return render(request,
                  'adminka/blog.html',
                  context)


# Список статей автора
def post_list_author(request, slug):
    posts = Post.objects.filter(autor=slug).order_by('-updated')
    context = {
        'posts': posts,
    }
    return render(request,
                  'adminka/blog.html',
                  context)

# Просмотр профиля автора
class ProfileView(DetailView):
    """ Представление для просмотра профиля """
    model = Profile
    context_object_name = 'profile'
    template_name = 'visitor/profile_home_tailwind.html'
    
    # Контекст данных для профиля автора
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # ВАЖНО: Показывать только ОПУБЛИКОВАННЫЕ статьи автора
        posts = Post.objects.filter(
            author=self.object.vizitor,
            status='published'
        ).order_by('-created')
        
        # Создаем Paginator объект, первый аргумент - это список, второй - количество элементов на страницу
        paginator = Paginator(posts, 12)  # показываем по 12 постов на странице

        # Получаем номер текущей страницы из параметров запроса
        page_number = self.request.GET.get('page')

        # Получаем соответствующую выборку постов для текущей страницы
        page_obj = paginator.get_page(page_number)

        # Получаем категории, в которых есть статьи автора (только published)
        from blog.models import Category
        from django.db.models import Count, Q
        author_categories = Category.objects.filter(
            posts__author=self.object.vizitor,
            posts__status='published'
        ).annotate(
            author_posts_count=Count('posts', filter=Q(posts__author=self.object.vizitor, posts__status='published'))
        ).distinct().order_by('title')

        # Получаем популярные теги из статей автора (только published)
        from taggit.models import Tag
        author_tags = Tag.objects.filter(
            taggit_taggeditem_items__content_type__model='post',
            taggit_taggeditem_items__object_id__in=posts.values_list('id', flat=True)
        ).annotate(
            posts_count=Count('taggit_taggeditem_items')
        ).distinct().order_by('-posts_count')[:15]  # Топ 15 популярных тегов автора

        # Добавляем в контекст объект страницы
        context['page_obj'] = page_obj
        context['title'] = f'Страница пользователя: {self.object.vizitor.username}'
        context['page_title'] = f'{self.object.vizitor.username} — Автор на IdealImage.ru'
        context['page_description'] = f'Профиль автора {self.object.vizitor.username}. Все статьи, публикации и активность на сайте IdealImage.ru'
        context['posts'] = posts
        context['categorys'] = author_categories  # Категории автора для меню
        context['tags'] = author_tags  # Популярные теги автора
        context['is_author_page'] = True  # Флаг, что мы на странице автора
        
        # Статистика подписок
        context['subscribers_count'] = Subscription.objects.filter(author=self.object.vizitor).count()
        context['subscriptions_count'] = Subscription.objects.filter(subscriber=self.object.vizitor).count()
        
        # Добавляем информацию о подписках (если пользователь залогинен)
        if self.request.user.is_authenticated:
            context['is_subscribed'] = Subscription.objects.filter(
                subscriber=self.request.user,
                author=self.object.vizitor
            ).exists()
            
            # Если это свой профиль, добавляем информацию о заявках
            if self.request.user == self.object.vizitor:
                context['has_pending_applications'] = RoleApplication.objects.filter(
                    user=self.request.user,
                    status='pending'
                ).exists()
        
        # ЧЕРНОВИКИ: доступны только автору, администратору и AI
        draft_posts = None
        can_view_drafts = False
        
        if self.request.user.is_authenticated:
            # Проверка прав: автор, суперюзер, администратор
            is_owner = self.request.user == self.object.vizitor
            is_admin = self.request.user.is_superuser or (hasattr(self.request.user, 'profile') and self.request.user.profile.is_admin)
            
            if is_owner or is_admin:
                can_view_drafts = True
                draft_posts = Post.objects.filter(
                    author=self.object.vizitor,
                    status='draft'
                ).order_by('-created')
        
        context['can_view_drafts'] = can_view_drafts
        context['draft_posts'] = draft_posts
        context['drafts_count'] = draft_posts.count() if draft_posts else 0

        return context


""" Представление для редактирования профиля  """
class ProfileUpdateView(UpdateView):
    """ Представление для редактирования профиля  """
    model = Profile
    form_class = ProfileUpdateForm
    template_name = 'visitor/profile_edit_tailwind.html'

    def get_object(self, queryset=None):
        return self.request.user.profile

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Редактирование профиля пользователя: {self.request.user.username}'
        context['page_title'] = f'Редактирование профиля — {self.request.user.username}'
        context['page_description'] = f'Редактирование профиля пользователя {self.request.user.username} на сайте IdealImage.ru'
        if self.request.POST:
            context['user_form'] = UserUpdateForm(self.request.POST, instance=self.request.user)
        else:
            context['user_form'] = UserUpdateForm(instance=self.request.user)
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        user_form = context['user_form']
        with transaction.atomic():
            if all([form.is_valid(), user_form.is_valid()]):
                user_form.save()
                form.save()
            else:
                context.update({'user_form': user_form})
                return self.render_to_response(context)
        return super(ProfileUpdateView, self).form_valid(form)

    def get_success_url(self):
        return reverse_lazy('Visitor:profile_detail', kwargs={'slug': self.object.slug})

""" Представление для регистрации на сайте  """
class UserRegisterView(SuccessMessageMixin, CreateView):
    """
    Представление регистрации на сайте с формой регистрации
    """
    form_class = UserRegisterForm
    template_name = 'visitor/user_register_tailwind.html'
    success_message = 'Вы успешно зарегистрировались и вошли на сайт!'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Регистрация на сайте'
        context['page_title'] = 'Регистрация — IdealImage.ru'
        context['page_description'] = 'Регистрация на сайте IdealImage.ru — создайте свой профиль, публикуйте статьи, зарабатывайте деньги'
        return context
    
    def form_valid(self, form):
        """Сохранение согласия на обработку данных и автоматический вход"""
        from django.contrib.auth import login
        
        response = super().form_valid(form)
        
        # Обновляем профиль пользователя
        profile = self.object.profile
        profile.agreed_to_terms = True
        profile.agreed_at = timezone.now()
        profile.save()
        
        # Автоматически входим пользователя после регистрации
        login(self.request, self.object, backend='django.contrib.auth.backends.ModelBackend')
        
        # Устанавливаем долгую сессию
        self.request.session.set_expiry(31536000)  # 365 дней
        
        # Логируем регистрацию
        ActivityLog.objects.create(
            user=self.object,
            action_type='user_registered',
            description=f'Пользователь {self.object.username} зарегистрировался и автоматически вошел'
        )
        
        # Перенаправляем на главную вместо страницы входа
        return redirect('blog:post_list')
    
    def get_success_url(self):
        """Перенаправление после успешной регистрации"""
        return reverse_lazy('blog:post_list')
 
""" Представление для авторизации на сайте  """
class UserLoginView(SuccessMessageMixin, LoginView):
    """
    Авторизация на сайте с автоматической долгой сессией
    """
    form_class = UserLoginForm
    template_name = 'visitor/user_login_tailwind.html'
    next_page = 'blog:post_list'
    success_message = 'Добро пожаловать на сайт!'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Авторизация на сайте'
        context['page_title'] = 'Вход — IdealImage.ru'
        context['page_description'] = 'Войдите в свой аккаунт на сайте IdealImage.ru'
        return context
    
    def form_valid(self, form):
        """Устанавливаем долгую сессию для всех пользователей"""
        response = super().form_valid(form)
        
        # Автоматически устанавливаем долгую сессию (1 год)
        self.request.session.set_expiry(31536000)  # 365 дней
        
        # Логируем вход
        ActivityLog.objects.create(
            user=self.request.user,
            action_type='user_registered',  # Используем существующий тип
            description=f'Пользователь {self.request.user.username} вошел в систему'
        )
        
        return response
        
""" Представление для выхода с сайта  """
class UserLogoutView(LogoutView):
    """
    Выход с сайта
    """
    template_name = 'blog/post_list_tailwind.html'
    next_page = 'blog:post_list'
    http_method_names = ['get', 'post', 'options']  # Разрешаем GET для обратной совместимости
    
    def get(self, request, *args, **kwargs):
        """Разрешаем GET запрос для logout"""
        return self.post(request, *args, **kwargs)
    
""" Представление для отправки обратной связи  """
class FeedbackCreateView(SuccessMessageMixin, CreateView):
    model = Feedback
    form_class = FeedbackCreateForm
    success_message = 'Ваше письмо успешно отправлено администрации сайта'
    template_name = 'visitor/feedback.html'
    extra_context = {
        'title': 'Контактная форма',
        'page_title': 'Контактная форма — IdealImage.ru',
        'page_description': 'Свяжитесь с нами через контактную форму на сайте IdealImage.ru'
    }
    success_url = reverse_lazy('Home:home')

    def form_valid(self, form):
        if form.is_valid():
            feedback = form.save(commit=False)
            feedback.ip_address = get_client_ip(self.request)
            if self.request.user.is_authenticated:
                feedback.user = self.request.user
            send_contact_email_message(feedback.subject, feedback.email, feedback.content, feedback.ip_address, feedback.user_id)
        return super().form_valid(form)

""" Представление для просмотра комментариев к статьям автора  """
class AuthorCommentsView(LoginRequiredMixin, ListView):
    """Страница комментариев к статьям автора"""
    model = Comment
    template_name = 'visitor/author_comments_tailwind.html'
    context_object_name = 'comments'
    paginate_by = 20
    login_url = 'Visitor:user-login'
    
    def get_queryset(self):
        # Получаем только комментарии к статьям текущего пользователя
        return Comment.objects.filter(
            post__author=self.request.user,
            active=True
        ).select_related('post', 'parent').order_by('-created')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Комментарии к моим статьям'
        context['page_description'] = 'Управление комментариями к статьям автора на сайте IdealImage.ru'
        context['unanswered_count'] = Comment.objects.filter(
            post__author=self.request.user,
            active=True,
            parent__isnull=True
        ).exclude(
            id__in=Comment.objects.filter(
                post__author=self.request.user,
                parent__isnull=False
            ).values_list('parent_id', flat=True)
        ).count()
        return context
    
    def post(self, request, *args, **kwargs):
        """Обработка ответов на комментарии"""
        comment_form = CommentForm(data=request.POST)
        if comment_form.is_valid():
            new_comment = comment_form.save(commit=False)
            parent_id = request.POST.get('parent')
            
            if parent_id:
                try:
                    parent_comment = Comment.objects.get(id=parent_id)
                    new_comment.post = parent_comment.post
                    new_comment.parent = parent_comment
                    new_comment.save()
                    return HttpResponseRedirect(request.path + f'#comment-{parent_id}')
                except Comment.DoesNotExist:
                    pass
        
        return self.get(request, *args, **kwargs)

""" Представление для просмотра личного кабинета пользователя  """
class PersonalCabinetView(LoginRequiredMixin, TemplateView):
    """Расширенный личный кабинет пользователя"""
    template_name = 'visitor/personal_cabinet.html'
    login_url = 'Visitor:user-login'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        profile = user.profile
        
        context['profile'] = profile
        context['title'] = f'Личный кабинет - {user.username}'
        context['page_title'] = f'Личный кабинет — {user.username}'
        context['page_description'] = f'Личный кабинет пользователя {user.username}. Управление профилем, статьями, подписками и активностью на IdealImage.ru'
        
        # Подписки пользователя
        subscriptions = Subscription.objects.filter(subscriber=user).select_related('author__profile')
        context['subscriptions'] = subscriptions
        context['subscriptions_count'] = subscriptions.count()
        
        # Последние статьи из подписок
        if subscriptions.exists():
            subscribed_authors = [sub.author for sub in subscriptions]
            context['subscribed_posts'] = Post.objects.filter(
                author__in=subscribed_authors,
                status='published'
            ).order_by('-created')[:10]
        
        # Комментарии пользователя (по имени, т.к. нет ForeignKey к User)
        context['user_comments'] = Comment.objects.filter(
            author_comment=user.username,
            active=True
        ).select_related('post').order_by('-created')[:10]
        
        # Заявки на роли (показываем только pending и rejected)
        # Одобренные заявки не показываем, т.к. роль уже получена
        context['role_applications'] = RoleApplication.objects.filter(
            user=user
        ).exclude(
            status='approved'  # Скрываем одобренные заявки
        ).order_by('-applied_at')
        
        # Проверяем наличие активных заявок
        context['has_pending_applications'] = RoleApplication.objects.filter(
            user=user,
            status='pending'
        ).exists()
        
        # Если пользователь автор
        if profile.is_author:
            # Подписчики автора
            subscribers = Subscription.objects.filter(author=user).select_related('subscriber__profile')
            context['subscribers'] = subscribers
            context['subscribers_count'] = subscribers.count()
            
            # Статистика автора
            author_posts = Post.objects.filter(author=user)
            context['author_posts_count'] = author_posts.count()
            
            # Лайки
            total_likes = Like.objects.filter(post__author=user).count()
            context['total_likes'] = total_likes
            
            # Комментарии к статьям автора (исключаем свои по имени)
            comments_to_author = Comment.objects.filter(
                post__author=user,
                active=True
            ).exclude(author_comment=user.username).count()
            context['comments_to_author'] = comments_to_author
            
            # Донаты
            donations = Donation.objects.filter(author=user).aggregate(
                total=Sum('amount'),
                count=Count('id')
            )
            context['total_donations'] = donations['total'] or 0
            context['donations_count'] = donations['count']
            
            # Последние комментарии к статьям автора
            context['recent_comments_to_posts'] = Comment.objects.filter(
                post__author=user,
                active=True
            ).exclude(author_comment=user.username).select_related('post').order_by('-created')[:5]
            
            # Премия
            context['total_bonus'] = profile.total_bonus
            
            # Данные заданий AI-ассистента для авторов
            from Asistent.models import TaskAssignment, AuthorTaskRejection, AuthorNotification, ContentTask
            
            # Получаем отклонённые задания автором
            rejected_task_ids = AuthorTaskRejection.objects.filter(author=user).values_list('task_id', flat=True)
            
            # Получаем задания которые автор уже взял
            taken_task_ids = TaskAssignment.objects.filter(author=user).values_list('task_id', flat=True)
            
            # Доступные задания (не отклонённые, не взятые, не закрытые)
            available_tasks = ContentTask.objects.filter(
                status='available'
            ).exclude(
                id__in=rejected_task_ids
            ).exclude(
                id__in=taken_task_ids
            ).filter(
                deadline__gt=timezone.now()
            )
            
            # Фильтруем по лимиту выполнений
            available_tasks_filtered = []
            for task in available_tasks:
                if task.get_completions_count() < task.max_completions:
                    available_tasks_filtered.append(task)
            
            # Задания автора (в работе и выполненные)
            my_assignments = TaskAssignment.objects.filter(
                author=user
            ).select_related('task', 'article').order_by('-taken_at')
            
            # Баланс из донатов (уже есть total_donations, добавим balance)
            context['balance'] = context['total_donations']
            
            # Уведомления AI-ассистента
            ai_notifications = AuthorNotification.objects.filter(
                recipient=user,
                is_read=False
            ).order_by('-created_at')[:5]
            
            # Статистика заданий
            context['ai_tasks_stats'] = {
                'total_completed': my_assignments.filter(status='approved').count(),
                'total_earned': Donation.objects.filter(
                    author=user,
                    message__contains='Выполнение задания'
                ).aggregate(total=Sum('amount'))['total'] or 0,
                'tasks_in_progress': my_assignments.filter(status='in_progress').count(),
                'unread_notifications': ai_notifications.count()
            }
            
            context['available_tasks'] = available_tasks_filtered
            context['my_assignments'] = my_assignments
            context['ai_notifications'] = ai_notifications
            
            # Бонусы и баланс автора
            from donations.models import AuthorBonus, BonusPaymentRegistry
            from Asistent.models import AuthorBalance
            
            # Последние бонусы (для превью)
            recent_bonuses = AuthorBonus.objects.filter(
                author=user
            ).select_related('role_at_calculation').order_by('-created_at')[:10]
            
            # История баланса (для превью)
            recent_transactions = AuthorBalance.objects.filter(
                author=user
            ).order_by('-created_at')[:10]
            
            # Статистика бонусов
            total_bonuses = AuthorBonus.objects.filter(author=user).aggregate(
                total=Sum('total_bonus')
            )['total'] or 0
            
            paid_bonuses = AuthorBonus.objects.filter(
                author=user,
                status='paid'
            ).aggregate(total=Sum('total_bonus'))['total'] or 0
            
            context['bonuses_stats'] = {
                'total': total_bonuses,
                'paid': paid_bonuses,
                'pending': total_bonuses - paid_bonuses,
            }
            context['recent_bonuses'] = recent_bonuses
            context['recent_transactions'] = recent_transactions
        
        # Уведомления (для всех пользователей)
        from Asistent.models import AuthorNotification
        all_notifications = AuthorNotification.objects.filter(
            recipient=user
        ).order_by('-created_at')[:20]
        
        context['all_notifications'] = all_notifications
        context['notifications_count'] = AuthorNotification.objects.filter(
            recipient=user, is_read=False
        ).count()
        
        return context


@login_required
def notifications_list(request):
    """API: Список уведомлений с пагинацией"""
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        page_number = request.GET.get('page', 1)
        notifications = AuthorNotification.objects.filter(
            recipient=request.user
        ).order_by('-created_at')

        paginator = Paginator(notifications, 20)
        page_obj = paginator.get_page(page_number)

        data = {
            'notifications': [{
                'id': n.id,
                'title': n.title,
                'message': n.message,
                'notification_type': n.notification_type,
                'is_read': n.is_read,
                'created_at': n.created_at.strftime('%d.%m.%Y %H:%M'),
            } for n in page_obj],
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous(),
            'current_page': page_obj.number,
            'total_pages': paginator.num_pages,
        }

        return JsonResponse(data)

    return redirect('Visitor:personal_cabinet')


@login_required
@require_POST
def mark_notification_read(request, notification_id):
    """Отметить уведомление как прочитанное"""
    notification = get_object_or_404(
        AuthorNotification,
        id=notification_id,
        recipient=request.user
    )
    notification.mark_as_read()

    return JsonResponse({'success': True})


@login_required
def balance_history(request):
    """API: История баланса с пагинацией"""
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        page_number = request.GET.get('page', 1)
        transactions = AuthorBalance.objects.filter(
            author=request.user
        ).order_by('-created_at')

        paginator = Paginator(transactions, 20)
        page_obj = paginator.get_page(page_number)

        balance = Donation.objects.filter(
            author=request.user
        ).aggregate(total=Sum('amount'))['total'] or 0

        data = {
            'balance': float(balance),
            'transactions': [{
                'id': t.id,
                'transaction_type': t.transaction_type,
                'amount': float(t.amount),
                'description': t.description,
                'task_title': t.task.title if t.task else None,
                'created_at': t.created_at.strftime('%d.%m.%Y %H:%M'),
            } for t in page_obj],
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous(),
            'current_page': page_obj.number,
            'total_pages': paginator.num_pages,
        }

        return JsonResponse(data)

    return redirect('Visitor:personal_cabinet')


@login_required
@require_POST
def take_task(request, task_id):
    """Автор берёт задание в работу"""
    task = get_object_or_404(ContentTask, id=task_id)

    success, reason = take_task_action(request.user, task)
    if success:
        messages.success(request, f'✅ Вы взяли задание "{task.title}" в работу!')
    else:
        messages.error(request, f'Не удалось взять задание: {reason}')

    return redirect('Visitor:personal_cabinet')


@login_required
@require_POST
def reject_task_by_author(request, task_id):
    """Автор отклоняет задание навсегда"""
    task = get_object_or_404(ContentTask, id=task_id)

    AuthorTaskRejection.objects.get_or_create(
        author=request.user,
        task=task
    )

    messages.info(request, f'Задание "{task.title}" отклонено. Оно больше не будет отображаться.')

    return redirect('Visitor:personal_cabinet')


@login_required
@require_POST
def submit_task_assignment(request, assignment_id):
    """Автор сдаёт статью по заданию"""
    assignment = get_object_or_404(
        TaskAssignment,
        id=assignment_id,
        author=request.user,
        status='in_progress'
    )

    article_id = request.POST.get('article_id')

    if not article_id:
        messages.error(request, 'Не указана статья.')
        return redirect('Visitor:personal_cabinet')

    article = get_object_or_404(Post, id=article_id, author=request.user)

    if assignment.submit_article(article):
        messages.success(request, '⏳ Статья отправлена на AI модерацию...')

        try:
            from django_q.tasks import async_task
            task_id = async_task('Asistent.tasks.moderate_task_article_task', assignment.id)
            messages.info(request, f'🤖 AI-Ассистент проверяет вашу статью. Результат придёт в уведомлениях.')
        except Exception as e:
            logger.error(f"Ошибка запуска AI модерации: {e}")
            messages.warning(request, 'Статья отправлена, но AI модерация не запустилась. Обратитесь к администратору.')
    else:
        messages.error(request, 'Не удалось отправить статью.')

    return redirect('Visitor:personal_cabinet')

""" Представление для подачи заявки на роль  """
class RoleApplicationCreateView(LoginRequiredMixin, CreateView):
    """Подача заявки на роль"""
    model = RoleApplication
    form_class = RoleApplicationForm
    template_name = 'visitor/role_application.html'
    login_url = 'Visitor:user-login'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Подать заявку на роль'
        context['page_title'] = 'Подача заявки на роль — IdealImage.ru'
        context['page_description'] = 'Подайте заявку на роль автора, модератора или маркетолога на сайте IdealImage.ru'
        
        # Проверяем есть ли уже активные заявки
        pending_applications = RoleApplication.objects.filter(
            user=self.request.user,
            status='pending'
        )
        context['has_pending_applications'] = pending_applications.exists()
        context['pending_applications'] = pending_applications
        
        return context
    
    def form_valid(self, form):
        # Проверяем, нет ли уже заявки на эту роль
        role = form.cleaned_data['role']
        existing = RoleApplication.objects.filter(
            user=self.request.user,
            role=role,
            status='pending'
        ).exists()
        
        if existing:
            messages.warning(self.request, 'У вас уже есть активная заявка на эту роль!')
            return redirect('Visitor:personal_cabinet')
        
        form.instance.user = self.request.user
        response = super().form_valid(form)
        
        # Логируем подачу заявки
        ActivityLog.objects.create(
            user=self.request.user,
            action_type='role_applied',
            target_object_id=self.object.id,
            description=f'Пользователь {self.request.user.username} подал заявку на роль {self.object.get_role_display()}'
        )
        
        messages.success(
            self.request,
            f'Ваша заявка на роль "{self.object.get_role_display()}" принята! Администрация рассмотрит её в течение 3 дней.'
        )
        return response
    
    def get_success_url(self):
        return reverse_lazy('Visitor:personal_cabinet')

""" Представление для подписки на автора  """
@login_required
def toggle_subscription(request, author_id):
    """Подписка/отписка на автора"""
    author = get_object_or_404(User, id=author_id)
    
    if author == request.user:
        messages.warning(request, 'Вы не можете подписаться на самого себя!')
        return redirect(request.META.get('HTTP_REFERER', '/'))
    
    subscription = Subscription.objects.filter(subscriber=request.user, author=author).first()
    
    if subscription:
        subscription.delete()
        messages.success(request, f'Вы отписались от {author.username}')
    else:
        Subscription.objects.create(subscriber=request.user, author=author)
        messages.success(request, f'Вы подписались на {author.username}')
        
        # Логируем подписку
        ActivityLog.objects.create(
            user=request.user,
            action_type='subscription_added',
            target_user=author,
            description=f'{request.user.username} подписался на {author.username}'
        )
    
    return redirect(request.META.get('HTTP_REFERER', '/'))

""" Представление для лайка статьи  """
@login_required
def toggle_like(request, post_id):
    """Лайк/удаление лайка статьи"""
    post = get_object_or_404(Post, id=post_id)
    
    like = Like.objects.filter(user=request.user, post=post).first()
    
    if like:
        like.delete()
        liked = False
        messages.success(request, 'Лайк убран')
    else:
        Like.objects.create(user=request.user, post=post)
        liked = True
        messages.success(request, 'Статья добавлена в избранное!')
        
        # Логируем лайк
        ActivityLog.objects.create(
            user=request.user,
            action_type='article_liked',
            target_user=post.author,
            target_object_id=post.id,
            description=f'{request.user.username} лайкнул статью "{post.title}"'
        )
    
    # Если это AJAX запрос, возвращаем JSON
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        likes_count = Like.objects.filter(post=post).count()
        return JsonResponse({'liked': liked, 'likes_count': likes_count})
    
    return redirect(request.META.get('HTTP_REFERER', '/'))

""" Представление для панели администратора  """
class SuperuserDashboardView(LoginRequiredMixin, TemplateView):
    """Панель суперпользователя"""
    template_name = 'visitor/superuser_dashboard.html'
    login_url = 'Visitor:user-login'
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            messages.error(request, 'У вас нет доступа к этой странице')
            return redirect('blog:post_list')
        return super().dispatch(request, *args, **kwargs)
    
    def _get_period_stats(self, author, start_date=None, end_date=None):
        """Получить статистику автора за указанный период"""
        # Базовые фильтры для постов
        posts_filter = {'author': author}
        if start_date and end_date:
            posts_filter['created__gte'] = start_date
            posts_filter['created__lte'] = end_date
        
        # Статистика
        posts_count = Post.objects.filter(**posts_filter).count()
        views_count = Post.objects.filter(**posts_filter).aggregate(total=Sum('views'))['total'] or 0
        
        # Like использует поле 'created', а не 'created_at'
        likes_filter = {'post__author': author}
        if start_date and end_date:
            likes_filter['created__gte'] = start_date
            likes_filter['created__lte'] = end_date
        likes_count = Like.objects.filter(**likes_filter).count()
        
        # Comment использует поле 'created'
        comments_filter = {'post__author': author}
        if start_date and end_date:
            comments_filter['created__gte'] = start_date
            comments_filter['created__lte'] = end_date
        comments_count = Comment.objects.filter(**comments_filter).exclude(author_comment=author.username).count()
        
        # Donation использует 'created_at'
        donations_filter = {'author': author}
        if start_date and end_date:
            donations_filter['created_at__gte'] = start_date
            donations_filter['created_at__lte'] = end_date
        donations = Donation.objects.filter(**donations_filter).aggregate(total=Sum('amount'))
        
        # Subscription использует 'created_at'
        subscribers_filter = {'author': author}
        if start_date and end_date:
            subscribers_filter['created_at__gte'] = start_date
            subscribers_filter['created_at__lte'] = end_date
        subscribers_count = Subscription.objects.filter(**subscribers_filter).count()
        
        return {
            'posts_count': posts_count,
            'views_count': views_count,
            'likes_count': likes_count,
            'comments_count': comments_count,
            'total_donations': donations['total'] or 0,
            'subscribers_count': subscribers_count,
        }
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Панель администратора'
        context['page_title'] = 'Панель администратора — IdealImage.ru'
        context['page_description'] = 'Панель управления администратора сайта IdealImage.ru — статистика, заявки, модерация'
        
        # Заявки на роли
        context['pending_applications'] = RoleApplication.objects.filter(
            status='pending'
        ).select_related('user__profile').order_by('-applied_at')
        
        # Последние 20 действий
        context['recent_activities'] = ActivityLog.objects.all().select_related(
            'user', 'target_user'
        ).order_by('-created_at')[:20]
        
        # Даты для периодов
        from datetime import datetime, timedelta
        now = timezone.now()
        
        # Текущий месяц (с 1-го числа до сейчас)
        current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        current_month_end = now
        
        # Прошлый месяц (полный календарный месяц)
        last_month_end = current_month_start - timedelta(days=1)
        last_month_start = last_month_end.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Получаем всех пользователей, у которых есть хотя бы одна статья
        authors_with_posts = User.objects.filter(
            author_posts__isnull=False
        ).distinct().select_related('profile')
        
        # 4 набора статистики
        authors_stats_all_time = []
        authors_stats_last_month = []
        authors_stats_current_month = []
        authors_stats_dynamics = []
        
        for author in authors_with_posts:
            # Проверяем наличие профиля
            if not hasattr(author, 'profile'):
                continue
            
            author_profile = author.profile
            
            # За всё время
            all_time = self._get_period_stats(author)
            authors_stats_all_time.append({
                'author': author,
                'profile': author_profile,
                'posts_count': all_time['posts_count'],
                'views_count': all_time['views_count'],
                'likes_count': all_time['likes_count'],
                'comments_count': all_time['comments_count'],
                'total_donations': all_time['total_donations'],
                'subscribers_count': all_time['subscribers_count'],
                'bonus': author_profile.total_bonus,
                'is_ai': author.username == 'ai_assistant',
            })
            
            # За прошлый месяц
            last_month = self._get_period_stats(author, last_month_start, last_month_end)
            authors_stats_last_month.append({
                'author': author,
                'profile': author_profile,
                'posts_count': last_month['posts_count'],
                'views_count': last_month['views_count'],
                'likes_count': last_month['likes_count'],
                'comments_count': last_month['comments_count'],
                'total_donations': last_month['total_donations'],
                'subscribers_count': last_month['subscribers_count'],
                'bonus': author_profile.total_bonus,
                'is_ai': author.username == 'ai_assistant',
            })
            
            # За текущий месяц
            current_month = self._get_period_stats(author, current_month_start, current_month_end)
            authors_stats_current_month.append({
                'author': author,
                'profile': author_profile,
                'posts_count': current_month['posts_count'],
                'views_count': current_month['views_count'],
                'likes_count': current_month['likes_count'],
                'comments_count': current_month['comments_count'],
                'total_donations': current_month['total_donations'],
                'subscribers_count': current_month['subscribers_count'],
                'bonus': author_profile.total_bonus,
                'is_ai': author.username == 'ai_assistant',
            })
            
            # Динамика (разница между текущим и прошлым месяцем)
            authors_stats_dynamics.append({
                'author': author,
                'profile': author_profile,
                'posts_diff': current_month['posts_count'] - last_month['posts_count'],
                'views_diff': current_month['views_count'] - last_month['views_count'],
                'likes_diff': current_month['likes_count'] - last_month['likes_count'],
                'comments_diff': current_month['comments_count'] - last_month['comments_count'],
                'donations_diff': current_month['total_donations'] - last_month['total_donations'],
                'subscribers_diff': current_month['subscribers_count'] - last_month['subscribers_count'],
                'bonus': author_profile.total_bonus,
                'is_ai': author.username == 'ai_assistant',
            })
        
        # Сортируем по количеству статей (сначала самые активные)
        authors_stats_all_time = sorted(authors_stats_all_time, key=lambda x: x['posts_count'], reverse=True)
        authors_stats_last_month = sorted(authors_stats_last_month, key=lambda x: x['posts_count'], reverse=True)
        authors_stats_current_month = sorted(authors_stats_current_month, key=lambda x: x['posts_count'], reverse=True)
        authors_stats_dynamics = sorted(authors_stats_dynamics, key=lambda x: x['posts_diff'], reverse=True)
        
        # Пагинация
        from django.core.paginator import Paginator
        per_page = int(self.request.GET.get('per_page', 20))
        if per_page not in [10, 20, 50, 100]:
            per_page = 20
        
        page_number = self.request.GET.get('page', 1)
        
        paginator_all_time = Paginator(authors_stats_all_time, per_page)
        paginator_last_month = Paginator(authors_stats_last_month, per_page)
        paginator_current_month = Paginator(authors_stats_current_month, per_page)
        paginator_dynamics = Paginator(authors_stats_dynamics, per_page)
        
        page_all_time = paginator_all_time.get_page(page_number)
        page_last_month = paginator_last_month.get_page(page_number)
        page_current_month = paginator_current_month.get_page(page_number)
        page_dynamics = paginator_dynamics.get_page(page_number)
        
        # Подсчитываем общие суммы для каждого периода
        context['authors_totals_all_time'] = {
            'posts': sum(stat['posts_count'] for stat in authors_stats_all_time),
            'views': sum(stat['views_count'] for stat in authors_stats_all_time),
            'likes': sum(stat['likes_count'] for stat in authors_stats_all_time),
            'donations': sum(stat['total_donations'] for stat in authors_stats_all_time),
            'comments': sum(stat['comments_count'] for stat in authors_stats_all_time),
            'subscribers': sum(stat['subscribers_count'] for stat in authors_stats_all_time),
        }
        
        context['authors_totals_last_month'] = {
            'posts': sum(stat['posts_count'] for stat in authors_stats_last_month),
            'views': sum(stat['views_count'] for stat in authors_stats_last_month),
            'likes': sum(stat['likes_count'] for stat in authors_stats_last_month),
            'donations': sum(stat['total_donations'] for stat in authors_stats_last_month),
            'comments': sum(stat['comments_count'] for stat in authors_stats_last_month),
            'subscribers': sum(stat['subscribers_count'] for stat in authors_stats_last_month),
        }
        
        context['authors_totals_current_month'] = {
            'posts': sum(stat['posts_count'] for stat in authors_stats_current_month),
            'views': sum(stat['views_count'] for stat in authors_stats_current_month),
            'likes': sum(stat['likes_count'] for stat in authors_stats_current_month),
            'donations': sum(stat['total_donations'] for stat in authors_stats_current_month),
            'comments': sum(stat['comments_count'] for stat in authors_stats_current_month),
            'subscribers': sum(stat['subscribers_count'] for stat in authors_stats_current_month),
        }
        
        context['authors_totals_dynamics'] = {
            'posts': sum(stat['posts_diff'] for stat in authors_stats_dynamics),
            'views': sum(stat['views_diff'] for stat in authors_stats_dynamics),
            'likes': sum(stat['likes_diff'] for stat in authors_stats_dynamics),
            'donations': sum(stat['donations_diff'] for stat in authors_stats_dynamics),
            'comments': sum(stat['comments_diff'] for stat in authors_stats_dynamics),
            'subscribers': sum(stat['subscribers_diff'] for stat in authors_stats_dynamics),
        }
        
        # Пагинированные данные
        context['page_all_time'] = page_all_time
        context['page_last_month'] = page_last_month
        context['page_current_month'] = page_current_month
        context['page_dynamics'] = page_dynamics
        
        context['total_authors'] = len(authors_stats_all_time)
        context['per_page'] = per_page
        
        # Обратная совместимость (для других частей шаблона)
        context['authors_stats'] = page_all_time.object_list
        context['authors_totals'] = context['authors_totals_all_time']
        
        # Общая статистика
        context['total_users'] = User.objects.count()
        context['total_posts'] = Post.objects.count()
        context['total_comments'] = Comment.objects.count()
        context['total_donations'] = Donation.objects.aggregate(total=Sum('amount'))['total'] or 0
        
        # ========================================
        # AI-АССИСТЕНТ: Интеграция функционала
        # ========================================
        try:
            from Asistent.models import (
                ContentTask, AISchedule, ModerationCriteria, ModerationLog, 
                AIGeneratedArticle, CommentModerationCriteria, CommentModerationLog,
                TaskAssignment, AIConversation, AITask
            )
            
            # Критерии модерации (новая упрощённая система)
            from Asistent.moderations.models import ArticleModerationSettings, CommentModerationSettings, ModerationLog as NewModerationLog
            
            context['article_criteria'] = ArticleModerationSettings.objects.all().order_by('-updated_at')
            context['comment_criteria'] = CommentModerationSettings.objects.all().order_by('-updated_at')
            
            # Статистика модерации (упрощённая)
            context['comment_moderation_stats'] = {
                'total': NewModerationLog.objects.filter(content_type='comment').count(),
                'passed': NewModerationLog.objects.filter(content_type='comment', passed=True).count(),
                'blocked': NewModerationLog.objects.filter(content_type='comment', passed=False).count(),
            }
            
            # Статистика заданий для авторов
            context['tasks_stats'] = {
                'total': ContentTask.objects.exclude(status='cancelled').count(),
                'in_progress': TaskAssignment.objects.filter(status='in_progress').count(),
                'authors_count': TaskAssignment.objects.filter(status='in_progress').values('author').distinct().count(),
                'completed': TaskAssignment.objects.filter(status='approved').count(),
            }
            
            # Задания на AI проверке
            context['tasks_for_review'] = TaskAssignment.objects.filter(
                status='completed'
            ).select_related('author__profile', 'article', 'task').order_by('-submitted_at')[:10]
            
            # Просроченные задания
            context['overdue_tasks'] = ContentTask.objects.filter(
                deadline__lt=timezone.now(),
                status__in=['available', 'active']
            ).order_by('deadline')
            
            # Активные расписания AI
            context['ai_schedules'] = AISchedule.objects.filter(
                is_active=True
            ).select_related('category').order_by('-created_at')
            
            # Критерии модерации (упрощённая система)
            from Asistent.moderations.models import ArticleModerationSettings
            context['moderation_criteria'] = ArticleModerationSettings.objects.filter(
                is_active=True
            ).first()
            
            # Статистика AI-Ассистента
            context['ai_stats'] = {
                'total_tasks': ContentTask.objects.exclude(status='cancelled').count(),
                'available_tasks': ContentTask.objects.filter(status='available').count(),
                'tasks_in_progress': TaskAssignment.objects.filter(status='in_progress').count(),
                'tasks_for_review': TaskAssignment.objects.filter(status='completed').count(),
                'completed_tasks': TaskAssignment.objects.filter(status='approved').count(),
                'overdue_tasks': ContentTask.objects.filter(
                    deadline__lt=timezone.now(),
                    status__in=['available', 'active']
                ).count(),
                'active_schedules': AISchedule.objects.filter(is_active=True).count(),
                'ai_articles_total': AIGeneratedArticle.objects.count(),
                'ai_articles_today': AIGeneratedArticle.objects.filter(
                    created_at__date=timezone.now().date()
                ).count(),
                'moderation_logs_today': ModerationLog.objects.filter(
                    created_at__date=timezone.now().date()
                ).count(),
                # Новая статистика для AI-чата
                'generated_articles': AIGeneratedArticle.objects.count(),
                'chat_conversations': AIConversation.objects.count(),
            }
            
            # Последние AI-статьи
            context['recent_ai_articles'] = AIGeneratedArticle.objects.select_related(
                'article', 'schedule'
            ).order_by('-created_at')[:5]
            
            # Последние логи модерации
            context['recent_moderation_logs'] = ModerationLog.objects.select_related(
                'article', 'criteria'
            ).order_by('-created_at')[:10]
            
            context['ai_enabled'] = True
            
        except ImportError:
            # Если Asistent не установлен
            context['ai_enabled'] = False
            context['ai_stats'] = {}
        
        return context

""" Представление для просмотра должностной инструкции для роли  """
def role_instructions(request, role):
    """Страница с должностной инструкцией для роли"""
    
    role_data = {
        'author': {
            'title': 'Должностная инструкция: Автор',
            'icon': '✍️',
            'description': 'Автор контента на платформе IdealImage.ru'
        },
        'moderator': {
            'title': 'Должностная инструкция: Модератор',
            'icon': '🛡️',
            'description': 'Модератор контента и сообщества'
        },
        'marketer': {
            'title': 'Должностная инструкция: Маркетолог',
            'icon': '📊',
            'description': 'Маркетолог платформы'
        },
    }
    
    if role not in role_data:
        messages.error(request, 'Неизвестная роль')
        return redirect('blog:post_list')
    
    context = {
        'role': role,
        'role_data': role_data[role],
        'title': role_data[role]['title'],
        'page_title': f"{role_data[role]['title']} — IdealImage.ru",
        'page_description': f"{role_data[role]['description']} на сайте IdealImage.ru"
    }
    
    return render(request, 'visitor/role_instructions.html', context)

""" Представление для просмотра личного кабинета пользователя (только для суперпользователей)  """
@login_required
def view_user_cabinet(request, user_id):
    """Просмотр личного кабинета пользователя (только для суперпользователей)"""
    if not request.user.is_superuser:
        messages.error(request, 'У вас нет прав для этого действия')
        return redirect('blog:post_list')
    
    # Получаем пользователя, чей кабинет хотим посмотреть
    target_user = get_object_or_404(User, id=user_id)
    profile = target_user.profile
    
    # Формируем контекст как для PersonalCabinetView, но для целевого пользователя
    context = {
        'profile': profile,
        'title': f'Личный кабинет - {target_user.username} (Просмотр администратора)',
        'page_title': f'Личный кабинет — {target_user.username} (Администратор)',
        'page_description': f'Просмотр личного кабинета пользователя {target_user.username} администратором',
        'is_admin_view': True,  # Флаг что это просмотр администратором
        'target_user': target_user,
    }
    
    # Подписки пользователя
    subscriptions = Subscription.objects.filter(subscriber=target_user).select_related('author__profile')
    context['subscriptions'] = subscriptions
    context['subscriptions_count'] = subscriptions.count()
    
    # Последние статьи из подписок
    if subscriptions.exists():
        subscribed_authors = [sub.author for sub in subscriptions]
        context['subscribed_posts'] = Post.objects.filter(
            author__in=subscribed_authors,
            status='published'
        ).order_by('-created')[:10]
    
    # Комментарии пользователя
    context['user_comments'] = Comment.objects.filter(
        author_comment=target_user.username,
        active=True
    ).select_related('post').order_by('-created')[:10]
    
    # Заявки на роли
    context['role_applications'] = RoleApplication.objects.filter(
        user=target_user
    ).exclude(
        status='approved'
    ).order_by('-applied_at')
    
    context['has_pending_applications'] = RoleApplication.objects.filter(
        user=target_user,
        status='pending'
    ).exists()
    
    # Если пользователь автор
    if profile.is_author or Post.objects.filter(author=target_user).exists():
        # Подписчики автора
        subscribers = Subscription.objects.filter(author=target_user).select_related('subscriber__profile')
        context['subscribers'] = subscribers
        context['subscribers_count'] = subscribers.count()
        
        # Статистика автора
        author_posts = Post.objects.filter(author=target_user)
        context['author_posts_count'] = author_posts.count()
        
        # Лайки
        total_likes = Like.objects.filter(post__author=target_user).count()
        context['total_likes'] = total_likes
        
        # Комментарии к статьям автора
        comments_to_author = Comment.objects.filter(
            post__author=target_user,
            active=True
        ).exclude(author_comment=target_user.username).count()
        context['comments_to_author'] = comments_to_author
        
        # Донаты
        donations = Donation.objects.filter(author=target_user).aggregate(
            total=Sum('amount'),
            count=Count('id')
        )
        context['total_donations'] = donations['total'] or 0
        context['donations_count'] = donations['count']
        
        # Последние комментарии к статьям автора
        context['recent_comments_to_posts'] = Comment.objects.filter(
            post__author=target_user,
            active=True
        ).exclude(author_comment=target_user.username).select_related('post').order_by('-created')[:5]
        
        # Премия
        context['total_bonus'] = profile.total_bonus
    
    return render(request, 'visitor/personal_cabinet.html', context)

""" Представление для обработки заявки на роль (только для суперпользователей)  """
@login_required
def process_role_application(request, application_id):
    """Обработка заявки на роль (только для суперпользователей)"""
    if not request.user.is_superuser:
        messages.error(request, 'У вас нет прав для этого действия')
        return redirect('blog:post_list')
    
    application = get_object_or_404(RoleApplication, id=application_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        admin_response = request.POST.get('admin_response', '')
        
        if action == 'approve':
            application.status = 'approved'
            application.processed_at = timezone.now()
            application.processed_by = request.user
            application.admin_response = admin_response
            application.save()
            
            # Присваиваем роль пользователю
            profile = application.user.profile
            if application.role == 'author':
                profile.is_author = True
            elif application.role == 'moderator':
                profile.is_moderator = True
            elif application.role == 'marketer':
                profile.is_marketer = True
            elif application.role == 'admin':
                profile.is_admin = True
                application.user.is_staff = True
                application.user.save()
            profile.save()
            
            # Логируем
            ActivityLog.objects.create(
                user=application.user,
                action_type='role_granted',
                target_user=request.user,
                target_object_id=application.id,
                description=f'Пользователю {application.user.username} присвоена роль {application.get_role_display()}'
            )
            
            messages.success(request, f'Заявка пользователя {application.user.username} одобрена!')
            
        elif action == 'reject':
            application.status = 'rejected'
            application.processed_at = timezone.now()
            application.processed_by = request.user
            application.admin_response = admin_response
            application.save()
            
            messages.success(request, f'Заявка пользователя {application.user.username} отклонена!')
    
    return redirect('Visitor:superuser_dashboard')

""" Представление для редактирования комментария (только для модераторов и суперпользователей)  """
@login_required
def edit_comment(request, comment_id):
    """Редактирование комментария (для модераторов и суперюзеров)"""
    import json
    
    # Проверка прав: модератор или суперюзер
    if not (request.user.profile.is_moderator or request.user.is_superuser):
        return JsonResponse({'success': False, 'error': 'Нет прав для редактирования'}, status=403)
    
    comment = get_object_or_404(Comment, id=comment_id)
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            new_content = data.get('content', '').strip()
            
            if not new_content:
                return JsonResponse({'success': False, 'error': 'Комментарий не может быть пустым'})
            
            # Сохраняем старое содержимое для логирования
            old_content = comment.content
            
            # Обновляем комментарий
            comment.content = new_content
            comment.save()
            
            # Логируем действие
            ActivityLog.objects.create(
                user=request.user,
                action_type='comment_added',  # Используем существующий тип
                target_user=comment.post.author,
                target_object_id=comment.id,
                description=f'{request.user.username} ({"суперюзер" if request.user.is_superuser else "модератор"}) отредактировал комментарий #{comment.id}'
            )
            
            return JsonResponse({
                'success': True,
                'message': 'Комментарий успешно отредактирован',
                'new_content': new_content
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    
    return JsonResponse({'success': False, 'error': 'Метод не поддерживается'}, status=405)

""" Представление для удаления комментария (только для суперпользователей)  """
@login_required
def delete_comment(request, comment_id):
    """Удаление комментария (только для суперюзеров)"""
    
    # Проверка прав: только суперюзер
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'error': 'Нет прав для удаления комментариев'}, status=403)
    
    comment = get_object_or_404(Comment, id=comment_id)
    
    if request.method == 'POST':
        try:
            # Сохраняем информацию для логирования
            comment_info = {
                'id': comment.id,
                'author': comment.author_comment,
                'post_title': comment.post.title,
                'content_preview': comment.content[:50]
            }
            
            # Удаляем комментарий
            comment.delete()
            
            # Логируем действие
            ActivityLog.objects.create(
                user=request.user,
                action_type='comment_added',  # Используем существующий тип
                target_user=comment.post.author,
                description=f'Суперюзер {request.user.username} удалил комментарий #{comment_info["id"]} от {comment_info["author"]} к статье "{comment_info["post_title"]}"'
            )
            
            return JsonResponse({
                'success': True,
                'message': 'Комментарий успешно удален'
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    
    return JsonResponse({'success': False, 'error': 'Метод не поддерживается'}, status=405)

""" Представление для сохранения согласия пользователя на cookies (GDPR/РФ)  """
@require_POST
def save_cookie_consent(request):
    """Сохранение согласия пользователя на cookies (GDPR/РФ)"""
    try:
        data = json.loads(request.body)
        
        # Получаем или создаем ключ сессии
        if not request.session.session_key:
            request.session.create()
        session_key = request.session.session_key
        
        # Сохраняем согласие
        consent, created = CookieConsent.objects.update_or_create(
            session_key=session_key,
            defaults={
                'user': request.user if request.user.is_authenticated else None,
                'necessary': True,  # Всегда True (обязательные)
                'functional': data.get('functional', False),
                'analytics': data.get('analytics', False),
                'advertising': data.get('advertising', False),
                'ip_address': get_client_ip(request),
                'user_agent': request.META.get('HTTP_USER_AGENT', ''),
            }
        )
        
        # Логируем активность
        ActivityLog.objects.create(
            user=request.user if request.user.is_authenticated else None,
            action_type='user_registered',  # Можем использовать этот тип
            description=f'Согласие на cookies: F={consent.functional}, A={consent.analytics}, Ad={consent.advertising}'
        )
        
        response = JsonResponse({
            'status': 'ok',
            'message': 'Спасибо! Ваши настройки сохранены.'
        })
        
        # Устанавливаем cookie на 1 год (по закону РФ)
        response.set_cookie(
            'cookie_consent_accepted', 
            'true', 
            max_age=31536000,  # 365 дней
            secure=False,  # True для HTTPS
            httponly=False,  # False чтобы JavaScript мог прочитать!
            samesite='Lax'
        )
        
        return response
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Ошибка сохранения: {str(e)}'
        }, status=500)



