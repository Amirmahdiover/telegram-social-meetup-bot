# Resetting the local database

`reset_db.ps1` permanently deletes the local SQLite database used by the bot: `meetup_bot.sqlite3` in the project root. Use it during development when you need an empty set of registrations and analytics.

It deletes all SQLite-stored data, including registrations, funnel analytics, statuses, registration attempts, and any other local database data.

Do not use it on a production database or once real user data is important.

## Reset steps

```powershell
# Stop the bot first
Ctrl + C

# From the project root, run the reset script
.\reset_db.ps1

# When prompted, type exactly
RESET

# Start the bot again
python bot.py
```

After deletion, `python bot.py` recreates `meetup_bot.sqlite3` and its tables automatically.

## Database locked error

If the script says the database is locked or in use, the bot is probably still running. Stop it with `Ctrl + C`, wait for it to exit, and run `.\reset_db.ps1` again.
