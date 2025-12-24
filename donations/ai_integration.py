"""
Модуль интеграции системы бонусов с AI агентом
"""
import json
import re
from decimal import Decimal
from django.contrib.auth.models import User
from django.utils import timezone
from django.db import transaction
import logging

from .models import (
    AIBonusCommand, AuthorRole, BonusFormula,
    AuthorPenaltyReward, AuthorBonus
)

logger = logging.getLogger(__name__)


def parse_ai_command(message_obj):
    """
    Парсить команду из сообщения AI
    
    Args:
        message_obj: AIMessage объект
    
    Returns:
        list: список найденных команд (dict)
    """
    commands = []
    
    # Проверяем metadata на наличие команд
    if message_obj.metadata and 'bonus_commands' in message_obj.metadata:
        # Команды в формате JSON в metadata
        metadata_commands = message_obj.metadata['bonus_commands']
        if isinstance(metadata_commands, list):
            commands.extend(metadata_commands)
        elif isinstance(metadata_commands, dict):
            commands.append(metadata_commands)
    
    # Парсим текст сообщения на наличие команд в специальном формате
    # Формат: [BONUS_COMMAND: {...json...}]
    pattern = r'\[BONUS_COMMAND:\s*(\{[^\]]+\})\]'
    matches = re.findall(pattern, message_obj.content, re.DOTALL)
    
    for match in matches:
        try:
            command_data = json.loads(match)
            commands.append(command_data)
        except json.JSONDecodeError as e:
            logger.error(f'Ошибка парсинга команды из текста: {str(e)}')
    
    logger.info(f'Найдено {len(commands)} команд в сообщении AI')
    return commands


def validate_command(command_data):
    """
    Валидировать команду перед выполнением
    
    Args:
        command_data: dict с данными команды
    
    Returns:
        tuple: (is_valid, error_message)
    """
    required_fields = ['command']
    
    # Проверяем обязательные поля
    for field in required_fields:
        if field not in command_data:
            return False, f'Отсутствует обязательное поле: {field}'
    
    command_type = command_data['command']
    
    # Валидация в зависимости от типа команды
    if command_type == 'add_penalty' or command_type == 'add_reward':
        required = ['author_id', 'amount', 'amount_type', 'reason', 'applied_to']
        for field in required:
            if field not in command_data:
                return False, f'Отсутствует обязательное поле для штрафа/премии: {field}'
        
        # Проверяем существование автора
        try:
            User.objects.get(id=command_data['author_id'])
        except User.DoesNotExist:
            return False, f'Автор с ID {command_data["author_id"]} не найден'
        
        # Проверяем amount_type
        if command_data['amount_type'] not in ['fixed', 'percentage']:
            return False, f'Неверный amount_type: {command_data["amount_type"]}'
        
        # Проверяем applied_to
        if command_data['applied_to'] not in ['one_time', 'weekly', 'monthly']:
            return False, f'Неверный applied_to: {command_data["applied_to"]}'
    
    elif command_type == 'update_formula':
        required = ['role_id']
        for field in required:
            if field not in command_data:
                return False, f'Отсутствует обязательное поле для обновления формулы: {field}'
        
        # Проверяем существование роли
        try:
            AuthorRole.objects.get(id=command_data['role_id'])
        except AuthorRole.DoesNotExist:
            return False, f'Роль с ID {command_data["role_id"]} не найдена'
    
    elif command_type == 'change_role_percentage':
        required = ['role_id', 'new_percentage']
        for field in required:
            if field not in command_data:
                return False, f'Отсутствует обязательное поле для изменения процента: {field}'
        
        # Проверяем существование роли
        try:
            AuthorRole.objects.get(id=command_data['role_id'])
        except AuthorRole.DoesNotExist:
            return False, f'Роль с ID {command_data["role_id"]} не найдена'
    
    elif command_type == 'adjust_bonus':
        required = ['author_id', 'adjustment_amount', 'reason']
        for field in required:
            if field not in command_data:
                return False, f'Отсутствует обязательное поле для корректировки бонуса: {field}'
        
        # Проверяем существование автора
        try:
            User.objects.get(id=command_data['author_id'])
        except User.DoesNotExist:
            return False, f'Автор с ID {command_data["author_id"]} не найден'
    
    else:
        return False, f'Неизвестный тип команды: {command_type}'
    
    return True, 'OK'


def execute_bonus_command(command_obj):
    """
    Выполнить команду по бонусам
    
    Args:
        command_obj: AIBonusCommand объект
    
    Returns:
        dict: результат выполнения
    """
    if command_obj.executed:
        logger.warning(f'Команда {command_obj.id} уже выполнена')
        return {
            'success': False,
            'error': 'Команда уже выполнена'
        }
    
    logger.info(f'Выполнение команды {command_obj.command_type} для {command_obj.target_author}')
    
    try:
        with transaction.atomic():
            result = {}
            
            if command_obj.command_type == 'add_penalty':
                result = _execute_add_penalty(command_obj)
            
            elif command_obj.command_type == 'add_reward':
                result = _execute_add_reward(command_obj)
            
            elif command_obj.command_type == 'update_formula':
                result = _execute_update_formula(command_obj)
            
            elif command_obj.command_type == 'change_role_percentage':
                result = _execute_change_role_percentage(command_obj)
            
            elif command_obj.command_type == 'adjust_bonus':
                result = _execute_adjust_bonus(command_obj)
            
            else:
                result = {
                    'success': False,
                    'error': f'Неизвестный тип команды: {command_obj.command_type}'
                }
            
            # Отмечаем команду как выполненную
            command_obj.executed = True
            command_obj.executed_at = timezone.now()
            command_obj.result = result
            command_obj.save()
            
            return result
    
    except Exception as e:
        logger.error(f'Ошибка выполнения команды: {str(e)}')
        command_obj.result = {
            'success': False,
            'error': str(e)
        }
        command_obj.save()
        return command_obj.result


def _execute_add_penalty(command_obj):
    """Добавить штраф"""
    params = command_obj.parameters
    
    penalty = AuthorPenaltyReward.objects.create(
        author=command_obj.target_author,
        type='penalty',
        amount=Decimal(str(params['amount'])),
        amount_type=params['amount_type'],
        reason=params['reason'],
        applied_to=params['applied_to'],
        applied_from=timezone.now(),
        applied_until=params.get('applied_until'),
        created_by=command_obj.conversation.admin,
        is_active=True
    )
    
    return {
        'success': True,
        'penalty_id': penalty.id,
        'author': command_obj.target_author.username,
        'amount': float(penalty.amount),
        'message': f'Штраф {penalty.amount}₽ добавлен для {command_obj.target_author.username}'
    }


def _execute_add_reward(command_obj):
    """Добавить премию"""
    params = command_obj.parameters
    
    reward = AuthorPenaltyReward.objects.create(
        author=command_obj.target_author,
        type='reward',
        amount=Decimal(str(params['amount'])),
        amount_type=params['amount_type'],
        reason=params['reason'],
        applied_to=params['applied_to'],
        applied_from=timezone.now(),
        applied_until=params.get('applied_until'),
        created_by=command_obj.conversation.admin,
        is_active=True
    )
    
    return {
        'success': True,
        'reward_id': reward.id,
        'author': command_obj.target_author.username,
        'amount': float(reward.amount),
        'message': f'Премия {reward.amount}₽ добавлена для {command_obj.target_author.username}'
    }


def _execute_update_formula(command_obj):
    """Обновить формулу расчета"""
    params = command_obj.parameters
    
    role = AuthorRole.objects.get(id=params['role_id'])
    formula = role.formula
    
    # Обновляем веса, если они указаны
    updated_fields = []
    
    if 'articles_weight' in params:
        formula.articles_weight = Decimal(str(params['articles_weight']))
        updated_fields.append('articles_weight')
    
    if 'likes_weight' in params:
        formula.likes_weight = Decimal(str(params['likes_weight']))
        updated_fields.append('likes_weight')
    
    if 'comments_weight' in params:
        formula.comments_weight = Decimal(str(params['comments_weight']))
        updated_fields.append('comments_weight')
    
    if 'views_weight' in params:
        formula.views_weight = Decimal(str(params['views_weight']))
        updated_fields.append('views_weight')
    
    if 'tasks_weight' in params:
        formula.tasks_weight = Decimal(str(params['tasks_weight']))
        updated_fields.append('tasks_weight')
    
    if 'min_points_required' in params:
        formula.min_points_required = Decimal(str(params['min_points_required']))
        updated_fields.append('min_points_required')
    
    if 'min_articles_required' in params:
        formula.min_articles_required = int(params['min_articles_required'])
        updated_fields.append('min_articles_required')
    
    formula.save()
    
    return {
        'success': True,
        'formula_id': formula.id,
        'role': role.name,
        'updated_fields': updated_fields,
        'message': f'Формула для роли {role.name} обновлена'
    }


def _execute_change_role_percentage(command_obj):
    """Изменить процент бонуса для роли"""
    params = command_obj.parameters
    
    role = AuthorRole.objects.get(id=params['role_id'])
    old_percentage = role.bonus_percentage
    role.bonus_percentage = Decimal(str(params['new_percentage']))
    role.save()
    
    return {
        'success': True,
        'role_id': role.id,
        'role': role.name,
        'old_percentage': float(old_percentage),
        'new_percentage': float(role.bonus_percentage),
        'message': f'Процент для роли {role.name} изменен с {old_percentage}% на {role.bonus_percentage}%'
    }


def _execute_adjust_bonus(command_obj):
    """Скорректировать бонус автора"""
    params = command_obj.parameters
    
    # Находим последний бонус автора
    latest_bonus = AuthorBonus.objects.filter(
        author=command_obj.target_author,
        status='approved'
    ).order_by('-period_start').first()
    
    if not latest_bonus:
        return {
            'success': False,
            'error': f'Не найден утвержденный бонус для {command_obj.target_author.username}'
        }
    
    adjustment = Decimal(str(params['adjustment_amount']))
    old_total = latest_bonus.total_bonus
    latest_bonus.total_bonus += adjustment
    
    # Не даем бонусу уйти в минус
    if latest_bonus.total_bonus < 0:
        latest_bonus.total_bonus = Decimal('0.00')
    
    # Добавляем примечание
    reason = params.get('reason', 'Корректировка от AI агента')
    if latest_bonus.notes:
        latest_bonus.notes += f'\n\nКорректировка {adjustment}₽: {reason}'
    else:
        latest_bonus.notes = f'Корректировка {adjustment}₽: {reason}'
    
    latest_bonus.save()
    
    return {
        'success': True,
        'bonus_id': latest_bonus.id,
        'author': command_obj.target_author.username,
        'old_total': float(old_total),
        'adjustment': float(adjustment),
        'new_total': float(latest_bonus.total_bonus),
        'message': f'Бонус для {command_obj.target_author.username} скорректирован: {old_total}₽ → {latest_bonus.total_bonus}₽'
    }


def create_bonus_command_from_message(message_obj, command_data):
    """
    Создать AIBonusCommand из сообщения и данных команды
    
    Args:
        message_obj: AIMessage объект
        command_data: dict с данными команды
    
    Returns:
        AIBonusCommand объект
    """
    # Валидируем команду
    is_valid, error_message = validate_command(command_data)
    
    if not is_valid:
        logger.error(f'Невалидная команда: {error_message}')
        # Создаем команду с ошибкой
        command = AIBonusCommand.objects.create(
            conversation=message_obj.conversation,
            message=message_obj,
            command_type='update_formula',  # fallback
            parameters=command_data,
            executed=True,
            executed_at=timezone.now(),
            result={
                'success': False,
                'error': error_message
            }
        )
        return command
    
    # Определяем тип команды
    command_type_map = {
        'add_penalty': 'add_penalty',
        'add_reward': 'add_reward',
        'update_formula': 'update_formula',
        'change_role_percentage': 'change_role_percentage',
        'adjust_bonus': 'adjust_bonus',
    }
    
    command_type = command_type_map.get(command_data['command'], 'update_formula')
    
    # Определяем целевого автора
    target_author = None
    if 'author_id' in command_data:
        try:
            target_author = User.objects.get(id=command_data['author_id'])
        except User.DoesNotExist:
            pass
    
    # Создаем команду
    command = AIBonusCommand.objects.create(
        conversation=message_obj.conversation,
        message=message_obj,
        command_type=command_type,
        target_author=target_author,
        parameters=command_data
    )
    
    logger.info(f'Создана команда {command.command_type} (ID: {command.id})')
    
    return command


def process_ai_message_for_commands(message_obj):
    """
    Обработать сообщение AI на наличие команд и выполнить их
    
    Args:
        message_obj: AIMessage объект
    
    Returns:
        list: список результатов выполнения команд
    """
    # Парсим команды из сообщения
    commands_data = parse_ai_command(message_obj)
    
    if not commands_data:
        return []
    
    results = []
    
    for command_data in commands_data:
        # Создаем объект команды
        command_obj = create_bonus_command_from_message(message_obj, command_data)
        
        # Выполняем команду
        result = execute_bonus_command(command_obj)
        results.append(result)
    
    return results


def get_bonus_command_help_text():
    """
    Получить справочный текст для AI агента о доступных командах
    
    Returns:
        str: справочный текст
    """
    help_text = """
# Команды для управления системой бонусов

AI агент может управлять системой бонусов, добавляя специальные команды в свои сообщения.

## Формат команд

Команды должны быть в формате JSON и помещены в специальный тег:
[BONUS_COMMAND: {...json...}]

Или в metadata сообщения в поле 'bonus_commands'.

## Доступные команды:

### 1. Добавить штраф
```json
{
    "command": "add_penalty",
    "author_id": 5,
    "amount": 100,
    "amount_type": "fixed",  // или "percentage"
    "reason": "Нарушение сроков",
    "applied_to": "one_time",  // или "weekly", "monthly"
    "applied_until": "2025-12-31T23:59:59"  // опционально
}
```

### 2. Добавить премию
```json
{
    "command": "add_reward",
    "author_id": 5,
    "amount": 500,
    "amount_type": "fixed",
    "reason": "Отличная работа",
    "applied_to": "one_time"
}
```

### 3. Обновить формулу расчета
```json
{
    "command": "update_formula",
    "role_id": 2,
    "articles_weight": 15.0,
    "likes_weight": 0.75,
    "comments_weight": 1.5,
    "views_weight": 0.02,
    "tasks_weight": 7.0,
    "min_points_required": 50.0,
    "min_articles_required": 3
}
```

### 4. Изменить процент бонуса для роли
```json
{
    "command": "change_role_percentage",
    "role_id": 2,
    "new_percentage": 25.0
}
```

### 5. Скорректировать бонус
```json
{
    "command": "adjust_bonus",
    "author_id": 5,
    "adjustment_amount": 100.0,  // может быть отрицательным
    "reason": "Дополнительная премия за качество"
}
```

## Примечания:
- Все команды выполняются автоматически при получении сообщения от AI
- Результаты выполнения сохраняются в AIBonusCommand
- При ошибке команда помечается как выполненная с ошибкой
"""
    return help_text

