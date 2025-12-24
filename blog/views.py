from django.shortcuts import render, redirect, get_object_or_404
from django.http import Http404, HttpResponse, HttpResponseRedirect, JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
import logging

logger = logging.getLogger(__name__)
from Visitor.models import *
from .models import *
# Импорт run_pipeline_by_slug_task удален - система пайплайнов больше не используется
import mptt
from taggit.models import Tag
from django.views.generic import *
from django.conf import settings
from .forms import *
from django.urls import reverse_lazy, reverse
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.messages.views import SuccessMessageMixin
from .mixins import AuthorRequiredMixin
from django.db.models import Q, F
from django.core.cache import cache
from django.views.decorators.cache import cache_page
from django.utils import timezone
from datetime import timedelta
from django.utils.decorators import method_decorator
from django.core.paginator import Paginator
from utilits.seo_utils import (
    generate_meta_description, generate_meta_keywords, get_og_image,
    generate_canonical_url, get_article_structured_data, get_website_structured_data,
    get_breadcrumb_structured_data, get_person_structured_data, get_organization_structured_data
)
import json
import os
from urllib.parse import urlparse





def article_lookup(request, slug):
    """Легаси-роут: ищет статью по старому слагу и редиректит на актуальный URL.
    Стратегия: точное совпадение -> slug__icontains -> title__icontains по словам.
    """
    try:
        post = Post.objects.filter(slug=slug, status='published').latest('created')
    except Post.DoesNotExist:
        # Пытаемся по частичному вхождению слага
        qs = Post.objects.filter(status='published')
        post = qs.filter(slug__icontains=slug).order_by('-created').first()
        if not post:
            # Пробуем по словам из слага в заголовке
            keywords = [w for w in slug.replace('-', ' ').split() if len(w) > 2]
            q = Q()
            for w in keywords:
                q &= Q(title__icontains=w)
            post = qs.filter(q).order_by('-created').first()
            if not post:
                raise Http404("Статья не найдена")
    return redirect(post.get_absolute_url(), permanent=True)
@method_decorator(cache_page(60 * 10), name='dispatch')  # Кэш на 10 минут для списка статей
class PostListView(ListView):
    model = Post
    template_name = 'blog/post_list_tailwind.html'
    paginate_by = 20
    
    def get_queryset(self):
        # Оптимизированный запрос с select_related и prefetch_related
        # ВАЖНО: Показывать только опубликованные статьи!
        return Post.objects.filter(status='published').select_related('author', 'category').prefetch_related('tags')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Kэширование авторов и тегов
        categorys = cache.get('categorys_list')
        if categorys is None:
            categorys = Category.objects.all()
            cache.set('categorys_list', categorys, 300)  # кэш на 5 минут
        
        authors = cache.get('authors_list')
        if authors is None:
            authors = Profile.objects.filter(spez='писатель')
            cache.set('authors_list', authors, 300)  # кэш на 5 минут
        
        # Получаем популярные теги (теги, которые используются в постах)
        from django.db.models import Count
        popular_tags = Tag.objects.filter(
            taggit_taggeditem_items__content_type__model='post'
        ).annotate(
            posts_count=Count('taggit_taggeditem_items')
        ).order_by('-posts_count')[:10]  # Топ 10 популярных тегов
            
        posts = cache.get('posts_list')
        if posts is None:
            # Кэшировать только опубликованные статьи
            posts = Post.objects.filter(status='published').order_by('-created')
            cache.set('posts_list', posts, 300)  # кэш на 5 минут
        
        # SEO данные
        context['categorys'] = categorys
        context['authors'] = authors
        context['tags'] = popular_tags
        context['page_title'] = 'Новости от Идеального Образа'
        context['page_description'] = 'Эксклюзивные новости из мира моды, здоровья и красоты. Советы по стилю, уходу за собой и здоровому образу жизни.'
        context['meta_keywords'] = 'мода, красота, здоровье, стиль, новости, идеальный образ'
        context['canonical_url'] = generate_canonical_url(self.request)
        context['og_image'] = get_og_image(None)
        context['structured_data'] = json.dumps(get_website_structured_data(), ensure_ascii=False)
        context['organization_schema'] = json.dumps(get_organization_structured_data(), ensure_ascii=False)
        
        return context


'''
class PostDetailView(DetailView):
    model = Post
    template_name = 'blog/new/post_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = self.object.title
        context['form'] = CommentCreateForm
        return context
'''

# Кэширование страницы статьи (15 минут)
# ВАЖНО: Без Redis используем LocMemCache (работает в памяти процесса)
@cache_page(60 * 15, cache='pages')  # Используем отдельный кэш для страниц
def post_detail(request, slug):
    # Получаем пост, если есть несколько с одинаковым slug - берем самый новый
    try:
        post = Post.objects.select_related('author', 'author__profile', 'category').prefetch_related('tags').filter(slug=slug).latest('created')
    except Post.DoesNotExist:
        raise Http404("Статья не найдена")
    comments = post.comments.filter(active=True).select_related('post')
    
    # Увеличиваем счетчик просмотров БЕЗ вызова сигналов
    Post.objects.filter(pk=post.pk).update(views=F('views') + 1)
    
    # SEO данные (используем AI-сгенерированные если доступны)
    page_title = post.meta_title if hasattr(post, 'meta_title') and post.meta_title else post.title
    page_description = generate_meta_description(post.description or post.content, post=post)
    meta_keywords = generate_meta_keywords(post)
    canonical_url = generate_canonical_url(request, post)
    og_image = get_og_image(post)
    
    # Open Graph заголовки и описания
    og_title = post.og_title if hasattr(post, 'og_title') and post.og_title else page_title
    og_description = post.og_description if hasattr(post, 'og_description') and post.og_description else page_description
    
    # Структурированные данные
    structured_data = get_article_structured_data(post)
    
    # Структурированные данные для автора (Person schema)
    person_schema = get_person_structured_data(post.author)
    
    # Структурированные данные для организации (Organization schema)
    organization_schema = get_organization_structured_data()
    
    # Хлебные крошки
    breadcrumbs = [
        ('Главная', '/'),
        ('Журнал', '/blog/'),
        (post.category.title, post.category.get_absolute_url()),
        (post.title, post.get_absolute_url())
    ]
    breadcrumb_structured_data = get_breadcrumb_structured_data(breadcrumbs)
    
    # Кэшированные данные
    authors = cache.get('authors_list')
    if authors is None:
        authors = Profile.objects.filter(spez='писатель')
        cache.set('authors_list', authors, 300)
    
    tags = cache.get('tags_list')
    if tags is None:
        tags = Tag.objects.all()
        cache.set('tags_list', tags, 300)
    
    # Популярные посты
    popular_posts = Post.objects.filter(status='published').order_by('-views')[:7]
    
    # Статьи с минимальными просмотрами из той же категории
    low_view_posts = Post.objects.filter(
        status='published',
        category=post.category
    ).exclude(id=post.id).select_related('author', 'category').prefetch_related('tags').order_by('views')[:3]
    
    # Автоматическая внутренняя перелинковка
    from blog.services.internal_linking import InternalLinker
    linker = InternalLinker()
    related_posts = linker.find_related_posts(post, limit=5)
    internal_links_html = linker.generate_internal_links_html(post, related_posts, count=3)

    if request.method == 'POST':
        comment_form = CommentForm(data=request.POST)
        if comment_form.is_valid():
            new_comment = comment_form.save(commit=False)
            new_comment.post = post
            
            # Обработка родительского комментария
            parent_id = request.POST.get('parent')
            if parent_id:
                try:
                    new_comment.parent = Comment.objects.get(id=parent_id)
                except Comment.DoesNotExist:
                    pass
            
            new_comment.save()
            return HttpResponseRedirect(request.path + '#comments')
    else:
        comment_form = CommentForm()
    categorys = cache.get('categorys_list')
    if categorys is None:
        categorys = Category.objects.all()
        cache.set('categorys_list', categorys, 300)
    
    return render(
        request,
        'blog/post_detail_tailwind.html',
        {
            'post': post,
            'comments': comments,
            'authors': authors,
            'tags': tags,
            'popular_posts': popular_posts,
            'low_view_posts': low_view_posts,
            'related_posts': related_posts,
            'internal_links_html': internal_links_html,
            'page_description': page_description,
            'page_title': page_title,
            'meta_keywords': meta_keywords,
            'canonical_url': canonical_url,
            'og_image': og_image,
            'og_title': og_title,
            'og_description': og_description,
            'structured_data': json.dumps(structured_data, ensure_ascii=False),
            'person_schema': json.dumps(person_schema, ensure_ascii=False) if person_schema else None,
            'organization_schema': json.dumps(organization_schema, ensure_ascii=False),
            'breadcrumb_structured_data': json.dumps(breadcrumb_structured_data, ensure_ascii=False) if breadcrumb_structured_data else None,
            'breadcrumbs': breadcrumbs,
            'comment_form': comment_form,
            'categorys': categorys,
        },
    )

class PostByCategoryListView(ListView):
    model = Post
    template_name = 'blog/post_list_tailwind.html'
    paginate_by = 20

    def get_queryset(self):
        category = self.get_category()
        descendant_categories = category.get_descendants(include_self=True)
        # Показывать только опубликованные статьи
        return Post.objects.filter(
            category__in=descendant_categories,
            status='published'
        ).select_related('author', 'category').prefetch_related('tags')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        category = self.get_category()
        
        # Получаем теги только из постов текущей категории
        from django.db.models import Count
        descendant_categories = category.get_descendants(include_self=True)
        category_tags = Tag.objects.filter(
            taggit_taggeditem_items__content_type__model='post',
            taggit_taggeditem_items__object_id__in=Post.objects.filter(
                category__in=descendant_categories
            ).values_list('id', flat=True)
        ).annotate(
            posts_count=Count('taggit_taggeditem_items')
        ).distinct().order_by('-posts_count')  # Все теги категории (без ограничения)
        
        # Кэширование категорий
        categorys = cache.get('categorys_list')
        if categorys is None:
            categorys = Category.objects.all()
            cache.set('categorys_list', categorys, 300)
        # Кэширование авторов
        authors = cache.get('authors_list')
        if authors is None:
            authors = Profile.objects.filter(spez='писатель')
            cache.set('authors_list', authors, 300)
            
        context['authors'] = authors
        context['page_title'] = f'Категория:{self.category.title}'
        context['category'] = category
        context['categorys'] = categorys
        context['tags'] = category_tags
        context['page_title'] = f'Категория:{self.category.title}'
        context['page_description'] = f'Статьи по теме: {self.category.title}'
        context['current_category'] = category  # Для подсветки в шаблоне
    
        return context

    def get_category(self):
        if not hasattr(self, 'category'):
            from django.shortcuts import get_object_or_404
            self.category = get_object_or_404(Category, slug=self.kwargs['slug'])
        return self.category

class PostCreateView(LoginRequiredMixin, CreateView):
    """
    Представление: создание материалов на сайте
    """
    model = Post
    template_name = 'blog/post_create.html'
    form_class = PostCreateForm
    login_url = 'Home:home'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Добавление статьи на сайт'
        context['page_description'] = 'Создайте новую статью на сайте IdealImage.ru'
        context['ai_disabled'] = getattr(settings, 'DISABLE_AI', False)
        return context

    def form_valid(self, form):
        form.instance.author = self.request.user
        
        # ОТКЛЮЧЕНИЕ АВТОМОДЕРАЦИИ для суперюзеров и AI агентов
        is_superuser = self.request.user.is_superuser or self.request.user.is_staff
        is_ai_agent = self.request.user.username == 'ai_assistant'
        
        if is_superuser or is_ai_agent:
            form.instance._skip_auto_moderation = True
        
        # Обработка AI-помощника
        use_ai = form.cleaned_data.get('use_ai_assistant', False)
        generate_image = form.cleaned_data.get('generate_image', False)
        
        # Если запрошен AI - ставим флаг чтобы НЕ запускать автомодерацию
        if (use_ai or generate_image) and form.instance.status == 'draft':
            # Временный флаг для сигнала
            form.instance._skip_auto_moderation = True
        
        post = form.save()
        
        # Проверяем что хотя бы что-то запрошено
        if (use_ai or generate_image) and post.status == 'draft':
            if getattr(settings, 'DISABLE_AI', False):
                messages.warning(self.request, 'AI-режим отключён. Задачи в очередь не ставятся.')
                # ничего не запускаем локально
                cache.delete('authors_list')
                return super().form_valid(form)
            from django_q.tasks import async_task
            messages_list = []
            needs_save = False
            
            # Улучшение текста
            if use_ai and post.content:
                style = form.cleaned_data.get('ai_improvement_style', 'balanced')
                custom_prompt = form.cleaned_data.get('ai_custom_prompt', '')
                
                post.ai_draft_improvement_requested = True
                post.ai_draft_original = post.content  # Сохраняем оригинал
                post.ai_improvement_status = 'pending'
                needs_save = True
                
                # Асинхронный запуск улучшения текста
                task_id = async_task(
                    'Asistent.tasks.improve_author_draft_task',
                    post.id,
                    style,
                    custom_prompt,
                    task_name=f'Improve draft #{post.id}'
                )
                post.ai_improvement_task_id = task_id
                post.ai_improvement_requested_at = timezone.now()
                messages_list.append('улучшает текст')
            
            # Генерация изображения (НЕЗАВИСИМО от текста!)
            if generate_image:
                image_prompt = form.cleaned_data.get('image_generation_prompt', '')
                
                async_task(
                    'Asistent.tasks.generate_post_image_task',
                    post.id,
                    image_prompt,
                    self.request.user.id,
                    task_name=f'Generate image for post #{post.id}'
                )
                messages_list.append('генерирует изображение')
            
            # Сохраняем ОДИН раз если нужно
            if needs_save:
                post.save()
            
            message = '✨ Черновик сохранен! AI-помощник ' + ' и '.join(messages_list) + '. Вы получите уведомление когда будет готово.'
            messages.success(self.request, message)
        
        # Очищаем кэш после создания нового поста
        cache.delete('authors_list')
        return super().form_valid(form)


class PostUpdateView(SuccessMessageMixin, UpdateView):
    """
    Представление: обновления материала на сайте
    Доступ: автор статьи или суперюзер
    """
    model = Post
    template_name = 'blog/post_update.html'
    context_object_name = 'post'
    form_class = PostUpdateForm
    login_url = 'Home:home'
    success_message = 'Материал был успешно обновлен'
    
    def get_success_url(self):
        """
        Если запрошен AI - остаёмся на странице редактирования
        Иначе - стандартный редирект на детальную страницу
        """
        # Проверяем был ли запрошен AI
        ai_requested = getattr(self, '_ai_requested', False)
        
        if ai_requested:
            # Остаёмся на странице редактирования
            return reverse('blog:post_update', kwargs={'slug': self.object.slug})
        else:
            # Стандартный редирект
            return self.object.get_absolute_url()

    def dispatch(self, request, *args, **kwargs):
        """Проверка прав доступа"""
        if not request.user.is_authenticated:
            messages.error(request, 'Войдите для редактирования статей')
            return redirect('Visitor:user-login')
        
        post = self.get_object()
        
        # Доступ для автора или суперюзера
        if request.user != post.author and not request.user.is_superuser:
            messages.error(request, 'У вас нет прав для редактирования этой статьи')
            return redirect('blog:post_list')
        
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = f'Обновление статьи: {self.object.title}'
        context['page_description'] = f'Редактирование статьи "{self.object.title}" на сайте IdealImage.ru'
        context['ai_disabled'] = getattr(settings, 'DISABLE_AI', False)
        
        # Проверяем есть ли уведомление о сгенерированном изображении
        # ВАЖНО: Ищем по related_article, а не по recipient (т.к. суперюзер может редактировать чужую статью)
        from Asistent.models import AuthorNotification
        
        generated_image_notification = AuthorNotification.objects.filter(
            related_article=self.object,
            message__contains='AI_GENERATED_IMAGE',
            is_read=False
        ).first()
        
        if generated_image_notification:
            # Извлекаем пути к изображениям из message
            lines = generated_image_notification.message.split('\n')
            new_image = None
            old_image = None
            
            for line in lines:
                if line.startswith('AI_GENERATED_IMAGE:'):
                    new_image = line.replace('AI_GENERATED_IMAGE:', '').strip()
                elif line.startswith('OLD_IMAGE:'):
                    old_image = line.replace('OLD_IMAGE:', '').strip()
                    if old_image == 'none':
                        old_image = None
            
            context['generated_image'] = {
                'new_image': new_image,
                'old_image': old_image,
                'notification': generated_image_notification
            }

        # Флаги состояния AI-улучшений
        context['ai_improvement_ready'] = (self.object.ai_improvement_status == 'ready')
        context['ai_improvement_in_progress'] = False
        context['ai_improvement_status_stale'] = False

        if self.object.ai_improvement_status in ('pending', 'processing'):
            pending = True

            task_id = getattr(self.object, 'ai_improvement_task_id', '')
            if task_id:
                try:
                    from django_q.models import Task  # noqa: WPS433
                except Exception:
                    Task = None  # type: ignore
                else:
                    if Task.objects.filter(id=task_id).exists():
                        pending = False

            request_time = getattr(self.object, 'ai_improvement_requested_at', None)
            if pending and request_time:
                if request_time < timezone.now() - timedelta(minutes=15):
                    pending = False
                    context['ai_improvement_status_stale'] = True

            context['ai_improvement_in_progress'] = pending
        
        return context

    def form_valid(self, form):
        form.instance.updater = self.request.user
        
        # ОТКЛЮЧЕНИЕ АВТОМОДЕРАЦИИ для суперюзеров и AI агентов
        is_superuser = self.request.user.is_superuser or self.request.user.is_staff
        is_ai_agent = self.request.user.username == 'ai_assistant'
        is_article_author_ai = form.instance.author and form.instance.author.username == 'ai_assistant'
        is_auto_generated = getattr(form.instance, '_auto_generated_by_schedule', False)
        
        if is_superuser or is_ai_agent or is_article_author_ai or is_auto_generated:
            form.instance._skip_auto_moderation = True
        
        # Если снята галочка "fixed" - очищаем telegram_posted_at для повторной отправки
        if not form.cleaned_data.get('fixed', False):
            form.instance.telegram_posted_at = None
        
        # Обработка AI-помощника
        use_ai = form.cleaned_data.get('use_ai_assistant', False)
        generate_image = form.cleaned_data.get('generate_image', False)
        
        # Если запрошен AI - ставим флаг чтобы НЕ запускать автомодерацию
        if (use_ai or generate_image) and form.instance.status == 'draft':
            # Временный флаг для сигнала
            form.instance._skip_auto_moderation = True
        
        # Сохраняем форму (включая теги)
        post = form.save()
        
        # Явно сохраняем ManyToMany поля (теги) если они есть
        # Это важно для TaggableManager - гарантируем сохранение тегов
        if hasattr(form, 'save_m2m'):
            form.save_m2m()
        
        # Проверяем что хотя бы что-то запрошено
        if (use_ai or generate_image) and post.status == 'draft':
            if getattr(settings, 'DISABLE_AI', False):
                messages.warning(self.request, 'AI-режим отключён. Задачи в очередь не ставятся.')
                cache.delete('authors_list')
                return super().form_valid(form)
            from django_q.tasks import async_task
            messages_list = []
            needs_save = False
            
            # Устанавливаем флаг что AI запрошен - чтобы остаться на странице редактирования
            self._ai_requested = True
            
            # Улучшение текста
            if use_ai and post.content:
                style = form.cleaned_data.get('ai_improvement_style', 'balanced')
                custom_prompt = form.cleaned_data.get('ai_custom_prompt', '')
                
                post.ai_draft_improvement_requested = True
                post.ai_draft_original = post.content  # Сохраняем оригинал
                post.ai_improvement_status = 'pending'
                needs_save = True
                
                # Асинхронный запуск улучшения текста
                async_task(
                    'Asistent.tasks.improve_author_draft_task',
                    post.id,
                    style,
                    custom_prompt,
                    task_name=f'Improve draft #{post.id}'
                )
                messages_list.append('улучшает текст')
            
            # Генерация изображения (НЕЗАВИСИМО от текста!)
            if generate_image:
                image_prompt = form.cleaned_data.get('image_generation_prompt', '')
                
                async_task(
                    'Asistent.tasks.generate_post_image_task',
                    post.id,
                    image_prompt,
                    self.request.user.id,
                    task_name=f'Generate image for post #{post.id}'
                )
                messages_list.append('генерирует изображение')
            
            # Сохраняем ОДИН раз если нужно (только определенные поля, чтобы не перезаписать теги)
            if needs_save:
                post.save(update_fields=['ai_draft_improvement_requested', 'ai_draft_original', 
                                        'ai_improvement_status', 'ai_improvement_task_id', 
                                        'ai_improvement_requested_at'])
            
            message = '✨ Статья обновлена! AI-помощник ' + ' и '.join(messages_list) + '. Вы получите уведомление когда будет готово.'
            messages.success(self.request, message)
        
        # Очищаем кэш после обновления
        cache.delete('authors_list')
        return super().form_valid(form)


class PostDeleteView(DeleteView):
    """
    Представление: удаления материала
    Доступ: модератор, суперюзер
    """
    model = Post
    success_url = reverse_lazy('blog:post_list')
    context_object_name = 'post'
    template_name = 'blog/post_delete.html'

    def dispatch(self, request, *args, **kwargs):
        """Проверка прав доступа"""
        if not request.user.is_authenticated:
            messages.error(request, 'Войдите для удаления статей')
            return redirect('Visitor:user-login')
        
        post = self.get_object()
        
        # Доступ для модератора или суперюзера
        is_moderator = hasattr(request.user, 'profile') and request.user.profile.is_moderator
        is_superuser = request.user.is_superuser
        
        if not (is_moderator or is_superuser):
            messages.error(request, 'У вас нет прав для удаления статей')
            return redirect('blog:post_list')
        
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = f'Удаление статьи: {self.object.title}'
        context['page_description'] = f'Подтверждение удаления статьи "{self.object.title}"'
        return context

    def delete(self, request, *args, **kwargs):
        # Очищаем кэш после удаления
        cache.delete('authors_list')
        messages.success(request, f'Статья "{self.get_object().title}" успешно удалена')
        return super().delete(request, *args, **kwargs)


class PostByTagListView(ListView):
    model = Post
    template_name = 'blog/post_list_tailwind.html'
    paginate_by = 20

    def get_queryset(self):
        from django.shortcuts import get_object_or_404
        self.tag = get_object_or_404(Tag, slug=self.kwargs['tag'])
        # Показывать только опубликованные статьи
        return Post.objects.filter(
            tags__slug=self.tag.slug,
            status='published'
        ).select_related('author', 'category').prefetch_related('tags')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Получаем популярные теги для текущего набора постов
        from django.db.models import Count
        related_tags = Tag.objects.filter(
            taggit_taggeditem_items__content_type__model='post',
            taggit_taggeditem_items__object_id__in=self.get_queryset().values_list('id', flat=True)
        ).annotate(
            posts_count=Count('taggit_taggeditem_items')
        ).distinct().order_by('-posts_count')[:10]
        
        # Кэширование категорий
        categorys = cache.get('categorys_list')
        if categorys is None:
            categorys = Category.objects.all()
            cache.set('categorys_list', categorys, 300)
        # Кэширование авторов
        authors = cache.get('authors_list')
        if authors is None:
            authors = Profile.objects.filter(spez='писатель')
            cache.set('authors_list', authors, 300)
            
        context['categorys'] = categorys
        context['tags'] = related_tags
        context['page_title'] = f'{self.tag.name}'
        context['page_description'] = f'{self.tag.name}-идеально'
        context['authors'] = authors
        context['current_tag'] = self.tag  # Для подсветки активного тега
        return context


class PostByAutorListView(ListView):
    model = Post
    template_name = 'blog/post_list_tailwind.html'
    context_object_name = 'posts'
    paginate_by = 50

    def get_queryset(self):
        # Показывать только опубликованные статьи автора
        return Post.objects.filter(
            author__username=self.kwargs.get('username'),
            status='published'
        ).select_related('author', 'category').prefetch_related('tags')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        author = get_object_or_404(User, username=self.kwargs.get("username"))
        
        # Получаем теги из постов автора
        from django.db.models import Count
        author_tags = Tag.objects.filter(
            taggit_taggeditem_items__content_type__model='post',
            taggit_taggeditem_items__object_id__in=self.get_queryset().values_list('id', flat=True)
        ).annotate(
            posts_count=Count('taggit_taggeditem_items')
        ).distinct().order_by('-posts_count')[:10]
        
        # Кэширование категорий
        categorys = cache.get('categorys_list')
        if categorys is None:
            categorys = Category.objects.all()
            cache.set('categorys_list', categorys, 300)
        
        context['author'] = author
        context['tags'] = author_tags
        context['categorys'] = categorys
        context['page_title'] = f'Посты пользователя {author}'
        context['page_description'] = f'Все статьи автора {author} на сайте IdealImage.ru'
        return context


class AutorPostListView(ListView):
    model = Post
    template_name = 'blog/post_list_tailwind.html'
    context_object_name = 'posts'
    paginate_by = 50

    def get_queryset(self, **kwargs):
        posts = Post.objects.filter(author=self.request.user).order_by('-updated').select_related('author', 'category').prefetch_related('tags')
        return posts
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Получаем теги из постов автора
        from django.db.models import Count
        author_tags = Tag.objects.filter(
            taggit_taggeditem_items__content_type__model='post',
            taggit_taggeditem_items__object_id__in=self.get_queryset().values_list('id', flat=True)
        ).annotate(
            posts_count=Count('taggit_taggeditem_items')
        ).distinct().order_by('-posts_count')[:10]
        
        # Кэширование категорий
        categorys = cache.get('categorys_list')
        if categorys is None:
            categorys = Category.objects.all()
            cache.set('categorys_list', categorys, 300)
        
        context['tags'] = author_tags
        context['categorys'] = categorys
        context['author'] = self.request.user  # Добавляем автора для заголовка
        context['page_title'] = f'Мои статьи'
        context['page_description'] = f'Управление моими статьями на сайте IdealImage.ru'
        
        return context


def autor(request, autor):
    posts = Post.objects.filter(author__username=autor).order_by('-updated').select_related('author', 'category')
    context = {
        'posts': posts,
    }
    return render(request, 'blog/post-list.html', context)


def send_post_to_telegram_view(request):
    post = Post.objects.first()
    if not post:
        return HttpResponse("Нет доступных постов для отправки", content_type='text/plain', status=404)

    # Использование пайплайнов удалено - система пайплайнов больше не используется
    message = f"Функция дистрибуции временно недоступна (система пайплайнов удалена)"
    return HttpResponse(message, content_type='text/plain')


@login_required
def draft_improvement_review(request, post_id):
    """
    Просмотр и применение AI-улучшений черновика
    Доступ контролируется через dispatch в UpdateView
    """
    post = get_object_or_404(Post, id=post_id)
    
    # Проверяем что есть улучшенная версия
    if post.ai_improvement_status != 'ready':
        messages.warning(request, 'AI еще не завершил улучшение или улучшение не запрашивалось')
        return redirect('blog:post_update', slug=post.slug)
    
    context = {
        'post': post,
        'original_content': post.ai_draft_original,
        'improved_content': post.ai_draft_improved,
        'improvements_notes': post.ai_improvement_notes,
        'improvement_style': post.ai_improvement_style,
        'page_title': f'AI-улучшения: {post.title}',
        'page_description': f'Просмотр и сравнение AI-улучшений для статьи "{post.title}"'
    }
    
    return render(request, 'blog/draft_improvement_review.html', context)


@login_required
@require_POST
def accept_ai_improvements(request, post_id):
    """
    Принять AI-улучшения
    Доступ контролируется через dispatch в UpdateView
    """
    post = get_object_or_404(Post, id=post_id)
    
    if post.ai_improvement_status == 'ready':
        # ОТКЛЮЧЕНИЕ АВТОМОДЕРАЦИИ для суперюзеров и AI агентов
        is_superuser = request.user.is_superuser or request.user.is_staff
        is_ai_agent = request.user.username == 'ai_assistant' or (post.author and post.author.username == 'ai_assistant')
        if is_superuser or is_ai_agent:
            post._skip_auto_moderation = True
        
        # Применяем улучшенную версию
        post.content = post.ai_draft_improved
        post.ai_improvement_status = 'accepted'
        post.save()
        
        messages.success(request, '✅ AI-улучшения приняты и применены к статье!')
    
    return redirect('blog:post_update', slug=post.slug)


@login_required
@require_POST
def reject_ai_improvements(request, post_id):
    """
    Отклонить AI-улучшения и вернуться к оригиналу
    Доступ контролируется через dispatch в UpdateView
    """
    post = get_object_or_404(Post, id=post_id)
    
    if post.ai_improvement_status == 'ready':
        # ОТКЛЮЧЕНИЕ АВТОМОДЕРАЦИИ для суперюзеров и AI агентов
        is_superuser = request.user.is_superuser or request.user.is_staff
        is_ai_agent = request.user.username == 'ai_assistant' or (post.author and post.author.username == 'ai_assistant')
        if is_superuser or is_ai_agent:
            post._skip_auto_moderation = True
        
        # Возвращаем оригинал (не меняем content!)
        post.ai_improvement_status = 'rejected'
        post.ai_draft_improved = ''  # Очищаем улучшенную версию
        post.save()
        
        messages.info(request, 'AI-улучшения отклонены. Сохранена оригинальная версия.')
    
    return redirect('blog:post_update', slug=post.slug)


@login_required
@require_POST
def retry_ai_improvements(request, post_id):
    """
    Попросить AI переделать улучшения ещё раз
    Доступ контролируется через dispatch в UpdateView
    """
    post = get_object_or_404(Post, id=post_id)
    
    if post.status != 'draft':
        messages.error(request, '❌ AI-помощник работает только с черновиками')
        return redirect('blog:post_update', slug=post.slug)
    
    # Получаем параметры
    style = request.POST.get('style', post.ai_improvement_style or 'balanced')
    custom_prompt = request.POST.get('custom_prompt', '')
    generate_image = request.POST.get('generate_image') == 'on'
    image_prompt = request.POST.get('image_prompt', '')
    
    # Запускаем задачу заново
    if settings.DISABLE_AI:
        messages.warning(request, '⚠️ Локальный режим: AI отключён. Задачи в очередь не ставятся.')
        return redirect('blog:post_update', slug=post.slug)
    from django_q.tasks import async_task
    
    # ОТКЛЮЧЕНИЕ АВТОМОДЕРАЦИИ для суперюзеров и AI агентов
    is_superuser = request.user.is_superuser or request.user.is_staff
    is_ai_agent = request.user.username == 'ai_assistant' or (post.author and post.author.username == 'ai_assistant')
    if is_superuser or is_ai_agent:
        post._skip_auto_moderation = True
    
    post.ai_improvement_status = 'pending'
    post.ai_draft_improved = ''  # Очищаем старую улучшенную версию
    post.save()
    
    # Асинхронный запуск улучшения текста
    task_id = async_task(
        'Asistent.tasks.improve_author_draft_task',
        post.id,
        style,
        custom_prompt,
        task_name=f'Retry improve draft #{post.id}'
    )
    post.ai_improvement_task_id = task_id
    post.ai_improvement_requested_at = timezone.now()
    post.save(update_fields=['ai_improvement_status', 'ai_draft_improved', 'ai_improvement_task_id', 'ai_improvement_requested_at'])
    
    # Если нужно сгенерировать изображение
    if generate_image:
        async_task(
            'Asistent.tasks.generate_post_image_task',
            post.id,
            image_prompt,
            request.user.id,
            task_name=f'Generate image for post #{post.id}'
        )
    
    messages.success(request, '🔄 AI-помощник переделывает улучшения! Вы получите уведомление когда будет готово.')
    return redirect('blog:post_update', slug=post.slug)


@login_required
@require_POST
def apply_generated_image(request, post_id):
    """
    Применить сгенерированное AI изображение к статье
    Доступ контролируется через dispatch в UpdateView
    """
    post = get_object_or_404(Post, id=post_id)
    
    image_path = request.POST.get('image_path', '')
    
    if not image_path:
        messages.error(request, '❌ Путь к изображению не указан')
        return redirect('blog:post_update', slug=post.slug)
    
    try:
        # Нормализуем путь: приводим к относительному внутри MEDIA_ROOT
        normalized = image_path.strip()
        if not normalized:
            raise ValueError('Путь к изображению пустой')

        # Если это URL, извлекаем путь
        if normalized.startswith('http://') or normalized.startswith('https://'):
            parsed = urlparse(normalized)
            normalized = parsed.path

        # Если начинается с MEDIA_URL, обрезаем его
        media_url = getattr(settings, 'MEDIA_URL', '/media/') or '/media/'
        if normalized.startswith(media_url):
            normalized = normalized[len(media_url):]

        # Если абсолютный путь внутри MEDIA_ROOT, делаем относительным
        media_root = getattr(settings, 'MEDIA_ROOT', '')
        if media_root and normalized.startswith(media_root):
            normalized = os.path.relpath(normalized, media_root)

        # Удаляем лидирующие слэши и обратные слэши
        normalized = normalized.lstrip('/\\')

        # Безопасность: запрещаем переходы по каталогам
        if '..' in normalized or normalized.startswith(('/', '\\')):
            raise ValueError('Недопустимый путь к файлу')

        # ОТКЛЮЧЕНИЕ АВТОМОДЕРАЦИИ для суперюзеров и AI агентов
        is_superuser = request.user.is_superuser or request.user.is_staff
        is_ai_agent = request.user.username == 'ai_assistant' or (post.author and post.author.username == 'ai_assistant')
        if is_superuser or is_ai_agent:
            post._skip_auto_moderation = True
        
        # Присваиваем относительное имя файлу (файл уже должен существовать в хранилище)
        post.kartinka.name = normalized
        post.save()
        
        # Удаляем уведомление о сгенерированном изображении
        from Asistent.models import AuthorNotification
        AuthorNotification.objects.filter(
            related_article=post,
            message__contains='AI_GENERATED_IMAGE'
        ).delete()
        
        messages.success(request, '✅ Новое изображение применено!')
        
    except Exception as e:
        messages.error(request, f'❌ Ошибка применения изображения: {str(e)}')
    
    return redirect('blog:post_update', slug=post.slug)


@login_required
@require_POST
def reject_generated_image(request, post_id):
    """
    Отклонить сгенерированное AI изображение
    Доступ контролируется через dispatch в UpdateView
    """
    post = get_object_or_404(Post, id=post_id)
    
    image_path = request.POST.get('image_path', '')
    
    if image_path:
        # Удаляем файл сгенерированного изображения
        try:
            from django.core.files.storage import default_storage
            if default_storage.exists(image_path):
                default_storage.delete(image_path)
                logger.info(f"🗑️ Удалено сгенерированное изображение: {image_path}")
        except Exception as e:
            logger.error(f"❌ Ошибка удаления файла: {e}")
    
    # Удаляем уведомление
    from Asistent.models import AuthorNotification
    AuthorNotification.objects.filter(
        related_article=post,
        message__contains='AI_GENERATED_IMAGE'
    ).delete()
    
    messages.info(request, '❌ Сгенерированное изображение отклонено')
    return redirect('blog:post_update', slug=post.slug)


@login_required
def request_ai_help(request, post_id):
    """
    Запросить помощь AI Agent через галочку в профиле
    Устанавливает флаг и СОХРАНЯЕТ СТАТЬЮ для запуска модерации
    Администратор может помогать с постами любых авторов
    """
    from django.contrib import messages
    
    # Администратор может редактировать посты любых авторов
    if request.user.is_staff or request.user.is_superuser:
        post = get_object_or_404(Post, id=post_id)
    else:
        post = get_object_or_404(Post, id=post_id, author=request.user)
    
    if request.method == 'POST':
        # Устанавливаем флаг запроса помощи
        post.ai_draft_improvement_requested = True
        
        # ОТКЛЮЧЕНИЕ АВТОМОДЕРАЦИИ для суперюзеров и AI агентов
        is_superuser = request.user.is_superuser or request.user.is_staff
        is_ai_agent = request.user.username == 'ai_assistant' or (post.author and post.author.username == 'ai_assistant')
        if is_superuser or is_ai_agent:
            post._skip_auto_moderation = True
        
        # КРИТИЧНО: Сохраняем статью со статусом 'published' чтобы запустить модерацию
        # AI Agent проверит и либо опубликует, либо вернет в draft с исправлениями
        original_status = post.status
        post.status = 'published'  # Пытаемся опубликовать - сработает полная модерация!
        post.save()  # Здесь сработает pre_save signal с модерацией
        
        # Перезагружаем из БД чтобы увидеть что сделал AI Agent
        post.refresh_from_db()
        
        # Формируем сообщение в зависимости от результата
        if post.status == 'published':
            messages.success(
                request, 
                f'✅ AI Agent исправил и ОПУБЛИКОВАЛ статью! '
                f'💰 Штраф: -{post.ai_penalty_percent}% баллов за помощь AI.'
            )
        else:
            # Статья всё еще в черновиках - смотрим причины
            messages.warning(
                request, 
                f'🤖 AI Agent поработал над статьей. '
                f'Проверьте замечания в черновике - возможно нужны дополнительные правки. '
                f'💰 Текущий штраф: -{post.ai_penalty_percent}% баллов.'
            )
    
    # Перенаправляем обратно в профиль
    user_slug = request.user.profile.slug if hasattr(request.user, 'profile') else request.user.username
    return redirect('Visitor:profile_detail', slug=user_slug)


@login_required
def request_ai_improvement(request, post_id):
    """
    Запросить AI-улучшение для существующего черновика
    Доступ контролируется через dispatch в UpdateView
    """
    post = get_object_or_404(Post, id=post_id)
    
    if post.status != 'draft':
        messages.error(request, '❌ AI-помощник работает только с черновиками')
        return redirect('blog:post_update', slug=post.slug)
    
    if not post.content:
        messages.error(request, '❌ Черновик пустой. Напишите текст перед запросом AI-помощника')
        return redirect('blog:post_update', slug=post.slug)
    
    # Запускаем задачу
    if settings.DISABLE_AI:
        messages.warning(request, '⚠️ Локальный режим: AI отключён. Задачи в очередь не ставятся.')
        return redirect('blog:post_update', slug=post.slug)
    from django_q.tasks import async_task
    style = request.POST.get('style', 'balanced')
    
    # ОТКЛЮЧЕНИЕ АВТОМОДЕРАЦИИ для суперюзеров и AI агентов
    is_superuser = request.user.is_superuser or request.user.is_staff
    is_ai_agent = request.user.username == 'ai_assistant' or (post.author and post.author.username == 'ai_assistant')
    if is_superuser or is_ai_agent:
        post._skip_auto_moderation = True
    
    post.ai_draft_improvement_requested = True
    post.ai_improvement_status = 'processing'
    post.save()
    
    task_id = async_task(
        'Asistent.tasks.improve_author_draft_task',
        post.id,
        style,
        task_name=f'Improve draft #{post.id}'
    )
    post.ai_improvement_task_id = task_id
    post.ai_improvement_requested_at = timezone.now()
    post.save(update_fields=['ai_draft_improvement_requested', 'ai_improvement_status', 'ai_improvement_task_id', 'ai_improvement_requested_at'])
    
    messages.success(request, '✨ AI-помощник начал работу! Вы получите уведомление когда улучшение будет готово.')
    return redirect('blog:post_update', slug=post.slug)


class SearchPageView(ListView):
    model = Post  
    template_name = 'home/search.html' 
    paginate_by = 5 

    def get_queryset(self):
        query = self.request.GET.get('query')
        if query:
            # Искать только среди опубликованных статей
            return Post.objects.filter(
                Q(title__icontains=query) | Q(description__icontains=query),
                status='published'
            ).select_related('author', 'category')
        return Post.objects.none()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query'] = self.request.GET.get('query')
        return context


