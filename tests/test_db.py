"""Тесты слоя данных: временная БД, без сети и без токена."""
import asyncio
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import db  # noqa: E402


class DbTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        handle, self.path = tempfile.mkstemp(suffix=".db")
        os.close(handle)
        os.unlink(self.path)
        await db.connect(self.path)

    async def asyncTearDown(self) -> None:
        for suffix in ("", "-wal", "-shm"):
            try:
                os.unlink(self.path + suffix)
            except FileNotFoundError:
                pass

    async def test_seed_and_catalog(self):
        cats = await db.categories(self.path)
        self.assertEqual(len(cats), 3)
        items = await db.products(self.path, cats[0][0])
        self.assertTrue(items)
        self.assertEqual(items[0][1], "Эспрессо")

    async def test_cart_and_order(self):
        product_id = (await db.products(self.path, 1))[0][0]
        await db.add_to_cart(self.path, 555, product_id)
        await db.add_to_cart(self.path, 555, product_id)
        items = await db.cart(self.path, 555)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0][3], 2)  # количество сложилось
        total = await db.cart_total(self.path, 555)
        self.assertEqual(total, items[0][2] * 2)

        order_id = await db.create_order(self.path, 555, "Фёдор", "+79990000000")
        details = await db.order(self.path, order_id)
        self.assertEqual(details["total"], total)
        self.assertEqual(details["status"], "new")
        self.assertEqual(await db.cart(self.path, 555), [])  # корзина очищена

    async def test_empty_cart_raises(self):
        with self.assertRaises(ValueError):
            await db.create_order(self.path, 777, "Нет", "+70000000000")

    async def test_hidden_product_disappears(self):
        product_id = (await db.products(self.path, 1))[0][0]
        await db.delete_product(self.path, product_id)
        self.assertNotIn(product_id, [row[0] for row in await db.products(self.path, 1)])

    def test_money_format(self):
        self.assertEqual(db.money(129000), "1 290 ₽")
        self.assertEqual(db.money(15000), "150 ₽")


if __name__ == "__main__":
    unittest.main()
