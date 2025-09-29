FROM python:3.11-slim

# Устанавливаем зависимости
RUN apt-get update && apt-get install -y build-essential libpq-dev && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Скопировать requirements и установить
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Скопировать всё приложение
COPY . .

CMD ["python", "-m", "bot.main"]