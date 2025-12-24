"""
Упрощенные функции для работы с промптами
БЕЗ автоматического определения модели - всегда GigaChat для текста
"""
import logging
import re
from typing import Dict, Optional
from django.utils.html import strip_tags
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from datetime import datetime, timedelta

from Asistent.models import PromptTemplate
from blog.models import Post, Category

# Импорт markdown с fallback
try:
    from markdown import markdown
    try:
        from markdown.extensions import fenced_code, tables, codehilite
    except ImportError:
        pass  # Расширения опциональны
    MARKDOWN_AVAILABLE = True
except ImportError:
    MARKDOWN_AVAILABLE = False
    # Fallback функция для markdown
    def markdown(text, extensions=None):
        """Простая замена markdown на HTML если библиотека не установлена"""
        if not text:
            return ""
        # Базовая замена переносов строк
        html = text.replace('\n', '<br>')
        # Замена заголовков
        import re
        html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)
        html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
        html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
        return html

logger = logging.getLogger(__name__)

# Константы таймаутов
GIGACHAT_TIMEOUT_ARTICLE = 300  # 5 минут для статей
GIGACHAT_TIMEOUT_TITLE = 60     # 1 минута для заголовков


def render_template_text(template_text: str, variables: Dict) -> str:
    """
    Рендеринг шаблона промпта с подстановкой переменных.
    
    Args:
        template_text: Текст шаблона с {переменными}
        variables: Словарь переменных для подстановки
    
    Returns:
        Отрендеренный текст
    """
    if not template_text:
        return ""
    
    try:
        return template_text.format(**variables)
    except KeyError as e:
        logger.warning(f"Отсутствует переменная {e} при рендеринге шаблона")
        # Пытаемся подставить доступные переменные
        result = template_text
        for key, value in variables.items():
            result = result.replace(f"{{{key}}}", str(value))
        return result
    except Exception as e:
        logger.error(f"Ошибка рендеринга шаблона: {e}")
        return template_text


def _clean_ai_markers(text: str) -> str:
    """
    Очищает текст от маркеров, которые добавляет AI:
    - ## Основная статья
    - ## Блок FAQ
    - Хештеги (#)
    - Звёздочки (*)
    """
    if not text:
        return ""
    
    lines = text.split('\n')
    cleaned_lines = []
    
    markers_to_remove = [
        r'^#+\s*Основная\s+статья\s*#*',
        r'^#+\s*Блок\s+FAQ\s*#*',
        r'^#+\s*Основная\s+статья',
        r'^#+\s*FAQ',
    ]
    
    for line in lines:
        # Удаляем маркеры
        should_skip = False
        for pattern in markers_to_remove:
            if re.match(pattern, line, re.IGNORECASE):
                should_skip = True
                break
        
        if should_skip:
            continue
        
        # Удаляем хештеги в начале строки
        line = re.sub(r'^#+\s*', '', line)
        
        # Удаляем звёздочки в начале строки (markdown списки, но оставляем форматирование)
        # Не удаляем полностью, только лишние
        
        cleaned_lines.append(line)
    
    return '\n'.join(cleaned_lines).strip()


def _convert_markdown_to_html(text: str) -> str:
    """
    Преобразует markdown в HTML для CKEditor.
    Сначала очищает от AI маркеров.
    """
    if not text:
        return ""
    
    # Очищаем от маркеров AI
    cleaned_text = _clean_ai_markers(text)
    
    # Конвертируем markdown в HTML
    if MARKDOWN_AVAILABLE:
        html = markdown(
            cleaned_text,
            extensions=[
                'fenced_code',
                'tables',
                'codehilite',
            ]
        )
    else:
        # Fallback: простая замена
        html = cleaned_text.replace('\n', '<br>')
    
    return html


@staff_member_required
@require_http_methods(["GET", "POST"])
def prompt_template_test(request, template_id):
    """
    Тестирование промпт шаблона с генерацией статьи.
    
    Поддерживает действия:
    - test: Запуск теста генерации
    - publish: Публикация тестовой статьи
    - draft: Сохранение в черновики
    - queue: Планирование публикации
    - delete: Удаление тестовой статьи из сессии
    """
    template = get_object_or_404(PromptTemplate, id=template_id)
    
    # Получаем тестовые данные из сессии
    session_key = f'prompt_test_{template_id}'
    test_data = request.session.get(session_key, {})
    
    # Обработка POST запросов
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'test':
            # Запуск теста генерации
            variables = {}
            
            # Собираем переменные из формы
            for key in request.POST.keys():
                if key.startswith('var_'):
                    var_name = key[4:]  # Убираем префикс 'var_'
                    var_value = request.POST.get(key, '').strip()
                    if var_value:
                        variables[var_name] = var_value
            
            try:
                # Ленивый импорт для избежания циклических зависимостей
                from Asistent.generators.universal import UniversalContentGenerator
                from Asistent.generators.base import GeneratorConfig
                
                # Создаем генератор в интерактивном режиме
                config = GeneratorConfig.for_interactive()
                generator = UniversalContentGenerator(template, config)
                
                # Генерируем контент
                result = generator.generate(variables=variables)
                
                logger.info(f"Результат генерации: success={result.success}, title={result.title}, content_len={len(result.content) if result.content else 0}")
                logger.info(f"Session key: {session_key}")
                logger.info(f"Result content preview: {result.content[:200] if result.content else 'EMPTY'}...")
                
                if result.success:
                    # Сохраняем в сессию
                    plain_text = result.session_data.get('plain_text', '') if result.session_data else ''
                    if not plain_text and result.content:
                        # Если plain_text нет, извлекаем из HTML
                        plain_text = strip_tags(result.content)
                    
                    session_data = {
                        'title': result.title or 'Без заголовка',
                        'content': result.content or '',
                        'content_full': result.content or '',  # Для шаблона
                        'plain_text': plain_text,
                        'image_path': result.image_path,
                        'image_info': 'Изображение сгенерировано' if result.image_path else 'Изображение не сгенерировано',
                        'tags': result.session_data.get('tags', []) if result.session_data else [],
                        'word_count': len(plain_text.split()) if plain_text else 0,
                        'category': template.blog_category.title if template.blog_category else 'Без категории',
                        'show_image_section': True,
                        'image_source_type_debug': template.image_source_type,
                        'image_criteria_debug': template.image_generation_criteria or template.image_search_criteria,
                        'success': True,
                        'message': 'Тест выполнен успешно',
                    }
                    
                    logger.info(f"Сохраняем в сессию: title={session_data['title']}, content_len={len(session_data['content'])}, success={session_data['success']}")
                    
                    request.session[session_key] = session_data
                    # Явно сохраняем сессию
                    request.session.modified = True
                    request.session.save()
                    
                    logger.info(f"Сессия сохранена. Проверка: {request.session.get(session_key, {}).get('title', 'NOT FOUND')}")
                    
                    messages.success(request, 'Тест выполнен успешно!')
                else:
                    messages.error(request, f'Ошибка генерации: {result.error}')
                    
            except Exception as e:
                logger.exception(f"Ошибка тестирования промпта: {e}")
                messages.error(request, f'Ошибка: {str(e)}')
            
            return redirect('asistent:prompt_template_test', template_id=template_id)
        
        elif action == 'publish':
            # Публикация статьи
            if not test_data:
                messages.error(request, 'Нет данных для публикации. Сначала запустите тест.')
                return redirect('asistent:prompt_template_test', template_id=template_id)
            
            try:
                # Создаем пост
                post = Post.objects.create(
                    title=test_data['title'],
                    content=test_data['content'],
                    author=template.default_author or request.user,
                    category=template.blog_category,
                    status='published',
                    kartinka=test_data.get('image_path') if test_data.get('image_path') else None,
                )
                
                # Добавляем теги если есть
                if test_data.get('tags'):
                    for tag_name in test_data['tags']:
                        from blog.models import Tag
                        tag, _ = Tag.objects.get_or_create(name=tag_name)
                        post.tags.add(tag)
                
                # Очищаем сессию
                del request.session[session_key]
                
                messages.success(request, f'Статья "{post.title}" опубликована!')
                return redirect('blog:post_detail', slug=post.slug)
                
            except Exception as e:
                logger.exception(f"Ошибка публикации: {e}")
                messages.error(request, f'Ошибка публикации: {str(e)}')
            
            return redirect('asistent:prompt_template_test', template_id=template_id)
        
        elif action == 'draft':
            # Сохранение в черновики
            if not test_data:
                messages.error(request, 'Нет данных для сохранения. Сначала запустите тест.')
                return redirect('asistent:prompt_template_test', template_id=template_id)
            
            try:
                post = Post.objects.create(
                    title=test_data['title'],
                    content=test_data['content'],
                    author=template.default_author or request.user,
                    category=template.blog_category,
                    status='draft',
                    kartinka=test_data.get('image_path') if test_data.get('image_path') else None,
                )
                
                if test_data.get('tags'):
                    for tag_name in test_data['tags']:
                        from blog.models import Tag
                        tag, _ = Tag.objects.get_or_create(name=tag_name)
                        post.tags.add(tag)
                
                del request.session[session_key]
                messages.success(request, f'Статья "{post.title}" сохранена в черновики!')
                return redirect('blog:post_detail', slug=post.slug)
                
            except Exception as e:
                logger.exception(f"Ошибка сохранения: {e}")
                messages.error(request, f'Ошибка сохранения: {str(e)}')
            
            return redirect('asistent:prompt_template_test', template_id=template_id)
        
        elif action == 'queue':
            # Планирование публикации
            if not test_data:
                messages.error(request, 'Нет данных для планирования. Сначала запустите тест.')
                return redirect('asistent:prompt_template_test', template_id=template_id)
            
            publish_date = request.POST.get('publish_date')
            publish_time = request.POST.get('publish_time')
            
            if not publish_date or not publish_time:
                messages.error(request, 'Укажите дату и время публикации.')
                return redirect('asistent:prompt_template_test', template_id=template_id)
            
            try:
                # Создаем datetime для публикации
                publish_datetime = datetime.strptime(
                    f"{publish_date} {publish_time}",
                    "%Y-%m-%d %H:%M"
                )
                publish_datetime = timezone.make_aware(publish_datetime)
                
                # Создаем пост с будущей датой публикации
                post = Post.objects.create(
                    title=test_data['title'],
                    content=test_data['content'],
                    author=template.default_author or request.user,
                    category=template.blog_category,
                    status='draft',  # Сначала черновик
                    kartinka=test_data.get('image_path') if test_data.get('image_path') else None,
                    publish_date=publish_datetime,
                )
                
                if test_data.get('tags'):
                    for tag_name in test_data['tags']:
                        from blog.models import Tag
                        tag, _ = Tag.objects.get_or_create(name=tag_name)
                        post.tags.add(tag)
                
                del request.session[session_key]
                messages.success(request, f'Статья "{post.title}" запланирована на {publish_datetime.strftime("%d.%m.%Y %H:%M")}!')
                return redirect('blog:post_detail', slug=post.slug)
                
            except Exception as e:
                logger.exception(f"Ошибка планирования: {e}")
                messages.error(request, f'Ошибка планирования: {str(e)}')
            
            return redirect('asistent:prompt_template_test', template_id=template_id)
        
        elif action == 'delete':
            # Удаление тестовых данных
            if session_key in request.session:
                del request.session[session_key]
                messages.info(request, 'Тестовые данные удалены.')
            
            return redirect('asistent:prompt_template_test', template_id=template_id)
    
    # GET запрос - отображение формы
    # Подготовка переменных для формы
    form_variables = []
    if template.variables:
        for var_name in template.variables:
            from django import forms
            field = forms.CharField(
                required=False,
                label=var_name.replace('_', ' ').title(),
                help_text=f'Переменная: {var_name}',
            )
            field.name = var_name
            form_variables.append(field)
    
    # Подготовка результата теста
    test_result = None
    if test_data:
        test_result = {
            'success': test_data.get('success', False),
            'title': test_data.get('title', ''),
            'content_full': test_data.get('content_full', ''),
            'image_path': test_data.get('image_path'),
            'image_info': test_data.get('image_info', ''),
            'tags': test_data.get('tags', []),
            'word_count': test_data.get('word_count', 0),
            'category': test_data.get('category', ''),
            'message': test_data.get('message', 'Тест выполнен'),
            'show_image_section': test_data.get('show_image_section', False),
            'image_source_type_debug': test_data.get('image_source_type_debug', ''),
            'image_criteria_debug': test_data.get('image_criteria_debug', ''),
            'error': test_data.get('error', ''),
        }
    
    # SEO метатеги для шаблона
    page_title = f'Тестирование: {template.name} — IdealImage.ru'
    page_description = f'Тестирование промпт шаблона {template.name} для генерации контента'
    og_title = f'Тестирование: {template.name}'
    meta_keywords = 'тестирование промптов, AI генерация, GigaChat, промпт шаблоны'
    
    # Формируем контекст с обязательными SEO переменными
    context = {
        'template': template,
        'form_variables': form_variables,
        'test_result': test_result,
        # SEO переменные (обязательные для base_tailwind.html)
        'title': page_title,
        'page_title': page_title,  # Обязательно для шаблона
        'page_description': page_description,  # Обязательно для шаблона
        'meta_keywords': meta_keywords,
        'og_title': og_title,
        'og_description': page_description,
    }
    
    return render(request, 'Asistent/prompt_template_test.html', context)

