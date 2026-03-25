import logging
from agents.base_agent import BaseAgent
from core.llm_client import LLMClient
from core.models import SkillMap

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Ты — старший аналитик IT-рынка труда.
Твой ответ — ТОЛЬКО валидный JSON, без markdown-блоков, без пояснений.
Структура ответа:

{
  "skill_map": {
    "languages": [
      {"name": "Python", "level": "critical", "trend": "growing"}
    ],
    "frameworks": [...],
    "infrastructure": [...],
    "soft_skills": [...]
  }
}

Правила:
- level: только "critical" | "important" | "nice-to-have"
- trend: только "growing" | "stable" | "declining"
- Минимум 3 навыка в каждой категории
"""


class MarketAnalystAgent(BaseAgent):
    name = "market_analyst"

    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    def run(self, context: dict) -> dict:
        role = context["role"]
        logger.info("Анализирую рынок для роли: %s", role)

        user_prompt = f"""Проанализируй рынок труда для специальности: "{role}"

Выдели: languages, frameworks, infrastructure, soft_skills.
Для каждого навыка: level (critical/important/nice-to-have) и trend (growing/stable/declining).
Верни ТОЛЬКО JSON."""

        raw = self.llm.ask_json(SYSTEM_PROMPT, user_prompt)
        skill_map = SkillMap(**raw["skill_map"])
        logger.info("skill_map готов: %d языков, %d фреймворков", len(skill_map.languages), len(skill_map.frameworks))
        return {"skill_map": skill_map.model_dump(mode="json")}