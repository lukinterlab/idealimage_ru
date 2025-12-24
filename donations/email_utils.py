"""
Утилиты для отправки email уведомлений
"""
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.utils.html import strip_tags
import logging

from .models import Donation, DonationSettings, DonationNotification

logger = logging.getLogger(__name__)


def send_thank_you_email(donation: Donation) -> bool:
    """
    Отправка благодарственного письма донатеру
    
    :param donation: Объект доната
    :return: True если отправлено успешно
    """
    donation_settings = DonationSettings.get_settings()
    
    if not donation_settings.send_email_to_donor:
        return False
    
    try:
        subject = donation_settings.thank_you_subject
        
        # Формируем HTML и текстовую версии письма
        html_content = render_to_string('donations/emails/thank_you_email.html', {
            'donation': donation,
            'settings': donation_settings,
            'site_url': settings.SITE_URL,
        })
        
        text_content = strip_tags(html_content)
        
        # Создаем email с HTML
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[donation.user_email],
        )
        email.attach_alternative(html_content, "text/html")
        email.send()
        
        # Логируем отправку
        DonationNotification.objects.create(
            donation=donation,
            notification_type='email_donor',
            recipient=donation.user_email,
            is_successful=True,
        )
        
        logger.info(f"Отправлено благодарственное письмо для доната {donation.id}")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка отправки благодарственного письма: {str(e)}")
        
        # Логируем ошибку
        DonationNotification.objects.create(
            donation=donation,
            notification_type='email_donor',
            recipient=donation.user_email,
            is_successful=False,
            error_message=str(e),
        )
        
        return False


def send_admin_notification(donation: Donation) -> bool:
    """
    Отправка уведомления администратору о новом донате
    
    :param donation: Объект доната
    :return: True если отправлено успешно
    """
    donation_settings = DonationSettings.get_settings()
    
    if not donation_settings.send_email_to_admin:
        return False
    
    # Получаем список email администраторов
    admin_emails = donation_settings.admin_emails.strip().split('\n')
    admin_emails = [email.strip() for email in admin_emails if email.strip()]
    
    if not admin_emails:
        # Используем EMAIL_ADMIN из настроек Django
        admin_emails = settings.EMAIL_ADMIN
    
    if not admin_emails:
        logger.warning("Не указаны email администраторов")
        return False
    
    try:
        subject = f'Новый донат: {donation.amount} ₽'
        
        # Формируем HTML и текстовую версии письма
        html_content = render_to_string('donations/emails/admin_notification.html', {
            'donation': donation,
            'site_url': settings.SITE_URL,
        })
        
        text_content = strip_tags(html_content)
        
        # Создаем email с HTML
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=admin_emails,
        )
        email.attach_alternative(html_content, "text/html")
        email.send()
        
        # Логируем отправку для каждого получателя
        for admin_email in admin_emails:
            DonationNotification.objects.create(
                donation=donation,
                notification_type='email_admin',
                recipient=admin_email,
                is_successful=True,
            )
        
        logger.info(f"Отправлено уведомление администраторам о донате {donation.id}")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка отправки уведомления администратору: {str(e)}")
        
        # Логируем ошибку
        for admin_email in admin_emails:
            DonationNotification.objects.create(
                donation=donation,
                notification_type='email_admin',
                recipient=admin_email,
                is_successful=False,
                error_message=str(e),
            )
        
        return False


def send_refund_notification(donation: Donation) -> bool:
    """
    Отправка уведомления о возврате средств
    
    :param donation: Объект доната
    :return: True если отправлено успешно
    """
    try:
        subject = 'Возврат средств - IdealImage.ru'
        
        html_content = render_to_string('donations/emails/refund_notification.html', {
            'donation': donation,
            'site_url': settings.SITE_URL,
        })
        
        text_content = strip_tags(html_content)
        
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[donation.user_email],
        )
        email.attach_alternative(html_content, "text/html")
        email.send()
        
        logger.info(f"Отправлено уведомление о возврате для доната {donation.id}")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка отправки уведомления о возврате: {str(e)}")
        return False


def send_test_email(recipient_email: str) -> bool:
    """
    Отправка тестового письма для проверки настроек
    
    :param recipient_email: Email получателя
    :return: True если отправлено успешно
    """
    try:
        subject = 'Тестовое письмо - IdealImage.ru Donations'
        message = 'Это тестовое письмо для проверки настроек email системы донатов.'
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient_email],
            fail_silently=False,
        )
        
        logger.info(f"Тестовое письмо отправлено на {recipient_email}")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка отправки тестового письма: {str(e)}")
        return False
