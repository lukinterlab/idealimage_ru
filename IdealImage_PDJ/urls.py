from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse
from django.urls import path, include, re_path
from blog.views_sitemap import image_sitemap
from blog.sitemaps import CategorySitemap, PostSitemap, TagSitemap, AuthorSitemap, ImageSitemap
from django.views.static import serve
from django.views.generic import RedirectView

sitemaps = {
    'posts': PostSitemap,
    'categorys': CategorySitemap,
    'tags': TagSitemap,
    'authors': AuthorSitemap,
    'images': ImageSitemap,
}

urlpatterns = [
    path('ckeditor/', include('ckeditor_uploader.urls')),
    path('admin/', admin.site.urls),
    path('sitemap.xml', image_sitemap, {'sitemaps': sitemaps}, name='sitemap'),
    path(
        '283ceba4f0c54817a342d7c177dedd19.txt',
        lambda request: HttpResponse("283ceba4f0c54817a342d7c177dedd19", content_type="text/plain"),
    ),
    
    path('blog/', include('blog.urls', namespace='blog')),
    
    path('post/tags/<str:tag>/', RedirectView.as_view(pattern_name='blog:post_by_tags', permanent=True)),
    path('post/author/<str:author>/', RedirectView.as_view(pattern_name='blog:post_by_author', permanent=True)),
    path('post/<slug:slug>/', RedirectView.as_view(pattern_name='blog:post_detail', permanent=True, query_string=True)),
    path('articles/<slug:slug>/', RedirectView.as_view(pattern_name='blog:article_lookup', permanent=True, query_string=True)),
    re_path(r'^articles/(?P<slug>[-a-z0-9]+)/?$', RedirectView.as_view(pattern_name='blog:article_lookup', permanent=True, query_string=True)),
    path('category/<str:slug>/', RedirectView.as_view(pattern_name='blog:post_list_by_category', permanent=True)),
    path('author/<str:slug>/', RedirectView.as_view(pattern_name='blog:autor', permanent=True)),
    
    path('visitor/', include('Visitor.urls', namespace='Visitor')),
    path('donations/', include('donations.urls', namespace='donations')),
    path('asistent/', include('Asistent.urls', namespace='asistent')),
    path('schedules/', include('Asistent.schedule.urls', namespace='schedule')),
    path('sozseti/', include('Sozseti.urls', namespace='sozseti')),
    path('advertising/', include('advertising.urls', namespace='advertising')),
    
    path('', include('Home.urls', namespace='Home')),
    
    # Ads.txt - динамический через advertising app (должен быть ДО других маршрутов)
    re_path(r'^ads\.txt$', lambda request: __import__('advertising.views', fromlist=['ads_txt_view']).ads_txt_view(request)),
    re_path(r'^robots\.txt$', serve, {'document_root': settings.BASE_DIR, 'path': "robots.txt"}),
    re_path(r'^favicon\.ico$', serve, {'document_root': settings.BASE_DIR, 'path': "favicon.ico"}),
    path("__reload__/", include("django_browser_reload.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
else:
    # Видео файлы - через кастомный view с Range support
    from blog.video_serve import serve_video
    urlpatterns += [
        re_path(r'^media/(?P<path>images/.*\.(mp4|webm|mov))$', serve_video, name='serve_video'),
        # Остальные media файлы - стандартный serve
        re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
        re_path(r'^static/(?P<path>.*)$', serve, {'document_root': settings.STATIC_ROOT}),
    ]

