import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from .db import init_db, ensure_user, get_user, create_payment, mark_payment_paid, add_requests, find_payment_by_payload, get_payment, mark_payment_paid as db_mark_paid
from .config import MONTHLY_PRICE_RUB, CURRENCY, TELEGRAM_PAYMENT_PROVIDER_TOKEN
from .payments import build_month_invoice, create_yoomoney_link
from .model_api import query_model
from datetime import datetime

log = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    ensure_user(user.id)
    text = (
        f"Привет, {user.first_name or 'пользователь'}!\n\n"
        "Я телеграм-бот с доступом к языковой модели.\n"
        "Команды:\n"
        "/profile — профиль и подписка\n"
        "/buy — купить подписку через Telegram (инвойс)\n"
        "/buy_yoomoney — ссылка на оплату через YooMoney (эмуляция)\n"
        "/mock_pay <payment_id> — (только для теста) отметить платёж как оплачен\n\n"
        "После покупки у тебя появится лимит запросов — ими бот будет списывать при использовании."
    )
    await update.message.reply_text(text)

async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    u = get_user(user.id)
    if not u:
        ensure_user(user.id)
        u = get_user(user.id)
    is_active = bool(u["is_active"])
    expire = u["expire_ts"]
    expire_str = datetime.utcfromtimestamp(expire).strftime("%d.%m.%Y") if expire else "—"
    text = (
        f"Профиль — {user.first_name}\n"
        f"Статус подписки: {'Активна ✅' if is_active else 'Неактивна ❌'}\n"
        f"Осталось запросов: {u['requests_left']}\n"
        f"Подписка до: {expire_str}\n"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("Купить через Telegram", callback_data="buy_sub")],
        [InlineKeyboardButton("Оплатить через YooMoney", callback_data="buy_yoomoney")],
    ])
    await update.message.reply_text(text, reply_markup=kb)

async def buy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # отправляем инвойс через Telegram Payments (если есть токен)
    user = update.effective_user
    if not TELEGRAM_PAYMENT_PROVIDER_TOKEN:
        await update.message.reply_text("Telegram Payments не настроены (нет PROVIDER TOKEN в .env).")
        return
    amount = MONTHLY_PRICE_RUB  # в копейках
    payload = f"tg_pay_{user.id}_{int(datetime.utcnow().timestamp())}"
    # создаём запись в БД
    pid = create_payment(user.id, provider="telegram", amount=amount, currency=CURRENCY, payload=payload)
    prices = build_month_invoice(context.bot, user.id, amount, payload)
    await context.bot.send_invoice(
        chat_id=user.id,
        title="Подписка (месяц)",
        description="Доступ к боту на 30 дней",
        payload=payload,
        provider_token=TELEGRAM_PAYMENT_PROVIDER_TOKEN,
        currency=CURRENCY,
        prices=prices,
        start_parameter="subscribe-month"
    )

async def precheckout_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # подтверждение предчека — всегда ок
    query = update.pre_checkout_query
    await query.answer(ok=True)

async def successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # обработка успешного платежа через Telegram
    user = update.effective_user
    # payload приходит в successful_payment.invoice_payload в old API, in PTB v20 it is in message.successful_payment.invoice_payload
    payload = update.message.successful_payment.invoice_payload if update.message and update.message.successful_payment else None
    if not payload:
        await update.message.reply_text("Не удалось получить payload платежа.")
        return
    payment = find_payment_by_payload(payload)
    if not payment:
        await update.message.reply_text("Платёж найден не в базе, но всё ок — активирую подписку (локально).")
        # на всякий случай создаём запись
        pid = create_payment(user.id, provider="telegram", amount=update.
        message.successful_payment.total_amount, currency=update.message.successful_payment.currency, payload=payload)
        payment_id = pid
    else:
        payment_id = payment["id"]
    # отмечаем платёж, активируем подписку
    db_mark_paid(payment_id)
    await update.message.reply_text("Оплата получена. Подписка активирована ✅")

async def buy_yoomoney_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    amount = MONTHLY_PRICE_RUB
    url, payload = create_yoomoney_link(user.id, amount)
    # сохраним платёж
    pid = create_payment(user.id, provider="yoomoney", amount=amount, currency=CURRENCY, payload=payload)
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("Оплатить через YooMoney", url=url)],
        [InlineKeyboardButton("Я оплатил ✅", callback_data=f"check_ym_{pid}")],
    ])
    await query.answer()
    await query.message.reply_text("Ссылка для оплаты (эмуляция). После оплаты нажмите кнопку 'Я оплатил'.", reply_markup=kb)

async def check_yoomoney_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    # ожидалось формат check_ym_{pid}
    try:
        pid = int(data.split("_")[-1])
    except Exception:
        await query.answer("Неверный запрос.")
        return
    payment = get_payment(pid)
    if not payment:
        await query.answer("Платёж не найден.")
        return
    if payment["status"] == "paid":
        await query.message.reply_text("Оплата подтверждена — подписка активирована ✅")
        await query.answer()
    else:
        await query.message.reply_text("Платёж ещё не подтверждён. Если ты тестируешь — используй /mock_pay <id> (админ/тест).")
        await query.answer()

async def mock_pay_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Команда для тестирования: /mock_pay <payment_id>
    msg = update.message.text.strip().split()
    if len(msg) < 2:
        await update.message.reply_text("Укажи id платежа: /mock_pay <id>")
        return
    try:
        pid = int(msg[1])
    except:
        await update.message.reply_text("Неверный id.")
        return
    payment = get_payment(pid)
    if not payment:
        await update.message.reply_text("Платёж не найден.")
        return
    # пометить как оплачен и активировать подписку (см. db.mark_payment_paid)
    from .db import mark_payment_paid as db_mark
    db_mark(pid)
    await update.message.reply_text(f"Платёж {pid} помечен как оплаченный (тест). Подписка активирована для {payment['tg_id']}.")

async def model_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Обработчик сообщений, использующий модель. Перед списанием запросов проверяем лимит.
    if update.message is None:
        return
    user = update.effective_user
    from .db import consume_request
    ok = consume_request(user.id)
    if not ok:
        await update.message.reply_text("У тебя нет доступных запросов. Купи подписку /profile -> Продлить.")
        return
    prompt = update.message.text
    resp = await query_model(prompt, user.id)
    await update.message.reply_text(resp)