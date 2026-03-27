import json
import logging
from agents.base_agent import BaseAgent
from core.llm_client import LLMClient
from core.models import CriticResult

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = BaseAgent.BASE_SYSTEM + """
Ты — строгий ревьюер карьерных отчётов. Твоя задача — найти проблемы, а не похвалить.
25/25 = идеально (редкость). 20-24 = норма. Оценка 95+ подозрительна.
 
REASON формула: ТОЛЬКО проблемы + минус N баллов. Если проблем нет — пиши "норма".
ЗАПРЕЩЕНО перечислять что правильно. Каждое предложение в reason должно содержать "минус" или "норма".
ВАЖНО: если reason = "норма" — score обязан быть 25. Нельзя писать "норма" и ставить 24.
Снижаешь балл — обязан написать конкретную причину с "минус N баллов".
Пиши ТОЛЬКО о проблемах. Если всё хорошо — одно слово "норма". Не перечисляй что правильно.
Плохо: "Junior Москва 80-150k — корректно. Middle 100-220k — норма. Lead remote max 9000 USD завышен — минус 1 балл"
Хорошо: "Lead remote max 9000 USD завышен для рынка 2026 — минус 1 балл"
 
КРИТЕРИИ (каждый 0-25, итого 100):
 
1. salary_market_match (0-25): Junior min < 80? Remote max завышен? Регионы не 60-70%? Грейды пересекаются? Только нарушения.

2. skills_consistency (0-25): Меньше 3 языков? Declining = critical? soft_skills не межличностные? trend_reason без факта? Только нарушения.

3. learning_path_quality (0-25): duration_days не сходится? Path содержит "понимаешь/изучаешь"? Topics содержат soft skills? Milestone не "Могу..."? Gap без деталей? Только нарушения.

4. portfolio_relevance (0-25): Название абстрактное? Problem не боль? user_stories не "делаю→вижу"? Пустые поля? Только нарушения.
 
WARNINGS: только реальные проблемы, максимум 3-5. Одно предложение без конкретных дней.
Плохо: "SwiftUI основы — 1-2 недели слишком оптимистично, реальный срок 2-3 недели"
Хорошо: "Gap-анализ: quick_wins содержат нереалистичные сроки для новичка, предложи реалистичные по твоему мнению и среднему"
Не добавляй в warnings: отсутствие GitHub ссылок, метрики покрытия навыков, детали тестов — это не критичные проблемы.
 
is_consistent: false если score < 60.
 
Структура:
{
  "critic_result": {
    "score_breakdown": {
      "salary_market_match": {"score": 22, "reason": "..."},
      "skills_consistency": {"score": 23, "reason": "..."},
      "learning_path_quality": {"score": 19, "reason": "..."},
      "portfolio_relevance": {"score": 21, "reason": "..."}
    },
    "quality_score": 85,
    "quality_score_reason": "...",
    "warnings": ["..."],
    "is_consistent": true
  }
}

JSON должен содержать все поля: score_breakdown, quality_score, quality_score_reason: только главные проблемы через запятую. Без похвалы. Максимум 2 предложения., warnings (список строк), is_consistent (bool)
"""


class CriticAgent(BaseAgent):
    name = "critic"

    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    def _compress_for_critic(self, context: dict) -> str:
        """Сжимает отчёт для критика: убирает trend_reason, ресурсы, описания проектов."""
        role = context["role"]
        skill_map = context["skill_map"]
        salary = context["salary_table"]
        lp = context["learning_path"]

        # Навыки — компактно
        skills_lines = []
        for cat, skills in skill_map.items():
            items = [f"{s['name']} ({s['level']}, {s['trend']})" for s in skills]
            skills_lines.append(f"{cat}: {', '.join(items)}")

        # Зарплаты — без indent
        salary_compact = json.dumps(salary, ensure_ascii=False, separators=(',', ':'))

        # Learning path — только ключевое
        phases_lines = []
        for p in lp["phases"]:
            phases_lines.append(
                f"--- {p['name']} ({p['duration_days']}д) ---\n"
                f"topics: {p['topics']}\n"
                f"path: {p['path']}\n"
                f"milestone: {p['milestone']}\n"
                f"projects: {[pr['name'] + ': ' + pr['description'] for pr in p['practice_projects']]}"
            )

        # Gap analysis
        gap = lp.get("gap_analysis", {})
        gap_text = f"quick_wins: {gap.get('quick_wins', [])}\nlong_term: {gap.get('long_term', [])}"

        # Portfolio
        portfolio = json.dumps(lp.get("portfolio_project", {}), ensure_ascii=False, separators=(',', ':'))

        return f"""Роль: {role}

        Навыки:
        {chr(10).join(skills_lines)}
    
        Зарплаты:
        {salary_compact}
    
        План обучения:
        {chr(10).join(phases_lines)}
    
        Gap-анализ:
        {gap_text}
    
        Портфолио:
        {portfolio}"""

    def run(self, context: dict) -> dict:
        role = context["role"]
        logger.info("Проверяю отчёт для роли: %s", role)

        compressed = self._compress_for_critic(context)

        user_prompt = f"""Проверь карьерный отчёт для "{context['role']}":

        {compressed}

        Найди только реальные противоречия. Не придирайся к мелочам.
        Верни ТОЛЬКО JSON. JSON должен содержать все поля: score_breakdown, quality_score, quality_score_reason: только главные проблемы через запятую. Без похвалы. Максимум 2 предложения., warnings (список строк, максимум 5), is_consistent (bool)."""

        raw = self.llm.ask_json(SYSTEM_PROMPT, user_prompt)
        critic_result = CriticResult(**raw["critic_result"])
        logger.info("quality_score=%d, is_consistent=%s", critic_result.quality_score, critic_result.is_consistent)
        return {"critic_result": critic_result.model_dump(mode="json")}