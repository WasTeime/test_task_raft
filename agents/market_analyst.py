import logging
from agents.base_agent import BaseAgent
from core.llm_client import LLMClient
from core.models import SkillMap

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = BaseAgent.BASE_SYSTEM + """
Ты — старший аналитик IT-рынка труда.
 
Правила:
- Каждая категория: минимум 3, максимум 4 навыка
- Основные языки роли — всегда "critical"
- infrastructure и frameworks — только самые востребованные
- trend_reason: одна фраза с конкретной причиной. Не ссылайся на конкретные проценты если не уверен в цифре — лучше опиши тенденцию
  Хорошо: "Apple активно переводит экосистему на Swift, доля Objective-C в новых проектах падает"
  Плохо: "вырос на 25% в 2026 году"
- soft_skills — ТОЛЬКО межличностные качества. Git, Agile, Troubleshooting — hard skills, НЕ добавляй в soft_skills
- critical — без этого не возьмут
- important — преимущество перед другими
- nice-to-have — встречается в вакансиях, не обязательно
 
Структура:
{
  "skill_map": {
    "languages": [{"name": "...", "level": "...", "trend": "...", "trend_reason": "..."}],
    "frameworks": [...],
    "infrastructure": [...],
    "soft_skills": [...]
  }
}
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