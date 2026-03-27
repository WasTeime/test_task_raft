import logging
import socket
import statistics
import time
from collections import Counter

import requests

logger = logging.getLogger(__name__)

HH_API_URL = "https://api.hh.ru/vacancies"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://hh.ru/",
    "Origin": "https://hh.ru",
}

AREA_MOSCOW = 1
AREA_RUSSIA = 113

EXPERIENCE_TO_GRADE = {
    "noExperience": "junior",
    "between1And3": "middle",
    "between3And6": "senior",
    "moreThan6": "lead",
}


def _fetch_vacancies_page(
    session: requests.Session, query: str, area: int, page: int, per_page: int = 100
) -> dict:
    """Запрашивает одну страницу вакансий с hh.ru."""
    params = {
        "text": query,
        "area": area,
        "currency": "RUR",
        "only_with_salary": True,
        "per_page": per_page,
        "page": page,
    }
    logger.debug("Отправляю запрос к hh.ru area=%d page=%d", area, page)
    response = session.get(HH_API_URL, params=params, timeout=(5, 30))
    logger.debug("Ответ получен: %d", response.status_code)
    response.raise_for_status()
    return response.json()


def _extract_salary_rub(salary: dict) -> tuple[float | None, float | None]:
    """Извлекает min и max зарплату в рублях. Переводит gross в net."""
    if not salary or salary.get("currency") != "RUR":
        return None, None

    tax_factor = 0.87 if salary.get("gross") else 1.0
    raw_min = salary.get("from")
    raw_max = salary.get("to")

    sal_min = raw_min * tax_factor if raw_min else None
    sal_max = raw_max * tax_factor if raw_max else None

    return sal_min, sal_max


def _midpoint(sal_min: float | None, sal_max: float | None) -> float | None:
    """Считает среднее между min и max, или возвращает любое из двух."""
    if sal_min and sal_max:
        return (sal_min + sal_max) / 2
    return sal_min or sal_max


def _compute_stats(values: list[float]) -> dict | None:
    """Считает min/median/max в тысячах рублей."""
    if not values:
        return None
    return {
        "min": round(min(values) / 1000, 1),
        "median": round(statistics.median(values) / 1000, 1),
        "max": round(max(values) / 1000, 1),
    }


def _collect_vacancies(
    session: requests.Session, query: str, area: int, max_pages: int
) -> list[dict]:
    """Собирает вакансии постранично."""
    items = []
    for page in range(max_pages):
        data = _fetch_vacancies_page(session, query, area, page)
        page_items = data.get("items", [])
        if not page_items:
            break
        items.extend(page_items)
        if page < max_pages - 1:
            time.sleep(0.3)
    return items


def _parse_vacancies(items: list[dict]) -> tuple[dict[str, list[float]], Counter]:
    """
    Парсит список вакансий.
    Возвращает:
      - grade_salaries: грейд -> список зарплат
      - employer_counter: счётчик работодателей
    """
    grade_salaries: dict[str, list[float]] = {
        "junior": [], "middle": [], "senior": [], "lead": [],
    }
    employer_counter: Counter = Counter()

    for vacancy in items:
        experience_id = (vacancy.get("experience") or {}).get("id")
        grade = EXPERIENCE_TO_GRADE.get(experience_id)
        if not grade:
            continue

        salary = vacancy.get("salary")
        sal_min, sal_max = _extract_salary_rub(salary)
        mid = _midpoint(sal_min, sal_max)

        if mid and 20_000 <= mid <= 1_000_000:
            grade_salaries[grade].append(mid)

        employer_name = (vacancy.get("employer") or {}).get("name")
        if employer_name:
            employer_counter[employer_name] += 1

    return grade_salaries, employer_counter


def fetch_salary_data(role: str, max_pages: int = 3) -> dict:
    """
    Запрашивает вакансии по роли на hh.ru и возвращает:
    - зарплаты по грейдам для Москвы и регионов (тыс. руб.)
    - топ работодателей по количеству вакансий

    Формат возврата:
    {
        "source": "hh.ru",
        "vacancy_count": {"moscow": 180, "regions": 420},
        "moscow": {
            "junior": {"min": 80.0, "median": 110.0, "max": 150.0, "sample_size": 25},
            ...
        },
        "regions": {
            "junior": {...},
            ...
        },
        "top_employers": ["Яндекс", "Сбер", "VK", "Тинькофф", "Avito"]
    }

    Если данных нет или hh.ru недоступен — возвращает {}.
    """
    logger.info("Запрашиваю данные с hh.ru для роли: %s", role)

    try:
        session = requests.Session()
        session.headers.update(HEADERS)

        moscow_items = _collect_vacancies(session, role, AREA_MOSCOW, max_pages)
        russia_items = _collect_vacancies(session, role, AREA_RUSSIA, max_pages)

        moscow_grades, moscow_employers = _parse_vacancies(moscow_items)
        russia_grades, russia_employers = _parse_vacancies(russia_items)

        def build_grade_stats(grade_salaries: dict[str, list[float]]) -> dict:
            result = {}
            for grade, values in grade_salaries.items():
                stats = _compute_stats(values)
                if stats:
                    stats["sample_size"] = len(values)
                    result[grade] = stats
            return result

        moscow_stats = build_grade_stats(moscow_grades)
        regions_stats = build_grade_stats(russia_grades)

        if not moscow_stats and not regions_stats:
            logger.warning("hh.ru: нет данных по грейдам для роли '%s'", role)
            return {}

        combined_employers = moscow_employers + russia_employers
        top_employers = [name for name, _ in combined_employers.most_common(5)]

        logger.info(
            "hh.ru: Москва %d вак., Россия %d вак., грейды Москва: %s, регионы: %s",
            len(moscow_items),
            len(russia_items),
            list(moscow_stats.keys()),
            list(regions_stats.keys()),
        )

        return {
            "source": "hh.ru",
            "vacancy_count": {
                "moscow": len(moscow_items),
                "regions": len(russia_items),
            },
            "moscow": moscow_stats,
            "regions": regions_stats,
            "top_employers": top_employers,
        }

    except requests.RequestException as e:
        logger.warning("hh.ru недоступен: %s. Агент работает без реальных данных.", e)
        return {}