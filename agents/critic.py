import json
import logging
from agents.base_agent import BaseAgent
from core.llm_client import LLMClient
from core.models import CriticResult

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = BaseAgent.BASE_SYSTEM + """
Ты — строгий ревьюер карьерных отчётов. Задача — найти проблемы, не хвалить.
25/25 = идеально (редкость). 20-24 = норма. 95+ подозрительна.

REASON: ТОЛЬКО проблемы + "минус N баллов". Нет проблем → "норма".
"норма" = строго 25. Снижаешь — обязан указать причину.

Тебе передаётся skill_level. Все проверки сложности — относительно него.

КРИТЕРИИ (каждый 0-25):

1. salary_market_match: Junior min < 80? Remote max завышен? Регионы не 60-70%? Грейды пересекаются?

2. skills_consistency: < 3 языков? Declining = critical? soft_skills не межличностные? trend_reason без факта?

3. learning_path_quality:

   ПОТОЛОК СЛОЖНОСТИ (главное):
   Тест для каждой темы: "Может ли человек с данным skill_level освоить ЭТО за неделю?" Нет → слишком сложно.
   Продвинутый инструмент = свой lifecycle + >1 недели на освоение.

   Новичок (пустой / < 1 года):
   - Foundation содержит не только язык и простое хранение → минус 3-5. Фреймворк в Foundation = ошибка (кроме мобилки где без UI-фреймворка нельзя ничего).
   - Practice: больше 1 крупной концепции сверх фреймворка и тестов → минус 2-3.
   - Portfolio вводит новые технологии → минус 2-3.
   - Больше 5 технологий за курс → минус 2.

   Опытный (1+ год): фреймворк в Foundation ОК. Practice > 2 крупных → минус 2. Не штрафуй за известное.

   PATH: "понимаешь/изучаешь/применяешь" → минус 1-2. Шаг с >1 концепцией → минус 1.
   СТРУКТУРА: duration != 30, topics с soft skills, milestone без "Могу", projects != 3, resources < 2 → минус 1-2 каждое.
   GAP: нереалистичные сроки для skill_level → минус 1-2. long_term не по порядку → минус 1.

4. portfolio_relevance: Абстрактное название? Problem не боль? user_stories не "делаю→вижу"? Нереализуем за 30 дней? Продвинутые инструменты для новичка?

WARNINGS: макс 3-5, по одному предложению. Приоритет: сложность vs уровень > сроки > структура.

is_consistent: false если score < 60.

{
  "critic_result": {
    "score_breakdown": {
      "salary_market_match": {"score": 0, "reason": "..."},
      "skills_consistency": {"score": 0, "reason": "..."},
      "learning_path_quality": {"score": 0, "reason": "..."},
      "portfolio_relevance": {"score": 0, "reason": "..."}
    },
    "quality_score": 0,
    "quality_score_reason": "Только проблемы. Макс 2 предложения.",
    "warnings": ["..."],
    "is_consistent": true
  }
}
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

        skill_level = context.get("skill_level", "")
        skill_level_block = f"\nУровень пользователя: {skill_level}\n" if skill_level else ""

        return f"""Роль: {role}
        {skill_level_block}

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
        critic_data = raw["critic_result"]

        # Пересчитываем quality_score из breakdown
        breakdown = critic_data.get("score_breakdown", {})
        computed_score = sum(
            v["score"] for v in breakdown.values() if isinstance(v, dict) and "score" in v
        )
        critic_data["quality_score"] = computed_score
        critic_data["is_consistent"] = computed_score >= 60

        critic_result = CriticResult(**critic_data)
        logger.info("quality_score=%d, is_consistent=%s", critic_result.quality_score, critic_result.is_consistent)
        return {"critic_result": critic_result.model_dump(mode="json")}