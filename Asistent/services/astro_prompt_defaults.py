from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Tuple

from .astro_context import AstrologyContextBuilder


def build_horoscope_prompt_context(sign_value: str) -> Dict[str, str]:
    """
    Возвращает полный набор астрологических данных для указанного знака.
    Используется там, где необходимо автоматически подставить контекст в промпт.
    """
    builder = AstrologyContextBuilder()
    context = builder.build_context(sign_value)
    context = context.copy()

    context.setdefault("zodiac", sign_value)
    context.setdefault("zodiac_sign", sign_value)

    if "next_date" in context:
        context.setdefault("date", context.get("next_date"))

    context.setdefault("current_year", datetime.now().year)

    planets_in_houses = context.get("planets_in_houses")
    if isinstance(planets_in_houses, dict):
        context["planets_in_houses"] = "; ".join(
            f"{planet}: дом {house}" for planet, house in planets_in_houses.items()
        )

    return context


def build_horoscope_variable_defaults(
    variable_names: List[str], sign_value: str
) -> Tuple[Dict[str, str], Dict[str, str]]:
    """
    Возвращает словари (defaults, values) для заполнения формы
    переменных в интерфейсе тестирования промптов гороскопов.
    """
    context = build_horoscope_prompt_context(sign_value)
    defaults: Dict[str, str] = {}
    values: Dict[str, str] = {}

    def _resolve_value(name: str) -> str:
        raw = context.get(name) or context.get(name.lower())
        if raw is None:
            return ""
        if isinstance(raw, (int, float)):
            return str(raw)
        if isinstance(raw, dict):
            return "; ".join(f"{k}: {v}" for k, v in raw.items())
        return str(raw)

    for var in variable_names or []:
        defaults[var] = _resolve_value(var)
        values[var] = defaults[var]

    return defaults, values

