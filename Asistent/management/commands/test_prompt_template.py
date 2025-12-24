"""
Команда для тестирования промпт шаблона из консоли
"""
import logging
from django.core.management.base import BaseCommand
from Asistent.models import PromptTemplate
from Asistent.generators.universal import UniversalContentGenerator
from Asistent.generators.base import GeneratorConfig

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Тестирование промпт шаблона с генерацией контента'

    def add_arguments(self, parser):
        parser.add_argument(
            'template_id',
            type=int,
            help='ID промпт шаблона для тестирования'
        )
        parser.add_argument(
            '--variables',
            type=str,
            nargs='*',
            help='Переменные для промпта в формате key=value (например: zodiac_sign=Овен date=12.12.2025)',
            default=[]
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Подробный вывод логов'
        )

    def handle(self, *args, **options):
        template_id = options['template_id']
        variables_list = options['variables']
        verbose = options['verbose']
        
        # Настройка уровня логирования
        if verbose:
            logging.getLogger('Asistent').setLevel(logging.DEBUG)
            logging.getLogger('Asistent.gigachat_api').setLevel(logging.DEBUG)
        
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('  🧪 ТЕСТИРОВАНИЕ ПРОМПТ ШАБЛОНА'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write('')
        
        # Получаем шаблон
        try:
            template = PromptTemplate.objects.get(id=template_id)
            self.stdout.write(self.style.SUCCESS(f'✅ Шаблон найден: {template.name}'))
            self.stdout.write(f'   ID: {template.id}')
            self.stdout.write(f'   Категория: {template.category or "Не указана"}')
            self.stdout.write(f'   Активен: {"Да" if template.is_active else "Нет"}')
            if template.variables:
                self.stdout.write(f'   Переменные: {", ".join(template.variables)}')
            self.stdout.write('')
        except PromptTemplate.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'❌ Шаблон с ID {template_id} не найден!'))
            return
        
        # Парсим переменные
        variables = {}
        if variables_list:
            self.stdout.write('📝 Переменные:')
            for var_str in variables_list:
                if '=' in var_str:
                    key, value = var_str.split('=', 1)
                    variables[key.strip()] = value.strip()
                    self.stdout.write(f'   {key.strip()} = {value.strip()}')
                else:
                    self.stdout.write(self.style.WARNING(f'   ⚠️ Пропущена переменная (нет =): {var_str}'))
            self.stdout.write('')
        
        # Создаем генератор
        self.stdout.write('🔧 Создание генератора...')
        try:
            config = GeneratorConfig.for_interactive()
            generator = UniversalContentGenerator(template, config)
            self.stdout.write(self.style.SUCCESS('   ✅ Генератор создан'))
            self.stdout.write('')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'   ❌ Ошибка создания генератора: {e}'))
            logger.exception("Ошибка создания генератора")
            return
        
        # Запускаем генерацию
        self.stdout.write('🚀 Запуск генерации контента...')
        self.stdout.write('   (Логи будут выводиться ниже)')
        self.stdout.write('')
        
        try:
            result = generator.generate(variables=variables)
            
            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS('=' * 70))
            
            if result.success:
                self.stdout.write(self.style.SUCCESS('  ✅ ГЕНЕРАЦИЯ УСПЕШНА'))
                self.stdout.write(self.style.SUCCESS('=' * 70))
                self.stdout.write('')
                
                self.stdout.write(f'📄 Заголовок:')
                self.stdout.write(f'   {result.title}')
                self.stdout.write('')
                
                if result.content:
                    content_preview = result.content[:200] + '...' if len(result.content) > 200 else result.content
                    self.stdout.write(f'📝 Контент (превью):')
                    self.stdout.write(f'   {content_preview}')
                    self.stdout.write('')
                
                # Показываем информацию о спарсенных источниках
                if result.session_data and result.session_data.get('source_info'):
                    self.stdout.write(f'📥 Спарсенные источники:')
                    source_info = result.session_data.get('source_info', '')
                    self.stdout.write(f'   {source_info}')
                    self.stdout.write('')
                
                # Показываем промпт, который использовался
                if result.session_data and result.session_data.get('prompt'):
                    prompt_preview = result.session_data.get('prompt', '')[:300] + '...' if len(result.session_data.get('prompt', '')) > 300 else result.session_data.get('prompt', '')
                    self.stdout.write(f'💬 Промпт для генерации (превью):')
                    self.stdout.write(f'   {prompt_preview}')
                    self.stdout.write('')
                
                if result.image_path:
                    self.stdout.write(self.style.SUCCESS(f'🖼️ Изображение: {result.image_path}'))
                else:
                    self.stdout.write('   Изображение не сгенерировано')
                self.stdout.write('')
                
                if result.session_data:
                    word_count = len(result.session_data.get('plain_text', '').split()) if result.session_data.get('plain_text') else 0
                    self.stdout.write(f'📊 Статистика:')
                    self.stdout.write(f'   Слов: {word_count}')
                    if result.session_data.get('tags'):
                        self.stdout.write(f'   Теги: {", ".join(result.session_data.get("tags", []))}')
                    self.stdout.write('')
                    
                    # Показываем информацию о спарсенных источниках
                    if result.session_data.get('source_info'):
                        self.stdout.write(f'📥 Спарсенные источники:')
                        source_info = result.session_data.get('source_info', '')
                        self.stdout.write(f'   {source_info}')
                        self.stdout.write('')
                    
                    # Показываем промпт, который использовался для генерации
                    if result.session_data.get('prompt'):
                        prompt_text = result.session_data.get('prompt', '')
                        if len(prompt_text) > 500:
                            prompt_preview = prompt_text[:500] + '...'
                        else:
                            prompt_preview = prompt_text
                        self.stdout.write(f'💬 Промпт для генерации (превью):')
                        self.stdout.write(f'   {prompt_preview}')
                        self.stdout.write('')
                    
                    # Показываем спарсенный контент (если был парсинг)
                    if result.session_data.get('parsed_content'):
                        parsed = result.session_data.get('parsed_content', {})
                        self.stdout.write(f'📋 Спарсенный контент:')
                        if parsed.get('url'):
                            self.stdout.write(f'   URL: {parsed.get("url")}')
                        if parsed.get('title'):
                            self.stdout.write(f'   Заголовок: {parsed.get("title")}')
                        if parsed.get('text'):
                            text_preview = parsed.get('text', '')[:300] + '...' if len(parsed.get('text', '')) > 300 else parsed.get('text', '')
                            self.stdout.write(f'   Текст (превью): {text_preview}')
                        self.stdout.write('')
                
                if result.metrics:
                    self.stdout.write('📈 Метрики:')
                    for key, value in result.metrics.items():
                        self.stdout.write(f'   {key}: {value}')
                    self.stdout.write('')
                
            else:
                self.stdout.write(self.style.ERROR('  ❌ ГЕНЕРАЦИЯ НЕУДАЧНА'))
                self.stdout.write(self.style.ERROR('=' * 70))
                self.stdout.write('')
                self.stdout.write(self.style.ERROR(f'Ошибка: {result.error}'))
                self.stdout.write('')
                
        except Exception as e:
            self.stdout.write('')
            self.stdout.write(self.style.ERROR('=' * 70))
            self.stdout.write(self.style.ERROR('  ❌ ОШИБКА ПРИ ГЕНЕРАЦИИ'))
            self.stdout.write(self.style.ERROR('=' * 70))
            self.stdout.write('')
            self.stdout.write(self.style.ERROR(f'Ошибка: {str(e)}'))
            logger.exception("Ошибка при генерации")
            self.stdout.write('')
            self.stdout.write('   Проверьте логи выше для подробностей')
        
        self.stdout.write('')
        self.stdout.write('=' * 70)

