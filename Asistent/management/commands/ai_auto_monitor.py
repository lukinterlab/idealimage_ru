"""
Management command для автоматического мониторинга и управления AI Agent
Agent будет автоматически:
- Проверять старые задачи и удалять их
- Модерировать контент
- Давать советы
- Контролировать процессы
"""
import time

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from Asistent.ai_agent import AIAgent
from Asistent.models import AITask, AIConversation, AIMessage
from django.db import OperationalError, connections
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'AI Agent автоматический мониторинг и управление'

    def add_arguments(self, parser):
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Подробный вывод',
        )

    def handle(self, *args, **options):
        verbose = options.get('verbose', False)
        retries = 2
        last_error: OperationalError | None = None

        for attempt in range(1, retries + 1):
            try:
                return self._run_monitor(verbose=verbose)
            except OperationalError as exc:
                last_error = exc
                if not self._is_mysql_gone_error(exc):
                    raise
                self.stdout.write(
                    self.style.WARNING(
                        f"[retry {attempt}/{retries}] MySQL разорвал соединение, пробую переподключиться..."
                    )
                )
                connections.close_all()
                time.sleep(3)

        raise CommandError(f"Мониторинг остановлен: {last_error}")

    def _run_monitor(self, verbose: bool = False):
        self.stdout.write('[OK] AI Agent автоматический мониторинг запущен...')

        # Получаем первого superuser для работы от его имени
        admin = User.objects.filter(is_superuser=True).first()
        if not admin:
            self.stdout.write(self.style.ERROR('[FAIL] Superuser не найден!'))
            return

        agent = AIAgent()
        
        # ==================================================================
        # 1. ПРОВЕРКА И ОЧИСТКА СТАРЫХ ЗАДАЧ
        # ==================================================================
        self.stdout.write('\n[1/5] Проверяю старые задачи...')
        
        # Находим задачи старше 7 дней со статусом completed/failed
        old_date = timezone.now() - timedelta(days=7)
        old_tasks = AITask.objects.filter(
            created_at__lt=old_date,
            status__in=['completed', 'failed']
        )
        
        old_count = old_tasks.count()
        
        if old_count > 0:
            self.stdout.write(f'[!] Найдено {old_count} старых задач для удаления')
            
            # Создаём системный диалог для логирования
            conversation, _ = AIConversation.objects.get_or_create(
                admin=admin,
                title='Автоматический мониторинг',
                defaults={'is_active': True}
            )
            
            # Agent удаляет старые задачи
            deleted_types = list(old_tasks.values_list('task_type', flat=True)[:5])
            old_tasks.delete()
            
            message = f"✅ Автоматическая очистка: Удалено {old_count} старых задач (старше 7 дней)\n\n"
            message += "Примеры удалённых типов задач:\n"
            for task_type in deleted_types:
                message += f"  - {task_type}\n"
            
            AIMessage.objects.create(
                conversation=conversation,
                role='assistant',
                content=message
            )
            
            self.stdout.write(self.style.SUCCESS(f'[OK] Удалено {old_count} старых задач'))
        else:
            self.stdout.write('[OK] Старых задач не найдено')
        
        # ==================================================================
        # 2. ПРОВЕРКА КОНТЕНТА НА МОДЕРАЦИЮ
        # ==================================================================
        self.stdout.write('\n[2/5] Проверяю контент на модерацию...')
        
        from blog.models import Post
        from blog.models import Comment
        
        # Статьи в черновиках старше 1 дня
        draft_posts = Post.objects.filter(
            status='draft',
            created__lt=timezone.now() - timedelta(days=1)
        ).count()
        
        # Комментарии на модерации
        pending_comments = 0  # Временно отключено
        # pending_comments = Comment.objects.filter(is_approved=False).count()
        
        if draft_posts > 0 or pending_comments > 0:
            conversation, _ = AIConversation.objects.get_or_create(
                admin=admin,
                title='Автоматический мониторинг',
                defaults={'is_active': True}
            )
            
            message = f"⚠️ Контент требует внимания:\n\n"
            
            if draft_posts > 0:
                message += f"📝 Статей в черновиках: {draft_posts}\n"
                message += f"💡 Рекомендация: Проверьте черновики старше 1 дня\n\n"
            
            if pending_comments > 0:
                message += f"💬 Комментариев на модерации: {pending_comments}\n"
                message += f"💡 Рекомендация: Промодерируйте комментарии\n"
            
            AIMessage.objects.create(
                conversation=conversation,
                role='assistant',
                content=message
            )
            
            self.stdout.write(f'[!] Черновиков: {draft_posts}, Комментариев: {pending_comments}')
        else:
            self.stdout.write('[OK] Контент в порядке')
        
        # ==================================================================
        # 3. ПРОВЕРКА РАСПИСАНИЙ
        # ==================================================================
        self.stdout.write('\n[3/5] Проверяю расписания...')
        
        from Asistent.models import AISchedule  # Через __getattr__
        from django_q.models import Schedule as DQSchedule
        
        # Неактивные расписания
        inactive_schedules = AISchedule.objects.filter(is_active=False).count()
        
        # Расписания без категории
        no_category_schedules = AISchedule.objects.filter(category__isnull=True).count()
        
        # Проверка ошибок schedule_not_found в последних задачах
        recent_failed = AITask.objects.filter(
            status='failed',
            error_message__icontains='schedule_not_found',
            created_at__gte=timezone.now() - timedelta(hours=24)
        )
        schedule_not_found_count = recent_failed.count()
        
        # Проверка синхронизации Django-Q с AISchedule
        dq_schedules = DQSchedule.objects.filter(func='Asistent.tasks.run_specific_schedule')
        missing_schedules = []
        for dq_schedule in dq_schedules:
            try:
                schedule_id = int(dq_schedule.args)
                if not AISchedule.objects.filter(id=schedule_id, is_active=True).exists():
                    missing_schedules.append(schedule_id)
            except (ValueError, AttributeError):
                pass
        
        issues_found = (
            inactive_schedules > 0 or 
            no_category_schedules > 0 or 
            schedule_not_found_count > 0 or 
            len(missing_schedules) > 0
        )
        
        if issues_found:
            conversation, _ = AIConversation.objects.get_or_create(
                admin=admin,
                title='Автоматический мониторинг',
                defaults={'is_active': True}
            )
            
            message = f"📅 ПРОВЕРКА РАСПИСАНИЙ:\n\n"
            
            if inactive_schedules > 0:
                message += f"⏸️ Неактивных расписаний: {inactive_schedules}\n"
            
            if no_category_schedules > 0:
                message += f"⚠️ Расписаний без категории: {no_category_schedules}\n"
            
            if schedule_not_found_count > 0:
                message += f"\n❌ КРИТИЧНО: Найдено {schedule_not_found_count} ошибок 'schedule_not_found' за последние 24 часа!\n"
                message += f"💡 РЕШЕНИЕ: Запустите 'python manage.py sync_schedules --force' для очистки\n"
            
            if len(missing_schedules) > 0:
                message += f"\n⚠️ Django-Q содержит расписания для несуществующих AISchedule: {missing_schedules}\n"
                message += f"💡 РЕШЕНИЕ: Запустите 'python manage.py sync_schedules --force' для синхронизации\n"
            
            AIMessage.objects.create(
                conversation=conversation,
                role='assistant',
                content=message
            )
            
            self.stdout.write(f'[!] Неактивных: {inactive_schedules}, Без категории: {no_category_schedules}')
            if schedule_not_found_count > 0:
                self.stdout.write(self.style.ERROR(f'[CRITICAL] Ошибок schedule_not_found: {schedule_not_found_count}'))
            if len(missing_schedules) > 0:
                self.stdout.write(self.style.WARNING(f'[!] Несуществующих расписаний в Django-Q: {len(missing_schedules)}'))
        else:
            self.stdout.write('[OK] Расписания в порядке')
        
        # ==================================================================
        # 4. АНАЛИТИКА И СОВЕТЫ
        # ==================================================================
        self.stdout.write('\n[4/5] Анализирую статистику...')
        
        # Получаем статистику через Agent
        try:
            stats = agent.get_site_statistics(days=7)
        except Exception as e:
            stats = None
            logger.warning(f"Ошибка получения статистики: {e}")
        
        conversation, _ = AIConversation.objects.get_or_create(
            admin=admin,
            title='Автоматический мониторинг',
            defaults={'is_active': True}
        )
        
        message = f"📊 Еженедельная статистика (последние 7 дней):\n\n"
        
        if stats:
            posts_stats = stats.get('posts', {})
            message += f"📝 Статьи:\n"
            message += f"  - Всего: {posts_stats.get('total', 0)}\n"
            message += f"  - Опубликовано: {posts_stats.get('published', 0)}\n"
            message += f"  - Черновиков: {posts_stats.get('draft', 0)}\n"
            message += f"  - За неделю: {posts_stats.get('last_week', 0)}\n\n"
            
            ads_stats = stats.get('advertising', {})
            message += f"📢 Реклама:\n"
            message += f"  - Баннеров: {ads_stats.get('total_banners', 0)}\n"
            message += f"  - Показов: {ads_stats.get('impressions', 0)}\n"
            message += f"  - Кликов: {ads_stats.get('clicks', 0)}\n"
            if ads_stats.get('impressions', 0) > 0:
                ctr = (ads_stats.get('clicks', 0) / ads_stats.get('impressions', 1)) * 100
                message += f"  - CTR: {ctr:.2f}%\n\n"
            
            # Советы
            message += f"💡 РЕКОМЕНДАЦИИ:\n"
            
            if posts_stats.get('draft', 0) > 10:
                message += f"  ⚠️ Много черновиков ({posts_stats.get('draft', 0)}) - проверьте почему не публикуются\n"
            
            if posts_stats.get('last_week', 0) < 20:
                message += f"  ⚠️ Мало статей за неделю ({posts_stats.get('last_week', 0)}) - проверьте расписания\n"
            
            if ads_stats.get('impressions', 0) > 0:
                ctr = (ads_stats.get('clicks', 0) / ads_stats.get('impressions', 1)) * 100
                if ctr < 1.0:
                    message += f"  ⚠️ Низкий CTR ({ctr:.2f}%) - оптимизируйте баннеры\n"
        
        AIMessage.objects.create(
            conversation=conversation,
            role='assistant',
            content=message
        )
        
        self.stdout.write('[OK] Статистика проанализирована')
        
        # ==================================================================
        # 5. ПРОВЕРКА СИСТЕМЫ
        # ==================================================================
        self.stdout.write('\n[5/5] Проверяю систему...')
        
        # Проверка Django-Q
        try:
            from django_q.models import Schedule as DQSchedule
            dq_schedules_count = DQSchedule.objects.count()
            self.stdout.write(f'[OK] Django-Q: {dq_schedules_count} расписаний')
        except Exception as e:
            self.stdout.write(f'[!] Django-Q: {str(e)}')
        
        # Проверка базы знаний
        from Asistent.models import AIKnowledgeBase
        kb_count = AIKnowledgeBase.objects.filter(is_active=True).count()
        self.stdout.write(f'[OK] База знаний: {kb_count} активных записей')
        
        # ==================================================================
        # ИТОГО
        # ==================================================================
        self.stdout.write(self.style.SUCCESS('\n[SUCCESS] Автоматический мониторинг завершён!'))
        self.stdout.write(f'\n[INFO] Результаты сохранены в диалоге "Автоматический мониторинг"')
        self.stdout.write(f'[INFO] Откройте чат: /asistent/chat/')
        self.stdout.write(f'[INFO] Следующий запуск: через 1 час (настройте через cron)')

    @staticmethod
    def _is_mysql_gone_error(exc: OperationalError) -> bool:
        code = exc.args[0] if exc.args else None
        return code == 2006 or "MySQL server has gone away" in str(exc)

