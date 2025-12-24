# Sozseti - Шпаргалка команд

## Быстрые команды

### Настройка (первый запуск)

```bash
# ВСЁ СРАЗУ (рекомендуется)
python manage.py setup_sozseti --with-demo

# ИЛИ ПО ШАГАМ:
python manage.py migrate
python manage.py init_social_platforms
python manage.py sync_telegram_channels
python manage.py create_demo_schedules
python manage.py populate_ai_knowledge
```

### Публикация

```bash
# Опубликовать статью с ID=1 в Telegram
python manage.py test_social_publish 1

# В несколько платформ
python manage.py test_social_publish 5 --platforms telegram vk rutube

# Все платформы
python manage.py test_social_publish 10 --platforms telegram vk pinterest rutube dzen
```

### Синхронизация

```bash
# Telegram каналы
python manage.py sync_telegram_channels

# Все платформы
python manage.py init_social_platforms
```

### Проверка

```bash
# Проверка системы
python manage.py check

# Проверка для продакшена
python manage.py check --deploy

# Django-Q статус
# Откройте: /admin/django_q/
```

## URL адреса

### Админка

```
/admin/Sozseti/socialplatform/      # Платформы
/admin/Sozseti/socialchannel/       # Каналы
/admin/Sozseti/postpublication/     # Публикации
/admin/Sozseti/publicationschedule/ # Расписания
/admin/Sozseti/channelanalytics/    # Аналитика
/admin/Sozseti/adcampaign/          # Реклама
```

### Дашборд

```
/sozseti/dashboard/          # Главная
/sozseti/channel/<id>/       # Детали канала
/sozseti/calendar/           # Календарь
```

## Python API

### Публикация в Telegram

```python
from Sozseti.api_integrations.telegram_manager import TelegramChannelManager
from blog.models import Post

telegram = TelegramChannelManager()
post = Post.objects.get(id=1)

# В один канал
telegram.publish_to_channel('@ideal_image_ru', post)

# Умный выбор
channels = telegram.select_channels_by_category(post)
telegram.publish_to_multiple_channels(post, channels=channels)
```

### AI Agent

```python
from Sozseti.ai_agent.social_agent import SocialMediaAgent

agent = SocialMediaAgent()

# Распределение
distribution = agent.distribute_post(post, strategy='auto')

# Оптимизация
optimal_time = agent.optimize_posting_time(channel, post)

# Анализ
suggestions = agent.suggest_improvements(channel)

# Реклама
campaign = agent.plan_ad_campaign(budget=10000, goal='subscribers')
```

## Template Tags

```django
{% load social_tags %}

<!-- Кнопки "Поделиться" -->
{% social_share_buttons post %}

<!-- WhatsApp -->
{% whatsapp_share_link post as wa_link %}

<!-- Каналы -->
{% get_telegram_channels as channels %}

<!-- Ссылки -->
{% get_main_social_links as links %}
```

## Django-Q задачи

```python
# Программно запустить
from django_q.tasks import async_task

# Публикация
async_task('Sozseti.tasks.publish_post_to_social', post_id)

# Статистика
async_task('Sozseti.tasks.update_channels_statistics')

# Аналитика
async_task('Sozseti.tasks.collect_social_analytics')
```

## Переменные окружения (.env)

```env
# Telegram (уже настроен)
BOT_TOKEN=...

# VK
VK_API_TOKEN=...
VK_GROUP_ID=...

# Pinterest
PINTEREST_ACCESS_TOKEN=...

# Rutube
RUTUBE_API_KEY=...

# Dzen
DZEN_TOKEN=...
```

## Troubleshooting

### Не работает автопубликация

```bash
# Проверьте Django-Q
python manage.py qcluster

# Проверьте задачи
# /admin/django_q/task/

# Проверьте логи
tail -f logs/django.log
```

### Telegram не публикует

```bash
# Проверьте бота
python manage.py sync_telegram_channels

# Проверьте токен
echo $BOT_TOKEN

# Проверьте что бот админ в каналах
```

### VK ошибка

```bash
# Получите новый токен
# https://vkhost.github.io/

# Проверьте права: wall, photos, groups
```

## Быстрые ссылки

- Документация: `Sozseti/README.md`
- Быстрый старт: `Sozseti/QUICKSTART.md`
- Инструкция: `ИНСТРУКЦИИ/ИНСТРУКЦИЯ_СОЦСЕТИ.md`
- Отчёт: `ИНСТРУКЦИИ/ОТЧЁТ_ИНТЕГРАЦИЯ_СОЦСЕТЕЙ.md`

## Получение токенов

- **Telegram:** @BotFather
- **VK:** https://vkhost.github.io/
- **Pinterest:** https://developers.pinterest.com/
- **Rutube:** https://rutube.ru/info/api/
- **Dzen:** https://yandex.ru/dev/zen/

