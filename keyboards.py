"""Инлайн-клавиатуры."""
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

import db


def main_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Каталог", callback_data="catalog")
    builder.button(text="Корзина", callback_data="cart")
    builder.button(text="Доставка и оплата", callback_data="delivery")
    builder.adjust(2, 1)
    return builder.as_markup()


def categories_menu(items: list[tuple[int, str]]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for category_id, title in items:
        builder.button(text=title, callback_data=f"cat:{category_id}")
    builder.button(text="Назад", callback_data="menu")
    builder.adjust(2, 1)
    return builder.as_markup()


async def products_menu(path: str, category_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for product_id, title, price in await db.products(path, category_id):
        builder.button(text=f"{title} · {db.money(price)}", callback_data=f"item:{product_id}")
    builder.button(text="Назад", callback_data="catalog")
    builder.adjust(1)
    return builder.as_markup()


def product_card(product_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Добавить в корзину", callback_data=f"add:{product_id}")
    builder.button(text="Корзина", callback_data="cart")
    builder.button(text="Назад", callback_data="catalog")
    builder.adjust(1)
    return builder.as_markup()


def cart_menu(has_items: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if has_items:
        builder.button(text="Оформить заказ", callback_data="checkout")
        builder.button(text="Очистить", callback_data="clear")
    builder.button(text="Каталог", callback_data="catalog")
    builder.adjust(2, 1)
    return builder.as_markup()


def order_card(order_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Подтвердить", callback_data=f"set:done:{order_id}")
    builder.button(text="Отменить", callback_data=f"set:cancel:{order_id}")
    builder.adjust(2)
    return builder.as_markup()
