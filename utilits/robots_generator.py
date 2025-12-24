"""
Автоматический генератор robots.txt с учётом всех параметров
"""
import logging
from pathlib import Path
from django.conf import settings

logger = logging.getLogger(__name__)


class RobotsGenerator:
    """
    Генератор robots.txt с поддержкой Clean-param
    """
    
    # Незначащие GET-параметры для Clean-param
    CLEAN_PARAMS = [
        'next',
        'from', 
        'utm_source',
        'utm_medium',
        'utm_campaign',
        'utm_content',
        'utm_term',
        'fbclid',
        'gclid',
        'yclid',
        '_openstat',
        'ref',
        'referer',
        'source',
    ]
    
    # Disallow правила
    DISALLOW_RULES = [
        '/admin/',
        '/ckeditor/',
        '/visitor/login/',
        '/visitor/register/',
        '/search?',
        '/*?page=',
        '/media/uploads/',
    ]
    
    def generate(self):
        """
        Генерация содержимого robots.txt
        
        Returns:
            String с содержимым robots.txt
        """
        site_url = getattr(settings, 'SITE_URL', 'https://idealimage.ru')
        
        content = """User-agent: *
Allow: /
"""
        
        # Добавляем Disallow правила
        for rule in self.DISALLOW_RULES:
            content += f"Disallow: {rule}\n"
        
        content += "\n# Игнорирование незначащих GET-параметров\n"
        
        # Добавляем Clean-param правила
        for param in self.CLEAN_PARAMS:
            content += f"Clean-param: {param}\n"
        
        content += f"\nSitemap: {site_url}/sitemap.xml\n\n"
        
        # Специальные правила для разных ботов
        content += """User-agent: Googlebot
Crawl-delay: 0
Allow: /media/images/
Allow: /static/

User-agent: Yandex
Crawl-delay: 0
Host: idealimage.ru

User-agent: Googlebot-Image
Allow: /media/
"""
        
        return content
    
    def save_to_file(self, file_path=None):
        """
        Сохранение robots.txt в файл
        
        Args:
            file_path: Путь к файлу (по умолчанию BASE_DIR/robots.txt)
        
        Returns:
            Bool - успешность операции
        """
        if file_path is None:
            file_path = Path(settings.BASE_DIR) / 'robots.txt'
        
        try:
            content = self.generate()
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info(f"✅ robots.txt generated: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to generate robots.txt: {e}")
            return False
    
    def add_custom_disallow(self, url_pattern):
        """
        Добавление пользовательского Disallow правила
        
        Args:
            url_pattern: Паттерн URL для блокировки
        """
        if url_pattern not in self.DISALLOW_RULES:
            self.DISALLOW_RULES.append(url_pattern)
            logger.info(f"Added custom disallow rule: {url_pattern}")


def regenerate_robots_txt():
    """
    Функция для запуска через Django-Q или management command
    Перегенерирует robots.txt
    """
    generator = RobotsGenerator()
    return generator.save_to_file()

