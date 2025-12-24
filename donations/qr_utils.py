"""
Утилиты для генерации QR-кодов для платежей
"""
import qrcode
from io import BytesIO
import base64
from decimal import Decimal
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def generate_qr_code(data: str, size: int = 10, border: int = 2) -> str:
    """
    Генерация QR-кода и возврат в виде base64 строки
    
    :param data: Данные для кодирования
    :param size: Размер QR-кода
    :param border: Размер границы
    :return: Base64 строка с изображением QR-кода
    """
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=size,
            border=border,
        )
        qr.add_data(data)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        return f"data:image/png;base64,{img_base64}"
        
    except Exception as e:
        logger.error(f"Ошибка генерации QR-кода: {str(e)}")
        return ""


def generate_payment_qr(payment_url: str) -> str:
    """
    Генерация QR-кода для ссылки на оплату
    
    :param payment_url: URL страницы оплаты
    :return: Base64 строка с QR-кодом
    """
    return generate_qr_code(payment_url)


def generate_sbp_qr(amount: Decimal, recipient_phone: str, recipient_name: str, 
                    purpose: Optional[str] = None) -> str:
    """
    Генерация QR-кода для СБП
    Формат: https://qr.nspk.ru/proxyapp?...
    
    :param amount: Сумма платежа
    :param recipient_phone: Телефон получателя (формат: +7XXXXXXXXXX)
    :param recipient_name: Имя получателя
    :param purpose: Назначение платежа
    :return: Base64 строка с QR-кодом
    """
    # Формируем данные для СБП QR
    # Это упрощенный формат, для полноценной работы нужны реальные реквизиты банка
    sbp_data_parts = [
        f"ST00012",  # Тип документа - статический QR
        f"|Name={recipient_name}",
        f"|PersonalAcc={recipient_phone}",
        f"|BankName=Bank",
    ]
    
    if purpose:
        sbp_data_parts.append(f"|Purpose={purpose}")
    
    if amount:
        sbp_data_parts.append(f"|Sum={float(amount):.2f}")
    
    sbp_data = "".join(sbp_data_parts)
    
    return generate_qr_code(sbp_data)


def generate_universal_qr(payment_url: str, amount: Decimal, description: str) -> str:
    """
    Генерация универсального QR-кода с информацией о платеже
    
    :param payment_url: URL для оплаты
    :param amount: Сумма платежа
    :param description: Описание платежа
    :return: Base64 строка с QR-кодом
    """
    # Для универсального QR используем просто URL оплаты
    # При сканировании откроется страница с выбором способа оплаты
    return generate_qr_code(payment_url)


def generate_yandex_qr(payment_url: str) -> str:
    """
    Генерация QR-кода для Яндекс.Кассы
    
    :param payment_url: URL подтверждения платежа от ЮKassa
    :return: Base64 строка с QR-кодом
    """
    return generate_qr_code(payment_url)


def generate_sber_qr(payment_url: str) -> str:
    """
    Генерация QR-кода для СберПей
    
    :param payment_url: URL оплаты от Сбербанка
    :return: Base64 строка с QR-кодом
    """
    return generate_qr_code(payment_url)
