"""
Management command для очистки базы данных AI Agent
Удаляет проблемные статьи:
- БЕЗ изображения
- С битыми изображениями
- С дублированными изображениями
"""
from django.core.management.base import BaseCommand
from Asistent.moderations.signals import ai_agent_cleanup_database


class Command(BaseCommand):
    help = 'AI Agent очистка базы данных от проблемных статей'

    def handle(self, *args, **options):
        self.stdout.write('[OK] AI Agent проверяет базу данных...')
        
        result = ai_agent_cleanup_database()
        
        if result:
            self.stdout.write(self.style.SUCCESS('\n[SUCCESS] Очистка завершена!'))
            self.stdout.write(f'  Удалено БЕЗ изображения: {result["deleted_no_image"]}')
            self.stdout.write(f'  Удалено с битыми изображениями: {result["deleted_broken_image"]}')
            self.stdout.write(f'  Переведено в черновики (дубли): {result["changed_to_draft"]}')
            self.stdout.write('\n[INFO] Результаты сохранены в чат: /asistent/chat/')
        else:
            self.stdout.write(self.style.WARNING('[WARNING] Очистка не выполнена'))

