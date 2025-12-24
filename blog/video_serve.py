"""
Отдача видео файлов с поддержкой HTTP Range requests
Критично для воспроизведения длинных/больших видео
Оптимизировано для быстрой загрузки и воспроизведения
"""
import os
import re
import mimetypes
from django.http import StreamingHttpResponse, HttpResponseNotModified, Http404, HttpResponse
from django.views.decorators.http import require_GET, condition
from django.conf import settings
from wsgiref.util import FileWrapper
from django.utils.http import http_date
from datetime import datetime, timedelta


def get_video_etag(request, path):
    """Генерирует ETag для видео файла"""
    full_path = os.path.join(settings.MEDIA_ROOT, path)
    if os.path.exists(full_path):
        stat = os.stat(full_path)
        return f'"{stat.st_mtime}-{stat.st_size}"'
    return None


def get_video_last_modified(request, path):
    """Получает время последнего изменения файла"""
    full_path = os.path.join(settings.MEDIA_ROOT, path)
    if os.path.exists(full_path):
        return datetime.fromtimestamp(os.path.getmtime(full_path))
    return None


@require_GET
@condition(etag_func=get_video_etag, last_modified_func=get_video_last_modified)
def serve_video(request, path):
    """
    Отдача видео с поддержкой Range requests (HTTP 206)
    Оптимизировано для:
    - Быстрой загрузки (увеличенный буфер)
    - Перемотки видео
    - Частичной загрузки
    - Воспроизведения длинных файлов
    - Кэширования на клиенте
    """
    # Полный путь к файлу
    full_path = os.path.join(settings.MEDIA_ROOT, path)
    
    # Проверка существования
    if not os.path.exists(full_path) or not os.path.isfile(full_path):
        raise Http404("Видео не найдено")
    
    # Определяем MIME-type
    content_type, encoding = mimetypes.guess_type(full_path)
    if not content_type:
        # Определяем по расширению
        ext = os.path.splitext(full_path)[1].lower()
        mime_types = {
            '.mp4': 'video/mp4',
            '.webm': 'video/webm',
            '.mov': 'video/quicktime',
            '.avi': 'video/x-msvideo',
        }
        content_type = mime_types.get(ext, 'application/octet-stream')
    
    # Размер файла
    file_size = os.path.getsize(full_path)
    
    # Обработка Range запроса
    range_header = request.META.get('HTTP_RANGE', '').strip()
    range_match = re.match(r'bytes=(\d+)-(\d*)', range_header)
    
    if range_match:
        # Range request - частичная загрузка
        start = int(range_match.group(1))
        end = int(range_match.group(2)) if range_match.group(2) else file_size - 1
        
        # Защита от некорректных значений
        if start >= file_size:
            start = 0
        if end >= file_size:
            end = file_size - 1
        if start > end:
            start = 0
            end = file_size - 1
        
        length = end - start + 1
        
        # Открываем файл и перемещаемся к нужной позиции
        # Увеличенный буфер для лучшей производительности (64KB вместо 8KB)
        file_handle = open(full_path, 'rb')
        file_handle.seek(start)
        
        # Создаём потоковый ответ с частью файла
        response = StreamingHttpResponse(
            FileWrapper(file_handle, 65536),  # 64KB буфер для лучшей производительности
            status=206,  # Partial Content
            content_type=content_type
        )
        
        # Заголовки для Range response
        response['Content-Length'] = str(length)
        response['Content-Range'] = f'bytes {start}-{end}/{file_size}'
        response['Accept-Ranges'] = 'bytes'
        
    else:
        # Обычный запрос - весь файл
        # Для небольших файлов (< 50MB) можно отдать сразу
        if file_size < 50 * 1024 * 1024:  # 50MB
            with open(full_path, 'rb') as f:
                content = f.read()
            response = HttpResponse(content, content_type=content_type)
            response['Content-Length'] = str(file_size)
        else:
            # Большие файлы - потоково
            file_handle = open(full_path, 'rb')
            response = StreamingHttpResponse(
                FileWrapper(file_handle, 65536),  # 64KB буфер
                content_type=content_type
            )
            response['Content-Length'] = str(file_size)
        
        response['Accept-Ranges'] = 'bytes'
    
    # Оптимизированное кэширование
    # Для видео - долгое кэширование, но с проверкой изменений через ETag
    response['Cache-Control'] = 'public, max-age=31536000, immutable'
    response['ETag'] = get_video_etag(request, path)
    
    # CORS заголовки (если нужно)
    response['Access-Control-Allow-Origin'] = '*'
    response['Access-Control-Allow-Methods'] = 'GET, HEAD, OPTIONS'
    response['Access-Control-Expose-Headers'] = 'Content-Range, Content-Length, Accept-Ranges'
    
    return response

