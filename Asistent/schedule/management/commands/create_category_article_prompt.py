"""
Management команда для создания промпт-шаблона CATEGORY_ARTICLE_PROMPT.
Используется для автопостинга статей по категориям.
"""
from django.core.management.base import BaseCommand
from django.conf import settings
from Asistent.models import PromptTemplate, PromptTemplateVersion
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = 'Создаёт промпт-шаблон CATEGORY_ARTICLE_PROMPT для автопостинга по категориям'
    
    def handle(self, *args, **options):
        PROMPT_NAME = "CATEGORY_ARTICLE_PROMPT"
        
        PROMPT_TEXT = (
            "Ты профессиональный журналист и контент-маркетолог с опытом создания качественных статей.\n\n"
            "Задача: Напиши интересную, полезную и SEO-оптимизированную статью на тему, связанную с категорией '{category}'.\n\n"
            "Контекст:\n"
            "- Категория: {category}\n"
            "- Дата: {date}\n"
            "- День недели: {weekday}\n"
            "- Сезон: {season}\n"
            "- Текущий год: {year}\n"
            "{partner_instruction}\n"
            "\n"
            "Требования к статье:\n"
            "1. Объём: 1500-2500 слов\n"
            "2. Структура: Введение, основная часть (3-5 разделов), заключение\n"
            "3. Стиль: Экспертный, но доступный. Используй примеры и практические советы\n"
            "4. SEO: Естественное использование ключевых слов, связанных с категорией\n"
            "5. Форматирование: Используй HTML теги: <h2> для заголовков разделов, <p> для абзацев, <ul>/<ol> для списков\n"
            "6. Уникальность: Статья должна быть полностью уникальной, без копирования\n\n"
            "Начни писать статью прямо сейчас. Используй формат HTML для структурирования."
        )
        
        VARIABLES = [
            "category",
            "date",
            "weekday",
            "season",
            "year",
            "partner_url",
            "partner_link_text",
            "partner_instruction",
        ]
        
        # Находим пользователя для создания шаблона
        ai_user = User.objects.filter(username="ai_assistant").first()
        if ai_user is None:
            ai_user = User.objects.filter(is_superuser=True).first()
        if ai_user is None:
            ai_user = User.objects.order_by("id").first()
        
        defaults = {
            "category": "article_single",
            "description": "Универсальный шаблон для генерации статей по категориям с поддержкой партнёрских ссылок",
            "template": PROMPT_TEXT,
            "variables": VARIABLES,
            "is_active": True,
            "content_source_type": "generate",
            "image_source_type": "generate_auto",
            "title_criteria": "Интересный, цепляющий заголовок, связанный с категорией {category}. Длина: 50-70 символов.",
            "tags_criteria": "{category}, статья, полезные советы",
            "last_change_summary": "Создан универсальный шаблон для автопостинга по категориям",
        }
        
        if ai_user:
            defaults["created_by"] = ai_user
            defaults["updated_by"] = ai_user
        
        template, created = PromptTemplate.objects.get_or_create(
            name=PROMPT_NAME,
            defaults=defaults,
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS(f'✅ Создан шаблон: {PROMPT_NAME}'))
        else:
            # Обновляем существующий шаблон
            template.template = PROMPT_TEXT
            template.variables = VARIABLES
            template.category = "article_single"
            template.description = defaults["description"]
            template.is_active = True
            template.title_criteria = defaults["title_criteria"]
            template.tags_criteria = defaults["tags_criteria"]
            template.content_source_type = defaults["content_source_type"]
            template.image_source_type = defaults["image_source_type"]
            template.last_change_summary = "Обновлён шаблон для автопостинга по категориям"
            
            if ai_user:
                if template.created_by is None:
                    template.created_by = ai_user
                template.updated_by = ai_user
            
            template.current_version = (template.current_version or 0) + 1
            template.save()
            
            # Создаём версию
            PromptTemplateVersion.objects.update_or_create(
                template=template,
                version=template.current_version,
                defaults={
                    "template_text": PROMPT_TEXT,
                    "variables": VARIABLES,
                    "description": template.description,
                    "title_criteria": template.title_criteria or "",
                    "image_search_criteria": template.image_search_criteria or "",
                    "image_generation_criteria": template.image_generation_criteria or "",
                    "tags_criteria": template.tags_criteria or "",
                    "change_summary": template.last_change_summary,
                    "created_by": ai_user,
                },
            )
            
            self.stdout.write(self.style.SUCCESS(f'✅ Обновлён шаблон: {PROMPT_NAME}'))
        
        self.stdout.write(f'   ID: {template.id}')
        self.stdout.write(f'   Категория: {template.category}')
        self.stdout.write(f'   Активен: {template.is_active}')

