# ChatBot_AI - Автономный модуль чат-бота

Переносимый Django-модуль для интеграции AI чат-бота на сайте.

## Возможности

- ✅ Поиск ответов в FAQ
- ✅ Интеллектуальный поиск по статьям блога
- ✅ Интеграция с AI (GigaChat, OpenAI, Claude и др.)
- ✅ Rate limiting (защита от спама)
- ✅ Автогенерация embeddings для FAQ
- ✅ Форма связи с администратором
- ✅ История сообщений
- ✅ Админ-панель

## Архитектура

Модуль использует паттерн интерфейсов для внешних зависимостей:

- **AIInterface** - абстракция для AI провайдеров
- **SearchInterface** - абстракция для поиска контента

Это позволяет легко переносить модуль между проектами и менять реализации.

## Установка на новый проект

### 1. Скопировать папку
```bash
cp -r Asistent/ChatBot_AI/ your_project/
```

### 2. Добавить в INSTALLED_APPS
```python
# settings.py
INSTALLED_APPS = [
    ...
    'your_app.ChatBot_AI',  # Добавить
    ...
]
```

### 3. Реализовать интерфейсы
Отредактируйте `ChatBot_AI/config.py`:

```python
from .interfaces.ai_interface import YourAIProvider
from .interfaces.search_interface import YourSearchProvider

AI_PROVIDER = YourAIProvider
SEARCH_PROVIDER = YourSearchProvider
```

Создайте свои провайдеры:

```python
# interfaces/ai_interface.py
class YourAIProvider(BaseAIProvider):
    def get_response(self, prompt: str, system_prompt: str = None) -> Dict:
        # Ваша реализация
        pass
```

### 4. Применить миграции
```bash
python manage.py migrate ChatBot_AI
```

### 5. Подключить URLs
```python
# urls.py
urlpatterns = [
    ...
    path('', include('your_app.ChatBot_AI.urls')),
]
```

### 6. Включить виджет в шаблон
```django
<!-- base.html -->
{% include 'chatbot/widget.html' %}
```

## Конфигурация

Настройки чат-бота управляются через админ-панель:

`/admin/ChatBot_AI/chatbotsettings/`

Основные параметры:
- **system_prompt** - инструкция для AI
- **use_ai** - использовать AI для ответов
- **search_articles** - искать по статьям
- **admin_contact_enabled** - форма связи с админом
- **rate_limit_messages** - лимит сообщений в час

## База знаний (FAQ)

Добавляйте FAQ через админку:

`/admin/ChatBot_AI/chatbotfaq/`

Каждый FAQ содержит:
- **question** - вопрос
- **answer** - ответ (поддерживает HTML)
- **keywords** - массив ключевых слов для поиска
- **priority** - приоритет (0-100)
- **embedding** - векторное представление (автогенерируется)

## API Endpoints

- `POST /api/chatbot/message/` - отправка сообщения
- `POST /api/chatbot/contact-admin/` - связь с админом
- `GET /api/chatbot/settings/` - получение настроек

## Зависимости

**Обязательные:**
- Django 4.2+
- Python 3.10+

**Опциональные:**
- GigaChat API - для AI ответов (или другой AI провайдер)
- Blog app - для поиска по статьям

## Интеграция с текущим проектом (IdealImage.ru)

Для IdealImage.ru используются:
- **GigaChatProvider** - для AI ответов
- **BlogSearchProvider** - для поиска по статьям блога

Эти провайдеры настроены в `config.py`.

## Семантический поиск

### FAQ - Гибридный поиск (реализовано)

✅ **Keyword поиск** - быстрый поиск по ключевым словам
✅ **Semantic поиск** - умный поиск через embeddings (косинусное сходство)

Работает автоматически:
1. Сначала keyword поиск (быстро)
2. Если не найдено → semantic поиск (умно)

Embeddings генерируются автоматически при создании/обновлении FAQ.

**Минимальный порог сходства:** 65% (можно настроить в `semantic_search.py`)

### Статьи - Keyword поиск с приоритетами (реализовано)

✅ Умный поиск с весами:
- Категория: +50 баллов
- Теги: +30 баллов
- Заголовок: +20 баллов
- Описание: +10 баллов
- Контент: +1 балл

### Будущие улучшения (опционально)

#### Semantic поиск статей

Для включения семантического поиска статей нужно:

1. Добавить поле в `blog.models.Post`:
```python
class Post(models.Model):
    # ... существующие поля
    embedding = models.JSONField(
        null=True,
        blank=True,
        verbose_name='Векторное представление'
    )
```

2. Создать signal для автогенерации:
```python
@receiver(post_save, sender=Post)
def generate_post_embedding(sender, instance, **kwargs):
    from Asistent.gigachat_api import get_embeddings
    text = f"{instance.title}\n{instance.description}\n{instance.content[:500]}"
    instance.embedding = get_embeddings(text)
    instance.save()
```

3. Обновить `BlogSearchProvider` для использования semantic search

## Расширение

### Добавить новый AI провайдер

```python
# interfaces/ai_interface.py
class OpenAIProvider(BaseAIProvider):
    def get_response(self, prompt: str, system_prompt: str = None) -> Dict:
        import openai
        # Реализация для OpenAI
        ...
```

### Добавить новый источник контента

```python
# interfaces/search_interface.py
class WikiSearchProvider(BaseSearchProvider):
    def search_articles(self, query: str, limit: int) -> List[Dict]:
        # Поиск в Wikipedia
        ...
```

## Поддержка

Модуль разработан для проекта IdealImage.ru

Контакт: admin@idealimage.ru

