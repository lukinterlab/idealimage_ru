"""
Запуск автопостинга всех 12 гороскопов прямо сейчас
"""
import os
import sys
import django

# Настройка Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'IdealImage_PDJ.settings.production')
django.setup()

import logging
from Asistent.schedule.tasks import run_specific_schedule
from Asistent.schedule.models import AISchedule

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Запуск автопостинга гороскопов"""
    logger.info("=" * 60)
    logger.info("🚀 ЗАПУСК АВТОПОСТИНГА ВСЕХ 12 ГОРОСКОПОВ")
    logger.info("=" * 60)
    
    try:
        # Ищем расписание гороскопов (ID=1 или по названию)
        schedule = None
        
        # Пробуем по ID=1
        try:
            schedule = AISchedule.objects.get(id=1)
            logger.info(f"✅ Найдено расписание по ID=1: {schedule.name}")
        except AISchedule.DoesNotExist:
            logger.warning("⚠️ Расписание с ID=1 не найдено, ищем по названию...")
            
            # Ищем по названию
            schedule = AISchedule.objects.filter(
                name__icontains='гороскоп',
                strategy='horoscope'
            ).first()
            
            if schedule:
                logger.info(f"✅ Найдено расписание по названию: {schedule.name} (ID={schedule.id})")
            else:
                logger.error("❌ Расписание гороскопов не найдено!")
                return
        
        # Проверяем активность
        if not schedule.is_active:
            logger.warning(f"⚠️ Расписание неактивно, активируем...")
            schedule.is_active = True
            schedule.save(update_fields=['is_active'])
            logger.info("✅ Расписание активировано")
        
        # Показываем параметры
        logger.info(f"\n📋 Параметры расписания:")
        logger.info(f"   ID: {schedule.id}")
        logger.info(f"   Название: {schedule.name}")
        logger.info(f"   Статей за запуск: {schedule.articles_per_run}")
        logger.info(f"   Активно: {schedule.is_active}")
        
        payload = schedule.payload_template or {}
        logger.info(f"   Задержка между гороскопами: {payload.get('generation_delay', 20)}с")
        logger.info(f"   Retry delay: {payload.get('retry_delay', 60)}с")
        logger.info(f"   Проверка cooldown: {payload.get('check_cooldown', True)}")
        
        # Запускаем
        logger.info(f"\n🚀 Запуск генерации всех 12 гороскопов...")
        logger.info(f"   Это может занять несколько минут (12 × ~20с = ~4 минуты минимум)...\n")
        
        result = run_specific_schedule(schedule.id)
        
        # Результаты
        logger.info("\n" + "=" * 60)
        logger.info("📊 РЕЗУЛЬТАТЫ ВЫПОЛНЕНИЯ")
        logger.info("=" * 60)
        logger.info(f"   Успешно: {result.get('success', False)}")
        logger.info(f"   Создано постов: {len(result.get('created_posts', []))}")
        
        if result.get('created_posts'):
            logger.info(f"\n   ✅ Созданные гороскопы:")
            for post in result.get('created_posts', [])[:12]:
                logger.info(f"      - {post.title}")
        
        if result.get('errors'):
            logger.warning(f"\n   ⚠️ Ошибки ({len(result.get('errors', []))}):")
            for error in result.get('errors', [])[:5]:
                logger.warning(f"      - {error}")
        
        if result.get('success'):
            logger.info("\n✅ Автопостинг гороскопов завершен успешно!")
        else:
            logger.error(f"\n❌ Автопостинг завершился с ошибками: {result.get('error', 'Неизвестная ошибка')}")
        
    except Exception as e:
        logger.error(f"\n❌ КРИТИЧЕСКАЯ ОШИБКА: {e}", exc_info=True)

if __name__ == '__main__':
    main()

