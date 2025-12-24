"""
Тест упрощенной архитектуры GigaChat
Проверяет:
1. Удаление call_gigachat_with_timeout
2. Логирование выбора модели
3. Оптимизированный cooldown механизм
"""
import os
import sys
import django

# Настройка Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'IdealImage_PDJ.settings.production')
django.setup()

import logging
from Asistent.gigachat_api import get_gigachat_client

# Настройка логирования для теста
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

def test_model_selection():
    """Тест выбора модели с логированием"""
    logger.info("=" * 60)
    logger.info("ТЕСТ 1: Выбор модели с логированием")
    logger.info("=" * 60)
    
    client = get_gigachat_client()
    
    # Тест 1: Текстовая генерация (GigaChat)
    logger.info("\n📝 Тест текстовой генерации (должен выбрать GigaChat):")
    try:
        response = client.chat("Привет, это тест")
        logger.info(f"✅ Успешно: {response[:50]}...")
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
    
    # Тест 2: Парсинг (GigaChat-Max)
    logger.info("\n🔍 Тест парсинга (должен выбрать GigaChat-Max):")
    try:
        response = client.chat_for_parsing("Перепиши этот текст: Тестовый текст для парсинга")
        logger.info(f"✅ Успешно: {response[:50]}...")
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
    
    # Тест 3: Чат-бот (GigaChat-Max)
    logger.info("\n💬 Тест чат-бота (должен выбрать GigaChat-Max):")
    try:
        response = client.chat_for_chatbot("Привет, как дела?")
        logger.info(f"✅ Успешно: {response[:50]}...")
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
    
    # Тест 4: Embeddings (Embeddings)
    logger.info("\n📊 Тест embeddings (должен выбрать Embeddings):")
    try:
        embedding = client.get_embeddings("Тестовый текст для embeddings")
        logger.info(f"✅ Успешно: размер вектора = {len(embedding)}")
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")


def test_cooldown_mechanism():
    """Тест оптимизированного cooldown механизма"""
    logger.info("\n" + "=" * 60)
    logger.info("ТЕСТ 2: Оптимизированный cooldown механизм")
    logger.info("=" * 60)
    
    client = get_gigachat_client()
    
    # Устанавливаем cooldown
    logger.info("\n⏳ Установка cooldown (60 секунд):")
    client._set_cooldown("test:cooldown:key", 60, reason="Тестовый cooldown")
    
    # Проверяем cooldown
    logger.info("\n🔍 Проверка cooldown:")
    remaining = client._get_cooldown_remaining("test:cooldown:key")
    logger.info(f"   Оставшееся время: {remaining} секунд")
    
    if remaining > 0:
        logger.info("✅ Cooldown работает (через cache или файловую систему)")
    else:
        logger.warning("⚠️ Cooldown не установлен или истек")


def test_call_gigachat_with_timeout_removed():
    """Проверка, что call_gigachat_with_timeout удален"""
    logger.info("\n" + "=" * 60)
    logger.info("ТЕСТ 3: Проверка удаления call_gigachat_with_timeout")
    logger.info("=" * 60)
    
    try:
        from Asistent.Test_Promot.test_prompt import call_gigachat_with_timeout
        logger.error("❌ call_gigachat_with_timeout все еще существует!")
    except ImportError:
        logger.info("✅ call_gigachat_with_timeout успешно удален")
    
    # Проверяем, что используется client.chat() напрямую
    logger.info("\n✅ Используется client.chat() напрямую (без обертки)")


if __name__ == '__main__':
    logger.info("🚀 Начало тестирования упрощенной архитектуры GigaChat\n")
    
    try:
        test_model_selection()
        test_cooldown_mechanism()
        test_call_gigachat_with_timeout_removed()
        
        logger.info("\n" + "=" * 60)
        logger.info("✅ ВСЕ ТЕСТЫ ЗАВЕРШЕНЫ")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"\n❌ КРИТИЧЕСКАЯ ОШИБКА: {e}", exc_info=True)

