"""
API представления для системы лайков и реакций
"""
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.db import transaction
import json

from .models import Post, Comment
from .models_likes import Like, PostRating, Bookmark


@require_POST
def toggle_like(request, post_id):
    """Переключение лайка/реакции на статью (для всех пользователей, включая анонимных)"""
    try:
        post = get_object_or_404(Post, id=post_id)
        data = json.loads(request.body)
        reaction_type = data.get('reaction_type', 'like')
        
        # Проверяем валидность типа реакции
        valid_reactions = [choice[0] for choice in Like.REACTION_TYPES]
        if reaction_type not in valid_reactions:
            return JsonResponse({'error': 'Неверный тип реакции'}, status=400)
        
        # Определяем идентификатор пользователя
        if request.user.is_authenticated:
            user = request.user
            session_key = None
        else:
            user = None
            # Для анонимных пользователей создаем/получаем сессию
            if not request.session.session_key:
                request.session.create()
            session_key = request.session.session_key
        
        with transaction.atomic():
            # Ищем существующий лайк
            if user:
                # Для зарегистрированного пользователя
                like = Like.objects.filter(post=post, user=user).first()
            else:
                # Для анонимного пользователя
                like = Like.objects.filter(post=post, session_key=session_key).first()
            
            if like:
                # Если лайк уже существует
                if like.reaction_type == reaction_type:
                    # Если тот же тип реакции - убираем лайк
                    like.delete()
                    action = 'removed'
                else:
                    # Если другой тип - обновляем
                    like.reaction_type = reaction_type
                    like.save()
                    action = 'updated'
            else:
                # Создаем новый лайк
                Like.objects.create(
                    post=post,
                    user=user,
                    session_key=session_key,
                    reaction_type=reaction_type
                )
                action = 'added'
        
        # Получаем обновленную статистику
        likes_count = post.get_likes_count()
        likes_by_type = list(post.get_likes_by_type())
        
        # Получаем реакцию пользователя
        if user:
            user_reaction = post.get_user_reaction(user)
        else:
            user_reaction = post.get_user_reaction_by_session(session_key)
        
        return JsonResponse({
            'success': True,
            'action': action,
            'likes_count': likes_count,
            'likes_by_type': likes_by_type,
            'user_reaction': user_reaction,
            'reaction_type': reaction_type
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Неверный JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_POST
@login_required
def rate_post(request, post_id):
    """Оценка статьи"""
    try:
        post = get_object_or_404(Post, id=post_id)
        data = json.loads(request.body)
        rating = data.get('rating')
        
        if not rating or not isinstance(rating, int) or rating < 1 or rating > 5:
            return JsonResponse({'error': 'Рейтинг должен быть от 1 до 5'}, status=400)
        
        with transaction.atomic():
            # Создаем или обновляем рейтинг
            post_rating, created = PostRating.objects.get_or_create(
                post=post,
                user=request.user,
                defaults={'rating': rating}
            )
            
            if not created:
                post_rating.rating = rating
                post_rating.save()
                action = 'updated'
            else:
                action = 'added'
        
        # Получаем обновленную статистику
        average_rating = post.get_average_rating()
        ratings_count = post.get_ratings_count()
        user_rating = post.get_user_rating(request.user)
        
        return JsonResponse({
            'success': True,
            'action': action,
            'average_rating': average_rating,
            'ratings_count': ratings_count,
            'user_rating': user_rating,
            'rating': rating
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Неверный JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_POST
@login_required
def toggle_bookmark(request, post_id):
    """Переключение закладки"""
    try:
        post = get_object_or_404(Post, id=post_id)
        
        with transaction.atomic():
            bookmark, created = Bookmark.objects.get_or_create(
                post=post,
                user=request.user
            )
            
            if not created:
                bookmark.delete()
                action = 'removed'
            else:
                action = 'added'
        
        # Получаем обновленную статистику
        bookmarks_count = post.get_bookmarks_count()
        is_bookmarked = post.is_bookmarked_by_user(request.user)
        
        return JsonResponse({
            'success': True,
            'action': action,
            'bookmarks_count': bookmarks_count,
            'is_bookmarked': is_bookmarked
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def get_post_stats(request, post_id):
    """Получить статистику статьи"""
    try:
        post = get_object_or_404(Post, id=post_id)
        
        # Статистика лайков
        likes_count = post.get_likes_count()
        likes_by_type = list(post.get_likes_by_type())
        
        # Определяем реакцию пользователя (зарегистрированного или анонимного)
        if request.user.is_authenticated:
            user_reaction = post.get_user_reaction(request.user)
        else:
            session_key = request.session.session_key
            user_reaction = post.get_user_reaction_by_session(session_key) if session_key else None
        
        # Статистика рейтингов
        average_rating = post.get_average_rating()
        ratings_count = post.get_ratings_count()
        user_rating = post.get_user_rating(request.user) if request.user.is_authenticated else None
        
        # Статистика закладок
        bookmarks_count = post.get_bookmarks_count()
        is_bookmarked = post.is_bookmarked_by_user(request.user) if request.user.is_authenticated else False
        
        return JsonResponse({
            'success': True,
            'likes': {
                'count': likes_count,
                'by_type': likes_by_type,
                'user_reaction': user_reaction
            },
            'ratings': {
                'average': average_rating,
                'count': ratings_count,
                'user_rating': user_rating
            },
            'bookmarks': {
                'count': bookmarks_count,
                'is_bookmarked': is_bookmarked
            }
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_POST
@login_required
def create_comment_reply(request):
    """Создание ответа на комментарий"""
    try:
        data = json.loads(request.body)
        post_id = data.get('post_id')
        parent_id = data.get('parent_id')
        content = data.get('content', '').strip()
        
        if not content:
            return JsonResponse({'success': False, 'error': 'Текст ответа не может быть пустым'}, status=400)
        
        if len(content) > 3000:
            return JsonResponse({'success': False, 'error': 'Текст слишком длинный (максимум 3000 символов)'}, status=400)
        
        # Получаем пост и родительский комментарий
        post = get_object_or_404(Post, id=post_id)
        parent_comment = get_object_or_404(Comment, id=parent_id, post=post)
        
        # Создаем ответ
        reply = Comment.objects.create(
            post=post,
            parent=parent_comment,
            author_comment=request.user.username,
            email=request.user.email,
            content=content,
            active=True
        )
        
        return JsonResponse({
            'success': True,
            'comment_id': reply.id,
            'message': 'Ответ успешно добавлен!'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Неверный формат данных'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_POST
@csrf_exempt
def increment_post_views(request, post_id):
    """Увеличение счётчика просмотров статьи (для AJAX)"""
    try:
        from django.db.models import F
        
        post = get_object_or_404(Post, id=post_id)
        
        # Увеличиваем счетчик просмотров БЕЗ вызова сигналов
        Post.objects.filter(pk=post.pk).update(views=F('views') + 1)
        
        # Получаем обновленное значение
        post.refresh_from_db()
        
        return JsonResponse({
            'success': True,
            'views': post.views
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)