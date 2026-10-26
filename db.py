"""Слой данных: SQLite через aiosqlite.

Все запросы — параметризованные, никакой склейки строк из пользовательского
ввода. Цены хранятся в копейках, чтобы не ловить ошибки округления.
"""
from __future__ import annotations

import aiosqlite

SCHEMA = """
CREATE TABLE IF NOT EXISTS categories (
    id    INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS products (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id INTEGER REFERENCES categories(id) ON DELETE CASCADE,
    title       TEXT    NOT NULL,
    description TEXT    DEFAULT '',
    price       INTEGER NOT NULL,          -- копейки
    is_active   INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS carts (
    user_id    INTEGER NOT NULL,
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    qty        INTEGER NOT NULL DEFAULT 1,
    PRIMARY KEY (user_id, product_id)
);

CREATE TABLE IF NOT EXISTS orders (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL,
    name       TEXT    NOT NULL,
    phone      TEXT    NOT NULL,
    total      INTEGER NOT NULL,           -- копейки
    status     TEXT    NOT NULL DEFAULT 'new',
    created_at TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS order_items (
    order_id   INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL,
    title      TEXT    NOT NULL,
    price      INTEGER NOT NULL,
    qty        INTEGER NOT NULL
);
"""

SEED = """
INSERT INTO categories (title) VALUES ('Кофе'), ('Десерты'), ('Мерч');
INSERT INTO products (category_id, title, description, price) VALUES
  (1, 'Эспрессо',   'Классика, 30 мл',        15000),
  (1, 'Капучино',   'Молоко 3.2%, 250 мл',    22000),
  (2, 'Чизкейк',    'Нью-Йорк, 120 г',        35000),
  (3, 'Термокружка','500 мл, сталь',          129000);
"""


def money(kopecks: int) -> str:
    """129000 -> '1 290 ₽'"""
    rubles = kopecks / 100
    text = f"{rubles:,.0f}".replace(",", " ")
    return f"{text} ₽"


async def connect(path: str) -> None:
    async with aiosqlite.connect(path) as db:
        await db.executescript(SCHEMA)
        cursor = await db.execute("SELECT COUNT(*) FROM products")
        (count,) = await cursor.fetchone()
        if count == 0:
            await db.executescript(SEED)
        await db.commit()


async def categories(path: str) -> list[tuple[int, str]]:
    async with aiosqlite.connect(path) as db:
        cursor = await db.execute("SELECT id, title FROM categories ORDER BY id")
        return list(await cursor.fetchall())


async def products(path: str, category_id: int) -> list[tuple[int, str, int]]:
    async with aiosqlite.connect(path) as db:
        cursor = await db.execute(
            "SELECT id, title, price FROM products "
            "WHERE category_id = ? AND is_active = 1 ORDER BY id",
            (category_id,),
        )
        return list(await cursor.fetchall())


async def product(path: str, product_id: int):
    async with aiosqlite.connect(path) as db:
        cursor = await db.execute(
            "SELECT id, title, description, price FROM products WHERE id = ? AND is_active = 1",
            (product_id,),
        )
        return await cursor.fetchone()


async def add_to_cart(path: str, user_id: int, product_id: int, qty: int = 1) -> int:
    async with aiosqlite.connect(path) as db:
        await db.execute(
            "INSERT INTO carts (user_id, product_id, qty) VALUES (?, ?, ?) "
            "ON CONFLICT(user_id, product_id) DO UPDATE SET qty = qty + excluded.qty",
            (user_id, product_id, qty),
        )
        await db.commit()
        cursor = await db.execute(
            "SELECT COALESCE(SUM(qty), 0) FROM carts WHERE user_id = ?", (user_id,)
        )
        (total,) = await cursor.fetchone()
        return int(total)


async def cart(path: str, user_id: int) -> list[tuple[int, str, int, int]]:
    """[(product_id, title, price, qty)]"""
    async with aiosqlite.connect(path) as db:
        cursor = await db.execute(
            "SELECT p.id, p.title, p.price, c.qty FROM carts c "
            "JOIN products p ON p.id = c.product_id "
            "WHERE c.user_id = ? AND p.is_active = 1 ORDER BY p.id",
            (user_id,),
        )
        return list(await cursor.fetchall())


async def cart_total(path: str, user_id: int) -> int:
    return sum(price * qty for _, _, price, qty in await cart(path, user_id))


async def clear_cart(path: str, user_id: int) -> None:
    async with aiosqlite.connect(path) as db:
        await db.execute("DELETE FROM carts WHERE user_id = ?", (user_id,))
        await db.commit()


async def create_order(path: str, user_id: int, name: str, phone: str) -> int:
    """Переносит корзину в заказ. Возвращает id заказа."""
    items = await cart(path, user_id)
    if not items:
        raise ValueError("Корзина пуста")
    total = sum(price * qty for _, _, price, qty in items)
    async with aiosqlite.connect(path) as db:
        cursor = await db.execute(
            "INSERT INTO orders (user_id, name, phone, total) VALUES (?, ?, ?, ?)",
            (user_id, name, phone, total),
        )
        order_id = cursor.lastrowid
        await db.executemany(
            "INSERT INTO order_items (order_id, product_id, title, price, qty) "
            "VALUES (?, ?, ?, ?, ?)",
            [(order_id, pid, title, price, qty) for pid, title, price, qty in items],
        )
        await db.execute("DELETE FROM carts WHERE user_id = ?", (user_id,))
        await db.commit()
    return int(order_id)


async def order(path: str, order_id: int):
    async with aiosqlite.connect(path) as db:
        cursor = await db.execute(
            "SELECT id, user_id, name, phone, total, status FROM orders WHERE id = ?",
            (order_id,),
        )
        row = await cursor.fetchone()
        if not row:
            return None
        cursor = await db.execute(
            "SELECT title, price, qty FROM order_items WHERE order_id = ?", (order_id,)
        )
        return {**dict(zip(("id", "user_id", "name", "phone", "total", "status"), row)),
                "items": list(await cursor.fetchall())}


async def set_status(path: str, order_id: int, status: str) -> None:
    async with aiosqlite.connect(path) as db:
        await db.execute("UPDATE orders SET status = ? WHERE id = ?", (status, order_id))
        await db.commit()


async def last_orders(path: str, limit: int = 10) -> list[tuple]:
    async with aiosqlite.connect(path) as db:
        cursor = await db.execute(
            "SELECT id, name, phone, total, status, created_at FROM orders "
            "ORDER BY id DESC LIMIT ?",
            (limit,),
        )
        return list(await cursor.fetchall())


async def add_product(path: str, category_id: int, title: str, price: int, description: str = "") -> int:
    async with aiosqlite.connect(path) as db:
        cursor = await db.execute(
            "INSERT INTO products (category_id, title, description, price) VALUES (?, ?, ?, ?)",
            (category_id, title, description, price),
        )
        await db.commit()
        return int(cursor.lastrowid)


async def delete_product(path: str, product_id: int) -> None:
    async with aiosqlite.connect(path) as db:
        await db.execute("UPDATE products SET is_active = 0 WHERE id = ?", (product_id,))
        await db.commit()


async def stats(path: str) -> dict:
    async with aiosqlite.connect(path) as db:
        cursor = await db.execute("SELECT COUNT(*), COALESCE(SUM(total), 0) FROM orders")
        orders_count, revenue = await cursor.fetchone()
        cursor = await db.execute("SELECT COUNT(*) FROM products WHERE is_active = 1")
        (products_count,) = await cursor.fetchone()
    return {"orders": orders_count, "revenue": revenue, "products": products_count}
