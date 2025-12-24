from django.utils import timezone
from django.contrib.auth.models import AnonymousUser


class SubscriptionMiddleware:
    """
    Middleware для проверки подписок пользователей
    Добавляет в request информацию о подписках
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Инициализируем флаги подписок
        request.has_premium = False
        request.has_ai_coauthor = False
        
        # Проверяем только для авторизованных пользователей
        if hasattr(request, 'user') and not isinstance(request.user, AnonymousUser) and request.user.is_authenticated:
            try:
                from donations.models import Subscription
                
                # Проверяем Premium подписку
                request.has_premium = Subscription.objects.filter(
                    user=request.user,
                    subscription_type='premium',
                    is_active=True,
                    end_date__gt=timezone.now()
                ).exists()
                
                # Проверяем AI-Соавтор подписку
                request.has_ai_coauthor = Subscription.objects.filter(
                    user=request.user,
                    subscription_type='ai_coauthor',
                    is_active=True,
                    end_date__gt=timezone.now()
                ).exists()
                
            except Exception as e:
                # В случае ошибки (например, миграции не применены) - просто пропускаем
                pass
        
        response = self.get_response(request)
        return response


class PaidContentMiddleware:
    """
    Middleware для проверки доступа к платному контенту
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        return response
    
    def process_view(self, request, view_func, view_args, view_kwargs):
        """
        Проверяет доступ к платным статьям и марафонам
        """
        # Проверяем только для детальных страниц статей
        if 'slug' in view_kwargs and hasattr(request, 'user'):
            try:
                from blog.models import Post
                from donations.models import PaidArticle, ArticlePurchase, Marathon, MarathonPurchase
                
                # Получаем статью
                post = Post.objects.get(slug=view_kwargs['slug'])
                
                # Проверяем, является ли статья платной
                if hasattr(post, 'paid_access') and post.paid_access.is_active:
                    # Проверяем, купил ли пользователь доступ
                    if not request.user.is_authenticated:
                        # Неавторизованный пользователь - показываем превью
                        request.show_paid_preview = True
                    else:
                        # Проверяем покупку
                        has_purchased = ArticlePurchase.objects.filter(
                            user=request.user,
                            article=post.paid_access
                        ).exists()
                        
                        if not has_purchased:
                            request.show_paid_preview = True
                        else:
                            request.show_paid_preview = False
                
            except Exception as e:
                # В случае ошибки - просто пропускаем
                pass
        
        return None
