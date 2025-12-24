import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ScheduleLogEntry:
    timestamp: float
    level: str
    message: str
    payload: Optional[Dict[str, Any]] = None


@dataclass
class ScheduleContext:
    """
    Контекст выполнения расписания. Передается стратегиями и сервисами.
    Позволяет накапливать промежуточные данные, логи и итоговый результат.
    """

    schedule: Any
    run: Any
    started_at: float = field(default_factory=time.time)
    data: Dict[str, Any] = field(default_factory=dict)
    logs: List[ScheduleLogEntry] = field(default_factory=list)
    result: Dict[str, Any] = field(default_factory=dict)

    def add_log(self, level: str, message: str, payload: Optional[Dict[str, Any]] = None) -> None:
        self.logs.append(ScheduleLogEntry(time.time(), level, message, payload))

    def set_data(self, key: str, value: Any) -> None:
        self.data[key] = value

    def get_data(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    def set_result(self, **kwargs: Any) -> None:
        self.result.update(kwargs)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schedule_id": getattr(self.schedule, "id", None),
            "run_id": getattr(self.run, "id", None),
            "duration": self.duration,
            "data": self.data,
            "logs": [
                {
                    "timestamp": entry.timestamp,
                    "level": entry.level,
                    "message": entry.message,
                    "payload": entry.payload,
                }
                for entry in self.logs
            ],
            "result": self.result,
        }

    @property
    def duration(self) -> float:
        return time.time() - self.started_at

