"""
Модели: AIKnowledgeBase
"""
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal

class AIKnowledgeBase(models.Model):
    
    CATEGORY_CHOICES = [
        ('промпты', 'Промпты'),
        ('правила', 'Правила'),
        ('примеры', 'Примеры'),
        ('команды', 'Команды'),
        ('faq', 'Частые вопросы'),
        ('инструкции', 'Инструкции'),
        ('источники', 'Источники'),  # Предпочтительные источники для парсинга
    ]
    
    category = models.CharField(
        max_length=100,
        choices=CATEGORY_CHOICES,
        verbose_name='Категория'
    )
    
    title = models.CharField(
        max_length=300,
        verbose_name='Заголовок'
    )
    
    content = models.TextField(
        verbose_name='Содержание'
    )
    
    tags = models.JSONField(
        default=list,
        verbose_name='Теги',
        help_text='Список тегов для поиска'
    )
    
    embedding = models.JSONField(
        null=True,
        blank=True,
        verbose_name='Векторное представление',
        help_text='Для семантического поиска (опционально)'
    )
    
    is_active = models.BooleanField(
        default=True,
        verbose_name='Активен'
    )
    
    usage_count = models.IntegerField(
        default=0,
        verbose_name='Количество использований'
    )
    
    priority = models.IntegerField(
        default=50,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name='Приоритет',
        help_text='0-100, чем выше - тем важнее (используется первым)'
    )
    
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='knowledge_entries',
        verbose_name='Создал'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Дата обновления'
    )
    
    class Meta:
        verbose_name = '🤖 AI-Агент: База знаний'
        verbose_name_plural = '🤖 AI-Агент: База знаний'
        ordering = ['-priority', '-usage_count', '-created_at']  # Сначала по приоритету
        indexes = [
            models.Index(fields=['category', '-priority'], name='kb_cat_prior_idx'),
            models.Index(fields=['-usage_count'], name='kb_usage_idx'),
            models.Index(fields=['is_active', 'category'], name='kb_active_cat_idx'),
            models.Index(fields=['-created_at'], name='kb_created_idx'),
        ]
    
    def __str__(self):
        return f"{self.get_category_display()}: {self.title}"
    
    def increment_usage(self):
        """Увеличить счетчик использований"""
        self.usage_count += 1
        self.save(update_fields=['usage_count'])
    
    @staticmethod
    def find_similar(query_text, top_k=5, category=None, min_similarity=0.0):
        """
        Находит топ-K наиболее похожих записей по векторному сходству
        
        Args:
            query_text: Текст запроса для поиска
            top_k: Количество результатов (по умолчанию 5)
            category: Фильтр по категории (опционально)
            min_similarity: Минимальный порог сходства (0.0-1.0)
            
        Returns:
            List[Tuple[AIKnowledgeBase, float]]: Список кортежей (запись, схожесть)
            
        Example:
            >>> results = AIKnowledgeBase.find_similar("Как стать автором?", top_k=3)
            >>> for item, similarity in results:
            ...     print(f"{item.title}: {similarity:.2%}")
        """
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            # Генерируем embedding запроса
            from .gigachat_api import get_embeddings
            import numpy as np
            
            query_embedding = np.array(get_embeddings(query_text))
            
            if len(query_embedding) == 0:
                logger.warning("Не удалось получить embedding для запроса, используем текстовый поиск")
                # Fallback на текстовый поиск
                return AIKnowledgeBase._fallback_text_search(query_text, top_k, category)
            
            # Получаем все активные записи с embeddings
            items = AIKnowledgeBase.objects.filter(
                is_active=True,
                embedding__isnull=False
            ).exclude(embedding=[])
            
            if category:
                items = items.filter(category=category)
            
            similarities = []
            
            for item in items:
                try:
                    item_embedding = np.array(item.embedding)
                    
                    # Проверяем размерность векторов
                    if item_embedding.shape != query_embedding.shape:
                        continue
                    
                    # Косинусная близость = dot(A, B) / (norm(A) * norm(B))
                    dot_product = np.dot(query_embedding, item_embedding)
                    norm_query = np.linalg.norm(query_embedding)
                    norm_item = np.linalg.norm(item_embedding)
                    
                    if norm_query == 0 or norm_item == 0:
                        continue
                    
                    similarity = dot_product / (norm_query * norm_item)
                    
                    # Фильтруем по минимальному порогу
                    if similarity >= min_similarity:
                        similarities.append((item, float(similarity)))
                        
                except Exception as e:
                    logger.warning(f"Ошибка расчёта similarity для {item.id}: {e}")
                    continue
            
            # Сортируем по убыванию схожести
            similarities.sort(key=lambda x: x[1], reverse=True)
            
            # Увеличиваем счётчик использований для найденных записей
            for item, _ in similarities[:top_k]:
                item.increment_usage()
            
            logger.info(f"✅ Найдено {len(similarities[:top_k])} похожих записей")
            return similarities[:top_k]
            
        except ImportError as e:
            logger.error(f"Ошибка импорта numpy: {e}. Установите: pip install numpy")
            return AIKnowledgeBase._fallback_text_search(query_text, top_k, category)
            
        except Exception as e:
            logger.error(f"Ошибка векторного поиска: {e}")
            return AIKnowledgeBase._fallback_text_search(query_text, top_k, category)
    
    @staticmethod
    def _fallback_text_search(query_text, top_k=5, category=None):
        """
        Резервный текстовый поиск при недоступности векторного
        
        Args:
            query_text: Текст запроса
            top_k: Количество результатов
            category: Фильтр по категории
            
        Returns:
            List[Tuple[AIKnowledgeBase, float]]: Список с фиктивным similarity=0.5
        """
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info("🔍 Используем текстовый fallback поиск")
        
        words = query_text.lower().split()
        items = AIKnowledgeBase.objects.filter(is_active=True)
        
        if category:
            items = items.filter(category=category)
        
        results = []
        for item in items:
            # Простой подсчёт совпадений слов в title, content И тегах
            text = f"{item.title} {item.content}".lower()
            
            # Добавляем теги к тексту поиска
            if hasattr(item, 'tags') and item.tags:
                tags_text = " ".join(str(tag) for tag in item.tags)
                text += " " + tags_text.lower()
            
            matches = sum(1 for word in words if word in text)
            
            if matches > 0:
                # Фиктивная схожесть на основе количества совпадений
                similarity = min(matches / len(words), 1.0)
                results.append((item, similarity))
        
        results.sort(key=lambda x: x[1], reverse=True)
        
        # Увеличиваем счётчик использований
        for item, _ in results[:top_k]:
            item.increment_usage()
        
        return results[:top_k]



