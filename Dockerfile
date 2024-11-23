# Используем Python 3.8
FROM python:3.8-slim

# Устанавливаем необходимые пакеты
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем poetry
RUN pip install poetry

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем файлы зависимостей
COPY pyproject.toml poetry.lock ./

# Настраиваем poetry для работы в Docker
RUN poetry config virtualenvs.create false \
    && poetry install --no-dev --no-interaction --no-ansi

# Копируем код приложения
COPY . .

# Запускаем бота
CMD ["python", "src/bot.py"] 