"""
Сигналы для приложения advertising
"""
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from .models import AdClick, AdImpression, AdCampaign, ExternalScript, AdsTxtSettings


@receiver(post_save, sender=AdClick)
def update_click_counters(sender, instance, created, **kwargs):
    """Обновление счетчиков кликов при создании клика"""
    if created:
        # Обновляем счетчик кликов в баннере
        if instance.ad_banner:
            instance.ad_banner.clicks += 1
            instance.ad_banner.save(update_fields=['clicks'])
            
            # Обновляем потраченную сумму кампании
            campaign = instance.ad_banner.campaign
            campaign.spent_amount += campaign.cost_per_click
            campaign.save(update_fields=['spent_amount'])
            
            # Обновляем общую сумму рекламодателя
            campaign.advertiser.update_total_spent()
        
        # Обновляем счетчик кликов в контекстной рекламе
        if instance.context_ad:
            instance.context_ad.clicks += 1
            instance.context_ad.save(update_fields=['clicks'])
            
            # Обновляем потраченную сумму
            campaign = instance.context_ad.campaign
            campaign.spent_amount += instance.context_ad.cost_per_click
            campaign.save(update_fields=['spent_amount'])
            
            campaign.advertiser.update_total_spent()
        
        # Обновляем счетчик кликов в конкретной вставке
        if instance.ad_insertion:
            instance.ad_insertion.clicks += 1
            instance.ad_insertion.save(update_fields=['clicks'])


@receiver(post_save, sender=AdImpression)
def update_impression_counters(sender, instance, created, **kwargs):
    """Обновление счетчиков показов при создании показа"""
    if created:
        # Обновляем счетчик показов в баннере
        if instance.ad_banner:
            instance.ad_banner.impressions += 1
            instance.ad_banner.save(update_fields=['impressions'])
            
            # Обновляем потраченную сумму кампании (CPM)
            campaign = instance.ad_banner.campaign
            if campaign.cost_per_impression > 0:
                # CPM = стоимость за 1000 показов
                cost = campaign.cost_per_impression / 1000
                campaign.spent_amount += cost
                campaign.save(update_fields=['spent_amount'])
                
                campaign.advertiser.update_total_spent()
        
        # Обновляем счетчик показов в контекстной рекламе
        if instance.context_ad:
            instance.context_ad.impressions += 1
            instance.context_ad.save(update_fields=['impressions'])
        
        # Обновляем счетчик показов в конкретной вставке
        if instance.ad_insertion:
            instance.ad_insertion.views += 1
            instance.ad_insertion.save(update_fields=['views'])
        
        # Обновляем счетчик показов в расписании
        if instance.ad_banner:
            for schedule in instance.ad_banner.schedules.filter(is_active=True):
                if schedule.can_show():
                    schedule.current_impressions += 1
                    schedule.save(update_fields=['current_impressions'])


# ============ ИНВАЛИДАЦИЯ КЭША ============

@receiver(post_save, sender=ExternalScript)
@receiver(post_delete, sender=ExternalScript)
def invalidate_external_scripts_cache(sender, instance, **kwargs):
    """Инвалидирует кэш внешних скриптов при изменении"""
    # Удаляем кэш для всех позиций
    for position in ['head_start', 'head_end', 'body_start', 'body_end']:
        cache.delete(f'external_scripts_html_{position}')
    
    # Инвалидируем статистику скриптов
    cache.delete('external_scripts_stats')


@receiver(post_save, sender=AdsTxtSettings)
@receiver(post_delete, sender=AdsTxtSettings)
def invalidate_ads_txt_cache(sender, instance, **kwargs):
    """Инвалидирует кэш ads.txt при изменении настроек"""
    cache.delete('ads_txt_settings_obj')
    if hasattr(instance, 'id'):
        cache.delete(f'ads_txt_content_{instance.id}')
        cache.delete(f'ads_txt_needs_update_{instance.id}')
    cache.delete('ads_txt_status')

