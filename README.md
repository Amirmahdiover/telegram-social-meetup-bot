# Tehran Social Meetup Bot

A small Telegram bot for collecting registrations for small, in-person social meetups in Tehran. It is not a dating app. Matching and meetup creation are intentionally manual in V0.

## Requirements

- Python 3.11 or newer
- A Telegram bot token from BotFather

## Setup on Windows (PowerShell / VS Code)

1. Create a bot: open Telegram, message [@BotFather](https://t.me/BotFather), use `/newbot`, and copy its token.
2. In this project folder, create and activate a virtual environment:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

3. Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

4. Create your local configuration:

```powershell
Copy-Item .env.example .env
```

5. Open `.env` and set `BOT_TOKEN` to the BotFather token. Set `ADMIN_IDS` to your numeric Telegram user ID (multiple IDs are comma-separated). You can obtain it from a Telegram ID bot.
6. Run the bot:

```powershell
python bot.py
```

The first start creates `meetup_bot.sqlite3` automatically. Keep that file private: it contains registrations and funnel analytics. Older databases may still contain phone numbers from the previous flow.

## Resetting the Local Database

Use this only for local development. It permanently deletes `meetup_bot.sqlite3`, including registrations, funnel analytics, statuses, registration attempts, and any other data stored in the SQLite database.

```powershell
# 1. Stop the running bot
Ctrl + C

# 2. Reset the database
.\reset_db.ps1

# 3. Type
RESET

# 4. Start the bot again
python bot.py
```

The script checks whether the database is in use and tells you to stop the bot first if it is locked. The final command recreates the database and tables automatically.

**Do not use this reset workflow on a production database or after real user data becomes important.**

## Commands

- `/start` — start or restart registration
- `/cancel` — cancel an in-progress registration
- `/me` — view your saved registration
- `/registrations` — admins only; downloads all registrations as an Excel-friendly UTF-8 CSV

## V0 registration flow

`/start` → 18+ confirmation → first name → age → gender → join reason → review → completed.

The current event format is café + conversation + UNO. Registration records interest only; selected people receive a Telegram message for final coordination.

## V0 workflow

The bot only collects and organizes data. An admin manually reviews registrations, chooses roughly 6–8 compatible people, contacts them, and manages statuses outside the bot for now. The bot does not create participant group chats, reveal participants' profiles/photos/phone numbers, perform automated matching, process payments, or use AI.
