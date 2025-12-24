from django.db import migrations
from django.utils import timezone
from datetime import datetime, timedelta


def create_priority_horoscope_schedule(apps, schema_editor):
    """Создает приоритетное расписание для ежедневных гороскопов."""
    AISchedule = apps.get_model("Asistent", "AISchedule")
    Category = apps.get_model("blog", "Category")
    
    # Проверяем, не существует ли уже такое расписание
    if AISchedule.objects.filter(name="Ежедневные гороскопы (приоритет)").exists():
        return
    
    # Получаем категорию для гороскопов (может быть None, если категория не найдена)
    category = Category.objects.filter(slug="intellektualnye-prognozy").first()
    if not category:
        # Если категория не найдена, пытаемся найти любую категорию или оставляем None
        category = Category.objects.first()
    
    # Вычисляем следующее время запуска (8:00 сегодня или завтра)
    now = timezone.now()
    today_8am = now.replace(hour=8, minute=0, second=0, microsecond=0)
    if now >= today_8am:
        next_run = (now + timedelta(days=1)).replace(hour=8, minute=0, second=0, microsecond=0)
    else:
        next_run = today_8am
    
    schedule = AISchedule.objects.create(
        name="Ежедневные гороскопы (приоритет)",
        strategy_type="pipeline",
        schedule_kind="cron",
        cron_expression="0,15,30,45 8-10 * * *",  # Каждые 15 минут с 8:00 до 10:45
        pipeline_slug="daily-horoscope-flow",
        category=category,
        tags="гороскоп, прогноз на завтра",
        payload_template={
            "target_date_offset": 1,
            "publish_mode": "published",
            "title_template": "{zodiac_sign} — гороскоп на {horoscope_target_date_display}",
            "description_template": "Ежедневный гороскоп для {zodiac_sign} на {horoscope_target_date_display}.",
            "base_tags": ["гороскоп", "прогноз на завтра"],
        },
        is_active=True,
        next_run=next_run,
        current_run_count=0,
    )
    
    print(f"[OK] Создано расписание: {schedule.name} (ID: {schedule.id})")
    print(f"   Следующий запуск: {next_run}")


def remove_priority_horoscope_schedule(apps, schema_editor):
    """Удаляет приоритетное расписание гороскопов."""
    AISchedule = apps.get_model("Asistent", "AISchedule")
    AISchedule.objects.filter(name="Ежедневные гороскопы (приоритет)").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("Asistent", "0060_add_systemlog"),
    ]

    operations = [
        migrations.RunPython(create_priority_horoscope_schedule, remove_priority_horoscope_schedule),
    ]

