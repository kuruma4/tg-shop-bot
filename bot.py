"""Точка входа: запуск магазина-бота.

    python bot.py
"""
import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Message

import db
import keyboards
from config import config
from handlers import admin, cart, catalog

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("shop")


def build_dispatcher() -> Dispatcher:
    dispatcher = Dispatcher()

    @dispatcher.message(CommandStart())
    async def start(message: Message) -> None:
        await message.answer(
            f"<b>{config.shop_name}</b>\n\n"
            "Здесь можно посмотреть каталог, собрать корзину и оформить заказ.\n"
            "Выберите раздел:",
            reply_markup=keyboards.main_menu(),
        )

    dispatcher.include_router(catalog.router)
    dispatcher.include_router(cart.router)
    dispatcher.include_router(admin.router)
    return dispatcher


async def main() -> None:
    if not config.token:
        raise SystemExit("Нет BOT_TOKEN. Скопируйте .env.example в .env и вставьте токен из @BotFather.")
    await db.connect(config.db_path)
    bot = Bot(config.token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dispatcher = build_dispatcher()
    log.info("Бот запущен, БД: %s", config.db_path)
    await dispatcher.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
