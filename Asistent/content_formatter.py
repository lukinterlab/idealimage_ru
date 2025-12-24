"""
Форматирование контента для CKEditor
"""
import re
import logging

logger = logging.getLogger(__name__)


"""Форматирование HTML контента для красивого отображения в CKEditor"""
class CKEditorFormatter:
    """Форматирование HTML контента для красивого отображения в CKEditor"""
    
    def format_content(self, html_content):
        """
        Форматирует HTML контент для CKEditor
        Оставляет чистую HTML разметку БЕЗ инлайн стилей
        
        Args:
            html_content: HTML контент от AI
        
        Returns:
            Чистый HTML с правильной структурой
        """
        logger.info("🎨 Форматирование контента для CKEditor...")
        
        # Удаляем лишние пробелы и переносы
        content = self._clean_content(html_content)
        
        # ВАЖНО: Конвертируем Markdown в HTML (если GigaChat вернул Markdown)
        content = self._convert_markdown_to_html(content)
        
        # Удаляем любые инлайн стили если AI добавил
        content = self._remove_inline_styles(content)
        
        # Добавляем пустые строки между блоками для читаемости
        content = self._add_spacing_simple(content)
        
        # Форматируем структуру (переносы строк)
        content = self._format_structure(content)
        
        logger.info(f"✅ Контент отформатирован ({len(content)} символов)")
        logger.info(f"   • Чистая HTML разметка без стилей")
        logger.info(f"   • Правильная структура с отступами")
        
        return content
    
    """Очищает контент от лишних пробелов"""
    def _clean_content(self, content):
        """Очищает контент от лишних пробелов"""
        # Нормализуем пробелы внутри текста
        content = re.sub(r'\s+', ' ', content)
        return content.strip()
    
    """Конвертирует Markdown в HTML (если GigaChat вернул Markdown)"""
    def _convert_markdown_to_html(self, content):
        """
        Конвертирует Markdown в HTML (если GigaChat вернул Markdown)
        """
        logger.info("   🔄 Проверка и конвертация Markdown в HTML...")
        html = render_markdown(content, preset=MarkdownPreset.CONTENT)
        logger.info("      ✓ Markdown конвертирован в HTML")
        return html
    
    """Удаляет все инлайн стили из HTML"""
    def _remove_inline_styles(self, content):
        """
        Удаляет все инлайн стили из HTML
        """
        # Удаляем атрибуты style=""
        content = re.sub(r'\s+style="[^"]*"', '', content)
        # Удаляем пустые атрибуты
        content = re.sub(r'\s+style=\'[^\']*\'', '', content)
        return content
    
    """Добавляет пустые строки между основными блоками"""
    def _add_spacing_simple(self, content):
        """
        Добавляет пустые строки между основными блоками
        Простая версия без CSS стилей
        """
        # Пустая строка перед H2 (если это не первый заголовок)
        parts = content.split('<h2>')
        if len(parts) > 1:
            content = parts[0] + '\n\n<h2>' + '\n\n<h2>'.join(parts[1:])
        
        # Пустая строка перед H3
        content = re.sub(r'<h3>', r'\n\n<h3>', content)
        
        # Пустая строка перед списками
        content = re.sub(r'<ul>', r'\n\n<ul>', content)
        content = re.sub(r'<ol>', r'\n\n<ol>', content)
        
        # Пустая строка перед blockquote
        content = re.sub(r'<blockquote>', r'\n\n<blockquote>', content)
        
        return content
    
    """Форматирует структуру HTML для читаемости в коде"""
    def _format_structure(self, content):
        """
        Форматирует структуру HTML для читаемости в коде
        """
        # Добавляем переносы строк после закрывающих тегов
        content = re.sub(r'</h2>', r'</h2>\n\n', content)
        content = re.sub(r'</h3>', r'</h3>\n\n', content)
        content = re.sub(r'</p>', r'</p>\n\n', content)
        content = re.sub(r'</ul>', r'</ul>\n\n', content)
        content = re.sub(r'</ol>', r'</ol>\n\n', content)
        content = re.sub(r'</blockquote>', r'</blockquote>\n\n', content)
        
        # Переносы внутри списков
        content = re.sub(r'</li>', r'</li>\n', content)
        content = re.sub(r'<li>', r'<li>', content)
        
        # Удаляем лишние множественные переносы
        content = re.sub(r'\n\n\n+', r'\n\n', content)
        
        return content.strip()
    
    """Добавляет оглавление статьи (опционально)"""
    def add_table_of_contents(self, content, title):
        """
        Добавляет оглавление статьи (опционально)
        
        Args:
            content: HTML контент
            title: Заголовок статьи
        
        Returns:
            Контент с оглавлением
        """
        # Извлекаем все заголовки H2 и H3
        headings = re.findall(r'<h[23].*?>(.*?)</h[23]>', content, re.IGNORECASE)
        
        if len(headings) < 3:
            # Если мало заголовков - не добавляем оглавление
            return content
        
        # Создаем оглавление
        toc_items = []
        for i, heading in enumerate(headings[:6], 1):  # Максимум 6 пунктов
            # Убираем HTML теги и эмодзи из заголовка
            clean_heading = re.sub(r'<.*?>', '', heading)
            clean_heading = re.sub(r'[🌟💡✨💫⭐️🎯❤️💪👍🔥💎🎨📚🌺🌸]', '', clean_heading).strip()
            
            if len(clean_heading) > 3:
                toc_items.append(f'<li style="margin-bottom: 5px;"><strong>{i}.</strong> {clean_heading}</li>')
        
        toc_html = f'''
            <div style="background-color: #f3e5f5; padding: 20px; border-radius: 10px; margin: 20px 0; border: 2px solid #e1bee7;">
                <h3 style="color: #9c27b0; margin-top: 0; font-size: 20px;">📋 Содержание статьи</h3>
                <ul style="list-style: none; padding-left: 10px; margin-bottom: 0;">
                    {''.join(toc_items)}
                </ul>
            </div>
            <p>&nbsp;</p>
            '''
        
        # Вставляем оглавление после первого абзаца
        first_p_end = content.find('</p>')
        if first_p_end != -1:
            content = content[:first_p_end + 4] + toc_html + content[first_p_end + 4:]
        
        return content


"""Главная функция для форматирования контента"""
def format_for_ckeditor(html_content, title=""):
    """
    Главная функция для форматирования контента
    Возвращает чистый HTML БЕЗ инлайн стилей
    
    Args:
        html_content: HTML от AI
        title: Заголовок статьи
    
    Returns:
        Чистый HTML с правильной структурой
    """
    formatter = CKEditorFormatter()
    
    # Форматирование: чистый HTML, без стилей
    content = formatter.format_content(html_content)
    
    # НЕ добавляем стили - оставляем чистый HTML
    # Стили будут применены через CSS сайта
    
    return content



"""Встраивает видео в HTML контент статьи"""
def embed_video_content(content, video_data, position='end'):
    """
    Встраивает видео в HTML контент статьи
    
    Args:
        content: HTML контент статьи
        video_data: Dict с данными видео (platform, embed_url, title, thumbnail)
        position: Позиция вставки ('start', 'end', 'middle')
    
    Returns:
        Контент с встроенным видео
    """
    platform = video_data.get('platform', 'youtube')
    embed_url = video_data.get('embed_url', '')
    title = video_data.get('title', '')
    
    if not embed_url:
        return content
    
    # Создаем responsive iframe обертку
    video_html = f'''
        <div class="video-embed-container" style="position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden; max-width: 100%; margin: 2em 0;">
            <iframe 
                src="{embed_url}" 
                title="{title}" 
                style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; border: 0;"
                frameborder="0" 
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" 
                allowfullscreen>
            </iframe>
        </div>
        <p class="video-caption" style="text-align: center; color: #666; font-size: 0.9em; margin-top: -1.5em; margin-bottom: 2em;">
            <em>📹 Видео по теме: {title}</em>
        </p>
        '''
    
    # Вставляем видео в зависимости от позиции
    if position == 'start':
        # После первого заголовка h2
        if '<h2>' in content:
            parts = content.split('<h2>', 1)
            return parts[0] + video_html + '<h2>' + parts[1]
        else:
            return video_html + content
    
    elif position == 'middle':
        # В середине статьи
        paragraphs = content.split('</p>')
        middle = len(paragraphs) // 2
        paragraphs.insert(middle, video_html)
        return '</p>'.join(paragraphs)
    
    else:  # end
        # Перед заключением или в конец
        if '<h2>✨ Заключение</h2>' in content:
            return content.replace('<h2>✨ Заключение</h2>', video_html + '<h2>✨ Заключение</h2>')
        else:
            return content + video_html


"""Встраивает галерею изображений из Pinterest"""
def embed_pinterest_gallery(content, pinterest_pins, max_images=6):
    """
    Встраивает галерею изображений из Pinterest
    
    Args:
        content: HTML контент
        pinterest_pins: List пинов с image_url
        max_images: Максимальное количество изображений
    
    Returns:
        Контент с галереей
    """
    if not pinterest_pins:
        return content
    
    gallery_html = '<div class="pinterest-gallery" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1em; margin: 2em 0;">\n'
    
    for pin in pinterest_pins[:max_images]:
        image_url = pin.get('image_url', '')
        pin_url = pin.get('pin_url', '')
        pin_title = pin.get('title', 'Изображение с Pinterest')
        
        if image_url:
            gallery_html += f'''<div class="pinterest-pin" style="position: relative; overflow: hidden; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                                    <a href="{pin_url}" target="_blank" rel="noopener">
                                        <img src="{image_url}" alt="{pin_title}" style="width: 100%; height: auto; display: block; transition: transform 0.3s;" onmouseover="this.style.transform='scale(1.05)'" onmouseout="this.style.transform='scale(1)'">
                                    </a>
                                </div>
                            '''
    
    gallery_html += '</div>\n<p style="text-align: center; color: #666; font-size: 0.9em; margin-top: -1em;"><em>📌 Изображения из Pinterest</em></p>\n'
    
    # Вставляем галерею перед заключением
    if '<h2>✨ Заключение</h2>' in content:
        return content.replace('<h2>✨ Заключение</h2>', gallery_html + '<h2>✨ Заключение</h2>')
    else:
        return content + gallery_html


"""Встраивает пост из Telegram"""
def embed_telegram_post(content, post_url):
    """
    Встраивает пост из Telegram
    
    Args:
        content: HTML контент
        post_url: URL поста в Telegram
    
    Returns:
        Контент с встроенным постом
    """
    if not post_url or 't.me' not in post_url:
        return content
    
    # Telegram embed widget
    telegram_html = f'''
                    <div class="telegram-embed" style="max-width: 600px; margin: 2em auto;">
                        <script async src="https://telegram.org/js/telegram-widget.js?22" 
                                data-telegram-post="{post_url.replace('https://t.me/', '')}" 
                                data-width="100%">
                        </script>
                    </div>
                    <p style="text-align: center; color: #666; font-size: 0.9em;"><em>💬 Обсуждение в Telegram</em></p>
                    '''
    
    return content + telegram_html

