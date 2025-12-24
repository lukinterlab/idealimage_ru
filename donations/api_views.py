"""
API views для системы бонусов (AJAX endpoints)
"""
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from django.utils import timezone
from decimal import Decimal
import json
import logging

from .models import (
    AuthorStats, AuthorBonus, AuthorRole, BonusFormula,
    AuthorPenaltyReward, BonusPaymentRegistry, WeeklyReport
)
from .bonus_calculator import (
    calculate_author_stats, calculate_bonus, get_author_stats_summary
)
from .weekly_processor import (
    get_week_boundaries, generate_weekly_report, mark_payment_as_paid
)

logger = logging.getLogger(__name__)


@require_GET
@login_required
def api_author_stats(request, author_id):
    """
    Получить статистику автора в JSON
    """
    try:
        author = get_object_or_404(User, id=author_id)
        
        # Проверка прав: автор может смотреть только свою статистику
        if not request.user.is_staff and request.user != author:
            return JsonResponse({'error': 'Нет доступа'}, status=403)
        
        period_type = request.GET.get('period', 'week')
        stats = get_author_stats_summary(author, period_type)
        
        return JsonResponse({
            'success': True,
            'author': {
                'id': author.id,
                'username': author.username,
                'full_name': author.get_full_name() or author.username
            },
            'stats': stats
        })
    
    except Exception as e:
        logger.error(f'Ошибка API api_author_stats: {str(e)}')
        return JsonResponse({'error': str(e)}, status=500)


@require_GET
@staff_member_required
def api_current_week_stats(request):
    """
    Получить статистику за текущую неделю
    """
    try:
        from .weekly_processor import get_current_week_summary
        
        summary = get_current_week_summary()
        
        return JsonResponse({
            'success': True,
            'week_summary': summary
        })
    
    except Exception as e:
        logger.error(f'Ошибка API api_current_week_stats: {str(e)}')
        return JsonResponse({'error': str(e)}, status=500)


@require_POST
@staff_member_required
def api_calculate_preview(request):
    """
    Предварительный расчет бонуса для автора
    """
    try:
        data = json.loads(request.body)
        author_id = data.get('author_id')
        
        if not author_id:
            return JsonResponse({'error': 'author_id обязателен'}, status=400)
        
        author = get_object_or_404(User, id=author_id)
        week_start, week_end = get_week_boundaries()
        
        # Рассчитываем статистику и бонус
        stats = calculate_author_stats(author, week_start, week_end)
        bonus = calculate_bonus(author, week_start, week_end)
        
        return JsonResponse({
            'success': True,
            'preview': {
                'author': author.username,
                'role': stats.current_role.name if stats.current_role else 'Стажёр',
                'points': float(stats.calculated_points),
                'bonus_from_donations': float(bonus.calculated_bonus),
                'bonus_from_tasks': float(bonus.tasks_reward),
                'bonus_from_points': float(bonus.bonus_from_points),
                'total_bonus': float(bonus.total_bonus),
            }
        })
    
    except Exception as e:
        logger.error(f'Ошибка API api_calculate_preview: {str(e)}')
        return JsonResponse({'error': str(e)}, status=500)


@require_POST
@staff_member_required
def api_mark_payment(request):
    """
    Отметить выплату как оплаченную
    """
    try:
        data = json.loads(request.body)
        registry_id = data.get('registry_id')
        paid_amount = data.get('paid_amount')
        payment_method = data.get('payment_method', '')
        payment_note = data.get('payment_note', '')
        
        if not registry_id or paid_amount is None:
            return JsonResponse({'error': 'Недостаточно данных'}, status=400)
        
        registry_entry = get_object_or_404(BonusPaymentRegistry, id=registry_id)
        paid_amount = Decimal(str(paid_amount))
        
        # Отмечаем оплату
        mark_payment_as_paid(
            registry_entry,
            paid_amount,
            payment_method,
            payment_note,
            request.user
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Выплата отмечена: {paid_amount}₽',
            'entry': {
                'id': registry_entry.id,
                'status': registry_entry.get_status_display(),
                'paid_amount': float(registry_entry.paid_amount),
            }
        })
    
    except Exception as e:
        logger.error(f'Ошибка API api_mark_payment: {str(e)}')
        return JsonResponse({'error': str(e)}, status=500)


@require_POST
@staff_member_required
def api_add_penalty_reward(request):
    """
    Добавить штраф или премию
    """
    try:
        data = json.loads(request.body)
        
        required_fields = ['author_id', 'type', 'amount', 'amount_type', 'reason', 'applied_to']
        for field in required_fields:
            if field not in data:
                return JsonResponse({'error': f'Поле {field} обязательно'}, status=400)
        
        author = get_object_or_404(User, id=data['author_id'])
        
        # Создаем штраф/премию
        pr = AuthorPenaltyReward.objects.create(
            author=author,
            type=data['type'],
            amount=Decimal(str(data['amount'])),
            amount_type=data['amount_type'],
            reason=data['reason'],
            applied_to=data['applied_to'],
            applied_from=timezone.now(),
            applied_until=data.get('applied_until'),
            created_by=request.user,
            is_active=True
        )
        
        return JsonResponse({
            'success': True,
            'message': f'{"Штраф" if pr.type == "penalty" else "Премия"} добавлен(а)',
            'penalty_reward': {
                'id': pr.id,
                'type': pr.get_type_display(),
                'amount': float(pr.amount),
                'author': author.username
            }
        })
    
    except Exception as e:
        logger.error(f'Ошибка API api_add_penalty_reward: {str(e)}')
        return JsonResponse({'error': str(e)}, status=500)


@require_POST
@staff_member_required
def api_update_formula(request):
    """
    Обновить формулу расчета для роли
    """
    try:
        data = json.loads(request.body)
        role_id = data.get('role_id')
        
        if not role_id:
            return JsonResponse({'error': 'role_id обязателен'}, status=400)
        
        role = get_object_or_404(AuthorRole, id=role_id)
        formula = role.formula
        
        # Обновляем веса
        updated_fields = []
        
        for field in ['articles_weight', 'likes_weight', 'comments_weight', 
                      'views_weight', 'tasks_weight', 'min_points_required', 
                      'min_articles_required']:
            if field in data:
                setattr(formula, field, Decimal(str(data[field])) if 'weight' in field or 'points' in field else int(data[field]))
                updated_fields.append(field)
        
        formula.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Формула для роли {role.name} обновлена',
            'updated_fields': updated_fields
        })
    
    except Exception as e:
        logger.error(f'Ошибка API api_update_formula: {str(e)}')
        return JsonResponse({'error': str(e)}, status=500)


@require_POST
@staff_member_required
def api_generate_report(request):
    """
    Запустить генерацию недельного отчета
    """
    try:
        from .weekly_processor import get_previous_week_boundaries
        
        week_start, week_end = get_previous_week_boundaries()
        
        # Генерируем отчет
        report = generate_weekly_report(week_start, week_end, force=True)
        
        return JsonResponse({
            'success': True,
            'message': f'Отчет сгенерирован за {week_start.date()} - {week_end.date()}',
            'report': {
                'id': report.id,
                'authors_count': report.authors_count,
                'total_bonuses': float(report.total_bonuses),
                'total_donations': float(report.total_donations),
            }
        })
    
    except Exception as e:
        logger.error(f'Ошибка API api_generate_report: {str(e)}')
        return JsonResponse({'error': str(e)}, status=500)


@require_GET
@staff_member_required
def api_author_detail_stats(request, author_id):
    """
    Детальная статистика автора для модального окна
    """
    try:
        author = get_object_or_404(User, id=author_id)
        
        # Статистика за текущую неделю
        week_stats = get_author_stats_summary(author, 'week')
        
        # Последний бонус
        latest_bonus = AuthorBonus.objects.filter(
            author=author
        ).order_by('-period_start').first()
        
        # Активные корректировки
        penalties_rewards = AuthorPenaltyReward.objects.filter(
            author=author,
            is_active=True
        ).values('type', 'amount', 'amount_type', 'reason')
        
        return JsonResponse({
            'success': True,
            'author': {
                'id': author.id,
                'username': author.username,
                'full_name': author.get_full_name() or author.username,
                'email': author.email
            },
            'week_stats': week_stats,
            'latest_bonus': {
                'total': float(latest_bonus.total_bonus) if latest_bonus else 0,
                'status': latest_bonus.get_status_display() if latest_bonus else 'Нет данных',
                'period': f'{latest_bonus.period_start.date()} - {latest_bonus.period_end.date()}' if latest_bonus else ''
            } if latest_bonus else None,
            'penalties_rewards': list(penalties_rewards)
        })
    
    except Exception as e:
        logger.error(f'Ошибка API api_author_detail_stats: {str(e)}')
        return JsonResponse({'error': str(e)}, status=500)


@require_GET
@staff_member_required
def api_roles_list(request):
    """Получить список всех ролей с формулами"""
    try:
        roles = AuthorRole.objects.all().order_by('level')
        
        roles_data = []
        for role in roles:
            try:
                formula = role.formula
                formula_data = {
                    'id': formula.id,
                    'articles_weight': float(formula.articles_weight),
                    'likes_weight': float(formula.likes_weight),
                    'comments_weight': float(formula.comments_weight),
                    'views_weight': float(formula.views_weight),
                    'tasks_weight': float(formula.tasks_weight),
                    'min_points_required': float(formula.min_points_required),
                    'min_articles_required': formula.min_articles_required,
                    'is_active': formula.is_active
                }
            except BonusFormula.DoesNotExist:
                formula_data = None
            
            roles_data.append({
                'id': role.id,
                'name': role.name,
                'level': role.level,
                'bonus_percentage': float(role.bonus_percentage),
                'point_value': float(role.point_value),
                'description': role.description,
                'color': role.color,
                'formula': formula_data
            })
        
        return JsonResponse({
            'success': True,
            'roles': roles_data
        })
    
    except Exception as e:
        logger.error(f'Ошибка API api_roles_list: {str(e)}')
        return JsonResponse({'error': str(e)}, status=500)


@require_POST
@staff_member_required
def api_role_create(request):
    """Создать новую роль"""
    try:
        data = json.loads(request.body)
        
        role = AuthorRole.objects.create(
            name=data['name'],
            level=data['level'],
            bonus_percentage=Decimal(str(data.get('bonus_percentage', 0))),
            point_value=Decimal(str(data.get('point_value', 1.0))),
            description=data.get('description', ''),
            color=data.get('color', '#6B7280')
        )
        
        # Создаем формулу для роли
        formula = BonusFormula.objects.create(
            role=role,
            articles_weight=Decimal(str(data.get('articles_weight', 10.0))),
            likes_weight=Decimal(str(data.get('likes_weight', 0.5))),
            comments_weight=Decimal(str(data.get('comments_weight', 1.0))),
            views_weight=Decimal(str(data.get('views_weight', 0.01))),
            tasks_weight=Decimal(str(data.get('tasks_weight', 5.0))),
            min_points_required=Decimal(str(data.get('min_points_required', 0))),
            min_articles_required=data.get('min_articles_required', 0),
            is_active=True
        )
        
        logger.info(f'Создана новая роль: {role.name} (уровень {role.level})')
        
        return JsonResponse({
            'success': True,
            'message': f'Роль "{role.name}" успешно создана',
            'role': {
                'id': role.id,
                'name': role.name,
                'level': role.level
            }
        })
    
    except Exception as e:
        logger.error(f'Ошибка API api_role_create: {str(e)}')
        return JsonResponse({'error': str(e)}, status=500)


@require_POST
@staff_member_required
def api_role_update(request, role_id):
    """Обновить роль"""
    try:
        data = json.loads(request.body)
        role = get_object_or_404(AuthorRole, id=role_id)
        
        # Обновляем поля роли
        role.name = data.get('name', role.name)
        role.level = data.get('level', role.level)
        role.bonus_percentage = Decimal(str(data.get('bonus_percentage', role.bonus_percentage)))
        role.point_value = Decimal(str(data.get('point_value', role.point_value)))
        role.description = data.get('description', role.description)
        role.color = data.get('color', role.color)
        role.save()
        
        logger.info(f'Обновлена роль: {role.name}')
        
        return JsonResponse({
            'success': True,
            'message': f'Роль "{role.name}" успешно обновлена'
        })
    
    except Exception as e:
        logger.error(f'Ошибка API api_role_update: {str(e)}')
        return JsonResponse({'error': str(e)}, status=500)


@require_POST
@staff_member_required
def api_role_delete(request, role_id):
    """Удалить роль"""
    try:
        role = get_object_or_404(AuthorRole, id=role_id)
        role_name = role.name
        
        # Проверяем, не используется ли роль
        if AuthorStats.objects.filter(current_role=role).exists():
            return JsonResponse({
                'error': f'Роль "{role_name}" используется авторами и не может быть удалена'
            }, status=400)
        
        role.delete()
        logger.info(f'Удалена роль: {role_name}')
        
        return JsonResponse({
            'success': True,
            'message': f'Роль "{role_name}" успешно удалена'
        })
    
    except Exception as e:
        logger.error(f'Ошибка API api_role_delete: {str(e)}')
        return JsonResponse({'error': str(e)}, status=500)


@require_POST
@staff_member_required
def api_formula_update(request, role_id):
    """Обновить формулу для роли"""
    try:
        data = json.loads(request.body)
        role = get_object_or_404(AuthorRole, id=role_id)
        
        # Получаем или создаем формулу
        formula, created = BonusFormula.objects.get_or_create(
            role=role,
            defaults={
                'articles_weight': Decimal('10.0'),
                'likes_weight': Decimal('0.5'),
                'comments_weight': Decimal('1.0'),
                'views_weight': Decimal('0.01'),
                'tasks_weight': Decimal('5.0'),
            }
        )
        
        # Обновляем веса
        formula.articles_weight = Decimal(str(data.get('articles_weight', formula.articles_weight)))
        formula.likes_weight = Decimal(str(data.get('likes_weight', formula.likes_weight)))
        formula.comments_weight = Decimal(str(data.get('comments_weight', formula.comments_weight)))
        formula.views_weight = Decimal(str(data.get('views_weight', formula.views_weight)))
        formula.tasks_weight = Decimal(str(data.get('tasks_weight', formula.tasks_weight)))
        formula.min_points_required = Decimal(str(data.get('min_points_required', formula.min_points_required)))
        formula.min_articles_required = data.get('min_articles_required', formula.min_articles_required)
        formula.is_active = data.get('is_active', formula.is_active)
        formula.save()
        
        action = 'создана' if created else 'обновлена'
        logger.info(f'Формула {action} для роли: {role.name}')
        
        return JsonResponse({
            'success': True,
            'message': f'Формула для роли "{role.name}" успешно {action}'
        })
    
    except Exception as e:
        logger.error(f'Ошибка API api_formula_update: {str(e)}')
        return JsonResponse({'error': str(e)}, status=500)


@require_GET
@staff_member_required
def api_penalties_list(request):
    """Получить список всех активных штрафов/премий"""
    try:
        penalties = AuthorPenaltyReward.objects.filter(
            is_active=True
        ).select_related('author', 'created_by').order_by('-created_at')
        
        penalties_data = []
        for penalty in penalties:
            penalties_data.append({
                'id': penalty.id,
                'author': {
                    'id': penalty.author.id,
                    'username': penalty.author.username,
                    'full_name': penalty.author.get_full_name() or penalty.author.username
                },
                'type': penalty.type,
                'type_display': penalty.get_type_display(),
                'amount': float(penalty.amount),
                'amount_type': penalty.amount_type,
                'amount_type_display': penalty.get_amount_type_display(),
                'reason': penalty.reason,
                'applied_to': penalty.applied_to,
                'applied_to_display': penalty.get_applied_to_display(),
                'created_by': {
                    'username': penalty.created_by.username if penalty.created_by else 'Система'
                },
                'created_at': penalty.created_at.isoformat(),
                'expires_at': penalty.expires_at.isoformat() if penalty.expires_at else None
            })
        
        return JsonResponse({
            'success': True,
            'penalties': penalties_data
        })
    
    except Exception as e:
        logger.error(f'Ошибка API api_penalties_list: {str(e)}')
        return JsonResponse({'error': str(e)}, status=500)


@require_POST
@staff_member_required
def api_penalty_create(request):
    """Создать новый штраф/премию"""
    try:
        data = json.loads(request.body)
        
        author = get_object_or_404(User, id=data['author_id'])
        
        penalty = AuthorPenaltyReward.objects.create(
            author=author,
            type=data['type'],
            amount=Decimal(str(data['amount'])),
            amount_type=data['amount_type'],
            reason=data['reason'],
            applied_to=data.get('applied_to', 'one_time'),
            created_by=request.user,
            is_active=True
        )
        
        # Если указана дата истечения
        if data.get('expires_at'):
            from django.utils.dateparse import parse_datetime
            penalty.expires_at = parse_datetime(data['expires_at'])
            penalty.save()
        
        logger.info(f'Создан {penalty.get_type_display()}: {penalty.amount} для {author.username}')
        
        return JsonResponse({
            'success': True,
            'message': f'{penalty.get_type_display()} успешно добавлен(а)',
            'penalty': {
                'id': penalty.id
            }
        })
    
    except Exception as e:
        logger.error(f'Ошибка API api_penalty_create: {str(e)}')
        return JsonResponse({'error': str(e)}, status=500)


@require_POST
@staff_member_required
def api_penalty_update(request, penalty_id):
    """Обновить штраф/премию"""
    try:
        data = json.loads(request.body)
        penalty = get_object_or_404(AuthorPenaltyReward, id=penalty_id)
        
        # Обновляем поля
        if 'amount' in data:
            penalty.amount = Decimal(str(data['amount']))
        if 'reason' in data:
            penalty.reason = data['reason']
        if 'applied_to' in data:
            penalty.applied_to = data['applied_to']
        if 'is_active' in data:
            penalty.is_active = data['is_active']
        
        penalty.save()
        
        logger.info(f'Обновлен {penalty.get_type_display()} ID:{penalty.id}')
        
        return JsonResponse({
            'success': True,
            'message': f'{penalty.get_type_display()} успешно обновлен(а)'
        })
    
    except Exception as e:
        logger.error(f'Ошибка API api_penalty_update: {str(e)}')
        return JsonResponse({'error': str(e)}, status=500)


@require_POST
@staff_member_required
def api_penalty_delete(request, penalty_id):
    """Удалить (деактивировать) штраф/премию"""
    try:
        penalty = get_object_or_404(AuthorPenaltyReward, id=penalty_id)
        
        # Вместо удаления - деактивируем
        penalty.is_active = False
        penalty.save()
        
        logger.info(f'Деактивирован {penalty.get_type_display()} ID:{penalty.id}')
        
        return JsonResponse({
            'success': True,
            'message': f'{penalty.get_type_display()} успешно удален(а)'
        })
    
    except Exception as e:
        logger.error(f'Ошибка API api_penalty_delete: {str(e)}')
        return JsonResponse({'error': str(e)}, status=500)


@require_GET
@staff_member_required
def api_authors_list(request):
    """Получить список всех авторов для выбора"""
    try:
        # Получаем всех активных пользователей (кроме суперюзеров)
        # Включаем тех, у кого есть статьи, задания или любая активность
        authors = User.objects.filter(
            is_active=True,
            is_superuser=False
        ).order_by('username')
        
        authors_data = []
        for author in authors:
            # Проверяем, есть ли у автора хоть какая-то активность
            has_posts = author.posts.exists() if hasattr(author, 'posts') else False
            has_tasks = hasattr(author, 'task_assignments') and author.task_assignments.exists()
            
            # Добавляем всех пользователей (можно фильтровать по активности если нужно)
            authors_data.append({
                'id': author.id,
                'username': author.username,
                'full_name': author.get_full_name() or author.username,
                'email': author.email,
                'has_activity': has_posts or has_tasks
            })
        
        return JsonResponse({
            'success': True,
            'authors': authors_data,
            'count': len(authors_data)
        })
    
    except Exception as e:
        logger.error(f'Ошибка API api_authors_list: {str(e)}')
        return JsonResponse({'error': str(e)}, status=500)