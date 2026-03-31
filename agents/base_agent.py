from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    name: str = "base_agent"

    BASE_SYSTEM = """Твой ответ — ТОЛЬКО валидный JSON. Без markdown-блоков, без пояснений, без текста до или после JSON.
    Отвечай ТОЛЬКО на русском языке. Никаких иероглифов или символов других языков.
    Текущий год — 2026.

    ENUM-ЗНАЧЕНИЯ (используй строго эти):
    - level: "critical" | "important" | "nice-to-have"
    - trend: "growing" | "stable" | "declining"
    
    ═══ ЯЗЫК ═══
    Весь текст только на русском. Названия технологий не переводи (Swift, Core Data, Django).
    Абстрактные термины заменяй конкретными: не "хранилище" — а "Core Data" или "SQLite", не "сервер" — а "Django backend" или "FastAPI сервис".
    """

    @abstractmethod
    def run(self, context: dict) -> dict:
        ...

    def __repr__(self) -> str:
        return f"<Agent: {self.name}>"