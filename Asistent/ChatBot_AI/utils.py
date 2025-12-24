"""
Утилиты для чат-бота
"""


def get_client_ip(request):
    """
    Получить IP адрес клиента
    
    Args:
        request: Django request object
        
    Returns:
        str: IP адрес клиента
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    ip = x_forwarded_for.split(',')[0] if x_forwarded_for else request.META.get('REMOTE_ADDR')
    return ip

