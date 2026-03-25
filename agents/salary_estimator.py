import json
import logging
from agents.base_agent import BaseAgent
from core.llm_client import LLMClient
from core.models import SalaryTable

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Ты — HR-аналитик по зарплатам IT-специалистов в России.
Ориентируйся на актуальные данные 2025-2026 года с этих источников:
Источники для российских зарплат:
- career.habr.com — самый точный срез IT-рынка РФ
- getmatch.ru — реальные офферы с цифрами
- hh.ru — массовый рынок

Источники для зарубежных (remote USD):
- levels.fyi — реальные офферы в крупных компаниях
- glassdoor.com — средние по рынку
- stackoverflow.com/survey — ежегодный опрос разработчиков

Указывай реальные рыночные цифры основываясь на этих источниках.
Не занижай и не завышай — данные должны совпадать с тем что видит кандидат на этих сайтах.

Данные должны отражать реальный рынок, не занижай и не завышай вилки.
Твой ответ — ТОЛЬКО валидный JSON без markdown и пояснений.

Структура:
{
  "salary_table": {
    "junior":  {"moscow": {"min": 80,  "median": 110, "max": 150}, "regions_rub": {"min": 50, "median": 70,  "max": 100}, "remote_usd": {"min": 800,  "median": 1200, "max": 1800}},
    "middle":  {"moscow": {"min": 150, "median": 210, "max": 280}, "regions_rub": {"min": 90, "median": 140, "max": 200}, "remote_usd": {"min": 2000, "median": 3000, "max": 4500}},
    "senior":  {"moscow": {"min": 280, "median": 370, "max": 480}, "regions_rub": {"min": 180,"median": 250, "max": 350}, "remote_usd": {"min": 4000, "median": 5500, "max": 7500}},
    "lead":    {"moscow": {"min": 400, "median": 550, "max": 750}, "regions_rub": {"min": 250,"median": 350, "max": 500}, "remote_usd": {"min": 5500, "median": 7500, "max": 10000}},
    "market_trend": "growing",
    - market_trend_reason: 1-2 предложения с конкретными причинами роста/падения спроса.
      Плохо: "Рост спроса на мобильные приложения"
      Хорошо: "Количество iOS-приложений в App Store выросло на 12% в 2024 году, Apple активно развивает экосистему Vision Pro и watchOS — это создаёт новые ниши для разработчиков"
    "top_employers": ["Компания1", "Компания2", "Компания3"]
  }
}

- Зарплаты в тысячах рублей, remote в USD
- market_trend: "growing" | "stable" | "declining"
- top_employers: 3-5 компаний, mix российских и зарубежных.
Для каждой: name, type (российская/зарубежная), description (3-5 слов чем занимается).
Структура:
{
    "top_employers": [
      {"name": "Яндекс", "type": "российская", "description": "поисковик и экосистема сервисов"},
      {"name": "Spotify", "type": "зарубежная", "description": "стриминг музыки"},
      {"name": "Тинькофф", "type": "российская", "description": "онлайн-банк"}
    ]
}
"""


class SalaryEstimatorAgent(BaseAgent):
    name = "salary_estimator"

    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    def run(self, context: dict) -> dict:
        role = context["role"]
        skill_map = context["skill_map"]
        logger.info("Оцениваю зарплаты для роли: %s", role)

        user_prompt = f"""Специальность: "{role}"

Карта навыков:
{json.dumps(skill_map, ensure_ascii=False, indent=2)}

Составь таблицу зарплат по грейдам и регионам. Верни ТОЛЬКО JSON."""

        raw = self.llm.ask_json(SYSTEM_PROMPT, user_prompt)
        salary_table = SalaryTable(**raw["salary_table"])
        logger.info("salary_table готов: тренд=%s", salary_table.market_trend)
        return {"salary_table": salary_table.model_dump(mode="json")}