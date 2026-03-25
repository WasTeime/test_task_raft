import json
import logging
from agents.base_agent import BaseAgent
from core.llm_client import LLMClient
from core.models import CriticResult

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Ты — строгий ревьюер карьерных отчётов.
Твой ответ — ТОЛЬКО валидный JSON без markdown и пояснений.

Оценивай по 4 критериям, каждый максимум 25 баллов (итого 100):
1. salary_market_match (0-25) — зарплаты соответствуют реальному рынку и уровню навыков
2. skills_consistency (0-25) — навыки в skill_map логичны, нет противоречий между трендами и приоритетами
3. learning_path_quality (0-25) — план обучения реалистичен, ресурсы реальные, milestones конкретные
4. portfolio_relevance (0-25) — портфолио-проект использует минимум 3 навыка из skill_map

quality_score = сумма всех четырёх баллов.

Структура:
{
  "critic_result": {
    "score_breakdown": {
      "salary_market_match": {"score": 20, "reason": "Junior Москва немного завышен"},
      "skills_consistency": {"score": 24, "reason": "Все навыки актуальны"},
      "learning_path_quality": {"score": 18, "reason": "Ресурсы без реальных URL"},
      "portfolio_relevance": {"score": 24, "reason": "Покрывает 4 навыка из skill_map"}
    }
    "quality_score": 85,
    "quality_score_reason": "Зарплаты немного завышены для Junior. План обучения реалистичный, ресурсы актуальные. Портфолио хорошо покрывает навыки.",
    "warnings": ["Junior Москва max 200 тыс. выглядит завышенно для начального уровня"],
    "is_consistent": true
  }
}

Правила:
- warnings только если есть реальная проблема — declining-навык в приоритетах, пустые поля, нереальные зарплаты
- is_consistent: false если quality_score < 60 или критические противоречия
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