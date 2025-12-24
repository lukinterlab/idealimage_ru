from django.db import migrations


def fill_schedule_defaults(apps, schema_editor):
    AISchedule = apps.get_model('Asistent', 'AISchedule')

    for schedule in AISchedule.objects.all():
        updated_fields = []

        if not schedule.schedule_kind:
            schedule.schedule_kind = 'daily'
            updated_fields.append('schedule_kind')

        if schedule.schedule_kind == 'interval' and not schedule.interval_minutes:
            schedule.interval_minutes = 60
            updated_fields.append('interval_minutes')

        if schedule.strategy_type == 'pipeline':
            if not schedule.pipeline_slug and schedule.pipeline_id:
                pipeline = getattr(schedule, 'pipeline', None)
                if pipeline and pipeline.slug:
                    schedule.pipeline_slug = pipeline.slug
                    updated_fields.append('pipeline_slug')
            elif schedule.pipeline_slug is None:
                schedule.pipeline_slug = ''
                updated_fields.append('pipeline_slug')

        if schedule.cron_expression is None:
            schedule.cron_expression = ''
            updated_fields.append('cron_expression')

        if not schedule.next_run:
            next_run = schedule.calculate_next_run()
            if next_run:
                schedule.next_run = next_run
                updated_fields.append('next_run')

        if updated_fields:
            schedule.save(update_fields=updated_fields)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('Asistent', '0056_remove_aifeedback_created_by_remove_aifeedback_task_and_more'),
    ]

    operations = [
        migrations.RunPython(fill_schedule_defaults, noop),
    ]

