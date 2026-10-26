"""Каталог: категории -> товары -> карточка -> корзина."""
from aiogram import F, Router
from aiogram.types import CallbackQuery

import db
import keyboards
from config import config

router = Router()


@router.callback_query(F.data == "menu")
async def to_menu(call: CallbackQuery) -> None:
    await call.message.edit_text(
        f"<b>{config.shop_name}</b>\n\nВыберите раздел:", reply_markup=keyboards.main_menu()
    )
    await call.answer()


@router.callback_query(F.data == "catalog")
async def show_catalog(call: CallbackQuery) -> None:
    items = await db.categories(config.db_path)
    await call.message.edit_text("Категории:", reply_markup=keyboards.categories_menu(items))
    await call.answer()


@router.callback_query(F.data.startswith("cat:"))
async def show_products(call: CallbackQuery) -> None:
    category_id = int(call.data.split(":", 1)[1])
    markup = await keyboards.products_menu(config.db_path, category_id)
    await call.message.edit_text("Выберите товар:", reply_markup=markup)
    await call.answer()


@router.callback_query(F.data.startswith("item:"))
async def show_product(call: CallbackQuery) -> None:
    product_id = int(call.data.split(":", 1)[1])
    row = await db.product(config.db_path, product_id)
    if not row:
        await call.answer("Товар недоступен", show_alert=True)
        return
    _, title, description, price = row
    text = f"<b>{title}</b>\n\n{description}\n\nЦена: <b>{db.money(price)}</b>"
    await call.message.edit_text(text, reply_markup=keyboards.product_card(product_id))
    await call.answer()


@router.callback_query(F.data.startswith("add:"))
async def add_to_cart(call: CallbackQuery) -> None:
    product_id = int(call.data.split(":", 1)[1])
    if not await db.product(config.db_path, product_id):
        await call.answer("Товар недоступен", show_alert=True)
        return
    count = await db.add_to_cart(config.db_path, call.from_user.id, product_id)
    await call.answer(f"В корзине {count} шт.", show_alert=False)
