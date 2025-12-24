import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from django.utils.html import escape


class MarkdownPreset(str, Enum):
    CKEDITOR = "ckeditor"
    MODERATOR = "moderator"
    CONTENT = "content"
    BASIC = "basic"


@dataclass(frozen=True)
class MarkdownOptions:
    preset: MarkdownPreset = MarkdownPreset.BASIC
    indent_paragraphs: bool = False
    paragraph_class: Optional[str] = None
    paragraph_style: Optional[str] = None
    heading_styles: Optional[dict] = None
    allow_inline_styles: bool = False


def render_markdown(text: str, *, options: Optional[MarkdownOptions] = None, preset: Optional[MarkdownPreset] = None) -> str:
    """
    Унифицированная конвертация markdown->HTML для Asistent.

    Args:
        text: исходный markdown или HTML
        options: настраиваемые параметры
        preset: предустановленные параметры
    """
    if not text:
        return ""

    if isinstance(preset, str):
        preset = MarkdownPreset(preset)

    if options is None:
        options = _options_for_preset(preset or MarkdownPreset.BASIC)

    text = text.strip()
    if not text:
        return ""

    has_html = bool(re.search(r"<(p|h\d|ul|ol|li|div|section|article|blockquote)\b", text))
    if has_html:
        return text

    lines = text.splitlines()
    result_lines = []
    list_stack = []

    def _close_lists():
        while list_stack:
            tag = list_stack.pop()
            result_lines.append(f"</{tag}>")

    heading_styles = options.heading_styles or {}

    for raw_line in lines:
        line = raw_line.rstrip()

        if not line.strip():
            _close_lists()
            result_lines.append("")
            continue

        heading_match = re.match(r"^(#{2,4})\s+(.*)", line)
        if heading_match:
            _close_lists()
            level = len(heading_match.group(1))
            content = heading_match.group(2).strip()
            tag = f"h{min(max(level, 2), 4)}"
            style_attr = ""
            if options.allow_inline_styles and tag in heading_styles:
                style_attr = f' style="{heading_styles[tag]}"'
            result_lines.append(f"<{tag}{style_attr}>{escape(content)}</{tag}>")
            continue

        bullet_match = re.match(r"^[-*]\s+(.*)", line)
        ordered_match = re.match(r"^\d+\.\s+(.*)", line)

        if bullet_match or ordered_match:
            tag = "ul" if bullet_match else "ol"
            content = bullet_match.group(1).strip() if bullet_match else ordered_match.group(1).strip()
            if not list_stack or list_stack[-1] != tag:
                if list_stack and list_stack[-1] != tag:
                    _close_lists()
                list_stack.append(tag)
                result_lines.append(f"<{tag}>")
            result_lines.append(f"<li>{escape(content)}</li>")
            continue

        _close_lists()

        paragraph = escape(line.strip())
        if options.paragraph_class or options.paragraph_style or options.indent_paragraphs:
            class_attr = f' class="{options.paragraph_class}"' if options.paragraph_class else ""
            style = options.paragraph_style or ""
            if options.indent_paragraphs and "text-indent" not in style:
                style = f"{style}; text-indent: 2em;" if style else "text-indent: 2em;"
            style_attr = f' style="{style}"' if style else ""
            result_lines.append(f"<p{class_attr}{style_attr}>{paragraph}</p>")
        else:
            result_lines.append(f"<p>{paragraph}</p>")

    _close_lists()
    html = "\n".join(result_lines)
    html = re.sub(r"\n{3,}", "\n\n", html)
    return html.strip()


def _options_for_preset(preset: MarkdownPreset) -> MarkdownOptions:
    if preset == MarkdownPreset.CKEDITOR:
        heading_styles = {
            "h2": "color: #ffffff; font-weight: 700; font-size: 1.5em; margin-top: 1.5em; margin-bottom: 0.75em;",
            "h3": "color: #ffffff; font-weight: 700; font-size: 1.25em; margin-top: 1.25em; margin-bottom: 0.5em;",
            "h4": "color: #ffffff; font-weight: 600; font-size: 1.1em; margin-top: 1em; margin-bottom: 0.5em;",
        }
        return MarkdownOptions(
            preset=preset,
            indent_paragraphs=False,
            paragraph_style="margin-bottom: 1em;",
            allow_inline_styles=True,
            heading_styles=heading_styles,
        )

    if preset == MarkdownPreset.MODERATOR:
        return MarkdownOptions(
            preset=preset,
            indent_paragraphs=True,
            paragraph_style="margin-bottom: 1em;",
            allow_inline_styles=False,
        )

    if preset == MarkdownPreset.CONTENT:
        return MarkdownOptions(
            preset=preset,
            indent_paragraphs=False,
            paragraph_class="prose max-w-none",
            allow_inline_styles=False,
        )

    return MarkdownOptions(preset=MarkdownPreset.BASIC)

