"""
Анализ стиля написания статей на сайте
Извлекает паттерны: длина, структура, тон, эмодзи, заголовки
"""
import re
import logging
from typing import List, Dict
from django.db.models import QuerySet

logger = logging.getLogger(__name__)


class StyleAnalyzer:
    """Анализ стиля статей"""
    
    def analyze_posts(self, posts: QuerySet) -> str:
        """
        Анализирует стиль коллекции статей
        
        Args:
            posts: QuerySet с постами
        
        Returns:
            Строка с описанием стиля для промпта
        """
        logger.info(f"📖 Анализ стиля {posts.count()} статей...")
        
        if not posts.exists():
            return "Стиль: Дружелюбный, информативный, с эмодзи. Заголовки с цифрами."
        
        stats = {
            'word_counts': [],
            'has_emojis': 0,
            'has_lists': 0,
            'has_headings': 0,
            'has_images': 0,
            'avg_paragraph_length': [],
            'tone_indicators': {
                'friendly': 0,  # вы, ваш, друзья
                'formal': 0,    # необходимо, следует, рекомендуется
                'casual': 0,    # классно, круто, супер
            }
        }
        
        for post in posts:
            content = post.content
            
            # Подсчет слов
            words = len(content.split())
            stats['word_counts'].append(words)
            
            # Эмодзи
            emoji_pattern = re.compile(r'[\U0001F300-\U0001F9FF]|[\u2600-\u26FF]|[\u2700-\u27BF]')
            if emoji_pattern.search(content):
                stats['has_emojis'] += 1
            
            # Списки
            if '<ul>' in content or '<ol>' in content or re.search(r'^\d+\.', content, re.MULTILINE):
                stats['has_lists'] += 1
            
            # Заголовки
            if '<h2>' in content or '<h3>' in content:
                stats['has_headings'] += 1
            
            # Изображения
            if '<img' in content or hasattr(post, 'images') and post.images.exists():
                stats['has_images'] += 1
            
            # Длина параграфов
            paragraphs = re.findall(r'<p>(.+?)</p>', content)
            if paragraphs:
                avg_p_len = sum(len(p.split()) for p in paragraphs) / len(paragraphs)
                stats['avg_paragraph_length'].append(avg_p_len)
            
            # Тон
            content_lower = content.lower()
            if any(word in content_lower for word in ['вы', 'ваш', 'друзья', 'поделимся']):
                stats['tone_indicators']['friendly'] += 1
            if any(word in content_lower for word in ['необходимо', 'следует', 'рекомендуется', 'важно']):
                stats['tone_indicators']['formal'] += 1
            if any(word in content_lower for word in ['классно', 'круто', 'супер', 'обалдеть']):
                stats['tone_indicators']['casual'] += 1
        
        # Формируем описание стиля
        total = posts.count()
        
        # Средняя длина
        avg_words = sum(stats['word_counts']) / len(stats['word_counts']) if stats['word_counts'] else 800
        
        # Тон
        tone_scores = stats['tone_indicators']
        dominant_tone = max(tone_scores, key=tone_scores.get)
        tone_map = {
            'friendly': 'дружелюбный, обращение на "вы"',
            'formal': 'формальный, экспертный',
            'casual': 'неформальный, разговорный'
        }
        tone_desc = tone_map.get(dominant_tone, 'нейтральный')
        
        # Структурные элементы
        structural_features = []
        if stats['has_emojis'] > total * 0.5:
            structural_features.append("эмодзи в заголовках и тексте")
        if stats['has_lists'] > total * 0.6:
            structural_features.append("нумерованные списки и буллиты")
        if stats['has_headings'] > total * 0.7:
            structural_features.append("подзаголовки H2, H3")
        if stats['has_images'] > total * 0.5:
            structural_features.append("иллюстрации и фото")
        
        # Средняя длина параграфа
        avg_p = sum(stats['avg_paragraph_length']) / len(stats['avg_paragraph_length']) if stats['avg_paragraph_length'] else 40
        paragraph_style = "короткие параграфы (2-3 предложения)" if avg_p < 50 else "средние параграфы (4-6 предложений)"
        
        # Итоговое описание
        style_guide = f"""Стиль сайта (на основе {total} статей):

📊 СТРУКТУРА:
- Длина: {int(avg_words)} слов ({int(avg_words * 0.8)}-{int(avg_words * 1.2)} диапазон)
- Параграфы: {paragraph_style}
- Элементы: {', '.join(structural_features) if structural_features else 'простой текст'}

🎭 ТОН:
- {tone_desc.capitalize()}
- Читателю: обращение на "вы", личные обращения
- Стиль: информативный с практическими советами

📝 ОФОРМЛЕНИЕ:
- Заголовки: {"с эмодзи" if stats['has_emojis'] > total * 0.5 else "без эмодзи"}
- Списки: {"часто используются" if stats['has_lists'] > total * 0.5 else "редко"}
- Выделения: цитаты, blockquote для важных мыслей

✅ РЕКОМЕНДАЦИИ:
- Используй структуру как в примерах выше
- Сохраняй дружелюбный но экспертный тон
- Добавляй практические советы и примеры
- Пиши живым русским языком без штампов"""
        
        logger.info(f"✅ Анализ завершён: {int(avg_words)} слов, тон={dominant_tone}")
        
        return style_guide
    
    def analyze_author_style(self, author, limit=10):
        """
        Анализирует стиль конкретного автора
        
        Args:
            author: Объект User (автор)
            limit: Количество последних статей для анализа
        
        Returns:
            Dict с анализом стиля автора
        """
        from blog.models import Post
        
        logger.info(f"🔍 Анализ стиля автора: {author.username}")
        
        # Получаем последние статьи автора
        posts = Post.objects.filter(
            author=author,
            status='published'
        ).order_by('-created')[:limit]
        
        if not posts.exists():
            logger.warning(f"⚠️ У автора {author.username} нет опубликованных статей")
            return {
                'style_description': 'Стиль: информативный, дружелюбный, с практическими советами',
                'avg_word_count': 1000,
                'tone': 'friendly',
                'use_emojis': True,
                'use_lists': True
            }
        
        # Используем существующий метод analyze_posts
        style_guide = self.analyze_posts(posts)
        
        # Возвращаем в формате словаря для использования в промпте
        return {
            'style_description': style_guide,
            'author_name': author.username,
            'analyzed_posts_count': posts.count()
        }