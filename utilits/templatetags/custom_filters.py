from django import template

register = template.Library()

@register.filter(is_safe=False)
def length_is(value, arg):
    """Возвращает True, если длина value равна arg"""
    try:
        return len(value) == int(arg)
    except (ValueError, TypeError):
        return False