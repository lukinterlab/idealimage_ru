"""
Template tags для отображения рекламы на сайте
"""
from django import template
from django.utils.safestring import mark_safe
from django.utils import timezone
from django.urls import reverse
from django.core.cache import cache
from urllib.parse import quote
import random
import json

from ..models import AdPlace, AdBanner, ContextAd

register = template.Library()


@register.simple_tag
def show_ad(place_code):
    """
    Показать баннер в указанном месте
    Использование: {% show_ad 'header_banner' %}
    """
    # Пробуем получить из кэша
    cache_key = f'ad_place_{place_code}'
    html = cache.get(cache_key)
    
    if html is not None:
        return mark_safe(html)
    
    try:
        place = AdPlace.objects.get(code=place_code, is_active=True)
    except AdPlace.DoesNotExist:
        return ''
    
    # Получаем активные баннеры для этого места
    banners = AdBanner.objects.filter(
        place=place,
        is_active=True,
        campaign__is_active=True
    ).select_related('campaign')
    
    # Фильтруем по датам кампании
    today = timezone.now().date()
    active_banners = [
        b for b in banners
        if b.campaign.start_date <= today <= b.campaign.end_date
    ]
    
    if not active_banners:
        return ''
    
    # Разделяем баннеры на безлимитные и с расписанием
    unlimited_banners = [b for b in active_banners if b.unlimited_impressions]
    scheduled_banners = [b for b in active_banners if not b.unlimited_impressions]
    
    # Безлимитные баннеры добавляем сразу
    valid_banners = list(unlimited_banners)
    
    # Для баннеров с выключенным безлимитным режимом проверяем расписание
    for banner in scheduled_banners:
        schedules = banner.schedules.filter(is_active=True)
        
        if not schedules.exists():
            # Нет расписания - показываем всегда (по умолчанию безлимитно)
            valid_banners.append(banner)
        else:
            # Есть расписание - проверяем
            for schedule in schedules:
                if schedule.can_show():
                    valid_banners.append(banner)
                    break
    
    if not valid_banners:
        return ''
    
    # Выбираем баннер по весу (для A/B тестирования)
    total_weight = sum(b.weight for b in valid_banners)
    random_weight = random.randint(1, total_weight)
    
    current_weight = 0
    selected_banner = valid_banners[0]
    
    for banner in valid_banners:
        current_weight += banner.weight
        if random_weight <= current_weight:
            selected_banner = banner
            break
    
    # Генерируем HTML
    html = render_banner_html(selected_banner, place)
    
    # Кэшируем на 5 минут
    cache.set(cache_key, html, 300)
    
    return mark_safe(html)


@register.simple_tag
def show_ad_in_post(place_code, post_id):
    """
    Показать баннер внутри статьи
    Использование: {% show_ad_in_post 'in_post_middle' post.id %}
    """
    return show_ad(place_code)


@register.simple_tag
def show_popup_ad():
    """
    Показать всплывающий баннер с настраиваемыми параметрами
    
    Режимы работы:
    1. Тестовый режим (popup_test_mode=True):
       - Popup всплывает каждые N секунд (popup_test_interval_seconds)
       - Cookie не используется
       - Для тестирования и отладки
    
    2. Стандартный режим (popup_test_mode=False):
       - Проверка cookie
       - Первое всплывание через popup_delay_seconds
       - После закрытия cookie на popup_cookie_hours
    
    Использование: {% show_popup_ad %}
    """
    try:
        place = AdPlace.objects.get(code='popup_modal', is_active=True)
    except AdPlace.DoesNotExist:
        return ''
    
    banners = AdBanner.objects.filter(
        place=place,
        is_active=True,
        campaign__is_active=True
    ).select_related('campaign')
    
    if not banners.exists():
        return ''
    
    # Выбираем случайный баннер
    banner = random.choice(list(banners))
    
    # Получаем настройки из модели
    test_mode = place.popup_test_mode
    test_interval_seconds = place.popup_test_interval_seconds
    delay_seconds = place.popup_delay_seconds
    cookie_hours = place.popup_cookie_hours
    
    # Конвертируем в нужные единицы
    delay_ms = delay_seconds * 1000  # секунды → миллисекунды
    test_interval_ms = test_interval_seconds * 1000
    cookie_max_age = cookie_hours * 3600  # часы → секунды
    
    # Генерируем JavaScript в зависимости от режима
    if test_mode:
        # ТЕСТОВЫЙ РЕЖИМ: всплывает каждые N секунд
        js_code = f'''
    function closeAdPopup() {{
        document.getElementById('adPopup').style.display = 'none';
    }}
    
    // 🧪 ТЕСТОВЫЙ РЕЖИМ: popup всплывает каждые {test_interval_seconds} секунд
    function showPopupTest() {{
        document.getElementById('adPopup').style.display = 'flex';
    }}
    
    // Первое показ через {delay_seconds} сек
    setTimeout(showPopupTest, {delay_ms});
    
    // Затем показываем каждые {test_interval_seconds} сек
    setInterval(showPopupTest, {test_interval_ms});
    
    console.log('🧪 Popup в тестовом режиме: интервал {test_interval_seconds} сек');
    '''
    else:
        # СТАНДАРТНЫЙ РЕЖИМ: с cookie
        js_code = f'''
    function closeAdPopup() {{
        document.getElementById('adPopup').style.display = 'none';
        // Сохраняем в cookie чтобы не показывать {cookie_hours} часов
        document.cookie = "ad_popup_closed=1; max-age={cookie_max_age}; path=/";
        console.log('✅ Popup закрыт. Cookie установлен на {cookie_hours} часов');
    }}
    
    // ⏱️ СТАНДАРТНЫЙ РЕЖИМ: показываем через {delay_seconds} сек если cookie нет
    setTimeout(function() {{
        if (!document.cookie.includes('ad_popup_closed=1')) {{
            document.getElementById('adPopup').style.display = 'flex';
            console.log('✅ Popup показан (cookie отсутствует)');
        }} else {{
            console.log('⏭️ Popup пропущен (есть cookie)');
        }}
    }}, {delay_ms});
    '''
    
    html = f'''
    <div class="ad-popup-overlay" id="adPopup" style="display: none;">
        <div class="ad-popup">
            <button class="ad-popup-close" onclick="closeAdPopup()">&times;</button>
            {render_banner_content(banner)}
        </div>
    </div>
    <script>
    {js_code}
    </script>
    '''
    
    return mark_safe(html)


@register.simple_tag
def show_ticker_ad():
    """
    Показать бегущую строку
    Использование: {% show_ticker_ad %}
    """
    try:
        place = AdPlace.objects.get(code='ticker_line', is_active=True)
    except AdPlace.DoesNotExist:
        return ''
    
    banners = AdBanner.objects.filter(
        place=place,
        is_active=True,
        campaign__is_active=True
    ).select_related('campaign')[:10]
    
    if not banners.exists():
        return ''
    
    ticker_items = []
    for banner in banners:
        click_url = reverse('advertising:banner_click', args=[banner.id])
        ticker_items.append(f'''
            <a href="{click_url}" 
               class="ad-ticker-item" 
               data-ad-click="{banner.id}"
               data-ad-type="banner"
               target="_blank">
                {banner.name}
            </a>
        ''')
    
    # Дублируем для бесшовной прокрутки
    ticker_content = ''.join(ticker_items) * 2
    
    html = f'''
    <div class="ad-ticker" id="adTicker">
        <div class="ad-ticker-content">
            {ticker_content}
        </div>
        <button class="ad-ticker-close" onclick="closeAdTicker()">Закрыть</button>
    </div>
    <script>
    function closeAdTicker() {{
        document.getElementById('adTicker').style.display = 'none';
        document.cookie = "ad_ticker_closed=1; max-age=3600; path=/";
    }}
    
    // Скрываем если уже закрывали
    if (document.cookie.includes('ad_ticker_closed=1')) {{
        document.getElementById('adTicker').style.display = 'none';
    }}
    </script>
    '''
    
    return mark_safe(html)


@register.filter
def process_content_with_ads(content, max_ads=3):
    """
    Обработать контент статьи и вставить контекстную рекламу
    Использование: {{ post.content|process_content_with_ads:2 }}
    """
    if not content:
        return content
    
    # Получаем активные контекстные объявления
    context_ads = ContextAd.objects.filter(
        is_active=True,
        campaign__is_active=True
    ).select_related('campaign').order_by('-priority')[:10]
    
    if not context_ads:
        return content
    
    # Ищем ключевые фразы в тексте
    processed_content = content
    ads_inserted = 0
    
    for ad in context_ads:
        if ads_inserted >= max_ads:
            break
        
        # Проверяем, есть ли ключевая фраза в тексте
        if ad.keyword_phrase.lower() in processed_content.lower():
            # Формируем рекламную ссылку
            click_url = reverse('advertising:context_click', args=[ad.id])
            ad_link = f'<a href="{click_url}" class="ad-context-link" data-ad-click="{ad.id}" data-ad-type="context" data-ad-context="{ad.id}" target="_blank">{ad.anchor_text}</a>'
            
            # Заменяем первое вхождение фразы
            processed_content = processed_content.replace(
                ad.keyword_phrase,
                ad_link,
                1
            )
            ads_inserted += 1
    
    return mark_safe(processed_content)


def render_card_content(card_num, banner, card_height):
    """Рендеринг одной карточки с поддержкой text_overlay и индивидуальной ссылки"""
    card_type = getattr(banner, f'card{card_num}_type', 'text')
    card_icon = getattr(banner, f'card{card_num}_icon', '✨')
    card_title = getattr(banner, f'card{card_num}_title', f'Карточка {card_num}')
    card_text = getattr(banner, f'card{card_num}_text', '')
    card_image = getattr(banner, f'card{card_num}_image', None)
    card_video = getattr(banner, f'card{card_num}_video', None)
    card_text_overlay = getattr(banner, f'card{card_num}_text_overlay', {})
    
    # Получаем URL карточки (если не указан - используется общий target_url баннера)
    card_url = getattr(banner, f'card{card_num}_url', None) or banner.target_url
    
    # Создаем URL для клика (через систему отслеживания)
    if card_url:
        # Кодируем URL для передачи в параметрах
        encoded_url = quote(card_url, safe='')
        click_url = reverse('advertising:banner_click', args=[banner.id]) + f'?card={card_num}&redirect={encoded_url}'
    else:
        click_url = reverse('advertising:banner_click', args=[banner.id])
    
    # Градиенты для каждой карточки
    gradients = {
        1: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        2: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
        3: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
        4: 'linear-gradient(135deg, #fa709a 0%, #fee140 100%)',
    }
    gradient = gradients.get(card_num, gradients[1])
    
    # Генерируем HTML для наложенного текста
    overlay_html = ''
    if isinstance(card_text_overlay, dict) and card_text_overlay.get('text'):
        overlay_text = card_text_overlay.get('text', '')
        overlay_color = card_text_overlay.get('color', '#ffffff')
        overlay_size = card_text_overlay.get('size', 24)
        overlay_x = card_text_overlay.get('x', 50)
        overlay_y = card_text_overlay.get('y', 50)
        overlay_align = card_text_overlay.get('align', 'center')
        
        overlay_html = f'''
        <div style="position:absolute; top:{overlay_y}%; left:{overlay_x}%; transform:translate(-50%, -50%); 
                    color:{overlay_color}; font-size:{overlay_size}px; font-weight:bold; 
                    text-align:{overlay_align}; text-shadow:2px 2px 4px rgba(0,0,0,0.8); 
                    white-space:nowrap; z-index:10; pointer-events:none;">
            {overlay_text}
        </div>
        '''
    
    # Обертка для ссылки
    link_start = f'<a href="{click_url}" class="ad-card-link" data-ad-banner="{banner.id}" data-ad-card="{card_num}" target="_blank" rel="noopener noreferrer" style="display:block; text-decoration:none; height:100%;">' if card_url else ''
    link_end = '</a>' if card_url else ''
    
    # Рендерим в зависимости от типа
    if card_type == 'image' and card_image:
        return f'''{link_start}<div style="position:relative; border-radius:8px; overflow:hidden; height:{card_height}px;">
        <img src="{card_image.url}" style="width:100%; height:{card_height}px; object-fit:cover;" alt="{card_title}">
        {overlay_html}
    </div>{link_end}'''
    elif card_type == 'video' and card_video:
        return f'''{link_start}<div style="position:relative; border-radius:8px; overflow:hidden; height:{card_height}px;">
        <video autoplay muted loop playsinline style="width:100%; height:{card_height}px; object-fit:cover;">
            <source src="{card_video.url}" type="video/mp4">
        </video>
        {overlay_html}
    </div>{link_end}'''
    else:
        # Текстовая карточка (по умолчанию)
        return f'''{link_start}<div style="background:{gradient}; color:white; text-align:center; border-radius:8px; padding:15px; display:flex; flex-direction:column; justify-content:center; height:{card_height}px;">
        <div style="font-size:32px; margin-bottom:8px;">{card_icon}</div>
        <h4 style="font-size:16px; font-weight:bold; margin-bottom:4px;">{card_title}</h4>
        <p style="font-size:12px; opacity:0.8;">{card_text}</p>
    </div>{link_end}'''


def render_banner_html(banner, place):
    """Генерация HTML для баннера"""
    click_url = reverse('advertising:banner_click', args=[banner.id])
    
    # Получаем высоту баннера
    banner_height = getattr(banner, 'banner_height', 100)
    
    # Если используется внешний код (от AdSense, РСЯ и т.д.)
    if banner.use_external_code and banner.external_code:
        # Внешний код показываем напрямую без обёртки в ссылку
        html = f'''
    <div class="ad-container" style="min-height: {banner_height}px;">
        <span class="ad-label">Реклама</span>
        <div class="ad-external" data-ad-banner="{banner.id}" data-ad-type="external" style="height: {banner_height}px;">
            {banner.external_code}
        </div>
    </div>
    '''
        return html
    
    # Для баннеров с 3 карточками (в статьях)
    if place.code in ['in_post_middle', 'in_post_middle_1', 'in_post_middle_2', 'before_article_content', 'after_comments'] and hasattr(banner, 'card1_type'):
        # Уменьшенные отступы: gap 5px, padding 10px
        card_height = banner_height - 20  # Вычитаем padding (10px * 2)
        card1 = render_card_content(1, banner, card_height)
        card2 = render_card_content(2, banner, card_height)
        card3 = render_card_content(3, banner, card_height)
        
        content = f'''<div style="display:grid; grid-template-columns:repeat(3, 1fr); gap:5px; padding:10px; height:{banner_height}px; box-sizing:border-box;">
        {card1}
        {card2}
        {card3}
    </div>'''
    # Для header и footer баннеров используем 4 карточки
    elif place.code in ['header_banner', 'footer_banner'] and hasattr(banner, 'card1_type'):
        # Уменьшенные отступы: gap 5px, padding 10px
        card_height = banner_height - 20  # Вычитаем padding (10px * 2)
        card1 = render_card_content(1, banner, card_height)
        card2 = render_card_content(2, banner, card_height)
        card3 = render_card_content(3, banner, card_height)
        card4 = render_card_content(4, banner, card_height)
        
        content = f'''<div style="display:grid; grid-template-columns:repeat(4, 1fr); gap:5px; padding:10px; height:{banner_height}px; box-sizing:border-box;">
        {card1}
        {card2}
        {card3}
        {card4}
    </div>'''
    # Стандартная обработка для остальных баннеров
    elif banner.banner_type == 'image' and banner.image:
        content = f'<img src="{banner.image.url}" alt="{banner.alt_text or banner.name}" style="height: {banner_height}px; width: 100%; object-fit: cover;" />'
    elif banner.banner_type == 'video' and banner.video:
        content = f'''
        <video autoplay muted loop style="height: {banner_height}px; width: 100%; object-fit: cover;">
            <source src="{banner.video.url}" type="video/mp4">
        </video>
        '''
    elif banner.banner_type == 'html' and banner.html_content:
        content = f'<div style="height: {banner_height}px;">{banner.html_content}</div>'
    else:
        content = f'<div style="padding: 2rem; height: {banner_height}px; text-align: center; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-radius: 0.5rem; display: flex; align-items: center; justify-content: center;"><h3>{banner.name}</h3></div>'
    
    # Если это баннер с карточками - не оборачиваем в общую ссылку (каждая карточка имеет свою)
    if place.code in ['header_banner', 'footer_banner', 'in_post_middle', 'in_post_middle_1', 'in_post_middle_2', 'before_article_content', 'after_comments'] and hasattr(banner, 'card1_type'):
        html = f'''
    <div class="ad-container" style="min-height: {banner_height}px;">
        <span class="ad-label">Реклама</span>
        <div class="ad-banner ad-banner-{place.code}" 
             data-ad-banner="{banner.id}"
             data-ad-type="banner">
            {content}
        </div>
    </div>
    '''
    else:
        # Для обычных баннеров - оборачиваем в ссылку
        html = f'''
    <div class="ad-container" style="min-height: {banner_height}px;">
        <span class="ad-label">Реклама</span>
        <a href="{click_url}" 
           class="ad-banner ad-banner-{place.code}" 
           data-ad-banner="{banner.id}"
           data-ad-click="{banner.id}"
           data-ad-type="banner"
           target="_blank"
           rel="noopener noreferrer"
           style="display: block; height: {banner_height}px;">
            {content}
        </a>
    </div>
    '''
    
    return html


def render_banner_content(banner):
    """Генерация контента баннера без обертки"""
    click_url = reverse('advertising:banner_click', args=[banner.id])
    
    if banner.banner_type == 'image' and banner.image:
        return f'<a href="{click_url}" data-ad-click="{banner.id}" data-ad-type="banner" target="_blank"><img src="{banner.image.url}" alt="{banner.alt_text or banner.name}" /></a>'
    elif banner.banner_type == 'video' and banner.video:
        return f'<a href="{click_url}" data-ad-click="{banner.id}" data-ad-type="banner" target="_blank"><video autoplay muted loop><source src="{banner.video.url}" type="video/mp4"></video></a>'
    elif banner.banner_type == 'html':
        return banner.html_content
    else:
        return f'<a href="{click_url}" data-ad-click="{banner.id}" data-ad-type="banner" target="_blank"><div style="padding: 2rem;">{banner.name}</div></a>'


@register.simple_tag(takes_context=True)
def ad_tracking_enabled(context):
    """Возвращает True, если пользователю разрешено показывать рекламные трекеры."""
    request = context.get('request')
    if not request:
        return True

    consent_raw = request.COOKIES.get('idealimage_cookie_consent')
    if not consent_raw:
        return True

    try:
        consent = json.loads(consent_raw)
    except json.JSONDecodeError:
        return True

    return bool(consent.get('advertising', True))


@register.simple_tag
def load_external_scripts(position='head_end'):
    """
    Загружает внешние скрипты для указанной позиции
    С кэшированием для оптимизации производительности
    
    Использование в шаблоне:
    {% load_external_scripts 'head_start' %}
    {% load_external_scripts 'head_end' %}
    {% load_external_scripts 'body_start' %}
    {% load_external_scripts 'body_end' %}
    """
    from ..models import ExternalScript
    
    # Кэшируем HTML скриптов на 10 минут
    cache_key = f'external_scripts_html_{position}'
    cached_html = cache.get(cache_key)
    
    if cached_html is not None:
        return mark_safe(cached_html)
    
    # Получаем активные скрипты для указанной позиции
    scripts = ExternalScript.objects.filter(
        is_active=True,
        position=position
    ).order_by('priority')
    
    # Формируем HTML
    html_parts = []
    html_parts.append(f'\n    <!-- External Scripts: {position} -->')
    
    for script in scripts:
        html_parts.append(f'\n    <!-- {script.name} ({script.get_script_type_display()}) -->')
        html_parts.append(f'\n    {script.get_safe_code()}')
    
    if scripts.exists():
        html_parts.append(f'\n    <!-- /External Scripts: {position} -->\n')
    
    html = ''.join(html_parts)
    
    # Кэшируем на 10 минут (600 секунд)
    cache.set(cache_key, html, 600)
    
    return mark_safe(html)

