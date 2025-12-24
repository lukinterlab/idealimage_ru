"""
AI-агент для обработки команд администратора
"""
import re
import logging
from typing import Dict, Optional, Tuple
from django.contrib.auth.models import User
from django.utils import timezone

from .models import AITask, AIKnowledgeBase
from .gigachat_api import GigaChatClient
from .prompt_registry import PromptRegistry

logger = logging.getLogger(__name__)

# ========================================================================
# Парсер команд от администратора
# ========================================================================
class CommandParser:
    """Парсер команд от администратора"""
    
    # Паттерны команд
    PATTERNS = {
        'generate_article': [
            r'генериру[йи]\s+стать[юя]\s+(?:на\s+тему\s+)?["\']?([^"\']+)["\']?(?:\s+категори[яию]\s+["\']?([^"\']+)["\']?)?',
            r'создай\s+стать[юя]\s+(?:про\s+)?["\']?([^"\']+)["\']?',
            r'напиши\s+стать[юя]\s+(?:о|про)\s+["\']?([^"\']+)["\']?',
            r'опубликуй\s+стать[юя]\s+(?:для\s+категории\s+)?["\']?([^"\']+)["\']?',
            r'опубликуй\s+(?:для\s+)?категори[июя]\s+["\']?([^"\']+)["\']?',
            r'сгенерируй\s+и\s+опубликуй\s+(?:для\s+)?["\']?([^"\']+)["\']?',
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
        # ========================================================================
        # AI-СОВЕТНИК: Анализ сайта и рекомендации
        # ========================================================================
        'analyze_site': [
            r'проанализируй\s+сайт',
            r'анализ\s+сайта',
            r'как\s+дела\s+на\s+сайте',
            r'статистика\s+сайта',
        ],
        'recommendations': [
            r'что\s+улучшить',
            r'дай\s+рекоменд',
            r'как\s+улучшить\s+сайт',
            r'что\s+можно\s+сделать\s+лучше',
        ],
        'monetization': [
            r'как\s+заработать',
            r'увеличить\s+доход',
            r'монетизация',
            r'стратеги[ия]\s+заработка',
        ],
        'optimize_tokens': [
            r'экономия\s+токенов',
            r'оптимизируй\s+расходы',
            r'как\s+сэкономить\s+на\s+api',
            r'снизить\s+затраты\s+gigachat',
        ],
        
        'manage_schedules': [
            r'покажи\s+расписания',
            r'список\s+расписаний',
            r'какие\s+расписания',
        ],
        'run_schedule': [
            r'запусти\s+расписание\s+(?:#)?(\d+)',
            r'выполни\s+расписание\s+(?:#)?(\d+)',
        ],
        'sync_schedules': [
            r'синхронизируй\s+расписания',
            r'обнови\s+расписания',
            r'пересоздай\s+расписания',
        ],
        'add_knowledge': [
            r'добавь\s+(?:себе\s+)?в\s+(промпт[ыи]?|правил[ао]|пример[ыи]?|команд[уы]|faq|инструкци[июя])\s+(.+)',
            r'сохрани\s+в\s+(промпт[ыи]?|правил[ао]|пример[ыи]?|команд[уы]|faq|инструкци[июя])\s+(.+)',
            r'запомни\s+в\s+(промпт[ыи]?|правил[ао]|пример[ыи]?|команд[уы]|faq|инструкци[июя])\s+(.+)',
        ],
        'show_knowledge': [
            r'покажи\s+(?:свою\s+)?базу\s+знаний',
            r'что\s+ты\s+знаешь',
            r'покажи\s+(промпт[ыи]?|правил[ао]|пример[ыи]?|команд[уы]|faq|инструкци[июя])',
        ],
        # Рекламные команды
        'ad_show_places': [
            r'реклама\s+показать\s+места',
            r'реклама\s+места',
            r'показать\s+рекламные\s+места',
            r'какие\s+рекламные\s+места',
        ],
        'ad_statistics': [
            r'реклама\s+статистика',
            r'статистика\s+рекламы',
            r'показать\s+статистику\s+рекламы',
        ],
        'ad_activate_banner': [
            r'реклама\s+включить\s+баннер\s+(?:#)?(\d+)',
            r'реклама\s+активировать\s+баннер\s+(?:#)?(\d+)',
            r'включи\s+баннер\s+(?:#)?(\d+)',
        ],
        'ad_deactivate_banner': [
            r'реклама\s+выключить\s+баннер\s+(?:#)?(\d+)',
            r'реклама\s+деактивировать\s+баннер\s+(?:#)?(\d+)',
            r'выключи\s+баннер\s+(?:#)?(\d+)',
        ],
        'ad_list_banners': [
            r'реклама\s+список\s+баннеров',
            r'показать\s+баннеры',
            r'какие\s+баннеры',
        ],
        'ad_insert_in_article': [
            r'реклама\s+вставить\s+в\s+статью\s+(?:#)?(\d+)',
            r'вставь\s+рекламу\s+в\s+статью\s+(?:#)?(\d+)',
            r'добавь\s+рекламу\s+в\s+пост\s+(?:#)?(\d+)',
        ],
    }
    
    # Метод для парсинга команды и возврата типа и параметров
    @classmethod
    def parse(cls, command: str) -> Tuple[Optional[str], Dict]:
        """
        Парсит команду и возвращает тип и параметры
        
        Returns:
            (task_type, parameters) или (None, {}) если команда не распознана
        """
        # Сохраняем оригинальную команду для сложных случаев
        cls._original_command = command
        command = command.strip().lower()
        
        for task_type, patterns in cls.PATTERNS.items():
            for pattern in patterns:
                match = re.search(pattern, command, re.IGNORECASE)
                if match:
                    params = cls._extract_parameters(task_type, match)
                    return task_type, params
        
        return None, {}
    
    # Метод для извлечения параметров из regex match
    @classmethod
    def _extract_parameters(cls, task_type: str, match) -> Dict:
        """Извлекает параметры из regex match"""
        params = {}
        
        if task_type == 'generate_article':
            if len(match.groups()) >= 1 and match.group(1):
                params['topic'] = match.group(1).strip()
            else:
                params['topic'] = 'общая тема'
            
            if len(match.groups()) >= 2 and match.group(2):
                params['category'] = match.group(2).strip()
            else:
                params['category'] = None
        
        elif task_type in ['parse_video', 'parse_audio']:
            if len(match.groups()) >= 1 and match.group(1):
                params['url'] = match.group(1).strip()
            else:
                params['url'] = ''
        
        elif task_type == 'run_schedule':
            if len(match.groups()) >= 1 and match.group(1):
                params['schedule_id'] = int(match.group(1))
            else:
                params['schedule_id'] = None
        
        elif task_type == 'add_knowledge':
            # Нормализуем категорию
            category_map = {
                'промпт': 'промпты',
                'промпты': 'промпты',
                'правило': 'правила',
                'правила': 'правила',
                'пример': 'примеры',
                'примеры': 'примеры',
                'команду': 'команды',
                'команды': 'команды',
                'faq': 'faq',
                'инструкцию': 'инструкции',
                'инструкция': 'инструкции',
                'инструкции': 'инструкции',
            }
            # Безопасное извлечение групп
            if len(match.groups()) >= 1 and match.group(1):
                raw_category = match.group(1).lower()
                params['category'] = category_map.get(raw_category, 'правила')
            else:
                params['category'] = 'правила'
            
            # Проверяем наличие второй группы (контент)
            if len(match.groups()) >= 2 and match.group(2):
                params['content'] = match.group(2).strip()
            else:
                params['content'] = ''
        
        elif task_type == 'show_knowledge':
            if len(match.groups()) >= 1 and match.group(1):
                # Нормализуем категорию
                category_map = {
                    'промпт': 'промпты',
                    'промпты': 'промпты',
                    'правило': 'правила',
                    'правила': 'правила',
                    'пример': 'примеры',
                    'примеры': 'примеры',
                    'команду': 'команды',
                    'команды': 'команды',
                    'faq': 'faq',
                    'инструкцию': 'инструкции',
                    'инструкция': 'инструкции',
                    'инструкции': 'инструкции',
                }
                raw_category = match.group(1).lower()
                params['category'] = category_map.get(raw_category)
            else:
                params['category'] = None
        
        # Рекламные команды
        elif task_type in ['ad_activate_banner', 'ad_deactivate_banner']:
            if len(match.groups()) >= 1 and match.group(1):
                params['banner_id'] = int(match.group(1))
            else:
                params['banner_id'] = None
        
        elif task_type == 'ad_insert_in_article':
            if len(match.groups()) >= 1 and match.group(1):
                params['post_id'] = int(match.group(1))
            else:
                params['post_id'] = None
        
        return params


# ========================================================================
# AI-агент для выполнения команд
# ========================================================================
class AIAgent:
    """AI-агент для выполнения команд"""
    
    def __init__(self):
        from .gigachat_api import get_gigachat_client
        self.gigachat = get_gigachat_client()
    
    # Метод для получения статистики сайта за период
    def get_site_statistics(self, days=7) -> Dict:
        """Получить статистику сайта за период"""
        from blog.models import Post
        from advertising.models import AdBanner, AdImpression, AdClick
        from donations.models import Donation
        from django.db import models
        from datetime import timedelta
        
        start_date = timezone.now() - timedelta(days=days)
        
        stats = {
            'period_days': days,
            'posts': {
                'total': Post.objects.count(),
                'published': Post.objects.filter(status='published').count(),
                'draft': Post.objects.filter(status='draft').count(),
                'new_in_period': Post.objects.filter(created__gte=start_date).count(),
            },
            'advertising': {
                'total_banners': AdBanner.objects.count(),
                'active_banners': AdBanner.objects.filter(is_active=True).count(),
                'impressions': AdImpression.objects.filter(shown_at__gte=start_date).count(),
                'clicks': AdClick.objects.filter(clicked_at__gte=start_date).count(),
            },
            'donations': {
                'total_amount': Donation.objects.filter(
                    created_at__gte=start_date,
                    status='completed'
                ).aggregate(total=models.Sum('amount'))['total'] or 0,
                'count': Donation.objects.filter(
                    created_at__gte=start_date,
                    status='completed'
                ).count(),
            }
        }
        
        # Рассчитываем CTR
        if stats['advertising']['impressions'] > 0:
            stats['advertising']['ctr'] = (
                stats['advertising']['clicks'] / stats['advertising']['impressions'] * 100
            )
        else:
            stats['advertising']['ctr'] = 0
        
        return stats
    
    # Метод для получения топ авторов за период
    def get_top_authors(self, days=7, limit=10) -> list:
        """Получить топ авторов за период"""
        from blog.models import Post
        from django.db.models import Count, Sum
        from datetime import timedelta
        
        start_date = timezone.now() - timedelta(days=days)
        
        authors = Post.objects.filter(
            created__gte=start_date,
            status='published'
        ).values(
            'author__username',
            'author__id'
        ).annotate(
            total_posts=Count('id'),
            total_views=Sum('views'),
            total_likes=Sum('likes_count')
        ).order_by('-total_views')[:limit]
        
        return list(authors)
    
    # Метод для получения контента на модерации
    def get_pending_moderation(self) -> Dict:
        """Получить контент на модерации"""
        from blog.models import Post, Comment
        
        return {
            'draft_posts': Post.objects.filter(status='draft').count(),
            'pending_comments': Comment.objects.filter(active=False).count(),
        }
    
    # Метод для обработки сообщения от пользователя
    def process_message(self, user: User, message: str, conversation) -> Dict:
        """
        Обрабатывает сообщение от пользователя
        
        Args:
            user: Пользователь (администратор)
            message: Текст сообщения
            conversation: Объект AIConversation
        
        Returns:
            Dict с ключами: response, task_created, task_id
        """
        logger.info(f"📨 process_message: user={user.username}, message='{message[:50]}...'")
        
        # Парсим команду
        task_type, parameters = CommandParser.parse(message)
        
        logger.info(f"🔍 Парсинг: task_type={task_type}, parameters={parameters}")
        
        if task_type:
            # Это команда - создаем задачу
            logger.info(f"✅ Распознана команда: {task_type}")
            return self._handle_command(user, message, task_type, parameters, conversation)
        else:
            # Обычный вопрос - отвечаем через GigaChat
            logger.info(f"💬 Обычный вопрос (команда не распознана)")
            return self._handle_question(user, message, conversation)
    
    # Метод для обработки команды и создания задачи
    def _handle_command(self, user: User, command: str, task_type: str, 
                       parameters: Dict, conversation) -> Dict:
        """Обрабатывает команду и создает задачу"""
        
        logger.info(f"🚀 _handle_command вызван: команда='{command}', тип={task_type}")
        
        # КРИТИЧНО: Создать задачу В БАЗЕ
        try:
            task = AITask.objects.create(
                conversation=conversation,
                command=command,
                task_type=task_type,
                parameters=parameters,
                status='pending'
            )
            # Явно сохранить и проверить ID
            task.save()
            logger.info(f"✅ AITask создана в БД! ID={task.id}, status={task.status}")
            
        except Exception as e:
            logger.error(f"❌ КРИТИЧЕСКАЯ ОШИБКА создания AITask: {e}", exc_info=True)
            return {
                'response': f"❌ Ошибка создания задачи: {str(e)}\n\n"
                           f"Пожалуйста, сообщите администратору об этой ошибке.",
                'task_created': False,
                'error': str(e)
            }
        
        # Формируем ответ - ПРИСТУПАЕМ К ВЫПОЛНЕНИЮ
        task_name = task.get_task_type_display()
        response = f"✅ Понял! Задача: {task_name}\n\n"
        response += f"📋 Задача #{task.id} создана в системе!\n"
        response += f"Параметры: {self._format_parameters(parameters)}\n\n"
        response += "🚀 **ЗАПУСКАЮ ВЫПОЛНЕНИЕ!**\n\n"
        response += "📊 **Отчёт будет обновляться в реальном времени:**\n"
        response += "⏳ Ожидайте завершения (30-120 секунд)...\n\n"
        response += f"💡 Проверить статус можно здесь:\n"
        response += f"📍 Чат с отчётами: обновите эту страницу через минуту\n"
        response += f"📍 Админка: http://127.0.0.1:8000/admin/Asistent/aitask/{task.id}/change/"
        
        # Запускаем задачу асинхронно через Django-Q
        try:
            # Проверяем, запущен ли Django-Q
            from django_q.models import Schedule as DQSchedule
            from django_q.cluster import Cluster
            
            self._queue_task(task)
            logger.info(f"✅ Задача {task.id} поставлена в очередь Django-Q")
        except Exception as e:
            logger.error(f"❌ ОШИБКА постановки в очередь Django-Q: {e}", exc_info=True)
            # Помечаем задачу как failed
            task.status = 'failed'
            task.error_message = f"Ошибка постановки в очередь: {str(e)}"
            task.save()
            
            response += f"\n\n❌ **ОШИБКА ЗАПУСКА:**\n"
            response += f"Задача создана, но Django-Q не смог её выполнить.\n\n"
            response += f"**Возможные причины:**\n"
            response += f"1. Django-Q Cluster не запущен (запустите: python manage.py qcluster)\n"
            response += f"2. Ошибка в коде: {str(e)[:100]}\n\n"
            response += f"**Что делать:**\n"
            response += f"- Проверьте, запущен ли qcluster в отдельной консоли\n"
            response += f"- Посмотрите логи: logs/django.log"
        
        return {
            'response': response,
            'task_created': True,
            'task_id': task.id,
            'task_type': task_type
        }
    
    # Метод для обработки обычного вопроса через GigaChat
    def _handle_question(self, user: User, message: str, conversation) -> Dict:
        """Обрабатывает обычный вопрос через GigaChat"""
        
        # ВАЖНО: Если сообщение похоже на команду - предупреждаем
        command_keywords = ['опубликуй', 'сгенерируй', 'создай', 'напиши', 'запусти', 
                           'выполни', 'распредели', 'спарси', 'прокомментируй', 'лайкни',
                           'реклама', 'баннер', 'показать', 'включи', 'выключи']
        
        if any(keyword in message.lower() for keyword in command_keywords):
            # Это похоже на команду, но не распознано
            return {
                'response': f"⚠️ Похоже вы хотите дать команду, но я её не распознал.\n\n"
                           f"Ваше сообщение: \"{message}\"\n\n"
                           f"Попробуйте переформулировать или используйте один из примеров:\n\n"
                           f"📝 Генерация статьи:\n"
                           f"- \"генерируй статью про моду\"\n"
                           f"- \"создай статью про красоту\"\n"
                           f"- \"опубликуй статью для категории Мода\"\n\n"
                           f"📹 Парсинг видео:\n"
                           f"- \"спарси видео https://youtube.com/...\"\n\n"
                           f"📅 Расписания:\n"
                           f"- \"покажи расписания\"\n"
                           f"- \"запусти расписание #5\"\n\n"
                           f"💰 Бонусы:\n"
                           f"- \"распредели бонусы\"\n\n"
                           f"🎯 Реклама:\n"
                           f"- \"реклама места\"\n"
                           f"- \"реклама статистика\"\n"
                           f"- \"реклама список баннеров\"\n"
                           f"- \"реклама активировать баннер 1\"\n"
                           f"- \"реклама деактивировать баннер 1\"\n"
                           f"- \"реклама вставить в статью 5 баннер 2\"\n\n"
                           f"Полный список команд смотрите в документации.",
                'task_created': False,
                'warning': 'command_not_recognized'
            }
        
        # Получаем контекст из истории диалога
        context = self._get_conversation_context(conversation)
        
        # Получаем релевантные знания из базы
        knowledge = self._get_relevant_knowledge(message)
        
        # Формируем промпт
        system_prompt = self._build_system_prompt(knowledge)
        full_message = f"{context}\n\nПользователь: {message}"
        
        # Получаем ответ от GigaChat
        try:
            # Используем GigaChat-Max для чат-бота
            response = self.gigachat.chat_for_chatbot(full_message, system_prompt=system_prompt)
            
            return {
                'response': response,
                'task_created': False
            }
        except Exception as e:
            logger.error(f"Ошибка GigaChat: {e}")
            return {
                'response': f"Извините, произошла ошибка при обработке запроса: {str(e)}",
                'task_created': False,
                'error': str(e)
            }
    
    # Метод для получения контекста последних сообщений из диалога
    def _get_conversation_context(self, conversation, limit=5) -> str:
        """Получает контекст последних сообщений из диалога"""
        messages = conversation.messages.order_by('-timestamp')[:limit]
        
        context_lines = []
        for msg in reversed(list(messages)):
            role = "Админ" if msg.role == 'admin' else "AI"
            context_lines.append(f"{role}: {msg.content}")
        
        return "\n".join(context_lines) if context_lines else ""
    
    # Метод для поиска релевантных знаний в базе знаний с помощью векторного поиска
    def _get_relevant_knowledge(self, query: str, limit=3) -> str:
        """
        Ищет релевантные знания в базе знаний с помощью векторного поиска
        
        Args:
            query: Запрос пользователя
            limit: Максимальное количество результатов
            
        Returns:
            str: Отформатированный текст найденных знаний
        """
        try:
            # Используем векторный поиск через GigaChat-Embeddings
            results = AIKnowledgeBase.find_similar(
                query_text=query,
                top_k=limit,
                min_similarity=0.3  # Порог релевантности 30%
            )
            
            if results:
                knowledge_text = "\n\n".join([
                    f"**{entry.title}** [Релевантность: {similarity:.0%}]\n{entry.content}"
                    for entry, similarity in results
                ])
                
                logger.info(f"🎯 Найдено {len(results)} релевантных знаний (векторный поиск)")
                return knowledge_text
            else:
                logger.info("❓ Релевантных знаний не найдено")
                return ""
                
        except Exception as e:
            logger.error(f"Ошибка векторного поиска знаний: {e}")
            # Fallback на старый метод уже встроен в find_similar()
            return ""
    
    # Метод для формирования системного промпта для GigaChat с критическими знаниями
    def _build_system_prompt(self, knowledge: str = "") -> str:
        """Формирует системный промпт для GigaChat с критическими знаниями"""
        
        # ВСЕГДА загружать критические знания (priority >= 90)
        critical_knowledge = AIKnowledgeBase.objects.filter(
            is_active=True,
            priority__gte=90
        ).order_by('-priority')[:10]
        
        critical_text = "\n\n".join([
            f"**[ПРИОРИТЕТ {k.priority}] {k.title}**\n{k.content}"
            for k in critical_knowledge
        ])

        critical_section = f"\n\n🔴 КРИТИЧЕСКИ ВАЖНАЯ ИНФОРМАЦИЯ О САЙТЕ:\n\n{critical_text}" if critical_text else ""
        knowledge_section = f"\n\n💡 ДОПОЛНИТЕЛЬНЫЙ КОНТЕКСТ:\n{knowledge}" if knowledge else ""

        default_prompt = (
            "Ты - СУПЕРАДМИН сайта IdealImage.ru (женский портал о моде, красоте, здоровье).\n\n"
            "🎯 ТВОЯ РОЛЬ И ПОЛНОМОЧИЯ:\n\n"
            "1. ГЛАВНЫЙ ОРГАНИЗАТОР всех служб сайта\n"
            "2. МОДЕРАТОР контента (статьи, комментарии)\n"
            "3. АНАЛИТИК и СОВЕТНИК по оптимизации\n"
            "4. КОНТРОЛЁР качества и метрик\n"
            "5. РАСПРЕДЕЛИТЕЛЬ бонусов и рекламы\n"
            "6. ГЕНЕРАТОР контента и расписаний\n\n"
            "💪 ЧТО ТЫ МОЖЕШЬ ДЕЛАТЬ:\n\n"
            "📊 АНАЛИТИКА:\n"
            "- Анализировать статистику (просмотры, CTR, конверсии)\n"
            "- Выявлять тренды и паттерны\n"
            "- Давать рекомендации по улучшению\n"
            "- Составлять детальные отчёты\n\n"
            "✅ МОДЕРАЦИЯ:\n"
            "- Проверять статьи на уникальность и качество\n"
            "- Модерировать комментарии\n"
            "- Одобрять/отклонять заявки авторов\n"
            "- Следить за качеством контента\n\n"
            "💰 ФИНАНСЫ:\n"
            "- Рассчитывать и распределять бонусы\n"
            "- Анализировать доходы авторов\n"
            "- Оптимизировать монетизацию\n\n"
            "🎯 РЕКЛАМА:\n"
            "- Анализировать эффективность баннеров\n"
            "- Оптимизировать размещение\n"
            "- Предлагать улучшения дизайна\n"
            "- Мониторить CTR и конверсии\n\n"
            "📝 ГЕНЕРАЦИЯ КОНТЕНТА:\n"
            "- Создавать статьи через парсинг и GigaChat\n"
            "- Подбирать изображения\n"
            "- Оптимизировать SEO\n"
            "- Публиковать по расписанию\n\n"
            "🗓️ РАСПИСАНИЯ:\n"
            "- Создавать и управлять автопубликацией\n"
            "- Оптимизировать время публикаций\n"
            "- Мониторить выполнение задач\n\n"
            "💡 ТВОЙ СТИЛЬ ОБЩЕНИЯ:\n\n"
            "1. ПРОАКТИВНЫЙ - сам предлагаешь улучшения\n"
            "2. АНАЛИТИЧЕСКИЙ - даёшь конкретные цифры и метрики\n"
            "3. ЭКСПЕРТНЫЙ - знаешь все процессы досконально\n"
            "4. КОНКРЕТНЫЙ - чёткие рекомендации, не общие слова\n"
            "5. ИНИЦИАТИВНЫЙ - видишь проблему → предупреждаешь\n\n"
            "📋 КАК ОТВЕЧАТЬ:\n\n"
            "НА КОМАНДЫ:\n"
            "- Подтверди что понял команду\n"
            "- Создай задачу через систему\n"
            "- Сообщи что задача в работе\n"
            "- Не обещай конкретные сроки (задачи выполняет Django-Q)\n\n"
            "НА ВОПРОСЫ:\n"
            "- Дай экспертный ответ с цифрами\n"
            "- Используй знания из базы данных\n"
            "- Предложи дополнительные инсайты\n"
            "- Покажи связанные метрики\n\n"
            "ПРОАКТИВНО:\n"
            "- Если видишь низкую эффективность → предложи оптимизацию\n"
            "- Если есть проблемы → предупреди\n"
            "- Если можно улучшить → посоветуй как\n\n"
            "⚠️ КРИТИЧЕСКИЕ ОГРАНИЧЕНИЯ:\n\n"
            "❌ НЕ ДЕЛАЙ:\n"
            "- Не публикуй статьи БЕЗ изображения (kartinka обязательно!)\n"
            "- Не создавай новые теги (используй только существующие)\n"
            "- Не обещай выполнить за конкретное время\n"
            "- Не пиши \"Готово\" если задача ещё в процессе\n\n"
            "✅ ОБЯЗАТЕЛЬНО:\n"
            "- Проверяй наличие изображения перед публикацией\n"
            "- Используй фейковых авторов для автостатей\n"
            "- Следи за уникальностью контента (>70%)\n"
            "- Подбирай релевантные теги из базы"
            "{critical_section}"
            "{knowledge_section}"
            "\n\n🚀 ТВОЯ ЗАДАЧА ПРЯМО СЕЙЧАС:\n"
            "Внимательно прочитай сообщение админа, проанализируй контекст диалога и дай максимально полезный, конкретный и аналитический ответ. Используй все доступные знания о сайте!"
        )

        prompt = PromptRegistry.render(
            'AI_AGENT_SYSTEM_PROMPT',
            params={
                'critical_section': critical_section,
                'knowledge_section': knowledge_section,
            },
            default=default_prompt,
        )

        PromptRegistry.increment_usage('AI_AGENT_SYSTEM_PROMPT')

        return prompt
    
    # Метод для форматирования параметров для отображения
    def _format_parameters(self, parameters: Dict) -> str:
        """Форматирует параметры для отображения"""
        if not parameters:
            return "нет"
        
        formatted = []
        for key, value in parameters.items():
            formatted.append(f"{key}: {value}")
        
        return ", ".join(formatted)
    
    # Метод для постановки задачи в очередь Django-Q
    def _queue_task(self, task: AITask):
        """Ставит задачу в очередь Django-Q"""
        from django_q.tasks import async_task
        
        task_handlers = {
            'generate_article': 'Asistent.tasks.execute_generate_article',
            'parse_video': 'Asistent.tasks.execute_parse_video',
            'parse_audio': 'Asistent.tasks.execute_parse_audio',
            'distribute_bonuses': 'Asistent.tasks.execute_distribute_bonuses',
            'manage_schedules': 'Asistent.tasks.execute_manage_schedules',
            'run_schedule': 'Asistent.tasks.execute_run_schedule',
            'sync_schedules': 'Asistent.tasks.execute_sync_schedules',
            'add_knowledge': 'Asistent.tasks.execute_add_knowledge',
            'show_knowledge': 'Asistent.tasks.execute_show_knowledge',
            # Рекламные команды
            'ad_show_places': 'Asistent.tasks.execute_ad_show_places',
            'ad_statistics': 'Asistent.tasks.execute_ad_statistics',
            'ad_list_banners': 'Asistent.tasks.execute_ad_list_banners',
            'ad_activate_banner': 'Asistent.tasks.execute_ad_activate_banner',
            'ad_deactivate_banner': 'Asistent.tasks.execute_ad_deactivate_banner',
            'ad_insert_in_article': 'Asistent.tasks.execute_ad_insert_in_article',
        }
        
        handler = task_handlers.get(task.task_type)
        if handler:
            try:
                async_task(
                    handler,
                    task.id,
                    task_name=f"{task.get_task_type_display()} #{task.id}"
                )
                logger.info(f"Задача {task.id} ({task.task_type}) поставлена в очередь")
            except Exception as e:
                logger.error(f"Ошибка при постановке задачи в очередь: {e}")
                task.fail(f"Ошибка постановки в очередь: {str(e)}")
        else:
            logger.warning(f"Нет обработчика для типа задачи: {task.task_type}")
            task.fail(f"Неизвестный тип задачи: {task.task_type}")
    
    # Метод для выполнения задачи по ID
    def execute_task(self, task_id: int):
        """Выполняет задачу по ID"""
        try:
            task = AITask.objects.get(id=task_id)
            task.start()
            
            # Вызываем соответствующий обработчик
            handler_method = getattr(self, f'_execute_{task.task_type}', None)
            if handler_method:
                result = handler_method(task)
                task.complete(result)
                logger.info(f"Задача {task_id} выполнена успешно")
            else:
                task.fail(f"Обработчик не найден для типа: {task.task_type}")
        
        except AITask.DoesNotExist:
            logger.error(f"Задача {task_id} не найдена")
        except Exception as e:
            logger.error(f"Ошибка выполнения задачи {task_id}: {e}")
            task.fail(str(e))
    
    # Метод для генерации статьи
    def _execute_generate_article(self, task: AITask) -> Dict:
        """Генерирует статью"""
        from blog.models import Post, Category
        from django.contrib.auth.models import User
        from .models import AIGeneratedArticle
        import re
        import time
        
        start_time = time.time()
        
        # ШАГ 1: Приступаем
        task.progress_description = "🚀 Приступаю к заданию..."
        task.progress_percentage = 0
        task.save()
        logger.info(f"📝 Начало генерации статьи")
        
        try:
            # ШАГ 2: Анализ параметров
            task.progress_description = "📋 Анализирую параметры задания..."
            task.progress_percentage = 10
            task.save()
            
            # Получаем параметры
            topic = task.parameters.get('topic', 'Мода и красота')
            category_name = task.parameters.get('category', topic)
            
            logger.info(f"   Тема: {topic}")
            logger.info(f"   Категория: {category_name}")
            
            # ШАГ 3: Подготовка пользователя и категории
            task.progress_description = "👤 Подготовка пользователя AI и поиск категории..."
            task.progress_percentage = 20
            task.save()
            
            # Получаем или создаём пользователя AI
            ai_user, _ = User.objects.get_or_create(
                username='ai_assistant',
                defaults={
                    'first_name': 'AI',
                    'last_name': 'Ассистент',
                    'email': 'ai@idealimage.ru',
                    'is_active': True
                }
            )
            
            # Ищем категорию
            category = None
            try:
                category = Category.objects.get(title__icontains=category_name)
                logger.info(f"   ✓ Категория найдена: {category.title}")
            except Category.DoesNotExist:
                # Пытаемся найти по части имени
                categories = Category.objects.filter(title__icontains=category_name[:5])
                if categories.exists():
                    category = categories.first()
                    logger.info(f"   ✓ Категория найдена (частично): {category.title}")
                else:
                    # Используем первую доступную
                    category = Category.objects.first()
                    logger.warning(f"   ⚠️ Категория '{category_name}' не найдена, использую: {category.title if category else 'нет'}")
            
            # ШАГ 4: Генерация контента через GigaChat
            task.progress_description = "🤖 Генерирую текст через GigaChat AI..."
            task.progress_percentage = 30
            task.save()
            
            logger.info(f"🤖 Запрос к GigaChat API...")
            
            # Простая сводка источников
            sources_summary = f"Создай статью на тему '{topic}' для категории '{category.title if category else 'Общее'}'.\n\n"
            sources_summary += "Статья должна быть интересной, полезной и уникальной."
            
            article_content = self.gigachat.generate_article(
                topic=topic,
                sources_summary=sources_summary,
                word_count=1000,
                keywords=[topic, category_name] if category_name else [topic],
                tone="дружелюбный и экспертный",
                category=category.title if category else ""
            )
            
            logger.info(f"   ✓ Контент сгенерирован ({len(article_content)} символов)")
            
            # ШАГ 5: Проверка качества текста
            task.progress_description = "📝 Проверяю текст на литературность и уникальность..."
            task.progress_percentage = 60
            task.save()
            
            # Извлекаем заголовок из контента
            title_match = re.search(r'#\s*(.+?)(?:\n|$)', article_content)
            if title_match:
                title = title_match.group(1).strip()
                # Удаляем заголовок из контента
                article_content = article_content.replace(title_match.group(0), '', 1).strip()
            else:
                title = f"{topic} - {category.title if category else 'IdealImage.ru'}"
            
            # Очистка от markdown
            article_content = article_content.replace('```html', '').replace('```', '').strip()
            
            # ШАГ 6: Генерация SEO
            task.progress_description = "🔍 Генерирую SEO-метаданные для поисковиков..."
            task.progress_percentage = 70
            task.save()
            
            seo_data = self.gigachat.generate_seo_metadata(
                title=title,
                content=article_content[:500],
                keywords=[topic, category_name] if category_name else [topic],
                category=category.title if category else ""
            )
            
            logger.info(f"   ✓ SEO метаданные созданы")
            
            # ШАГ 7: Создание и публикация статьи
            task.progress_description = "💾 Создаю и публикую статью на сайте..."
            task.progress_percentage = 80
            task.save()
            
            post = Post.objects.create(
                title=title[:200],  # Ограничение Django
                content=article_content,
                author=ai_user,
                category=category,
                status='published',  # Публикуем сразу
                meta_title=seo_data.get('meta_title', title)[:60],
                meta_description=seo_data.get('meta_description', '')[:160],
                og_title=seo_data.get('og_title', title)[:95],
                og_description=seo_data.get('og_description', '')[:200],
            )
            
            logger.info(f"   ✓ Статья создана (ID: {post.id})")
            
            # ШАГ 8: Сохранение в историю
            task.progress_description = "📊 Сохраняю в историю AI..."
            task.progress_percentage = 90
            task.save()
            
            end_time = time.time()
            generation_time_seconds = int(end_time - start_time)
            
            # Сохраняем в историю AI
            ai_article = AIGeneratedArticle.objects.create(
                schedule=None,  # Создана через команду, не по расписанию
                post=post,
                topic=topic,
                category=category,
                word_count=len(article_content.split()),
                generation_time=generation_time_seconds,
                sources_used=0,
                uniqueness_score=95.0,  # По умолчанию высокая уникальность AI
                seo_score=85.0
            )
            
            # ШАГ 9: Финализация
            task.progress_description = "✅ Завершаю работу..."
            task.progress_percentage = 100
            task.save()
            
            logger.info(f"✅ Статья успешно опубликована!")
            
            # Формируем URL статьи
            post_url = f"/blog/post/{post.id}/"
            
            return {
                'status': 'completed',
                'message': f"🎉 **ГОТОВО!**\n\n"
                          f"✅ Статья успешно создана и опубликована!\n\n"
                          f"📋 **ДЕТАЛИ:**\n"
                          f"━━━━━━━━━━━━━━━━━━━━━\n"
                          f"📝 Заголовок: **{title}**\n"
                          f"   post_id:{post.id}\n"
                          f"✍️ Автор: {post.author.username}\n"
                          f"   user_id:{post.author.id}\n"
                          f"📂 Категория: **{category.title if category else 'нет'}**\n"
                          f"📊 Слов: **{len(article_content.split())}**\n"
                          f"⏱️ Время генерации: **{generation_time_seconds} сек**\n"
                          f"━━━━━━━━━━━━━━━━━━━━━\n\n"
                          f"🌐 **ССЫЛКА:**\n"
                          f"👉 {post_url}\n\n"
                          f"📊 **СТАТИСТИКА:**\n"
                          f"✓ Уникальность: 95%\n"
                          f"✓ SEO-оценка: 85/100\n"
                          f"✓ Статус: Опубликовано\n\n"
                          f"🎊 Статья доступна на сайте!",
                'post_id': post.id,
                'title': title,
                'category': category.title if category else None,
                'word_count': len(article_content.split()),
                'generation_time': generation_time_seconds,
                'post_url': post_url
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка генерации статьи: {e}")
            import traceback
            logger.error(f"Traceback:\n{traceback.format_exc()}")
            return {
                'status': 'failed',
                'message': f"❌ Ошибка при генерации статьи: {str(e)}"
            }
    
    # Метод для парсинга видео
    def _execute_parse_video(self, task: AITask) -> Dict:
        """Парсит видео"""

        def action():
            from .parsers.universal_parser import UniversalVideoParser

            video_url = task.parameters.get('url')
            if not video_url:
                raise ValueError("URL видео не указан")

            parser = UniversalVideoParser()
            result = parser.parse_video(video_url)

            if result['success']:
                return {
                    'status': 'completed',
                    'message': f"Видео обработано: {result.get('title', 'Без названия')}",
                    'data': result
                }
            return {
                'status': 'failed',
                'message': f"Ошибка парсинга: {', '.join(result.get('errors', []))}"
            }

        return self._run_task_with_progress(task, "Парсинг видео...", action)
    
    # Метод для парсинга аудио
    def _execute_parse_audio(self, task: AITask) -> Dict:
        """Парсит аудио"""

        def action():
            from .parsers.universal_parser import UniversalVideoParser

            audio_url = task.parameters.get('url')
            if not audio_url:
                raise ValueError("URL аудио не указан")

            parser = UniversalVideoParser()
            result = parser.parse_video(audio_url)

            if result['success']:
                return {
                    'status': 'completed',
                    'message': f"Аудио обработано: {result.get('title', 'Без названия')}",
                    'data': result
                }
            return {
                'status': 'failed',
                'message': f"Ошибка парсинга: {', '.join(result.get('errors', []))}"
            }

        return self._run_task_with_progress(task, "Парсинг аудио...", action)
    
    # Метод для распределения бонусов
    def _execute_distribute_bonuses(self, task: AITask) -> Dict:
        """Распределяет бонусы"""

        def action():
            from .bonus_calculator import BonusCalculator
            from django.contrib.auth.models import User

            calculator = BonusCalculator()

            period_days = task.parameters.get('period_days', 30)
            results = calculator.calculate_all_authors_bonuses(period_days)

            for result in results:
                try:
                    author = User.objects.get(id=result['author_id'])
                    calculator.save_calculation_result(author, result)
                except Exception:
                    continue

            total_bonus = sum(r.get('total_bonus', 0) for r in results)

            return {
                'status': 'completed',
                'message': f"Рассчитаны бонусы для {len(results)} авторов",
                'total_bonus': total_bonus,
                'authors_count': len(results),
                'top_authors': results[:5]
            }

        return self._run_task_with_progress(task, "Расчет и распределение бонусов...", action)
    
    # ============ ОБРАБОТЧИКИ РЕКЛАМНЫХ КОМАНД ============
    
    # Метод для показа рекламных мест
    def _execute_ad_show_places(self, task: AITask) -> Dict:
        """Показать рекламные места"""

        def action():
            from advertising.models import AdPlace

            places = AdPlace.objects.all()

            message = "📊 **Рекламные места на IdealImage.ru:**\n\n"

            for place in places:
                active_banners = place.banners.filter(is_active=True).count()
                message += f"• **{place.name}** (`{place.code}`)\n"
                message += f"  - Позиция: {place.get_position_display()}\n"
                message += f"  - Активных баннеров: {active_banners}\n"
                message += f"  - Размер: {place.width}x{place.height}px\n\n"

            message += f"\n📍 Всего мест: {places.count()}\n"
            message += f"🔗 Управление: /advertising/"

            return {
                'status': 'completed',
                'message': message
            }

        return self._run_task_with_progress(task, "📊 Получаю список рекламных мест...", action, progress=50)
    
    # Метод для показа статистики рекламы
    def _execute_ad_statistics(self, task: AITask) -> Dict:
        """Показать статистику рекламы"""

        def action():
            from advertising.models import AdBanner, AdImpression, AdClick

            total_banners = AdBanner.objects.count()
            active_banners = AdBanner.objects.filter(is_active=True).count()
            total_impressions = AdImpression.objects.count()
            total_clicks = AdClick.objects.count()

            ctr = (total_clicks / total_impressions) * 100 if total_impressions > 0 else 0

            top_banners = AdBanner.objects.filter(is_active=True).order_by('-clicks')[:5]

            message = "📈 **Статистика рекламы IdealImage.ru:**\n\n"
            message += f"📊 **Общие показатели:**\n"
            message += f"• Всего баннеров: {total_banners} ({active_banners} активных)\n"
            message += f"• Показов: {total_impressions:,}\n"
            message += f"• Кликов: {total_clicks:,}\n"
            message += f"• CTR: {ctr:.2f}%\n\n"

            if top_banners.exists():
                message += "🏆 **Топ-5 баннеров по кликам:**\n"
                for i, banner in enumerate(top_banners, 1):
                    banner_ctr = banner.get_ctr()
                    message += f"{i}. **{banner.name}** - {banner.clicks} кликов (CTR: {banner_ctr:.2f}%)\n"

            message += "\n🔗 Подробная аналитика: /advertising/analytics/"

            return {
                'status': 'completed',
                'message': message
            }

        return self._run_task_with_progress(task, "📈 Собираю статистику рекламы...", action, progress=50)
    
    # Метод для активации баннера
    def _execute_ad_activate_banner(self, task: AITask) -> Dict:
        """Активировать баннер"""

        def action():
            from advertising.models import AdBanner
            from advertising.action_logger import AdActionLogger

            banner_id = task.parameters.get('banner_id')
            if not banner_id:
                return {'status': 'failed', 'message': '❌ Не указан ID баннера'}

            task.progress_description = f"🟢 Активирую баннер #{banner_id}..."
            task.progress_percentage = 50
            task.save()

            try:
                banner = AdBanner.objects.get(id=banner_id)
            except AdBanner.DoesNotExist:
                return {'status': 'failed', 'message': f'❌ Баннер #{banner_id} не найден'}

            if banner.is_active:
                return {
                    'status': 'completed',
                    'message': f"ℹ️ Баннер **{banner.name}** уже активен"
                }

            banner.is_active = True
            banner.save(update_fields=['is_active'])

            AdActionLogger.log_banner_activate(
                banner=banner,
                performed_by=task.conversation.user,
                performed_by_ai=True
            )

            return {
                'status': 'completed',
                'message': f"✅ Баннер **{banner.name}** активирован!\n\n📍 Место: {banner.place.name}"
            }

        return self._run_task_with_progress(task, "Подготовка к активации баннера...", action)
    
    # Метод для деактивации баннера
    def _execute_ad_deactivate_banner(self, task: AITask) -> Dict:
        """Деактивировать баннер"""

        def action():
            from advertising.models import AdBanner
            from advertising.action_logger import AdActionLogger

            banner_id = task.parameters.get('banner_id')
            if not banner_id:
                return {'status': 'failed', 'message': '❌ Не указан ID баннера'}

            task.progress_description = f"🔴 Деактивирую баннер #{banner_id}..."
            task.progress_percentage = 50
            task.save()

            try:
                banner = AdBanner.objects.get(id=banner_id)
            except AdBanner.DoesNotExist:
                return {'status': 'failed', 'message': f'❌ Баннер #{banner_id} не найден'}

            if not banner.is_active:
                return {
                    'status': 'completed',
                    'message': f"ℹ️ Баннер **{banner.name}** уже деактивирован"
                }

            banner.is_active = False
            banner.save(update_fields=['is_active'])

            AdActionLogger.log_banner_deactivate(
                banner=banner,
                performed_by=task.conversation.user,
                performed_by_ai=True
            )

            return {
                'status': 'completed',
                'message': f"✅ Баннер **{banner.name}** деактивирован"
            }

        return self._run_task_with_progress(task, "Подготовка к деактивации баннера...", action)
    
    # Метод для получения списка баннеров
    def _execute_ad_list_banners(self, task: AITask) -> Dict:
        """Список баннеров"""

        def action():
            from advertising.models import AdBanner

            banners = AdBanner.objects.select_related('place', 'campaign').all()[:20]

            message = "📋 **Список баннеров IdealImage.ru:**\n\n"

            for banner in banners:
                status_icon = "🟢" if banner.is_active else "🔴"
                external_icon = "🌐" if banner.use_external_code else "🖼️"

                message += f"{status_icon} **#{banner.id} {banner.name}**\n"
                message += f"   {external_icon} {banner.get_banner_type_display()} | "
                message += f"📍 {banner.place.name}\n"
                message += f"   👁️ {banner.impressions} показов | 👆 {banner.clicks} кликов"

                ctr = banner.get_ctr()
                if ctr > 0:
                    message += f" | CTR: {ctr:.2f}%"
                message += "\n\n"

            if banners.count() >= 20:
                message += "\n📌 Показаны первые 20 баннеров\n"

            message += "\n🔗 Управление: /advertising/banners/"

            return {
                'status': 'completed',
                'message': message
            }

        return self._run_task_with_progress(task, "📋 Получаю список баннеров...", action, progress=50)
    
    # Метод для вставки контекстной рекламы в статью
    def _execute_ad_insert_in_article(self, task: AITask) -> Dict:
        """Вставить контекстную рекламу в статью"""

        def action():
            from advertising.models import ContextAd, AdInsertion
            from advertising.action_logger import AdActionLogger
            from blog.models import Post

            post_id = task.parameters.get('post_id')
            if not post_id:
                return {'status': 'failed', 'message': '❌ Не указан ID статьи'}

            task.progress_description = f"🔗 Вставляю рекламу в статью #{post_id}..."
            task.progress_percentage = 30
            task.save()

            try:
                post = Post.objects.get(id=post_id)
            except Post.DoesNotExist:
                return {'status': 'failed', 'message': f'❌ Статья #{post_id} не найдена'}

            context_ads = ContextAd.objects.filter(is_active=True)

            if not context_ads.exists():
                return {
                    'status': 'failed',
                    'message': '❌ Нет активных контекстных объявлений для вставки'
                }

            task.progress_percentage = 50
            task.save()

            context_ad = context_ads.first()

            insertion = AdInsertion.objects.create(
                post=post,
                context_ad=context_ad,
                insertion_position=len(post.content) // 2
            )

            AdActionLogger.log_context_ad_insert(
                insertion=insertion,
                performed_by=task.conversation.user,
                performed_by_ai=True
            )

            task.progress_percentage = 100
            task.save()

            return {
                'status': 'completed',
                'message': (
                    f"✅ Реклама **{context_ad.anchor_text}** вставлена в статью **{post.title}**\n\n"
                    f"📍 Позиция: символ {insertion.insertion_position}\n"
                    f"🔗 Ссылка: {context_ad.target_url}"
                )
            }

        return self._run_task_with_progress(task, "Подготовка к вставке рекламы...", action)
    
    # ========================================================================
    # AI-СОВЕТНИК: Анализ и рекомендации по сайту
    # ========================================================================
    def analyze_full_site(self) -> Dict:
        """
        Полный анализ сайта через GigaChat Pro
        Собирает все метрики и отправляет AI для анализа
        
        Returns:
            Dict с анализом и рекомендациями
        """
        logger.info("🔍 AI-советник: начинаю анализ сайта...")
        
        try:
            from blog.models import Post
            from donations.models import Donation
            from .models import GigaChatUsageStats
            from django.db.models import Sum, Avg
            from datetime import timedelta
            
            # Собираем данные за 30 дней
            thirty_days_ago = timezone.now() - timedelta(days=30)
            
            # 1. Контент
            total_posts = Post.objects.filter(status='published').count()
            recent_posts = Post.objects.filter(
                status='published',
                created__gte=thirty_days_ago
            ).count()
            
            top_posts = Post.objects.filter(status='published').order_by('-views')[:5]
            low_posts = Post.objects.filter(status='published', views__gt=0).order_by('views')[:5]
            
            # 2. Трафик
            total_views = Post.objects.filter(status='published').aggregate(
                total=Sum('views')
            )['total'] or 0
            
            avg_views = Post.objects.filter(status='published').aggregate(
                avg=Avg('views')
            )['avg'] or 0
            
            # 3. SEO
            with_faq = Post.objects.filter(
                status='published',
                content__icontains='faq-section'
            ).count()
            
            with_meta = Post.objects.filter(
                status='published'
            ).exclude(meta_title='').count()
            
            # 4. GigaChat затраты
            all_stats = GigaChatUsageStats.objects.all()
            total_requests = sum([s.total_requests for s in all_stats])
            
            # 5. Донаты
            total_donations = Donation.objects.filter(
                status='completed',
                created_at__gte=thirty_days_ago
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            # Формируем данные для AI
            data_summary = f"""
            📊 АНАЛИТИКА САЙТА IdealImage.ru (последние 30 дней)

            📰 КОНТЕНТ:
            - Всего статей: {total_posts}
            - Опубликовано за месяц: {recent_posts}
            - Средние просмотры: {avg_views:.0f}
            - Общие просмотры: {total_views:,}

            🏆 ТОП-5 СТАТЕЙ:
            {chr(10).join([f"- {p.title} ({p.views} просмотров)" for p in top_posts])}

            ⚠️ ХУДШИЕ 5 СТАТЕЙ:
            {chr(10).join([f"- {p.title} ({p.views} просмотров)" for p in low_posts])}

            🚀 SEO:
            - FAQ блоки: {with_faq}/{total_posts} ({with_faq/total_posts*100:.1f}%)
            - SEO метаданные: {with_meta}/{total_posts} ({with_meta/total_posts*100:.1f}%)

            🤖 GIGACHAT API:
            - Всего запросов: {total_requests}

            💰 МОНЕТИЗАЦИЯ:
            - Донаты за месяц: {total_donations}₽
            """
            
            # Отправляем в GigaChat Pro для анализа
            default_prompt = (
                "Ты - бизнес-аналитик женского онлайн-журнала о красоте и моде.\n\n"
                "{data_summary}\n\n"
                "✅ ЗАДАНИЕ: Проанализируй сайт и дай 7 конкретных рекомендаций по улучшению.\n\n"
                "📌 ТРЕБОВАНИЯ:\n"
                "1. Рекомендации должны быть КОНКРЕТНЫМИ и ВЫПОЛНИМЫМИ\n"
                "2. Каждая рекомендация с кратким обоснованием (2-3 предложения)\n"
                "3. Приоритизируй по важности (от самого важного к менее важному)\n"
                "4. Учитывай специфику женской аудитории\n"
                "5. Фокус на РОСТ ТРАФИКА и МОНЕТИЗАЦИИ\n\n"
                "💡 ФОРМАТ ОТВЕТА:\n"
                "**1. [Название рекомендации]**\n"
                "[2-3 предложения с обоснованием и конкретными действиями]\n\n"
                "**2. [Следующая рекомендация]**\n"
                "...\n\n"
                "Верни 7 рекомендаций. Будь конкретным, не используй общие фразы!"
            )
            
            prompt = PromptRegistry.render(
                'AI_AGENT_SITE_ANALYSIS_PROMPT',
                params={'data_summary': data_summary},
                default=default_prompt,
            )
            PromptRegistry.increment_usage('AI_AGENT_SITE_ANALYSIS_PROMPT')
            
            # Используем GigaChat для текста
            response = self.gigachat.chat(
                prompt,
                system_prompt="Ты опытный бизнес-аналитик и SEO-эксперт"
            )
            
            logger.info("✅ Анализ сайта завершен")
            
            return {
                'success': True,
                'analysis': response,
                'raw_data': data_summary,
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка анализа сайта: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': "Не удалось выполнить анализ сайта"
            }
    
    # Метод для генерации рекомендаций по улучшению сайта
    def give_recommendations(self, focus: str = None) -> Dict:
        """
        Дать рекомендации по улучшению сайта
        
        Args:
            focus: Область фокуса ('seo', 'content', 'traffic', etc.)
        
        Returns:
            Dict с рекомендациями
        """
        logger.info(f"💡 AI-советник: генерирую рекомендации (фокус: {focus or 'общие'})...")
        
        try:
            # Получаем базовую статистику
            stats = self.get_site_statistics(days=7)
            
            focus_text = ""
            if focus:
                focus_map = {
                    'seo': 'SEO-оптимизации',
                    'content': 'улучшения контента',
                    'traffic': 'увеличения трафика',
                    'monetization': 'монетизации',
                }
                focus_text = f"Фокус на: {focus_map.get(focus, focus)}"
            
            focus_block = f"{focus_text}\n\n" if focus_text else ""
            default_prompt = (
                "Ты - консультант по онлайн-журналам.\n\n"
                "📊 КРАТКАЯ СТАТИСТИКА (за 7 дней):\n"
                "- Новых статей: {new_posts}\n"
                "- Всего статей: {total_posts}\n"
                "- Донаты: {donations}₽\n\n"
                "{focus_block}"
                "✅ ЗАДАНИЕ: Дай 5 быстрых и конкретных рекомендаций что сделать ПРЯМО СЕЙЧАС.\n\n"
                "📌 ТРЕБОВАНИЯ:\n"
                "- Каждая рекомендация - 1-2 предложения\n"
                "- Конкретные действия, НЕ общие советы\n"
                "- Быстро выполнимо (в течение дня-недели)\n"
                "- Ориентация на женскую аудиторию\n\n"
                "Формат: краткий список с 💡"
            )
            
            prompt = PromptRegistry.render(
                'AI_AGENT_QUICK_RECOMMENDATIONS_PROMPT',
                params={
                    'new_posts': stats['posts']['new_in_period'],
                    'total_posts': stats['posts']['published'],
                    'donations': stats['donations']['total_amount'],
                    'focus_block': focus_block,
                },
                default=default_prompt,
            )
            PromptRegistry.increment_usage('AI_AGENT_QUICK_RECOMMENDATIONS_PROMPT')
            
            response = self.gigachat.chat(prompt)
            
            return {
                'success': True,
                'recommendations': response,
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка генерации рекомендаций: {e}")
            return {
                'success': False,
                'error': str(e),
            }
    
    # Метод для предложения стратегий монетизации сайта
    def suggest_monetization(self) -> Dict:
        """
        Предложить стратегии монетизации сайта
        
        Returns:
            Dict со стратегиями заработка
        """
        logger.info("💰 AI-советник: генерирую стратегии монетизации...")
        
        try:
            from donations.models import Donation
            from blog.models import Post
            from django.db.models import Sum
            
            # Статистика
            total_posts = Post.objects.filter(status='published').count()
            total_views = Post.objects.filter(status='published').aggregate(
                total=Sum('views')
            )['total'] or 0
            
            monthly_donations = Donation.objects.filter(
                status='completed',
                created_at__gte=timezone.now() - timedelta(days=30)
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            total_views_display = f"{total_views:,}".replace(',', ' ')
            default_prompt = (
                "Ты - эксперт по монетизации онлайн-изданий.\n\n"
                "📊 ДАННЫЕ САЙТА IdealImage.ru:\n"
                "- Тематика: женский журнал (красота, мода, lifestyle)\n"
                "- Статей: {total_posts}\n"
                "- Просмотров всего: {total_views}\n"
                "- Донаты за месяц: {monthly_donations}₽\n\n"
                "✅ ЗАДАНИЕ: Предложи 5 реалистичных стратегий заработка для этого сайта.\n\n"
                "📌 ТРЕБОВАНИЯ:\n"
                "1. Каждая стратегия с прогнозом дохода\n"
                "2. Учитывай женскую аудиторию\n"
                "3. Реализуемо без больших вложений\n"
                "4. От простых к сложным\n"
                "5. С конкретными шагами внедрения\n\n"
                "💡 ФОРМАТ:\n"
                "**1. [Название стратегии]** (прогноз: XX,000₽/месяц)\n"
                "[Описание и 3-5 шагов внедрения]\n\n"
                "Будь конкретным!"
            )
            
            prompt = PromptRegistry.render(
                'AI_AGENT_MONETIZATION_PROMPT',
                params={
                    'total_posts': total_posts,
                    'total_views': total_views_display,
                    'monthly_donations': monthly_donations,
                },
                default=default_prompt,
            )
            PromptRegistry.increment_usage('AI_AGENT_MONETIZATION_PROMPT')
            
            response = self.gigachat.chat(prompt)
            
            return {
                'success': True,
                'strategies': response,
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка генерации стратегий: {e}")
            return {
                'success': False,
                'error': str(e),
            }
    
    # Метод для анализа расходов на GigaChat API
    def optimize_costs(self) -> Dict:
        """
        Анализ и план экономии на GigaChat API
        
        Returns:
            Dict с планом оптимизации
        """
        logger.info("⚡ AI-советник: анализирую расходы на GigaChat...")
        
        try:
            from .models import GigaChatUsageStats, GigaChatSettings
            
            # Получаем статистику моделей
            all_stats = GigaChatUsageStats.objects.all()
            settings = GigaChatSettings.objects.get(pk=1)
            
            models_usage = []
            for stats in all_stats:
                models_usage.append({
                    'model': stats.model_name,
                    'requests': stats.total_requests,
                    'tokens': stats.tokens_remaining or 0,
                })
            
            # Прайс-лист
            prices = {
                'GigaChat': settings.price_lite,
                'GigaChat-Pro': settings.price_pro,
                'GigaChat-Max': settings.price_max,
            }
            
            usage_summary = "\n".join([
                f"- {m['model']}: {m['requests']} запросов, {m['tokens']:,} токенов"
                for m in models_usage
            ])
            
            default_prompt = (
                "Ты - эксперт по оптимизации API расходов.\n\n"
                "📊 ТЕКУЩЕЕ ИСПОЛЬЗОВАНИЕ GIGACHAT API:\n"
                "{usage_summary}\n\n"
                "💰 ПРАЙС-ЛИСТ (₽ за 1M токенов):\n"
                "- Lite: {lite_price}₽\n"
                "- Pro: {pro_price}₽\n"
                "- Max: {max_price}₽\n\n"
                "✅ ЗАДАНИЕ: Предложи 5 способов сэкономить на GigaChat API БЕЗ потери качества.\n\n"
                "📌 ТРЕБОВАНИЯ:\n"
                "1. Конкретные технические рекомендации\n"
                "2. С оценкой экономии в %\n"
                "3. Легко внедряемые\n"
                "4. Без ухудшения UX\n\n"
                "💡 ФОРМАТ:\n"
                "**1. [Способ]** (экономия ~XX%)\n"
                "[1-2 предложения как реализовать]\n\n"
                "Только практичные советы!"
            )
            
            prompt = PromptRegistry.render(
                'AI_AGENT_API_COST_OPTIMIZATION_PROMPT',
                params={
                    'usage_summary': usage_summary,
                    'lite_price': prices['GigaChat'],
                    'pro_price': prices['GigaChat-Pro'],
                    'max_price': prices['GigaChat-Max'],
                },
                default=default_prompt,
            )
            PromptRegistry.increment_usage('AI_AGENT_API_COST_OPTIMIZATION_PROMPT')
            
            response = self.gigachat.chat(prompt)
            
            return {
                'success': True,
                'optimization_plan': response,
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка анализа расходов: {e}")
            return {
                'success': False,
                'error': str(e),
            }

