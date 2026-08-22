# Telegram Bot Commands

## Command registration audit

- No commands are registered through `BotCommand` or `bot.set_my_commands`.
- All slash commands are implemented with aiogram `Command(...)` handlers.
- No slash commands are detected manually from message text.
- Registration and event actions use reply or inline buttons; they are not slash commands.

## User commands

### `/start`

- **Example:** `/start`
- **Access level:** User
- **Description:** Starts or restarts the registration entry flow, clears any active registration state, and records the registration-start funnel event.
- **Required arguments:** None.
- **Expected output:** An introduction and a reply button to begin registration.

### `/cancel`

- **Example:** `/cancel`
- **Access level:** User
- **Description:** Cancels an in-progress registration flow.
- **Required arguments:** None.
- **Expected output:** Confirms cancellation and removes the reply keyboard. If no registration is active, reports that instead.

### `/me`

- **Example:** `/me`
- **Access level:** User
- **Description:** Shows the caller's saved registration profile.
- **Required arguments:** None.
- **Expected output:** Name, age, gender, join reason, and registration status. Older saved registrations also show any previously collected non-empty fields. Unregistered users are directed to `/start`.

### `/whoami`

- **Example:** `/whoami`
- **Access level:** User
- **Description:** Returns the caller's numeric Telegram user ID. This is a diagnostic/setup command useful for configuring `ADMIN_IDS`.
- **Required arguments:** None.
- **Expected output:** The caller's numeric Telegram ID.

## Admin-only commands

All commands in this section require the caller's numeric Telegram ID to be present in `ADMIN_IDS`.

### `/registrations`

- **Example:** `/registrations`
- **Access level:** Admin only
- **Description:** Exports all saved registrations.
- **Required arguments:** None.
- **Expected output:** A UTF-8 CSV file named `registrations.csv`, including registration details and phone numbers, plus the registration count in its caption.

### `/users`

- **Example:** `/users`
- **Access level:** Admin only
- **Description:** Shows all registered users in a numbered list. The number can be used with `/select`.
- **Required arguments:** None.
- **Expected output:** Each user's list number, first name, and Telegram ID. Reports when no registrations exist.

### `/funnel`

- **Example:** `/funnel`
- **Access level:** Admin only
- **Description:** Shows registration funnel analytics.
- **Required arguments:** None.
- **Expected output:** Unique-user counts for the streamlined registration stages and the overall completion rate. Historical funnel events remain stored but are not part of this report.

### `/create_event`

- **Example:** `/create_event`
- **Access level:** Admin only
- **Description:** Starts the event-creation conversation.
- **Required arguments:** None. The bot asks for title, date, time, location name, address, optional latitude/longitude, and an invitation message.
- **Expected output:** Sequential prompts followed by a confirmation containing the new event ID. Send `-` at the latitude prompt to omit both coordinates.

### `/select_user`

- **Example:** `/select_user 123456 1`
- **Access level:** Admin only
- **Description:** Adds a registered Telegram user to an event directly by Telegram user ID.
- **Required arguments:** `user_id`, `event_id`.
- **Expected output:** Confirms that the user was added with status `invited`. Returns an error if the user is not registered or the event does not exist. Re-adding an existing member resets their status to `invited`.

### `/select`

- **Example:** `/select 2 1`
- **Access level:** Admin only
- **Description:** Adds a user to an event by the number currently shown in `/users`.
- **Required arguments:** `user_number`, `event_id`.
- **Expected output:** Confirms that the selected user was added with status `invited`. Returns an error for an invalid list number or unknown event.

### `/preview_event`

- **Example:** `/preview_event 1`
- **Access level:** Admin only
- **Description:** Shows the full event preview without sending invitations.
- **Required arguments:** `event_id`.
- **Expected output:** Event title, date, time, location name, address, coordinate text, invited-user count, and the exact invitation text. If both coordinates exist, sends a Telegram location to the requesting admin after the text preview.

### `/send_event`

- **Example:** `/send_event 1`
- **Access level:** Admin only
- **Description:** Opens a confirmation preview before invitations are sent to members whose current status is `invited`.
- **Required arguments:** `event_id`.
- **Expected output:** The same preview as `/preview_event`, followed by **Confirm Send** and **Cancel** buttons. No invitation is sent until an admin confirms. After confirmation, the admin receives successful and failed delivery counts.

### `/event_members`

- **Example:** `/event_members 1`
- **Access level:** Admin only
- **Description:** Shows the roster for an event.
- **Required arguments:** `event_id`.
- **Expected output:** Each selected user's name, Telegram ID, and membership status (`invited`, `confirmed`, or `declined`). Reports when the event does not exist or has no selected users.

### `/event_users`

- **Example:** `/event_users 1`
- **Access level:** Admin only
- **Description:** Shows the event roster. This currently has the same behavior as `/event_members`.
- **Required arguments:** `event_id`.
- **Expected output:** Each selected user's name, Telegram ID, and membership status (`invited`, `confirmed`, or `declined`). Reports when the event does not exist or has no selected users.

## Inline callback actions

These are inline buttons, not slash commands.

### `✅ میام`

- **Access level:** Invited event member
- **Description:** Confirms attendance for an event invitation.
- **Required arguments:** None.
- **Expected output:** Changes the membership status to `confirmed`, confirms the action, and removes the invitation buttons.

### `❌ نمی‌تونم بیام`

- **Access level:** Invited event member
- **Description:** Declines attendance for an event invitation.
- **Required arguments:** None.
- **Expected output:** Changes the membership status to `declined`, confirms the action, and removes the invitation buttons.

### `✅ Confirm Send`

- **Access level:** Admin only
- **Description:** Confirms the `/send_event` preview and sends invitations to members whose status is still `invited`.
- **Required arguments:** None.
- **Expected output:** Removes the confirmation buttons, sends each invitation, sends locations where coordinates exist, and reports delivery totals to the admin.

### `❌ Cancel`

- **Access level:** Admin only
- **Description:** Cancels a pending invitation-send confirmation.
- **Required arguments:** None.
- **Expected output:** Removes the confirmation buttons and sends no invitations.

# Command Coverage Check

## Commands implemented in code but missing from this document

None. This document covers all current aiogram command handlers.

## Commands documented in this document but missing implementation

None.

## Notes for future development

- `/event_members` and `/event_users` are currently equivalent roster commands.
- Invitations include a Telegram support link (`https://t.me/amirmahq`).
- Because no `BotCommand` list is registered, Telegram clients may not automatically show these commands in the command menu.
