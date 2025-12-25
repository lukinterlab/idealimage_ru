"""
Модели: AuthorBalance, BonusFormula, BonusCalculation, DonationDistribution, AuthorDonationShare
"""
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal

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



