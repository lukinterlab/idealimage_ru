from django.conf import settings
from django.db import migrations

PROMPT_NAME = "DAILY_HOROSCOPE_PROMPT"
PROMPT_TEXT = (
    "Ты профессиональный астролог с 30-летним опытом и работаешь в ведущем журнале.\n\n"
    "На входе данные для прогноза на завтра:\n"
    "- Сегодня: {current_date}\n"
    "- Завтра: {next_date}, день недели: {weekday} ({weekend_status})\n"
    "- Сезон: {season}\n"
    "- Прогноз погоды: {weather}\n"
    "- Солнце: {sun_sign} ({sun_degrees} градусов)\n"
    "- Луна: {moon_sign} ({moon_degrees} градусов), фаза {moon_phase}\n"
    "- Меркурий: {mercury_sign} | Венера: {venus_sign} | Марс: {mars_sign}\n"
    "- Планетные аспекты: {aspects}\n"
    "- Асцендент: {ascendant}\n"
    "- Планеты по домам: {planets_in_houses_text}\n"
    "- Знак читателя: {zodiac}\n\n"
    "Важно: {aspects} может сообщать, что точных аспектов нет — в таком случае подчёркни мягкий, ровный фон дня.\n"
    "Пиши живым, но спокойным тоном, без пафоса и без оговорок вроде \"это условно\".\n\n"
    "Структура ответа (строго в HTML):\n"
    "1. <h2>Общий тон дня</h2><p>2-3 предложения, сделай вывод на основе Луны и аспектов.</p>\n"
    "2. <h2>Стиль и одежда</h2><p>Практический совет по цвету, материалу, фасону с учётом погоды и Венеры/Луны.</p>\n"
    "3. <h2>Настроение и энергия</h2><p>Опиши эмоциональный фон, уровень активности, упомяни асцендент или дом Луны.</p>\n"
    "4. <h2>Любовь</h2><p>Отдельно для тех, кто в отношениях, и для свободных. Ссылки на Венеру, Луну, аспекты.</p>\n"
    "5. <h2>Финансы и удача</h2><p>Риски, возможности, удачные часы. Упоминай Меркурий, Марс, дома 2/8, если это уместно.</p>\n"
    "6. <h2>Здоровье</h2><p>Уязвимые зоны знака, влияние Луны на самочувствие, рекомендация по режиму.</p>\n"
    "7. <h2>Ритуал дня</h2><p>Короткий совет: дыхание, свеча, прогулка, дневник и т.п., связан с текущим знаком/фазой.</p>\n\n"
    "Каждый абзац 2-3 предложения, используй конкретику и призывы к действию."
)

VARIABLES = [
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
]


def create_daily_horoscope_prompt(apps, schema_editor):
    PromptTemplate = apps.get_model("Asistent", "PromptTemplate")
    PromptTemplateVersion = apps.get_model("Asistent", "PromptTemplateVersion")
    UserModel = apps.get_model(*settings.AUTH_USER_MODEL.split("."))

    ai_user = UserModel.objects.filter(username="ai_assistant").first()
    if ai_user is None:
        ai_user = UserModel.objects.filter(is_superuser=True).first()
    if ai_user is None:
        ai_user = UserModel.objects.order_by("id").first()

    defaults = {
        "category": "horoscope",
        "description": "Ежедневный гороскоп на завтра",
        "template": PROMPT_TEXT,
        "variables": VARIABLES,
        "is_active": True,
        "last_change_summary": "Создан шаблон ежедневного гороскопа",
    }
    if ai_user:
        defaults["created_by"] = ai_user
        defaults["updated_by"] = ai_user

    template, created = PromptTemplate.objects.get_or_create(
        name=PROMPT_NAME,
        defaults=defaults,
    )

    change_summary = "Обновлен шаблон ежедневного гороскопа"

    if created:
        template.last_change_summary = defaults["last_change_summary"]
    else:
        template.template = PROMPT_TEXT
        template.variables = VARIABLES
    template.category = "horoscope"
    template.description = "Ежедневный гороскоп на завтра"
    template.is_active = True
    template.last_change_summary = change_summary
    if ai_user and template.created_by is None:
        template.created_by = ai_user
    if ai_user:
        template.updated_by = ai_user
    template.current_version = (template.current_version or 0) + 1
    template.save()

    version_kwargs = {
        "template_text": PROMPT_TEXT,
        "variables": VARIABLES,
        "description": template.description,
        "title_criteria": template.title_criteria or "",
        "image_search_criteria": template.image_search_criteria or "",
        "image_generation_criteria": template.image_generation_criteria or "",
        "tags_criteria": template.tags_criteria or "",
        "change_summary": template.last_change_summary,
        "created_by": ai_user,
    }

    PromptTemplateVersion.objects.update_or_create(
        template=template,
        version=template.current_version,
        defaults=version_kwargs,
    )


def noop(apps, schema_editor):
    """Обратное действие не требуется."""
    # Шаблон можно отредактировать вручную через админку при необходимости
    return None


class Migration(migrations.Migration):

    dependencies = [
        ("Asistent", "0043_convert_database_to_utf8mb4"),
    ]

    operations = [
        migrations.RunPython(create_daily_horoscope_prompt, noop),
    ]
