"""
Message Flow Handlers - PART 1
✅ Setup flow + Folder handlers
✅ God Eye functions completely removed
"""

import re
import time
from datetime import datetime
from telethon import events, Button
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError

from config import (
    SESSIONS_FILE, SETTINGS_FILE, FOLDERS_FILE, SCHEDULES_FILE,
    DATA_DIR, user_sessions, temp_data, LOGIN_SUCCESS_MSG, get_main_keyboard
)
from utils import (
    is_authorized, load_json, save_json, 
    is_valid_otp_format, sanitize_otp, extract_chat_id,
    parse_time_string, convert_to_12hour, get_current_time
)


async def setup_flow_handler(event):
    """Handle all setup flow steps"""
    user_id = event.sender_id
    
    if user_id not in temp_data:
        return
    
    step = temp_data[user_id].get('step')
    
    if event.raw_text.strip() == '/cancel':
        del temp_data[user_id]
        await event.respond("❌ **CANCELLED**\n\nOperation cancelled successfully.")
        raise events.StopPropagation
    
    if step == 'api_id':
        await handle_api_id_step(event)
    elif step == 'api_hash':
        await handle_api_hash_step(event)
    elif step == 'phone':
        await handle_phone_step(event)
    elif step == 'otp':
        await handle_otp_step(event)
    elif step == '2fa':
        await handle_2fa_step(event)
    elif step == 'folder_name':
        await handle_folder_name_step(event)
    elif step == 'folder_groups':
        await handle_folder_groups_step(event)
    elif step == 'add_groups_to_folder':
        await handle_add_groups_to_folder_step(event)
    elif step == 'task_name':
        await handle_task_name_step(event)
    elif step == 'task_post':
        await handle_task_post_step(event)
    elif step == 'task_folder_choice':
        await handle_task_folder_choice_step(event)
    elif step == 'task_specific_groups':
        await handle_task_specific_groups_step(event)
    elif step == 'task_time':
        await handle_task_time_step(event)
    elif step == 'broadcast_content':
        await handle_broadcast_content_step(event)
    elif step == 'edit_schedule_name':
        await handle_edit_schedule_name_step(event)
    elif step == 'edit_schedule_post':
        await handle_edit_schedule_post_step(event)
    elif step == 'edit_schedule_time':
        await handle_edit_schedule_time_step(event)
    
    raise events.StopPropagation


# ============================================
# SETUP FLOW HANDLERS
# ============================================

async def handle_api_id_step(event):
    """Handle API ID input"""
    user_id = event.sender_id
    
    try:
        api_id = int(event.raw_text.strip())
        temp_data[user_id]['api_id'] = api_id
        temp_data[user_id]['step'] = 'api_hash'
        
        await event.respond(
            "✅ **API ID RECEIVED**\n\n"
            "🔑 Now send your **API HASH**:\n\n"
            "💡 Example: `1a2b3c4d5e6f7g8h9i0j`"
        )
    except ValueError:
        await event.respond(
            "❌ **INVALID API ID**\n\n"
            "Please send a valid number.\n\n"
            "💡 Example: `12345678`"
        )


async def handle_api_hash_step(event):
    """Handle API Hash input"""
    user_id = event.sender_id
    api_hash = event.raw_text.strip()
    
    temp_data[user_id]['api_hash'] = api_hash
    temp_data[user_id]['step'] = 'phone'
    
    await event.respond(
        "✅ **API HASH RECEIVED**\n\n"
        "📱 Now send your **PHONE NUMBER** (with country code):\n\n"
        "💡 Example: `+1234567890`\n"
        "⚠️ Make sure to include the `+` sign"
    )


async def handle_phone_step(event):
    """Handle phone number input"""
    user_id = event.sender_id
    phone = event.raw_text.strip()
    
    try:
        api_id = temp_data[user_id]['api_id']
        api_hash = temp_data[user_id]['api_hash']
        
        session_name = f"{DATA_DIR}/user_{user_id}"
        client = TelegramClient(session_name, api_id, api_hash)
        await client.connect()
        
        result = await client.send_code_request(phone)
        
        temp_data[user_id]['phone'] = phone
        temp_data[user_id]['phone_code_hash'] = result.phone_code_hash
        temp_data[user_id]['client'] = client
        temp_data[user_id]['step'] = 'otp'
        
        await event.respond(
            "📨 **OTP SENT**\n\n"
            "📢 Send the OTP code in this format:\n"
            "**Example:** `1-2-3-4-5`\n\n"
            "⚠️ **DO NOT** send as: `12345`\n"
            "✅ **CORRECT FORMAT:** `1-2-3-4-5`"
        )
    except Exception as e:
        await event.respond(
            f"❌ **ERROR**\n\n"
            f"Failed to send OTP: `{str(e)}`\n\n"
            "Please check your API credentials and try again with /setup"
        )
        if user_id in temp_data:
            del temp_data[user_id]


async def handle_otp_step(event):
    """Handle OTP input"""
    user_id = event.sender_id
    otp = event.raw_text.strip()
    
    if not is_valid_otp_format(otp):
        await event.respond(
            "❌ **WRONG FORMAT**\n\n"
            "Please send OTP as: `1-2-3-4-5`\n\n"
            "⚠️ Don't forget the dashes!"
        )
        return
    
    otp_code = sanitize_otp(otp)
    
    try:
        client = temp_data[user_id]['client']
        phone = temp_data[user_id]['phone']
        phone_code_hash = temp_data[user_id]['phone_code_hash']
        
        await client.sign_in(phone, otp_code, phone_code_hash=phone_code_hash)
        
        sessions = load_json(SESSIONS_FILE, {})
        sessions[str(user_id)] = {
            'api_id': temp_data[user_id]['api_id'],
            'api_hash': temp_data[user_id]['api_hash'],
            'phone': phone,
            'logged_in': datetime.now().isoformat()
        }
        save_json(SESSIONS_FILE, sessions)
        
        user_sessions[user_id] = client
        
        del temp_data[user_id]
        
        keyboard = get_main_keyboard()
        
        await event.respond(
            LOGIN_SUCCESS_MSG,
            buttons=keyboard
        )
        
    except SessionPasswordNeededError:
        temp_data[user_id]['step'] = '2fa'
        await event.respond(
            "🔐 **2FA ENABLED**\n\n"
            "🔒 Send your **2FA Password**:\n\n"
            "💡 This is your Cloud Password"
        )
    except PhoneCodeInvalidError:
        await event.respond(
            "❌ **INVALID OTP**\n\n"
            "The code you entered is incorrect.\n\n"
            "Please try again or type /cancel to restart."
        )
    except Exception as e:
        await event.respond(
            f"❌ **ERROR**\n\n"
            f"Login failed: `{str(e)}`\n\n"
            "Please restart setup with /setup"
        )
        if user_id in temp_data:
            del temp_data[user_id]


async def handle_2fa_step(event):
    """Handle 2FA password input"""
    user_id = event.sender_id
    password = event.raw_text.strip()
    
    try:
        client = temp_data[user_id]['client']
        
        await client.sign_in(password=password)
        
        sessions = load_json(SESSIONS_FILE, {})
        sessions[str(user_id)] = {
            'api_id': temp_data[user_id]['api_id'],
            'api_hash': temp_data[user_id]['api_hash'],
            'phone': temp_data[user_id]['phone'],
            'logged_in': datetime.now().isoformat()
        }
        save_json(SESSIONS_FILE, sessions)
        
        user_sessions[user_id] = client
        
        del temp_data[user_id]
        
        keyboard = get_main_keyboard()
        
        await event.respond(
            LOGIN_SUCCESS_MSG,
            buttons=keyboard
        )
        
    except Exception as e:
        await event.respond(
            f"❌ **WRONG PASSWORD**\n\n"
            f"Error: `{str(e)}`\n\n"
            "Please try again with /setup"
        )
        if user_id in temp_data:
            del temp_data[user_id]


# ============================================
# FOLDER HANDLERS
# ============================================

async def handle_folder_name_step(event):
    """Handle folder name input"""
    user_id = event.sender_id
    folder_name = event.raw_text.strip()
    
    temp_data[user_id]['folder_name'] = folder_name
    temp_data[user_id]['step'] = 'folder_groups'
    
    await event.respond(
        f"✅ **FOLDER NAME:** `{folder_name}`\n\n"
        "📢 Now send group links or IDs (comma-separated for multiple):\n\n"
        "💡 **Examples:**\n"
        "• Single: `https://t.me/mygroup`\n"
        "• Multiple: `https://t.me/group1, https://t.me/group2`\n"
        "• Mix: `-1001234567890, https://t.me/group2`\n\n"
        "⚠️ Private groups supported!"
    )


async def handle_folder_groups_step(event):
    """Handle folder groups input"""
    user_id = event.sender_id
    groups_input = event.raw_text.strip()
    folder_name = temp_data[user_id]['folder_name']
    
    group_list = [g.strip() for g in groups_input.split(',')]
    
    folders = load_json(FOLDERS_FILE, {})
    if str(user_id) not in folders:
        folders[str(user_id)] = {}
    
    validated_groups = []
    
    for group_input in group_list:
        group_id = extract_chat_id(group_input)
        
        if user_id in user_sessions:
            try:
                chat = await user_sessions[user_id].get_entity(group_id)
                chat_title = chat.title if hasattr(chat, 'title') else str(chat.id)
                validated_groups.append({
                    'id': chat.id,
                    'title': chat_title,
                    'link': group_input
                })
            except:
                validated_groups.append({
                    'id': group_id,
                    'title': str(group_id),
                    'link': group_input
                })
        else:
            validated_groups.append({
                'id': group_id,
                'title': str(group_id),
                'link': group_input
            })
    
    folders[str(user_id)][folder_name] = validated_groups
    save_json(FOLDERS_FILE, folders)
    
    del temp_data[user_id]
    
    group_names = "\n".join([f"• {g['title']}" for g in validated_groups])
    
    await event.respond(
        f"✅ **FOLDER CREATED**\n\n"
        f"📂 **Folder:** {folder_name}\n"
        f"📢 **Groups ({len(validated_groups)}):**\n{group_names}\n\n"
        "Type /start to return to main menu."
    )


async def handle_add_groups_to_folder_step(event):
    """Handle adding groups to existing folder"""
    user_id = event.sender_id
    groups_input = event.raw_text.strip()
    folder_name = temp_data[user_id]['folder_name']
    
    group_list = [g.strip() for g in groups_input.split(',')]
    
    folders = load_json(FOLDERS_FILE, {})
    if str(user_id) not in folders or folder_name not in folders[str(user_id)]:
        await event.respond("❌ Folder not found!")
        del temp_data[user_id]
        return
    
    existing_groups = folders[str(user_id)][folder_name]
    validated_groups = []
    
    for group_input in group_list:
        group_id = extract_chat_id(group_input)
        
        if any(g['id'] == group_id for g in existing_groups):
            continue
        
        if user_id in user_sessions:
            try:
                chat = await user_sessions[user_id].get_entity(group_id)
                chat_title = chat.title if hasattr(chat, 'title') else str(chat.id)
                validated_groups.append({
                    'id': chat.id,
                    'title': chat_title,
                    'link': group_input
                })
            except:
                validated_groups.append({
                    'id': group_id,
                    'title': f"Group {group_id}",
                    'link': group_input
                })
        else:
            validated_groups.append({
                'id': group_id,
                'title': f"Group {group_id}",
                'link': group_input
            })
    
    folders[str(user_id)][folder_name].extend(validated_groups)
    save_json(FOLDERS_FILE, folders)
    
    del temp_data[user_id]
    
    if validated_groups:
        group_names = "\n".join([f"• {g['title']}" for g in validated_groups])
        
        await event.respond(
            f"✅ **GROUPS ADDED**\n\n"
            f"📂 **Folder:** {folder_name}\n"
            f"📢 **Added ({len(validated_groups)}):**\n{group_names}\n\n"
            f"📊 **Total Groups:** {len(folders[str(user_id)][folder_name])}\n\n"
            "Type /start to return to main menu."
        )
    else:
        await event.respond(
            f"⚠️ **NO NEW GROUPS ADDED**\n\n"
            f"All groups already exist in `{folder_name}`\n\n"
            "Type /start to return to main menu."
        )
"""
Message Flow Handlers - PART 2
✅ Schedule handlers + Broadcast handlers
✅ Text button handler + Registration
✅ God Eye functions completely removed
"""

# ============================================
# SCHEDULE HANDLERS
# ============================================

async def handle_task_name_step(event):
    """Handle task name input - WITH TIMEZONE CHECK"""
    user_id = event.sender_id
    text = event.raw_text.strip()
    
    from utils import get_user_settings
    
    user_settings = get_user_settings(user_id, SETTINGS_FILE)
    user_timezone = user_settings.get('timezone', 'UTC')
    
    if user_timezone == 'UTC' or not user_timezone:
        keyboard = [
            [Button.inline("🌍 Set Timezone Now", b"timezone")],
            [Button.inline("❌ Cancel", b"cancel_task")]
        ]
        
        await event.respond(
            "⚠️ **TIMEZONE NOT CONFIGURED**\n\n"
            "─────────────────────\n\n"
            "🌍 Before creating a schedule, you must set your timezone to ensure posts are sent at the correct time.\n\n"
            "⏰ **Why is this important?**\n"
            "• Scheduled posts use your timezone\n"
            "• Ensures accurate post timing\n"
            "• Prevents posting at wrong hours\n\n"
            "💡 **How to set timezone:**\n"
            "1. Click '🌍 Set Timezone Now' below\n"
            "2. Select your timezone from the list\n"
            "3. Return and create your schedule\n\n"
            "─────────────────────\n"
            "⚠️ **Action Required:** Please set your timezone first!",
            buttons=keyboard
        )
        
        if user_id in temp_data:
            del temp_data[user_id]
        return
    
    if text == '/skip':
        schedules = load_json(SCHEDULES_FILE, {})
        user_schedules = schedules.get(str(user_id), {})
        task_count = len(user_schedules) + 1
        task_name = f"Task-{task_count}"
    else:
        task_name = text
    
    temp_data[user_id]['task_name'] = task_name
    temp_data[user_id]['step'] = 'task_post'
    
    await event.respond(
        f"✅ **TASK NAME:** `{task_name}`\n\n"
        f"🌍 **Timezone:** `{user_timezone}`\n\n"
        "🔗 Now send the **POST LINK** to forward:\n\n"
        "💡 **Example:** `https://t.me/channel/123`\n"
        "⚠️ Must be a valid Telegram post link"
    )


async def handle_task_post_step(event):
    """Handle task post link input"""
    user_id = event.sender_id
    post_link = event.raw_text.strip()
    
    if 't.me/' not in post_link and 'telegram.me/' not in post_link:
        await event.respond(
            "❌ **INVALID LINK**\n\n"
            "Please send a valid Telegram post link.\n\n"
            "💡 Example: `https://t.me/channel/123`"
        )
        return
    
    temp_data[user_id]['task_post'] = post_link
    temp_data[user_id]['step'] = 'task_folder_choice'
    
    keyboard = [
        [Button.inline("📂 Specific Folder", b"task_target:folder")],
        [Button.inline("📢 Specific Groups", b"task_target:groups")],
        [Button.inline("🌍 All Groups", b"task_target:all")],
        [Button.inline("❌ Cancel", b"cancel_task")]
    ]
    
    await event.respond(
        f"✅ **POST LINK SAVED**\n\n"
        "🎯 **Choose Target:**\n\n"
        "Where do you want to forward this post?",
        buttons=keyboard
    )


async def handle_task_folder_choice_step(event):
    """Handle specific folder selection"""
    user_id = event.sender_id
    folder_names = event.raw_text.strip()
    
    temp_data[user_id]['task_folders'] = folder_names
    temp_data[user_id]['step'] = 'task_time'
    
    await event.respond(
        f"✅ **FOLDER(S) SELECTED:** `{folder_names}`\n\n"
        "⏰ Now send the **TIME(S)** to post:\n\n"
        "💡 **Formats Supported:**\n"
        "• 12-hour: `11:00 PM, 2:30 PM`\n"
        "• 24-hour: `14:30, 20:00`\n"
        "• With date: `2024-12-25 10:00`"
    )


async def handle_task_specific_groups_step(event):
    """Handle specific groups input"""
    user_id = event.sender_id
    groups_input = event.raw_text.strip()
    
    temp_data[user_id]['task_groups'] = groups_input
    temp_data[user_id]['step'] = 'task_time'
    
    await event.respond(
        f"✅ **GROUP(S) SELECTED**\n\n"
        "⏰ Now send the **TIME(S)** to post:\n\n"
        "💡 **Formats Supported:**\n"
        "• 12-hour: `11:00 PM, 2:30 PM`\n"
        "• 24-hour: `14:30, 20:00`\n"
        "• With date: `2024-12-25 10:00`"
    )


async def handle_task_time_step(event):
    """Handle task time input"""
    user_id = event.sender_id
    time_input = event.raw_text.strip()
    
    time_strings = [t.strip() for t in time_input.split(',')]
    parsed_times = []
    display_times = []
    
    for time_str in time_strings:
        parsed = parse_time_string(time_str)
        if parsed:
            parsed_times.append(parsed)
            if parsed['type'] == 'daily':
                display_times.append(convert_to_12hour(parsed['hour'], parsed['minute']))
            else:
                display_times.append(time_str)
    
    if not parsed_times:
        await event.respond(
            "❌ **INVALID TIME FORMAT**\n\n"
            "Please use:\n"
            "• 12-hour: `11:00 PM, 2:30 PM`\n"
            "• 24-hour: `23:00, 14:30`\n"
            "• With date: `2024-12-25 10:00`"
        )
        return
    
    schedules = load_json(SCHEDULES_FILE, {})
    if str(user_id) not in schedules:
        schedules[str(user_id)] = {}
    
    task_name = temp_data[user_id]['task_name']
    task_post = temp_data[user_id]['task_post']
    task_target = temp_data[user_id].get('task_target', 'all')
    task_folders = temp_data[user_id].get('task_folders', '')
    task_groups = temp_data[user_id].get('task_groups', '')
    
    schedules[str(user_id)][task_name] = {
        'post': task_post,
        'target': task_target,
        'folders': task_folders,
        'groups': task_groups,
        'times': display_times,
        'parsed_times': parsed_times,
        'created': datetime.now().isoformat(),
        'last_run': None,
        'next_run': None
    }
    save_json(SCHEDULES_FILE, schedules)
    
    del temp_data[user_id]
    
    times_list = "\n".join([f"• {t}" for t in display_times])
    
    await event.respond(
        f"✅ **SCHEDULE CREATED**\n\n"
        f"📋 **Task:** {task_name}\n"
        f"🔗 **Post:** {task_post[:50]}...\n"
        f"🎯 **Target:** {task_target}\n"
        f"⏰ **Times ({len(display_times)}):**\n{times_list}\n\n"
        f"🚀 Scheduler will auto-post at these times!\n\n"
        "Type /start to return to main menu."
    )


# ============================================
# BROADCAST & EDIT HANDLERS
# ============================================

async def handle_broadcast_content_step(event):
    """Handle broadcast content input"""
    user_id = event.sender_id
    content = event.raw_text.strip()
    
    broadcast_type = temp_data[user_id].get('broadcast_type', 'message')
    
    temp_data[user_id]['broadcast_content'] = content
    temp_data[user_id]['step'] = 'broadcast_target'
    
    keyboard = [
        [Button.inline("📂 Specific Folder", b"bc_target:folder")],
        [Button.inline("📢 Specific Groups", b"bc_target:groups")],
        [Button.inline("🌍 All Groups", b"bc_target:all")],
        [Button.inline("❌ Cancel", b"cancel_broadcast")]
    ]
    
    content_preview = content[:50] + "..." if len(content) > 50 else content
    
    await event.respond(
        f"✅ **CONTENT SAVED**\n\n"
        f"📝 Preview: `{content_preview}`\n\n"
        "🎯 **Choose Target:**\n\n"
        "Where do you want to broadcast?",
        buttons=keyboard
    )


async def handle_edit_schedule_name_step(event):
    """Handle editing schedule name"""
    user_id = event.sender_id
    new_name = event.raw_text.strip()
    old_name = temp_data[user_id]['old_schedule_name']
    
    schedules = load_json(SCHEDULES_FILE, {})
    if str(user_id) in schedules and old_name in schedules[str(user_id)]:
        schedules[str(user_id)][new_name] = schedules[str(user_id)].pop(old_name)
        save_json(SCHEDULES_FILE, schedules)
        
        del temp_data[user_id]
        
        await event.respond(
            f"✅ **NAME UPDATED**\n\n"
            f"Old: `{old_name}`\n"
            f"New: `{new_name}`\n\n"
            "Type /start to return to main menu."
        )
    else:
        await event.respond("❌ Schedule not found!")


async def handle_edit_schedule_post_step(event):
    """Handle editing schedule post link"""
    user_id = event.sender_id
    new_post = event.raw_text.strip()
    schedule_name = temp_data[user_id]['schedule_name']
    
    if 't.me/' not in new_post and 'telegram.me/' not in new_post:
        await event.respond("❌ Invalid Telegram link!")
        return
    
    schedules = load_json(SCHEDULES_FILE, {})
    if str(user_id) in schedules and schedule_name in schedules[str(user_id)]:
        schedules[str(user_id)][schedule_name]['post'] = new_post
        save_json(SCHEDULES_FILE, schedules)
        
        del temp_data[user_id]
        
        await event.respond(
            f"✅ **POST UPDATED**\n\n"
            f"New post: {new_post[:50]}...\n\n"
            "Type /start to return to main menu."
        )


async def handle_edit_schedule_time_step(event):
    """Handle editing schedule times"""
    user_id = event.sender_id
    time_input = event.raw_text.strip()
    schedule_name = temp_data[user_id]['schedule_name']
    
    time_strings = [t.strip() for t in time_input.split(',')]
    parsed_times = []
    display_times = []
    
    for time_str in time_strings:
        parsed = parse_time_string(time_str)
        if parsed:
            parsed_times.append(parsed)
            if parsed['type'] == 'daily':
                display_times.append(convert_to_12hour(parsed['hour'], parsed['minute']))
            else:
                display_times.append(time_str)
    
    if not parsed_times:
        await event.respond("❌ Invalid time format!")
        return
    
    schedules = load_json(SCHEDULES_FILE, {})
    if str(user_id) in schedules and schedule_name in schedules[str(user_id)]:
        schedules[str(user_id)][schedule_name]['times'] = display_times
        schedules[str(user_id)][schedule_name]['parsed_times'] = parsed_times
        save_json(SCHEDULES_FILE, schedules)
        
        del temp_data[user_id]
        
        times_list = "\n".join([f"• {t}" for t in display_times])
        await event.respond(
            f"✅ **TIMES UPDATED**\n\n"
            f"New times:\n{times_list}\n\n"
            "Type /start to return to main menu."
        )


# ============================================
# TEXT MESSAGE HANDLER (KEYBOARD BUTTONS)
# ============================================

async def text_message_handler(event):
    """Handle text messages from keyboard buttons"""
    user_id = event.sender_id
    text = event.raw_text.strip()
    
    if user_id in temp_data:
        return
    
    if not is_authorized(user_id):
        return
    
    button_map = {
        "📂 Folders": "folders",
        "⏰ Scheduler": "scheduler",
        "📢 Broadcast": "broadcast",
        "🌍 Timezone": "timezone",
        "⚙️ Console": "console",
        "💎 Plan": "plan",
        "❓ Help": "help",
        "💬 Support": "support"
    }
    
    if text in button_map:
        class FakeCallbackEvent:
            def __init__(self, message_event, callback_data):
                self.sender_id = message_event.sender_id
                self.message_event = message_event
                self.data = callback_data.encode()
            
            async def edit(self, *args, **kwargs):
                await self.message_event.respond(*args, **kwargs)
            
            async def answer(self, *args, **kwargs):
                pass
        
        fake_event = FakeCallbackEvent(event, button_map[text])
        
        from callbacks import callback_handler
        await callback_handler(fake_event, event.client)
        
        raise events.StopPropagation


# ============================================
# REGISTER ALL MESSAGE HANDLERS
# ============================================

def register_message_handlers(bot):
    """Register all message handlers"""
    
    # Setup flow handler
    bot.add_event_handler(
        setup_flow_handler,
        events.NewMessage(incoming=True, func=lambda e: e.sender_id in temp_data)
    )
    
    # Text button handler
    bot.add_event_handler(
        text_message_handler,
        events.NewMessage(incoming=True, func=lambda e: not e.raw_text.startswith('/') and e.sender_id not in temp_data)
    )
    
    print("✅ Message flow handlers registered")