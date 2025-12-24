"""
Context processors для Sozseti
"""
from .models import SocialChannel, SocialPlatform


def social_links(request):
    """
    Добавляет ссылки на социальные сети в контекст всех шаблонов
    
    Returns:
        dict: {'social_links': {...}}
    """
    links = {
        'telegram_main': 'https://t.me/ideal_image_ru',
        'telegram_channels': [],
        'vk': None,
        'pinterest': None,
        'rutube': None,
        'dzen': None,
        'whatsapp_enabled': True,
        'max_coming_soon': True,
        'instagram_coming_soon': True,
        'facebook_coming_soon': True,
        'youtube_coming_soon': True,
    }
    
    try:
        # Telegram каналы
        telegram_platform = SocialPlatform.objects.filter(name='telegram').first()
        if telegram_platform:
            telegram_channels = SocialChannel.objects.filter(
                platform=telegram_platform,
                is_active=True
            ).values('channel_name', 'channel_url', 'channel_id')[:5]  # Топ 5 для футера
            
            links['telegram_channels'] = list(telegram_channels)
            
            # Главный канал
            main_channel = SocialChannel.objects.filter(
                platform=telegram_platform,
                channel_id='@ideal_image_ru'
            ).first()
            
            if main_channel:
                links['telegram_main'] = main_channel.channel_url
        
        # VK
        vk_platform = SocialPlatform.objects.filter(name='vk').first()
        if vk_platform:
            vk_channel = vk_platform.channels.first()
            if vk_channel:
                links['vk'] = vk_channel.channel_url
        
        # Pinterest
        pinterest_platform = SocialPlatform.objects.filter(name='pinterest').first()
        if pinterest_platform:
            pinterest_channel = pinterest_platform.channels.first()
            if pinterest_channel:
                links['pinterest'] = pinterest_channel.channel_url
        
        # Rutube
        rutube_platform = SocialPlatform.objects.filter(name='rutube').first()
        if rutube_platform:
            rutube_channel = rutube_platform.channels.first()
            if rutube_channel:
                links['rutube'] = rutube_channel.channel_url
        
        # Dzen
        dzen_platform = SocialPlatform.objects.filter(name='dzen').first()
        if dzen_platform:
            dzen_channel = dzen_platform.channels.first()
            if dzen_channel:
                links['dzen'] = dzen_channel.channel_url
    
    except Exception:
        # Если ошибка БД, возвращаем значения по умолчанию
        pass
    
    return {'social_links': links}

