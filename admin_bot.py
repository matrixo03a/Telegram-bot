"""
ADMIN BOT - Complete Management System
Auto-starts with main bot
Features: Add User, Set Plan, Add Admin, Remove Admin, Delete User, Broadcast
"""

import asyncio
import json
import os
from datetime import datetime, timedelta
from telethon import TelegramClient, events, Button

# ============================================
# ADMIN BOT CONFIG
# ============================================
ADMIN_BOT_TOKEN = "8589067733:AAFopNVcyV58sSC2ZcL0s0FNc1JHyS6BJW8"
ADMIN_API_ID = 36363448
ADMIN_API_HASH = "2920b3f570b33122db81fde2df17f6ce"

# Owner IDs (from main bot)
SUPER_ADMINS = [2024653852, 5510835149]

# File paths
DATA_DIR = "bot_data"
USERS_FILE = f"{DATA_DIR}/users.json"
ADMINS_FILE = f"{DATA_DIR}/admins.json"

# ============================================
# UTILITY FUNCTIONS
# ============================================

def load_json(file_path, default=None):
    """Load JSON file"""
    if default is None:
        default = {}
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except:
        pass
    return default


def save_json(file_path, data):
    """Save JSON file"""
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except:
        return False


def is_super_admin(user_id):
    """Check if user is super admin (owner)"""
    return user_id in SUPER_ADMINS


def is_admin(user_id):
    """Check if user is admin or super admin"""
    if is_super_admin(user_id):
        return True
    admins = load_json(ADMINS_FILE, {})
    return str(user_id) in admins


def get_all_users():
    """Get all users from main bot"""
    return load_json(USERS_FILE, {})


def get_admins():
    """Get all admins"""
    return load_json(ADMINS_FILE, {})


# ============================================
# COMMAND HANDLERS
# ============================================

async def start_handler(event):
    """Admin panel start"""
    user_id = event.sender_id
    
    if not is_admin(user_id):
        await event.respond(
            "🚫 **ACCESS DENIED**\n\n"
            "This bot is for administrators only."
        )
        return
    
    is_super = is_super_admin(user_id)
    
    users = get_all_users()
    admins = get_admins()
    
    text = (
        "╔═══════════════════╗\n"
        "║  👑 **ADMIN PANEL**  ║\n"
        "╚═══════════════════╝\n\n"
        f"👤 **Admin:** `{user_id}`\n"
        f"🎖️ **Role:** {'Super Admin' if is_super else 'Admin'}\n"
        f"📊 **Total Users:** {len(users)}\n"
        f"👥 **Total Admins:** {len(admins)}\n"
        f"🕐 **Time:** `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`\n\n"
        "────────────────────\n"
        "⚡ **ADMIN CONTROL PANEL**"
    )
    
    keyboard = [
        [Button.text("➕ Add User", resize=True), Button.text("📋 View Users", resize=True)],
        [Button.text("💎 Set Plan", resize=True), Button.text("🗑️ Delete User", resize=True)],
    ]
    
    if is_super:
        keyboard.append([Button.text("👨‍💼 Add Admin", resize=True), Button.text("❌ Remove Admin", resize=True)])
    
    keyboard.append([Button.text("📢 Broadcast", resize=True), Button.text("📊 Stats", resize=True)])
    
    await event.respond(text, buttons=keyboard)


async def add_user_handler(event):
    """Add new user"""
    user_id = event.sender_id
    
    if not is_admin(user_id):
        return
    
    await event.respond(
        "➕ **ADD NEW USER**\n\n"
        "📝 Send user ID to add:\n\n"
        "💡 Example: `123456789`\n\n"
        "⚠️ Type /cancel to cancel"
    )
    
    # Wait for user input
    global temp_admin_data
    temp_admin_data[user_id] = {'action': 'add_user'}


async def view_users_handler(event):
    """View all users"""
    user_id = event.sender_id
    
    if not is_admin(user_id):
        return
    
    users = get_all_users()
    
    if not users:
        await event.respond("📋 **NO USERS**\n\nNo users registered yet.")
        return
    
    text = "📋 **ALL USERS**\n\n"
    text += f"Total: {len(users)} users\n\n"
    
    for idx, (uid, udata) in enumerate(users.items(), 1):
        plan_days = udata.get('plan_days', 0)
        plan_type = udata.get('plan_type', 'Free')
        text += f"{idx}. `{uid}` - {plan_type} ({plan_days}d)\n"
    
    await event.respond(text)


async def set_plan_handler(event):
    """Set user plan"""
    user_id = event.sender_id
    
    if not is_admin(user_id):
        return
    
    await event.respond(
        "💎 **SET USER PLAN**\n\n"
        "📝 Send in this format:\n"
        "`USER_ID PLAN_TYPE DAYS`\n\n"
        "💡 **Example:**\n"
        "`123456789 Premium 30`\n"
        "`987654321 VIP 90`\n\n"
        "⚠️ Type /cancel to cancel"
    )
    
    global temp_admin_data
    temp_admin_data[user_id] = {'action': 'set_plan'}


async def delete_user_handler(event):
    """Delete user"""
    user_id = event.sender_id
    
    if not is_admin(user_id):
        return
    
    await event.respond(
        "🗑️ **DELETE USER**\n\n"
        "📝 Send user ID to delete:\n\n"
        "💡 Example: `123456789`\n\n"
        "⚠️ This will permanently remove the user!\n"
        "⚠️ Type /cancel to cancel"
    )
    
    global temp_admin_data
    temp_admin_data[user_id] = {'action': 'delete_user'}


async def add_admin_handler(event):
    """Add new admin (super admin only)"""
    user_id = event.sender_id
    
    if not is_super_admin(user_id):
        await event.respond("🚫 **ACCESS DENIED**\n\nOnly super admins can add new admins.")
        return
    
    await event.respond(
        "👨‍💼 **ADD NEW ADMIN**\n\n"
        "📝 Send admin ID to add:\n\n"
        "💡 Example: `123456789`\n\n"
        "⚠️ Type /cancel to cancel"
    )
    
    global temp_admin_data
    temp_admin_data[user_id] = {'action': 'add_admin'}


async def remove_admin_handler(event):
    """Remove admin (super admin only)"""
    user_id = event.sender_id
    
    if not is_super_admin(user_id):
        await event.respond("🚫 **ACCESS DENIED**\n\nOnly super admins can remove admins.")
        return
    
    admins = get_admins()
    
    if not admins:
        await event.respond("👨‍💼 **NO ADMINS**\n\nNo admins to remove.")
        return
    
    text = "👨‍💼 **CURRENT ADMINS**\n\n"
    for aid, adata in admins.items():
        added_date = adata.get('added', 'Unknown')
        text += f"• `{aid}` - Added: {added_date}\n"
    
    text += "\n📝 Send admin ID to remove:\n"
    text += "⚠️ Type /cancel to cancel"
    
    await event.respond(text)
    
    global temp_admin_data
    temp_admin_data[user_id] = {'action': 'remove_admin'}


async def broadcast_handler(event):
    """Broadcast message to all users"""
    user_id = event.sender_id
    
    if not is_admin(user_id):
        return
    
    await event.respond(
        "📢 **BROADCAST MESSAGE**\n\n"
        "📝 Send the message you want to broadcast to all users:\n\n"
        "💡 Type your message below\n"
        "⚠️ Type /cancel to cancel"
    )
    
    global temp_admin_data
    temp_admin_data[user_id] = {'action': 'broadcast'}


async def stats_handler(event):
    """Show bot statistics"""
    user_id = event.sender_id
    
    if not is_admin(user_id):
        return
    
    users = get_all_users()
    admins = get_admins()
    
    # Count plans
    free_users = sum(1 for u in users.values() if u.get('plan_type') == 'Free')
    premium_users = sum(1 for u in users.values() if u.get('plan_type') in ['Premium', 'VIP'])
    
    # Count active plans
    active_users = sum(1 for u in users.values() if u.get('plan_days', 0) > 0)
    
    text = (
        "📊 **BOT STATISTICS**\n\n"
        f"👥 **Total Users:** {len(users)}\n"
        f"👨‍💼 **Total Admins:** {len(admins)}\n\n"
        f"💎 **Plan Distribution:**\n"
        f"• Free: {free_users}\n"
        f"• Premium/VIP: {premium_users}\n"
        f"• Active Plans: {active_users}\n\n"
        f"🕐 **Generated:** `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`"
    )
    
    await event.respond(text)


# ============================================
# MESSAGE HANDLER (for text inputs)
# ============================================

temp_admin_data = {}

async def message_handler(event):
    """Handle admin text inputs"""
    user_id = event.sender_id
    
    if user_id not in temp_admin_data:
        return
    
    action = temp_admin_data[user_id].get('action')
    text = event.raw_text.strip()
    
    if text == '/cancel':
        del temp_admin_data[user_id]
        await event.respond("❌ **CANCELLED**")
        return
    
    if action == 'add_user':
        try:
            new_user_id = int(text)
            users = load_json(USERS_FILE, {})
            
            if str(new_user_id) in users:
                await event.respond(f"⚠️ User `{new_user_id}` already exists!")
            else:
                users[str(new_user_id)] = {
                    'plan_days': 3,
                    'plan_type': 'Free Trial',
                    'started': datetime.now().isoformat()
                }
                save_json(USERS_FILE, users)
                await event.respond(
                    f"✅ **USER ADDED**\n\n"
                    f"👤 User ID: `{new_user_id}`\n"
                    f"💎 Plan: Free Trial (3 days)"
                )
            del temp_admin_data[user_id]
        except:
            await event.respond("❌ Invalid user ID format!")
    
    elif action == 'set_plan':
        try:
            parts = text.split()
            if len(parts) != 3:
                await event.respond("❌ Wrong format! Use: `USER_ID PLAN_TYPE DAYS`")
                return
            
            target_user = parts[0]
            plan_type = parts[1]
            plan_days = int(parts[2])
            
            users = load_json(USERS_FILE, {})
            
            if target_user not in users:
                await event.respond(f"❌ User `{target_user}` not found!")
            else:
                users[target_user]['plan_type'] = plan_type
                users[target_user]['plan_days'] = plan_days
                save_json(USERS_FILE, users)
                
                await event.respond(
                    f"✅ **PLAN UPDATED**\n\n"
                    f"👤 User: `{target_user}`\n"
                    f"💎 Plan: {plan_type}\n"
                    f"📅 Days: {plan_days}"
                )
            del temp_admin_data[user_id]
        except:
            await event.respond("❌ Invalid format!")
    
    elif action == 'delete_user':
        try:
            target_user = text
            users = load_json(USERS_FILE, {})
            
            if target_user not in users:
                await event.respond(f"❌ User `{target_user}` not found!")
            else:
                del users[target_user]
                save_json(USERS_FILE, users)
                await event.respond(f"✅ **USER DELETED**\n\nUser `{target_user}` removed.")
            del temp_admin_data[user_id]
        except:
            await event.respond("❌ Error deleting user!")
    
    elif action == 'add_admin':
        try:
            new_admin_id = int(text)
            admins = load_json(ADMINS_FILE, {})
            
            if str(new_admin_id) in admins:
                await event.respond(f"⚠️ `{new_admin_id}` is already an admin!")
            else:
                admins[str(new_admin_id)] = {
                    'added': datetime.now().isoformat(),
                    'added_by': user_id
                }
                save_json(ADMINS_FILE, admins)
                await event.respond(f"✅ **ADMIN ADDED**\n\nAdmin ID: `{new_admin_id}`")
            del temp_admin_data[user_id]
        except:
            await event.respond("❌ Invalid admin ID!")
    
    elif action == 'remove_admin':
        try:
            target_admin = text
            admins = load_json(ADMINS_FILE, {})
            
            if target_admin not in admins:
                await event.respond(f"❌ `{target_admin}` is not an admin!")
            else:
                del admins[target_admin]
                save_json(ADMINS_FILE, admins)
                await event.respond(f"✅ **ADMIN REMOVED**\n\nAdmin `{target_admin}` removed.")
            del temp_admin_data[user_id]
        except:
            await event.respond("❌ Error removing admin!")
    
    elif action == 'broadcast':
        message = text
        users = get_all_users()
        
        success = 0
        failed = 0
        
        status_msg = await event.respond(
            f"📢 **BROADCASTING...**\n\n"
            f"Total users: {len(users)}\n"
            f"⏳ Starting..."
        )
        
        for idx, uid in enumerate(users.keys(), 1):
            try:
                await event.client.send_message(int(uid), message)
                success += 1
            except:
                failed += 1
            
            if idx % 10 == 0:
                await status_msg.edit(
                    f"📢 **BROADCASTING...**\n\n"
                    f"Progress: {idx}/{len(users)}\n"
                    f"✅ Success: {success}\n"
                    f"❌ Failed: {failed}"
                )
        
        await status_msg.edit(
            f"✅ **BROADCAST COMPLETE**\n\n"
            f"📊 Total: {len(users)}\n"
            f"✅ Success: {success}\n"
            f"❌ Failed: {failed}"
        )
        
        del temp_admin_data[user_id]


# ============================================
# BUTTON TEXT HANDLER
# ============================================

async def button_text_handler(event):
    """Handle button text clicks"""
    user_id = event.sender_id
    
    if not is_admin(user_id):
        return
    
    text = event.raw_text.strip()
    
    handlers = {
        "➕ Add User": add_user_handler,
        "📋 View Users": view_users_handler,
        "💎 Set Plan": set_plan_handler,
        "🗑️ Delete User": delete_user_handler,
        "👨‍💼 Add Admin": add_admin_handler,
        "❌ Remove Admin": remove_admin_handler,
        "📢 Broadcast": broadcast_handler,
        "📊 Stats": stats_handler
    }
    
    handler = handlers.get(text)
    if handler:
        await handler(event)


# ============================================
# MAIN FUNCTION
# ============================================

async def main():
    """Start admin bot"""
    print("🔧 Initializing Admin Bot...")
    
    bot = TelegramClient('admin_bot', ADMIN_API_ID, ADMIN_API_HASH)
    
    await bot.start(bot_token=ADMIN_BOT_TOKEN)
    
    me = await bot.get_me()
    print(f"✅ Admin Bot started: @{me.username}")
    
    # Register handlers
    bot.add_event_handler(start_handler, events.NewMessage(pattern='/start'))
    bot.add_event_handler(message_handler, events.NewMessage(incoming=True, func=lambda e: e.sender_id in temp_admin_data))
    bot.add_event_handler(button_text_handler, events.NewMessage(incoming=True, func=lambda e: not e.raw_text.startswith('/')))
    
    print("✅ Admin Bot handlers registered")
    print("👑 Admin Panel ready!\n")
    
    await bot.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(main())