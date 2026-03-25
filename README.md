# Career Market Analyzer

Мультиагентная система анализа карьерного рынка IT. Принимает название специальности и возвращает структурированный карьерный отчёт: карту навыков, зарплатную таблицу, план обучения и оценку качества.

```bash
python main.py --role "Backend Python Developer"
```

---

## Структура проекта

```
career-analyzer/
├── agents/
│   ├── base_agent.py          # Абстрактный BaseAgent (ABC)
│   ├── market_analyst.py      # Агент 1: карта навыков
│   ├── salary_estimator.py    # Агент 2: зарплатная таблица
│   ├── career_advisor.py      # Агент 3: план обучения
│   └── critic.py              # Агент 4: верификация
├── core/
│   ├── pipeline.py            # Оркестратор агентов
│   ├── llm_client.py          # Обёртка над Anthropic SDK (retry, валидация JSON)
│   └── models.py              # Pydantic-схемы выходных данных
├── output/
│   └── report_writer.py       # Сохранение report.json и report.md
├── examples/
│   ├── TC01/                  # Backend Python Developer
│   ├── TC02/                  # ML Engineer
│   └── TC03/                  # iOS Developer (Swift)
├── main.py                    # Точка входа, CLI
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

## Зависимости

| Библиотека      | Версия | Зачем                             |
|-----------------|--------|-----------------------------------|
| `Python`        | ≥3.12  |
| `groq`          | ≥1.1.1 | Клиент для Groq API               |
| `pydantic`      | ≥2.0   | Валидация выходных данных агентов |
| `python-dotenv` | ≥1.0   | Загрузка `.env`                   |

## Архитектура

Система построена на **Pipeline Pattern**

```
main.py
  └── Pipeline
        ├── MarketAnalystAgent   → skill_map
        ├── SalaryEstimatorAgent → salary_table
        ├── CareerAdvisorAgent   → learning_path
        └── CriticAgent         → critic_result
```

### Почему Pipeline Pattern

Агенты не вызывают друг друга — они не знают о существовании друг друга. Это означает:
- **Тестируемость:** каждый агент тестируется изолированно с любым контекстом
- **Расширяемость:** новый агент = новый файл, без правок в существующих
- **Отлаживаемость:** можно запустить pipeline с первыми N агентами и осмотреть промежуточный контекст

### Принцип работы

Каждый агент:
1. Получает **полный контекст** (словарь со всеми данными предыдущих агентов)
2. Читает нужные ему ключи
3. Возвращает **свой блок данных**, который Pipeline добавляет в контекст


### Добавить нового агента — одна строка

```python
# main.py
pipeline = (
    Pipeline(role=args.role)
    .add_agent(MarketAnalystAgent(llm))
    .add_agent(SalaryEstimatorAgent(llm))
    .add_agent(CareerAdvisorAgent(llm))
    .add_agent(CriticAgent(llm))
    .add_agent(NewAgent(llm))  # ← новый агент
)
```

Новый агент — новый файл в `agents/`, наследующий `BaseAgent`.

---

## Описание агентов

### Агент 1 — Market Analyst (`agents/market_analyst.py`)

**Вход:** `role`  
**Выход:** `skill_map`

Анализирует рынок вакансий и формирует карту навыков по четырём категориям: `languages`, `frameworks`, `infrastructure`, `soft_skills`. Для каждого навыка определяет востребованность (`critical / important / nice-to-have`) и тренд (`growing / stable / declining`).

### Агент 2 — Salary Estimator (`agents/salary_estimator.py`)

**Вход:** `skill_map`  
**Выход:** `salary_table`

Строит зарплатную таблицу по грейдам (Junior/Middle/Senior/Lead) и регионам (Москва/Регионы РФ/Remote USD). Добавляет оценку тренда рынка и список топовых работодателей.

### Агент 3 — Career Advisor (`agents/career_advisor.py`)

**Вход:** `skill_map` + `salary_table`  
**Выход:** `learning_path`

Составляет трёхфазный план обучения (Foundation → Practice → Portfolio, по 30 дней каждая), gap-анализ с quick wins и долгосрочными целями, конкретный портфолио-проект с технологиями.

### Агент 4 — Critic (`agents/critic.py`)

**Вход:** полный контекст агентов 1–3  
**Выход:** `critic_result`

Проверяет согласованность отчёта: соответствие зарплат навыкам, противоречия между трендами и приоритетами обучения, полноту данных. Выставляет `quality_score` (0–100) и `is_consistent`.


---
## Почему данные корректные?

В промптах каждого агента явно указано, на какие источники ориентироваться: HeadHunter, Habr Career, LinkedIn, Glassdoor, Stack Overflow Developer Survey.
Модель не придумывает — она синтезирует данные опираясь на источники. Также модели заданы конкретные инструкции по многим пунктам, поэтому она следует по заданной траектории, а не уходит в абстракции. 

### Валидация JSON через Pydantic

Каждый агент валидирует свой выход через Pydantic-модели (`core/models.py`). Если LLM вернул неполные данные — получаем конкретную ошибку с указанием поля, а не молчаливый баг в следующем агенте.

### Retry при невалидном JSON

`LLMClient.ask_json()` делает до 3 попыток при ошибке парсинга, добавляя в промпт подсказку с описанием проблемы.

---

# Быстрый старт

### Локально

```bash
# 1. Клонировать репозиторий
git clone https://github.com/WasTeime/test_task_raft.git
cd test_task_raft

# 2. Установить зависимости и создать окружение
uv sync

# 3. Настроить переменные окружения
cp .env.example .env
# Открыть .env и вставить GROQ_API_KEY

# 4. Запустить
uv run main.py --role "Backend Python Developer"
```

### Docker
```bash
# 1. Клонировать репозиторий
git clone https://github.com/WasTeime/test_task_raft.git
cd test_task_raft

# 2. Настроить переменные окружения
cp .env.example .env
# Открыть .env и вставить GROQ_API_KEY

# 3. Создать папку для результатов
mkdir results

# 4. Запустить
docker compose run --rm career-analyser --role "Backend Python Developer"
```

---

### Параметры CLI

| Параметр        | Обязательный | Описание                                                      |
|-----------------|--------------|---------------------------------------------------------------|
| `--role`        | ДА           | Название специальности                                        |
| `--output`      | НЕТ          | Директория для отчётов (по умолчанию: `.`)                    |
| `--verbose`     | НЕТ          | Подробное логирование (DEBUG)                                 |
| `--log-prompts` | НЕТ          | Вывод отправленных промптов и полученных ответов от нейросети |

```bash
uv run main.py --role "Backend Python Developer" --output ./results --verbose --log-prompts
```

---

## Выходные данные

После каждого запуска создаются два файла:

### report.json

Полный контекст в json. Содержит поле `generated_at` (UTC ISO 8601) для верификации реального запуска.

```json
{
  "role": "Backend Python Developer",
  "generated_at": "2025-03-24T10:30:00+00:00",
  "skill_map": { ... },
  "salary_table": { ... },
  "learning_path": { ... },
  "critic_result": {
    "quality_score": 87,
    "is_consistent": true,
    "warnings": []
  }
}
```

### report.md

Отчёт с анализом указанной позиции для пользователя и структурированным планом обучения.

### Примеры отчётов

Папка `examples/` содержит готовые отчёты, полученные реальным запуском системы:

| Директория | Роль |
|-----------|------|
| `examples/TC01/` | Backend Python Developer 
| `examples/TC02/` | ML Engineer 
| `examples/TC03/` | iOS Developer (Swift)

