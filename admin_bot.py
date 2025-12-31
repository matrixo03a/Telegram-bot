"""
ADMIN BOT
Full Admin Management Panel
"""

import asyncio
import json
import os
from datetime import datetime
from telethon import TelegramClient, events, Button

# ============================================
# ADMIN BOT CONFIG (UPDATED)
# ============================================

ADMIN_BOT_TOKEN = "8456691972:AAGI_Y5pSZhZL5XXEssm2Yi4CI2pEGzBLEI"
ADMIN_API_ID = 36363448
ADMIN_API_HASH = "2920b3f570b33122db81fde2df17f6ce"

SUPER_ADMINS = [5510835149]

DATA_DIR = "bot_data"
USERS_FILE = f"{DATA_DIR}/users.json"
ADMINS_FILE = f"{DATA_DIR}/admins.json"

os.makedirs(DATA_DIR, exist_ok=True)

# ============================================
# JSON HELPERS
# ============================================

def load_json(path, default=None):
    if default is None:
        default = {}
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except:
        pass
    return default


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


# ============================================
# AUTH CHECK
# ============================================

def is_super_admin(uid):
    return uid in SUPER_ADMINS


def is_admin(uid):
    admins = load_json(ADMINS_FILE, {})
    return str(uid) in admins or is_super_admin(uid)


# ============================================
# TEMP STORAGE
# ============================================

temp_admin = {}

# ============================================
# START PANEL
# ============================================

@events.register(events.NewMessage(pattern="/start"))
async def start_handler(event):
    uid = event.sender_id

    if not is_admin(uid):
        await event.respond("🚫 Access denied")
        return

    users = load_json(USERS_FILE, {})
    admins = load_json(ADMINS_FILE, {})

    text = (
        "👑 **ADMIN PANEL**\n\n"
        f"👤 Admin: `{uid}`\n"
        f"👥 Users: `{len(users)}`\n"
        f"🛡️ Admins: `{len(admins)}`\n"
        f"🕒 Time: `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`"
    )

    keyboard = [
        [Button.text("➕ Add User"), Button.text("📋 View Users")],
        [Button.text("💎 Set Plan"), Button.text("🗑️ Delete User")],
        [Button.text("📢 Broadcast")]
    ]

    if is_super_admin(uid):
        keyboard.append([Button.text("👨‍💼 Add Admin"), Button.text("❌ Remove Admin")])

    await event.respond(text, buttons=keyboard, resize=True)


# ============================================
# BUTTON HANDLER
# ============================================

@events.register(events.NewMessage)
async def button_handler(event):
    uid = event.sender_id
    text = event.raw_text.strip()

    if not is_admin(uid):
        return

    if text == "➕ Add User":
        temp_admin[uid] = "add_user"
        await event.respond("Send USER ID to add:")

    elif text == "📋 View Users":
        users = load_json(USERS_FILE, {})
        msg = "📋 **USERS LIST**\n\n"
        for u, d in users.items():
            msg += f"• `{u}` — {d.get('plan_type','Free')} ({d.get('plan_days',0)}d)\n"
        await event.respond(msg or "No users")

    elif text == "💎 Set Plan":
        temp_admin[uid] = "set_plan"
        await event.respond("Format:\n`USER_ID PLAN DAYS`\nExample:\n`123 Premium 30`")

    elif text == "🗑️ Delete User":
        temp_admin[uid] = "delete_user"
        await event.respond("Send USER ID to delete:")

    elif text == "👨‍💼 Add Admin" and is_super_admin(uid):
        temp_admin[uid] = "add_admin"
        await event.respond("Send ADMIN ID:")

    elif text == "❌ Remove Admin" and is_super_admin(uid):
        temp_admin[uid] = "remove_admin"
        admins = load_json(ADMINS_FILE, {})
        msg = "Admins:\n"
        for a in admins:
            msg += f"• `{a}`\n"
        await event.respond(msg)

    elif text == "📢 Broadcast":
        temp_admin[uid] = "broadcast"
        await event.respond("Send broadcast message:")


# ============================================
# INPUT HANDLER
# ============================================

@events.register(events.NewMessage)
async def input_handler(event):
    uid = event.sender_id
    if uid not in temp_admin:
        return

    action = temp_admin[uid]
    text = event.raw_text.strip()

    users = load_json(USERS_FILE, {})
    admins = load_json(ADMINS_FILE, {})

    try:
        if action == "add_user":
            users[text] = {
                "plan_type": "Free Trial",
                "plan_days": 3,
                "started": datetime.now().isoformat()
            }
            save_json(USERS_FILE, users)
            await event.respond("✅ User added")

        elif action == "set_plan":
            uid2, plan, days = text.split()
            users[uid2]["plan_type"] = plan
            users[uid2]["plan_days"] = int(days)
            save_json(USERS_FILE, users)
            await event.respond("✅ Plan updated")

        elif action == "delete_user":
            users.pop(text, None)
            save_json(USERS_FILE, users)
            await event.respond("✅ User deleted")

        elif action == "add_admin":
            admins[text] = {"added": datetime.now().isoformat()}
            save_json(ADMINS_FILE, admins)
            await event.respond("✅ Admin added")

        elif action == "remove_admin":
            admins.pop(text, None)
            save_json(ADMINS_FILE, admins)
            await event.respond("✅ Admin removed")

        elif action == "broadcast":
            sent = 0
            for u in users:
                try:
                    await event.client.send_message(int(u), text)
                    sent += 1
                except:
                    pass
            await event.respond(f"✅ Broadcast sent to {sent} users")

    except Exception as e:
        await event.respond(f"❌ Error: {e}")

    temp_admin.pop(uid, None)


# ============================================
# MAIN
# ============================================

async def main():
    bot = TelegramClient("admin_bot", ADMIN_API_ID, ADMIN_API_HASH)
    await bot.start(bot_token=ADMIN_BOT_TOKEN)
    print("✅ Admin bot running")
    await bot.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(main())