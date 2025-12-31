"""
Command Handlers
FULL PRODUCTION VERSION
God Eye REMOVED
"""

import asyncio
import time
from datetime import datetime
from telethon import events, Button

from config import (
    OWNERS, UNAUTHORIZED_MSG, SETUP_START_MSG, LOGIN_SUCCESS_MSG,
    SESSIONS_FILE, get_main_keyboard, user_sessions, temp_data, DATA_DIR
)
from utils import (
    is_authorized, is_owner, get_user_plan,
    get_current_time, load_json, save_json
)

# ======================================================
# /start
# ======================================================

async def start_handler(event):
    user_id = event.sender_id

    if not is_authorized(user_id):
        keyboard = [
            [Button.url("👤 Admin", "https://t.me/NEOECHOO")]
        ]
        await event.respond(UNAUTHORIZED_MSG, buttons=keyboard)
        return

    logged_in = str(user_id) in load_json(SESSIONS_FILE, {})

    msg = await event.respond(
        "⚡ **INITIALIZING SYSTEM**\n\n"
        "`▰▱▱▱▱▱▱▱▱▱` 10%"
    )

    for p in [30, 50, 70, 100]:
        await asyncio.sleep(0.4)
        bar = "▰" * (p // 10) + "▱" * (10 - p // 10)
        await msg.edit(f"⚡ **INITIALIZING SYSTEM**\n\n`{bar}` {p}%")

    start_time = time.time()
    await event.client.get_me()
    ping = round((time.time() - start_time) * 1000, 2)

    plan_days = get_user_plan(user_id)
    status = "🟢 CONNECTED" if logged_in else "🔴 NOT CONNECTED"
    setup_hint = "" if logged_in else "\n\n⚠️ Use /setup to login"

    text = (
        "╔════════════════════╗\n"
        "║ 🤖 AUTO FORWARDER ║\n"
        "╚════════════════════╝\n\n"
        f"👤 User ID: `{user_id}`\n"
        f"📡 Status: {status}\n"
        f"💎 Plan: `{plan_days} days`\n"
        f"📶 Ping: `{ping} ms`\n"
        f"🕐 Time: `{get_current_time()}`"
        f"{setup_hint}"
    )

    await msg.edit(text, buttons=get_main_keyboard() if logged_in else None)


# ======================================================
# /setup
# ======================================================

async def setup_handler(event):
    user_id = event.sender_id

    if not is_authorized(user_id):
        return

    sessions = load_json(SESSIONS_FILE, {})
    if str(user_id) in sessions:
        await event.respond(
            "✅ **ALREADY LOGGED IN**\n\n"
            "Use /logout if you want to reconnect."
        )
        return

    temp_data[user_id] = {"step": "api_id"}
    await event.respond(SETUP_START_MSG)


# ======================================================
# /logout
# ======================================================

async def logout_handler(event):
    user_id = event.sender_id

    if not is_authorized(user_id):
        return

    sessions = load_json(SESSIONS_FILE, {})
    if str(user_id) not in sessions:
        await event.respond("❌ You are not logged in.")
        return

    keyboard = [
        [Button.inline("✅ Confirm Logout", b"confirm_logout")],
        [Button.inline("❌ Cancel", b"cancel_logout")]
    ]

    await event.respond(
        "⚠️ **LOGOUT CONFIRMATION**\n\n"
        "Are you sure?",
        buttons=keyboard
    )


# ======================================================
# /cancel
# ======================================================

async def cancel_handler(event):
    user_id = event.sender_id

    if user_id in temp_data:
        del temp_data[user_id]
        await event.respond("❌ Operation cancelled.")
    else:
        await event.respond("ℹ️ No active process.")


# ======================================================
# /help
# ======================================================

async def help_handler(event):
    user_id = event.sender_id

    if not is_authorized(user_id):
        return

    help_text = (
        "❓ **HELP MENU**\n\n"
        "📂 Folders – Manage group folders\n"
        "⏰ Scheduler – Auto post scheduling\n"
        "📢 Broadcast – Instant posting\n"
        "🌍 Timezone – Set timezone\n"
        "⚙️ Console – Forward settings\n"
        "💎 Plan – View plan\n\n"
        "📌 Commands:\n"
        "/start\n"
        "/setup\n"
        "/logout\n"
        "/cancel\n"
        "/help"
    )

    await event.respond(help_text)


# ======================================================
# REGISTER
# ======================================================

def register_command_handlers(bot):
    bot.add_event_handler(start_handler, events.NewMessage(pattern="/start"))
    bot.add_event_handler(setup_handler, events.NewMessage(pattern="/setup"))
    bot.add_event_handler(logout_handler, events.NewMessage(pattern="/logout"))
    bot.add_event_handler(cancel_handler, events.NewMessage(pattern="/cancel"))
    bot.add_event_handler(help_handler, events.NewMessage(pattern="/help"))

    print("✅ Command handlers registered")