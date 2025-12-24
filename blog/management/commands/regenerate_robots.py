"""
Команда для регенерации robots.txt
"""
from django.core.management.base import BaseCommand
from utilits.robots_generator import RobotsGenerator


class Command(BaseCommand):
    help = 'Регенерация robots.txt с актуальными правилами'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--add-disallow',
            type=str,
            help='Добавить дополнительное Disallow правило'
        )
        parser.add_argument(
            '--preview',
            action='store_true',
            help='Только показать содержимое без сохранения'
        )
    
    def handle(self, *args, **options):
        generator = RobotsGenerator()
        
        # Добавляем пользовательское правило если указано
        if options['add_disallow']:
            generator.add_custom_disallow(options['add_disallow'])
            self.stdout.write(self.style.SUCCESS(
                f"✅ Добавлено правило: {options['add_disallow']}"
            ))
        
        # Показываем содержимое
        self.stdout.write('\n📄 Содержимое robots.txt:')
        self.stdout.write('-' * 70)
        self.stdout.write(generator.generate())
        self.stdout.write('-' * 70)
        
        # Сохраняем если не preview режим
        if not options['preview']:
            if generator.save_to_file():
                self.stdout.write(self.style.SUCCESS('\n✅ robots.txt успешно обновлён'))
            else:
                self.stdout.write(self.style.ERROR('\n❌ Ошибка при генерации robots.txt'))
        else:
            self.stdout.write(self.style.WARNING('\n⚠️ Режим preview - файл НЕ сохранён'))

