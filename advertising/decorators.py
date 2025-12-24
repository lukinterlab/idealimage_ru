"""
Декораторы для проверки доступа к функциям управления рекламой
"""
from functools import wraps
from django.http import HttpResponseForbidden
from django.shortcuts import redirect


def marketing_required(view_func):
    """
    Декоратор для проверки прав доступа к управлению рекламой
    Доступ имеют: staff, маркетологи
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('Visitor:user-login')
        
        # Проверка прав доступа
        is_staff = request.user.is_staff
        is_marketer = hasattr(request.user, 'profile') and request.user.profile.is_marketer
        
        if not (is_staff or is_marketer):
            return HttpResponseForbidden(
                '<h1>Доступ запрещен</h1>'
                '<p>У вас нет прав для доступа к панели управления рекламой.</p>'
                '<p>Требуется роль: Администратор или Маркетолог</p>'
            )
        
        return view_func(request, *args, **kwargs)
    return wrapper


def staff_or_marketer_required(function=None):
    """
    Альтернативный декоратор для проверки прав
    Использование: @staff_or_marketer_required
    """
    actual_decorator = marketing_required
    if function:
        return actual_decorator(function)
    return actual_decorator

