import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    bot_token: str
    admin_ids: set[int]


def get_settings() -> Settings:
    load_dotenv()
    token = os.getenv("BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("BOT_TOKEN is missing. Copy .env.example to .env and add your token.")

    admin_ids: set[int] = set()
    for value in os.getenv("ADMIN_IDS", "").split(","):
        value = value.strip()
        if value:
            try:
                admin_ids.add(int(value))
            except ValueError as exc:
                raise RuntimeError("ADMIN_IDS must contain comma-separated numeric Telegram IDs.") from exc

    return Settings(bot_token=token, admin_ids=admin_ids)
