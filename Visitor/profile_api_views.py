"""
API views для динамической загрузки контента профиля
"""
from django.shortcuts import render, get_object_or_404
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.db import models
from blog.models import Comment, Post
from blog.models_likes import Like, Bookmark  # Используем модели из blog

User = get_user_model()


def profile_comments_api(request, user_id):
    """API для загрузки комментариев К СТАТЬЯМ автора (только неотвеченные)"""
    user = get_object_or_404(User, id=user_id)
    
    # Получаем все статьи автора
    user_posts = Post.objects.filter(author=user).values_list('id', flat=True)
    
    # Получаем все комментарии к статьям автора
    all_comments = Comment.objects.filter(
        post_id__in=user_posts,
        active=True,
        parent__isnull=True  # Только родительские комментарии
    ).select_related('post').prefetch_related('replies').order_by('-created')
    
    # Фильтруем: показываем только те, на которые автор еще НЕ ответил
    unanswered_comments = []
    for comment in all_comments:
        # Проверяем есть ли ответ от автора (по username или email)
        author_replied = comment.replies.filter(
            models.Q(author_comment=user.username) | 
            models.Q(email=user.email)
        ).exists()
        
        if not author_replied:
            unanswered_comments.append(comment)
    
    comments = unanswered_comments
    
    # Пагинация
    paginator = Paginator(comments, 15)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'comments': page_obj,
        'page_obj': page_obj,
        'user_profile': user,
        'is_author': request.user.is_authenticated and request.user == user,  # Автор может отвечать
        'current_user': request.user,
    }
    
    return render(request, 'visitor/partials/comments_list.html', context)


def profile_favorites_api(request, user_id):
    """API для загрузки избранных постов (лайкнутых)"""
    user = get_object_or_404(User, id=user_id)
    
    # Получаем посты которые лайкнул пользователь
    liked_post_ids = Like.objects.filter(user=user).values_list('post_id', flat=True)
    posts = Post.objects.filter(id__in=liked_post_ids, status='published').select_related('author', 'category').order_by('-created')
    
    # Пагинация
    paginator = Paginator(posts, 12)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'posts': page_obj,
        'page_obj': page_obj,
        'user_profile': user,
    }
    
    return render(request, 'visitor/partials/favorites_list.html', context)


def profile_bookmarks_api(request, user_id):
    """API для загрузки закладок пользователя"""
    user = get_object_or_404(User, id=user_id)
    
    # Пока закладки не реализованы, показываем заглушку
    # TODO: добавить модель Bookmark
    
    context = {
        'user_profile': user,
        'bookmarks_available': False,
    }
    
    return render(request, 'visitor/partials/bookmarks_list.html', context)

