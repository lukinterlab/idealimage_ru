"""
Утилиты для работы с платежными системами
"""
import requests
import uuid
from decimal import Decimal
from typing import Dict, Optional
from django.conf import settings
from decouple import config
import logging

logger = logging.getLogger(__name__)


class YandexKassaPayment:
    """Класс для работы с Яндекс.Кассой (ЮKassa)"""
    
    def __init__(self):
        self.shop_id = config('YANDEX_SHOP_ID', default='')
        self.secret_key = config('YANDEX_SECRET_KEY', default='')
        self.api_url = 'https://api.yookassa.ru/v3/payments'
        
        # Для тестового режима
        self.test_mode = config('YANDEX_TEST_MODE', default=True, cast=bool)
        if self.test_mode:
            self.api_url = 'https://api.yookassa.ru/v3/payments'
    
    def create_payment(self, amount: Decimal, description: str, return_url: str, 
                      user_email: str, metadata: Optional[Dict] = None) -> Dict:
        """
        Создание платежа в Яндекс.Кассе
        
        :param amount: Сумма платежа
        :param description: Описание платежа
        :param return_url: URL для возврата после оплаты
        :param user_email: Email пользователя
        :param metadata: Дополнительные данные
        :return: Данные созданного платежа
        """
        if not self.shop_id or not self.secret_key:
            logger.error("Не настроены данные для Яндекс.Кассы")
            return {'error': 'Payment system not configured'}
        
        idempotence_key = str(uuid.uuid4())
        
        payment_data = {
            "amount": {
                "value": f"{float(amount):.2f}",
                "currency": "RUB"
            },
            "confirmation": {
                "type": "redirect",
                "return_url": return_url
            },
            "capture": True,
            "description": description,
            "receipt": {
                "customer": {
                    "email": user_email
                },
                "items": [
                    {
                        "description": description[:128],  # Максимум 128 символов
                        "quantity": "1.00",
                        "amount": {
                            "value": f"{float(amount):.2f}",
                            "currency": "RUB"
                        },
                        "vat_code": 1,  # НДС не облагается
                        "payment_mode": "full_payment",  # Полная оплата
                        "payment_subject": "service"  # Услуга
                    }
                ]
            },
            "metadata": metadata or {}
        }
        
        try:
            response = requests.post(
                self.api_url,
                json=payment_data,
                auth=(self.shop_id, self.secret_key),
                headers={
                    'Idempotence-Key': idempotence_key,
                    'Content-Type': 'application/json'
                },
                timeout=10
            )
            
            if response.status_code in [200, 201]:
                result = response.json()
                logger.info(f"Создан платеж ЮKassa: {result.get('id')}")
                return result
            else:
                logger.error(f"Ошибка создания платежа ЮKassa: {response.text}")
                return {'error': response.text}
                
        except Exception as e:
            logger.error(f"Исключение при создании платежа ЮKassa: {str(e)}")
            return {'error': str(e)}
    
    def get_payment(self, payment_id: str) -> Dict:
        """Получение информации о платеже"""
        try:
            response = requests.get(
                f"{self.api_url}/{payment_id}",
                auth=(self.shop_id, self.secret_key),
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Ошибка получения платежа: {response.text}")
                return {'error': response.text}
                
        except Exception as e:
            logger.error(f"Исключение при получении платежа: {str(e)}")
            return {'error': str(e)}
    
    def capture_payment(self, payment_id: str, amount: Optional[Decimal] = None) -> Dict:
        """Подтверждение платежа"""
        try:
            data = {}
            if amount:
                data['amount'] = {
                    "value": f"{float(amount):.2f}",
                    "currency": "RUB"
                }
            
            response = requests.post(
                f"{self.api_url}/{payment_id}/capture",
                json=data,
                auth=(self.shop_id, self.secret_key),
                headers={
                    'Idempotence-Key': str(uuid.uuid4()),
                    'Content-Type': 'application/json'
                },
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Ошибка подтверждения платежа: {response.text}")
                return {'error': response.text}
                
        except Exception as e:
            logger.error(f"Исключение при подтверждении платежа: {str(e)}")
            return {'error': str(e)}
    
    def cancel_payment(self, payment_id: str) -> Dict:
        """Отмена платежа"""
        try:
            response = requests.post(
                f"{self.api_url}/{payment_id}/cancel",
                auth=(self.shop_id, self.secret_key),
                headers={
                    'Idempotence-Key': str(uuid.uuid4()),
                    'Content-Type': 'application/json'
                },
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Ошибка отмены платежа: {response.text}")
                return {'error': response.text}
                
        except Exception as e:
            logger.error(f"Исключение при отмене платежа: {str(e)}")
            return {'error': str(e)}


class SberPayPayment:
    """Класс для работы с СберПей"""
    
    def __init__(self):
        self.merchant_login = config('SBER_MERCHANT_LOGIN', default='')
        self.merchant_password = config('SBER_MERCHANT_PASSWORD', default='')
        
        # API endpoints
        self.test_mode = config('SBER_TEST_MODE', default=True, cast=bool)
        if self.test_mode:
            self.api_url = 'https://3dsec.sberbank.ru/payment/rest'
        else:
            self.api_url = 'https://securepayments.sberbank.ru/payment/rest'
    
    def create_payment(self, amount: Decimal, order_number: str, return_url: str, 
                      description: str, user_email: Optional[str] = None) -> Dict:
        """
        Создание платежа через СберПей
        
        :param amount: Сумма в рублях
        :param order_number: Номер заказа
        :param return_url: URL возврата
        :param description: Описание платежа
        :param user_email: Email для отправки чека
        :return: Данные созданного платежа
        """
        if not self.merchant_login or not self.merchant_password:
            logger.error("Не настроены данные для СберПей")
            return {'error': 'Payment system not configured'}
        
        # Сумма в копейках
        amount_kopeks = int(amount * 100)
        
        params = {
            'userName': self.merchant_login,
            'password': self.merchant_password,
            'orderNumber': order_number,
            'amount': amount_kopeks,
            'returnUrl': return_url,
            'description': description,
        }
        
        if user_email:
            params['email'] = user_email
        
        try:
            response = requests.post(
                f"{self.api_url}/register.do",
                params=params,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('errorCode') == '0':
                    logger.info(f"Создан платеж СберПей: {result.get('orderId')}")
                    return result
                else:
                    logger.error(f"Ошибка СберПей: {result.get('errorMessage')}")
                    return {'error': result.get('errorMessage')}
            else:
                logger.error(f"Ошибка HTTP при создании платежа СберПей: {response.text}")
                return {'error': response.text}
                
        except Exception as e:
            logger.error(f"Исключение при создании платежа СберПей: {str(e)}")
            return {'error': str(e)}
    
    def get_order_status(self, order_id: str) -> Dict:
        """Получение статуса заказа"""
        try:
            params = {
                'userName': self.merchant_login,
                'password': self.merchant_password,
                'orderId': order_id,
            }
            
            response = requests.post(
                f"{self.api_url}/getOrderStatusExtended.do",
                params=params,
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Ошибка получения статуса: {response.text}")
                return {'error': response.text}
                
        except Exception as e:
            logger.error(f"Исключение при получении статуса: {str(e)}")
            return {'error': str(e)}
    
    def refund_payment(self, order_id: str, amount: Decimal) -> Dict:
        """Возврат платежа"""
        try:
            amount_kopeks = int(amount * 100)
            
            params = {
                'userName': self.merchant_login,
                'password': self.merchant_password,
                'orderId': order_id,
                'amount': amount_kopeks,
            }
            
            response = requests.post(
                f"{self.api_url}/refund.do",
                params=params,
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Ошибка возврата: {response.text}")
                return {'error': response.text}
                
        except Exception as e:
            logger.error(f"Исключение при возврате: {str(e)}")
            return {'error': str(e)}


class SBPPayment:
    """Класс для работы с Системой Быстрых Платежей"""
    
    def __init__(self):
        # СБП работает через банки-участники, используем ЮKassa или Сбер в качестве шлюза
        self.gateway = config('SBP_GATEWAY', default='yookassa')  # yookassa или sber
        
        if self.gateway == 'yookassa':
            self.payment_provider = YandexKassaPayment()
        else:
            self.payment_provider = SberPayPayment()
    
    def create_sbp_payment(self, amount: Decimal, description: str, return_url: str, 
                          user_email: str) -> Dict:
        """
        Создание платежа через СБП
        СБП интегрируется через платежные шлюзы (ЮKassa или Сбербанк)
        """
        if self.gateway == 'yookassa':
            # Через ЮKassa с указанием метода оплаты СБП
            payment = self.payment_provider.create_payment(
                amount=amount,
                description=description,
                return_url=return_url,
                user_email=user_email,
                metadata={'payment_method': 'sbp'}
            )
            return payment
        else:
            # Через Сбербанк
            order_number = str(uuid.uuid4())
            return self.payment_provider.create_payment(
                amount=amount,
                order_number=order_number,
                return_url=return_url,
                description=description,
                user_email=user_email
            )


def get_payment_handler(payment_method: str):
    """Фабрика для получения обработчика платежей"""
    handlers = {
        'yandex': YandexKassaPayment,
        'sberpay': SberPayPayment,
        'sbp': SBPPayment,
    }
    
    handler_class = handlers.get(payment_method)
    if handler_class:
        return handler_class()
    else:
        raise ValueError(f"Неподдерживаемый метод оплаты: {payment_method}")
