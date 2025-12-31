"""
Message Flow Handlers
Handles setup, folders, scheduler, broadcast and edit flows
FULL PRODUCTION VERSION
"""

from datetime import datetime
from telethon import events, Button
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError

from config import (
    DATA_DIR, SESSIONS_FILE, FOLDERS_FILE, SCHEDULES_FILE,
    SETTINGS_FILE, temp_data, user_sessions, LOGIN_SUCCESS_MSG,
    get_main_keyboard
)
from utils import (
    load_json, save_json, is_authorized,
    extract_chat_id, parse_time_string,
    convert_to_12hour, is_valid_otp_format, sanitize_otp
)


# =====================================================
# MAIN MESSAGE ROUTER
# =====================================================

async def message_flow_router(event):
    user_id = event.sender_id

    if user_id not in temp_data:
        return

    step = temp_data[user_id].get("step")
    text = event.raw_text.strip()

    if text == "/cancel":
        temp_data.pop(user_id, None)
        await event.respond("❌ **CANCELLED**")
        raise events.StopPropagation

    handlers = {
        "api_id": handle_api_id,
        "api_hash": handle_api_hash,
        "phone": handle_phone,
        "otp": handle_otp,
        "2fa": handle_2fa,
        "folder_name": handle_folder_name,
        "folder_groups": handle_folder_groups,
        "task_name": handle_task_name,
        "task_post": handle_task_post,
        "task_time": handle_task_time,
        "broadcast_content": handle_broadcast_content,
    }

    if step in handlers:
        await handlers[step](event)
        raise events.StopPropagation


# =====================================================
# SETUP FLOW
# =====================================================

async def handle_api_id(event):
    user_id = event.sender_id
    try:
        temp_data[user_id]["api_id"] = int(event.raw_text.strip())
        temp_data[user_id]["step"] = "api_hash"
        await event.respond("🔑 Send **API HASH**:")
    except:
        await event.respond("❌ Invalid API ID")


async def handle_api_hash(event):
    user_id = event.sender_id
    temp_data[user_id]["api_hash"] = event.raw_text.strip()
    temp_data[user_id]["step"] = "phone"
    await event.respond("📱 Send **PHONE NUMBER** with country code:")


async def handle_phone(event):
    user_id = event.sender_id
    phone = event.raw_text.strip()

    try:
        session = f"{DATA_DIR}/user_{user_id}"
        client = TelegramClient(
            session,
            temp_data[user_id]["api_id"],
            temp_data[user_id]["api_hash"]
        )
        await client.connect()
        sent = await client.send_code_request(phone)

        temp_data[user_id].update({
            "phone": phone,
            "client": client,
            "phone_hash": sent.phone_code_hash,
            "step": "otp"
        })

        await event.respond("📨 Send OTP like `1-2-3-4-5`")

    except Exception as e:
        temp_data.pop(user_id, None)
        await event.respond(f"❌ Error: `{e}`")


async def handle_otp(event):
    user_id = event.sender_id
    otp = event.raw_text.strip()

    if not is_valid_otp_format(otp):
        await event.respond("❌ OTP format wrong")
        return

    try:
        client = temp_data[user_id]["client"]
        await client.sign_in(
            temp_data[user_id]["phone"],
            sanitize_otp(otp),
            phone_code_hash=temp_data[user_id]["phone_hash"]
        )

        save_session(user_id)
        user_sessions[user_id] = client
        temp_data.pop(user_id, None)

        await event.respond(LOGIN_SUCCESS_MSG, buttons=get_main_keyboard())

    except SessionPasswordNeededError:
        temp_data[user_id]["step"] = "2fa"
        await event.respond("🔐 Send **2FA Password**")

    except PhoneCodeInvalidError:
        await event.respond("❌ Wrong OTP")

    except Exception as e:
        temp_data.pop(user_id, None)
        await event.respond(f"❌ Login failed: `{e}`")


async def handle_2fa(event):
    user_id = event.sender_id
    try:
        client = temp_data[user_id]["client"]
        await client.sign_in(password=event.raw_text.strip())

        save_session(user_id)
        user_sessions[user_id] = client
        temp_data.pop(user_id, None)

        await event.respond(LOGIN_SUCCESS_MSG, buttons=get_main_keyboard())
    except Exception as e:
        temp_data.pop(user_id, None)
        await event.respond(f"❌ 2FA Error: `{e}`")


def save_session(user_id):
    sessions = load_json(SESSIONS_FILE, {})
    sessions[str(user_id)] = {
        "logged_in": datetime.now().isoformat()
    }
    save_json(SESSIONS_FILE, sessions)


# =====================================================
# FOLDER FLOW
# =====================================================

async def handle_folder_name(event):
    user_id = event.sender_id
    temp_data[user_id]["folder"] = event.raw_text.strip()
    temp_data[user_id]["step"] = "folder_groups"
    await event.respond("📢 Send group links / IDs (comma separated)")


async def handle_folder_groups(event):
    user_id = event.sender_id
    folder = temp_data[user_id]["folder"]
    groups = [g.strip() for g in event.raw_text.split(",")]

    folders = load_json(FOLDERS_FILE, {})
    folders.setdefault(str(user_id), {})
    folders[str(user_id)][folder] = []

    for g in groups:
        gid = extract_chat_id(g)
        folders[str(user_id)][folder].append({
            "id": gid,
            "title": str(gid)
        })

    save_json(FOLDERS_FILE, folders)
    temp_data.pop(user_id, None)

    await event.respond(f"✅ Folder `{folder}` created")


# =====================================================
# SCHEDULER FLOW
# =====================================================

async def handle_task_name(event):
    user_id = event.sender_id
    temp_data[user_id]["task_name"] = event.raw_text.strip()
    temp_data[user_id]["step"] = "task_post"
    await event.respond("🔗 Send post link")


async def handle_task_post(event):
    user_id = event.sender_id
    temp_data[user_id]["post"] = event.raw_text.strip()
    temp_data[user_id]["step"] = "task_time"
    await event.respond("⏰ Send time (11:00 PM / 23:00)")


async def handle_task_time(event):
    user_id = event.sender_id
    times = event.raw_text.split(",")

    parsed = []
    display = []

    for t in times:
        p = parse_time_string(t.strip())
        if p:
            parsed.append(p)
            if p["type"] == "daily":
                display.append(convert_to_12hour(p["hour"], p["minute"]))

    schedules = load_json(SCHEDULES_FILE, {})
    schedules.setdefault(str(user_id), {})

    name = temp_data[user_id]["task_name"]
    schedules[str(user_id)][name] = {
        "post": temp_data[user_id]["post"],
        "times": display,
        "parsed_times": parsed,
        "target": "all",
        "created": datetime.now().isoformat()
    }

    save_json(SCHEDULES_FILE, schedules)
    temp_data.pop(user_id, None)

    await event.respond(f"✅ Schedule `{name}` created")


# =====================================================
# BROADCAST FLOW
# =====================================================

async def handle_broadcast_content(event):
    user_id = event.sender_id
    content = event.raw_text.strip()

    if user_id not in user_sessions:
        await event.respond("❌ Login required")
        temp_data.pop(user_id, None)
        return

    folders = load_json(FOLDERS_FILE, {}).get(str(user_id), {})
    groups = []

    for f in folders.values():
        for g in f:
            if g["id"] not in groups:
                groups.append(g["id"])

    success = 0
    for gid in groups:
        try:
            await user_sessions[user_id].send_message(gid, content)
            success += 1
        except:
            pass

    temp_data.pop(user_id, None)
    await event.respond(f"✅ Broadcast sent to {success} groups")


# =====================================================
# REGISTER
# =====================================================

def register_message_handlers(bot):
    bot.add_event_handler(
        message_flow_router,
        events.NewMessage(incoming=True)
    )
    print("✅ Message flow handlers registered")