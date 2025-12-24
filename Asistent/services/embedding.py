import logging
from typing import Dict, Iterable, Optional, Sequence

logger = logging.getLogger(__name__)


def cache_previous_state(
    cache: Dict[int, Dict[str, object]],
    instance,
    *,
    model_cls,
    fields: Sequence[str],
    extra_fields: Optional[Iterable[str]] = None,
) -> None:
    """
    Сохраняет предыдущее состояние полей модели перед сохранением.
    """
    if not instance.pk:
        return

    try:
        old_instance = model_cls.objects.get(pk=instance.pk)
    except model_cls.DoesNotExist:
        return

    snapshot = {field: getattr(old_instance, field) for field in fields}
    if extra_fields:
        for field in extra_fields:
            snapshot[field] = getattr(old_instance, field)

    cache[instance.pk] = snapshot


def should_regenerate_embedding(
    cache: Dict[int, Dict[str, object]],
    instance,
    *,
    created: bool,
    fields: Sequence[str],
    embedding_field: Optional[str] = None,
) -> bool:
    """
    Определяет, нужно ли генерировать embedding после сохранения.
    """
    if created:
        return True

    previous = cache.pop(instance.pk, None)
    if not previous:
        return False

    if embedding_field and not previous.get(embedding_field):
        return True

    for field in fields:
        if previous.get(field) != getattr(instance, field):
            return True

    return False


def store_embedding(
    instance,
    embedding,
    *,
    model_cls,
    skip_flag: str = "_skip_embedding_generation",
    field_name: str = "embedding",
) -> bool:
    """
    Сохраняет embedding для экземпляра модели, устанавливая флаг,
    чтобы избежать повторного срабатывания сигналов.
    """
    if not embedding:
        return False

    setattr(instance, skip_flag, True)
    model_cls.objects.filter(pk=instance.pk).update(**{field_name: embedding})
    return True


