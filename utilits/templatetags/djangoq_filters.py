"""
Template tags для работы с Django-Q задачами
"""
from django import template
from utilits.djangoq_translations import get_task_description, format_task_with_description

register = template.Library()


@register.filter(name='task_description')
def task_description(task_name):
    """
    Фильтр для получения русского описания задачи
    
    Использование в шаблоне:
        {{ task.name|task_description }}
    """
    return get_task_description(task_name)


@register.filter(name='task_formatted')
def task_formatted(task_name):
    """
    Фильтр для форматированного вывода задачи с описанием
    
    Использование в шаблоне:
        {{ task.name|task_formatted }}
    """
    return format_task_with_description(task_name)


@register.simple_tag
def get_task_info(task_name):
    """
    Простой тег для получения информации о задаче
    
    Использование в шаблоне:
        {% get_task_info task.name %}
    """
    return {
        'name': task_name,
        'description': get_task_description(task_name),
        'formatted': format_task_with_description(task_name)
    }

