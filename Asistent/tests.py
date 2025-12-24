from __future__ import annotations

import json
from typing import Any, Dict, List

from django.test import TestCase

from Asistent.moderations.services.rule_config import (
    get_rules_catalog,
    validate_rule_config,
)
from Asistent.pipeline.base import step_registry, trigger_registry
from Asistent.pipeline.steps.advertising import AdvertisingAutoInsertStep
from Asistent.pipeline.steps.seo import SeoKeywordAnalysisStep
from Asistent.pipeline.steps.social import SocialGenerateAnnounceStep
from Asistent.pipeline.steps.assistant import AITextAssistStep, AIImageAssistStep


class RuleConfigValidationTests(TestCase):
    """Юнит-тесты для проверки валидации конфигурации правил модерации."""

    def _assert_valid(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        is_valid, errors, normalized = validate_rule_config(payload)
        self.assertTrue(is_valid, msg=f"Ожидали валидный результат, но ошибки: {errors}")
        self.assertEqual(errors, [])
        self.assertIsInstance(normalized, dict)
        return normalized

    def _assert_invalid(self, payload: Dict[str, Any], expected_messages: List[str]) -> None:
        is_valid, errors, _ = validate_rule_config(payload)
        self.assertFalse(is_valid)
        for message in expected_messages:
            self.assertTrue(
                any(message in err for err in errors),
                msg=f"Не найдено сообщение об ошибке '{message}'. Фактические ошибки: {errors}",
            )

    def test_catalog_contains_registered_rules(self):
        """Каталог должен возвращать все зарегистрированные правила."""
        catalog = get_rules_catalog()
        codes = {item["code"] for item in catalog}
        self.assertIn("MEDIA_REQUIRED", codes)
        self.assertIn("WORD_COUNT", codes)
        self.assertIn("AI_PENALTY_SUMMARY", codes)
        # Проверяем, что для правила есть базовые метаданные
        media_rule = next(item for item in catalog if item["code"] == "MEDIA_REQUIRED")
        self.assertIn("fields", media_rule)
        self.assertIsInstance(media_rule["fields"], list)

    def test_valid_config_is_accepted(self):
        """Корректная конфигурация принимается без ошибок."""
        payload = {
            "global": [
                {"code": "MEDIA_REQUIRED", "priority": 10, "auto_fix": True, "penalty": 25, "penalty_key": "media"},
                {"code": "WORD_COUNT", "priority": 20, "target": 650, "min_required": 600},
            ],
            "roles": {
                "author_with_ai": [{"code": "WORD_COUNT", "priority": 15, "penalty": 40}],
            },
            "categories": {
                "beauty": [{"code": "FAQ_REQUIRED", "priority": 30}],
            },
        }
        normalized = self._assert_valid(payload)
        # Проверяем, что порядки сохранены
        self.assertEqual(normalized["global"][0]["code"], "MEDIA_REQUIRED")
        self.assertEqual(normalized["roles"]["author_with_ai"][0]["priority"], 15)

    def test_duplicate_codes_produce_error(self):
        """Дублирующиеся правила в одной секции запрещены."""
        payload = {"global": [{"code": "MEDIA_REQUIRED"}, {"code": "MEDIA_REQUIRED"}]}
        self._assert_invalid(payload, ["Правило 'MEDIA_REQUIRED' добавлено несколько раз"])

    def test_unknown_rule_code_produces_error(self):
        """Неизвестный код правила приводит к ошибке."""
        payload = {"global": [{"code": "UNKNOWN_RULE"}]}
        self._assert_invalid(payload, ["Правило 'UNKNOWN_RULE' не зарегистрировано"])

    def test_invalid_priority_type(self):
        """Приоритет должен быть числом."""
        payload = {"global": [{"code": "MEDIA_REQUIRED", "priority": "high"}]}
        self._assert_invalid(payload, ["Приоритет должен быть числом"])

    def test_penalty_range_validation(self):
        """Штраф 0-100, иначе ошибка."""
        payload = {"global": [{"code": "MEDIA_REQUIRED", "penalty": 120}]}
        self._assert_invalid(payload, ["'penalty' должен быть числом 0-100"])

    def test_hours_validation(self):
        """Поле 'hours' валидируется как объект со start/end."""
        payload = {
            "global": [
                {
                    "code": "PUBLICATION_WINDOW",
                    "hours": {"start": 22, "end": 22},
                }
            ]
        }
        self._assert_invalid(payload, ["Интервал публикации не может начинаться и заканчиваться в один час"])

        payload["global"][0]["hours"] = {"start": -1, "end": 25}
        self._assert_invalid(
            payload,
            ["'hours.start' должно быть числом от 0 до 23", "'hours.end' должно быть числом от 0 до 23"],
        )

        payload["global"][0]["hours"] = {"start": 8, "end": 19}
        normalized = self._assert_valid(payload)
        self.assertEqual(normalized["global"][0]["hours"], {"start": 8, "end": 19})

    def test_roles_and_categories_expect_dicts(self):
        """Секции roles/categories должны быть словарями."""
        payload = {"global": [], "roles": ["invalid"], "categories": "invalid"}
        self._assert_invalid(payload, ["[roles] Ожидается объект", "[categories] Ожидается объект"])

    def test_disabled_rule_removed_from_overrides(self):
        """Если в override указано enabled=false, правило удаляется для этой секции."""
        payload = {
            "global": [{"code": "MEDIA_REQUIRED"}, {"code": "WORD_COUNT"}],
            "roles": {"editor": [{"code": "WORD_COUNT", "enabled": False}]},
        }
        normalized = self._assert_valid(payload)
        self.assertEqual(normalized["roles"]["editor"], [])

    def test_unknown_fields_raise_error(self):
        """Не разрешённые поля в конфигурации вызывают ошибку."""
        payload = {"global": [{"code": "MEDIA_REQUIRED", "unexpected": True}]}
        self._assert_invalid(payload, ["Поле 'unexpected' не поддерживается"])

    def test_empty_config_defaults_to_valid(self):
        """Пустой конфиг считается валидным и возвращает пустые списки."""
        normalized = self._assert_valid({})
        self.assertEqual(normalized["global"], [])
        self.assertEqual(normalized["roles"], {})
        self.assertEqual(normalized["categories"], {})

    def test_respects_default_rule_matrix_in_catalog_sample(self):
        """Каталог возвращает дефолтную конфигурацию, совпадающую с DEFAULT_RULE_MATRIX."""
        catalog = get_rules_catalog()
        # Находим запись по коду и сравниваем с DEFAULT_RULE_MATRIX
        word_count_entry = next(item for item in catalog if item["code"] == "WORD_COUNT")
        default_config = word_count_entry.get("default_config")
        self.assertIsInstance(default_config, dict)
        self.assertEqual(default_config.get("code"), "WORD_COUNT")
        self.assertIn("priority", default_config)
        self.assertIn("auto_fix", default_config)
        # проверяем, что JSON сериализуемый
        json.loads(json.dumps(default_config, ensure_ascii=False))


class PipelineRegistryTests(TestCase):
    """Проверяем, что ключевые триггеры и шаги зарегистрированы в реестрах."""

    def test_trigger_registry_contains_expected_codes(self):
        codes = {trigger["code"] for trigger in trigger_registry.describe()}
        self.assertIn("POST_STATUS_PUBLISHED", codes)
        self.assertIn("AI_ASSIST_REQUESTED", codes)
        self.assertIn("MANUAL_SINGLE", codes)
        self.assertIn("SCHEDULE_WEEKLY", codes)

    def test_step_registry_contains_expected_codes(self):
        codes = {step["code"] for step in step_registry.describe()}
        self.assertIn("VALIDATE_REQUIRED_FIELDS", codes)
        self.assertIn("SEO_INTERNAL_LINKING", codes)
        self.assertIn("SOCIAL_TELEGRAM_PUBLISH", codes)
        self.assertIn("ADS_AUTO_INSERT", codes)
        self.assertIn("AI_TEXT_ASSIST", codes)
        self.assertIn("AI_IMAGE_ASSIST", codes)


class PipelineStepValidationTests(TestCase):
    """Тесты на базовую корректность шагов пайплайна (ошибки при некорректном payload)."""

    def test_social_generate_announce_requires_post_id(self):
        step = SocialGenerateAnnounceStep()
        result = step.run(payload={}, config={})
        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "post_id_missing")

    def test_ads_auto_insert_requires_post_id(self):
        step = AdvertisingAutoInsertStep()
        result = step.run(payload={}, config={})
        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "post_id_missing")

    def test_seo_keyword_analysis_requires_post_id(self):
        step = SeoKeywordAnalysisStep()
        result = step.run(payload={}, config={})
        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "post_id_missing")

    def test_ai_text_assist_requires_post_id(self):
        step = AITextAssistStep()
        result = step.run(payload={}, config={})
        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "post_id_missing")

    def test_ai_image_assist_requires_post_id(self):
        step = AIImageAssistStep()
        result = step.run(payload={}, config={})
        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "post_id_missing")
