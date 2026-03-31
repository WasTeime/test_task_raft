import json
import logging

from core.llm_client import LLMClient

logger = logging.getLogger(__name__)

CLARIFY_SYSTEM = """Определи, является ли строка понятной IT-специальностью.

Ответь ТОЛЬКО валидным JSON:
- Роль понятна: {"suggestions": []}
- Роль непонятна: {"suggestions": ["вариант 1", "вариант 2", "вариант 3"]}

suggestions — 3-5 конкретных IT-ролей с ОДНИМ основным языком или фреймворком в скобках.
Пример: "Frontend Developer (React)", "Backend Developer (Python)", "iOS Developer (Swift)"
ЗАПРЕЩЕНО: два языка через слэш — не "Backend Developer (Python/Java)", не "Full Stack (JavaScript/Node.js)"
Выбирай самый популярный/востребованный вариант для каждой роли.

Роль без конкретного стека непонятна: "Backend Developer", "Mobile Developer", "Frontend Developer" предложи варианты со стеком.
Понятная роль: "Backend Python Developer", "iOS Developer (Swift)", "ML Engineer"
Непонятная роль: "программист", "разработчик", "хочу в IT", "программист сайтов", "Backend Developer", "Mobile Developer", "Frontend Developer"
"""


def clarify_role(llm: LLMClient, raw_role: str) -> str:
    try:
        result = llm.ask_json(CLARIFY_SYSTEM, f'Роль: "{raw_role}"')
    except ValueError:
        return raw_role

    suggestions = result.get("suggestions", [])
    if not suggestions:
        return raw_role

    print(f'\nРоль "{raw_role}" слишком общая. Выбери специальность:\n')
    for i, s in enumerate(suggestions, 1):
        print(f"  {i}. {s}")
    print(f"  0. Оставить: {raw_role}\n")

    while True:
        try:
            num = int(input("Номер: ").strip())
            if num == 0:
                return raw_role
            if 1 <= num <= len(suggestions):
                return suggestions[num - 1]
        except (ValueError, EOFError):
            pass
        print(f"Введи 0-{len(suggestions)}")

HINT = """
Опиши свой текущий уровень (или нажми Enter чтобы пропустить):

Примеры:
  - "Совсем новичок, никогда не программировал"
  - "Знаю базовый Python (циклы, функции, списки), SQL не знаю"
  - "1 год опыта на PHP, хочу перейти на Python/Django"
  - "Middle Java разработчик, нужно быстро освоить FastAPI"
"""

def clarify_skill_level() -> str:
    print(HINT)
    level = input("Твой уровень: ").strip()
    if not level:
        return ""
    # Убираем суррогатные символы которые могут появиться
    level = level.encode("utf-8", errors="ignore").decode("utf-8")
    return level

GOAL_HINT = """
Опиши что хочешь получить в итоге (или нажми Enter чтобы пропустить):

Примеры:
  - "Устроиться на первую работу джуном"
  - "Разобраться как работают микросервисы"
  - "Научиться оптимизировать запросы к БД"
  - "Повысить грейд до Senior"
  - "Быстро пересесть на новый стек"
"""

def clarify_goal() -> str:
    print(GOAL_HINT)
    goal = input("Твоя цель: ").strip()
    if not goal:
        return ""
    return goal.encode("utf-8", errors="ignore").decode("utf-8")