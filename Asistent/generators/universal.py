"""
УНИВЕРСАЛЬНЫЙ ГЕНЕРАТОР КОНТЕНТА

Объединяет лучшее из трёх систем:
- Test_Promot (модульная архитектура, сервисы)
- tasks.py (очереди, heartbeat, приоритизация, метрики)
- schedule (интеграция с расписаниями)

Режимы работы:
- AUTO: Полная автоматизация с очередями
- INTERACTIVE: Ручной запуск с предпросмотром
- BATCH: Массовая генерация
- SCHEDULED: Через систему schedule
"""

import logging
import time
from typing import Dict, Optional
from django.db import transaction
from django.utils import timezone
from django.utils.html import strip_tags
from django.contrib.auth.models import User

from Asistent.models import PromptTemplate
from Asistent.Test_Promot.services import (
    ContentGenerationFactory,
    TitleGenerator,
    ImageProcessor,
    TagProcessor,
)
from Asistent.Test_Promot.test_prompt import render_template_text, _convert_markdown_to_html
from Asistent.gigachat_api import get_gigachat_client, RateLimitCooldown
from blog.models import Post, Category

from .base import GeneratorMode, GeneratorConfig, GenerationResult
from .context import UniversalContextBuilder
from .queue import QueueManager
from .heartbeat import HeartbeatManager
from .metrics import MetricsTracker

logger = logging.getLogger(__name__)


class UniversalContentGenerator:
    """
    УНИВЕРСАЛЬНЫЙ ГЕНЕРАТОР КОНТЕНТА.
    
    Примеры использования:
    
    # Автоматический режим (как tasks.py)
    config = GeneratorConfig.for_auto()
    generator = UniversalContentGenerator(template, config, schedule_id=123)
    result = generator.generate(schedule_payload={'zodiac_sign': 'Овен'})
    
    # Интерактивный режим (как test_prompt.py)
    config = GeneratorConfig.for_interactive()
    generator = UniversalContentGenerator(template, config)
    result = generator.generate(variables={'category': 'здоровье'})
    
    # Через schedule
    config = GeneratorConfig.for_scheduled()
    generator = UniversalContentGenerator(template, config, schedule_id=456)
    result = generator.generate(schedule_payload={...})
    """
    
    def __init__(
        self,
        template: PromptTemplate,
        config: GeneratorConfig = None,
        schedule_id: Optional[int] = None
    ):
        """
        Args:
            template: Шаблон промпта
            config: Конфигурация генератора (по умолчанию INTERACTIVE)
            schedule_id: ID расписания (для AUTO/SCHEDULED режимов)
        """
        self.template = template
        self.config = config or GeneratorConfig.for_interactive()
        self.schedule_id = schedule_id
        
        # Компоненты (ленивая инициализация)
        self._queue_manager: Optional[QueueManager] = None
        self._heartbeat: Optional[HeartbeatManager] = None
        self._metrics: Optional[MetricsTracker] = None
        self._context_builder: Optional[UniversalContextBuilder] = None
        self._client = None
        
        logger.info(
            f"🎨 UniversalContentGenerator инициализирован "
            f"(режим: {self.config.mode.value}, шаблон: {template.name})"
        )
    
    def generate(
        self,
        variables: Dict = None,
        schedule_payload: Dict = None
    ) -> GenerationResult:
        """
        ГЛАВНЫЙ МЕТОД ГЕНЕРАЦИИ КОНТЕНТА.
        
        Args:
            variables: Переменные из формы (для INTERACTIVE)
            schedule_payload: Параметры из расписания (для SCHEDULED/AUTO)
        
        Returns:
            GenerationResult с результатом генерации
        """
        try:
            # 1. Инициализация компонентов
            self._initialize_components()
            
            # 2. Проверка дневного лимита удалена - не используется
            
            # 3. Добавление в очередь (только AUTO)
            if self.config.use_queue and self.schedule_id:
                if not self._enter_queue():
                    return GenerationResult(
                        success=False,
                        error='queue_timeout'
                    )
            
            # 4. Подготовка контекста
            context = self._build_context(variables, schedule_payload)
            
            # 5. Генерация контента
            content_result = self._generate_content(context)
            
            # 6. Генерация изображения
            image_result = self._generate_image(context)
            
            # 7. Публикация или предпросмотр
            if self.config.preview_only:
                result = self._save_to_session(content_result, image_result, context)
            else:
                post = self._publish_post(content_result, image_result, context)
                
                # 8. Метрики
                if self.config.use_metrics and self._metrics:
                    self._metrics.save_to_database(
                        post=post,
                        prompt_text=content_result.get('prompt', ''),
                        ai_response=content_result.get('plain_text', ''),
                    )
                    self._metrics.log_summary()
                
                result = GenerationResult(
                    success=True,
                    post=post,
                    post_id=post.id,
                    title=post.title,
                    content=post.content,
                    image_path=str(post.kartinka) if post.kartinka else None,
                    metrics=self._metrics.get_data() if self._metrics else {}
                )
            
            logger.info(f"✅ Генерация завершена успешно (post_id: {result.post_id})")
            return result
        
        except RateLimitCooldown as e:
            logger.warning(f"⏸️ Rate limit: {e}")
            return GenerationResult(
                success=False,
                error=f'rate_limit: {str(e)}'
            )
        
        except Exception as e:
            logger.exception(f"❌ Ошибка генерации: {e}")
            return GenerationResult(
                success=False,
                error=str(e)
            )
        
        finally:
            # Очистка
            self._cleanup()
    
    def _initialize_components(self):
        """Инициализация компонентов"""
        logger.debug("   🔧 Инициализация компонентов")
        
        if self.config.use_queue and self.schedule_id:
            queue_name = f"{self.template.category or 'content'}_generation"
            self._queue_manager = QueueManager(queue_name=queue_name)
        
        if self.config.use_heartbeat and self.schedule_id:
            self._heartbeat = HeartbeatManager(self.schedule_id)
            self._heartbeat.start()
        
        if self.config.use_metrics:
            self._metrics = MetricsTracker()
        
        self._context_builder = UniversalContextBuilder(
            template=self.template,
            user_variables={},
            mode=self.config.mode
        )
        
        self._client = get_gigachat_client()
    
    
    def _enter_queue(self) -> bool:
        """
        Добавление в очередь и ожидание.
        
        Returns:
            True если успешно вошли в очередь, False если таймаут
        """
        if not self._queue_manager or not self.schedule_id:
            return True
        
        position = self._queue_manager.add_to_queue(self.schedule_id)
        if self._metrics:
            self._metrics.record_queue_position(position)
        
        success = self._queue_manager.wait_for_turn(self.schedule_id, max_wait=3600)
        
        if not success:
            logger.error(f"   ❌ Таймаут ожидания очереди")
        
        return success
    
    def _build_context(self, variables: Dict, schedule_payload: Dict) -> Dict:
        """
        Построение контекста переменных.
        
        Args:
            variables: Переменные из формы
            schedule_payload: Параметры из расписания
        
        Returns:
            Полный контекст переменных
        """
        logger.debug("   📝 Построение контекста")
        
        # Обновляем heartbeat
        if self._heartbeat:
            self._heartbeat.update()
        
        # Объединяем переменные
        self._context_builder.user_variables = variables or {}
        context = self._context_builder.build(schedule_payload)
        
        return context
    
    def _generate_content(self, context: Dict) -> Dict:
        """
        Генерация текстового контента.
        
        Args:
            context: Контекст переменных
        
        Returns:
            Словарь с результатом (title, content, plain_text, prompt)
        """
        logger.info("   📄 Генерация текста...")
        
        # Обновляем heartbeat
        if self._heartbeat:
            self._heartbeat.update()
        
        # Рендерим промпт
        article_prompt = render_template_text(self.template.template or '', context)
        
        if not article_prompt.strip():
            raise ValueError('Промпт пустой после рендеринга')
        
        # Генерация через ContentGenerationFactory (из Test_Promot)
        strategy = ContentGenerationFactory.create_strategy(
            self.template,
            self._client,
            self.config.timeout,
            context=context  # Передаем контекст для автоматического формирования URL гороскопов
        )
        
        # Генерация с retry
        article_text, source_info, parsed_content = self._generate_with_retry(
            strategy, article_prompt, context
        )
        
        # Генерация заголовка
        title_generator = TitleGenerator(
            self.template, self._client, self.config.timeout
        )
        title = title_generator.generate(
            context, article_text, context.get('title', '')
        )
        
        # Обновляем heartbeat
        if self._heartbeat:
            self._heartbeat.update()
        
        # Конвертация Markdown → HTML
        content_html = _convert_markdown_to_html(article_text)
        
        logger.info(f"   ✅ Текст сгенерирован (длина: {len(article_text)} символов)")
        
        return {
            'title': title,
            'content': content_html,
            'plain_text': article_text,
            'source_info': source_info,
            'prompt': article_prompt,
            'parsed_content': parsed_content,  # Добавляем спарсенный контент
        }
    
    def _generate_with_retry(self, strategy, prompt: str, context: Dict) -> tuple:
        """
        Генерация с retry механизмом.
        
        Args:
            strategy: Стратегия генерации
            prompt: Текст промпта
            context: Контекст переменных
        
        Returns:
            (article_text, source_info, parsed_content)
        """
        parsed_content = None
        for attempt in range(self.config.retry_count):
            try:
                if self._metrics:
                    self._metrics.record_api_call()
                
                result = strategy.generate(prompt, context)
                # Обрабатываем разные форматы возврата (для обратной совместимости)
                if len(result) == 3:
                    article_text, source_info, parsed_content = result
                else:
                    article_text, source_info = result
                    parsed_content = None
                
                if article_text and article_text.strip():
                    return article_text, source_info, parsed_content
                
                logger.warning(f"   ⚠️ Пустой ответ (попытка {attempt + 1}/{self.config.retry_count})")
                
            except RateLimitCooldown as e:
                if self._metrics:
                    self._metrics.record_error(f'RateLimitCooldown: {str(e)}')
                    self._metrics.record_retry()
                
                if attempt < self.config.retry_count - 1:
                    wait_time = getattr(e, 'retry_after', 60)
                    logger.warning(f"   ⏸️ Rate limit, ожидание {wait_time} сек...")
                    time.sleep(wait_time)
                    
                    if self._heartbeat:
                        self._heartbeat.update(force=True)
                else:
                    raise
            
            except Exception as e:
                if self._metrics:
                    self._metrics.record_error(f'Exception: {str(e)}')
                    self._metrics.record_retry()
                
                if attempt < self.config.retry_count - 1:
                    wait_time = 5 * (attempt + 1)
                    logger.warning(f"   ⚠️ Ошибка, повтор через {wait_time} сек: {e}")
                    time.sleep(wait_time)
                else:
                    raise
        
        raise ValueError('Не удалось сгенерировать текст после всех попыток')
    
    def _generate_image(self, context: Dict) -> Dict:
        """
        Генерация изображения.
        
        Args:
            context: Контекст переменных
        
        Returns:
            Словарь с результатом (path, info, source_type)
        """
        logger.info("   🎨 Генерация изображения...")
        
        # Обновляем heartbeat
        if self._heartbeat:
            self._heartbeat.update()
        
        try:
            image_processor = ImageProcessor(self.template, self._client)
            image_path = image_processor.generate(context, title=context.get('title', ''))
            
            logger.info(f"   ✅ Изображение обработано: {image_path or 'нет'}")
            
            return {
                'path': image_path,
                'info': None,
                'source_type': 'generated' if image_path else None,
            }
        
        except Exception as e:
            logger.warning(f"   ⚠️ Ошибка генерации изображения: {e}")
            return {'path': None, 'info': str(e), 'source_type': 'none'}
    
    def _publish_post(self, content_result: Dict, image_result: Dict, context: Dict) -> Post:
        """
        Создание и публикация поста.
        
        Args:
            content_result: Результат генерации контента
            image_result: Результат генерации изображения
            context: Контекст переменных
        
        Returns:
            Созданный Post объект
        """
        logger.info("   📰 Создание поста...")
        
        # Определяем автора
        if self.template.default_author:
            author = self.template.default_author
        else:
            author = User.objects.filter(username='ai_assistant').first()
            author = author or User.objects.filter(is_superuser=True).first()
        
        # Категория
        category = self.template.blog_category or Category.objects.first()
        
        # Статус публикации
        if self.config.mode == GeneratorMode.AUTO:
            status = 'published'
        else:
            status = 'draft'
        
        # Создаём пост
        with transaction.atomic():
            post = Post(
                title=content_result['title'],
                content=content_result['content'],
                category=category,
                author=author,
                description=strip_tags(content_result['content'])[:200],
                status=status,
            )
            
            # Флаги пропуска автоматической обработки
            post._skip_auto_moderation = True
            post._skip_auto_publication = True
            post.save()
            
            logger.info(f"   ✅ Пост создан: ID={post.id}, статус={status}")
            
            # Изображение
            if image_result.get('path'):
                post.kartinka = image_result['path']
                post.save(update_fields=['kartinka'])
                logger.info(f"   🖼️ Изображение добавлено: {image_result['path']}")
            
            # Теги (через TagProcessor из Test_Promot)
            tag_processor = TagProcessor(self.template)
            valid_tags = tag_processor.generate(context)
            if valid_tags:
                post.tags.add(*valid_tags)
                logger.info(f"   🏷️ Теги добавлены: {len(valid_tags)} шт.")
        
        # Telegram (только для AUTO режима)
        if self.config.mode == GeneratorMode.AUTO and status == 'published':
            self._send_to_telegram(post)
        
        return post
    
    def _send_to_telegram(self, post: Post):
        """
        Отправка в Telegram.
        
        Args:
            post: Post объект
        """
        try:
            from blog.telegram_utils import send_telegram_message
            post.refresh_from_db()
            success = send_telegram_message(post)
            
            if success:
                logger.info(f"   ✅ Отправлено в Telegram")
            else:
                logger.warning(f"   ⚠️ Не удалось отправить в Telegram")
        
        except Exception as e:
            logger.error(f"   ❌ Ошибка отправки в Telegram: {e}")
    
    def _save_to_session(
        self,
        content_result: Dict,
        image_result: Dict,
        context: Dict
    ) -> GenerationResult:
        """
        Сохранение результата в сессию (для INTERACTIVE режима).
        
        Args:
            content_result: Результат генерации контента
            image_result: Результат генерации изображения
            context: Контекст переменных
        
        Returns:
            GenerationResult с данными для сессии
        """
        logger.info("   💾 Сохранение в сессию (preview режим)")
        
        session_data = {
            'template_id': self.template.id,
            'title': content_result['title'],
            'content_html': content_result['content'],
            'plain_text': content_result['plain_text'],
            'image_path': image_result.get('path'),
            'image_source_type': image_result.get('source_type'),
            'context': context,
            'source_info': content_result.get('source_info'),  # Информация об источнике
            'prompt': content_result.get('prompt', ''),  # Промпт для генерации
            'parsed_content': content_result.get('parsed_content'),  # Спарсенный контент
        }
        
        return GenerationResult(
            success=True,
            title=content_result['title'],
            content=content_result['content'],
            image_path=image_result.get('path'),
            session_data=session_data,
            metrics=self._metrics.get_data() if self._metrics else {}
        )
    
    def _cleanup(self):
        """Очистка ресурсов"""
        logger.debug("   🧹 Очистка ресурсов")
        
        if self._queue_manager and self.schedule_id:
            self._queue_manager.remove_from_queue(self.schedule_id)
        
        if self._heartbeat:
            self._heartbeat.stop()


