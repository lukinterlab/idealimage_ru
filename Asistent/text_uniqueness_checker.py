"""
Проверка уникальности текста статей
Проверяет на дубли в базе и (опционально) в интернете
"""
import logging
from typing import Tuple, Dict
from django.utils.html import strip_tags
import re
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


class TextUniquenessChecker:
    """Проверка уникальности текста"""
    
    # Минимальная уникальность в процентах
    MIN_UNIQUENESS = 70
    
    # Минимальная длина текста для проверки (в символах)
    MIN_TEXT_LENGTH = 200
    
    def __init__(self):
        pass
    
    def check_uniqueness(self, post) -> Tuple[bool, float, str]:
        """
        Проверяет уникальность текста статьи
        
        Args:
            post: Объект статьи (Post model)
        
        Returns:
            Tuple (is_unique, uniqueness_percent, message)
        """
        logger.info(f"🔍 Проверка уникальности текста: {post.title}")
        
        # Получаем чистый текст
        clean_text = self._clean_text(post.content)
        
        # Проверяем минимальную длину
        if len(clean_text) < self.MIN_TEXT_LENGTH:
            return True, 100.0, "Текст слишком короткий для проверки"
        
        # Проверка 1: Дубли в базе данных
        db_uniqueness, db_message = self._check_database_duplicates(post, clean_text)
        
        if db_uniqueness < self.MIN_UNIQUENESS:
            return False, db_uniqueness, db_message
        
        # Проверка 2: Интернет (опционально, если есть API)
        # web_uniqueness = self._check_web_duplicates(clean_text)
        
        # Финальная оценка
        final_uniqueness = db_uniqueness
        
        if final_uniqueness >= self.MIN_UNIQUENESS:
            return True, final_uniqueness, f"Текст уникален ({final_uniqueness:.1f}%)"
        else:
            return False, final_uniqueness, f"Текст не уникален ({final_uniqueness:.1f}%)"
    
    def _clean_text(self, content: str) -> str:
        """Очищает текст от HTML и лишних символов"""
        # Удаляем HTML теги
        text = strip_tags(content)
        
        # Удаляем множественные пробелы
        text = re.sub(r'\s+', ' ', text)
        
        # Удаляем специальные символы но оставляем знаки препинания
        text = text.strip()
        
        return text
    
    def _check_database_duplicates(self, post, clean_text: str) -> Tuple[float, str]:
        """
        Проверяет на дубли в базе данных
        
        Returns:
            Tuple (uniqueness_percent, message)
        """
        try:
            from blog.models import Post
            
            # Получаем все опубликованные статьи кроме текущей
            other_posts = Post.objects.exclude(pk=post.pk if post.pk else None)
            other_posts = other_posts.filter(status='published')[:200]  # Последние 200
            
            max_similarity = 0.0
            most_similar_post = None
            
            for other_post in other_posts:
                # Получаем чистый текст другой статьи
                other_text = self._clean_text(other_post.content)
                
                # Вычисляем сходство
                similarity = self._calculate_similarity(clean_text, other_text)
                
                if similarity > max_similarity:
                    max_similarity = similarity
                    most_similar_post = other_post
                
                # Если найдено 100% совпадение - сразу возвращаем
                if similarity >= 0.99:
                    logger.warning(f"   ❌ ДУБЛИКАТ! Совпадение {similarity*100:.1f}% со статьей #{other_post.id}")
                    return 0.0, f"Дубликат статьи #{other_post.id} '{other_post.title}'"
            
            # Вычисляем уникальность (инверсия сходства)
            uniqueness = (1 - max_similarity) * 100
            
            if most_similar_post and max_similarity > 0.3:
                message = f"Наибольшее сходство {max_similarity*100:.1f}% со статьей #{most_similar_post.id}"
                logger.info(f"   📊 {message}")
            else:
                message = "Совпадений в базе не найдено"
                logger.info(f"   ✓ {message}")
            
            return uniqueness, message
            
        except Exception as e:
            logger.error(f"   ❌ Ошибка проверки базы данных: {e}")
            # В случае ошибки считаем уникальным
            return 100.0, f"Ошибка проверки: {str(e)}"
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """
        Вычисляет сходство двух текстов
        
        Returns:
            float от 0.0 (разные) до 1.0 (идентичные)
        """
        # Приводим к нижнему регистру
        text1_lower = text1.lower()
        text2_lower = text2.lower()
        
        # Метод 1: Быстрая проверка по первым символам
        if len(text1_lower) > 100 and len(text2_lower) > 100:
            first_chars_similarity = SequenceMatcher(
                None, 
                text1_lower[:100], 
                text2_lower[:100]
            ).ratio()
            
            # Если первые 100 символов сильно отличаются - тексты разные
            if first_chars_similarity < 0.3:
                return first_chars_similarity
        
        # Метод 2: Проверка по шинглам (n-граммы слов)
        similarity_shingles = self._shingle_similarity(text1_lower, text2_lower)
        
        # Метод 3: Общее сходство всего текста (для небольших текстов)
        if len(text1) < 1000 and len(text2) < 1000:
            similarity_full = SequenceMatcher(None, text1_lower, text2_lower).ratio()
            # Берем максимум из двух методов
            return max(similarity_shingles, similarity_full)
        
        return similarity_shingles
    
    def _shingle_similarity(self, text1: str, text2: str, n: int = 3) -> float:
        """
        Вычисляет сходство текстов методом шинглов (n-грамм слов)
        
        Args:
            text1, text2: Тексты для сравнения
            n: Размер шингла (количество слов)
        
        Returns:
            float от 0.0 до 1.0
        """
        # Разбиваем на слова
        words1 = text1.split()
        words2 = text2.split()
        
        if len(words1) < n or len(words2) < n:
            # Если текст слишком короткий, используем посимвольное сравнение
            return SequenceMatcher(None, text1, text2).ratio()
        
        # Создаем шинглы
        shingles1 = set(
            ' '.join(words1[i:i+n]) 
            for i in range(len(words1) - n + 1)
        )
        shingles2 = set(
            ' '.join(words2[i:i+n]) 
            for i in range(len(words2) - n + 1)
        )
        
        # Вычисляем коэффициент Жаккара
        if not shingles1 or not shingles2:
            return 0.0
        
        intersection = len(shingles1 & shingles2)
        union = len(shingles1 | shingles2)
        
        jaccard = intersection / union if union > 0 else 0.0
        
        return jaccard
    
    def _check_web_duplicates(self, text: str) -> float:
        """
        Проверяет текст на наличие в интернете (опционально)
        Требует API антиплагиата
        
        Returns:
            float уникальность от 0.0 до 100.0
        """
        # TODO: Интеграция с бесплатными API антиплагиата
        # Возможные варианты:
        # - text.ru API (бесплатный лимит)
        # - content-watch.ru API
        # - advego.com API
        
        logger.info(f"   ℹ️  Проверка в интернете пока не реализована")
        return 100.0


def check_text_uniqueness(post) -> Dict:
    """
    Удобная функция для быстрой проверки уникальности
    
    Args:
        post: Объект статьи
    
    Returns:
        Dict с результатами проверки
    """
    checker = TextUniquenessChecker()
    is_unique, uniqueness, message = checker.check_uniqueness(post)
    
    return {
        'is_unique': is_unique,
        'uniqueness_percent': uniqueness,
        'message': message,
        'min_required': checker.MIN_UNIQUENESS
    }

