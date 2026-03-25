import logging
from agents.base_agent import BaseAgent
from core.llm_client import LLMClient
from core.models import SkillMap

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Ты — старший аналитик IT-рынка труда 2025-2026 года.
Твой ответ — ТОЛЬКО валидный JSON, без markdown-блоков, без пояснений.

Структура ответа:
{
  "skill_map": {
    "languages": [{"name": "Python", "level": "critical", "trend": "growing"}],
    "frameworks": [...],
    "infrastructure": [...],
    "soft_skills": [...]
  }
}

Правила:
- level: только "critical" | "important" | "nice-to-have"
- trend: только "growing" | "stable" | "declining"
- Минимум 3 навыка в каждой категории, максимум 4
- Swift, Python, JavaScript и другие основные языки роли — всегда "critical", никогда иначе
- infrastructure и frameworks: максимум 4 навыка — только самые востребованные, остальное убирай
- trend_reason: одна фраза почему такой тренд
  Пример: {"name": "Objective-C", "level": "nice-to-have", "trend": "declining", "trend_reason": "Apple активно переводит экосистему на Swift начиная с 2014 года"}
- Данные актуальны для рынка 2025-2026 (hh.ru, habr career, LinkedIn)
- critical — без этого навыка не возьмут на работу
- important — даёт преимущество перед другими кандидатами
- nice-to-have — упомянуто в вакансиях, но не обязательно
- growing — спрос растёт последние 12 месяцев
- declining — спрос падает, технология устаревает
- soft_skills — только межличностные и рабочие качества: коммуникация, работа в команде, управление временем. Git, Agile, Troubleshooting — это hard skills, их НЕ добавляй в soft_skills
"""


class MarketAnalystAgent(BaseAgent):
    name = "market_analyst"

    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    def run(self, context: dict) -> dict:
        role = context["role"]
        logger.info("Анализирую рынок для роли: %s", role)

        user_prompt = f"""Проанализируй рынок труда для специальности: "{role}"

        Требования:
        - Выдели навыки которые реально встречаются в вакансиях на hh.ru и habr career прямо сейчас
        - languages: языки программирования используемые в этой роли
        - frameworks: фреймворки и библиотеки специфичные для этой роли
        - infrastructure: инструменты деплоя, CI/CD, облака, IDE специфичные для этой роли
        - soft_skills: только межличностные качества проверяемые на собеседовании

        Верни ТОЛЬКО JSON."""

        raw = self.llm.ask_json(SYSTEM_PROMPT, user_prompt)
        skill_map = SkillMap(**raw["skill_map"])
        logger.info("skill_map готов: %d языков, %d фреймворков", len(skill_map.languages), len(skill_map.frameworks))
        return {"skill_map": skill_map.model_dump(mode="json")}