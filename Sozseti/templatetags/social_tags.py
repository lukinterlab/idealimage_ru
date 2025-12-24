"""
Template tags для социальных сетей
"""
from django import template
from django.utils.safestring import mark_safe
from Sozseti.api_integrations.whatsapp_share import WhatsAppShare
from Sozseti.models import SocialChannel, SocialPlatform


register = template.Library()


@register.simple_tag
def whatsapp_share_link(post):
    """
    Генерирует ссылку для кнопки WhatsApp
    
    Usage:
        {% whatsapp_share_link post %}
    """
    return WhatsAppShare.generate_share_link(post)


@register.simple_tag
def whatsapp_share_button(post, css_classes=''):
    """
    Генерирует HTML кнопку WhatsApp
    
    Usage:
        {% whatsapp_share_button post "btn btn-success" %}
    """
    return mark_safe(WhatsAppShare.get_share_button_html(post, css_classes))


@register.simple_tag
def get_telegram_channels():
    """
    Возвращает все активные Telegram каналы
    
    Usage:
        {% get_telegram_channels as channels %}
    """
    try:
        platform = SocialPlatform.objects.get(name='telegram')
        return SocialChannel.objects.filter(
            platform=platform,
            is_active=True
        ).order_by('channel_name')
    except SocialPlatform.DoesNotExist:
        return []


@register.simple_tag
def get_main_social_links():
    """
    Возвращает основные ссылки на соцсети для футера
    
    Usage:
        {% get_main_social_links as social_links %}
    """
    links = {}
    
    try:
        # Telegram главный канал
        telegram_platform = SocialPlatform.objects.get(name='telegram')
        main_channel = SocialChannel.objects.filter(
            platform=telegram_platform,
            channel_id='@ideal_image_ru'
        ).first()
        
        if main_channel:
            links['telegram'] = main_channel.channel_url
        
        # VK группа
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
    
    except Exception as e:
        pass
    
    return links


@register.inclusion_tag('Sozseti/widgets/social_share_buttons.html')
def social_share_buttons(post):
    """
    Включаемый тег для блока кнопок "Поделиться"
    
    Usage:
        {% social_share_buttons post %}
    """
    return {
        'post': post,
    }


@register.filter
def get_publication_count(post):
    """
    Возвращает количество публикаций статьи в соцсетях
    
    Usage:
        {{ post|get_publication_count }}
    """
    if hasattr(post, 'social_publications'):
        return post.social_publications.filter(status='published').count()
    return 0

