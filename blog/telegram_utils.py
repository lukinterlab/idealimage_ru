import os
import logging
import re

from django.conf import settings
from django.utils.html import strip_tags

from Asistent.services.telegram_client import get_telegram_client

logger = logging.getLogger(__name__)

def send_telegram_message(post):
    """
    Отправляет сообщение в Telegram-каналы с изображением и отформатированным сообщением
    
    Логика:
    1. Отправляет в основной канал @ideal_image_ru (CHAT_ID3)
    2. Если у категории статьи есть chat_id - дублирует туда же
    """
    if not settings.BOT_TOKEN or not settings.CHAT_ID3:
        logger.error("Настройки Telegram не настроены")
        return False
    
    # Формируем список каналов для отправки
    channels = [settings.CHAT_ID3]  # Основной канал @ideal_image_ru
    
    # Добавляем канал категории если есть
    if post.category and post.category.chat_id:
        if post.category.chat_id not in channels:
            channels.append(post.category.chat_id)
            logger.info(f"📢 Дополнительный канал категории: {post.category.chat_id}")
    
    logger.info(f"📤 Отправка в {len(channels)} канал(ов): {', '.join(channels)}")
    
    # Получаем полный URL сайта
    site_url = settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'https://idealimage.ru/'
    
    # Формируем текст сообщения для Telegram
    message = ""
    
    # 1. ЗАГОЛОВОК
    message += f"*{post.title}*\n\n"
    
    # 2. 100 ПЕРВЫХ СЛОВ ТЕКСТА (без HTML-тегов)
    clean_content = strip_tags(post.content)
    words = clean_content.split()[:100]
    preview = ' '.join(words)
    if len(words) == 100:
        preview += '...'
    message += f"{preview}\n\n"
    
    # 3. ДВА ПЕРВЫХ ВОПРОСА ИЗ FAQ (если есть)
    faq_match = re.search(r'<div class="faq-section[^>]*>(.*?)</div>', post.content, re.DOTALL | re.IGNORECASE)
    if faq_match:
        faq_html = faq_match.group(1)
        # Ищем вопросы в FAQ
        questions = re.findall(r'<div class="faq-question[^>]*>(.*?)</div>', faq_html, re.DOTALL | re.IGNORECASE)
        if questions and len(questions) >= 2:
            q1 = strip_tags(questions[0]).strip()
            q2 = strip_tags(questions[1]).strip()
            message += f"❓ *Часто задаваемые вопросы:*\n"
            message += f"• {q1}\n"
            message += f"• {q2}\n\n"
    
    # 4. ТЕГИ
    if post.tags.exists():
        tags_list = [f"#{tag.name.replace(' ', '_')}" for tag in post.tags.all()]
        message += ' '.join(tags_list) + '\n\n'
    
    # 5. ССЫЛКА НА ПОЛНЫЙ ТЕКСТ
    message += f"📖 *ЧИТАТЬ ПОЛНЫЙ ТЕКСТ >>*\n{site_url}{post.get_absolute_url()}"
    
    logger.info(f"Попытка отправить сообщение '{post.title}' в Telegram")
    
    client = get_telegram_client()
    success_count = 0
    
    # Отправляем в каждый канал из списка
    for channel_id in channels:
        logger.info(f"  → Отправка в канал: {channel_id}")
        
        # Сначала попробуйте отправить медиа (фото/видео) с подписью
        if post.kartinka:
            # Получаем правильный путь к файлу через Django storage
            from django.core.files.storage import default_storage
            
            # Пробуем разные способы получения пути
            file_path = None
            if hasattr(post.kartinka, 'path'):
                file_path = post.kartinka.path
            elif hasattr(post.kartinka, 'name'):
                # Используем Django storage для получения полного пути
                if default_storage.exists(post.kartinka.name):
                    file_path = default_storage.path(post.kartinka.name)
                else:
                    # Если файл не найден через storage, пробуем через MEDIA_ROOT
                    file_path = os.path.join(settings.MEDIA_ROOT, post.kartinka.name)
            
            if not file_path or not os.path.exists(file_path):
                logger.error(f"  ❌ Файл медиа не найден: {post.kartinka.name if hasattr(post.kartinka, 'name') else post.kartinka}")
                file_path = None

            try:
                if file_path:
                    _, ext = os.path.splitext(post.kartinka.name or "")
                    ext = ext.lower()
                    is_video = ext in {".mp4", ".webm", ".mov", ".m4v"}

                    # Проверяем размер файла перед отправкой
                    file_size = os.path.getsize(file_path)
                    file_size_mb = file_size / (1024 * 1024)
                    
                    # Telegram ограничения:
                    # - Фото: до 10 МБ
                    # - Видео: до 50 МБ (но лучше до 20 МБ для надежности)
                    if is_video:
                        if file_size_mb > 50:
                            logger.warning(f"  ⚠️ Видео слишком большое ({file_size_mb:.2f} МБ > 50 МБ), отправляем только текст")
                            raise ValueError(f"Video file too large: {file_size_mb:.2f} MB")
                        elif file_size_mb > 20:
                            logger.warning(f"  ⚠️ Видео большое ({file_size_mb:.2f} МБ), может быть проблема с отправкой")
                    else:
                        if file_size_mb > 10:
                            logger.warning(f"  ⚠️ Изображение слишком большое ({file_size_mb:.2f} МБ > 10 МБ), отправляем только текст")
                            raise ValueError(f"Photo file too large: {file_size_mb:.2f} MB")

                    if is_video:
                        logger.info(f"  🎥 Попытка отправить видео ({file_size_mb:.2f} МБ) в {channel_id}")
                        sent = client.send_video(
                            channel_id,
                            file_path,
                            caption=message,
                            parse_mode="Markdown",
                        )
                    else:
                        logger.info(f"  📷 Попытка отправить изображение ({file_size_mb:.2f} МБ) в {channel_id}")
                        sent = client.send_photo(
                            channel_id,
                            file_path,
                            caption=message,
                            parse_mode="Markdown",
                        )

                    if sent:
                        logger.info(f"  ✅ Отправлено с медиа ({'видео' if is_video else 'изображение'}) в {channel_id}")
                        success_count += 1
                        continue
                    else:
                        logger.warning(f"  ⚠️ Не удалось отправить медиа в {channel_id}, пробуем отправить только текст")

            except Exception as e:
                logger.error(f"  ❌ Ошибка отправки медиа в {channel_id}: {str(e)}")
                logger.info(f"  🔄 Пробуем отправить только текст (без медиа)")

            # В случае любой ошибки пробуем отправить только текст
            try:
                # Добавляем информацию о медиа в текст, если оно не отправилось
                fallback_message = message
                if post.kartinka:
                    _, ext = os.path.splitext(post.kartinka.name or "")
                    ext = ext.lower()
                    is_video = ext in {".mp4", ".webm", ".mov", ".m4v"}
                    media_type = "видео" if is_video else "изображение"
                    # Добавляем ссылку на медиа в сообщение
                    try:
                        media_url = f"{site_url}{post.kartinka.url}" if hasattr(post.kartinka, 'url') else ""
                        if media_url:
                            fallback_message = f"🎬 *{media_type.upper()} доступно по ссылке:*\n{media_url}\n\n{message}"
                        else:
                            fallback_message = f"🎬 *{media_type.upper()} не удалось загрузить*\n\n{message}"
                    except Exception:
                        fallback_message = f"🎬 *{media_type.upper()} не удалось загрузить*\n\n{message}"
                
                if client.send_message(channel_id, fallback_message, parse_mode="Markdown"):
                    logger.info(f"  ✅ Отправлено только текст (fallback) в {channel_id}")
                    success_count += 1
            except Exception as e2:
                logger.error(f"  ❌ Ошибка отправки текста в {channel_id}: {str(e2)}")
        else:
            # Если изображения нет, просто отправьте сообщение
            try:
                if client.send_message(channel_id, message, parse_mode="Markdown"):
                    logger.info(f"  ✅ Отправлено только текст в {channel_id}")
                    success_count += 1
            except Exception as e:
                logger.error(f"  ❌ Ошибка отправки в {channel_id}: {str(e)}")
    
    # Обновляем telegram_posted_at при успешной отправке
    if success_count > 0:
        from django.utils import timezone
        from django.db import transaction
        
        with transaction.atomic():
            post.telegram_posted_at = timezone.now()
            post.fixed = True
            post.save(update_fields=['telegram_posted_at', 'fixed'])
        
        logger.info(f"✅ Статья отправлена в {success_count} из {len(channels)} каналов")
        logger.info(f"✅ Обновлено telegram_posted_at для статьи: {post.title}")
        return True
    else:
        logger.error(f"❌ Не удалось отправить ни в один канал")
        # НЕ обновляем telegram_posted_at при ошибке - оставляем как есть чтобы не было повторных попыток
        return False
