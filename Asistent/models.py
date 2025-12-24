"""
Модели для приложения AI-Ассистент
"""
from doctest import debug_script
from decimal import Decimal
from datetime import datetime, timedelta
from typing import Optional

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
import json

# ПРИМЕЧАНИЕ: Модели AISchedule и AIScheduleRun теперь в schedule/models.py
# Импортировать их напрямую НЕЛЬЗЯ - циклический импорт!
# Используйте: from Asistent.schedule.models import AISchedule
# Или: from Asistent.models import AISchedule (через __getattr__ в конце файла)


"""Задания для авторов от администратора"""
class ContentTask(models.Model):
    
    STATUS_CHOICES = [
        ('available', 'Доступно'),
        ('active', 'Активно'),
        ('completed', 'Завершено'),
        ('cancelled', 'Отменено'),
    ]
    
    title = models.CharField(max_length=300, verbose_name="Название задания")
    description = models.TextField(verbose_name="Описание задания")
    category = models.ForeignKey('blog.Category', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Категория")
    tags = models.CharField(max_length=500, blank=True, verbose_name="Теги (через запятую)")
    deadline = models.DateTimeField(verbose_name="Срок выполнения")
    required_word_count = models.IntegerField(validators=[MinValueValidator(100)], verbose_name="Минимальное количество слов")
    required_links = models.TextField(blank=True, verbose_name="Обязательные ссылки (по одной на строке)")
    required_keywords = models.TextField(blank=True, verbose_name="Ключевые фразы (по одной на строке)")
    reward = models.DecimalField(max_digits=10, decimal_places=2, default=100.00, verbose_name="Вознаграждение (руб.)")
    max_completions = models.IntegerField(default=1, validators=[MinValueValidator(1)], verbose_name="Лимит выполнений", help_text="Сколько авторов могут выполнить это задание")
    task_criteria = models.JSONField(default=dict, verbose_name="Специфические критерии для статьи", help_text="Особые требования к статье (имеют приоритет над общими критериями)")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available', verbose_name="Статус")
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_tasks', verbose_name="Создал")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")
    
    class Meta:
        verbose_name = "📋 Задания: Задание"
        verbose_name_plural = "📋 Задания: Задания"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"
    
    def get_assignments(self):
        """Получить все назначения"""
        return self.assignments.all()
    
    def get_completions_count(self):
        """Сколько раз выполнено"""
        return self.assignments.filter(status='approved').count()
    
    def can_be_taken(self, user):
        """Может ли пользователь взять задание"""
        # Проверка просрочки
        if timezone.now() > self.deadline:
            return False, "Срок выполнения истёк"
        
        # Проверка статуса
        if self.status == 'cancelled':
            return False, "Задание отменено"
        
        # Проверка что автор не отклонил
        if AuthorTaskRejection.objects.filter(author=user, task=self).exists():
            return False, "Вы отклонили это задание"
        
        # Проверка что автор еще не взял
        if self.assignments.filter(author=user).exists():
            return False, "Вы уже взяли это задание"
        
        # Проверка лимита выполнений
        if self.get_completions_count() >= self.max_completions:
            return False, "Достигнут лимит выполнений"
        
        return True, "OK"
    
    def is_closed(self):
        """Закрыто ли задание"""
        if self.status == 'cancelled':
            return True
        if timezone.now() > self.deadline:
            return True
        if self.get_completions_count() >= self.max_completions:
            return True
        return False
    
    @property
    def is_overdue(self):
        """Проверка просрочки"""
        return timezone.now() > self.deadline and self.status not in ['completed', 'cancelled']
    
    def get_task_criteria_as_text(self):
        """Преобразует специфические критерии задания в текст"""
        if not self.task_criteria:
            return ""
        
        criteria_text = []
        
        if 'min_length' in self.task_criteria:
            criteria_text.append(f"Минимальная длина: {self.task_criteria['min_length']} символов")
        
        if 'max_length' in self.task_criteria:
            criteria_text.append(f"Максимальная длина: {self.task_criteria['max_length']} символов")
        
        if 'required_keywords' in self.task_criteria:
            keywords = ', '.join(self.task_criteria['required_keywords'])
            criteria_text.append(f"Обязательные ключевые слова: {keywords}")
        
        if 'forbidden_words' in self.task_criteria:
            words = ', '.join(self.task_criteria['forbidden_words'])
            criteria_text.append(f"Запрещённые слова: {words}")
        
        if 'tone' in self.task_criteria:
            criteria_text.append(f"Требуемый тон: {self.task_criteria['tone']}")
        
        if 'structure' in self.task_criteria:
            criteria_text.append(f"Структура: {self.task_criteria['structure']}")
        
        if 'additional_rules' in self.task_criteria:
            criteria_text.append(f"Дополнительно: {self.task_criteria['additional_rules']}")
        
        return '\n'.join(criteria_text)

"""Связь автора с заданием (многие-ко-многим)"""
class TaskAssignment(models.Model):
    
    STATUS_CHOICES = [
        ('in_progress', 'В работе'),
        ('completed', 'Выполнено'),
        ('rejected_by_author', 'Отклонено автором'),
        ('rejected_by_ai', 'Отклонено AI'),
        ('approved', 'Одобрено'),
    ]
    
    task = models.ForeignKey('Asistent.ContentTask', on_delete=models.CASCADE, related_name='assignments', verbose_name="Задание")
    author = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='task_assignments', verbose_name="Автор")
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='in_progress', verbose_name="Статус")
    article = models.ForeignKey('blog.Post', on_delete=models.SET_NULL, null=True, blank=True, related_name='task_assignment', verbose_name="Статья")
    submitted_at = models.DateTimeField(null=True, blank=True, verbose_name="Дата сдачи")
    ai_moderation_result = models.JSONField(default=dict, verbose_name="Результат AI модерации", help_text="Полный ответ от GigaChat")
    rejection_reason = models.TextField(blank=True, verbose_name="Причина отклонения")
    taken_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата взятия")
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="Дата выполнения")
    
    class Meta:
        verbose_name = "📋 Задания: Назначение"
        verbose_name_plural = "📋 Задания: Назначения"
        ordering = ['-taken_at']
        unique_together = ['task', 'author']
    
    def __str__(self):
        return f"{self.author.username} - {self.task.title} ({self.get_status_display()})"
    
    def submit_article(self, article):
        """Автор сдаёт статью на проверку"""
        if self.status == 'in_progress':
            self.article = article
            self.status = 'completed'
            self.submitted_at = timezone.now()
            self.save()
            return True
        return False

"""Задания, отклонённые автором (не показывать повторно)"""
class AuthorTaskRejection(models.Model):
    author = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='rejected_tasks', verbose_name="Автор")
    task = models.ForeignKey('Asistent.ContentTask', on_delete=models.CASCADE, related_name='rejections', verbose_name="Задание")
    rejected_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата отклонения")
    
    class Meta:
        verbose_name = "Отклонённое задание"
        verbose_name_plural = "Отклонённые задания"
        ordering = ['-rejected_at']
        unique_together = ['author', 'task']
    
    def __str__(self):
        return f"{self.author.username} отклонил {self.task.title}"

# ПРИМЕЧАНИЕ: Модели AISchedule и AIScheduleRun перенесены в schedule/models.py
# Используйте: from Asistent.schedule.models import AISchedule, AIScheduleRun
# Или: from Asistent.models import AISchedule (через __getattr__ в конце файла)

"""Баланс и транзакции авторов"""
class AuthorBalance(models.Model):
    
    TRANSACTION_TYPES = [
        ('task_completed', 'Выполнение задания'),
        ('donation', 'Донат'),
        ('bonus', 'Бонус'),
        ('penalty', 'Штраф'),
        ('withdrawal', 'Вывод средств'),
    ]
    
    author = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='balance_transactions', verbose_name="Автор")
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Сумма")
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES, verbose_name="Тип транзакции")
    task = models.ForeignKey('Asistent.ContentTask', on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions', verbose_name="Задание")
    description = models.TextField(blank=True, verbose_name="Описание")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата")
    
    class Meta:
        verbose_name = "Транзакция"
        verbose_name_plural = "Транзакции"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.author.username} - {self.amount} руб. ({self.get_transaction_type_display()})"
    
    @staticmethod
    def get_author_balance(author):
        """Получить текущий баланс автора"""
        from django.db.models import Sum
        balance = AuthorBalance.objects.filter(author=author).aggregate(
            total=Sum('amount')
        )['total']
        return balance or 0

"""История выполненных заданий"""
class TaskHistory(models.Model):
    
    task = models.ForeignKey('Asistent.ContentTask', on_delete=models.CASCADE, related_name='history', verbose_name="Задание")
    author = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='completed_tasks_history', verbose_name="Автор")
    completed_at = models.DateTimeField(verbose_name="Дата выполнения")
    reward = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Вознаграждение")
    
    class Meta:
        verbose_name = "История задания"
        verbose_name_plural = "История заданий"
        ordering = ['-completed_at']
    
    def __str__(self):
        return f"{self.author.username} - {self.task.title}"

"""Статьи, сгенерированные AI-ассистентом"""
class AIGeneratedArticle(models.Model):
    
    schedule = models.ForeignKey('schedule.AISchedule', on_delete=models.SET_NULL, null=True, blank=True, related_name='generated_articles', verbose_name="Расписание")
    article = models.ForeignKey('blog.Post', on_delete=models.CASCADE, related_name='ai_generation_info', verbose_name="Статья")
    source_urls = models.TextField(blank=True, verbose_name="Источники")
    prompt = models.TextField(blank=True, verbose_name="Промпт")
    ai_response = models.TextField(blank=True, verbose_name="Ответ AI")
    generation_time_seconds = models.IntegerField(default=0, verbose_name="Время генерации (сек)")
    api_calls_count = models.IntegerField(default=0, verbose_name="Количество API вызовов")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата генерации")
    
    class Meta:
        verbose_name = "AI-статья"
        verbose_name_plural = "AI-статьи"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"AI: {self.article.title}"

"""Уведомления для авторов"""
class AuthorNotification(models.Model):
    
    NOTIFICATION_TYPES = [
        ('task_available', 'Новое задание'),
        ('task_taken', 'Задание взято'),
        ('moderation_passed', 'Модерация пройдена'),
        ('moderation_failed', 'Модерация не пройдена'),
        ('task_approved', 'Задание одобрено'),
        ('task_rejected', 'Задание отклонено'),
        ('payment', 'Начисление средств'),
        ('system', 'Системное уведомление'),
    ]
    
    recipient = models.ForeignKey(
        'auth.User',
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name="Получатель",
    )
    notification_type = models.CharField(
        max_length=30,
        choices=NOTIFICATION_TYPES,
        verbose_name="Тип уведомления",
    )
    title = models.CharField(max_length=200, verbose_name="Заголовок")
    message = models.TextField(verbose_name="Сообщение")
    related_task = models.ForeignKey(
        'Asistent.ContentTask',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notifications',
        verbose_name="Связанное задание",
    )
    related_article = models.ForeignKey(
        'blog.Post',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notifications',
        verbose_name="Связанная статья",
    )
    is_read = models.BooleanField(default=False, verbose_name="Прочитано")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    read_at = models.DateTimeField(null=True, blank=True, verbose_name="Дата прочтения")
    
    class Meta:
        verbose_name = "📬 Уведомления для авторов"
        verbose_name_plural = "📬 Уведомления для авторов"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.recipient.username} - {self.title}"
    
    def mark_as_read(self):
        """Отметить как прочитанное"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])

"""Профиль стиля написания автора для имитации AI"""
class AuthorStyleProfile(models.Model):
    
    profile = models.OneToOneField(
        'Visitor.Profile',
        on_delete=models.CASCADE,
        related_name='style_profile',
        verbose_name="Профиль",
        null=True,
        blank=True,
    )
    style_name = models.CharField(max_length=200, blank=True, null=True, default='', verbose_name="Название стиля", help_text='Например: "Легкий и вдохновляющий", "Экспертный научный"')
    style_analysis = models.JSONField(default=dict, blank=True, null=True, verbose_name="Анализ стиля", help_text="Результат автоматического анализа статей автора")
    top_articles = models.ManyToManyField('blog.Post', blank=True, verbose_name="Лучшие статьи для обучения")
    is_active = models.BooleanField(default=True, verbose_name="Активен")
    usage_count = models.IntegerField(default=0, verbose_name="Использований")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")   
    
    def get_style_prompt(self):
        """
        Генерирует текст для промпта на основе анализа
        
        Returns:
            str: Описание стиля для AI
        """
        from .style_analyzer import StyleAnalyzer
        
        analyzer = StyleAnalyzer()
        return analyzer.generate_style_prompt(self.style_analysis)
    
    def update_analysis(self, limit=10):
        """
        Обновляет анализ стиля на основе последних статей
        
        Args:
            limit: Количество статей для анализа
        """
        from .style_analyzer import StyleAnalyzer
        import logging
        
        logger = logging.getLogger(__name__)
        analyzer = StyleAnalyzer()
        self.style_analysis = analyzer.analyze_author_style(self.author, limit=limit)
        self.save()
        
        logger.info(f"✅ Обновлен профиль стиля @{self.author.username}")

"""История диалогов с AI-ассистентом"""
class AIConversation(models.Model):
    
    admin = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='ai_conversations',
        verbose_name='Администратор'
    )
    
    title = models.CharField(
        max_length=200,
        default='Новый диалог',
        verbose_name='Название диалога'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Дата обновления'
    )
    
    is_active = models.BooleanField(
        default=True,
        verbose_name='Активен',
        help_text='Активный диалог отображается в списке'
    )
    
    class Meta:
        verbose_name = '🤖 AI-Агент: Диалоги'
        verbose_name_plural = '🤖 AI-Агент: Диалоги'
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"{self.title} ({self.admin.username})"
    
    def get_messages_count(self):
        """Количество сообщений в диалоге"""
        return self.messages.count()
    
    def get_last_message(self):
        """Последнее сообщение в диалоге"""
        return self.messages.order_by('-timestamp').first()

"""Сообщения в диалоге с AI"""
class AIMessage(models.Model):
    
    ROLE_CHOICES = [
        ('admin', 'Администратор'),
        ('assistant', 'AI-ассистент'),
        ('system', 'Система'),
    ]
    
    conversation = models.ForeignKey(
        AIConversation,
        on_delete=models.CASCADE,
        related_name='messages',
        verbose_name='Диалог'
    )
    
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        verbose_name='Роль'
    )
    
    content = models.TextField(
        verbose_name='Содержание сообщения'
    )
    
    timestamp = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Время отправки'
    )
    
    metadata = models.JSONField(
        default=dict,
        verbose_name='Метаданные',
        help_text='Дополнительная информация: задачи, команды, результаты'
    )
    
    embedding = models.JSONField(
        null=True,
        blank=True,
        verbose_name='Векторное представление',
        help_text='Для поиска похожих диалогов (генерируется для admin-сообщений)'
    )
    
    class Meta:
        verbose_name = '🤖 AI-Агент: Сообщения'
        verbose_name_plural = '🤖 AI-Агент: Сообщения'
        ordering = ['timestamp']
        indexes = [
            models.Index(fields=['conversation', 'timestamp'], name='aimsg_conv_time_idx'),
            models.Index(fields=['role', 'timestamp'], name='aimsg_role_time_idx'),
        ]
    
    def __str__(self):
        return f"{self.get_role_display()}: {self.content[:50]}..."

"""База знаний AI-ассистента"""
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

"""Задачи, поставленные через AI-чат"""
class AITask(models.Model):
    
    STATUS_CHOICES = [
        ('pending', 'В очереди'),
        ('in_progress', 'Выполняется'),
        ('completed', 'Выполнено'),
        ('failed', 'Ошибка'),
        ('cancelled', 'Отменено'),
    ]
    
    TASK_TYPE_CHOICES = [
        ('generate_article', 'Генерация статьи'),
        ('parse_video', 'Парсинг видео'),
        ('parse_audio', 'Парсинг аудио'),
        ('distribute_bonuses', 'Распределение бонусов'),
        ('optimize_schedule', 'Оптимизация расписания'),
        # Социальные сети
        ('publish_to_social', 'Публикация в соцсети'),
        ('schedule_posts', 'Создание расписания публикаций'),
        ('reply_to_comment', 'Ответ на комментарий в соцсети'),
        ('reply_to_message', 'Ответ в переписке'),
        ('analyze_channel', 'Анализ канала'),
        ('optimize_posting', 'Оптимизация времени публикации'),
        ('create_ad_campaign', 'Создание рекламной кампании'),
        ('crosspost_content', 'Кросс-постинг контента'),
        # Реклама
        ('ad_show_places', 'Показать рекламные места'),
        ('ad_statistics', 'Статистика рекламы'),
        ('ad_activate_banner', 'Активировать баннер'),
        ('ad_deactivate_banner', 'Деактивировать баннер'),
        ('ad_list_banners', 'Список баннеров'),
        ('ad_insert_in_article', 'Вставить рекламу в статью'),
    ]
    
    conversation = models.ForeignKey(
        AIConversation,
        on_delete=models.CASCADE,
        related_name='tasks',
        verbose_name='Диалог'
    )
    
    command = models.CharField(
        max_length=500,
        verbose_name='Исходная команда',
        help_text='Команда от администратора'
    )
    
    task_type = models.CharField(
        max_length=50,
        choices=TASK_TYPE_CHOICES,
        verbose_name='Тип задачи'
    )
    
    parameters = models.JSONField(
        default=dict,
        verbose_name='Параметры',
        help_text='Параметры выполнения задачи'
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='Статус'
    )
    
    progress_description = models.TextField(
        blank=True,
        verbose_name='Описание прогресса',
        help_text='Текущее состояние выполнения'
    )
    
    result = models.JSONField(
        null=True,
        blank=True,
        verbose_name='Результат',
        help_text='Результат выполнения задачи'
    )
    
    error_message = models.TextField(
        blank=True,
        verbose_name='Сообщение об ошибке'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    
    started_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Дата начала выполнения'
    )
    
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Дата завершения'
    )
    
    class Meta:
        verbose_name = '🤖 AI-Агент: Задачи'
        verbose_name_plural = '🤖 AI-Агент: Задачи'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_task_type_display()} - {self.get_status_display()}"
    
    def start(self):
        """Начать выполнение задачи"""
        self.status = 'in_progress'
        self.started_at = timezone.now()
        self.save()
    
    def complete(self, result=None):
        """Завершить задачу успешно"""
        self.status = 'completed'
        self.completed_at = timezone.now()
        if result:
            self.result = result
        self.save()
    
    def fail(self, error_message):
        """Завершить задачу с ошибкой"""
        self.status = 'failed'
        self.completed_at = timezone.now()
        self.error_message = error_message
        self.save()


# ============================================================================
# ЭТАП 2: МОДЕЛИ ДЛЯ ПАРСИНГА И АВТОМАТИЗАЦИИ
# ============================================================================

"""Профили ботов для автоматического комментирования и лайков"""
class BotProfile(models.Model):
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='bot_profile',
        verbose_name='Пользователь'
    )
    
    is_active = models.BooleanField(
        default=True,
        verbose_name='Активен'
    )
    
    bot_name = models.CharField(
        max_length=100,
        verbose_name='Имя бота',
        help_text='Отображаемое имя для комментариев'
    )
    
    comment_style = models.CharField(
        max_length=50,
        choices=[
            ('formal', 'Формальный'),
            ('casual', 'Неформальный'),
            ('friendly', 'Дружелюбный'),
            ('expert', 'Экспертный'),
            ('humorous', 'Юмористический'),
        ],
        default='friendly',
        verbose_name='Стиль комментирования'
    )
    
    comment_templates = models.JSONField(
        default=list,
        verbose_name='Шаблоны комментариев',
        help_text='Список шаблонов для генерации комментариев'
    )
    
    max_comments_per_day = models.IntegerField(
        default=10,
        verbose_name='Максимум комментариев в день'
    )
    
    max_likes_per_day = models.IntegerField(
        default=20,
        verbose_name='Максимум лайков в день'
    )
    
    preferred_categories = models.JSONField(
        default=list,
        verbose_name='Предпочитаемые категории',
        help_text='Категории статей для комментирования'
    )
    
    avoid_categories = models.JSONField(
        default=list,
        verbose_name='Избегаемые категории',
        help_text='Категории статей, которые бот не комментирует'
    )
    
    min_article_views = models.IntegerField(
        default=100,
        verbose_name='Минимальные просмотры статьи',
        help_text='Комментировать только статьи с таким количеством просмотров'
    )
    
    comment_probability = models.FloatField(
        default=0.3,
        verbose_name='Вероятность комментирования',
        help_text='От 0.0 до 1.0'
    )
    
    like_probability = models.FloatField(
        default=0.5,
        verbose_name='Вероятность лайка',
        help_text='От 0.0 до 1.0'
    )
    
    last_activity = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Последняя активность'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    
    class Meta:
        verbose_name = 'Профиль бота'
        verbose_name_plural = 'Профили ботов'
    
    def __str__(self):
        return f"{self.bot_name} ({self.user.username})"
    
    def can_comment_today(self):
        """Можно ли комментировать сегодня"""
        from django.utils import timezone
        from django.db.models import Count
        
        today = timezone.now().date()
        today_comments = self.user.comments.filter(
            created_at__date=today
        ).count()
        
        return today_comments < self.max_comments_per_day
    
    def can_like_today(self):
        """Можно ли лайкать сегодня"""
        from django.utils import timezone
        from blog.models import PostLike
        
        today = timezone.now().date()
        today_likes = PostLike.objects.filter(
            user=self.user,
            created_at__date=today
        ).count()
        
        return today_likes < self.max_likes_per_day
    
    def get_random_comment_template(self):
        """Получить случайный шаблон комментария"""
        import random
        
        if not self.comment_templates:
            return "Интересная статья!"
        
        return random.choice(self.comment_templates)

"""Лог активности ботов"""
class BotActivity(models.Model):
    
    ACTION_CHOICES = [
        ('comment', 'Комментарий'),
        ('like', 'Лайк'),
        ('skip', 'Пропуск'),
    ]
    
    bot_profile = models.ForeignKey(
        BotProfile,
        on_delete=models.CASCADE,
        related_name='activities',
        verbose_name='Профиль бота'
    )
    
    action = models.CharField(
        max_length=20,
        choices=ACTION_CHOICES,
        verbose_name='Действие'
    )
    
    article = models.ForeignKey(
        'blog.Post',
        on_delete=models.CASCADE,
        related_name='bot_activities',
        verbose_name='Статья'
    )
    
    content = models.TextField(
        blank=True,
        verbose_name='Содержание',
        help_text='Текст комментария или причина пропуска'
    )
    
    success = models.BooleanField(
        default=True,
        verbose_name='Успешно'
    )
    
    error_message = models.TextField(
        blank=True,
        verbose_name='Сообщение об ошибке'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата действия'
    )
    
    class Meta:
        verbose_name = 'Активность бота'
        verbose_name_plural = 'Активности ботов'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.bot_profile.bot_name} - {self.get_action_display()} - {self.article.title[:50]}"


# ============================================================================
# ЭТАП 3: МОДЕЛИ ДЛЯ БОНУСОВ, ДОНАТОВ И ОБУЧЕНИЯ
# ============================================================================

"""Формула расчета бонусов"""
class BonusFormula(models.Model):
    
    name = models.CharField(
        max_length=200,
        verbose_name='Название формулы'
    )
    
    description = models.TextField(
        blank=True,
        verbose_name='Описание'
    )
    
    coefficients = models.JSONField(
        default=dict,
        verbose_name='Коэффициенты',
        help_text='Словарь с коэффициентами для расчета'
    )
    
    is_active = models.BooleanField(
        default=False,
        verbose_name='Активна'
    )
    
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='bonus_formulas',
        verbose_name='Создал'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    
    class Meta:
        verbose_name = 'Формула бонусов'
        verbose_name_plural = 'Формулы бонусов'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} {'(Активна)' if self.is_active else ''}"
    
    def activate(self):
        """Активирует эту формулу и деактивирует остальные"""
        BonusFormula.objects.filter(is_active=True).update(is_active=False)
        self.is_active = True
        self.save()

"""История расчетов бонусов"""
class BonusCalculation(models.Model):
    
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='bonus_calculations',
        verbose_name='Автор'
    )
    
    period_days = models.IntegerField(
        default=30,
        verbose_name='Период (дней)'
    )
    
    total_bonus = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='Общий бонус'
    )
    
    articles_count = models.IntegerField(
        default=0,
        verbose_name='Количество статей'
    )
    
    details = models.JSONField(
        default=dict,
        verbose_name='Детали расчета'
    )
    
    formula_snapshot = models.JSONField(
        default=dict,
        verbose_name='Снимок формулы',
        help_text='Формула, использованная для расчета'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата расчета'
    )
    
    class Meta:
        verbose_name = 'Расчет бонуса'
        verbose_name_plural = 'Расчеты бонусов'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.author.username} - {self.total_bonus} баллов ({self.created_at.date()})"

"""Распределение донатов"""
class DonationDistribution(models.Model):
    
    pool_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Сумма фонда'
    )
    
    distributed_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Распределено'
    )
    
    authors_count = models.IntegerField(
        default=0,
        verbose_name='Количество авторов'
    )
    
    period_days = models.IntegerField(
        default=30,
        verbose_name='Период анализа (дней)'
    )
    
    weights = models.JSONField(
        default=dict,
        verbose_name='Веса распределения'
    )
    
    distributions_data = models.JSONField(
        default=list,
        verbose_name='Данные распределения'
    )
    
    is_completed = models.BooleanField(
        default=False,
        verbose_name='Завершено'
    )
    
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='donation_distributions',
        verbose_name='Создал'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    
    class Meta:
        verbose_name = 'Распределение донатов'
        verbose_name_plural = 'Распределения донатов'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Распределение {self.pool_amount} руб. ({self.created_at.date()})"

"""Доля автора в распределении донатов"""
class AuthorDonationShare(models.Model):
    
    distribution = models.ForeignKey(
        DonationDistribution,
        on_delete=models.CASCADE,
        related_name='author_shares',
        verbose_name='Распределение'
    )
    
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='donation_shares',
        verbose_name='Автор'
    )
    
    share_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        verbose_name='Доля (%)'
    )
    
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Сумма'
    )
    
    metrics = models.JSONField(
        default=dict,
        verbose_name='Метрики автора'
    )
    
    is_paid = models.BooleanField(
        default=False,
        verbose_name='Выплачено'
    )
    
    paid_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Дата выплаты'
    )
    
    class Meta:
        verbose_name = 'Доля автора'
        verbose_name_plural = 'Доли авторов'
        unique_together = ['distribution', 'author']
    
    def __str__(self):
        return f"{self.author.username} - {self.amount} руб. ({self.share_percentage}%)"

"""Шаблоны промптов для AI"""
class PromptTemplate(models.Model):
    
    CATEGORY_CHOICES = [
        ('article_single', 'Генерация статьи'),
        ('article_series', 'Генерация серии статей'),
        ('horoscope', 'Генерация гороскопа'),
        ('faq', 'Генерация FAQ'),
        ('comments', 'Генерация комментариев'),
    ]
    
    category = models.CharField(
        blank=True,
        default='article_single',
        null=True,
        max_length=50,
        choices=CATEGORY_CHOICES,
        verbose_name='Категория'
    )
    name = models.CharField(blank=True, null=True, default='', max_length=200, verbose_name='Название')
    description = models.TextField(blank=True, verbose_name='Описание')
    debug_script = models.TextField(blank=True, null=True, default='', verbose_name='Скрипт отладки', help_text='Используйте {переменные} для подстановки')    
    template = models.TextField(blank=True, null=True, default='', verbose_name='Шаблон промпта', help_text='Используйте {переменные} для подстановки')
    variables = models.JSONField(default=list, verbose_name='Переменные', help_text='Список доступных переменных')
    is_active = models.BooleanField(default=True, verbose_name='Активен')
    usage_count = models.IntegerField(default=0, verbose_name='Количество использований')
    current_version = models.IntegerField(default=1, verbose_name='Текущая версия')
    last_change_summary = models.TextField(blank=True, verbose_name='Последнее описание изменений')
    success_rate = models.FloatField(default=0.0, verbose_name='Процент успеха', help_text='От 0.0 до 1.0')
    created_by = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='prompt_templates', verbose_name='Создал')
    updated_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='updated_prompt_templates', verbose_name='Последний редактор')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')
    # Поля для полного контроля генерации статей
    blog_category = models.ForeignKey('blog.Category', on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Категория в блоге', help_text='В какую категорию публиковать статью')
    default_author = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='authored_prompt_templates', verbose_name='Автор статей', help_text='Кто будет автором сгенерированных статей (если пусто - используется ai_assistant или текущий пользователь)')
    title_criteria = models.TextField(blank=True, verbose_name='Критерии для заголовка', help_text='Инструкции AI как формировать заголовок. Переменные: {zodiac_sign}, {date}, {category}')
    image_source_type = models.CharField(max_length=20, choices=[('upload', 'Загрузить (модератор загружает)'), ('search_db', 'Поиск в нашей базе'), ('parse_web', 'Парсинг из интернета'), ('generate_auto', 'Генерация - на усмотрение AI'), ('generate_custom', 'Генерация - с кастомным промптом'), ('none', 'Без изображения')], default='generate_auto', blank=True, verbose_name='Источник главного изображения')
    image_search_criteria = models.TextField(blank=True, null=True, default='', verbose_name='Критерии поиска изображения', help_text='По каким критериям искать. Если пусто - AI выбирает по категории и названию. Переменные: {zodiac_sign}, {category}, {title}')
    image_generation_criteria = models.TextField(blank=True, null=True, default='', verbose_name='Критерии генерации изображения', help_text='Промпт для генерации. Если пусто - AI выбирает сам. Переменные: {zodiac_sign}, {season}, {category}, {title}')
    auto_process_image = models.BooleanField(default=True, verbose_name='AI обработка изображения', help_text='Переименование по-английски, оптимизация размера, формат, индексация')
    tags_criteria = models.TextField(blank=True, null=True, default='', verbose_name='Критерии для тегов', help_text='Через запятую. В кавычках "слово" = буквально, без кавычек знак_зодиака = подобрать по смыслу. Переменные: {zodiac_sign}, {category}')
    content_source_type = models.CharField(max_length=20, choices=[('parse', 'Парсить из источников + переписать'), ('generate', 'Полностью генерировать AI'), ('hybrid', 'Гибрид: парсить темы + генерировать текст')], default='hybrid', blank=True, verbose_name='Источник контента')
    content_source_urls = models.TextField(blank=True, null=True, default='', verbose_name='URL источников для контента', help_text='По одному на строке. Если пусто - используется из AISchedule')
    parse_first_paragraph = models.BooleanField(default=False, verbose_name='Парсить первый абзац из источников', help_text='Спарсить первый абзац с сайтов и использовать как основу')
    uploaded_media = models.FileField(upload_to='prompt_templates/', null=True, blank=True, verbose_name='Загруженный файл (изображение/видео)', help_text='Для режима "Загрузить (модератор загружает)". AI обработает автоматически')
    
    class Meta:
        verbose_name = 'Шаблон промпта'
        verbose_name_plural = 'Шаблоны промптов'
        ordering = ['-created_at']
    
    def save(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        change_summary = kwargs.pop('change_summary', '')
        
        is_new = self.pk is None
        previous_state = None
        
        if not is_new:
            previous_state = PromptTemplate.objects.get(pk=self.pk)
        
        fields_for_version = [
            'template',
            'variables',
            'description',
            'title_criteria',
            'image_search_criteria',
            'image_generation_criteria',
            'tags_criteria',
        ]
        
        has_changes = is_new
        if previous_state:
            for field in fields_for_version:
                if getattr(previous_state, field) != getattr(self, field):
                    has_changes = True
                    break
        
        if is_new:
            self.current_version = 1
            if user and not self.created_by_id:
                self.created_by = user
        elif has_changes:
            self.current_version = previous_state.current_version + 1
        else:
            # Версия не изменилась — сохраняем метаданные и выходим
            if user:
                self.updated_by = user
            super().save(*args, **kwargs)
            return
        
        if user:
            if not self.created_by_id:
                self.created_by = user
            self.updated_by = user
        if change_summary:
            self.last_change_summary = change_summary
        
        super().save(*args, **kwargs)
        
        # Создаём запись об изменениях
        PromptTemplateVersion.objects.create(
            template=self,
            version=self.current_version,
            template_text=self.template,
            variables=self.variables,
            description=self.description,
            title_criteria=self.title_criteria,
            image_search_criteria=self.image_search_criteria,
            image_generation_criteria=self.image_generation_criteria,
            tags_criteria=self.tags_criteria,
            change_summary=change_summary,
            created_by=user
        )
    
    def __str__(self):
        return f"{self.name} ({self.get_category_display()})"


class ArticleGenerationMetric(models.Model):
    """Метрики производительности генерации статей"""
    
    # Идентификаторы
    template = models.ForeignKey(
        PromptTemplate,
        on_delete=models.CASCADE,
        related_name='generation_metrics',
        verbose_name='Шаблон промпта'
    )
    
    # Временные метки
    started_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Начало генерации',
        db_index=True
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Завершение генерации'
    )
    
    # Общие метрики
    total_duration = models.FloatField(
        null=True,
        blank=True,
        verbose_name='Общее время (сек)',
        help_text='Время от начала до конца генерации'
    )
    success = models.BooleanField(
        default=False,
        verbose_name='Успешно',
        db_index=True
    )
    error_message = models.TextField(
        blank=True,
        verbose_name='Сообщение об ошибке'
    )
    
    # Метрики этапов (в секундах)
    context_build_duration = models.FloatField(
        null=True,
        blank=True,
        verbose_name='Построение контекста (сек)'
    )
    content_generation_duration = models.FloatField(
        null=True,
        blank=True,
        verbose_name='Генерация контента (сек)'
    )
    title_generation_duration = models.FloatField(
        null=True,
        blank=True,
        verbose_name='Генерация заголовка (сек)'
    )
    image_processing_duration = models.FloatField(
        null=True,
        blank=True,
        verbose_name='Обработка изображения (сек)'
    )
    tags_generation_duration = models.FloatField(
        null=True,
        blank=True,
        verbose_name='Генерация тегов (сек)'
    )
    
    # Метрики результата
    content_length = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='Длина контента (символов)'
    )
    word_count = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='Количество слов'
    )
    tags_count = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='Количество тегов'
    )
    has_image = models.BooleanField(
        default=False,
        verbose_name='Есть изображение'
    )
    image_source_type = models.CharField(
        max_length=20,
        blank=True,
        verbose_name='Тип источника изображения'
    )
    
    # Метаданные
    gigachat_model = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='Модель GigaChat'
    )
    user_id = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='ID пользователя'
    )
    
    class Meta:
        verbose_name = '📊 Метрика генерации статьи'
        verbose_name_plural = '📊 Метрики генерации статей'
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['-started_at']),
            models.Index(fields=['template', '-started_at']),
            models.Index(fields=['success', '-started_at']),
        ]
    
    def __str__(self):
        status = "✅" if self.success else "❌"
        duration = f"{self.total_duration:.1f}s" if self.total_duration else "N/A"
        return f"{status} {self.template.name} - {duration} ({self.started_at.strftime('%d.%m %H:%M')})"
    
    def complete(self, success: bool = True, error_message: str = ''):
        """Завершение метрики с расчётом общего времени"""
        self.completed_at = timezone.now()
        self.success = success
        self.error_message = error_message
        
        if self.started_at:
            delta = self.completed_at - self.started_at
            self.total_duration = delta.total_seconds()
        
        self.save()


class PromptTemplateVersion(models.Model):
    """История изменений шаблонов промптов"""
    
    template = models.ForeignKey(
        PromptTemplate,
        on_delete=models.CASCADE,
        related_name='versions',
        verbose_name='Шаблон'
    )
    
    version = models.IntegerField(
        verbose_name='Версия'
    )
    
    template_text = models.TextField(
        verbose_name='Текст промпта'
    )
    
    variables = models.JSONField(
        default=list,
        verbose_name='Переменные'
    )
    
    description = models.TextField(
        blank=True,
        verbose_name='Описание'
    )
    
    title_criteria = models.TextField(
        blank=True,
        verbose_name='Критерии заголовка'
    )
    
    image_search_criteria = models.TextField(
        blank=True,
        verbose_name='Критерии поиска изображения'
    )
    
    image_generation_criteria = models.TextField(
        blank=True,
        verbose_name='Критерии генерации изображения'
    )
    
    tags_criteria = models.TextField(
        blank=True,
        verbose_name='Критерии тегов'
    )
    
    change_summary = models.TextField(
        blank=True,
        verbose_name='Описание изменений'
    )
    
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='prompt_template_versions',
        verbose_name='Автор версии'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    
    class Meta:
        verbose_name = 'Версия промпта'
        verbose_name_plural = 'Версии промптов'
        ordering = ['-created_at']
        unique_together = [('template', 'version')]
    
    def __str__(self):
        return f"{self.template.name} v{self.version}"
    
    def increment_usage(self, success: bool = True):
        """Увеличивает счетчик использований и обновляет success_rate"""
        self.usage_count += 1
        if self.usage_count == 1:
            self.success_rate = 1.0 if success else 0.0
        else:
            # Экспоненциальное скользящее среднее
            alpha = 0.1
            self.success_rate = alpha * (1.0 if success else 0.0) + (1 - alpha) * self.success_rate
        self.save(update_fields=['usage_count', 'success_rate'])

"""Настройки поведения чат-бота для пользователей"""
# ============================================
# Импорты моделей чат-бота из ChatBot_AI
# Обратная совместимость для старых импортов
# ============================================
from Asistent.ChatBot_AI.models import (
    ChatbotSettings,
    ChatbotFAQ,
    ChatMessage,
)


"Интеграционные события (GigaChat, Telegram и т.д.)"
class IntegrationEvent(models.Model):
    
    SERVICE_CHOICES = [
        ("telegram", "Telegram"),
        ("gigachat", "GigaChat"),
        ("storage", "Хранилище"),
        ("other", "Другое"),
    ]
    
    SEVERITY_CHOICES = [
        ("info", "Info"),
        ("warning", "Warning"),
        ("error", "Error"),
    ]
    
    created_at = models.DateTimeField(default=timezone.now, db_index=True, verbose_name="Дата")
    service = models.CharField(max_length=32, choices=SERVICE_CHOICES, default="other", verbose_name="Сервис")
    code = models.CharField(max_length=64, verbose_name="Код/статус")
    message = models.TextField(verbose_name="Сообщение")
    severity = models.CharField(max_length=16, choices=SEVERITY_CHOICES, default="warning", verbose_name="Уровень")
    extra = models.JSONField(default=dict, blank=True, verbose_name="Доп. данные")
    
    class Meta:
        verbose_name = "⚙️ Интеграция: событие"
        verbose_name_plural = "⚙️ Интеграции: события"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"[{self.service}] {self.code} ({self.severity})"

"""Статистика использования GigaChat API по моделям"""
class GigaChatUsageStats(models.Model):
    
    model_name = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Название модели",
        help_text="GigaChat, GigaChat-Max, GigaChat-Pro"
    )
    
    tokens_used = models.IntegerField(
        default=0,
        verbose_name="Токенов использовано"
    )
    
    tokens_remaining = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="Токенов осталось"
    )
    
    total_requests = models.IntegerField(
        default=0,
        verbose_name="Всего запросов"
    )
    
    successful_requests = models.IntegerField(
        default=0,
        verbose_name="Успешных запросов"
    )
    
    failed_requests = models.IntegerField(
        default=0,
        verbose_name="Неудачных запросов"
    )
    
    # ============================================================================
    # НОВЫЕ ПОЛЯ: Дневная статистика и стоимость
    # ============================================================================
    
    tokens_used_today = models.IntegerField(
        default=0,
        verbose_name="Токенов использовано сегодня",
        help_text="Счетчик токенов за текущий день (сбрасывается в 00:00)"
    )
    
    cost_today = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        verbose_name="Стоимость сегодня (₽)",
        help_text="Расходы на API за текущий день"
    )
    
    cost_total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        verbose_name="Общая стоимость (₽)",
        help_text="Все расходы на API за все время"
    )
    
    last_daily_reset = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Последний сброс дневной статистики",
        help_text="Дата последнего сброса tokens_used_today и cost_today (в 00:00)"
    )
    
    last_check_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Последняя проверка"
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата создания"
    )
    
    class Meta:
        verbose_name = "🤖 GigaChat: Статистика модели"
        verbose_name_plural = "🤖 GigaChat: Статистика моделей"
        ordering = ['model_name']
    
    def __str__(self):
        return f"{self.model_name}: {self.tokens_remaining or 0} токенов"
    
    @property
    def success_rate(self):
        """Процент успешных запросов"""
        if self.total_requests == 0:
            return 0
        return round((self.successful_requests / self.total_requests) * 100, 2)

    def reset_daily_counters_if_needed(self, save=True):
        """Сбрасывает дневные счетчики, если наступил новый день."""
        now = timezone.now()
        if not self.last_daily_reset or self.last_daily_reset.date() != now.date():
            self.tokens_used_today = 0
            self.cost_today = Decimal("0.00")
            self.last_daily_reset = now
            if save:
                self.save(update_fields=["tokens_used_today", "cost_today", "last_daily_reset"])

    def register_usage(self, tokens_used: int, price_per_million: Decimal) -> None:
        """Фиксирует расход токенов и стоимость запроса."""
        if tokens_used <= 0:
            return
        self.reset_daily_counters_if_needed(save=False)
        self.tokens_used += tokens_used
        self.tokens_used_today += tokens_used
        cost_increment = (Decimal(tokens_used) / Decimal(1_000_000)) * price_per_million
        self.cost_today += cost_increment
        self.cost_total += cost_increment
        self.last_check_at = timezone.now()
        self.save(
            update_fields=[
                "tokens_used",
                "tokens_used_today",
                "cost_today",
                "cost_total",
                "last_daily_reset",
                "last_check_at",
            ]
        )

"""Настройки работы с GigaChat API"""
class GigaChatSettings(models.Model):
    
    # УСТАРЕВШИЕ ПОЛЯ (не используются в логике, оставлены для совместимости)
    check_balance_after_requests = models.IntegerField(default=1, validators=[MinValueValidator(1)], verbose_name="Проверять баланс после N запросов", help_text="[УСТАРЕЛО] Только для ручной проверки в дашборде")
    current_model = models.CharField(max_length=50, default='GigaChat', verbose_name="Текущая модель", help_text="[УСТАРЕЛО] Только для отображения, не используется в логике")
    auto_switch_enabled = models.BooleanField(default=True, verbose_name="Автопереключение моделей", help_text="[УСТАРЕЛО] Не используется - переключения отключены")
    models_priority = models.JSONField(default=list, verbose_name="Приоритет моделей", help_text="[УСТАРЕЛО] Только для отображения")
    request_counter = models.IntegerField(default=0, verbose_name="Счётчик запросов", help_text="[УСТАРЕЛО] Не используется")
    # ============================================================================
    # НОВЫЕ ПОЛЯ: Включение моделей и прайс-лист
    # ============================================================================
    embeddings_enabled = models.BooleanField(default=True, verbose_name="Embeddings включен", help_text="Использовать GigaChat-Embeddings для RAG и векторного поиска")
    lite_enabled = models.BooleanField(default=True, verbose_name="Lite включен", help_text="Использовать GigaChat Lite для простых задач")
    pro_enabled = models.BooleanField(default=True, verbose_name="Pro включен", help_text="Использовать GigaChat Pro для средних задач")
    max_enabled = models.BooleanField(default=True, verbose_name="Max включен", help_text="Использовать GigaChat Max для сложных задач")
    # Прайс-лист (₽ за 1M токенов) для расчета стоимости
    price_embeddings = models.DecimalField(max_digits=10, decimal_places=2, default=40.00, verbose_name="Цена Embeddings (₽/1M)", help_text="10M токенов = 400₽ → 1M = 40₽")
    price_lite = models.DecimalField(max_digits=10, decimal_places=2, default=194.00, verbose_name="Цена Lite (₽/1M)", help_text="30M токенов = 5,820₽ → 1M = 194₽")
    price_pro = models.DecimalField(max_digits=10, decimal_places=2, default=1500.00, verbose_name="Цена Pro (₽/1M)", help_text="1M токенов = 1,500₽")
    price_max = models.DecimalField(max_digits=10, decimal_places=2, default=1950.00, verbose_name="Цена Max (₽/1M)", help_text="1M токенов = 1,950₽")
    # УСТАРЕВШИЕ ПОЛЯ (не используются - проверки лимитов отключены)
    lite_daily_limit = models.IntegerField(default=2_000_000, verbose_name="Дневной лимит Lite (токены)", help_text="[УСТАРЕЛО] Не используется - проверки лимитов отключены")
    pro_daily_limit = models.IntegerField(default=1_000_000, verbose_name="Дневной лимит Pro (токены)", help_text="[УСТАРЕЛО] Не используется - проверки лимитов отключены")
    max_daily_limit = models.IntegerField(default=500_000, verbose_name="Дневной лимит Max (токены)", help_text="[УСТАРЕЛО] Не используется - проверки лимитов отключены")
    task_failure_limit = models.IntegerField(default=5, verbose_name="Порог ошибок на задачу", help_text="Сколько ошибок подряд допускается для одного типа задачи")
    task_failure_window = models.IntegerField(default=30, verbose_name="Окно ошибок (минуты)", help_text="За какой период анализировать ошибки для circuit breaker")
    # Пороги для алертов (только для дашборда)
    alert_threshold_percent = models.IntegerField(default=20, validators=[MinValueValidator(1), MaxValueValidator(100)], verbose_name="Порог алерта (%)", help_text="Только для отображения в Dashboard")
    # УСТАРЕВШЕЕ ПОЛЕ (не используется - переключения отключены)
    preventive_switch_threshold = models.IntegerField(default=10, validators=[MinValueValidator(1), MaxValueValidator(100)], verbose_name="Порог превентивного переключения (%)", help_text="[УСТАРЕЛО] Не используется - переключения отключены")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Последнее обновление")
    
    class Meta:
        verbose_name = "🤖 GigaChat: Настройки"
        verbose_name_plural = "🤖 GigaChat: Настройки"
    
    def __str__(self):
        return f"GigaChat Settings (текущая модель: {self.current_model})"
    
    def save(self, *args, **kwargs):
        # Гарантируем что всегда существует только одна запись с pk=1
        self.pk = 1
        super().save(*args, **kwargs)


"""Системные логи - все логи Django, Django-Q, Asistent и других модулей"""
class SystemLog(models.Model):
    """
    Модель для хранения всех системных логов в базе данных.
    Логи хранятся не более 24 часов (автоматическая очистка).
    """
    
    LEVEL_CHOICES = [
        ('DEBUG', 'DEBUG'),
        ('INFO', 'INFO'),
        ('WARNING', 'WARNING'),
        ('ERROR', 'ERROR'),
        ('CRITICAL', 'CRITICAL'),
    ]
    
    timestamp = models.DateTimeField(
        default=timezone.now,
        db_index=True,
        verbose_name='Время события'
    )
    
    level = models.CharField(
        max_length=10,
        choices=LEVEL_CHOICES,
        db_index=True,
        verbose_name='Уровень'
    )
    
    logger_name = models.CharField(
        max_length=100,
        db_index=True,
        verbose_name='Имя логгера',
        help_text='Например: django, Asistent, django-q'
    )
    
    message = models.TextField(
        verbose_name='Сообщение'
    )
    
    module = models.CharField(
        max_length=200,
        blank=True,
        db_index=True,
        verbose_name='Модуль',
        help_text='Имя модуля где произошло событие'
    )
    
    function = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='Функция',
        help_text='Имя функции где произошло событие'
    )
    
    line = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='Номер строки'
    )
    
    process_id = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='ID процесса'
    )
    
    thread_id = models.BigIntegerField(
        null=True,
        blank=True,
        verbose_name='ID потока'
    )
    
    extra_data = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='Дополнительные данные',
        help_text='Дополнительная информация в формате JSON'
    )
    
    class Meta:
        verbose_name = '📋 Системный лог'
        verbose_name_plural = '📋 Системные логи'
        ordering = ['-timestamp']
        db_table = 'asistent_systemlog'
        indexes = [
            models.Index(fields=['-timestamp']),
            models.Index(fields=['level', '-timestamp']),
            models.Index(fields=['logger_name', '-timestamp']),
            models.Index(fields=['module', '-timestamp']),
        ]
    
    def __str__(self):
        return f"{self.level} [{self.logger_name}] {self.message[:50]}... ({self.timestamp.strftime('%Y-%m-%d %H:%M:%S')})"


# ============================================
# Импорты моделей модерации из moderations
# Упрощённая версия v2.0
# ============================================
from Asistent.moderations.models import (
    ArticleModerationSettings,
    CommentModerationSettings,
    ModerationLog,
)

# Алиасы для обратной совместимости
ModerationCriteria = ArticleModerationSettings
CommentModerationCriteria = CommentModerationSettings
CommentModerationLog = ModerationLog


# =============================================================================
# ОБРАТНАЯ СОВМЕСТИМОСТЬ: Ленивый импорт моделей из schedule
# =============================================================================
def __getattr__(name):
    """
    Ленивый импорт моделей из schedule для обратной совместимости.
    Позволяет использовать: from Asistent.models import AISchedule
    Без циклического импорта при загрузке модуля.
    """
    if name == 'AISchedule':
        from .schedule.models import AISchedule
        return AISchedule
    elif name == 'AIScheduleRun':
        from .schedule.models import AIScheduleRun
        return AIScheduleRun
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")