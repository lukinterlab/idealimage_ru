from django.conf import settings
from django.db import migrations


HOROSCOPE_TEXT_PROMPT = """Ты профессиональный астролог с 30-летним опытом и редактируешь глянцевый журнал в Москве.

На входе данные для прогноза:
- Сегодня: {current_date}
- Завтра: {next_date}, день недели: {weekday} ({weekend_status})
- Сезон: {season}
- Прогноз погоды в Москве: {weather}
- Солнце: {sun_sign} ({sun_degrees}°)
- Луна: {moon_sign} ({moon_degrees}°), фаза {moon_phase}
- Меркурий: {mercury_sign} | Венера: {venus_sign} | Марс: {mars_sign}
- Планетные аспекты: {aspects}
- Асцендент: {ascendant}
- Планеты по домам: {planets_in_houses_text}
- Знак читателя: {zodiac_sign}

Правила:
1. Объем 600-650 слов, дружелюбный, уверенный тон.
2. Пиши образно, но без клише, используй московский контекст: стиль дня, трафик, погоду.
3. Каждый блок 2-3 абзаца, используй конкретику из астрологических данных.
4. В каждом разделе обратись напрямую к читателю, избегай фраз \"возможно\" или \"скорее всего\".

Структура (строго HTML):
<h2>Общий тон дня</h2>
<p>... (выводы по Луне и аспектам)</p>

<h2>Настроение и энергия</h2>
<p>... (асцендент, дома Луны, лучшее время дня)</p>

<h2>Стиль и одежда</h2>
<p>... (что надеть, цвета, материалы по погоде и Венере; упомяни московские улицы)</p>

<h2>Любовь</h2>
<p>... (для тех, кто в отношениях, и для свободных; опора на Венеру, Луну, аспекты)</p>

<h2>Финансы и удача</h2>
<p>... (риски и возможности, удачные часы, связь с Меркурием/Марсом, домами 2 и 8)</p>

<h2>Здоровье</h2>
<p>... (уязвимые зоны, режим дня, напоминание о погоде)</p>

<h2>Практическая рекомендация</h2>
<p>Конкретное действие на день: привычка, маршрут по Москве, ритуал, спорт.</p>

<h2>Совет по карьерному росту</h2>
<p>Как использовать аспекты дня для профессионального развития, контактов или учебы.</p>

Закончить абзацем: \"Пусть {next_date} подарит тебе уверенность и вдохновение, {zodiac_sign}!\""""


HOROSCOPE_TEXT_VARIABLES = [
    "current_date",
    "next_date",
    "weekday",
    "weekend_status",
    "season",
    "weather",
    "sun_sign",
    "sun_degrees",
    "moon_sign",
    "moon_degrees",
    "moon_phase",
    "mercury_sign",
    "venus_sign",
    "mars_sign",
    "aspects",
    "ascendant",
    "planets_in_houses_text",
    "zodiac",
    "zodiac_sign",
]


HOROSCOPE_IMAGE_PROMPT = """Иллюстрация высокого качества (формат 3:2) в стиле глянцевого журнала. На переднем плане мужчина и женщина знака зодиака {zodiac_sign}, их внешность отражает архетип знака. Одежда передает сезон {season} и прогноз погоды {weather}, подходит для прогулки по улицам Москвы. Фон: московские улицы или бульвары с мягким естественным светом, без текста и логотипов. Цветовая палитра согласована с настроением знака и погодой. Камера — полупортрет или средний план, лёгкое боке. Качество 4K, современная fashion-фотография."""


HOROSCOPE_IMAGE_VARIABLES = [
    "zodiac_sign",
    "season",
    "weather",
]


def _get_ai_user(apps):
    user_model = apps.get_model(*settings.AUTH_USER_MODEL.split("."))
    ai_user = user_model.objects.filter(username="ai_assistant").first()
    if ai_user:
        return ai_user
    ai_user = user_model.objects.filter(is_superuser=True).first()
    if ai_user:
        return ai_user
    return user_model.objects.order_by("id").first()


def update_prompts(apps, schema_editor):
    PromptTemplate = apps.get_model("Asistent", "PromptTemplate")
    PromptTemplateVersion = apps.get_model("Asistent", "PromptTemplateVersion")

    ai_user = _get_ai_user(apps)

    # Обновляем текстовый промпт
    text_defaults = {
        "category": "horoscope",
        "description": "Ежедневный гороскоп на завтра",
        "template": HOROSCOPE_TEXT_PROMPT,
        "variables": HOROSCOPE_TEXT_VARIABLES,
        "is_active": True,
        "last_change_summary": "Обновлен шаблон ежедневного гороскопа (600-650 слов, новый тон, новые блоки)",
    }
    if ai_user:
        text_defaults["created_by"] = ai_user
        text_defaults["updated_by"] = ai_user

    text_template, _ = PromptTemplate.objects.get_or_create(
        name="DAILY_HOROSCOPE_PROMPT",
        defaults=text_defaults,
    )

    text_template.template = HOROSCOPE_TEXT_PROMPT
    text_template.variables = HOROSCOPE_TEXT_VARIABLES
    text_template.category = "horoscope"
    text_template.description = "Ежедневный гороскоп на завтра"
    text_template.is_active = True
    text_template.last_change_summary = text_defaults["last_change_summary"]
    if ai_user and text_template.created_by is None:
        text_template.created_by = ai_user
    if ai_user:
        text_template.updated_by = ai_user
    text_template.current_version = (text_template.current_version or 0) + 1
    text_template.save()

    PromptTemplateVersion.objects.update_or_create(
        template=text_template,
        version=text_template.current_version,
        defaults={
            "template_text": HOROSCOPE_TEXT_PROMPT,
            "variables": HOROSCOPE_TEXT_VARIABLES,
            "description": text_template.description,
            "change_summary": text_template.last_change_summary,
            "created_by": ai_user,
            "title_criteria": text_template.title_criteria or "",
            "image_search_criteria": text_template.image_search_criteria or "",
            "image_generation_criteria": text_template.image_generation_criteria or "",
            "tags_criteria": text_template.tags_criteria or "",
        },
    )

    # Создаем или обновляем промпт для изображений
    image_defaults = {
        "category": "image_generation",
        "description": "Промпт для генерации иллюстрации гороскопа",
        "template": HOROSCOPE_IMAGE_PROMPT,
        "variables": HOROSCOPE_IMAGE_VARIABLES,
        "is_active": True,
        "last_change_summary": "Добавлен шаблон изображения гороскопа (Москва, сезон, пара)",
    }
    if ai_user:
        image_defaults["created_by"] = ai_user
        image_defaults["updated_by"] = ai_user

    image_template, _ = PromptTemplate.objects.get_or_create(
        name="HOROSCOPE_IMAGE_PROMPT",
        defaults=image_defaults,
    )

    image_template.template = HOROSCOPE_IMAGE_PROMPT
    image_template.variables = HOROSCOPE_IMAGE_VARIABLES
    image_template.category = "image_generation"
    image_template.description = "Промпт для генерации иллюстрации гороскопа"
    image_template.is_active = True
    image_template.last_change_summary = image_defaults["last_change_summary"]
    if ai_user and image_template.created_by is None:
        image_template.created_by = ai_user
    if ai_user:
        image_template.updated_by = ai_user
    image_template.current_version = (image_template.current_version or 0) + 1
    image_template.save()

    PromptTemplateVersion.objects.update_or_create(
        template=image_template,
        version=image_template.current_version,
        defaults={
            "template_text": HOROSCOPE_IMAGE_PROMPT,
            "variables": HOROSCOPE_IMAGE_VARIABLES,
            "description": image_template.description,
            "change_summary": image_template.last_change_summary,
            "created_by": ai_user,
            "title_criteria": image_template.title_criteria or "",
            "image_search_criteria": image_template.image_search_criteria or "",
            "image_generation_criteria": image_template.image_generation_criteria or "",
            "tags_criteria": image_template.tags_criteria or "",
        },
    )


def noop(apps, schema_editor):
    """Обратное действие не требуется."""
    return None


class Migration(migrations.Migration):

    dependencies = [
        ("Asistent", "0051_update_pipeline_presets"),
    ]

    operations = [
        migrations.RunPython(update_prompts, noop),
    ]

