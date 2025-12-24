from django.contrib import admin
from django.urls import path
from .views import *
from . import api_views
from .feeds import LatestPostsFeed, CategoryPostsFeed

app_name = 'blog'

urlpatterns = [
    path('', PostListView.as_view(), name='post_list'),
    
    # RSS/Atom Feeds
    path('feed/', LatestPostsFeed(), name='rss_feed'),
    path('category/<str:slug>/feed/', CategoryPostsFeed(), name='category_rss_feed'),
    # Сначала — фиксированные пути
   
    path('post/create/', PostCreateView.as_view(), name='post_create'),
    path('post/<str:slug>/', post_detail, name='post_detail'),
     # Потом — динамические
    path('article-lookup/<str:slug>/', article_lookup, name='article_lookup'),  # ← ИСПРАВЛЕНО: убран views.
    path('post/<str:slug>/update/', PostUpdateView.as_view(), name='post_update'),
    path('post/<str:slug>/delete/', PostDeleteView.as_view(), name='post_delete'),
    path('category/<str:slug>/', PostByCategoryListView.as_view(), name="post_list_by_category"),
    path('post/tags/<str:tag>/', PostByTagListView.as_view(), name='post_by_tags'),
    path('author/<str:slug>/', AutorPostListView.as_view(), name='autor'),
    path('post/author/<str:author>/', PostByAutorListView.as_view(), name='post_by_author'),
    
    # API для лайков и реакций
    path('api/post/<int:post_id>/like/', api_views.toggle_like, name='toggle_like'),
    path('api/post/<int:post_id>/rate/', api_views.rate_post, name='rate_post'),
    path('api/post/<int:post_id>/bookmark/', api_views.toggle_bookmark, name='toggle_bookmark'),
    path('api/post/<int:post_id>/stats/', api_views.get_post_stats, name='get_post_stats'),
    path('api/post/<int:post_id>/increment-views/', api_views.increment_post_views, name='increment_post_views'),
    
    # AI-соавтор
    path('post/<int:post_id>/ai-review/', draft_improvement_review, name='draft_improvement_review'),
    path('post/<int:post_id>/ai-accept/', accept_ai_improvements, name='accept_ai_improvements'),
    path('post/<int:post_id>/ai-reject/', reject_ai_improvements, name='reject_ai_improvements'),
    path('post/<int:post_id>/ai-retry/', retry_ai_improvements, name='retry_ai_improvements'),
    path('post/<int:post_id>/ai-request/', request_ai_improvement, name='request_ai_improvement'),
    path('post/<int:post_id>/ai-help/', request_ai_help, name='request_ai_help'),  # Помощь через галочку
    
    # AI-генерация изображений
    path('post/<int:post_id>/apply-generated-image/', apply_generated_image, name='apply_generated_image'),
    path('post/<int:post_id>/reject-generated-image/', reject_generated_image, name='reject_generated_image'),
    
    # API для комментариев
    path('comment/reply/', api_views.create_comment_reply, name='create_comment_reply'),
]

