import logging
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, CallbackQueryHandler, PreCheckoutQueryHandler
from .config import BOT_TOKEN
from . import db
from .handlers import start, profile, buy_command, precheckout_update, successful_payment, buy_yoomoney_callback, check_yoomoney_payment, mock_pay_command, model_query_handler

import asyncio
import os

LOG_LEVEL = logging.INFO
logging.basicConfig(level=LOG_LEVEL, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger(__name__)

def main():
    if not BOT_TOKEN:
        log.error("Не задан BOT_TOKEN в .env. Останов.")
        return

    # Инициализируем БД
    db.init_db()

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Команды
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("profile", profile))
    app.add_handler(CommandHandler("buy", buy_command))
    app.add_handler(CommandHandler("buy_yoomoney", buy_command))  # на случай вызова команды напрямую
    app.add_handler(CommandHandler("mock_pay", mock_pay_command))

    # pre-checkout (для Telegram Payments)
    app.add_handler(PreCheckoutQueryHandler(precheckout_update))
    # successful payment
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment))

    # Inline callbacks
    app.add_handler(CallbackQueryHandler(buy_yoomoney_callback, pattern="buy_yoomoney"))
    app.add_handler(CallbackQueryHandler(check_yoomoney_payment, pattern=r"^check_ym_"))
    app.add_handler(CallbackQueryHandler(buy_yoomoney_callback, pattern="buy_sub"))
    # Сообщения (вызов модели)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, model_query_handler))

    log.info("Запуск бота (long polling)...")
    app.run_polling()

if name == "__main__":
    main()