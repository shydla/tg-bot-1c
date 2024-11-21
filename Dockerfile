# Используем Python 3.8
FROM python:3.8-slim

# Устанавливаем poetry
RUN pip install poetry

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем файлы зависимостей
COPY pyproject.toml poetry.lock ./

# Настраиваем poetry для работы в Docker
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi

# Копируем код приложения
COPY . .

# Запускаем бота
CMD ["poetry", "run", "python", "src/bot.py"] 