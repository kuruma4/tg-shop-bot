"""Корзина и оформление заказа."""
from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

import db
import keyboards
from config import config

router = Router()


class Checkout(StatesGroup):
    name = State()
    phone = State()


def cart_text(items, total: int) -> str:
    if not items:
        return "Корзина пуста."
    lines = [f"• {title} × {qty} — {db.money(price * qty)}" for _, title, price, qty in items]
    return "Ваш заказ:\n\n" + "\n".join(lines) + f"\n\nИтого: <b>{db.money(total)}</b>"


@router.callback_query(F.data == "cart")
async def show_cart(call: CallbackQuery) -> None:
    items = await db.cart(config.db_path, call.from_user.id)
    total = sum(price * qty for _, _, price, qty in items)
    await call.message.edit_text(cart_text(items, total), reply_markup=keyboards.cart_menu(bool(items)))
    await call.answer()


@router.callback_query(F.data == "clear")
async def clear(call: CallbackQuery) -> None:
    await db.clear_cart(config.db_path, call.from_user.id)
    await call.message.edit_text("Корзина пуста.", reply_markup=keyboards.cart_menu(False))
    await call.answer("Очищено")


@router.callback_query(F.data == "checkout")
async def checkout(call: CallbackQuery, state: FSMContext) -> None:
    if not await db.cart(config.db_path, call.from_user.id):
        await call.answer("Корзина пуста", show_alert=True)
        return
    await state.set_state(Checkout.name)
    await call.message.answer("Как вас зовут?")
    await call.answer()


@router.message(Checkout.name)
async def got_name(message: Message, state: FSMContext) -> None:
    await state.update_data(name=message.text.strip()[:100])
    await state.set_state(Checkout.phone)
    await message.answer("Телефон для связи?")


@router.message(Checkout.phone)
async def got_phone(message: Message, state: FSMContext, bot: Bot) -> None:
    phone = message.text.strip()
    if sum(char.isdigit() for char in phone) < 10:
        await message.answer("Похоже, в номере ошибка. Введите телефон ещё раз.")
        return
    data = await state.get_data()
    order_id = await db.create_order(config.db_path, message.from_user.id, data["name"], phone[:30])
    await state.clear()

    details = await db.order(config.db_path, order_id)
    await message.answer(
        f"Заказ №{order_id} принят.\nМы свяжемся с вами по номеру {phone}.",
        reply_markup=keyboards.main_menu(),
    )
    # Уведомление админу
    lines = [f"• {title} × {qty} — {db.money(price * qty)}" for title, price, qty in details["items"]]
    admin_text = (
        f"Новый заказ №{order_id}\n"
        f"Клиент: {details['name']}, {details['phone']}\n"
        f"Сумма: {db.money(details['total'])}\n\n" + "\n".join(lines)
    )
    for admin_id in config.admins:
        try:
            await bot.send_message(admin_id, admin_text, reply_markup=keyboards.order_card(order_id))
        except Exception:  # админ мог не нажать /start
            continue


@router.callback_query(F.data == "delivery")
async def delivery(call: CallbackQuery) -> None:
    await call.message.edit_text(
        "Доставка по городу — 300 ₽, от 2 000 ₽ бесплатно.\n"
        "Оплата: при получении или онлайн.\n"
        "Срок: 1–2 дня.",
        reply_markup=keyboards.main_menu(),
    )
    await call.answer()
