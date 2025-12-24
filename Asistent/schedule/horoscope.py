"""
Генерация гороскопов через промпт-шаблон
Упрощенная версия - использует UniversalContentGenerator
"""
import logging
from typing import Dict, Any
from django.utils import timezone

from Asistent.generators.universal import UniversalContentGenerator, GeneratorConfig, GeneratorMode
from Asistent.schedule.models import AISchedule
from Asistent.constants import ZODIAC_SIGNS

logger = logging.getLogger(__name__)


def generate_horoscope_from_prompt_template(schedule_id: int) -> Dict[str, Any]:
    """
    Генерация всех 12 гороскопов для расписания.
    
    Args:
        schedule_id: ID расписания AISchedule
    
    Returns:
        dict: Результат генерации с ключами success, created_posts, errors
    """
    logger.info(f"🔮 [Гороскоп] Запуск генерации для расписания ID={schedule_id}")
    
    try:
        schedule = AISchedule.objects.select_related('prompt_template', 'category').get(id=schedule_id)
        
        if not schedule.prompt_template:
            return {
                'success': False,
                'error': 'no_prompt_template',
                'message': 'У расписания нет шаблона промпта'
            }
        
        logger.info(f"   📋 Расписание: {schedule.name}")
        logger.info(f"   📊 Статей за запуск: {schedule.articles_per_run}")
        logger.info(f"   🔮 Режим: генерация гороскопа из шаблона промпта")
        
        # Получаем параметры из payload_template
        payload = schedule.payload_template or {}
        generation_delay = payload.get('generation_delay', 20)
        retry_count = payload.get('retry_count', 2)
        retry_delay = payload.get('retry_delay', 60)
        skip_signs = payload.get('skip_signs', [])
        check_cooldown = payload.get('check_cooldown', True)
        
        logger.info(f"   ⚙️ Параметры: задержка={generation_delay}с, retry={retry_count} раз, retry_delay={retry_delay}с, проверка cooldown={check_cooldown}")
        
        if skip_signs:
            logger.info(f"   ⏭️ Пропуск знаков: {', '.join(skip_signs)}")
        
        # Фильтруем знаки
        signs_to_generate = [s for s in ZODIAC_SIGNS if s not in skip_signs]
        total_signs = len(signs_to_generate)
        
        logger.info(f"   📋 Первый проход: генерация всех {total_signs} гороскопов...")
        
        created_posts = []
        errors = []
        
        # Генерируем каждый гороскоп
        for idx, zodiac_sign in enumerate(signs_to_generate, 1):
            logger.info(f"   [{idx}/{total_signs}] Генерация гороскопа для {zodiac_sign}...")
            
            try:
                # Создаем конфигурацию генератора
                config = GeneratorConfig.for_auto()
                config.timeout = 300
                config.retry_count = retry_count
                
                # Создаем генератор
                generator = UniversalContentGenerator(
                    template=schedule.prompt_template,
                    config=config,
                    schedule_id=schedule.id
                )
                
                # Параметры для генерации
                schedule_payload = {
                    'target_date_offset': payload.get('target_date_offset', 1),
                    'title_template': payload.get('title_template'),
                    'base_tags': payload.get('base_tags', ['гороскоп', 'прогноз на завтра']),
                    'category': schedule.category.title if schedule.category else None,
                    'zodiac_sign': zodiac_sign
                }
                
                # Генерируем
                result = generator.generate(schedule_payload=schedule_payload)
                
                if result.success and result.post_id:
                    from blog.models import Post
                    post = Post.objects.get(id=result.post_id)
                    created_posts.append(post)
                    logger.info(f"   ✅ Гороскоп для {zodiac_sign} создан: {post.title}")
                else:
                    error_msg = result.error or 'Неизвестная ошибка'
                    errors.append(f"{zodiac_sign}: {error_msg}")
                    logger.error(f"   ❌ Ошибка генерации для {zodiac_sign}: {error_msg}")
                
                # Задержка между гороскопами (кроме последнего)
                if idx < total_signs:
                    import time
                    time.sleep(generation_delay)
            
            except Exception as e:
                error_msg = f"Ошибка генерации для {zodiac_sign}: {str(e)}"
                errors.append(error_msg)
                logger.error(f"   ❌ {error_msg}", exc_info=True)
        
        # Результат
        success = len(created_posts) > 0 and len(errors) == 0
        
        logger.info(f"   ✅ Генерация завершена: создано {len(created_posts)}/{total_signs}, ошибок: {len(errors)}")
        
        return {
            'success': success,
            'created_posts': created_posts,
            'created_count': len(created_posts),
            'errors': errors,
            'status': 'success' if success else 'partial' if created_posts else 'failed'
        }
    
    except AISchedule.DoesNotExist:
        logger.error(f"❌ Расписание ID={schedule_id} не найдено")
        return {
            'success': False,
            'error': 'schedule_not_found',
            'message': f'Расписание ID={schedule_id} не найдено'
        }
    except Exception as e:
        logger.error(f"❌ Критическая ошибка генерации гороскопов: {e}", exc_info=True)
        return {
            'success': False,
            'error': str(e),
            'message': f'Критическая ошибка: {str(e)}'
        }

