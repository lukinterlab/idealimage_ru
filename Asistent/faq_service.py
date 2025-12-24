import json
import logging
import re
from typing import Dict, List, Optional, Tuple

from django.utils.html import escape, strip_tags

from .prompt_registry import PromptRegistry

logger = logging.getLogger(__name__)


def generate_faq_bundle(
    post,
    gigachat_client,
    context: Optional[Dict] = None,
    *,
    include_html: bool = True,
    include_schema: bool = True,
) -> Tuple[Dict, Dict]:
    """
    Универсальная генерация FAQ данных.

    Возвращает кортеж (payload, meta), где payload содержит вопросы, html и schema,
    а meta — вспомогательную информацию (например, сырой ответ).
    """
    clean_content = strip_tags(post.content or "")[:2000]
    category_title = post.category.title if getattr(post.category, "title", None) else "Общее"

    prompt_params = {
        "title": post.title,
        "category": category_title,
        "content": clean_content,
        "context": context or {},
    }

    prompt = PromptRegistry.render("FAQ_GENERATION_PROMPT", params=prompt_params)

    if not prompt:
        logger.warning("FAQ_GENERATION_PROMPT не найден или отключен")
        return (
            {
                "questions": [],
                "html": "" if include_html else None,
                "schema": {} if include_schema else None,
                "success": False,
                "error": "faq_prompt_missing",
            },
            {"raw_response": "", "prompt_context": prompt_params},
        )

    PromptRegistry.increment_usage("FAQ_GENERATION_PROMPT")

    raw_response = gigachat_client.chat(prompt)

    extraction_mode = None
    sanitized_json = None
    questions_raw: List[Dict[str, str]] = []

    # 1. Пытаемся вытащить JSON, если он действительно похож на JSON
    json_candidate = _extract_json_block(raw_response)
    if json_candidate and _looks_like_json(json_candidate):
        sanitized_json = _normalize_json_string(json_candidate)
        try:
            faq_data = json.loads(sanitized_json)
            questions_raw = faq_data.get("questions", [])
            extraction_mode = "json"
        except json.JSONDecodeError as decode_error:
            logger.warning(
                "FAQ: JSON не распознан, переключаемся на текстовый парсинг: %s",
                decode_error,
            )

    # 2. Если JSON не получился или пустой — парсим текст свободной формы
    if not questions_raw:
        questions_raw = _parse_faq_from_text(raw_response)
        if questions_raw:
            extraction_mode = "text"

    questions = _prepare_questions(questions_raw)

    if not questions:
        logger.warning("FAQ: не удалось извлечь вопросы и ответы из ответа модели")
        html = "" if include_html else None
        schema = {} if include_schema else None
        payload = {
            "success": False,
            "questions": [],
            "html": html,
            "schema": schema,
            "count": 0,
            "error": "faq_extraction_failed",
        }
        meta = {
            "raw_response": raw_response,
            "sanitized_json": sanitized_json,
            "extraction_mode": extraction_mode,
            "prompt_context": prompt_params,
        }
        return payload, meta

    html = _build_html_block(questions) if include_html else None
    schema = _build_schema(questions) if include_schema else None

    payload = {
        "success": True,
        "questions": questions,
        "html": html,
        "schema": schema,
        "count": len(questions),
    }

    meta = {
        "raw_response": raw_response,
        "sanitized_json": sanitized_json,
        "extraction_mode": extraction_mode,
        "prompt_context": prompt_params,
    }

    return payload, meta


def _extract_json_block(response: str) -> str:
    if "```json" in response:
        json_start = response.find("```json") + 7
        json_end = response.find("```", json_start)
        response = response[json_start:json_end if json_end != -1 else None].strip()
    elif "```" in response:
        json_start = response.find("```") + 3
        json_end = response.find("```", json_start)
        response = response[json_start:json_end if json_end != -1 else None].strip()
    return response.strip()


def _looks_like_json(candidate: str) -> bool:
    if not candidate:
        return False
    trimmed = candidate.lstrip()
    return trimmed.startswith("{") or trimmed.startswith("[")


def _normalize_json_string(response: str) -> str:
    sanitized_response = response.replace("\\n", "\n").replace("\\t", "\t")
    sanitized_response = sanitized_response.replace('\\"', '"').replace("\\'", "'")
    sanitized_response = sanitized_response.replace("\\/", "/")
    sanitized_response = re.sub(r"\\\\(?![\"\\/bfnrt])", r"\\", sanitized_response)
    return sanitized_response


def _prepare_questions(raw_questions: List[Dict]) -> List[Dict]:
    prepared = []
    for item in raw_questions:
        question = _clean_text(item.get("question", ""))
        answer = _clean_text(item.get("answer", ""))

        if not question or not answer:
            continue

        prepared.append(
            {
                "question": question,
                "answer": answer,
            }
        )
    return prepared


def _clean_text(text: str) -> str:
    text = escape(text or "")
    text = re.sub(r"\[(.*?)\]\((https?://[^\s)]+)\)", _link_replacer, text)
    text = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"__(.*?)__", r"<strong>\1</strong>", text)
    text = re.sub(r"^#+\s*", "", text)
    text = re.sub(r"\s*#+\s*", " ", text)
    text = text.replace("*", "")
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip()


def _link_replacer(match: re.Match) -> str:
    label, url = match.group(1), match.group(2)
    return (
        f'<a href="{url}" target="_blank" rel="noopener noreferrer" '
        f'class="text-blue-600 dark:text-blue-400 font-medium underline">{escape(label)}</a>'
    )


def _build_html_block(questions: List[Dict]) -> str:
    html_parts = [
        '<div class="faq-section bg-gray-50 dark:bg-gray-800 p-8 rounded-2xl my-8 shadow-sm">',
        '<h2 class="text-2xl font-bold text-gray-900 dark:text-white mb-6">❓ Часто задаваемые вопросы</h2>',
        '<div class="faq-list space-y-4">'
    ]

    for index, item in enumerate(questions, 1):
        html_parts.append(
            f'''
                <div class="faq-item bg-white dark:bg-gray-700 p-6 rounded-xl shadow-sm border border-gray-200 dark:border-gray-600">
                    <h3 class="text-lg font-semibold text-blue-600 dark:text-blue-400 mb-3">
                        {index}. {item["question"]}
                    </h3>
                    <p class="text-gray-700 dark:text-gray-300 leading-relaxed indent-8">
                        {item["answer"]}
                    </p>
                </div>
            '''.strip()
        )

    html_parts.extend(
        [
            "</div>",
            "</div>",
        ]
    )

    return "\n".join(html_parts)


def _build_schema(questions: List[Dict]) -> Dict:
    return {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": item["question"],
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": item["answer"],
                },
            }
            for item in questions
        ],
    }


def _parse_faq_from_text(response: str) -> List[Dict[str, str]]:
    """
    Извлекает пары вопрос-ответ из свободного текста.
    Поддерживает форматы:
      - «Вопрос 1: ...», «Ответ: ...»
      - «Q: ...», «A: ...»
      - Строки, заканчивающиеся на «?» с последующими абзацами-ответами.
    """
    if not response:
        return []

    lines = [line.strip() for line in response.splitlines()]
    lines = [re.sub(r"\s+", " ", line) for line in lines if line.strip()]

    faq: List[Dict[str, str]] = []
    current_question: Optional[str] = None
    answer_lines: List[str] = []

    question_pattern = re.compile(r"^(?:вопрос|question|q)[\s\d\.:#\-–]*", re.IGNORECASE)
    answer_pattern = re.compile(r"^(?:ответ|answer|a)[\s\d\.:#\-–]*", re.IGNORECASE)

    def flush_pair():
        nonlocal current_question, answer_lines
        if current_question and answer_lines:
            answer_text = " ".join(answer_lines).strip()
            if answer_text:
                faq.append({"question": current_question.strip(), "answer": answer_text})
        current_question = None
        answer_lines = []

    for line in lines:
        normalized = line
        if question_pattern.match(normalized):
            flush_pair()
            normalized = question_pattern.sub("", normalized).strip()
            if not normalized:
                continue
            if not normalized.endswith("?"):
                normalized += "?"
            current_question = normalized
            continue

        if current_question:
            if answer_pattern.match(normalized):
                normalized = answer_pattern.sub("", normalized).strip()
                if not normalized:
                    continue
            answer_lines.append(normalized)
            continue

        # Если нет явной метки "Вопрос", но строка заканчивается вопросительным знаком,
        # трактуем её как вопрос.
        if normalized.endswith("?"):
            flush_pair()
            current_question = normalized
            continue

    flush_pair()

    if faq:
        return faq

    # Второй проход: пытаемся извлечь пары из списка нумерованных пунктов
    bullets = re.split(r"(?:^|\n)\s*\d+[\).\s-]+", response)
    fallback: List[Dict[str, str]] = []
    for chunk in bullets:
        chunk = chunk.strip()
        if not chunk:
            continue
        parts = chunk.split("?", 1)
        if len(parts) != 2:
            continue
        question_text = parts[0].strip() + "?"
        answer_text = parts[1].strip()
        if question_text and answer_text:
            fallback.append({"question": question_text, "answer": answer_text})
    return fallback

