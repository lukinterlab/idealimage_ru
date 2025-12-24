"""
WhatsApp Share - Генерация ссылок для кнопки "Поделиться в WhatsApp"
"""
import logging
from urllib.parse import quote
from django.conf import settings


logger = logging.getLogger(__name__)


class WhatsAppShare:
    """
    Генератор ссылок для кнопки "Поделиться в WhatsApp"
    Не требует API - работает через wa.me
    """
    
    @staticmethod
    def generate_share_link(post, custom_text=None):
        """
        Генерирует ссылку для шеринга статьи в WhatsApp
        
        Args:
            post: Объект blog.Post
            custom_text: Кастомный текст (иначе генерируется автоматически)
        
        Returns:
            str: URL для кнопки WhatsApp
        """
        if custom_text:
            text = custom_text
        else:
            # Формируем текст для шеринга
            article_url = f"{settings.SITE_URL}{post.get_absolute_url()}"
            text = f"{post.title}\n\n{article_url}"
        
        # URL-кодируем текст
        encoded_text = quote(text)
        
        # Генерируем ссылку wa.me
        whatsapp_url = f"https://wa.me/?text={encoded_text}"
        
        logger.info(f"[OK] WhatsApp share link сгенерирован для '{post.title}'")
        
        return whatsapp_url
    
    @staticmethod
    def get_share_button_html(post, css_classes=''):
        """
        Генерирует HTML для кнопки WhatsApp
        
        Args:
            post: Объект blog.Post
            css_classes: CSS классы для кнопки
        
        Returns:
            str: HTML код кнопки
        """
        share_url = WhatsAppShare.generate_share_link(post)
        
        button_html = f'''
<a href="{share_url}" 
   target="_blank" 
   rel="noopener noreferrer"
   class="whatsapp-share-button {css_classes}"
   title="Поделиться в WhatsApp">
    <i class="fab fa-whatsapp"></i> Поделиться
</a>
'''
        
        return button_html


def generate_whatsapp_link(post):
    """Convenience функция для генерации ссылки"""
    return WhatsAppShare.generate_share_link(post)

