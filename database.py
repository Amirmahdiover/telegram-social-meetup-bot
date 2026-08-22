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
                area TEXT,
                phone TEXT,
                activities TEXT,
                age_preference TEXT,
                availability TEXT,
                join_reason TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'new',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await _make_legacy_registration_fields_nullable(db)
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
        await db.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                date TEXT NOT NULL,
                time TEXT NOT NULL,
                location_name TEXT NOT NULL,
                location_address TEXT NOT NULL,
                latitude REAL,
                longitude REAL,
                message TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS event_members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'invited'
                    CHECK (status IN ('invited', 'confirmed', 'declined')),
                UNIQUE (event_id, user_id),
                FOREIGN KEY (event_id) REFERENCES events(id),
                FOREIGN KEY (user_id) REFERENCES registrations(telegram_user_id)
            )
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_event_members_event_status
            ON event_members (event_id, status)
        """)
        await db.commit()


async def _make_legacy_registration_fields_nullable(db: aiosqlite.Connection) -> None:
    """Relax V0-only fields without losing existing registrations or funnel data."""
    cursor = await db.execute("PRAGMA table_info(registrations)")
    columns = {row[1]: row[3] for row in await cursor.fetchall()}
    legacy_fields = {"area", "phone", "activities", "age_preference", "availability"}
    if not any(columns.get(field) for field in legacy_fields):
        return

    await db.execute("PRAGMA foreign_keys = OFF")
    await db.execute("""
        CREATE TABLE registrations_new (
            telegram_user_id INTEGER PRIMARY KEY,
            telegram_username TEXT,
            first_name TEXT NOT NULL,
            age INTEGER NOT NULL,
            gender TEXT NOT NULL,
            area TEXT,
            phone TEXT,
            activities TEXT,
            age_preference TEXT,
            availability TEXT,
            join_reason TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'new',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)
    await db.execute("""
        INSERT INTO registrations_new
        SELECT telegram_user_id, telegram_username, first_name, age, gender, area, phone,
               activities, age_preference, availability, join_reason, status, created_at, updated_at
        FROM registrations
    """)
    await db.execute("DROP TABLE registrations")
    await db.execute("ALTER TABLE registrations_new RENAME TO registrations")
    await db.execute("PRAGMA foreign_keys = ON")


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
        "area": None,
        "phone": None,
        "activities": None,
        "age_preference": None,
        "availability": None,
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
    result["activities"] = json.loads(result["activities"] or "[]")
    result["availability"] = json.loads(result["availability"] or "[]")
    return result


async def get_all_registrations() -> list[dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM registrations ORDER BY created_at DESC")
        rows = await cursor.fetchall()
    return [dict(row) for row in rows]


async def create_event(data: dict[str, Any]) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            INSERT INTO events (
                title, date, time, location_name, location_address,
                latitude, longitude, message
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data["title"], data["date"], data["time"], data["location_name"],
            data["location_address"], data.get("latitude"), data.get("longitude"),
            data["message"],
        ))
        await db.commit()
        return cursor.lastrowid


async def get_event(event_id: int) -> dict[str, Any] | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM events WHERE id = ?", (event_id,))
        row = await cursor.fetchone()
    return dict(row) if row else None


async def add_event_member(event_id: int, user_id: int) -> bool:
    """Add a registered user as invited. Returns False when either ID is unknown."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            INSERT INTO event_members (event_id, user_id, status)
            SELECT ?, ?, 'invited'
            WHERE EXISTS (SELECT 1 FROM events WHERE id = ?)
              AND EXISTS (SELECT 1 FROM registrations WHERE telegram_user_id = ?)
            ON CONFLICT(event_id, user_id) DO UPDATE SET status = 'invited'
        """, (event_id, user_id, event_id, user_id))
        await db.commit()
        return cursor.rowcount > 0


async def get_invited_members(event_id: int) -> list[int]:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            SELECT user_id FROM event_members
            WHERE event_id = ? AND status = 'invited'
        """, (event_id,))
        rows = await cursor.fetchall()
    return [row[0] for row in rows]


async def get_event_members(event_id: int) -> list[dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("""
            SELECT registrations.first_name, event_members.user_id, event_members.status
            FROM event_members
            JOIN registrations ON registrations.telegram_user_id = event_members.user_id
            WHERE event_members.event_id = ?
            ORDER BY event_members.id
        """, (event_id,))
        rows = await cursor.fetchall()
    return [dict(row) for row in rows]


async def update_event_member_status(event_id: int, user_id: int, status: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            UPDATE event_members SET status = ?
            WHERE event_id = ? AND user_id = ?
        """, (status, event_id, user_id))
        await db.commit()
        return cursor.rowcount > 0
