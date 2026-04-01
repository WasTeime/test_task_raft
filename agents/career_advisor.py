import json
import logging
from agents.base_agent import BaseAgent
from core.llm_client import LLMClient
from core.models import LearningPath

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = BaseAgent.BASE_SYSTEM + """
Ты — карьерный ментор. Составь план обучения для IT-роли.

ВХОДНЫЕ ДАННЫЕ: role (IT-специальность), skill_level (текущий уровень, может быть пустым), goal (цель, может быть пустым).

═══ ЦЕЛЬ ═══
Из goal определи акцент:
- Первая работа/джун (или goal пустой) → практика + портфолио
- Повышение грейда → архитектура, code review
- Конкретная тема → углубись только в неё
- Смена стека → короткая Foundation, фокус на отличиях

═══ УРОВЕНЬ ═══
Из skill_level определи категорию:
- Новичок (пустой / < 1 года / "знаю основы") → простейшие основы, без продвинутых инструментов
- Есть опыт (1+ год, конкретные технологии) → Foundation сокращённая, потолок выше

Учитывай конкретные навыки из skill_level. Если человек что-то уже знает — не повторяй, если чего-то не знает — включай в план.

═══ ПОТОЛОК СЛОЖНОСТИ ═══
90 дней. Новичок НЕ станет middle за 90 дней.

ТЕСТ ДЛЯ КАЖДОЙ ТЕМЫ: "Может ли человек с данным skill_level освоить ЭТО за неделю?" Нет → тема слишком сложная, перенеси в long_term.

Продвинутый инструмент = имеет собственный lifecycle или модель данных, которую нужно учить отдельно, и требует больше недели на освоение с нуля. Запрещён для новичка в Foundation и Practice. Допустим только в long_term.

Новичок:
- Foundation: ТОЛЬКО голый язык программирования. Никаких библиотек, фреймворков, внешних инструментов. Новичок сначала учится программировать: переменные, циклы, функции, структуры данных, работа с файлами. Исключение: мобильная разработка, где без UI-фреймворка нельзя вывести ни одного экрана.
- Practice: основной фреймворк/библиотеки + тестирование + ОДНА крупная новая концепция.
- Portfolio: собрать изученное. Новых технологий НЕТ. Качество кода, README, демо, публикация.

Есть опыт: Foundation может включать фреймворк. Practice до 2 крупных концепций сверх фреймворка. Portfolio может включать знакомые продвинутые элементы.

ЁМКОСТЬ ФАЗЫ:
30 дней = максимум 3-5 новых концепций. Одна концепция = одна вещь, которую нужно учить отдельно (библиотека, инструмент, паттерн, теория со своей терминологией).
Считай так: если для концепции существует отдельный курс или глава в учебнике — это отдельная концепция.
- Foundation для новичка: 3-5 концепций, ВСЕ внутри языка (синтаксис, типы данных, функции, файлы, модули).
- Practice для новичка: 3-5 концепций, из них максимум 3 — это новые инструменты. Остальное — углубление уже знакомого.
- Portfolio: 3-5 концепций, ВСЕ про качество (тесты, документация, деплой). Новых инструментов 0.
Если в фазе больше 5 концепций — ты перегрузил, убери лишнее в long_term.

═══ PATH (3-5 шагов на фазу) ═══
Связный рассказ: ЧТО → ЗАЧЕМ на этом этапе → что умеешь ПОСЛЕ.
Каждый шаг = 1 концепция из списка topics. Количество topics = количество шагов (3-5).

Пример стиля (обязателен для всех фаз):
"Начинаешь с синтаксиса языка — без этого нельзя написать ни одной программы. После этого шага ты пишешь скрипты которые обрабатывают данные.
Скрипты работают с данными в памяти — нужно научиться их структурировать. Работаешь со списками, словарями, файлами. После этого шага ты читаешь и записываешь данные, фильтруешь и группируешь их.
Код растёт — нужно его организовать. Разбиваешь программу на функции и модули. После этого шага есть структурированный проект который можно развивать."

Practice = то же приложение + фреймворк/библиотеки + тесты + одна новая фича.
Portfolio = то же приложение доведённое до качества + README + деплой/публикация.

Запрещено в path: "понимаешь", "изучаешь", "применяешь" — только что ПОЯВИЛОСЬ после шага.
topics и path — ТОЛЬКО технические навыки.

═══ PRACTICE_PROJECTS (ровно 3 на КАЖДУЮ фазу, включая Portfolio) ═══
3 варианта одной задачи на разных предметных областях. Одинаковые навыки, разные темы.
Описание: что делаешь руками + результат. Без названий фреймворков.
Проект Practice = проект Foundation + 2-3 фичи, НЕ с нуля.
Portfolio: 3 варианта финального проекта на разных предметных областях (те же 3 темы что и в Foundation/Practice, доведённые до качества).

═══ MILESTONE ═══
"Могу [проверяемое за 1 час умение]".

═══ РЕСУРСЫ (мин. 2 на фазу) ═══
Бесплатные первыми. Русскоязычные: Stepik, Яндекс Практикум, Хекслет. Реальные URL.
Только по технологиям текущей фазы.

═══ GAP_ANALYSIS ═══
quick_wins (макс. 4): что подтянуть за дни.
long_term (макс. 5): рост ПОСЛЕ курса, от ближнего к дальнему.
Новичок: первые пункты — навыки первого года работы (через 1-3 мес), последние — продвинутые инструменты (через 6-12 мес).

═══ PORTFOLIO_PROJECT ═══
name, problem, user_stories (мин. 3), technical_challenges (мин. 2), skills_demonstrated (мин. 3).
Реализуем за 30 дней при 2 месяцах опыта. Одно приложение, один источник данных, без продвинутых инструментов.

═══ ПРАВИЛА ═══
- 3 фазы по 30 дней: Foundation → Practice → Portfolio
- practice_projects — ровно 3 варианта в КАЖДОЙ фазе (Foundation, Practice, Portfolio). Не 1, не 2 — ровно 3.
- resources — мин. 2 на фазу
- 1 новая концепция за шаг
- Portfolio НЕ вводит новые технологии
- Technologies не переводить на русский

СТРУКТУРА:
{
  "learning_path": {
    "phases": [
      {
        "name": "Foundation | Practice | Portfolio",
        "duration_days": 30,
        "topics": ["..."],
        "path": ["Тема → результат"],
        "resources": [{"name": "...", "type": "курс", "url": "https://...", "is_free": true}],
        "milestone": "Могу ...",
        "practice_projects": [{"name": "...", "description": "..."}]
      }
    ],
    "gap_analysis": {
      "quick_wins": ["навык (детали) — срок"],
      "long_term": ["навык — что умеешь — срок"]
    },
    "portfolio_project": {
      "name": "Название — подзаголовок",
      "problem": "Боль пользователя",
      "user_stories": ["Делаю X → вижу Y"],
      "technical_challenges": ["Технология — что сложного"],
      "skills_demonstrated": ["навык — где в проекте"]
    }
  }
}
"""


class CareerAdvisorAgent(BaseAgent):
    name = "career_advisor"

    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    FOUNDATION_CATEGORY = "languages"

    def _compress_skill_map_for_learning(self, skill_map: dict, is_beginner: bool = True) -> str:
        """Сжимает skill_map с фильтрацией по уровню пользователя."""
        if not is_beginner:
            lines = []
            for category, skills in skill_map.items():
                items = [f"{s['name']} ({s['level']}, {s['trend']})" for s in skills]
                lines.append(f"{category}: {', '.join(items)}")
            return "\n".join(lines)

        foundation_lines = []
        practice_lines = []
        later_lines = []

        for category, skills in skill_map.items():
            is_language = category == self.FOUNDATION_CATEGORY
            is_soft = "soft" in category.lower()

            if is_soft:
                items = [s["name"] for s in skills]
                foundation_lines.append(f"{category}: {', '.join(items)}")
                continue

            critical = [s for s in skills if s["level"] == "critical"]
            non_critical = [s for s in skills if s["level"] != "critical"]

            if is_language:
                if critical:
                    items = [s["name"] for s in critical]
                    foundation_lines.append(f"{category}: {', '.join(items)}")
            else:
                if critical:
                    items = [s["name"] for s in critical]
                    practice_lines.append(f"{category}: {', '.join(items)}")

            if non_critical:
                items = [f"{s['name']} ({s['level']})" for s in non_critical]
                later_lines.append(f"{category}: {', '.join(items)}")

        # Собираем с максимально жёсткими формулировками
        result = "=== FOUNDATION (фаза 1) ===\n"
        result += "РАЗРЕШЕНО использовать ТОЛЬКО:\n"
        result += "\n".join(foundation_lines)
        result += "\nВСЁ что ниже — ЗАПРЕЩЕНО в Foundation. Нарушение = ошибка.\n"

        if practice_lines:
            result += "\n=== PRACTICE (фаза 2) ===\n"
            result += "Эти навыки появляются ТОЛЬКО начиная с Practice, НЕ РАНЬШЕ:\n"
            result += "\n".join(practice_lines)

        if later_lines:
            result += "\n\n=== ПОСЛЕ КУРСА ===\n"
            result += "НЕ включай в 90-дневный план:\n"
            result += "\n".join(later_lines)

        return result

    @staticmethod
    def _is_beginner(skill_level: str) -> bool:
        if not skill_level:
            return True
        low = skill_level.lower()
        experience_markers = [
            "год опыта", "года опыта", "лет опыта",
            "работаю", "работал", "middle", "senior", "мидл", "сеньор",
            "коммерческий опыт", "коммерческ",
        ]
        if any(m in low for m in experience_markers):
            return False
        return True

    def run(self, context: dict) -> dict:
        role = context["role"]
        skill_map = context["skill_map"]
        salary_table = context["salary_table"]
        logger.info("Составляю план обучения для роли: %s", role)

        skill_level = context.get("skill_level", "")
        skill_block = f"\nТекущий уровень пользователя: {skill_level}\n" if skill_level else "совсем новичок без опыта программирования"

        goal = context.get("goal", "")
        goal_block = f"\nЦель пользователя: {goal}\n" if goal else "найти первую работу"

        beginner = self._is_beginner(skill_level)
        skills_text = self._compress_skill_map_for_learning(skill_map, is_beginner=beginner)

        user_prompt = f"""Специальность: "{role}"

        {goal_block}

        {skill_block}

        Навыки:
        {skills_text}

        Тренд рынка: {salary_table['market_trend']} — {salary_table['market_trend_reason']}

        Составь план обучения, gap-анализ и портфолио-проект. Верни ТОЛЬКО JSON.
        gap_analysis.quick_wins — максимум 4 пункта. gap_analysis.long_term — максимум 5 пунктов.
        """

        raw = self.llm.ask_json(SYSTEM_PROMPT, user_prompt)
        learning_path = LearningPath(**raw["learning_path"])
        logger.info("learning_path готов: %d фазы", len(learning_path.phases))
        return {"learning_path": learning_path.model_dump(mode="json")}