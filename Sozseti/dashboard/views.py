"""
Dashboard views для управления социальными сетями
"""
from django.views.generic import TemplateView, ListView, DetailView
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.decorators import method_decorator
from django.db.models import Sum, Count, Avg, Q
from django.utils import timezone
from datetime import timedelta
from ..models import (
    SocialChannel,
    PostPublication,
    ChannelAnalytics,
    PublicationSchedule,
    SocialPlatform,
    AdCampaign,
)


@method_decorator(staff_member_required, name='dispatch')
class DashboardOverview(TemplateView):
    """
    Главная страница дашборда с общей статистикой
    """
    template_name = 'Sozseti/dashboard/overview.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Базовые переменные для base_tailwind.html
        context['page_title'] = 'Дашборд социальных сетей - IdealImage.ru'
        context['page_description'] = 'Управление публикациями в социальных сетях'
        context['og_title'] = 'Дашборд социальных сетей'
        context['og_description'] = 'Статистика и управление публикациями в Telegram, VK, Pinterest, Rutube, Dzen'
        
        # Общая статистика
        week_ago = timezone.now() - timedelta(days=7)
        
        context['stats'] = {
            'total_channels': SocialChannel.objects.filter(is_active=True).count(),
            'total_platforms': SocialPlatform.objects.filter(is_active=True).count(),
            'publications_week': PostPublication.objects.filter(
                published_at__gte=week_ago,
                status='published'
            ).count(),
            'total_views_week': PostPublication.objects.filter(
                published_at__gte=week_ago,
                status='published'
            ).aggregate(total=Sum('views_count'))['total'] or 0,
            'total_engagement_week': PostPublication.objects.filter(
                published_at__gte=week_ago,
                status='published'
            ).aggregate(
                total=Sum('likes_count') + Sum('comments_count') + Sum('shares_count')
            )['total'] or 0,
            'active_schedules': PublicationSchedule.objects.filter(is_active=True).count(),
        }
        
        # Топ каналы по вовлечённости
        context['top_channels'] = PostPublication.objects.filter(
            published_at__gte=week_ago,
            status='published'
        ).values('channel__channel_name', 'channel__id').annotate(
            avg_engagement=Avg('engagement_score'),
            total_views=Sum('views_count')
        ).order_by('-avg_engagement')[:5]
        
        # Последние публикации
        context['recent_publications'] = PostPublication.objects.filter(
            status='published'
        ).select_related('post', 'channel', 'channel__platform').order_by('-published_at')[:10]
        
        # Ошибки публикаций
        context['failed_publications'] = PostPublication.objects.filter(
            status='failed',
            created_at__gte=week_ago
        ).select_related('post', 'channel').order_by('-created_at')[:5]
        
        return context


@method_decorator(staff_member_required, name='dispatch')
class ChannelsList(ListView):
    """
    Список всех каналов со статистикой
    """
    model = SocialChannel
    template_name = 'Sozseti/dashboard/channels_list.html'
    context_object_name = 'channels'
    paginate_by = 50
    
    def get_queryset(self):
        queryset = SocialChannel.objects.select_related('platform').prefetch_related(
            'publications'
        ).annotate(
            total_publications=Count('publications', filter=Q(publications__status='published')),
            total_views=Sum('publications__views_count', filter=Q(publications__status='published')),
            avg_engagement=Avg('publications__engagement_score', filter=Q(publications__status='published')),
        )
        
        # Фильтр по платформе
        platform = self.request.GET.get('platform')
        if platform:
            queryset = queryset.filter(platform__name=platform)
        
        # Сортировка
        sort_by = self.request.GET.get('sort', '-subscribers_count')
        queryset = queryset.order_by(sort_by)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Базовые переменные
        context['page_title'] = 'Список каналов - IdealImage.ru'
        context['page_description'] = 'Все каналы и статистика публикаций'
        context['og_title'] = 'Список каналов'
        context['og_description'] = 'Управление каналами в социальных сетях'
        
        # Фильтры
        context['platforms'] = SocialPlatform.objects.all()
        context['selected_platform'] = self.request.GET.get('platform', '')
        context['selected_sort'] = self.request.GET.get('sort', '-subscribers_count')
        
        # Общая статистика
        channels = self.get_queryset()
        context['total_subscribers'] = sum(ch.subscribers_count for ch in channels)
        context['total_channels'] = channels.count()
        
        return context


@method_decorator(staff_member_required, name='dispatch')
class ChannelPerformance(DetailView):
    """
    Детальная статистика по конкретному каналу
    """
    model = SocialChannel
    template_name = 'Sozseti/dashboard/channel_detail.html'
    context_object_name = 'channel'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        channel = self.object
        
        # Базовые переменные для base_tailwind.html
        context['page_title'] = f'{channel.channel_name} - Статистика канала'
        context['page_description'] = f'Детальная статистика и аналитика канала {channel.channel_name}'
        context['og_title'] = f'{channel.channel_name} - Статистика'
        context['og_description'] = f'Просмотры, вовлечённость и топ посты канала {channel.channel_name}'
        
        # Статистика за последний месяц
        month_ago = timezone.now() - timedelta(days=30)
        
        publications = PostPublication.objects.filter(
            channel=channel,
            status='published',
            published_at__gte=month_ago
        )
        
        context['stats'] = {
            'publications_count': publications.count(),
            'total_views': publications.aggregate(total=Sum('views_count'))['total'] or 0,
            'total_likes': publications.aggregate(total=Sum('likes_count'))['total'] or 0,
            'total_comments': publications.aggregate(total=Sum('comments_count'))['total'] or 0,
            'avg_engagement': publications.aggregate(avg=Avg('engagement_score'))['avg'] or 0,
        }
        
        # Топ посты
        context['top_posts'] = publications.order_by('-engagement_score')[:10]
        
        # График публикаций по дням
        daily_stats = publications.extra(
            select={'day': 'date(published_at)'}
        ).values('day').annotate(
            posts=Count('id'),
            views=Sum('views_count')
        ).order_by('day')
        
        context['daily_chart_data'] = list(daily_stats)
        
        # Аналитика по дням
        context['analytics'] = ChannelAnalytics.objects.filter(
            channel=channel
        ).order_by('-date')[:30]
        
        return context


@method_decorator(staff_member_required, name='dispatch')
class ContentCalendar(TemplateView):
    """
    Календарь запланированных публикаций
    """
    template_name = 'Sozseti/dashboard/calendar.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Базовые переменные для base_tailwind.html
        context['page_title'] = 'Календарь публикаций - IdealImage.ru'
        context['page_description'] = 'Календарь запланированных публикаций в социальных сетях'
        context['og_title'] = 'Календарь публикаций'
        context['og_description'] = 'Расписания и запланированные публикации в соцсетях'
        
        # Запланированные публикации
        context['scheduled'] = PostPublication.objects.filter(
            status='scheduled'
        ).select_related('post', 'channel').order_by('scheduled_at')
        
        # Активные расписания
        context['schedules'] = PublicationSchedule.objects.filter(
            is_active=True
        ).prefetch_related('channels', 'categories').order_by('next_run')
        
        return context


@method_decorator(staff_member_required, name='dispatch')
class AdvertisingDashboard(TemplateView):
    """
    Дашборд рекламных кампаний
    """
    template_name = 'Sozseti/dashboard/advertising.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Базовые переменные
        context['page_title'] = 'Дашборд рекламы - IdealImage.ru'
        context['page_description'] = 'Управление рекламными кампаниями в социальных сетях'
        context['og_title'] = 'Дашборд рекламы'
        context['og_description'] = 'Статистика и аналитика рекламных кампаний'
        
        # Активные кампании
        active_campaigns = AdCampaign.objects.filter(status='active')
        context['active_campaigns'] = active_campaigns
        
        # Статистика
        context['stats'] = {
            'total_campaigns': AdCampaign.objects.count(),
            'active_campaigns': active_campaigns.count(),
            'total_budget': AdCampaign.objects.aggregate(total=Sum('budget'))['total'] or 0,
            'total_spent': AdCampaign.objects.aggregate(total=Sum('spent'))['total'] or 0,
        }
        
        # Топ кампании по ROI
        campaigns_with_metrics = AdCampaign.objects.filter(
            status__in=['active', 'completed']
        ).order_by('-created_at')
        
        context['top_campaigns'] = campaigns_with_metrics[:10]
        
        # Кампании по платформам
        context['campaigns_by_platform'] = {}
        for platform in SocialPlatform.objects.all():
            campaigns = AdCampaign.objects.filter(platforms=platform)
            if campaigns.exists():
                context['campaigns_by_platform'][platform.get_name_display()] = {
                    'count': campaigns.count(),
                    'budget': campaigns.aggregate(total=Sum('budget'))['total'] or 0,
                    'spent': campaigns.aggregate(total=Sum('spent'))['total'] or 0,
                }
        
        return context


@method_decorator(staff_member_required, name='dispatch')
class AIAgentDashboard(TemplateView):
    """
    Дашборд AI-агента для управления каналами
    """
    template_name = 'Sozseti/dashboard/ai_agent.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Базовые переменные
        context['page_title'] = 'AI-Агент - IdealImage.ru'
        context['page_description'] = 'Управление каналами с помощью AI-агента'
        context['og_title'] = 'AI-Агент'
        context['og_description'] = 'Умное управление публикациями и аналитика'
        
        # Рекомендации AI для каналов
        channels = SocialChannel.objects.filter(
            platform__name='telegram',
            is_active=True
        ).annotate(
            publications_count=Count('publications', filter=Q(publications__status='published'))
        ).order_by('-subscribers_count')
        
        context['channels'] = channels
        
        # Последние действия AI
        week_ago = timezone.now() - timedelta(days=7)
        context['recent_publications'] = PostPublication.objects.filter(
            published_at__gte=week_ago,
            status='published'
        ).select_related('post', 'channel').order_by('-published_at')[:20]
        
        return context
