"""
Команда для анализа текущего состояния расписаний и заданий
"""
from django.core.management.base import BaseCommand
from django_q.models import Schedule as DQSchedule, Task
from django.utils import timezone
from datetime import timedelta
from Asistent.models import AISchedule, AIScheduleRun  # Через __getattr__


class Command(BaseCommand):
    help = 'Анализ текущего состояния расписаний и заданий'

    def handle(self, *args, **options):
        now = timezone.now()
        
        self.stdout.write(self.style.SUCCESS('=' * 80))
        self.stdout.write(self.style.SUCCESS('  📊 АНАЛИЗ РАСПИСАНИЙ И ЗАДАНИЙ'))
        self.stdout.write(self.style.SUCCESS('=' * 80))
        self.stdout.write('')
        
        # 1. Анализ AISchedule
        self._analyze_ai_schedules(now)
        
        # 2. Анализ Django-Q Schedule
        self._analyze_djangoq_schedules(now)
        
        # 3. Анализ последних запусков
        self._analyze_recent_runs(now)
        
        # 4. Анализ задач Django-Q
        self._analyze_djangoq_tasks(now)
        
        # 5. Рекомендации
        self._show_recommendations()

    def _analyze_ai_schedules(self, now):
        """Анализ AISchedule"""
        self.stdout.write(self.style.SUCCESS('[1/5] АНАЛИЗ AISCHEDULE'))
        self.stdout.write('-' * 80)
        
        all_schedules = AISchedule.objects.all()
        active_schedules = all_schedules.filter(is_active=True)
        inactive_schedules = all_schedules.filter(is_active=False)
        
        self.stdout.write(f'📋 Всего расписаний: {all_schedules.count()}')
        self.stdout.write(f'✅ Активных: {active_schedules.count()}')
        self.stdout.write(f'⏸️ Неактивных: {inactive_schedules.count()}')
        self.stdout.write('')
        
        if active_schedules.exists():
            self.stdout.write('📅 АКТИВНЫЕ РАСПИСАНИЯ:')
            for schedule in active_schedules.select_related('category', 'prompt_template').order_by('id'):
                status_icon = '🟢' if schedule.next_run and schedule.next_run > now else '🟡'
                last_run_str = schedule.last_run.strftime('%d.%m.%Y %H:%M') if schedule.last_run else 'Никогда'
                next_run_str = schedule.next_run.strftime('%d.%m.%Y %H:%M') if schedule.next_run else 'Не установлено'
                
                self.stdout.write(f'  {status_icon} #{schedule.id} - {schedule.name}')
                self.stdout.write(f'     Тип: {schedule.get_strategy_type_display()} | '
                                f'Частота: {schedule.get_posting_frequency_display()}')
                self.stdout.write(f'     Расписание: {schedule.get_schedule_kind_display()}')
                if schedule.scheduled_time:
                    self.stdout.write(f'     Время: {schedule.scheduled_time}')
                if schedule.interval_minutes:
                    self.stdout.write(f'     Интервал: {schedule.interval_minutes} мин')
                if schedule.cron_expression:
                    self.stdout.write(f'     CRON: {schedule.cron_expression}')
                self.stdout.write(f'     Последний запуск: {last_run_str}')
                self.stdout.write(f'     Следующий запуск: {next_run_str}')
                self.stdout.write(f'     Статей за раз: {schedule.articles_per_run}')
                
                # Проверка синхронизации с Django-Q
                dq_schedule = DQSchedule.objects.filter(name=f'ai_schedule_{schedule.id}').first()
                if dq_schedule:
                    func_status = '✅' if 'schedule.tasks' in dq_schedule.func else '⚠️'
                    self.stdout.write(f'     {func_status} Django-Q: {dq_schedule.func}')
                    if dq_schedule.next_run:
                        dq_next = dq_schedule.next_run.strftime('%d.%m.%Y %H:%M')
                        self.stdout.write(f'     Django-Q next_run: {dq_next}')
                else:
                    self.stdout.write(self.style.WARNING(f'     ⚠️ Django-Q: НЕ синхронизировано!'))
                
                self.stdout.write('')
        else:
            self.stdout.write('📭 Нет активных расписаний')
        
        self.stdout.write('')

    def _analyze_djangoq_schedules(self, now):
        """Анализ Django-Q Schedule"""
        self.stdout.write(self.style.SUCCESS('[2/5] АНАЛИЗ DJANGO-Q SCHEDULE'))
        self.stdout.write('-' * 80)
        
        all_dq = DQSchedule.objects.all()
        ai_dq = all_dq.filter(name__startswith='ai_schedule_')
        other_dq = all_dq.exclude(name__startswith='ai_schedule_')
        
        self.stdout.write(f'📋 Всего Django-Q расписаний: {all_dq.count()}')
        self.stdout.write(f'🤖 AI расписаний: {ai_dq.count()}')
        self.stdout.write(f'⚙️ Других расписаний: {other_dq.count()}')
        self.stdout.write('')
        
        # Проверка путей
        old_path = ai_dq.filter(func='Asistent.tasks.run_specific_schedule').count()
        new_path = ai_dq.filter(func='Asistent.schedule.tasks.run_specific_schedule').count()
        
        self.stdout.write(f'📌 Пути функций:')
        self.stdout.write(f'   Старый путь: {old_path}')
        self.stdout.write(f'   Новый путь: {new_path}')
        
        if old_path > 0:
            self.stdout.write(self.style.WARNING(f'   ⚠️ Найдено {old_path} расписаний со старым путем!'))
            self.stdout.write(self.style.WARNING(f'   💡 Запустите: python manage.py update_schedule_paths'))
        
        self.stdout.write('')
        
        # Ближайшие запуски
        upcoming = ai_dq.filter(next_run__gt=now).order_by('next_run')[:5]
        if upcoming.exists():
            self.stdout.write('⏰ БЛИЖАЙШИЕ ЗАПУСКИ:')
            for dq in upcoming:
                schedule_id = dq.name.replace('ai_schedule_', '')
                try:
                    ai_schedule = AISchedule.objects.get(id=schedule_id)
                    time_until = dq.next_run - now
                    hours = int(time_until.total_seconds() / 3600)
                    minutes = int((time_until.total_seconds() % 3600) / 60)
                    self.stdout.write(f'   📅 {ai_schedule.name}: через {hours}ч {minutes}м ({dq.next_run.strftime("%d.%m.%Y %H:%M")})')
                except AISchedule.DoesNotExist:
                    self.stdout.write(f'   ⚠️ Расписание ID={schedule_id} не найдено в AISchedule')
            self.stdout.write('')
        
        self.stdout.write('')

    def _analyze_recent_runs(self, now):
        """Анализ последних запусков"""
        self.stdout.write(self.style.SUCCESS('[3/5] АНАЛИЗ ПОСЛЕДНИХ ЗАПУСКОВ'))
        self.stdout.write('-' * 80)
        
        recent_runs = AIScheduleRun.objects.select_related('schedule').order_by('-started_at')[:10]
        
        if recent_runs.exists():
            self.stdout.write('📊 ПОСЛЕДНИЕ 10 ЗАПУСКОВ:')
            for run in recent_runs:
                status_icons = {
                    'running': '🔄',
                    'success': '✅',
                    'failed': '❌',
                    'partial': '⚠️'
                }
                icon = status_icons.get(run.status, '❓')
                
                duration_str = ''
                if run.duration:
                    seconds = run.duration.total_seconds()
                    if seconds < 60:
                        duration_str = f'{int(seconds)}с'
                    else:
                        duration_str = f'{int(seconds/60)}м'
                
                self.stdout.write(f'  {icon} {run.schedule.name} - {run.get_status_display()}')
                self.stdout.write(f'     Время: {run.started_at.strftime("%d.%m.%Y %H:%M:%S")}')
                if duration_str:
                    self.stdout.write(f'     Длительность: {duration_str}')
                self.stdout.write(f'     Создано: {run.created_count} объектов')
                if run.errors:
                    self.stdout.write(self.style.ERROR(f'     Ошибки: {len(run.errors)}'))
                self.stdout.write('')
        else:
            self.stdout.write('📭 Нет запусков')
        
        # Статистика за сегодня
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_runs = AIScheduleRun.objects.filter(started_at__gte=today_start)
        success_today = today_runs.filter(status='success').count()
        failed_today = today_runs.filter(status='failed').count()
        running_today = today_runs.filter(status='running').count()
        
        self.stdout.write(f'📈 СТАТИСТИКА ЗА СЕГОДНЯ:')
        self.stdout.write(f'   Всего запусков: {today_runs.count()}')
        self.stdout.write(f'   ✅ Успешных: {success_today}')
        self.stdout.write(f'   ❌ Ошибок: {failed_today}')
        self.stdout.write(f'   🔄 Выполняется: {running_today}')
        self.stdout.write('')

    def _analyze_djangoq_tasks(self, now):
        """Анализ задач Django-Q"""
        self.stdout.write(self.style.SUCCESS('[4/5] АНАЛИЗ DJANGO-Q ЗАДАЧ'))
        self.stdout.write('-' * 80)
        
        # Активные задачи
        active_tasks = Task.objects.filter(stopped__isnull=True, started__isnull=False)
        queued_tasks = Task.objects.filter(started__isnull=True)
        
        self.stdout.write(f'🔄 Активных задач: {active_tasks.count()}')
        self.stdout.write(f'⏳ В очереди: {queued_tasks.count()}')
        
        # Задачи за последний час
        hour_ago = now - timedelta(hours=1)
        recent_tasks = Task.objects.filter(started__gte=hour_ago)
        success_recent = recent_tasks.filter(success=True).count()
        failed_recent = recent_tasks.filter(success=False).count()
        
        self.stdout.write(f'📊 За последний час:')
        self.stdout.write(f'   Всего: {recent_tasks.count()}')
        self.stdout.write(f'   ✅ Успешных: {success_recent}')
        self.stdout.write(f'   ❌ Ошибок: {failed_recent}')
        
        # Задачи связанные с расписаниями
        schedule_tasks = recent_tasks.filter(
            func__in=['Asistent.tasks.run_specific_schedule', 'Asistent.schedule.tasks.run_specific_schedule']
        )
        if schedule_tasks.exists():
            self.stdout.write(f'📅 Задач расписаний за час: {schedule_tasks.count()}')
            schedule_success = schedule_tasks.filter(success=True).count()
            schedule_failed = schedule_tasks.filter(success=False).count()
            self.stdout.write(f'   ✅ Успешных: {schedule_success}')
            self.stdout.write(f'   ❌ Ошибок: {schedule_failed}')
        
        self.stdout.write('')

    def _show_recommendations(self):
        """Показать рекомендации"""
        self.stdout.write(self.style.SUCCESS('[5/5] РЕКОМЕНДАЦИИ'))
        self.stdout.write('-' * 80)
        
        recommendations = []
        
        # Проверка синхронизации
        active_ai = AISchedule.objects.filter(is_active=True).count()
        ai_dq = DQSchedule.objects.filter(name__startswith='ai_schedule_').count()
        
        if active_ai != ai_dq:
            recommendations.append(
                f'⚠️ Несоответствие: {active_ai} активных AISchedule, но {ai_dq} в Django-Q. '
                f'Запустите: python manage.py sync_schedules --force'
            )
        
        # Проверка старых путей
        old_path_count = DQSchedule.objects.filter(
            name__startswith='ai_schedule_',
            func='Asistent.tasks.run_specific_schedule'
        ).count()
        
        if old_path_count > 0:
            recommendations.append(
                f'⚠️ Найдено {old_path_count} расписаний со старым путем. '
                f'Запустите: python manage.py update_schedule_paths'
            )
        
        # Проверка qcluster
        try:
            from django_q.models import OrmQ
            # Проверяем наличие активных воркеров через ORM (без distinct для MySQL)
            cluster_keys = OrmQ.objects.filter(key__startswith='cluster').values_list('key', flat=True)
            active_workers = len(set(cluster_keys))
            if active_workers == 0:
                # Альтернативная проверка через процессы
                import os
                import subprocess
                try:
                    # Проверяем наличие процесса qcluster
                    result = subprocess.run(
                        ['tasklist', '/FI', 'IMAGENAME eq python.exe', '/FO', 'CSV'],
                        capture_output=True,
                        text=True,
                        timeout=5
                    ) if os.name == 'nt' else subprocess.run(
                        ['ps', 'aux'],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if 'qcluster' not in result.stdout.lower() and 'manage.py' in result.stdout:
                        recommendations.append(
                            '⚠️ Django-Q Cluster возможно не запущен! Проверьте: python manage.py qcluster'
                        )
                except:
                    recommendations.append(
                        '⚠️ Не удалось проверить процессы. Убедитесь, что Django-Q Cluster запущен: python manage.py qcluster'
                    )
        except ImportError:
            recommendations.append(
                '⚠️ Не удалось импортировать django_q.models. Проверьте установку Django-Q.'
            )
        except Exception as e:
            recommendations.append(
                f'⚠️ Ошибка проверки Django-Q Cluster: {e}. Проверьте вручную: python manage.py qcluster'
            )
        
        # Проверка расписаний без next_run
        schedules_without_next = AISchedule.objects.filter(
            is_active=True,
            next_run__isnull=True
        )
        if schedules_without_next.exists():
            recommendations.append(
                f'⚠️ Найдено {schedules_without_next.count()} активных расписаний без next_run. '
                f'Обновите их в админке или через: schedule.update_next_run()'
            )
        
        if recommendations:
            for i, rec in enumerate(recommendations, 1):
                self.stdout.write(self.style.WARNING(f'{i}. {rec}'))
        else:
            self.stdout.write(self.style.SUCCESS('✅ Все проверки пройдены! Система работает корректно.'))
        
        self.stdout.write('')
        self.stdout.write('=' * 80)

