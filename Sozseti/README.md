# Sozseti - Интеграция социальных сетей

Приложение для автоматической публикации статей во все социальные сети с AI-управлением.

## Возможности

### Поддерживаемые платформы

✅ **Активные (готовы к использованию):**
- **Telegram** - 18 каналов с умным распределением
- **WhatsApp** - кнопка "Поделиться"

⚙️ **Требуют настройки API:**
- **VK** - группы и сообщества
- **Pinterest** - пины и доски
- **Rutube** - видеоплатформа
- **Яндекс.Дзен** - публикация статей

🔜 **В разработке:**
- **MAX** - ожидание открытия API
- **Instagram** - требует VPN
- **Facebook** - требует VPN
- **YouTube** - требует VPN

## Быстрый старт

### 1. Инициализация платформ

```bash
python manage.py init_social_platforms
```

Эта команда:
- Создаёт все 10 платформ в БД
- Синхронизирует 18 Telegram каналов
- Проверяет настройку VK, Rutube, Dzen

### 2. Настройка API токенов

Добавьте в `.env` файл:

```env
# VK API
VK_API_TOKEN=your_vk_token
VK_GROUP_ID=your_group_id

# Pinterest API
PINTEREST_ACCESS_TOKEN=your_token
PINTEREST_BOARD_ID=your_board_id

# Rutube API
RUTUBE_API_KEY=your_api_key
RUTUBE_CHANNEL_ID=your_channel_id

# Яндекс.Дзен
DZEN_TOKEN=your_token
DZEN_CHANNEL_ID=your_channel_id
```

### 3. Синхронизация каналов

```bash
# Telegram каналы
python manage.py sync_telegram_channels

# Проверка всех платформ
python manage.py init_social_platforms
```

### 4. Тестовая публикация

```bash
# Опубликовать статью с ID=1 в Telegram
python manage.py test_social_publish 1 --platforms telegram

# Опубликовать в несколько платформ
python manage.py test_social_publish 1 --platforms telegram vk rutube
```

## Использование

### Автоматическая публикация

При создании статьи через админку:

1. Убедитесь что статус = "Опубликовано"
2. Чекбокс "Автопубликация в соцсетях" = включен
3. Статья автоматически опубликуется в соцсети через Django-Q

### Ручная публикация через админку

1. Откройте админку: `/admin/Sozseti/`
2. Зайдите в раздел "Публикации"
3. Создайте новую публикацию вручную

### Расписания автопостинга

1. Откройте `/admin/Sozseti/publicationschedule/`
2. Создайте новое расписание
3. Выберите каналы и категории
4. Настройте частоту (ежедневно/3 раза в день/еженедельно)
5. Активируйте расписание

Django-Q автоматически будет публиковать статьи по расписанию.

### AI-управление

AI-агент может:
- Умно распределять статьи по каналам на основе категории
- Оптимизировать время публикации
- Адаптировать контент под каждую платформу
- Анализировать метрики и давать рекомендации
- Планировать рекламные кампании

## Template Tags

### В шаблонах

```django
{% load social_tags %}

<!-- Кнопки "Поделиться" -->
{% social_share_buttons post %}

<!-- Ссылка WhatsApp -->
{% whatsapp_share_link post %}

<!-- Список всех каналов -->
{% get_telegram_channels as channels %}

<!-- Основные соцсети для футера -->
{% get_main_social_links as social_links %}
{{ social_links.telegram }}
{{ social_links.vk }}
{{ social_links.pinterest }}
```

## API Интеграции

### Telegram (18 каналов)

```python
from Sozseti.api_integrations.telegram_manager import TelegramChannelManager

telegram = TelegramChannelManager()

# Публикация в один канал
telegram.publish_to_channel('@ideal_image_ru', post, image_url)

# Публикация во все каналы
telegram.publish_to_multiple_channels(post, image_url=image_url)

# Умный выбор каналов
channels = telegram.select_channels_by_category(post)
telegram.publish_to_multiple_channels(post, channels=channels)

# Обновление статистики
telegram.update_all_channels_statistics()
```

### VK

```python
from Sozseti.api_integrations.vk_manager import VKManager

vk = VKManager()
result = vk.publish_to_wall(post, image_url)
```

### Rutube

```python
from Sozseti.api_integrations.rutube_manager import RutubeManager

rutube = RutubeManager()
result = rutube.publish_announcement(post, image_url)
```

### Dzen

```python
from Sozseti.api_integrations.dzen_manager import DzenManager

dzen = DzenManager()
result = dzen.publish_article(post, image_url)
```

### WhatsApp Share

```python
from Sozseti.api_integrations.whatsapp_share import WhatsAppShare

# Генерация ссылки
link = WhatsAppShare.generate_share_link(post)

# HTML кнопка
button = WhatsAppShare.get_share_button_html(post, 'btn btn-success')
```

## AI Agent

```python
from Sozseti.ai_agent.social_agent import SocialMediaAgent

agent = SocialMediaAgent()

# Умное распределение
channels = agent.distribute_post(post, strategy='auto')

# Оптимизация времени
optimal_time = agent.optimize_posting_time(channel, post)

# Адаптация контента
content = agent.generate_post_content(post, 'telegram')

# Анализ канала
suggestions = agent.suggest_improvements(channel)

# Планирование рекламы
campaign = agent.plan_ad_campaign(budget=10000, goal='subscribers')
```

## Модели

### SocialPlatform
Платформы: Telegram, VK, Pinterest, Rutube, Dzen, WhatsApp, MAX, Instagram, Facebook, YouTube

### SocialChannel
Каналы и группы в соцсетях. Например, 18 Telegram каналов.

### PostPublication
История всех публикаций с метриками (просмотры, лайки, комментарии, репосты).

### PublicationSchedule
Расписания автоматического постинга. Можно настроить:
- Частоту (hourly/daily/weekly)
- Категории статей
- Конкретные каналы
- Оптимальное время
- AI-оптимизацию

### ChannelAnalytics
Суточная аналитика по каждому каналу.

### AdCampaign
Рекламные кампании с бюджетами и метриками.

## Django-Q задачи

Автоматические задачи (настраиваются в админке `/admin/django_q/schedule/`):

```python
# Публикация статьи
publish_post_to_social(post_id, platforms=['telegram', 'vk'])

# Синхронизация каналов
sync_telegram_channels()

# Обновление статистики (раз в час)
update_channels_statistics()

# Обработка расписаний (раз в 10 минут)
process_publication_schedules()

# Сбор аналитики (раз в день)
collect_social_analytics()
```

## Админ-панель

Разделы в админке:

- **📱 Платформы** - управление платформами
- **📢 Каналы** - все каналы с статистикой
- **📱 Telegram: Группы** - группировка 18 каналов
- **📅 Расписания** - автопостинг
- **📊 Публикации** - история с метриками
- **💬 Переписка** - входящие сообщения
- **💬 Комментарии** - комментарии из соцсетей
- **📈 Аналитика** - суточная статистика
- **💰 Рекламные кампании** - управление рекламой
- **🔄 Кросс-постинг** - правила репостов

## Получение токенов

### Telegram
1. Найдите @BotFather в Telegram
2. Создайте бота: `/newbot`
3. Получите токен: `BOT_TOKEN`
4. Добавьте бота админом во все 18 каналов

### VK
1. Создайте приложение: https://vk.com/apps?act=manage
2. Получите токен: https://vkhost.github.io/
3. Права: wall,photos,groups

### Pinterest
1. Создайте приложение: https://developers.pinterest.com/apps/
2. Получите токен через OAuth

### Rutube
1. Регистрация: https://rutube.ru/
2. API документация: https://rutube.ru/info/api/

### Яндекс.Дзен
1. Подключите канал: https://dzen.ru/
2. API: https://yandex.ru/dev/zen/

## Структура приложения

```
Sozseti/
├── models.py                    # Модели данных
├── admin.py                     # Админ-панель
├── tasks.py                     # Django-Q задачи
├── signals.py                   # Автопубликация
├── urls.py                      # URL маршруты
├── api_integrations/            # API интеграции
│   ├── telegram_manager.py      # 18 Telegram каналов
│   ├── vk_manager.py           # VK группы
│   ├── pinterest_manager.py    # Pinterest пины
│   ├── rutube_manager.py       # Rutube видео
│   ├── dzen_manager.py         # Яндекс.Дзен
│   ├── whatsapp_share.py       # WhatsApp кнопка
│   ├── max_manager.py          # MAX (заглушка)
│   └── future/                 # Instagram, Facebook, YouTube
├── ai_agent/
│   └── social_agent.py         # AI управление
├── analytics/
│   └── collector.py            # Сбор статистики
├── dashboard/                   # Дашборд (в разработке)
├── monetization/               # Реклама (в разработке)
└── templates/
    └── Sozseti/
        └── widgets/            # Виджеты для шаблонов
```

## Поддержка

Вопросы и предложения: admin@idealimage.ru

Документация API платформ:
- Telegram Bot API: https://core.telegram.org/bots/api
- VK API: https://dev.vk.com/ru/reference
- Pinterest API: https://developers.pinterest.com/docs/
- Rutube API: https://rutube.ru/info/api/
- Яндекс.Дзен API: https://yandex.ru/dev/zen/

