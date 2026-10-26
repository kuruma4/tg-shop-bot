"""Админка: заказы, статистика, добавление товаров."""
import shlex

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

import db
import keyboards
from config import config

router = Router()


def is_admin(user_id: int) -> bool:
    return user_id in config.admins


@router.message(Command("admin"))
async def admin_panel(message: Message) -> None:
    if not is_admin(message.from_user.id):
        return
    data = await db.stats(config.db_path)
    orders = await db.last_orders(config.db_path, limit=5)
    lines = [
        "<b>Админка</b>",
        f"Заказов: {data['orders']} · Выручка: {db.money(data['revenue'])}",
        f"Товаров: {data['products']}",
        "",
        "Последние заказы:",
    ]
    lines += [f"№{oid} · {name} · {db.money(total)} · {status}" for oid, name, _, total, status, _ in orders] or ["—"]
    lines += ["", "Команды:", "/add_category Название", "/add_product id|Название|Цена ₽", "/hide id"]
    await message.answer("\n".join(lines))


@router.message(Command("add_category"))
async def add_category(message: Message) -> None:
    if not is_admin(message.from_user.id):
        return
    title = message.text.partition(" ")[2].strip()
    if not title:
        await message.answer("Формат: /add_category Кофе")
        return
    import aiosqlite

    async with aiosqlite.connect(config.db_path) as database:
        await database.execute("INSERT INTO categories (title) VALUES (?)", (title,))
        await database.commit()
    await message.answer(f"Категория «{title}» добавлена.")


@router.message(Command("add_product"))
async def add_product(message: Message) -> None:
    if not is_admin(message.from_user.id):
        return
    payload = message.text.partition(" ")[2]
    parts = [part.strip() for part in payload.split("|")]
    if len(parts) < 3 or not parts[0].isdigit():
        await message.answer("Формат: /add_product id_категории|Название|Цена в рублях")
        return
    category_id, title, price = int(parts[0]), parts[1], parts[2].replace(" ", "")
    if not price.isdigit():
        await message.answer("Цена должна быть числом в рублях, например 350")
        return
    product_id = await db.add_product(config.db_path, category_id, title, int(price) * 100)
    await message.answer(f"Товар №{product_id} «{title}» добавлен за {db.money(int(price) * 100)}.")


@router.message(Command("hide"))
async def hide_product(message: Message) -> None:
    if not is_admin(message.from_user.id):
        return
    arg = message.text.partition(" ")[2].strip()
    if not arg.isdigit():
        await message.answer("Формат: /hide 12")
        return
    await db.delete_product(config.db_path, int(arg))
    await message.answer(f"Товар №{arg} скрыт из каталога.")


@router.callback_query(F.data.startswith("set:"))
async def change_status(call: CallbackQuery, bot: Bot) -> None:
    if not is_admin(call.from_user.id):
        await call.answer("Нет доступа", show_alert=True)
        return
    _, status, order_id = call.data.split(":")
    await db.set_status(config.db_path, int(order_id), status)
    label = "подтверждён" if status == "done" else "отменён"
    await call.message.edit_text(f"{call.message.text}\n\nСтатус: {label}")
    await call.answer(f"Заказ {label}")

    details = await db.order(config.db_path, int(order_id))
    if details:
        try:
            await bot.send_message(
                details["user_id"],
                f"Ваш заказ №{order_id}: {label}.",
            )
        except Exception:
            pass
