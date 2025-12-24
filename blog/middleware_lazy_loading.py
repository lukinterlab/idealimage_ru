"""
Middleware для автоматического добавления lazy loading к изображениям
Улучшает Core Web Vitals (LCP, FID)
"""
import re
import logging
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)


class LazyLoadingMiddleware(MiddlewareMixin):
    """
    Автоматически добавляет loading="lazy" ко всем изображениям кроме первого
    Первое изображение не получает lazy loading для оптимизации LCP
    """
    
    def process_response(self, request, response):
        """
        Обрабатывает HTML ответ и добавляет lazy loading
        """
        # Обрабатываем только HTML ответы
        if not response.get('Content-Type', '').startswith('text/html'):
            return response
        
        # Получаем контент
        if hasattr(response, 'content'):
            content = response.content.decode('utf-8', errors='ignore')
            
            # Находим все img теги
            img_pattern = r'<img\s+([^>]*)>'
            img_tags = re.finditer(img_pattern, content, re.IGNORECASE)
            
            img_count = 0
            replacements = []
            
            for match in img_tags:
                img_count += 1
                img_attrs = match.group(1)
                
                # Пропускаем если уже есть loading атрибут
                if 'loading=' in img_attrs.lower():
                    continue
                
                # Первое изображение - без lazy loading (для LCP)
                if img_count == 1:
                    # Добавляем loading="eager" для первого изображения
                    new_attrs = img_attrs.rstrip() + ' loading="eager"'
                else:
                    # Остальные - lazy loading
                    new_attrs = img_attrs.rstrip() + ' loading="lazy"'
                
                # Заменяем
                old_tag = match.group(0)
                new_tag = f'<img {new_attrs}>'
                replacements.append((old_tag, new_tag))
            
            # Применяем замены
            for old_tag, new_tag in replacements:
                content = content.replace(old_tag, new_tag)
            
            # Обновляем ответ
            response.content = content.encode('utf-8')
            
            if img_count > 0:
                logger.debug(f"Добавлен lazy loading к {img_count} изображениям")
        
        return response

