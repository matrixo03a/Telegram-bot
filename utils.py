"""
Utility Functions
Helper functions for JSON operations, authorization, forwarding,
time parsing, folders, schedules – FULL VERSION
"""

import json
import os
import time
from datetime import datetime
from config import USERS_FILE, OWNERS, user_sessions


# ======================================================
# JSON HELPERS
# ======================================================

def load_json(file_path, default=None):
    if default is None:
        default = {}

    try:
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"⚠️ JSON load error ({file_path}): {e}")

    return default


def save_json(file_path, data):
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"❌ JSON save error ({file_path}): {e}")
        return False


# ======================================================
# AUTHORIZATION & USER INFO
# ======================================================

def is_authorized(user_id):
    users = load_json(USERS_FILE, {})
    return str(user_id) in users or user_id in OWNERS


def is_owner(user_id):
    return user_id in OWNERS


def get_user_plan(user_id):
    users = load_json(USERS_FILE, {})
    return users.get(str(user_id), {}).get("plan_days", 0)


def get_user_info(user_id):
    users = load_json(USERS_FILE, {})
    return users.get(str(user_id), {
        "plan_days": 0,
        "plan_type": "Free",
        "started": "N/A"
    })


# ======================================================
# TIME & FORMAT HELPERS
# ======================================================

def get_current_time():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def format_time_ago(timestamp):
    diff = time.time() - timestamp

    if diff < 60:
        return f"{int(diff)}s ago"
    elif diff < 3600:
        return f"{int(diff / 60)}m ago"
    elif diff < 86400:
        return f"{int(diff / 3600)}h ago"
    else:
        return f"{int(diff / 86400)}d ago"


# ======================================================
# CHAT / GROUP ID PARSER
# ======================================================

def extract_chat_id(text):
    """
    Accepts:
    - -100xxxxxxxxx
    - https://t.me/username
    - https://t.me/c/123456/78
    - username
    """
    text = str(text).strip()

    # Already numeric
    if text.startswith("-100"):
        return int(text)

    if text.startswith("-"):
        try:
            return int(text)
        except:
            pass

    if "t.me/" in text:
        text = text.replace("https://", "").replace("http://", "")
        text = text.replace("t.me/", "")

        # private channel
        if text.startswith("c/"):
            parts = text.split("/")
            return int("-100" + parts[1])

        # public channel
        return text.split("/")[0].replace("@", "")

    try:
        num = int(text)
        if num > 0:
            return int(f"-100{num}")
        return num
    except:
        return text.replace("@", "")


# ======================================================
# OTP HELPERS
# ======================================================

def is_valid_otp_format(otp):
    return "-" in otp and len(otp.replace("-", "")) >= 5


def sanitize_otp(otp):
    return otp.replace("-", "").strip()


# ======================================================
# SETTINGS HELPERS
# ======================================================

def get_user_settings(user_id, settings_file):
    data = load_json(settings_file, {})

    default = {
        "timezone": "UTC",
        "delay": 0,
        "simulation": "None",
        "forward_mode": "Copy"
    }

    user_settings = data.get(str(user_id), {})
    for k, v in default.items():
        user_settings.setdefault(k, v)

    return user_settings


def update_user_setting(user_id, settings_file, key, value):
    data = load_json(settings_file, {})
    data.setdefault(str(user_id), {})[key] = value
    return save_json(settings_file, data)


# ======================================================
# TIME PARSER
# ======================================================

def parse_time_string(time_str):
    time_str = time_str.strip()

    try:
        # AM / PM
        if "am" in time_str.lower() or "pm" in time_str.lower():
            t = time_str.replace(" ", "").upper()
            if "PM" in t:
                h, m = map(int, t.replace("PM", "").split(":"))
                if h != 12:
                    h += 12
            else:
                h, m = map(int, t.replace("AM", "").split(":"))
                if h == 12:
                    h = 0
            return {"type": "daily", "hour": h, "minute": m}

        # Date time
        if " " in time_str:
            dt = datetime.strptime(time_str, "%Y-%m-%d %H:%M")
            return {
                "type": "date",
                "datetime": dt,
                "hour": dt.hour,
                "minute": dt.minute
            }

        # 24h
        h, m = map(int, time_str.split(":"))
        return {"type": "daily", "hour": h, "minute": m}

    except:
        return None


def convert_to_12hour(hour, minute):
    period = "AM" if hour < 12 else "PM"
    h = hour % 12 or 12
    return f"{h}:{minute:02d} {period}"


# ======================================================
# FOLDER / GROUP HELPERS
# ======================================================

async def parse_groups_input(user_id, groups_input):
    group_list = [g.strip() for g in groups_input.split(",") if g.strip()]
    result = []

    for g in group_list:
        gid = extract_chat_id(g)

        if user_id in user_sessions:
            try:
                chat = await user_sessions[user_id].get_entity(gid)
                result.append({
                    "id": chat.id,
                    "title": chat.title,
                    "link": g
                })
            except:
                result.append({"id": gid, "title": str(gid), "link": g})
        else:
            result.append({"id": gid, "title": str(gid), "link": g})

    return result


async def get_all_groups_from_folders(user_id, folders_file):
    folders = load_json(folders_file, {}).get(str(user_id), {})
    groups = []

    for g_list in folders.values():
        for g in g_list:
            if g["id"] not in groups:
                groups.append(g["id"])

    return groups


async def get_groups_from_folder_names(user_id, folder_names, folders_file):
    folders = load_json(folders_file, {}).get(str(user_id), {})
    names = [f.strip() for f in folder_names.split(",")]
    result = []

    for n in names:
        for g in folders.get(n, []):
            if g["id"] not in result:
                result.append(g["id"])

    return result


# ======================================================
# POST FORWARDER
# ======================================================

async def forward_post_from_link(client, post_link, target_chat, mode="Copy"):
    try:
        post_link = post_link.replace("https://", "").replace("http://", "")
        post_link = post_link.replace("t.me/", "")

        if post_link.startswith("c/"):
            parts = post_link.split("/")
            channel_id = int("-100" + parts[1])
            message_id = int(parts[2])
        else:
            parts = post_link.split("/")
            channel = parts[0]
            message_id = int(parts[1])
            channel_id = (await client.get_entity(channel)).id

        msg = await client.get_messages(channel_id, ids=message_id)

        if mode == "Copy":
            if msg.media:
                await client.send_file(target_chat, msg.media, caption=msg.text or "")
            else:
                await client.send_message(target_chat, msg.text)
        else:
            await client.forward_messages(target_chat, msg.id, channel_id)

        return True
    except Exception as e:
        print(f"❌ Forward failed: {e}")
        return False