import time
from datetime import datetime
from telethon import events, Button

from config import (
    OWNERS, SESSIONS_FILE, SETTINGS_FILE, FOLDERS_FILE, 
    SCHEDULES_FILE, TIMEZONES, DELAY_OPTIONS, SIMULATION_TYPES,
    FORWARD_MODES, get_main_keyboard, user_sessions, temp_data
)
from utils import (
    is_authorized, get_user_plan, get_user_info, get_user_settings,
    update_user_setting, load_json, save_json, is_logged_in,
    get_current_time, get_status_emoji, get_all_groups_from_folders,
    get_groups_from_folder_names, forward_post_from_link
)


# ============================================
# BACK TO MAIN MENU
# ============================================

async def handle_back_main(event, bot):
    """Handle back to main menu"""
    await event.answer()
    
    user_id = event.sender_id
    logged_in = is_logged_in(user_id, SESSIONS_FILE)
    
    plan_days = get_user_plan(user_id)
    start_time = time.time()
    await bot.get_me()
    ping = round((time.time() - start_time) * 1000, 2)
    
    status = "🟢 **CONNECTED**" if logged_in else "🔴 **NOT CONNECTED**"
    setup_text = "" if logged_in else "\n\n⚠️ To connect your account, type /setup"
    
    welcome_text = (
        "╔═══════════════════╗\n"
        "║  🤖 **AUTO FORWARDER**  ║\n"
        "╚═══════════════════╝\n\n"
        f"👤 **User:** `{user_id}`\n"
        f"🎯 **Status:** {status}\n"
        f"📡 **Ping:** `{ping}ms`\n"
        f"⏱️ **Latency:** `{ping/1000:.3f}s`\n"
        f"💎 **Plan:** `{plan_days} days`\n"
        f"🕐 **Time:** `{get_current_time()}`"
        f"{setup_text}\n\n"
        "────────────────────\n"
        "⚡ **POWERED BY SHADOW FLEX**"
    )
    
    keyboard = get_main_keyboard() if logged_in else None
    await event.edit(welcome_text, buttons=keyboard)


# ============================================
# FOLDERS HANDLERS
# ============================================

async def handle_folders(event):
    """Handle folders menu"""
    await event.answer()
    
    user_id = event.sender_id
    folders = load_json(FOLDERS_FILE, {}).get(str(user_id), {})
    
    if not folders:
        text = (
            "📂 **FOLDERS**\n\n"
            "❌ No folders created yet.\n\n"
            "💡 Click below to create your first folder!"
        )
        keyboard = [
            [Button.inline("➕ Add Folder", b"add_folder")],
            [Button.inline("🔙 Back", b"back_main")]
        ]
    else:
        text = "📂 **YOUR FOLDERS**\n\n"
        keyboard = []
        for folder_name in folders.keys():
            group_count = len(folders[folder_name])
            text += f"📁 {folder_name} ({group_count} groups)\n"
            keyboard.append([Button.inline(f"📁 {folder_name}", f"view_folder:{folder_name}".encode())])
        keyboard.append([Button.inline("➕ Add Folder", b"add_folder")])
        keyboard.append([Button.inline("🔙 Back", b"back_main")])
    
    await event.edit(text, buttons=keyboard)


async def handle_add_folder(event):
    """Handle add folder button"""
    await event.answer()
    
    user_id = event.sender_id
    temp_data[user_id] = {'step': 'folder_name'}
    
    await event.edit(
        "📂 **CREATE NEW FOLDER**\n\n"
        "📝 Send a name for your folder:\n\n"
        "💡 Example: `Important Groups`\n\n"
        "⚠️ Type /cancel to cancel"
    )


async def handle_view_folder(event, folder_name):
    """Handle view folder details"""
    await event.answer()
    
    user_id = event.sender_id
    folders = load_json(FOLDERS_FILE, {}).get(str(user_id), {})
    
    if folder_name not in folders:
        await event.answer("Folder not found!", alert=True)
        return
    
    groups = folders[folder_name]
    
    text = f"📁 **FOLDER: {folder_name}**\n\n"
    text += f"📢 **Groups ({len(groups)}):**\n\n"
    
    for idx, group in enumerate(groups, 1):
        text += f"{idx}. {group['title']}\n"
        text += f"   🆔 `{group['id']}`\n\n"
    
    keyboard = [
        [Button.inline("➕ Add Groups", f"add_grp_folder:{folder_name}".encode())],
        [Button.inline("🗑️ Delete Folder", f"del_folder:{folder_name}".encode())],
        [Button.inline("❌ Delete Group", f"del_group:{folder_name}".encode())],
        [Button.inline("🔙 Back to Folders", b"folders")]
    ]
    
    await event.edit(text, buttons=keyboard)


async def handle_add_groups_to_folder(event, folder_name):
    """Handle adding groups to existing folder"""
    await event.answer()
    
    user_id = event.sender_id
    
    temp_data[user_id] = {
        'step': 'add_groups_to_folder',
        'folder_name': folder_name
    }
    
    await event.edit(
        f"➕ **ADD GROUPS TO: {folder_name}**\n\n"
        "📝 Send group links or IDs (comma-separated for multiple):\n\n"
        "💡 **Examples:**\n"
        "• Single: `https://t.me/mygroup`\n"
        "• Multiple: `https://t.me/group1, https://t.me/group2`\n"
        "• ID: `3663748162` or `-1001234567890`\n\n"
        "⚠️ Type /cancel to cancel"
    )


async def handle_delete_folder(event, folder_name):
    """Handle delete folder confirmation"""
    await event.answer()
    
    keyboard = [
        [Button.inline("✅ Yes, Delete", f"confirm_del_folder:{folder_name}".encode())],
        [Button.inline("❌ Cancel", f"view_folder:{folder_name}".encode())]
    ]
    
    await event.edit(
        f"⚠️ **DELETE FOLDER**\n\n"
        f"📂 Folder: `{folder_name}`\n\n"
        f"⚠️ **Warning:** This will delete the folder and all group references inside it.\n\n"
        f"Are you sure?",
        buttons=keyboard
    )


async def handle_confirm_delete_folder(event, folder_name):
    """Confirm and delete folder"""
    await event.answer()
    
    user_id = event.sender_id
    folders = load_json(FOLDERS_FILE, {})
    
    if str(user_id) in folders and folder_name in folders[str(user_id)]:
        del folders[str(user_id)][folder_name]
        save_json(FOLDERS_FILE, folders)
        
        await event.edit(
            f"✅ **FOLDER DELETED**\n\n"
            f"📂 `{folder_name}` has been removed.\n\n"
            "Type /start to return to main menu."
        )
    else:
        await event.answer("Folder not found!", alert=True)


async def handle_delete_group_menu(event, folder_name):
    """Show group deletion menu"""
    await event.answer()
    
    user_id = event.sender_id
    folders = load_json(FOLDERS_FILE, {}).get(str(user_id), {})
    
    if folder_name not in folders:
        await event.answer("Folder not found!", alert=True)
        return
    
    groups = folders[folder_name]
    
    text = f"🗑️ **DELETE GROUP FROM: {folder_name}**\n\n"
    text += "Select a group to delete:\n\n"
    
    keyboard = []
    for idx, group in enumerate(groups):
        text += f"{idx + 1}. {group['title']}\n"
        keyboard.append([Button.inline(f"❌ {group['title'][:20]}", f"del_grp_confirm:{folder_name}:{idx}".encode())])
    
    keyboard.append([Button.inline("🔙 Back", f"view_folder:{folder_name}".encode())])
    
    await event.edit(text, buttons=keyboard)


async def handle_confirm_delete_group(event, folder_name, group_idx):
    """Confirm and delete specific group"""
    await event.answer()
    
    user_id = event.sender_id
    folders = load_json(FOLDERS_FILE, {})
    
    try:
        group_idx = int(group_idx)
        if str(user_id) in folders and folder_name in folders[str(user_id)]:
            groups = folders[str(user_id)][folder_name]
            if 0 <= group_idx < len(groups):
                deleted_group = groups.pop(group_idx)
                save_json(FOLDERS_FILE, folders)
                
                await event.answer(f"✅ Deleted: {deleted_group['title']}", alert=True)
                await handle_view_folder(event, folder_name)
            else:
                await event.answer("Invalid group!", alert=True)
    except Exception as e:
        await event.answer(f"Error: {str(e)}", alert=True)
        
        
# ============================================
# SCHEDULER HANDLERS
# ============================================

async def handle_scheduler(event):
    """Handle scheduler menu"""
    await event.answer()
    
    user_id = event.sender_id
    schedules = load_json(SCHEDULES_FILE, {}).get(str(user_id), {})
    
    if not schedules:
        text = (
            "⏰ **SCHEDULER**\n\n"
            "❌ No schedules found.\n\n"
            "💡 Create your first scheduled task!"
        )
        keyboard = [
            [Button.inline("➕ Add Task", b"add_schedule")],
            [Button.inline("🔙 Back", b"back_main")]
        ]
    else:
        text = "⏰ **YOUR SCHEDULES**\n\n"
        keyboard = []
        for schedule_name, schedule_data in schedules.items():
            times_count = len(schedule_data.get('times', []))
            next_run = schedule_data.get('next_run', 'Pending')
            text += f"📋 {schedule_name} ({times_count} times)\n"
            text += f"   ⏰ Next: {next_run}\n\n"
            keyboard.append([Button.inline(f"📋 {schedule_name}", f"view_schedule:{schedule_name}".encode())])
        keyboard.append([Button.inline("➕ Add Task", b"add_schedule")])
        keyboard.append([Button.inline("🔙 Back", b"back_main")])
    
    await event.edit(text, buttons=keyboard)


async def handle_add_schedule(event):
    """Handle add schedule button"""
    await event.answer()
    
    user_id = event.sender_id
    temp_data[user_id] = {'step': 'task_name'}
    
    await event.edit(
        "⏰ **CREATE NEW SCHEDULE**\n\n"
        "📝 Send a name for your task:\n\n"
        "💡 Example: `Morning Post`\n"
        "⚡ Or type `/skip` to auto-generate name\n\n"
        "⚠️ Type /cancel to cancel"
    )


async def handle_view_schedule(event, schedule_name):
    """Handle view schedule details"""
    await event.answer()
    
    user_id = event.sender_id
    schedules = load_json(SCHEDULES_FILE, {}).get(str(user_id), {})
    
    if schedule_name not in schedules:
        await event.answer("Schedule not found!", alert=True)
        return
    
    schedule = schedules[schedule_name]
    
    post = schedule.get('post', 'N/A')
    target = schedule.get('target', 'all')
    folders = schedule.get('folders', 'N/A')
    groups = schedule.get('groups', 'N/A')
    times = schedule.get('times', [])
    last_run = schedule.get('last_run', 'Never')
    next_run = schedule.get('next_run', 'Calculating...')
    
    text = f"📋 **SCHEDULE: {schedule_name}**\n\n"
    text += f"🔗 **Post:** {post[:40]}...\n"
    text += f"🎯 **Target:** {target}\n"
    
    if target == 'folder':
        text += f"📂 **Folders:** {folders}\n"
    elif target == 'groups':
        text += f"📢 **Groups:** {groups}\n"
    
    text += f"\n⏰ **Times ({len(times)}):**\n"
    for t in times:
        text += f"• {t}\n"
    
    text += f"\n📊 **Status:**\n"
    text += f"• Last run: {last_run[:16] if last_run != 'Never' else 'Never'}\n"
    text += f"• Next run: {next_run}\n"
    
    keyboard = [
        [Button.inline("✏️ Edit Schedule", f"edit_schedule:{schedule_name}".encode())],
        [Button.inline("🗑️ Delete Schedule", f"del_schedule:{schedule_name}".encode())],
        [Button.inline("🔙 Back to Scheduler", b"scheduler")]
    ]
    
    await event.edit(text, buttons=keyboard)


async def handle_edit_schedule(event, schedule_name):
    """Handle edit schedule menu"""
    await event.answer()
    
    keyboard = [
        [Button.inline("📝 Edit Name", f"edit_sch_name:{schedule_name}".encode())],
        [Button.inline("🔗 Edit Post", f"edit_sch_post:{schedule_name}".encode())],
        [Button.inline("🎯 Edit Target", f"edit_sch_target:{schedule_name}".encode())],
        [Button.inline("⏰ Edit Times", f"edit_sch_time:{schedule_name}".encode())],
        [Button.inline("🔙 Back", f"view_schedule:{schedule_name}".encode())]
    ]
    
    await event.edit(
        f"✏️ **EDIT SCHEDULE: {schedule_name}**\n\n"
        "What would you like to edit?",
        buttons=keyboard
    )


async def handle_edit_schedule_name(event, schedule_name):
    """Edit schedule name"""
    await event.answer()
    
    user_id = event.sender_id
    temp_data[user_id] = {
        'step': 'edit_schedule_name',
        'old_schedule_name': schedule_name
    }
    
    await event.edit(
        f"📝 **EDIT NAME**\n\n"
        f"Current: `{schedule_name}`\n\n"
        f"Send new name:"
    )


async def handle_edit_schedule_post(event, schedule_name):
    """Edit schedule post link"""
    await event.answer()
    
    user_id = event.sender_id
    temp_data[user_id] = {
        'step': 'edit_schedule_post',
        'schedule_name': schedule_name
    }
    
    await event.edit(
        f"🔗 **EDIT POST LINK**\n\n"
        f"Send new post link:\n\n"
        f"💡 Example: `https://t.me/channel/123`"
    )


async def handle_edit_schedule_target(event, schedule_name):
    """Edit schedule target"""
    await event.answer()
    
    keyboard = [
        [Button.inline("📂 Specific Folder", f"edit_sch_tgt:folder:{schedule_name}".encode())],
        [Button.inline("📢 Specific Groups", f"edit_sch_tgt:groups:{schedule_name}".encode())],
        [Button.inline("🌍 All Groups", f"edit_sch_tgt:all:{schedule_name}".encode())],
        [Button.inline("🔙 Cancel", f"view_schedule:{schedule_name}".encode())]
    ]
    
    await event.edit(
        f"🎯 **EDIT TARGET**\n\n"
        f"Choose new target:",
        buttons=keyboard
    )


async def handle_edit_schedule_target_select(event, schedule_name, target_type):
    """Handle target selection for schedule edit"""
    await event.answer()
    
    user_id = event.sender_id
    
    schedules = load_json(SCHEDULES_FILE, {})
    if str(user_id) in schedules and schedule_name in schedules[str(user_id)]:
        schedules[str(user_id)][schedule_name]['target'] = target_type
        save_json(SCHEDULES_FILE, schedules)
        
        await event.answer(f"✅ Target updated to: {target_type}", alert=True)
        await handle_view_schedule(event, schedule_name)


async def handle_edit_schedule_time(event, schedule_name):
    """Edit schedule times"""
    await event.answer()
    
    user_id = event.sender_id
    temp_data[user_id] = {
        'step': 'edit_schedule_time',
        'schedule_name': schedule_name
    }
    
    await event.edit(
        f"⏰ **EDIT TIMES**\n\n"
        f"Send new time(s):\n\n"
        f"💡 **Formats:**\n"
        f"• 12-hour: `11:00 PM, 2:30 PM`\n"
        f"• 24-hour: `23:00, 14:30`\n"
        f"• With date: `2024-12-25 10:00`"
    )


async def handle_delete_schedule(event, schedule_name):
    """Handle delete schedule confirmation"""
    await event.answer()
    
    keyboard = [
        [Button.inline("✅ Yes, Delete", f"confirm_del_schedule:{schedule_name}".encode())],
        [Button.inline("❌ Cancel", f"view_schedule:{schedule_name}".encode())]
    ]
    
    await event.edit(
        f"⚠️ **DELETE SCHEDULE**\n\n"
        f"📋 Task: `{schedule_name}`\n\n"
        f"⚠️ **Warning:** This will permanently delete this scheduled task.\n\n"
        f"Are you sure?",
        buttons=keyboard
    )


async def handle_confirm_delete_schedule(event, schedule_name):
    """Confirm and delete schedule"""
    await event.answer()
    
    user_id = event.sender_id
    schedules = load_json(SCHEDULES_FILE, {})
    
    if str(user_id) in schedules and schedule_name in schedules[str(user_id)]:
        del schedules[str(user_id)][schedule_name]
        save_json(SCHEDULES_FILE, schedules)
        
        await event.edit(
            f"✅ **SCHEDULE DELETED**\n\n"
            f"📋 `{schedule_name}` has been removed.\n\n"
            "Type /start to return to main menu."
        )
    else:
        await event.answer("Schedule not found!", alert=True)


# ============================================
# BROADCAST HANDLERS
# ============================================

async def handle_broadcast(event):
    """Handle broadcast menu"""
    await event.answer()
    
    user_id = event.sender_id
    folders = load_json(FOLDERS_FILE, {}).get(str(user_id), {})
    
    if not folders:
        keyboard = [
            [Button.inline("➕ Create Folder First", b"add_folder")],
            [Button.inline("🔙 Back", b"back_main")]
        ]
        
        await event.edit(
            "⚠️ **NO FOLDERS FOUND**\n\n"
            "─────────────────────\n\n"
            "📂 Before broadcasting, you need to create at least one folder with groups.\n\n"
            "💡 **What to do:**\n"
            "1. Click 'Create Folder First' below\n"
            "2. Give your folder a name\n"
            "3. Add groups to the folder\n"
            "4. Then return to broadcast\n\n"
            "─────────────────────\n"
            "⚠️ **Action Required:** Create a folder first!",
            buttons=keyboard
        )
        return
    
    text = (
        "📢 **BROADCAST**\n\n"
        "📝 Choose content type to broadcast:\n\n"
        "💬 **Message** - Send text message\n"
        "🔗 **Post Link** - Forward from channel/group"
    )
    keyboard = [
        [Button.inline("💬 Message", b"broadcast_msg"), Button.inline("🔗 Post Link", b"broadcast_link")],
        [Button.inline("🔙 Back", b"back_main")]
    ]
    await event.edit(text, buttons=keyboard)


async def handle_broadcast_message(event):
    """Handle broadcast message type"""
    await event.answer()
    
    user_id = event.sender_id
    temp_data[user_id] = {
        'step': 'broadcast_content',
        'broadcast_type': 'message'
    }
    
    await event.edit(
        "💬 **BROADCAST MESSAGE**\n\n"
        "📝 Send the message you want to broadcast:\n\n"
        "💡 Type your message below\n\n"
        "⚠️ Type /cancel to cancel"
    )


async def handle_broadcast_link(event):
    """Handle broadcast post link type"""
    await event.answer()
    
    user_id = event.sender_id
    temp_data[user_id] = {
        'step': 'broadcast_content',
        'broadcast_type': 'link'
    }
    
    await event.edit(
        "🔗 **BROADCAST POST LINK**\n\n"
        "📝 Send the post link you want to forward:\n\n"
        "💡 Example: `https://t.me/channel/123`\n\n"
        "⚠️ Type /cancel to cancel"
    )


async def handle_broadcast_target_all(event):
    """Handle broadcast to all groups"""
    await event.answer()
    
    user_id = event.sender_id
    
    content = temp_data[user_id].get('broadcast_content', '')
    broadcast_type = temp_data[user_id].get('broadcast_type', 'message')
    
    target_groups = await get_all_groups_from_folders(user_id, FOLDERS_FILE)
    
    if not target_groups:
        await event.edit(
            "❌ **NO GROUPS FOUND**\n\n"
            "You don't have any groups in folders.\n"
            "Create folders and add groups first!"
        )
        del temp_data[user_id]
        return
    
    if user_id not in user_sessions:
        await event.edit(
            "❌ **NOT LOGGED IN**\n\n"
            "Please login first using /setup"
        )
        del temp_data[user_id]
        return
    
    success_count = 0
    failed_count = 0
    
    status_msg = await event.edit(
        f"🚀 **BROADCASTING...**\n\n"
        f"🌍 Target: All Groups\n"
        f"📢 Total: {len(target_groups)}\n\n"
        f"⏳ Starting..."
    )
    
    client = user_sessions[user_id]
    
    user_settings = get_user_settings(user_id, SETTINGS_FILE)
    delay = user_settings.get('delay', 0)
    mode = user_settings.get('forward_mode', 'Copy')
    
    for idx, group_id in enumerate(target_groups):
        try:
            if broadcast_type == 'link':
                success = await forward_post_from_link(client, content, group_id, mode)
                if success:
                    success_count += 1
                else:
                    failed_count += 1
            else:
                await client.send_message(group_id, content)
                success_count += 1
            
            if (idx + 1) % 5 == 0 or (idx + 1) == len(target_groups):
                progress = int(((idx + 1) / len(target_groups)) * 100)
                await status_msg.edit(
                    f"🚀 **BROADCASTING...**\n\n"
                    f"📊 Progress: {idx + 1}/{len(target_groups)}\n"
                    f"✅ Success: {success_count}\n"
                    f"❌ Failed: {failed_count}\n\n"
                    f"`{'▰' * (progress // 10)}{'▱' * (10 - progress // 10)}` {progress}%"
                )
            
            if delay > 0:
                import asyncio
                await asyncio.sleep(delay)
                
        except Exception as e:
            failed_count += 1
            print(f"❌ Broadcast failed for {group_id}: {e}")
    
    del temp_data[user_id]
    
    await status_msg.edit(
        f"✅ **BROADCAST COMPLETE**\n\n"
        f"🌍 Target: All Groups\n"
        f"📢 Total: {len(target_groups)}\n\n"
        f"✅ Successful: {success_count}\n"
        f"❌ Failed: {failed_count}\n"
        f"📊 Success Rate: {int((success_count/len(target_groups))*100)}%\n\n"
        f"🕐 Finished at: `{get_current_time()}`"
    )


# ============================================
# CONSOLE HANDLERS
# ============================================

async def handle_console(event):
    """Handle console menu"""
    await event.answer()
    
    user_id = event.sender_id
    user_settings = get_user_settings(user_id, SETTINGS_FILE)
    
    delay = user_settings.get('delay', 0)
    simulation = user_settings.get('simulation', 'None')
    mode = user_settings.get('forward_mode', 'Copy')
    
    text = (
        "⚙️ **CONSOLE SETTINGS**\n\n"
        f"⏱️ **Delay:** {delay}s\n"
        f"🎭 **Simulation:** {simulation}\n"
        f"📤 **Mode:** {mode}\n\n"
        "────────────────────\n"
        "🔧 Adjust your forwarding settings:"
    )
    
    keyboard = [
        [Button.inline("⏱️ Set Delay", b"set_delay")],
        [Button.inline("🎭 Simulation", b"set_simulation")],
        [Button.inline("📤 Forward Mode", b"set_forward_mode")],
        [Button.inline("🔙 Back", b"back_main")]
    ]
    
    await event.edit(text, buttons=keyboard)


async def handle_set_delay_menu(event):
    """Show delay options"""
    await event.answer()
    
    text = (
        "⏱️ **SET DELAY**\n\n"
        "⏳ Choose forwarding delay time:\n\n"
        "💡 Delay helps avoid spam detection"
    )
    
    keyboard = []
    row = []
    for i, delay in enumerate(DELAY_OPTIONS):
        label = "0s (Instant)" if delay == 0 else f"{delay}s"
        row.append(Button.inline(label, f"delay:{delay}".encode()))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    
    keyboard.append([Button.inline("🔙 Back to Console", b"console")])
    await event.edit(text, buttons=keyboard)


async def handle_delay_select(event, delay):
    """Handle delay selection"""
    await event.answer()
    
    user_id = event.sender_id
    update_user_setting(user_id, SETTINGS_FILE, 'delay', int(delay))
    
    user_settings = get_user_settings(user_id, SETTINGS_FILE)
    simulation = user_settings.get('simulation', 'None')
    mode = user_settings.get('forward_mode', 'Copy')
    
    text = (
        "⚙️ **CONSOLE SETTINGS**\n\n"
        f"⏱️ **Delay:** {delay}s\n"
        f"🎭 **Simulation:** {simulation}\n"
        f"📤 **Mode:** {mode}\n\n"
        "────────────────────\n"
        "🔧 Adjust your forwarding settings:"
    )
    
    keyboard = [
        [Button.inline("⏱️ Set Delay", b"set_delay")],
        [Button.inline("🎭 Simulation", b"set_simulation")],
        [Button.inline("📤 Forward Mode", b"set_forward_mode")],
        [Button.inline("🔙 Back", b"back_main")]
    ]
    
    await event.edit(text, buttons=keyboard)


async def handle_set_simulation_menu(event):
    """Show simulation options"""
    await event.answer()
    
    text = (
        "🎭 **SIMULATION SETTINGS**\n\n"
        "⌨️ Choose typing simulation:\n\n"
        "💡 Makes forwarding look more natural"
    )
    
    keyboard = []
    for sim_type in SIMULATION_TYPES:
        emoji = "❌" if sim_type == "None" else ("⌨️" if sim_type == "Typing" else "🎬")
        keyboard.append([Button.inline(f"{emoji} {sim_type}", f"sim:{sim_type}".encode())])
    
    keyboard.append([Button.inline("🔙 Back to Console", b"console")])
    await event.edit(text, buttons=keyboard)


async def handle_simulation_select(event, simulation):
    """Handle simulation selection"""
    await event.answer()
    
    user_id = event.sender_id
    update_user_setting(user_id, SETTINGS_FILE, 'simulation', simulation)
    
    user_settings = get_user_settings(user_id, SETTINGS_FILE)
    delay = user_settings.get('delay', 0)
    mode = user_settings.get('forward_mode', 'Copy')
    
    text = (
        "⚙️ **CONSOLE SETTINGS**\n\n"
        f"⏱️ **Delay:** {delay}s\n"
        f"🎭 **Simulation:** {simulation}\n"
        f"📤 **Mode:** {mode}\n\n"
        "────────────────────\n"
        "🔧 Adjust your forwarding settings:"
    )
    
    keyboard = [
        [Button.inline("⏱️ Set Delay", b"set_delay")],
        [Button.inline("🎭 Simulation", b"set_simulation")],
        [Button.inline("📤 Forward Mode", b"set_forward_mode")],
        [Button.inline("🔙 Back", b"back_main")]
    ]
    
    await event.edit(text, buttons=keyboard)


async def handle_set_forward_mode_menu(event):
    """Show forward mode options"""
    await event.answer()
    
    text = (
        "📤 **FORWARD MODE**\n\n"
        "📋 **Copy** - Forward without sender tag (hide source)\n"
        "↗️ **Forward** - Forward with sender tag (show source)\n\n"
        "💡 Choose your preferred mode:"
    )
    
    keyboard = [
        [Button.inline("📋 Copy Mode", b"mode:Copy")],
        [Button.inline("↗️ Forward Mode", b"mode:Forward")],
        [Button.inline("🔙 Back to Console", b"console")]
    ]
    
    await event.edit(text, buttons=keyboard)


async def handle_forward_mode_select(event, mode):
    """Handle forward mode selection"""
    await event.answer()
    
    user_id = event.sender_id
    update_user_setting(user_id, SETTINGS_FILE, 'forward_mode', mode)
    
    user_settings = get_user_settings(user_id, SETTINGS_FILE)
    delay = user_settings.get('delay', 0)
    simulation = user_settings.get('simulation', 'None')
    
    text = (
        "⚙️ **CONSOLE SETTINGS**\n\n"
        f"⏱️ **Delay:** {delay}s\n"
        f"🎭 **Simulation:** {simulation}\n"
        f"📤 **Mode:** {mode}\n\n"
        "────────────────────\n"
        "🔧 Adjust your forwarding settings:"
    )
    
    keyboard = [
        [Button.inline("⏱️ Set Delay", b"set_delay")],
        [Button.inline("🎭 Simulation", b"set_simulation")],
        [Button.inline("📤 Forward Mode", b"set_forward_mode")],
        [Button.inline("🔙 Back", b"back_main")]
    ]
    
    await event.edit(text, buttons=keyboard)


# ============================================
# TIMEZONE HANDLERS
# ============================================

async def handle_timezone(event):
    """Handle timezone menu"""
    await event.answer()
    
    user_id = event.sender_id
    user_settings = get_user_settings(user_id, SETTINGS_FILE)
    current_tz = user_settings.get('timezone', 'UTC')
    
    text = (
        "🌍 **TIMEZONE SETTINGS**\n\n"
        f"⏰ Current Timezone: **{current_tz}**\n\n"
        "🌍 Select your timezone:"
    )
    
    keyboard = []
    for tz_key, tz_label in TIMEZONES.items():
        keyboard.append([Button.inline(tz_label, f"tz:{tz_key}".encode())])
    keyboard.append([Button.inline("🔙 Back", b"back_main")])
    
    await event.edit(text, buttons=keyboard)


async def handle_timezone_select(event, timezone):
    """Handle timezone selection"""
    await event.answer()
    
    user_id = event.sender_id
    update_user_setting(user_id, SETTINGS_FILE, 'timezone', timezone)
    
    text = (
        "🌍 **TIMEZONE SETTINGS**\n\n"
        f"⏰ Current Timezone: **{timezone}**\n\n"
        "✅ Timezone updated successfully!\n\n"
        "🌍 Select your timezone:"
    )
    
    keyboard = []
    for tz_key, tz_label in TIMEZONES.items():
        keyboard.append([Button.inline(tz_label, f"tz:{tz_key}".encode())])
    keyboard.append([Button.inline("🔙 Back", b"back_main")])
    
    await event.edit(text, buttons=keyboard)


# ============================================
# PLAN, SUPPORT, HELP, LOGOUT HANDLERS
# ============================================

async def handle_plan(event):
    """Handle plan menu"""
    await event.answer()
    
    user_id = event.sender_id
    plan_days = get_user_plan(user_id)
    user_info = get_user_info(user_id)
    
    plan_type = user_info.get('plan_type', 'Free')
    started = user_info.get('started', 'N/A')
    
    text = (
        "💎 **YOUR PLAN**\n\n"
        f"📊 **Plan Type:** {plan_type}\n"
        f"⏳ **Days Remaining:** {plan_days} days\n"
        f"📅 **Started:** {started}\n\n"
        "────────────────────\n"
        "💡 Contact support to upgrade!"
    )
    
    keyboard = [[Button.inline("🔙 Back", b"back_main")]]
    await event.edit(text, buttons=keyboard)


async def handle_support(event):
    """Handle support menu"""
    await event.answer()
    
    text = (
        "💬 **SUPPORT**\n\n"
        "🆘 Need assistance? Our team is here to help!\n\n"
        "👥 **Contact Owners:**\n"
        "────────────────────"
    )
    
    keyboard = [
        [Button.url("👤 Owner 1", OWNERS[2024653852])],
        [Button.url("👤 Owner 2", OWNERS[5510835149])],
        [Button.inline("🔙 Back", b"back_main")]
    ]
    
    await event.edit(text, buttons=keyboard)


async def handle_help(event):
    """Handle help menu"""
    await event.answer()
    
    help_text = (
        "❓ **HELP & FEATURES**\n\n"
        "─────────────────────\n\n"
        
        "📂 **FOLDERS**\n"
        "Organize your groups into folders for easy management.\n"
        "• Create unlimited folders\n"
        "• Add multiple groups per folder\n"
        "• Support for private & public groups\n"
        "• Delete folders & groups anytime\n"
        "• View all groups in a folder\n\n"
        
        "⏰ **SCHEDULER**\n"
        "Automate your posts to be sent at specific times.\n"
        "• Create multiple scheduled tasks\n"
        "• Set multiple time slots per task\n"
        "• Choose target: All groups, Specific folders, or Specific groups\n"
        "• Supports 12-hour (11:00 PM) and 24-hour (23:00) formats\n"
        "• Schedule for specific dates (2024-12-25 10:00)\n"
        "• Edit task name, post, target, and times\n"
        "• Auto-executes at set times based on your timezone\n\n"
        
        "📢 **BROADCAST**\n"
        "Send instant messages to your groups.\n"
        "• Broadcast text messages\n"
        "• Forward posts from channels\n"
        "• Send to all groups, specific folders, or specific groups\n"
        "• Multi-select folders and groups\n"
        "• Real-time progress tracking\n"
        "• No scheduling needed - instant delivery\n\n"
        
        "⚙️ **CONSOLE**\n"
        "Configure forwarding behavior and settings.\n"
        "• **Delay**: Set time between forwards (0-10 seconds)\n"
        "  - Helps avoid Telegram spam detection\n"
        "• **Simulation**: Make forwarding look natural\n"
        "  - None, Typing, or Recording simulation\n"
        "• **Forward Mode**:\n"
        "  - Copy: Hide source (no attribution)\n"
        "  - Forward: Show source (with attribution)\n\n"
        
        "🌍 **TIMEZONE**\n"
        "Set your timezone for accurate scheduling.\n"
        "• Required before creating schedules\n"
        "• Supports major timezones worldwide\n"
        "• Asia/Dhaka, America/New_York, Europe/London, etc.\n"
        "• All scheduled times use your timezone\n\n"
        
        "💎 **PLAN**\n"
        "View your subscription details.\n"
        "• See remaining days\n"
        "• Check plan type (Free/Premium)\n"
        "• View activation date\n\n"
        
        "─────────────────────\n"
        "💬 **Need more help?**\n"
        "Contact support for assistance!"
    )
    
    keyboard = [[Button.inline("🔙 Back to Menu", b"back_main")]]
    await event.edit(help_text, buttons=keyboard)


async def handle_confirm_logout(event):
    """Handle logout confirmation"""
    await event.answer()
    
    user_id = event.sender_id
    
    sessions = load_json(SESSIONS_FILE, {})
    if str(user_id) in sessions:
        del sessions[str(user_id)]
        save_json(SESSIONS_FILE, sessions)
    
    if user_id in user_sessions:
        try:
            await user_sessions[user_id].log_out()
        except:
            pass
        del user_sessions[user_id]
    
    await event.edit(
        "✅ **LOGGED OUT**\n\n"
        "Your session has been terminated successfully!\n\n"
        "🔒 Use /setup to login again."
    )


async def handle_cancel_logout(event):
    """Handle cancel logout"""
    await event.answer()
    
    await event.edit(
        "❌ **LOGOUT CANCELLED**\n\n"
        "Your session remains active.\n\n"
        "Type /start to return to main menu."
    )


# ============================================
# MAIN CALLBACK ROUTER - COMPLETE
# ============================================

async def callback_handler(event, bot):
    """Main callback query router - handles ALL button clicks"""
    user_id = event.sender_id
    data = event.data.decode('utf-8')
    
    if not is_authorized(user_id):
        await event.answer("Access Denied!", alert=True)
        return
    
    # Main Router
    if data == "back_main":
        await handle_back_main(event, bot)
    elif data == "folders":
        await handle_folders(event)
    elif data == "add_folder":
        await handle_add_folder(event)
    elif data.startswith("view_folder:"):
        folder_name = data.split(":", 1)[1]
        await handle_view_folder(event, folder_name)
    elif data.startswith("add_grp_folder:"):
        folder_name = data.split(":", 1)[1]
        await handle_add_groups_to_folder(event, folder_name)
    elif data.startswith("del_folder:"):
        folder_name = data.split(":", 1)[1]
        await handle_delete_folder(event, folder_name)
    elif data.startswith("confirm_del_folder:"):
        folder_name = data.split(":", 1)[1]
        await handle_confirm_delete_folder(event, folder_name)
    elif data.startswith("del_group:"):
        folder_name = data.split(":", 1)[1]
        await handle_delete_group_menu(event, folder_name)
    elif data.startswith("del_grp_confirm:"):
        parts = data.split(":", 2)
        folder_name = parts[1]
        group_idx = parts[2]
        await handle_confirm_delete_group(event, folder_name, group_idx)
    elif data == "scheduler":
        await handle_scheduler(event)
    elif data == "add_schedule":
        await handle_add_schedule(event)
    elif data.startswith("view_schedule:"):
        schedule_name = data.split(":", 1)[1]
        await handle_view_schedule(event, schedule_name)
    elif data.startswith("edit_schedule:"):
        schedule_name = data.split(":", 1)[1]
        await handle_edit_schedule(event, schedule_name)
    elif data.startswith("edit_sch_name:"):
        schedule_name = data.split(":", 1)[1]
        await handle_edit_schedule_name(event, schedule_name)
    elif data.startswith("edit_sch_post:"):
        schedule_name = data.split(":", 1)[1]
        await handle_edit_schedule_post(event, schedule_name)
    elif data.startswith("edit_sch_target:"):
        schedule_name = data.split(":", 1)[1]
        await handle_edit_schedule_target(event, schedule_name)
    elif data.startswith("edit_sch_time:"):
        schedule_name = data.split(":", 1)[1]
        await handle_edit_schedule_time(event, schedule_name)
    elif data.startswith("edit_sch_tgt:"):
        parts = data.split(":", 2)
        target_type = parts[1]
        schedule_name = parts[2]
        await handle_edit_schedule_target_select(event, schedule_name, target_type)
    elif data.startswith("del_schedule:"):
        schedule_name = data.split(":", 1)[1]
        await handle_delete_schedule(event, schedule_name)
    elif data.startswith("confirm_del_schedule:"):
        schedule_name = data.split(":", 1)[1]
        await handle_confirm_delete_schedule(event, schedule_name)
    elif data.startswith("task_target:"):
        await event.answer()
        target = data.split(":")[1]
        temp_data[user_id]['task_target'] = target
        
        if target == "all":
            temp_data[user_id]['step'] = 'task_time'
            await event.edit(
                "✅ **TARGET: All Groups**\n\n"
                "⏰ Now send the **TIME(S)** to post:\n\n"
                "💡 **Formats Supported:**\n"
                "• 12-hour: `11:00 PM, 2:30 PM`\n"
                "• 24-hour: `14:30, 20:00`\n"
                "• With date: `2024-12-25 10:00`"
            )
        elif target == "folder":
            folders = load_json(FOLDERS_FILE, {}).get(str(user_id), {})
            if not folders:
                await event.answer("No folders found! Create folders first.", alert=True)
                return
            
            text = "📂 **SELECT FOLDER(S)**\n\n"
            text += "Available folders:\n"
            for folder_name in folders.keys():
                text += f"• {folder_name}\n"
            
            text += "\n📝 Send folder name(s) (comma-separated for multiple):"
            temp_data[user_id]['step'] = 'task_folder_choice'
            await event.edit(text)
        elif target == "groups":
            temp_data[user_id]['step'] = 'task_specific_groups'
            await event.edit(
                "📢 **SELECT GROUPS**\n\n"
                "📝 Send group link(s) or ID(s):\n\n"
                "💡 Example: `https://t.me/group1, https://t.me/group2`"
            )
    elif data == "broadcast":
        await handle_broadcast(event)
    elif data == "broadcast_msg":
        await handle_broadcast_message(event)
    elif data == "broadcast_link":
        await handle_broadcast_link(event)
    elif data.startswith("bc_target:"):
        target = data.split(":")[1]
        temp_data[user_id]['broadcast_target'] = target
        
        if target == "all":
            await handle_broadcast_target_all(event)
    elif data == "timezone":
        await handle_timezone(event)
    elif data.startswith("tz:"):
        timezone = data.split(":", 1)[1]
        await handle_timezone_select(event, timezone)
    elif data == "console":
        await handle_console(event)
    elif data == "set_delay":
        await handle_set_delay_menu(event)
    elif data.startswith("delay:"):
        delay = data.split(":")[1]
        await handle_delay_select(event, delay)
    elif data == "set_simulation":
        await handle_set_simulation_menu(event)
    elif data.startswith("sim:"):
        simulation = data.split(":", 1)[1]
        await handle_simulation_select(event, simulation)
    elif data == "set_forward_mode":
        await handle_set_forward_mode_menu(event)
    elif data.startswith("mode:"):
        mode = data.split(":", 1)[1]
        await handle_forward_mode_select(event, mode)
    elif data == "plan":
        await handle_plan(event)
    elif data == "support":
        await handle_support(event)
    elif data == "help":
        await handle_help(event)
    elif data == "confirm_logout":
        await handle_confirm_logout(event)
    elif data == "cancel_logout":
        await handle_cancel_logout(event)
    else:
        await event.answer("Feature coming soon!", alert=True)


def register_callback_handlers(bot):
    """Register callback query handler"""
    
    bot.add_event_handler(
        lambda event: callback_handler(event, bot),
        events.CallbackQuery
    )
    
    print("✅ Callback handlers registered")


# ============================================
# END OF PART 3 - CALLBACKS.PY COMPLETE!
# ============================================