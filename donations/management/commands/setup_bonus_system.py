"""
Management команда для настройки системы бонусов
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from decimal import Decimal

from donations.models import AuthorRole, BonusFormula


class Command(BaseCommand):
    help = 'Настройка системы бонусов: создание ролей и формул'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Настройка системы бонусов...'))
        
        # Создаем роли
        self.create_roles()
        
        # Создаем формулы для каждой роли
        self.create_formulas()
        
        self.stdout.write(self.style.SUCCESS('[OK] Система бонусов настроена успешно!'))

    def create_roles(self):
        """Создать базовые роли авторов"""
        self.stdout.write('Создание ролей авторов...')
        
        roles_data = [
            {
                'name': 'Стажёр',
                'level': 1,
                'bonus_percentage': Decimal('5.00'),
                'point_value': Decimal('0.50'),
                'description': 'Начинающий автор. Первые шаги в создании контента.',
                'color': '#9CA3AF'
            },
            {
                'name': 'Автор',
                'level': 2,
                'bonus_percentage': Decimal('10.00'),
                'point_value': Decimal('1.00'),
                'description': 'Опытный автор. Регулярно создает качественный контент.',
                'color': '#3B82F6'
            },
            {
                'name': 'Писатель',
                'level': 3,
                'bonus_percentage': Decimal('15.00'),
                'point_value': Decimal('1.50'),
                'description': 'Профессиональный писатель. Создает популярный контент.',
                'color': '#8B5CF6'
            },
            {
                'name': 'Бестселлер',
                'level': 4,
                'bonus_percentage': Decimal('25.00'),
                'point_value': Decimal('2.00'),
                'description': 'Топовый автор. Создает вирусный контент с максимальной вовлеченностью.',
                'color': '#F59E0B'
            },
        ]
        
        for role_data in roles_data:
            role, created = AuthorRole.objects.get_or_create(
                level=role_data['level'],
                defaults=role_data
            )
            
            if created:
                self.stdout.write(self.style.SUCCESS(f'  [+] Создана роль: {role.name}'))
            else:
                # Обновляем существующую роль
                for key, value in role_data.items():
                    setattr(role, key, value)
                role.save()
                self.stdout.write(self.style.WARNING(f'  [*] Обновлена роль: {role.name}'))

    def create_formulas(self):
        """Создать формулы расчета для каждой роли"""
        self.stdout.write('Создание формул расчета...')
        
        # Формулы для каждого уровня
        formulas_data = [
            {
                # Стажёр - базовая формула
                'level': 1,
                'articles_weight': Decimal('10.00'),
                'likes_weight': Decimal('0.30'),
                'comments_weight': Decimal('0.50'),
                'views_weight': Decimal('0.005'),
                'tasks_weight': Decimal('5.00'),
                'min_points_required': Decimal('0.00'),
                'min_articles_required': 0,
            },
            {
                # Автор - требуется 50 баллов и 3 статьи
                'level': 2,
                'articles_weight': Decimal('12.00'),
                'likes_weight': Decimal('0.40'),
                'comments_weight': Decimal('0.75'),
                'views_weight': Decimal('0.008'),
                'tasks_weight': Decimal('6.00'),
                'min_points_required': Decimal('50.00'),
                'min_articles_required': 3,
            },
            {
                # Писатель - требуется 150 баллов и 5 статей
                'level': 3,
                'articles_weight': Decimal('15.00'),
                'likes_weight': Decimal('0.50'),
                'comments_weight': Decimal('1.00'),
                'views_weight': Decimal('0.010'),
                'tasks_weight': Decimal('8.00'),
                'min_points_required': Decimal('150.00'),
                'min_articles_required': 5,
            },
            {
                # Бестселлер - требуется 300 баллов и 8 статей
                'level': 4,
                'articles_weight': Decimal('20.00'),
                'likes_weight': Decimal('0.70'),
                'comments_weight': Decimal('1.50'),
                'views_weight': Decimal('0.015'),
                'tasks_weight': Decimal('10.00'),
                'min_points_required': Decimal('300.00'),
                'min_articles_required': 8,
            },
        ]
        
        for formula_data in formulas_data:
            level = formula_data.pop('level')
            role = AuthorRole.objects.get(level=level)
            
            formula, created = BonusFormula.objects.get_or_create(
                role=role,
                defaults=formula_data
            )
            
            if created:
                self.stdout.write(self.style.SUCCESS(f'  [+] Создана формула для роли: {role.name}'))
            else:
                # Обновляем существующую формулу
                for key, value in formula_data.items():
                    setattr(formula, key, value)
                formula.save()
                self.stdout.write(self.style.WARNING(f'  [*] Обновлена формула для роли: {role.name}'))
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Формулы расчета:'))
        self.stdout.write(self.style.SUCCESS('  • Статья: 10-20 баллов (зависит от роли)'))
        self.stdout.write(self.style.SUCCESS('  • Лайк: 0.3-0.7 балла'))
        self.stdout.write(self.style.SUCCESS('  • Комментарий: 0.5-1.5 балла'))
        self.stdout.write(self.style.SUCCESS('  • Просмотр: 0.005-0.015 балла'))
        self.stdout.write(self.style.SUCCESS('  • Выполненное задание: 5-10 баллов'))

