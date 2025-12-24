"""
Проверка и очистка текста от мата и ненормативной лексики
"""
import re
import logging
from typing import Tuple, List
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)


class ProfanityChecker:
    """Проверка текста на мат и ненормативную лексику"""
    
    # Базовый список ненормативной лексики
    # ВНИМАНИЕ: Содержит реальный мат для фильтрации
    PROFANITY_WORDS = [
        # Оскорбления
        'дурак', 'идиот', 'дебил', 'тупой', 'кретин',
        'сволочь', 'скотина', 'мразь', 'гнида', 'подонок',
        
        # РЕАЛЬНЫЙ русский мат
        'хуй', 'хуя', 'хуе', 'хуи', 'хую', 'хуем', 'хуев', 'хуевый', 'хуевая', 'хуёво',
        'пизда', 'пизде', 'пизду', 'пизды', 'пиздой', 'пиздец', 'пиздеть', 'пиздят',
        'ебать', 'ебал', 'ебала', 'ебут', 'ебёт', 'ебёшь', 'ебёте',
        'ебан', 'ебаный', 'ебанный', 'ебанутый', 'ёбаный', 'ёбанный', 'ёбанная', 'ёбаные', 'ёбанные',
        'ебля', 'ёбля', 'ебло', 'ебальник',
        'заебал', 'заебала', 'заебали', 'заебись', 'заебато',
        'наебал', 'наебала', 'наебать', 'наебнуться',
        'проебал', 'проебала', 'проебать',
        'охуел', 'охуела', 'охуеть', 'охуенно', 'охуительно',
        'блять', 'блядь', 'блядина', 'блядство', 'бляди', 'блядей', 'блядский',
        'бля', 'бляха', 'бляшка',
        'сука', 'суки', 'суку', 'сукой', 'сукам', 'сучка', 'сучки',
        
        # Варианты написания (латиница)
        'xyй', 'xуй', 'хyй', 'xer',
        
        # НЕ добавляйте: 'ад', 'гад', 'зараза', 'хрен', 'чёрт' - это НЕ мат!
    ]
    
    # Варианты написания через звездочки, дефисы и т.д.
    OBFUSCATION_PATTERNS = [
        r'(\w)[*]+(\w)',  # х*н
        r'(\w)[-]+(\w)',  # х-рен
        r'(\w)[.]+(\w)',  # х.рен
        r'(\w)\s+(\w)',   # х рен (с пробелом)
    ]
    
    def __init__(self):
        # Загружаем дополнительные слова из базы знаний AI
        self.profanity_list = self._load_profanity_list()
    
    def check_text(self, text: str) -> Tuple[bool, List[str]]:
        """
        Проверяет текст на наличие мата
        
        Args:
            text: Текст для проверки
        
        Returns:
            Tuple (has_profanity, list_of_found_words)
        """
        if not text:
            return False, []
        
        # Очищаем от HTML
        clean_text = strip_tags(text).lower()
        
        found_words = []
        
        # Проверяем каждое слово из списка
        for word in self.profanity_list:
            # ВАЖНО: Ищем ТОЛЬКО ПОЛНЫЕ СЛОВА с границами \b (не части слов!)
            # Минимум 3 символа чтобы избежать ложных срабатываний на части слов
            if len(word) < 3:
                continue
                
            # Ищем точное совпадение слова (с границами слов)
            pattern = r'\b' + re.escape(word.lower()) + r'\b'
            if re.search(pattern, clean_text, re.IGNORECASE):
                if word not in found_words:
                    found_words.append(word)
        
        # Проверяем обфусцированные варианты
        for pattern in self.OBFUSCATION_PATTERNS:
            matches = re.findall(pattern, clean_text)
            for match in matches:
                potential_word = ''.join(match)
                
                # Пропускаем слишком короткие части (< 3 символов)
                if len(potential_word) < 3:
                    continue
                
                # Проверяем похожесть на мат
                for profanity in self.profanity_list:
                    # Проверяем только с полными словами (не короче 3 символов)
                    if len(profanity) < 3:
                        continue
                        
                    if self._is_similar(potential_word, profanity):
                        if potential_word not in found_words:
                            found_words.append(potential_word)
        
        has_profanity = len(found_words) > 0
        
        if has_profanity:
            logger.warning(f"Найден мат в тексте: {found_words}")
        
        return has_profanity, found_words
    
    def clean_text(self, text: str) -> Tuple[str, List[str]]:
        """
        Очищает текст от мата (УДАЛЯЕТ слова полностью)
        
        Args:
            text: Исходный текст (может содержать HTML)
        
        Returns:
            Tuple (cleaned_text, list_of_removed_words)
        """
        if not text:
            return text, []
        
        # ВАЖНО: Сначала убираем HTML, потом чистим, потом возвращаем HTML структуру
        from bs4 import BeautifulSoup
        
        cleaned_text = text
        removed_words = []
        
        # Проверяем наличие мата
        has_profanity, found_words = self.check_text(text)
        
        if not has_profanity:
            return text, []
        
        # Если есть HTML - работаем с текстом без тегов
        try:
            soup = BeautifulSoup(text, 'html.parser')
            has_html = bool(soup.find())
            
            if has_html:
                # Работаем с каждым текстовым узлом отдельно
                for element in soup.find_all(string=True):
                    original_text = str(element)
                    cleaned_element = original_text
                    
                    # УДАЛЯЕМ каждое матерное слово из этого узла
                    for word in found_words:
                        # Удаляем слово вместе с пробелами вокруг
                        pattern = r'\s*\b' + re.escape(word) + r'\b\s*'
                        cleaned_element = re.sub(pattern, ' ', cleaned_element, flags=re.IGNORECASE)
                    
                    # Убираем множественные пробелы
                    cleaned_element = re.sub(r'\s+', ' ', cleaned_element).strip()
                    
                    # Если текст изменился - заменяем
                    if cleaned_element != original_text:
                        element.replace_with(cleaned_element)
                        for word in found_words:
                            if word not in removed_words:
                                removed_words.append(word)
                
                cleaned_text = str(soup)
            else:
                # Нет HTML - работаем как раньше
                for word in found_words:
                    # Удаляем слово вместе с пробелами вокруг
                    pattern = r'\s*\b' + re.escape(word) + r'\b\s*'
                    cleaned_text = re.sub(pattern, ' ', cleaned_text, flags=re.IGNORECASE)
                    removed_words.append(word)
                
                # Убираем множественные пробелы
                cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()
        
        except Exception as e:
            logger.error(f"Ошибка очистки HTML: {e}")
            # Fallback - простое удаление без учета HTML
            for word in found_words:
                pattern = r'\s*\b' + re.escape(word) + r'\b\s*'
                cleaned_text = re.sub(pattern, ' ', cleaned_text, flags=re.IGNORECASE)
                removed_words.append(word)
            
            # Убираем множественные пробелы
            cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()
        
        logger.info(f"УДАЛЕНО {len(removed_words)} матерных слов из текста")
        
        return cleaned_text, removed_words
    
    def _censor_word(self, word: str) -> str:
        """
        Цензурирует слово (заменяет на звездочки)
        
        Args:
            word: Матерное слово
        
        Returns:
            Цензурированная версия
        """
        if len(word) <= 2:
            return '*' * len(word)
        
        # Оставляем первую и последнюю букву, остальное звездочки
        return word[0] + '*' * (len(word) - 2) + word[-1]
    
    def _is_similar(self, word1: str, word2: str, threshold: float = 0.7) -> bool:
        """Проверяет похожесть двух слов (для обфусцированных вариантов)"""
        from difflib import SequenceMatcher
        
        similarity = SequenceMatcher(None, word1.lower(), word2.lower()).ratio()
        return similarity >= threshold
    
    def _load_profanity_list(self) -> List[str]:
        """Загружает список мата ТОЛЬКО из локального списка PROFANITY_WORDS"""
        profanity_list = list(self.PROFANITY_WORDS)
        
        # ВАЖНО: НЕ загружаем из базы знаний!
        # База знаний содержит объяснения и примеры, а не только список мата
        # Это приводило к ложным срабатываниям на части слов типа "хи", "уи"
        
        logger.info(f"Загружено {len(profanity_list)} матерных слов из локального списка")
        
        return profanity_list


def check_profanity(text: str) -> dict:
    """
    Удобная функция для быстрой проверки
    
    Args:
        text: Текст для проверки
    
    Returns:
        Dict с результатами
    """
    checker = ProfanityChecker()
    has_profanity, found_words = checker.check_text(text)
    
    return {
        'has_profanity': has_profanity,
        'found_words': found_words,
        'count': len(found_words)
    }


def clean_profanity(text: str) -> dict:
    """
    Удобная функция для очистки текста
    
    Args:
        text: Текст для очистки
    
    Returns:
        Dict с результатами
    """
    checker = ProfanityChecker()
    cleaned_text, removed_words = checker.clean_text(text)
    
    return {
        'cleaned_text': cleaned_text,
        'removed_words': removed_words,
        'count': len(removed_words),
        'was_cleaned': len(removed_words) > 0
    }

