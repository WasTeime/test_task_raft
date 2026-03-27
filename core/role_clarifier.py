import json
import logging

from core.llm_client import LLMClient

logger = logging.getLogger(__name__)

CLARIFY_SYSTEM = """Определи, является ли строка понятной IT-специальностью.

Ответь ТОЛЬКО валидным JSON:
- Роль понятна: {"suggestions": []}
- Роль непонятна: {"suggestions": ["вариант 1", "вариант 2", "вариант 3"]}

suggestions — 3-5 конкретных IT-ролей с основной технологией в скобках.
Пример: "Frontend Developer (React)", "Backend Developer (Python/Django)", "iOS Developer (Swift)"

Понятная роль: "Backend Python Developer", "iOS Developer (Swift)", "ML Engineer"
Непонятная роль: "программист", "разработчик", "хочу в IT", "программист сайтов"
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