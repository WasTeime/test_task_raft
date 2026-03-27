import logging
from agents.base_agent import BaseAgent
from core.hh_client import fetch_salary_data
from core.llm_client import LLMClient
from core.models import SalaryTable

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = BaseAgent.BASE_SYSTEM + """
Ты — HR-аналитик по зарплатам IT-специалистов в России.
 
Источники:
Россия: career.habr.com, getmatch.ru, hh.ru
Remote/USD: levels.fyi, glassdoor.com
 
Правила:
- Зарплаты в тысячах рублей, remote в USD
- Если в запросе есть реальные данные с hh.ru — используй их как ориентир.
  Но применяй здравый смысл: если цифра явно аномальная для роли
  (например, Junior iOS < 60k или Senior < 150k) — это артефакт выборки,
  скорректируй на основе знания рынка и укажи реалистичное значение.
- sample_size < 5 — данные ненадёжны, опирайся на своё знание рынка.
- Если данных по какому-то грейду нет — оцени самостоятельно на основе соседних грейдов
- remote_usd всегда оценивай самостоятельно — реальных данных по нему нет
- market_trend_reason: 1-2 предложения с конкретной причиной. Не ссылайся на конкретные проценты если не уверен в цифре
  Плохо: "Рост спроса на мобильные приложения"
  Хорошо: "Apple активно развивает экосистему Vision Pro и watchOS — это создаёт новые ниши для разработчиков, количество iOS-вакансий на hh.ru стабильно растёт"
- top_employers: используй список из запроса если он есть, дополни до 3-5 компаний
 
Структура ответа:
moscow и regions_rub в тысячах рублей, remote_usd в долларах.
 
{
  "salary_table": {
    "junior": {"moscow": {"min": 80, "median": 110, "max": 150}, "regions_rub": {"min": 50, "median": 70, "max": 100}, "remote_usd": {"min": 800, "median": 1200, "max": 1800}},
    "middle": {"moscow": {...}, "regions_rub": {...}, "remote_usd": {...}},
    "senior": {"moscow": {...}, "regions_rub": {...}, "remote_usd": {...}},
    "lead": {"moscow": {...}, "regions_rub": {...}, "remote_usd": {...}},
    "market_trend": "growing",
    "market_trend_reason": "...",
    "top_employers": [
      {"name": "Яндекс", "type": "российская", "description": "поисковик и экосистема сервисов"}
    ]
  }
}
"""


def _format_hh_data(hh_data: dict) -> str:
    """Форматирует данные с hh.ru в читаемый текст для user_prompt."""
    if not hh_data:
        return ""

    lines = [
        f"Реальные данные с hh.ru ({hh_data['vacancy_count']['moscow']} вак. Москва, "
        f"{hh_data['vacancy_count']['regions']} вак. Россия):",
    ]

    grades = ["junior", "middle", "senior", "lead"]

    lines.append("\nМосква (тыс. руб., net):")
    for grade in grades:
        stats = hh_data.get("moscow", {}).get(grade)
        if stats:
            lines.append(
                f"  {grade}: min={stats['min']}, median={stats['median']}, "
                f"max={stats['max']} (выборка: {stats['sample_size']} вак.)"
            )
        else:
            lines.append(f"  {grade}: нет данных")

    lines.append("\nРегионы (тыс. руб., net):")
    for grade in grades:
        stats = hh_data.get("regions", {}).get(grade)
        if stats:
            lines.append(
                f"  {grade}: min={stats['min']}, median={stats['median']}, "
                f"max={stats['max']} (выборка: {stats['sample_size']} вак.)"
            )
        else:
            lines.append(f"  {grade}: нет данных")

    if hh_data.get("top_employers"):
        lines.append(f"\nТоп работодателей по числу вакансий: {', '.join(hh_data['top_employers'])}")

    return "\n".join(lines)

class SalaryEstimatorAgent(BaseAgent):
    name = "salary_estimator"

    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    def _compress_skill_map(self, skill_map: dict) -> str:
        """Сжимает skill_map до компактного формата для salary-агента."""
        lines = []
        for category, skills in skill_map.items():
            names = [f"{s['name']} ({s['level']})" for s in skills]
            lines.append(f"{category}: {', '.join(names)}")
        return "\n".join(lines)

    def run(self, context: dict) -> dict:
        role = context["role"]
        skill_map = context["skill_map"]

        logger.info("Оцениваю зарплаты для роли: %s", role)

        hh_data = fetch_salary_data(role)
        hh_context = _format_hh_data(hh_data)

        if hh_context:
            hh_block = f"\n{hh_context}\n"
            logger.info("hh.ru данные получены, передаю в LLM как контекст")
        else:
            hh_block = ""
            logger.info("hh.ru данных нет, LLM работает самостоятельно")

        user_prompt = f"""Специальность: "{role}"

        Навыки:
        {self._compress_skill_map(skill_map)}
        {hh_block}
        Составь таблицу зарплат по грейдам и регионам. Верни ТОЛЬКО JSON."""

        raw = self.llm.ask_json(SYSTEM_PROMPT, user_prompt)
        salary_table = SalaryTable(**raw["salary_table"])
        logger.info("salary_table готов: тренд=%s", salary_table.market_trend)
        return {"salary_table": salary_table.model_dump(mode="json")}