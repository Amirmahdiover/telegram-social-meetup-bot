import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiosqlite

DB_PATH = Path(__file__).with_name("meetup_bot.sqlite3")


async def init_db() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS registrations (
                telegram_user_id INTEGER PRIMARY KEY,
                telegram_username TEXT,
                first_name TEXT NOT NULL,
                age INTEGER NOT NULL,
                gender TEXT NOT NULL,
                area TEXT NOT NULL,
                phone TEXT NOT NULL,
                activities TEXT NOT NULL,
                age_preference TEXT NOT NULL,
                availability TEXT NOT NULL,
                join_reason TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'new',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS funnel_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_user_id INTEGER NOT NULL,
                event_name TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_funnel_events_user_event_created
            ON funnel_events (telegram_user_id, event_name, created_at)
        """)
        await db.commit()


async def track_funnel_event(telegram_user_id: int, event_name: str) -> None:
    """Record a funnel transition, ignoring accidental repeats within five minutes."""
    created_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO funnel_events (telegram_user_id, event_name, created_at)
            SELECT ?, ?, ?
            WHERE NOT EXISTS (
                SELECT 1 FROM funnel_events
                WHERE telegram_user_id = ? AND event_name = ?
                  AND created_at >= datetime(?, '-5 minutes')
            )
        """, (telegram_user_id, event_name, created_at, telegram_user_id, event_name, created_at))
        await db.commit()


async def get_funnel_counts() -> dict[str, int]:
    """Return unique-user counts for every tracked funnel event."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            SELECT event_name, COUNT(DISTINCT telegram_user_id) AS user_count
            FROM funnel_events
            GROUP BY event_name
        """)
        rows = await cursor.fetchall()
    return {event_name: user_count for event_name, user_count in rows}


async def save_registration(user_id: int, username: str | None, data: dict[str, Any]) -> None:
    values = {
        "telegram_user_id": user_id,
        "telegram_username": username or "",
        "first_name": data["first_name"],
        "age": data["age"],
        "gender": data["gender"],
        "area": data["area"],
        "phone": data["phone"],
        "activities": json.dumps(data["activities"], ensure_ascii=False),
        "age_preference": data["age_preference"],
        "availability": json.dumps(data["availability"], ensure_ascii=False),
        "join_reason": data["join_reason"],
    }
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO registrations (
                telegram_user_id, telegram_username, first_name, age, gender, area, phone,
                activities, age_preference, availability, join_reason
            ) VALUES (
                :telegram_user_id, :telegram_username, :first_name, :age, :gender, :area, :phone,
                :activities, :age_preference, :availability, :join_reason
            )
            ON CONFLICT(telegram_user_id) DO UPDATE SET
                telegram_username=excluded.telegram_username,
                first_name=excluded.first_name, age=excluded.age, gender=excluded.gender,
                area=excluded.area, phone=excluded.phone, activities=excluded.activities,
                age_preference=excluded.age_preference, availability=excluded.availability,
                join_reason=excluded.join_reason, status='new', updated_at=CURRENT_TIMESTAMP
        """, values)
        await db.commit()


async def get_registration(user_id: int) -> dict[str, Any] | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM registrations WHERE telegram_user_id = ?", (user_id,))
        row = await cursor.fetchone()
    if row is None:
        return None
    result = dict(row)
    result["activities"] = json.loads(result["activities"])
    result["availability"] = json.loads(result["availability"])
    return result


async def get_all_registrations() -> list[dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM registrations ORDER BY created_at DESC")
        rows = await cursor.fetchall()
    return [dict(row) for row in rows]
