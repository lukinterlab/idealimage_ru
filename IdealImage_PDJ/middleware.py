"""
Middleware для правильной отдачи медиа файлов
"""
import mimetypes

# Регистрируем WebP MIME-type
mimetypes.add_type('image/webp', '.webp')
mimetypes.add_type('video/mp4', '.mp4')
mimetypes.add_type('video/webm', '.webm')

class MediaMimeTypeMiddleware:
    """
    Middleware для установки правильного Content-Type для медиа файлов
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        # Если это media файл
        if request.path.startswith('/media/'):
            # Определяем MIME-type по расширению
            content_type, encoding = mimetypes.guess_type(request.path)
            
            if content_type:
                response['Content-Type'] = content_type
                
            # Добавляем кэширование для медиа
            response['Cache-Control'] = 'public, max-age=31536000'
        
        return response

