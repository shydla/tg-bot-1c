# Используем Python 3.8
FROM python:3.8-slim

# Устанавливаем необходимые пакеты
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем файлы зависимостей
COPY requirements.txt .

# Устанавливаем зависимости напрямую через pip
RUN pip install -r requirements.txt

# Копируем код приложения
COPY . .

# Запускаем бота
CMD ["python", "src/bot.py"] 