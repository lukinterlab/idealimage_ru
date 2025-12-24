"""
Context processors для Asistent app
Добавляют данные во все шаблоны
"""
import logging
from django.utils import timezone

logger = logging.getLogger(__name__)


def gigachat_mini_widget(request):
    """
    Добавляет данные для GigaChat Mini Widget
    
    Вызывается только для авторизованных пользователей (staff)
    Обновляется каждые 5 минут через AJAX
    """
    # Проверяем что пользователь - администратор
    if not request.user.is_authenticated or not request.user.is_staff:
        return {}
    
    try:
        from .dashboard_helpers import get_all_models_balance, calculate_costs
        
        # Получаем компактные данные
        balances = get_all_models_balance()
        costs_today = calculate_costs('today')
        
        # Формируем упрощенные данные для виджета
        mini_stats = {
            'models': balances.get('models', [])[:4],  # Только 4 модели
            'cost_today': f"{costs_today.get('total', 0):.2f}",
            'timestamp': timezone.now(),
        }
        
        return {
            'gigachat_mini_stats': mini_stats
        }
        
    except Exception as e:
        logger.error(f"Ошибка context processor gigachat_mini_widget: {e}")
        # Возвращаем пустые данные при ошибке
        return {
            'gigachat_mini_stats': None
        }

