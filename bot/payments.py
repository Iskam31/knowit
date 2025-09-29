from telegram import LabeledPrice, Invoice, KeyboardButton, ReplyKeyboardMarkup
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from .config import TELEGRAM_PAYMENT_PROVIDER_TOKEN, CURRENCY, MONTHLY_PRICE_RUB
from .db import create_payment, mark_payment_paid, get_payment, find_payment_by_payload
import secrets
from urllib.parse import urlencode

def build_month_invoice(bot, chat_id, price_amount_cents: int, payload: str, title="Подписка на месяц", description="Подписка"):
    # price_amount_cents: в наименьших единицах (копейки). Но Telegram expects amount in smallest currency unit (cents) for some currencies.
    # python-telegram-bot принимает LabeledPrice с amount в целых "центах"/копейках.
    prices = [LabeledPrice(label=title, amount=price_amount_cents)]
    # отправлять invoice будет в handlers (там есть bot.send_invoice)
    return prices

def create_yoomoney_link(tg_id: int, amount_cents: int):
    """
    Простая заглушка: генерируем уникальную ссылку, которая ведёт на страницу-подтверждение (в реале — на YooMoney).
    Для реальной интеграции: используйте API YooMoney и webhook для подтверждения.
    """
    # генерируем payload и сохраняем платёж в БД (через create_payment в handlers)
    payload = secrets.token_urlsafe(16)
    # пример реальной ссылки будет отличаться; здесь укажем placeholder
    params = {"sum": amount_cents/100, "currency": CURRENCY, "payload": payload}
    url = "https://example-payments.local/yoomoney/checkout?" + urlencode(params)
    return url, payload