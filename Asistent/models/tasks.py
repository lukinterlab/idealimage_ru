"""
Модели: ContentTask, TaskAssignment, AuthorTaskRejection, TaskHistory
"""
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal

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



