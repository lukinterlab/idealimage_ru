"""
Базовые классы и утилиты для универсального генератора контента
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Optional, Any


class GeneratorMode(Enum):
    """Режимы работы генератора"""
    AUTO = 'auto'          # Автоматический (как tasks.py)
    INTERACTIVE = 'interactive'  # Интерактивный (как test_prompt.py)
    BATCH = 'batch'        # Batch-генерация
    SCHEDULED = 'scheduled'  # Через систему schedule


@dataclass
class GeneratorConfig:
    """Конфигурация генератора"""
    mode: GeneratorMode
    use_queue: bool = False
    use_heartbeat: bool = False
    use_priority: bool = False
    use_metrics: bool = False
    preview_only: bool = False
    retry_count: int = 3
    timeout: int = 300
    daily_limit: Optional[int] = None
    
    @classmethod
    def for_auto(cls):
        """Конфиг для автоматического режима (как tasks.py)"""
        return cls(
            mode=GeneratorMode.AUTO,
            use_queue=True,
            use_heartbeat=True,
            use_priority=True,
            use_metrics=True,
            retry_count=3,
            timeout=300,
            daily_limit=12,  # Для гороскопов
        )
    
    @classmethod
    def for_interactive(cls):
        """Конфиг для интерактивного режима (как test_prompt.py)"""
        return cls(
            mode=GeneratorMode.INTERACTIVE,
            use_queue=False,
            use_heartbeat=False,
            use_priority=False,
            use_metrics=False,
            preview_only=True,
            retry_count=1,
            timeout=300,
        )
    
    @classmethod
    def for_scheduled(cls):
        """Конфиг для расписания (schedule/)"""
        return cls(
            mode=GeneratorMode.SCHEDULED,
            use_queue=False,  # schedule имеет свою систему
            use_heartbeat=False,
            use_priority=False,
            use_metrics=True,
            retry_count=3,
            timeout=300,
        )
    
    @classmethod
    def for_batch(cls):
        """Конфиг для batch-генерации"""
        return cls(
            mode=GeneratorMode.BATCH,
            use_queue=True,
            use_heartbeat=False,
            use_priority=False,
            use_metrics=True,
            retry_count=2,
            timeout=300,
        )


@dataclass
class GenerationResult:
    """Результат генерации"""
    success: bool
    post: Optional[Any] = None  # Post объект
    post_id: Optional[int] = None
    title: Optional[str] = None
    content: Optional[str] = None
    image_path: Optional[str] = None
    error: Optional[str] = None
    metrics: Dict = field(default_factory=dict)
    session_data: Dict = field(default_factory=dict)  # Для preview режима
    
    def to_dict(self) -> Dict:
        """Преобразование в словарь"""
        return {
            'success': self.success,
            'post_id': self.post_id,
            'title': self.title,
            'content': self.content,
            'image_path': self.image_path,
            'error': self.error,
            'metrics': self.metrics,
        }


