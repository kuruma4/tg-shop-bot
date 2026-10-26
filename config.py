"""Настройки бота: читаются из .env."""
import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


def _ids(raw: str) -> list[int]:
    return [int(part) for part in raw.replace(" ", "").split(",") if part.strip().isdigit()]


@dataclass
class Config:
    token: str = os.getenv("BOT_TOKEN", "")
    admins: list[int] = field(default_factory=lambda: _ids(os.getenv("ADMIN_IDS", "")))
    shop_name: str = os.getenv("SHOP_NAME", "Магазин")
    db_path: str = os.getenv("DB_PATH", "shop.db")
    # Токен платёжного провайдера Telegram (BotFather -> Payments).
    # Пусто — оплата не показывается, заказ уходит админу вручную.
    payment_token: str = os.getenv("PAYMENT_TOKEN", "")


config = Config()
