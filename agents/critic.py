import json
import logging
from agents.base_agent import BaseAgent
from core.llm_client import LLMClient
from core.models import CriticResult

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Ты — строгий ревьюер карьерных отчётов.
Твой ответ — ТОЛЬКО валидный JSON без markdown и пояснений.

Структура:
{
  "critic_result": {
    "quality_score": 85,
    "quality_score_reason": "Обоснование в 2-3 предложения",
    "warnings": ["замечание1", "замечание2"],
    "is_consistent": true
  }
}

Проверяй:
1. Соответствие зарплат уровню навыков
2. Если declining-навыки занимают приоритетное место в learning_path — фиксируй в warnings. Если declining-навыков нет или они не приоритизированы — это норма, ничего не пиши.
3. Портфолио использует навыки из skill_map (минимум 3)
4. Полнота всех полей
"""


class CriticAgent(BaseAgent):
    name = "critic"

    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    def run(self, context: dict) -> dict:
        role = context["role"]
        logger.info("Проверяю отчёт для роли: %s", role)

        report_data = {
            "role": role,
            "skill_map": context.get("skill_map"),
            "salary_table": context.get("salary_table"),
            "learning_path": context.get("learning_path"),
        }

        user_prompt = f"""Проверь карьерный отчёт для "{role}":

{json.dumps(report_data, ensure_ascii=False, indent=2)}

Найди противоречия, оцени качество. Верни ТОЛЬКО JSON."""

        raw = self.llm.ask_json(SYSTEM_PROMPT, user_prompt)
        critic_result = CriticResult(**raw["critic_result"])
        logger.info("quality_score=%d, is_consistent=%s", critic_result.quality_score, critic_result.is_consistent)
        return {"critic_result": critic_result.model_dump(mode="json")}