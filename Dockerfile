FROM python:3.12-slim

WORKDIR /app

# Устанавливаем uv
RUN pip install uv

# Копируем зависимости и устанавливаем их (кешируется отдельно от кода)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Копируем исходники
COPY . .

ENTRYPOINT ["uv", "run", "main.py", "--output", "/app/results"]
