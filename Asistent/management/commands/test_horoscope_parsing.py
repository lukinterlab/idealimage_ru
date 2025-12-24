"""
Команда для тестирования парсинга гороскопов
Позволяет проверить парсинг с выбором даты и знака зодиака
"""
import logging
from django.core.management.base import BaseCommand
from Asistent.parsers.universal_parser import UniversalParser

logger = logging.getLogger(__name__)

# Знаки зодиака для horo.mail.ru
ZODIAC_SIGNS = {
    'овен': 'aries',
    'телец': 'taurus',
    'близнецы': 'gemini',
    'рак': 'cancer',
    'лев': 'leo',
    'дева': 'virgo',
    'весы': 'libra',
    'скорпион': 'scorpio',
    'стрелец': 'sagittarius',
    'козерог': 'capricorn',
    'водолей': 'aquarius',
    'рыбы': 'pisces',
}


class Command(BaseCommand):
    help = 'Тестирование парсинга гороскопов с выбором даты и знака зодиака'

    def add_arguments(self, parser):
        parser.add_argument(
            '--url',
            type=str,
            help='URL для парсинга (например: https://horo.mail.ru/)',
            default='https://horo.mail.ru/'
        )
        parser.add_argument(
            '--zodiac',
            type=str,
            help='Знак зодиака (овен, телец, близнецы, рак, лев, дева, весы, скорпион, стрелец, козерог, водолей, рыбы)',
            default=None
        )
        parser.add_argument(
            '--date',
            type=str,
            choices=['today', 'tomorrow'],
            help='Дата: today (сегодня) или tomorrow (завтра)',
            default='tomorrow'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Подробный вывод'
        )

    def handle(self, *args, **options):
        url = options['url']
        zodiac = options['zodiac']
        date = options['date']
        verbose = options['verbose']
        
        if verbose:
            logging.getLogger('Asistent.parsers').setLevel(logging.DEBUG)
        
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('  🔮 ТЕСТИРОВАНИЕ ПАРСИНГА ГОРОСКОПОВ'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write('')
        
        # Формируем URL с параметрами
        final_url = self._build_horoscope_url(url, zodiac, date)
        
        self.stdout.write(f'📋 Параметры:')
        self.stdout.write(f'   Исходный URL: {url}')
        if zodiac:
            self.stdout.write(f'   Знак зодиака: {zodiac}')
        self.stdout.write(f'   Дата: {date}')
        self.stdout.write(f'   Финальный URL: {final_url}')
        self.stdout.write('')
        
        # Парсим
        self.stdout.write('🔍 Запуск парсинга...')
        self.stdout.write('')
        
        try:
            parser = UniversalParser()
            result = parser.parse_article(final_url, download_images=False)
            
            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS('=' * 70))
            
            if result.get('success'):
                self.stdout.write(self.style.SUCCESS('  ✅ ПАРСИНГ УСПЕШЕН'))
                self.stdout.write(self.style.SUCCESS('=' * 70))
                self.stdout.write('')
                
                # Заголовок
                title = result.get('title', 'Не найден')
                self.stdout.write(f'📄 Заголовок:')
                self.stdout.write(f'   {title}')
                self.stdout.write('')
                
                # Текст (полный)
                text = result.get('text', '')
                if text:
                    self.stdout.write(f'📝 Текст (полный, {len(text)} символов):')
                    self.stdout.write('')
                    # Выводим текст с отступом, разбивая на строки для читаемости
                    for line in text.split('\n'):
                        if line.strip():
                            self.stdout.write(f'   {line.strip()}')
                    self.stdout.write('')
                else:
                    self.stdout.write(self.style.WARNING('   ⚠️ Текст не найден'))
                    self.stdout.write('')
                
                # Изображения
                images_count = len(result.get('images', []))
                self.stdout.write(f'🖼️ Изображений найдено: {images_count}')
                self.stdout.write('')
                
                # Видео
                videos_count = len(result.get('videos', []))
                if videos_count > 0:
                    self.stdout.write(f'🎥 Видео найдено: {videos_count}')
                    self.stdout.write('')
                
                # Метаданные
                if result.get('meta'):
                    meta = result.get('meta', {})
                    if meta.get('description'):
                        self.stdout.write(f'📋 Описание:')
                        self.stdout.write(f'   {meta.get("description")[:200]}...')
                        self.stdout.write('')
                
            else:
                self.stdout.write(self.style.ERROR('  ❌ ПАРСИНГ НЕУДАЧЕН'))
                self.stdout.write(self.style.ERROR('=' * 70))
                self.stdout.write('')
                error = result.get('error', 'Неизвестная ошибка')
                self.stdout.write(self.style.ERROR(f'Ошибка: {error}'))
                self.stdout.write('')
                
        except Exception as e:
            self.stdout.write('')
            self.stdout.write(self.style.ERROR('=' * 70))
            self.stdout.write(self.style.ERROR('  ❌ ОШИБКА ПРИ ПАРСИНГЕ'))
            self.stdout.write(self.style.ERROR('=' * 70))
            self.stdout.write('')
            self.stdout.write(self.style.ERROR(f'Ошибка: {str(e)}'))
            logger.exception("Ошибка при парсинге")
            self.stdout.write('')
        
        self.stdout.write('')
        self.stdout.write('=' * 70)
    
    def _build_horoscope_url(self, base_url: str, zodiac: str = None, date: str = 'tomorrow') -> str:
        """
        Формирует URL для парсинга гороскопа с учетом знака зодиака и даты.
        
        Для horo.mail.ru возможные варианты URL:
        1. https://horo.mail.ru/{zodiac_sign}/
        2. https://horo.mail.ru/{zodiac_sign}/tomorrow/
        3. https://horo.mail.ru/{zodiac_sign}/?date=tomorrow
        
        Args:
            base_url: Базовый URL
            zodiac: Знак зодиака (русское название)
            date: 'today' или 'tomorrow'
        
        Returns:
            Финальный URL для парсинга
        """
        url = base_url.rstrip('/')
        
        # Если указан знак зодиака, добавляем его в URL
        if zodiac:
            zodiac_lower = zodiac.lower().strip()
            zodiac_en = ZODIAC_SIGNS.get(zodiac_lower)
            
            if zodiac_en:
                # Правильный формат URL для horo.mail.ru: /prediction/{zodiac}/{date}/
                url = f"{url}/prediction/{zodiac_en}/"
                
                # Добавляем дату, если это не 'today'
                if date == 'tomorrow':
                    url = f"{url}tomorrow/"
                # Для 'today' дата не добавляется (по умолчанию показывается сегодня)
                
                self.stdout.write(self.style.SUCCESS(f'   ✅ Знак зодиака распознан: {zodiac} → {zodiac_en}'))
                self.stdout.write(f'   ✅ Дата: {date}')
            else:
                self.stdout.write(self.style.WARNING(f'   ⚠️ Неизвестный знак зодиака: {zodiac}'))
                self.stdout.write(f'   Доступные: {", ".join(ZODIAC_SIGNS.keys())}')
        
        return url

