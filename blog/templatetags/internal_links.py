"""
Template tags для автоматической внутренней перелинковки
"""
from django import template
from blog.services.internal_linking import get_internal_links_block

register = template.Library()


@register.simple_tag
def show_internal_links(post, count=3):
    """
    Показывает блок автоматических внутренних ссылок
    
    Args:
        post: Текущая статья
        count: Количество ссылок
    
    Returns:
        HTML блок с ссылками
    """
    return get_internal_links_block(post, count)

