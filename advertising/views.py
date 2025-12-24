"""
Views для управления рекламой
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST, require_http_methods
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.db.models import Sum, Count, Q, F, Avg
from django.utils import timezone
from django.contrib import messages
from datetime import timedelta, datetime
from decimal import Decimal
from urllib.parse import unquote
from collections import defaultdict
import json

from .decorators import marketing_required
from .models import (
    AdPlace, Advertiser, AdCampaign, AdBanner, AdSchedule,
    ContextAd, AdInsertion, AdClick, AdImpression,
    AdPerformanceML, AdRecommendation, ExternalScript, AdsTxtSettings
)
from blog.models import Post
from django.views.decorators.http import require_GET


def get_client_ip(request):
    """Получить IP адрес клиента"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


# ============ РЕДИРЕКТЫ КЛИКОВ ============

def banner_click_redirect(request, banner_id):
    """Редирект при клике на баннер или карточку"""
    banner = get_object_or_404(AdBanner, id=banner_id, is_active=True)
    
    # Получаем номер карточки и URL редиректа из параметров
    card_num = request.GET.get('card')
    redirect_url = request.GET.get('redirect')
    
    # Если указана карточка и её URL - используем его
    if card_num and redirect_url:
        target_url = unquote(redirect_url)
    else:
        # Иначе используем общий target_url баннера
        target_url = banner.target_url
    
    # Создаем сессию если её нет
    if not request.session.session_key:
        request.session.create()
    
    # Сохраняем клик
    AdClick.objects.create(
        ad_banner=banner,
        user=request.user if request.user.is_authenticated else None,
        session_key=request.session.session_key or '',
        ip_address=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
        referer=request.META.get('HTTP_REFERER', ''),
        redirect_url=target_url
    )
    
    return redirect(target_url)


def context_click_redirect(request, context_ad_id):
    """Редирект при клике на контекстную рекламу"""
    context_ad = get_object_or_404(ContextAd, id=context_ad_id, is_active=True)
    
    # Создаем сессию если её нет
    if not request.session.session_key:
        request.session.create()
    
    # Сохраняем клик
    AdClick.objects.create(
        context_ad=context_ad,
        user=request.user if request.user.is_authenticated else None,
        session_key=request.session.session_key or '',
        ip_address=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
        referer=request.META.get('HTTP_REFERER', ''),
        redirect_url=context_ad.target_url
    )
    
    return redirect(context_ad.target_url)


def insertion_click_redirect(request, insertion_id):
    """Редирект при клике на конкретную вставку рекламы"""
    insertion = get_object_or_404(AdInsertion, id=insertion_id, is_active=True)
    
    # Создаем сессию если её нет
    if not request.session.session_key:
        request.session.create()
    
    # Сохраняем клик
    AdClick.objects.create(
        context_ad=insertion.context_ad,
        ad_insertion=insertion,
        user=request.user if request.user.is_authenticated else None,
        session_key=request.session.session_key or '',
        ip_address=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
        referer=request.META.get('HTTP_REFERER', ''),
        redirect_url=insertion.context_ad.target_url
    )
    
    return redirect(insertion.context_ad.target_url)


# ============ AJAX ENDPOINTS ============

@csrf_exempt
@require_POST
def track_impression(request):
    """AJAX endpoint для отслеживания показов"""
    try:
        data = json.loads(request.body)
        
        ad_type = data.get('ad_type')  # 'banner' или 'context'
        ad_id = data.get('ad_id')
        viewport_position = data.get('viewport_position', 'middle')
        time_visible = data.get('time_visible', 0)
        
        impression_data = {
            'user': request.user if request.user.is_authenticated else None,
            'session_key': request.session.session_key,
            'ip_address': get_client_ip(request),
            'user_agent': request.META.get('HTTP_USER_AGENT', '')[:500],
            'viewport_position': viewport_position,
            'time_visible': time_visible,
        }
        
        if ad_type == 'banner':
            banner = AdBanner.objects.filter(id=ad_id, is_active=True).first()
            if banner:
                impression_data['ad_banner'] = banner
                AdImpression.objects.create(**impression_data)
        
        elif ad_type == 'context':
            context_ad = ContextAd.objects.filter(id=ad_id, is_active=True).first()
            if context_ad:
                impression_data['context_ad'] = context_ad
                AdImpression.objects.create(**impression_data)
        
        elif ad_type == 'insertion':
            insertion = AdInsertion.objects.filter(id=ad_id, is_active=True).first()
            if insertion:
                impression_data['context_ad'] = insertion.context_ad
                impression_data['ad_insertion'] = insertion
                AdImpression.objects.create(**impression_data)
        
        return JsonResponse({'status': 'ok'})
    
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


# ============ ДАШБОРД ============

@marketing_required
def advertising_dashboard(request):
    """Главный дашборд системы управления рекламой"""
    
    # Период для статистики (по умолчанию - последние 7 дней)
    days = int(request.GET.get('days', 7))
    date_from = timezone.now().date() - timedelta(days=days)
    
    # Общая статистика
    total_impressions = AdImpression.objects.filter(shown_at__date__gte=date_from).count()
    total_clicks = AdClick.objects.filter(clicked_at__date__gte=date_from).count()
    avg_ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0
    
    # Доход за период
    campaigns = AdCampaign.objects.all()
    total_revenue = campaigns.aggregate(total=Sum('spent_amount'))['total'] or Decimal('0.00')
    
    # Активные кампании
    active_campaigns = campaigns.filter(is_active=True).count()
    
    # Топ-5 мест по эффективности - ОПТИМИЗИРОВАНО
    top_places = AdPlace.objects.filter(
        banners__impression_records__shown_at__date__gte=date_from
    ).annotate(
        total_impressions=Count('banners__impression_records', filter=Q(banners__impression_records__shown_at__date__gte=date_from)),
        total_clicks=Count('banners__click_records', filter=Q(banners__click_records__clicked_at__date__gte=date_from))
    ).order_by('-total_clicks')[:5]
    
    # Топ-5 рекламодателей - ОПТИМИЗИРОВАНО
    top_advertisers = Advertiser.objects.filter(
        is_active=True
    ).select_related().order_by('-total_spent')[:5]
    
    # Последние клики
    recent_clicks = AdClick.objects.select_related(
        'ad_banner', 'context_ad', 'user'
    ).order_by('-clicked_at')[:10]
    
    # Рекомендации AI
    recommendations = AdRecommendation.objects.filter(
        is_applied=False
    ).order_by('-confidence_score', '-predicted_revenue')[:5]
    
    # График дохода по дням (последние N дней) - ОПТИМИЗИРОВАНО
    # Используем агрегацию вместо цикла по каждому клику
    revenue_by_day = []
    
    # Получаем все клики за период одним запросом с select_related
    clicks = AdClick.objects.filter(
        clicked_at__date__gte=date_from
    ).select_related('ad_banner__campaign', 'context_ad').only(
        'clicked_at', 'ad_banner__campaign__cost_per_click', 'context_ad__cost_per_click'
    )
    
    # Группируем по дням и считаем доход
    daily_revenue = defaultdict(Decimal)
    
    for click in clicks:
        day = click.clicked_at.date()
        if click.ad_banner and click.ad_banner.campaign:
            daily_revenue[day] += click.ad_banner.campaign.cost_per_click
        elif click.context_ad:
            daily_revenue[day] += click.context_ad.cost_per_click
    
    # Формируем массив для графика
    for i in range(days):
        day = timezone.now().date() - timedelta(days=days-i-1)
        revenue = daily_revenue.get(day, Decimal('0.00'))
        revenue_by_day.append({
            'date': day.strftime('%d.%m'),
            'revenue': float(revenue)
        })
    
    # Внешние скрипты - ОПТИМИЗИРОВАНО (кэшируем на 5 минут)
    from django.core.cache import cache as django_cache
    scripts_cache_key = 'external_scripts_stats'
    scripts_stats = django_cache.get(scripts_cache_key)
    
    if scripts_stats is None:
        total_external_scripts = ExternalScript.objects.count()
        active_external_scripts = ExternalScript.objects.filter(is_active=True).count()
        scripts_stats = {
            'total': total_external_scripts,
            'active': active_external_scripts
        }
        django_cache.set(scripts_cache_key, scripts_stats, 300)  # 5 минут
    else:
        total_external_scripts = scripts_stats['total']
        active_external_scripts = scripts_stats['active']
    
    # Ads.txt статус - ОПТИМИЗИРОВАНО (кэшируем на 2 минуты)
    ads_txt_cache_key = 'ads_txt_status'
    ads_txt_status = django_cache.get(ads_txt_cache_key)
    
    if ads_txt_status is None:
        ads_txt_settings = AdsTxtSettings.objects.first()
        ads_txt_status = {
            'exists': ads_txt_settings is not None,
            'is_active': ads_txt_settings.is_active if ads_txt_settings else False,
            'last_update': ads_txt_settings.last_successful_update if ads_txt_settings else None,
            'needs_update': ads_txt_settings.needs_update() if ads_txt_settings else False,
            'has_error': bool(ads_txt_settings.last_error if ads_txt_settings else False),
        }
        django_cache.set(ads_txt_cache_key, ads_txt_status, 120)  # 2 минуты
        ads_txt_settings = AdsTxtSettings.objects.first()  # Для контекста
    else:
        ads_txt_settings = AdsTxtSettings.objects.first()  # Для контекста
    
    context = {
        'page_title': 'Управление рекламой - IdealImage.ru',
        'page_description': 'Система управления рекламой и мониторинга кампаний',
        'total_impressions': total_impressions,
        'total_clicks': total_clicks,
        'avg_ctr': round(avg_ctr, 2),
        'total_revenue': total_revenue,
        'active_campaigns': active_campaigns,
        'top_places': top_places,
        'top_advertisers': top_advertisers,
        'recent_clicks': recent_clicks,
        'recommendations': recommendations,
        'revenue_by_day': revenue_by_day,
        'days': days,
        'total_external_scripts': total_external_scripts,
        'active_external_scripts': active_external_scripts,
        'ads_txt_settings': ads_txt_settings,
        'ads_txt_status': ads_txt_status,
    }
    
    # Используем упрощенный шаблон для лучшей видимости
    return render(request, 'advertising/dashboard_simple.html', context)


# ============ УПРАВЛЕНИЕ БАННЕРАМИ ============

@marketing_required
def banners_manage(request):
    """Управление баннерами"""
    banners = AdBanner.objects.select_related(
        'campaign', 'campaign__advertiser', 'place'
    ).order_by('-created_at')
    
    # Фильтры
    place_id = request.GET.get('place')
    campaign_id = request.GET.get('campaign')
    is_active = request.GET.get('is_active')
    
    if place_id:
        banners = banners.filter(place_id=place_id)
    if campaign_id:
        banners = banners.filter(campaign_id=campaign_id)
    if is_active:
        banners = banners.filter(is_active=(is_active == '1'))
    
    # Для фильтров
    places = AdPlace.objects.filter(is_active=True)
    campaigns = AdCampaign.objects.filter(is_active=True)
    
    context = {
        'page_title': 'Управление баннерами - IdealImage.ru',
        'page_description': 'Управление рекламными баннерами',
        'banners': banners,
        'places': places,
        'campaigns': campaigns,
    }
    
    return render(request, 'advertising/banners_manage.html', context)


@marketing_required
def banner_create(request):
    """Создание баннера"""
    from .forms import AdBannerForm
    
    if request.method == 'POST':
        form = AdBannerForm(request.POST, request.FILES)
        if form.is_valid():
            banner = form.save()
            messages.success(request, f'Баннер "{banner.name}" успешно создан')
            return redirect('advertising:banners_manage')
        else:
            messages.error(request, 'Пожалуйста, исправьте ошибки в форме')
    else:
        form = AdBannerForm()
    
    context = {
        'page_title': 'Создание баннера - IdealImage.ru',
        'page_description': 'Создание нового рекламного баннера',
        'form': form,
        'place_code': None,
    }
    
    return render(request, 'advertising/banner_form.html', context)


@marketing_required
def banner_edit(request, banner_id):
    """Редактирование баннера"""
    from .forms import AdBannerForm
    
    banner = get_object_or_404(AdBanner, id=banner_id)
    
    if request.method == 'POST':
        form = AdBannerForm(request.POST, request.FILES, instance=banner)
        if form.is_valid():
            banner = form.save()
            messages.success(request, f'Баннер "{banner.name}" успешно обновлен')
            return redirect('advertising:banners_manage')
        else:
            messages.error(request, 'Пожалуйста, исправьте ошибки в форме')
    else:
        form = AdBannerForm(instance=banner)
    
    # Получаем расписания для этого баннера
    schedules = banner.schedules.all().order_by('day_of_week', 'start_time')
    
    context = {
        'page_title': f'Редактирование баннера {banner.name} - IdealImage.ru',
        'page_description': 'Редактирование рекламного баннера',
        'form': form,
        'banner': banner,
        'place_code': banner.place.code,
        'schedules': schedules,
    }
    
    return render(request, 'advertising/banner_form.html', context)


@marketing_required
def banner_delete(request, banner_id):
    """Удаление баннера"""
    banner = get_object_or_404(AdBanner, id=banner_id)
    
    if request.method == 'POST':
        banner.delete()
        messages.success(request, 'Баннер успешно удален')
        return redirect('advertising:banners_manage')
    
    return render(request, 'advertising/banner_confirm_delete.html', {'banner': banner})


@marketing_required
@require_POST
def banner_update_preview(request, banner_id):
    """Сохранить отредактированное превью баннера или карточки"""
    import base64
    from django.core.files.base import ContentFile
    
    banner = get_object_or_404(AdBanner, id=banner_id)
    
    try:
        data = json.loads(request.body)
        image_data = data.get('image')
        card_num = data.get('card_num')  # Номер карточки (1-4) или None для основного изображения
        
        if image_data:
            # Извлекаем base64 данные
            format, imgstr = image_data.split(';base64,')
            ext = format.split('/')[-1]
            
            if card_num:
                # Сохраняем превью карточки
                filename = f'banner_{banner_id}_card{card_num}_preview.{ext}'
                image_file = ContentFile(base64.b64decode(imgstr), name=filename)
                
                # Сохраняем в соответствующее поле карточки
                setattr(banner, f'card{card_num}_image', image_file)
                setattr(banner, f'card{card_num}_type', 'image')
                banner.save()
                
                messages.success(request, f'Превью карточки {card_num} баннера "{banner.name}" успешно сохранено!')
                return JsonResponse({'success': True, 'message': f'Превью карточки {card_num} сохранено'})
            else:
                # Сохраняем основное превью (для баннеров без карточек)
                filename = f'banner_{banner_id}_preview.{ext}'
                image_file = ContentFile(base64.b64decode(imgstr), name=filename)
                
                banner.image = image_file
                banner.banner_type = 'image'
                banner.save()
                
                messages.success(request, f'Превью баннера "{banner.name}" успешно сохранено!')
                return JsonResponse({'success': True, 'message': 'Превью сохранено'})
        
        return JsonResponse({'success': False, 'error': 'Нет данных изображения'})
    
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


# ============ УПРАВЛЕНИЕ КОНТЕКСТНОЙ РЕКЛАМОЙ ============

@marketing_required
def context_ads_manage(request):
    """Управление контекстной рекламой"""
    context_ads = ContextAd.objects.select_related('campaign', 'campaign__advertiser').order_by('-created_at')
    
    # Вставки рекламы
    insertions = AdInsertion.objects.select_related(
        'context_ad', 'post', 'post__author'
    ).filter(is_active=True).order_by('-inserted_at')[:50]
    
    context = {
        'page_title': 'Контекстная реклама - IdealImage.ru',
        'page_description': 'Управление контекстной рекламой в статьях',
        'context_ads': context_ads,
        'insertions': insertions,
    }
    
    return render(request, 'advertising/context_ads_manage.html', context)


@marketing_required
def context_ad_create(request):
    """Создание контекстной рекламы"""
    from .forms import ContextAdForm
    
    if request.method == 'POST':
        form = ContextAdForm(request.POST)
        if form.is_valid():
            context_ad = form.save()
            messages.success(request, f'Контекстная реклама "{context_ad.anchor_text}" создана')
            return redirect('advertising:context_ads_manage')
        else:
            messages.error(request, 'Пожалуйста, исправьте ошибки в форме')
    else:
        form = ContextAdForm()
    
    context = {
        'page_title': 'Создание контекстной рекламы - IdealImage.ru',
        'page_description': 'Создание нового контекстного объявления',
        'form': form,
    }
    
    return render(request, 'advertising/context_ad_form.html', context)


@marketing_required
def context_ad_edit(request, ad_id):
    """Редактирование контекстной рекламы"""
    from .forms import ContextAdForm
    
    context_ad = get_object_or_404(ContextAd, id=ad_id)
    
    if request.method == 'POST':
        form = ContextAdForm(request.POST, instance=context_ad)
        if form.is_valid():
            context_ad = form.save()
            messages.success(request, f'Контекстная реклама "{context_ad.anchor_text}" обновлена')
            return redirect('advertising:context_ads_manage')
        else:
            messages.error(request, 'Пожалуйста, исправьте ошибки в форме')
    else:
        form = ContextAdForm(instance=context_ad)
    
    context = {
        'page_title': f'Редактирование рекламы {context_ad.anchor_text} - IdealImage.ru',
        'page_description': 'Редактирование контекстной рекламы',
        'form': form,
        'context_ad': context_ad,
    }
    
    return render(request, 'advertising/context_ad_form.html', context)


@marketing_required
def context_ad_delete(request, ad_id):
    """Удаление контекстной рекламы"""
    context_ad = get_object_or_404(ContextAd, id=ad_id)
    
    if request.method == 'POST':
        context_ad.delete()
        messages.success(request, 'Контекстная реклама удалена')
        return redirect('advertising:context_ads_manage')
    
    return render(request, 'advertising/context_ad_confirm_delete.html', {'context_ad': context_ad})


# ============ УПРАВЛЕНИЕ КАМПАНИЯМИ ============

@marketing_required
def campaigns_list(request):
    """Список кампаний"""
    campaigns = AdCampaign.objects.select_related('advertiser').order_by('-created_at')
    
    context = {
        'page_title': 'Рекламные кампании - IdealImage.ru',
        'page_description': 'Управление рекламными кампаниями',
        'campaigns': campaigns,
    }
    
    return render(request, 'advertising/campaigns_list.html', context)


@marketing_required
def campaign_create(request):
    """Создание кампании"""
    from .forms import AdCampaignForm
    
    if request.method == 'POST':
        form = AdCampaignForm(request.POST)
        if form.is_valid():
            campaign = form.save(commit=False)
            campaign.created_by = request.user
            campaign.save()
            messages.success(request, f'Кампания "{campaign.name}" создана')
            return redirect('advertising:campaigns_list')
        else:
            messages.error(request, 'Пожалуйста, исправьте ошибки в форме')
    else:
        form = AdCampaignForm()
    
    context = {
        'page_title': 'Создание кампании - IdealImage.ru',
        'page_description': 'Создание новой рекламной кампании',
        'form': form,
    }
    
    return render(request, 'advertising/campaign_form.html', context)


@marketing_required
def campaign_detail(request, campaign_id):
    """Детальная информация о кампании"""
    campaign = get_object_or_404(AdCampaign, id=campaign_id)
    
    # Статистика кампании
    banners = campaign.banners.all()
    total_impressions = sum(b.impressions for b in banners)
    total_clicks = sum(b.clicks for b in banners)
    avg_ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0
    
    context = {
        'page_title': f'Кампания {campaign.name} - IdealImage.ru',
        'page_description': f'Детали рекламной кампании {campaign.name}',
        'campaign': campaign,
        'banners': banners,
        'total_impressions': total_impressions,
        'total_clicks': total_clicks,
        'avg_ctr': round(avg_ctr, 2),
    }
    
    return render(request, 'advertising/campaign_detail.html', context)


@marketing_required
def campaign_edit(request, campaign_id):
    """Редактирование кампании"""
    from .forms import AdCampaignForm
    
    campaign = get_object_or_404(AdCampaign, id=campaign_id)
    
    if request.method == 'POST':
        form = AdCampaignForm(request.POST, instance=campaign)
        if form.is_valid():
            campaign = form.save()
            messages.success(request, f'Кампания "{campaign.name}" обновлена')
            return redirect('advertising:campaign_detail', campaign_id=campaign.id)
        else:
            messages.error(request, 'Пожалуйста, исправьте ошибки в форме')
    else:
        form = AdCampaignForm(instance=campaign)
    
    context = {
        'page_title': f'Редактирование {campaign.name} - IdealImage.ru',
        'page_description': 'Редактирование рекламной кампании',
        'form': form,
        'campaign': campaign,
    }
    
    return render(request, 'advertising/campaign_form.html', context)


# ============ УПРАВЛЕНИЕ РЕКЛАМОДАТЕЛЯМИ ============

@marketing_required
def advertisers_list(request):
    """Список рекламодателей"""
    advertisers = Advertiser.objects.order_by('-created_at')
    
    context = {
        'page_title': 'Рекламодатели - IdealImage.ru',
        'page_description': 'Управление рекламодателями',
        'advertisers': advertisers,
    }
    
    return render(request, 'advertising/advertisers_list.html', context)


@marketing_required
def advertiser_create(request):
    """Создание рекламодателя"""
    from .forms import AdvertiserForm
    
    if request.method == 'POST':
        form = AdvertiserForm(request.POST)
        if form.is_valid():
            advertiser = form.save()
            messages.success(request, f'Рекламодатель "{advertiser.name}" создан')
            return redirect('advertising:advertisers_list')
        else:
            messages.error(request, 'Пожалуйста, исправьте ошибки в форме')
    else:
        form = AdvertiserForm()
    
    context = {
        'page_title': 'Создание рекламодателя - IdealImage.ru',
        'page_description': 'Добавление нового рекламодателя',
        'form': form,
    }
    return render(request, 'advertising/advertiser_form.html', context)


@marketing_required
def advertiser_detail(request, advertiser_id):
    """Детальная информация о рекламодателе"""
    advertiser = get_object_or_404(Advertiser, id=advertiser_id)
    
    campaigns = advertiser.campaigns.all()
    
    context = {
        'page_title': f'{advertiser.name} - IdealImage.ru',
        'page_description': f'Информация о рекламодателе {advertiser.name}',
        'advertiser': advertiser,
        'campaigns': campaigns,
    }
    
    return render(request, 'advertising/advertiser_detail.html', context)


# ============ АНАЛИТИКА ============

@marketing_required
def analytics_dashboard(request):
    """Дашборд аналитики"""
    
    # Период
    days = int(request.GET.get('days', 30))
    date_from = timezone.now().date() - timedelta(days=days)
    
    # Статистика по рекламодателям
    advertisers_stats = []
    for advertiser in Advertiser.objects.filter(is_active=True):
        campaigns = advertiser.campaigns.filter(
            created_at__date__gte=date_from
        )
        
        total_impressions = AdImpression.objects.filter(
            ad_banner__campaign__in=campaigns,
            shown_at__date__gte=date_from
        ).count()
        
        total_clicks = AdClick.objects.filter(
            ad_banner__campaign__in=campaigns,
            clicked_at__date__gte=date_from
        ).count()
        
        advertisers_stats.append({
            'advertiser': advertiser,
            'total_spent': advertiser.total_spent,
            'impressions': total_impressions,
            'clicks': total_clicks,
            'ctr': (total_clicks / total_impressions * 100) if total_impressions > 0 else 0
        })
    
    context = {
        'page_title': 'Аналитика рекламы - IdealImage.ru',
        'page_description': 'Детальная аналитика рекламных кампаний',
        'advertisers_stats': advertisers_stats,
        'days': days,
    }
    
    return render(request, 'advertising/analytics.html', context)


@marketing_required
def analytics_export(request):
    """Экспорт аналитики в CSV"""
    import csv
    from django.http import StreamingHttpResponse
    
    # TODO: Реализовать экспорт
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="advertising_analytics.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Дата', 'Показы', 'Клики', 'CTR', 'Доход'])
    
    # TODO: Добавить данные
    
    return response


# ============ AI РЕКОМЕНДАЦИИ ============

@marketing_required
def ai_recommendations(request):
    """Рекомендации AI"""
    recommendations = AdRecommendation.objects.select_related(
        'campaign', 'place', 'post'
    ).order_by('-confidence_score', '-predicted_revenue')
    
    # Фильтр по статусу
    status = request.GET.get('status')
    if status == 'active':
        recommendations = recommendations.filter(is_applied=False)
    elif status == 'applied':
        recommendations = recommendations.filter(is_applied=True)
    
    context = {
        'page_title': 'Рекомендации AI - IdealImage.ru',
        'page_description': 'AI рекомендации по оптимизации рекламы',
        'recommendations': recommendations,
    }
    
    return render(request, 'advertising/ai_recommendations.html', context)


@marketing_required
@require_POST
def apply_recommendation(request, rec_id):
    """Применить рекомендацию AI"""
    recommendation = get_object_or_404(AdRecommendation, id=rec_id)
    
    if not recommendation.is_applied:
        recommendation.apply_recommendation()
        messages.success(request, f'Рекомендация применена: {recommendation.recommendation_reason}')
    else:
        messages.warning(request, 'Рекомендация уже была применена ранее')
    
    return redirect('advertising:recommendations')


# ============ ЖУРНАЛ ДЕЙСТВИЙ ============

@marketing_required
def action_log_view(request):
    """Страница журнала действий с рекламой"""
    from .models import AdActionLog
    
    # Получаем все записи
    logs = AdActionLog.objects.select_related('performed_by', 'reverted_by').order_by('-timestamp')
    
    # Фильтры
    action_type = request.GET.get('action_type')
    target_type = request.GET.get('target_type')
    performed_by_ai = request.GET.get('performed_by_ai')
    reverted = request.GET.get('reverted')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    if action_type:
        logs = logs.filter(action_type=action_type)
    if target_type:
        logs = logs.filter(target_type=target_type)
    if performed_by_ai == '1':
        logs = logs.filter(performed_by_ai=True)
    elif performed_by_ai == '0':
        logs = logs.filter(performed_by_ai=False)
    if reverted == '1':
        logs = logs.filter(reverted=True)
    elif reverted == '0':
        logs = logs.filter(reverted=False)
    if date_from:
        logs = logs.filter(timestamp__date__gte=date_from)
    if date_to:
        logs = logs.filter(timestamp__date__lte=date_to)
    
    # Пагинация
    from django.core.paginator import Paginator
    paginator = Paginator(logs, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Статистика
    total_actions = AdActionLog.objects.count()
    ai_actions = AdActionLog.objects.filter(performed_by_ai=True).count()
    reverted_actions = AdActionLog.objects.filter(reverted=True).count()
    
    context = {
        'page_title': 'Журнал действий - Реклама IdealImage.ru',
        'page_description': 'Журнал всех действий с рекламой',
        'logs': page_obj,
        'total_actions': total_actions,
        'ai_actions': ai_actions,
        'reverted_actions': reverted_actions,
        'action_types': AdActionLog.ACTION_TYPES,
        # Текущие фильтры
        'current_action_type': action_type,
        'current_target_type': target_type,
        'current_performed_by_ai': performed_by_ai,
        'current_reverted': reverted,
        'current_date_from': date_from,
        'current_date_to': date_to,
    }
    
    return render(request, 'advertising/action_log.html', context)


@marketing_required
@require_POST
def revert_action(request, log_id):
    """Отменить действие"""
    from .models import AdActionLog, AdBanner, AdInsertion, ExternalScript
    
    log = get_object_or_404(AdActionLog, id=log_id)
    
    if not log.can_be_reverted():
        messages.error(request, 'Это действие не может быть отменено')
        return redirect('advertising:action_log')
    
    # Пытаемся отменить в зависимости от типа
    try:
        if log.action_type == 'activate' and log.target_type == 'banner':
            # Отменяем активацию = деактивируем
            banner = AdBanner.objects.get(id=log.target_id)
            banner.is_active = False
            banner.save(update_fields=['is_active'])
            
        elif log.action_type == 'deactivate' and log.target_type == 'banner':
            # Отменяем деактивацию = активируем
            banner = AdBanner.objects.get(id=log.target_id)
            banner.is_active = True
            banner.save(update_fields=['is_active'])
            
        elif log.action_type == 'insert' and log.target_type == 'insertion':
            # Отменяем вставку = удаляем
            insertion = AdInsertion.objects.get(id=log.target_id)
            insertion.is_active = False
            insertion.removed_at = timezone.now()
            insertion.removal_reason = f'Отменено действие #{log.id}'
            insertion.save(update_fields=['is_active', 'removed_at', 'removal_reason'])
        
        elif log.action_type == 'activate' and log.target_type == 'external_script':
            # Отменяем активацию внешнего скрипта = деактивируем
            script = ExternalScript.objects.get(id=log.target_id)
            script.is_active = False
            script.save(update_fields=['is_active'])
            
        elif log.action_type == 'deactivate' and log.target_type == 'external_script':
            # Отменяем деактивацию внешнего скрипта = активируем
            script = ExternalScript.objects.get(id=log.target_id)
            script.is_active = True
            script.save(update_fields=['is_active'])
        
        # Помечаем действие как отменённое
        success, message = log.revert(user=request.user)
        
        if success:
            messages.success(request, f'Действие отменено: {log.description}')
        else:
            messages.error(request, message)
            
    except Exception as e:
        messages.error(request, f'Ошибка при отмене действия: {str(e)}')
    
    return redirect('advertising:action_log')


@marketing_required
@require_POST
def replay_action(request, log_id):
    """Повторить действие"""
    from .models import AdActionLog, AdBanner, ExternalScript
    
    log = get_object_or_404(AdActionLog, id=log_id)
    
    # Повторяем действие в зависимости от типа
    try:
        if log.action_type == 'activate' and log.target_type == 'banner':
            banner = AdBanner.objects.get(id=log.target_id)
            banner.is_active = True
            banner.save(update_fields=['is_active'])
            messages.success(request, f'Баннер "{banner.name}" активирован')
            
        elif log.action_type == 'deactivate' and log.target_type == 'banner':
            banner = AdBanner.objects.get(id=log.target_id)
            banner.is_active = False
            banner.save(update_fields=['is_active'])
            messages.success(request, f'Баннер "{banner.name}" деактивирован')
        
        elif log.action_type == 'activate' and log.target_type == 'external_script':
            script = ExternalScript.objects.get(id=log.target_id)
            script.is_active = True
            script.save(update_fields=['is_active'])
            messages.success(request, f'Скрипт "{script.name}" активирован')
            
        elif log.action_type == 'deactivate' and log.target_type == 'external_script':
            script = ExternalScript.objects.get(id=log.target_id)
            script.is_active = False
            script.save(update_fields=['is_active'])
            messages.success(request, f'Скрипт "{script.name}" деактивирован')
        
        else:
            messages.warning(request, 'Повтор этого типа действия пока не поддерживается')
            
    except Exception as e:
        messages.error(request, f'Ошибка при повторе действия: {str(e)}')
    
    return redirect('advertising:action_log')


# ============ УПРАВЛЕНИЕ ВНЕШНИМИ СКРИПТАМИ ============

@marketing_required
def external_scripts_list(request):
    """Список внешних скриптов с возможностью управления"""
    
    # Получаем все скрипты
    scripts = ExternalScript.objects.select_related('created_by').order_by('position', 'priority', '-created_at')
    
    # Фильтры
    script_type = request.GET.get('script_type')
    position = request.GET.get('position')
    is_active = request.GET.get('is_active')
    
    if script_type:
        scripts = scripts.filter(script_type=script_type)
    if position:
        scripts = scripts.filter(position=position)
    if is_active:
        scripts = scripts.filter(is_active=(is_active == '1'))
    
    # Статистика
    total_scripts = ExternalScript.objects.count()
    active_scripts = ExternalScript.objects.filter(is_active=True).count()
    
    # По типам
    scripts_by_type = {}
    for choice in ExternalScript.SCRIPT_TYPES:
        count = ExternalScript.objects.filter(script_type=choice[0]).count()
        scripts_by_type[choice[1]] = count
    
    # По позициям
    scripts_by_position = {}
    for choice in ExternalScript.SCRIPT_POSITIONS:
        count = ExternalScript.objects.filter(position=choice[0]).count()
        scripts_by_position[choice[1]] = count
    
    context = {
        'page_title': 'Внешние скрипты - IdealImage.ru',
        'page_description': 'Управление внешними скриптами и счетчиками',
        'scripts': scripts,
        'total_scripts': total_scripts,
        'active_scripts': active_scripts,
        'scripts_by_type': scripts_by_type,
        'scripts_by_position': scripts_by_position,
        'script_types': ExternalScript.SCRIPT_TYPES,
        'positions': ExternalScript.SCRIPT_POSITIONS,
        # Текущие фильтры
        'current_script_type': script_type,
        'current_position': position,
        'current_is_active': is_active,
    }
    
    return render(request, 'advertising/external_scripts_list.html', context)


@marketing_required
def external_script_detail(request, script_id):
    """Детальная страница внешнего скрипта"""
    script = get_object_or_404(ExternalScript, id=script_id)
    
    context = {
        'page_title': f'{script.name} - Внешние скрипты',
        'page_description': 'Просмотр и редактирование внешнего скрипта',
        'script': script,
    }
    
    return render(request, 'advertising/external_script_detail.html', context)


@marketing_required
def external_script_create(request):
    """Создание нового внешнего скрипта"""
    
    if request.method == 'POST':
        try:
            from .action_logger import AdActionLogger
            
            script = ExternalScript.objects.create(
                name=request.POST.get('name'),
                script_type=request.POST.get('script_type', 'other'),
                provider=request.POST.get('provider', ''),
                code=request.POST.get('code'),
                position=request.POST.get('position', 'head_end'),
                priority=int(request.POST.get('priority', 10)),
                is_active=request.POST.get('is_active') == 'on',
                description=request.POST.get('description', ''),
                created_by=request.user
            )
            
            # Логируем создание
            AdActionLogger.log_external_script_create(
                script=script,
                performed_by=request.user,
                performed_by_ai=False
            )
            
            messages.success(request, f'Скрипт "{script.name}" успешно создан!')
            return redirect('advertising:external_script_detail', script_id=script.id)
            
        except Exception as e:
            messages.error(request, f'Ошибка при создании скрипта: {str(e)}')
    
    context = {
        'page_title': 'Добавить внешний скрипт - IdealImage.ru',
        'page_description': 'Создание нового внешнего скрипта',
        'script_types': ExternalScript.SCRIPT_TYPES,
        'positions': ExternalScript.SCRIPT_POSITIONS,
    }
    
    return render(request, 'advertising/external_script_form.html', context)


@marketing_required
def external_script_edit(request, script_id):
    """Редактирование внешнего скрипта"""
    script = get_object_or_404(ExternalScript, id=script_id)
    
    if request.method == 'POST':
        try:
            from .action_logger import AdActionLogger
            
            # Сохраняем старые значения для логирования
            old_values = {
                'name': script.name,
                'script_type': script.script_type,
                'provider': script.provider,
                'position': script.position,
                'priority': script.priority,
                'is_active': script.is_active,
            }
            
            script.name = request.POST.get('name')
            script.script_type = request.POST.get('script_type', 'other')
            script.provider = request.POST.get('provider', '')
            script.code = request.POST.get('code')
            script.position = request.POST.get('position', 'head_end')
            script.priority = int(request.POST.get('priority', 10))
            script.is_active = request.POST.get('is_active') == 'on'
            script.description = request.POST.get('description', '')
            script.save()
            
            # Логируем изменение
            AdActionLogger.log_external_script_update(
                script=script,
                old_values=old_values,
                performed_by=request.user,
                performed_by_ai=False
            )
            
            messages.success(request, f'Скрипт "{script.name}" успешно обновлён!')
            return redirect('advertising:external_script_detail', script_id=script.id)
            
        except Exception as e:
            messages.error(request, f'Ошибка при обновлении скрипта: {str(e)}')
    
    context = {
        'page_title': f'Редактировать {script.name} - IdealImage.ru',
        'page_description': 'Редактирование внешнего скрипта',
        'script': script,
        'script_types': ExternalScript.SCRIPT_TYPES,
        'positions': ExternalScript.SCRIPT_POSITIONS,
        'is_edit': True,
    }
    
    return render(request, 'advertising/external_script_form.html', context)


@marketing_required
@require_POST
def external_script_delete(request, script_id):
    """Удаление внешнего скрипта"""
    script = get_object_or_404(ExternalScript, id=script_id)
    script_name = script.name
    script_type_display = script.get_script_type_display()
    
    try:
        from .action_logger import AdActionLogger
        
        # Логируем удаление (перед удалением!)
        AdActionLogger.log_external_script_delete(
            script_id=script.id,
            script_name=script_name,
            script_type=script_type_display,
            performed_by=request.user,
            performed_by_ai=False
        )
        
        script.delete()
        messages.success(request, f'Скрипт "{script_name}" успешно удалён!')
    except Exception as e:
        messages.error(request, f'Ошибка при удалении скрипта: {str(e)}')
    
    return redirect('advertising:external_scripts_list')


@marketing_required
@require_POST
def external_script_toggle(request, script_id):
    """Переключение активности скрипта"""
    script = get_object_or_404(ExternalScript, id=script_id)
    
    from .action_logger import AdActionLogger
    
    # Логируем действие
    if script.is_active:
        # Будет деактивирован
        script.is_active = False
        script.save(update_fields=['is_active'])
        AdActionLogger.log_external_script_deactivate(
            script=script,
            performed_by=request.user,
            performed_by_ai=False
        )
        status = "деактивирован"
    else:
        # Будет активирован
        script.is_active = True
        script.save(update_fields=['is_active'])
        AdActionLogger.log_external_script_activate(
            script=script,
            performed_by=request.user,
            performed_by_ai=False
        )
        status = "активирован"
    
    messages.success(request, f'Скрипт "{script.name}" {status}!')
    
    # Возвращаем на предыдущую страницу
    return redirect(request.META.get('HTTP_REFERER', 'advertising:external_scripts_list'))


# ============ ADS.TXT ============

@require_GET
def ads_txt_view(request):
    """View для отдачи файла ads.txt"""
    from django.core.cache import cache
    
    # Кэшируем настройки на 5 минут
    cache_key_settings = 'ads_txt_settings_obj'
    settings_obj = cache.get(cache_key_settings)
    
    if settings_obj is None:
        # Получаем настройки (singleton)
        settings_obj = AdsTxtSettings.objects.first()
        
        if not settings_obj:
            # Создаём дефолтные настройки
            settings_obj = AdsTxtSettings.objects.create(
                domain='idealimage.ru',
                ezoic_manager_url='https://srv.adstxtmanager.com/19390/idealimage.ru'
            )
        
        # Кэшируем на 5 минут
        cache.set(cache_key_settings, settings_obj, 300)
    
    # Если неактивен - возвращаем пустой файл
    if not settings_obj.is_active:
        return HttpResponse('', content_type='text/plain; charset=utf-8')
    
    # Кэшируем содержимое файла на 10 минут
    cache_key_content = f'ads_txt_content_{settings_obj.id}'
    content = cache.get(cache_key_content)
    
    if content is None:
        # Получаем содержимое
        content = settings_obj.get_content()
        # Кэшируем на 10 минут
        cache.set(cache_key_content, content, 600)
    
    # Проверяем, нужно ли обновление (в фоне, не блокируя ответ)
    if settings_obj.needs_update() and settings_obj.auto_update:
        # Запускаем обновление в фоне (не блокируем ответ)
        cache_key_updating = f'ads_txt_updating_{settings_obj.id}'
        if not cache.get(cache_key_updating):
            cache.set(cache_key_updating, True, 300)  # Блокируем на 5 минут
            try:
                settings_obj.update_from_ezoic()
                # Инвалидируем кэш содержимого после обновления
                cache.delete(cache_key_content)
            except:
                pass  # Игнорируем ошибки при фоновом обновлении
            finally:
                cache.delete(cache_key_updating)
    
    # Формируем ответ
    response = HttpResponse(content, content_type='text/plain; charset=utf-8')
    
    # Кэширование на 1 час (ads.txt не меняется часто)
    response['Cache-Control'] = 'public, max-age=3600'
    response['X-Content-Type-Options'] = 'nosniff'
    
    return response


# ============ УПРАВЛЕНИЕ ADS.TXT ============

@marketing_required
@ensure_csrf_cookie
def ads_txt_manage(request):
    """Страница управления ads.txt"""
    settings_obj = AdsTxtSettings.objects.first()
    
    if not settings_obj:
        # Создаём дефолтные настройки
        settings_obj = AdsTxtSettings.objects.create(
            domain='idealimage.ru',
            ezoic_manager_url='https://srv.adstxtmanager.com/19390/idealimage.ru'
        )
    
    context = {
        'page_title': 'Управление ads.txt - IdealImage.ru',
        'page_description': 'Настройка файла ads.txt для Ezoic',
        'settings': settings_obj,
        'needs_update': settings_obj.needs_update(),
    }
    
    return render(request, 'advertising/ads_txt_manage.html', context)


@marketing_required
@require_POST
def ads_txt_update(request):
    """Обновить ads.txt вручную"""
    settings_obj = AdsTxtSettings.objects.first()
    
    if not settings_obj:
        messages.error(request, 'Настройки ads.txt не найдены')
        return redirect('advertising:dashboard')
    
    success, message = settings_obj.update_from_ezoic()
    
    if success:
        messages.success(request, f'✅ {message}')
    else:
        messages.error(request, f'❌ {message}')
    
    return redirect('advertising:ads_txt_manage')


# ============ API ДЛЯ ПОЛУЧЕНИЯ ДАННЫХ БАННЕРА ============

@require_GET
def banner_detail_api(request, banner_id):
    """API: Получить полные данные баннера для редактора"""
    try:
        banner = AdBanner.objects.select_related('place', 'campaign').get(id=banner_id)
        
        # Собираем данные карточек
        cards_data = {}
        for i in range(1, 5):
            card_type = getattr(banner, f'card{i}_type', None)
            card_image = getattr(banner, f'card{i}_image', None)
            card_video = getattr(banner, f'card{i}_video', None)
            
            cards_data[f'card{i}'] = {
                'type': card_type,
                'image_url': card_image.url if card_image else None,
                'video_url': card_video.url if card_video else None,
                'title': getattr(banner, f'card{i}_title', ''),
                'text': getattr(banner, f'card{i}_text', ''),
                'icon': getattr(banner, f'card{i}_icon', ''),
            }
        
        return JsonResponse({
            'success': True,
            'banner': {
                'id': banner.id,
                'name': banner.name,
                'place_code': banner.place.code,
                'banner_type': banner.banner_type,
                'image_url': banner.image.url if banner.image else None,
                'video_url': banner.video.url if banner.video else None,
                **cards_data
            }
        })
    except AdBanner.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Баннер не найден'
        }, status=404)


# ============ API ДЛЯ УПРАВЛЕНИЯ POPUP ============

@require_GET
def popup_status_api(request):
    """API: Получить текущий статус popup"""
    try:
        place = AdPlace.objects.get(code='popup_modal')
        
        return JsonResponse({
            'success': True,
            'test_mode': place.popup_test_mode,
            'test_interval': place.popup_test_interval_seconds,
            'delay': place.popup_delay_seconds,
            'cookie_hours': place.popup_cookie_hours,
        })
    except AdPlace.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Рекламное место popup_modal не найдено'
        }, status=404)


@marketing_required
@require_POST
def popup_toggle_test_api(request):
    """API: Переключить тестовый режим popup"""
    try:
        place = AdPlace.objects.get(code='popup_modal')
        
        # Переключаем режим
        place.popup_test_mode = not place.popup_test_mode
        place.save(update_fields=['popup_test_mode'])
        
        return JsonResponse({
            'success': True,
            'test_mode': place.popup_test_mode,
            'test_interval': place.popup_test_interval_seconds,
            'delay': place.popup_delay_seconds,
            'cookie_hours': place.popup_cookie_hours,
        })
    except AdPlace.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Рекламное место popup_modal не найдено'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


# ============ API ДЛЯ УПРАВЛЕНИЯ РАСПИСАНИЕМ ============

@require_GET
def schedule_detail_api(request, schedule_id):
    """API: Получить данные расписания"""
    try:
        schedule = AdSchedule.objects.get(id=schedule_id)
        
        return JsonResponse({
            'success': True,
            'id': schedule.id,
            'day_of_week': schedule.day_of_week,
            'start_time': schedule.start_time.strftime('%H:%M'),
            'end_time': schedule.end_time.strftime('%H:%M'),
            'max_impressions_per_day': schedule.max_impressions_per_day,
            'is_active': schedule.is_active,
            'current_impressions': schedule.current_impressions,
        })
    except AdSchedule.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Расписание не найдено'
        }, status=404)


@marketing_required
@require_POST
def schedule_create_api(request):
    """API: Создать новое расписание"""
    try:
        data = json.loads(request.body)
        banner_id = data.get('banner_id')
        
        banner = AdBanner.objects.get(id=banner_id)
        
        schedule = AdSchedule.objects.create(
            banner=banner,
            day_of_week=int(data['day_of_week']) if data.get('day_of_week') else None,
            start_time=data['start_time'],
            end_time=data['end_time'],
            max_impressions_per_day=int(data['max_impressions_per_day']) if data.get('max_impressions_per_day') else None,
            is_active=data.get('is_active', True)
        )
        
        return JsonResponse({
            'success': True,
            'schedule_id': schedule.id,
            'message': 'Расписание создано успешно'
        })
    except AdBanner.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Баннер не найден'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@marketing_required
@require_POST
def schedule_update_api(request, schedule_id):
    """API: Обновить расписание"""
    try:
        data = json.loads(request.body)
        schedule = AdSchedule.objects.get(id=schedule_id)
        
        schedule.day_of_week = int(data['day_of_week']) if data.get('day_of_week') else None
        schedule.start_time = data['start_time']
        schedule.end_time = data['end_time']
        schedule.max_impressions_per_day = int(data['max_impressions_per_day']) if data.get('max_impressions_per_day') else None
        schedule.is_active = data.get('is_active', True)
        schedule.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Расписание обновлено'
        })
    except AdSchedule.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Расписание не найдено'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@marketing_required
@require_POST
def schedule_toggle_api(request, schedule_id):
    """API: Включить/выключить расписание"""
    try:
        data = json.loads(request.body)
        schedule = AdSchedule.objects.get(id=schedule_id)
        
        schedule.is_active = data.get('is_active', not schedule.is_active)
        schedule.save(update_fields=['is_active'])
        
        return JsonResponse({
            'success': True,
            'is_active': schedule.is_active
        })
    except AdSchedule.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Расписание не найдено'
        }, status=404)


@marketing_required
@require_POST
def schedule_delete_api(request, schedule_id):
    """API: Удалить расписание"""
    try:
        schedule = AdSchedule.objects.get(id=schedule_id)
        schedule.delete()
        
        return JsonResponse({
            'success': True,
            'message': 'Расписание удалено'
        })
    except AdSchedule.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Расписание не найдено'
        }, status=404)