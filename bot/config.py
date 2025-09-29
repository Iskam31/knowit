import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
TELEGRAM_PAYMENT_PROVIDER_TOKEN = os.getenv("TELEGRAM_PAYMENT_PROVIDER_TOKEN", "")

# Данные для Postgres
DB_NAME = os.getenv("POSTGRES_DB", "botdb")
DB_USER = os.getenv("POSTGRES_USER", "botuser")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "botpass")
DB_HOST = os.getenv("POSTGRES_HOST", "db")
DB_PORT = int(os.getenv("POSTGRES_PORT", "5432"))

MONTHLY_PRICE_RUB = int(os.getenv("MONTHLY_PRICE_RUB", "19900"))
CURRENCY = os.getenv("CURRENCY", "RUB")