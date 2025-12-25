"""
Единый сервис генерации контента для всего приложения
Объединяет логику из ai_agent.py, daily_article_generator.py и Test_Promot
"""
import logging
from typing import Dict, Optional, Tuple, List
from django.utils import timezone
from Asistent.models import AITask, PromptTemplate
from Asistent.gigachat_api import get_gigachat_client
from Asistent.Test_Promot.services import (
    ContentGenerationFactory,
    TitleGenerator,
    ImageProcessor,
    TagProcessor,
    ContextBuilder
)
from Asistent.Test_Promot.test_prompt import (
    render_template_text,
    GIGACHAT_TIMEOUT_ARTICLE,
    GIGACHAT_TIMEOUT_TITLE
)
from blog.models import Post, Category
from Asistent.formatting import render_markdown, MarkdownPreset
from Asistent.seo_advanced import AdvancedSEOOptimizer


logger = logging.getLogger(__name__)


class UnifiedContentGenerationService:
    """
    Единый сервис для генерации контента, объединяющий:
    - Логику из ai_agent.py
    - Логику из daily_article_generator.py
    - Новые стратегии из Test_Promot
    """
    
    def __init__(self):
        self.client = get_gigachat_client()
        self.optimizer = AdvancedSEOOptimizer()
        
    def generate_article_from_command(self, command_text: str, user=None) -> Dict:
        """
        Генерация статьи по команде администратора (аналог ai_agent.py)
        """
        # Пока используем простую реализацию, позже можно расширить
        try:
            # Создаем шаблонный промпт на основе команды
            template = self._create_template_from_command(command_text)
            context = {
                'topic': command_text,
                'current_datetime': timezone.now().strftime('%d.%m.%Y %H:%M'),
            }
            
            result = self.generate_from_template(template, context, user)
            return result
        except Exception as e:
            logger.error(f"Error generating article from command: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def generate_from_template(
        self, 
        template: PromptTemplate, 
        context: Dict, 
        user=None,
        category: Optional[Category] = None
    ) -> Dict:
        """
        Генерация контента из шаблона с использованием новых стратегий
        """
        try:
            # Подготовка контекста
            context_builder = ContextBuilder(template, context)
            final_context = context_builder.build()
            
            # Генерация контента через стратегию
            strategy = ContentGenerationFactory.create_strategy(
                template,
                self.client,
                GIGACHAT_TIMEOUT_ARTICLE,
                context=final_context
            )
            
            prompt = render_template_text(template.template or '', final_context)
            if not prompt.strip():
                raise ValueError("Промпт пустой после рендеринга")
            
            article_text, source_info = strategy.generate(prompt, final_context)
            if not article_text:
                raise ValueError("AI вернул пустой ответ")
            
            # Генерация заголовка
            title_generator = TitleGenerator(
                template, 
                self.client, 
                GIGACHAT_TIMEOUT_TITLE
            )
            title = title_generator.generate(final_context, article_text)
            
            # Обработка контента
            content_html = render_markdown(article_text, preset=MarkdownPreset.CKEDITOR)
            
            # Создание поста
            ai_user = user or self._get_or_create_ai_user()
            post_category = category or template.blog_category
            
            post = Post(
                title=title,
                content=content_html,
                author=ai_user,
                category=post_category,
                status='published',
                moderation_status='auto_checked',
            )
            post.save()
            
            # Генерация изображения
            if template.image_source_type and template.image_source_type != 'none':
                image_processor = ImageProcessor(template, self.client)
                try:
                    # Простая генерация изображения без вызова несуществующего метода
                    image_path = self._generate_image_simple(template, final_context, title)
                    if image_path:
                        post.kartinka = image_path
                        post.save(update_fields=['kartinka'])
                except Exception as img_error:
                    logger.warning(f"Image generation failed: {img_error}")
            
            # Применение тегов
            tag_processor = TagProcessor(template)
            valid_tags = tag_processor.generate(final_context)
            for tag in valid_tags:
                post.tags.add(tag)
            
            # Добавление FAQ если отсутствует
            if 'faq-section' not in content_html.lower():
                faq_result = self.optimizer.generate_faq_block(post)
                if faq_result.get('success') and faq_result.get('html'):
                    post.content = f"{post.content}\n\n{faq_result['html']}"
                    post.save(update_fields=['content'])
            
            return {
                'success': True,
                'post': post,
                'title': title,
                'source_info': source_info,
                'created': True
            }
            
        except Exception as e:
            logger.error(f"Error generating content from template: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _generate_image_simple(self, template: PromptTemplate, context: Dict, title: str) -> Optional[str]:
        """
        Простая генерация изображения без вызова несуществующих методов
        """
        try:
            import asyncio
            
            # Формирование промпта для изображения
            if template.image_generation_criteria:
                image_prompt = template.image_generation_criteria.format(**context)
            else:
                image_prompt = f"Изображение для статьи: {title[:100]}"
            
            # Запуск асинхронной генерации
            loop = asyncio.new_event_loop()
            try:
                asyncio.set_event_loop(loop)
                image_path = loop.run_until_complete(
                    self.client.generate_and_save_image(prompt=image_prompt)
                )
                return image_path
            finally:
                loop.close()
        except Exception as e:
            logger.error(f"Simple image generation failed: {e}")
            return None
    
    def _create_template_from_command(self, command_text: str) -> PromptTemplate:
        """
        Создание временного шаблона из команды
        """
        # В реальной реализации можно создать временный шаблон или использовать стандартный
        # Для начала используем первый доступный шаблон или создаем базовый
        template, created = PromptTemplate.objects.get_or_create(
            name=f"Команда: {command_text[:50]}",
            defaults={
                'template': f"Напиши подробную статью на тему: {command_text}. Структурируй текст с заголовками, подзаголовками и логичными абзацами.",
                'category': 'general',
                'content_source_type': 'generate',
            }
        )
        return template
    
    def _get_or_create_ai_user(self):
        """
        Получение или создание AI-пользователя
        """
        from django.contrib.auth.models import User
        ai_user, created = User.objects.get_or_create(
            username='ai_assistant',
            defaults={
                'first_name': 'AI Ассистент',
                'is_active': True,
                'is_staff': False,
                'is_superuser': False,
            }
        )
        return ai_user


class CommandParserService:
    """
    Сервис для парсинга команд администратора (перенос из ai_agent.py)
    """
    
    # Паттерны команд
    PATTERNS = {
        'generate_article': [
            r'генериру[йи]\s+стать[юя]\s+(?:на\s+тему\s+)?[\"\']?([^\"]+)[\"\']?(?:\s+категори[яию]\s+[\"\']?([^\"]+)[\"\']?)?',
            r'создай\s+стать[юя]\s+(?:про\s+)?[\"\']?([^\"]+)[\"\']?',
            r'напиши\s+стать[юя]\s+(?:о|про)\s+[\"\']?([^\"]+)[\"\']?',
            r'опубликуй\s+стать[юя]\s+(?:для\s+категории\s+)?[\"\']?([^\"]+)[\"\']?',
            r'опубликуй\s+(?:для\s+)?категори[июя]\s+[\"\']?([^\"]+)[\"\']?',
            r'сгенерируй\s+и\s+опубликуй\s+(?:для\s+)?[\"\']?([^\"]+)[\"\']?',
        ],
        'parse_video': [
            r'спарси\s+видео\s+(https?://[^\s]+)',
            r'обработай\s+видео\s+(https?://[^\s]+)',
            r'извлеки\s+(?:текст|контент)\s+из\s+видео\s+(https?://[^\s]+)',
        ],
        'parse_audio': [
            r'спарси\s+аудио\s+(https?://[^\s]+)',
            r'транскрибируй\s+(https?://[^\s]+)',
        ],
        'distribute_bonuses': [
            r'распредели\s+бонусы',
            r'рассчитай\s+бонусы',
            r'начисли\s+бонусы',
        ],
        'analyze_site': [
            r'проанализируй\s+сайт',
            r'дай\s+рекомендации\s+по\s+сайту',
            r'что\s+можно\s+улучшить',
            r'советы\s+для\s+сайта',
        ],
    }
    
    def __init__(self):
        self.generation_service = UnifiedContentGenerationService()
    
    def parse_and_execute(self, command_text: str, user=None) -> Dict:
        """
        Парсинг команды и выполнение соответствующего действия
        """
        import re
        
        for action_type, patterns in self.PATTERNS.items():
            for pattern in patterns:
                match = re.search(pattern, command_text, re.IGNORECASE)
                if match:
                    return self._execute_action(action_type, match.groups(), user, command_text)
        
        # Если команда не распознана, возвращаем ошибку
        return {
            'success': False,
            'error': 'Команда не распознана',
            'command': command_text,
            'action': 'unknown'
        }
    
    def _execute_action(self, action_type: str, groups: tuple, user, original_command: str) -> Dict:
        """
        Выполнение действия на основе распознанной команды
        """
        if action_type == 'generate_article':
            topic = groups[0] or original_command
            return self.generation_service.generate_article_from_command(topic, user)
        
        # Добавляем другие действия по мере необходимости
        return {
            'success': False,
            'error': f'Действие {action_type} еще не реализовано',
            'action': action_type
        }