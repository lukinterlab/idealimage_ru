"""
Автоматическая активация услуг после успешной оплаты
"""
from datetime import timedelta
from django.utils import timezone
from django.db import transaction
import logging

from .models import (
    Donation, Subscription, PaidArticle, ArticlePurchase, 
    Marathon, MarathonPurchase
)

logger = logging.getLogger(__name__)


class ServiceActivator:
    """Класс для автоматической активации услуг после оплаты"""
    
    def activate_service(self, donation):
        """
        Активировать услугу на основе назначения платежа
        
        :param donation: Объект Donation
        :return: bool - успешность активации
        """
        try:
            purpose = donation.payment_purpose
            
            if purpose == 'premium_monthly':
                return self._activate_premium(donation, months=1)
            elif purpose == 'premium_3months':
                return self._activate_premium(donation, months=3)
            elif purpose == 'premium_yearly':
                return self._activate_premium(donation, months=12)
            
            elif purpose == 'ai_coauthor_monthly':
                return self._activate_ai_coauthor(donation, months=1)
            elif purpose == 'ai_once':
                return self._activate_ai_once(donation)
            elif purpose in ['ai_pack_5', 'ai_pack_10', 'ai_pack_30']:
                return self._activate_ai_pack(donation, purpose)
            
            elif purpose.startswith('marathon_'):
                return self._activate_marathon(donation, purpose)
            
            elif purpose.startswith('ad_'):
                return self._activate_advertising(donation, purpose)
            
            elif purpose == 'article_purchase':
                return self._activate_article_purchase(donation)
            
            else:
                logger.info(f"Донат {donation.id} - обычный донат, активация не требуется")
                return True
                
        except Exception as e:
            logger.error(f"Ошибка активации услуги для доната {donation.id}: {str(e)}")
            return False
    
    @transaction.atomic
    def _activate_premium(self, donation, months=1):
        """Активировать Premium подписку"""
        if not donation.user:
            logger.error(f"Донат {donation.id} без пользователя")
            return False
        
        # Проверить, есть ли уже активная подписка
        existing = Subscription.objects.filter(
            user=donation.user,
            subscription_type='premium',
            is_active=True,
            end_date__gt=timezone.now()
        ).first()
        
        if existing:
            # Продлить существующую подписку
            existing.end_date += timedelta(days=30 * months)
            existing.save()
            logger.info(f"Premium подписка продлена для пользователя {donation.user.id} до {existing.end_date}")
        else:
            # Создать новую подписку
            end_date = timezone.now() + timedelta(days=30 * months)
            Subscription.objects.create(
                user=donation.user,
                subscription_type='premium',
                price=donation.amount,
                end_date=end_date,
                is_active=True,
                payment=donation
            )
            logger.info(f"Premium подписка создана для пользователя {donation.user.id} до {end_date}")
        
        return True
    
    @transaction.atomic
    def _activate_ai_coauthor(self, donation, months=1):
        """Активировать подписку AI-Соавтор"""
        if not donation.user:
            logger.error(f"Донат {donation.id} без пользователя")
            return False
        
        existing = Subscription.objects.filter(
            user=donation.user,
            subscription_type='ai_coauthor',
            is_active=True,
            end_date__gt=timezone.now()
        ).first()
        
        if existing:
            existing.end_date += timedelta(days=30 * months)
            existing.save()
            logger.info(f"AI-Соавтор подписка продлена для пользователя {donation.user.id}")
        else:
            end_date = timezone.now() + timedelta(days=30 * months)
            Subscription.objects.create(
                user=donation.user,
                subscription_type='ai_coauthor',
                price=donation.amount,
                end_date=end_date,
                is_active=True,
                payment=donation
            )
            logger.info(f"AI-Соавтор подписка создана для пользователя {donation.user.id}")
        
        return True
    
    def _activate_ai_once(self, donation):
        """Активировать разовую генерацию AI"""
        # Для разовой генерации создаем запись с коротким сроком
        if not donation.user:
            return False
        
        end_date = timezone.now() + timedelta(days=1)  # 1 день на использование
        Subscription.objects.create(
            user=donation.user,
            subscription_type='ai_once',
            price=donation.amount,
            end_date=end_date,
            is_active=True,
            payment=donation
        )
        logger.info(f"AI разовая генерация активирована для пользователя {donation.user.id}")
        return True
    
    def _activate_ai_pack(self, donation, purpose):
        """Активировать пакет AI статей"""
        # Извлечь количество статей из purpose (ai_pack_5 -> 5)
        count = int(purpose.split('_')[-1])
        
        if not donation.user:
            return False
        
        # Создать запись с количеством доступных генераций
        end_date = timezone.now() + timedelta(days=365)  # Год на использование
        Subscription.objects.create(
            user=donation.user,
            subscription_type=f'ai_pack_{count}',
            price=donation.amount,
            end_date=end_date,
            is_active=True,
            payment=donation
        )
        logger.info(f"AI пакет {count} статей активирован для пользователя {donation.user.id}")
        return True
    
    @transaction.atomic
    def _activate_marathon(self, donation, purpose):
        """Активировать марафон"""
        # Определить марафон по purpose
        marathon_map = {
            'marathon_skin': 'Идеальная кожа',
            'marathon_makeup': 'Макияж',
            'marathon_wardrobe': 'Гардероб',
        }
        
        marathon_title = marathon_map.get(purpose)
        if not marathon_title:
            logger.error(f"Неизвестный марафон: {purpose}")
            return False
        
        if not donation.user:
            return False
        
        # Найти марафон
        try:
            marathon = Marathon.objects.get(title__icontains=marathon_title)
        except Marathon.DoesNotExist:
            logger.error(f"Марафон '{marathon_title}' не найден в базе")
            return False
        
        # Проверить, не купил ли уже
        if MarathonPurchase.objects.filter(user=donation.user, marathon=marathon).exists():
            logger.info(f"Пользователь {donation.user.id} уже купил марафон {marathon.id}")
            return True
        
        # Создать покупку
        MarathonPurchase.objects.create(
            user=donation.user,
            marathon=marathon,
            payment=donation
        )
        logger.info(f"Марафон {marathon.id} активирован для пользователя {donation.user.id}")
        return True
    
    def _activate_advertising(self, donation, purpose):
        """Активировать рекламу"""
        # TODO: Интеграция с модулем advertising
        # Пока просто логируем
        logger.info(f"Реклама {purpose} оплачена донатом {donation.id}")
        return True
    
    @transaction.atomic
    def _activate_article_purchase(self, donation):
        """Активировать покупку платной статьи"""
        # Нужно получить ID статьи из metadata или другого поля
        article_id = donation.payment_data.get('metadata', {}).get('article_id')
        
        if not article_id or not donation.user:
            logger.error(f"Не указан article_id для доната {donation.id}")
            return False
        
        try:
            paid_article = PaidArticle.objects.get(article_id=article_id)
        except PaidArticle.DoesNotExist:
            logger.error(f"Платная статья {article_id} не найдена")
            return False
        
        # Проверить, не купил ли уже
        if ArticlePurchase.objects.filter(user=donation.user, article=paid_article).exists():
            logger.info(f"Пользователь {donation.user.id} уже купил статью {article_id}")
            return True
        
        # Создать покупку
        ArticlePurchase.objects.create(
            user=donation.user,
            article=paid_article,
            payment=donation
        )
        logger.info(f"Статья {article_id} активирована для пользователя {donation.user.id}")
        return True


# Глобальный экземпляр активатора
service_activator = ServiceActivator()

