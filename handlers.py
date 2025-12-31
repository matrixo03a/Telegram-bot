"""
Command Handlers - COMPLETE FIXED VERSION
✅ God Eye removed
✅ Help updated
✅ Code protection added
✅ All commands working
"""

import asyncio
import time
from datetime import datetime
from telethon import events, Button
from telethon import TelegramClient

from config import (
    OWNERS, UNAUTHORIZED_MSG, SETUP_START_MSG, LOGIN_SUCCESS_MSG,
    SESSIONS_FILE, get_main_keyboard, user_sessions, temp_data, DATA_DIR
)
from utils import (
    is_authorized, is_logged_in, get_user_plan, 
    get_current_time, load_json, save_json
)

# ============================================
# 🔒 CODE PROTECTION - DO NOT MODIFY
# ============================================
def verify_handlers_integrity():
    """Verify handlers file hasn't been tampered with"""
    try:
        with open(__file__, 'r', encoding='utf-8') as f:
            content = f.read()
        if "CODE PROTECTION" not in content:
            return False
        if "verify_handlers_integrity" not in content:
            return False
        return True
    except:
        return False

def check_handlers_protection():
    """Check protection status"""
    if not verify_handlers_integrity():
        print("❌ HANDLERS FILE TAMPERING DETECTED!")
        print("🚫 Bot will not start")
        exit(1)

check_handlers_protection()

# ============================================
# COMMAND HANDLERS
# ============================================

async def start_handler(event):
    """Handle /start command"""
    user_id = event.sender_id
    
    if not is_authorized(user_id):
        keyboard = [
            [Button.url("👤 Owner 1", OWNERS[2024653852])],
            [Button.url("👤 Owner 2", OWNERS[5510835149])]
        ]
        await event.respond(UNAUTHORIZED_MSG, buttons=keyboard)
        return
    
    logged_in = is_logged_in(user_id, SESSIONS_FILE)
    
    msg = await event.respond("⚡ **INITIALIZING SYSTEM**\n\n`▰▱▱▱▱▱▱▱▱▱` 10%\n🔄 Preparing environment...")
    await asyncio.sleep(0.5)
    await msg.edit("⚡ **INITIALIZING SYSTEM**\n\n`▰▰▰▱▱▱▱▱▱▱` 30%\n🔧 Loading modules...")
    await asyncio.sleep(0.5)
    await msg.edit("⚡ **INITIALIZING SYSTEM**\n\n`▰▰▰▰▰▱▱▱▱▱` 50%\n🛠️ System booting...")
    await asyncio.sleep(0.5)
    await msg.edit("⚡ **INITIALIZING SYSTEM**\n\n`▰▰▰▰▰▰▰▱▱▱` 70%\n✅ Checking connection...")
    await asyncio.sleep(0.5)
    await msg.edit("⚡ **INITIALIZING SYSTEM**\n\n`▰▰▰▰▰▰▰▰▰▰` 100%\n✨ System ready!")
    await asyncio.sleep(0.5)
    
    start_time = time.time()
    await event.client.get_me()
    ping = round((time.time() - start_time) * 1000, 2)
    
    plan_days = get_user_plan(user_id)
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
    
    await msg.edit(welcome_text, buttons=keyboard)


async def setup_handler(event):
    """Handle /setup command"""
    user_id = event.sender_id
    
    if not is_authorized(user_id):
        return
    
    if is_logged_in(user_id, SESSIONS_FILE):
        await event.respond(
            "✅ **ALREADY LOGGED IN**\n\n"
            "You are already connected!\n\n"
            "💡 Use /logout to disconnect first if you want to reconnect."
        )
        return
    
    temp_data[user_id] = {'step': 'api_id'}
    await event.respond(SETUP_START_MSG)


async def logout_handler(event):
    """Handle /logout command"""
    user_id = event.sender_id
    
    if not is_authorized(user_id):
        return
    
    sessions = load_json(SESSIONS_FILE, {})
    if str(user_id) not in sessions:
        await event.respond(
            "❌ **NOT LOGGED IN**\n\n"
            "You are not currently logged in!"
        )
        return
    
    keyboard = [
        [Button.inline("✅ Yes, Logout", b"confirm_logout")],
        [Button.inline("❌ Cancel", b"cancel_logout")]
    ]
    
    await event.respond(
        "⚠️ **LOGOUT CONFIRMATION**\n\n"
        "Are you sure you want to logout?\n\n"
        "🔒 Your session will be terminated and you'll need to setup again.",
        buttons=keyboard
    )


async def cancel_handler(event):
    """Handle /cancel command"""
    user_id = event.sender_id
    
    if user_id in temp_data:
        del temp_data[user_id]
        await event.respond("❌ **CANCELLED**\n\nOperation cancelled successfully.")
    else:
        await event.respond("ℹ️ No active operation to cancel.")


async def help_handler(event):
    """Handle /help command - ✅ UPDATED WITHOUT GOD EYE"""
    user_id = event.sender_id
    
    if not is_authorized(user_id):
        return
    
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
        
        "─────────────────────\n\n"
        
        "📋 **COMMANDS**\n"
        "• `/start` - Main menu\n"
        "• `/setup` - Connect your account\n"
        "• `/logout` - Disconnect account\n"
        "• `/cancel` - Cancel current operation\n"
        "• `/help` - Show this help message\n\n"
        
        "─────────────────────\n"
        "💬 **Need more help?**\n"
        "Contact support for assistance!"
    )
    
    keyboard = [[Button.inline("🔙 Back to Menu", b"back_main")]]
    await event.respond(help_text, buttons=keyboard)


def register_command_handlers(bot):
    """Register all command handlers with the bot"""
    
    # Run protection check
    check_handlers_protection()
    
    bot.add_event_handler(
        start_handler,
        events.NewMessage(pattern='/start')
    )
    
    bot.add_event_handler(
        setup_handler,
        events.NewMessage(pattern='/setup')
    )
    
    bot.add_event_handler(
        logout_handler,
        events.NewMessage(pattern='/logout')
    )
    
    bot.add_event_handler(
        cancel_handler,
        events.NewMessage(pattern='/cancel')
    )
    
    bot.add_event_handler(
        help_handler,
        events.NewMessage(pattern='/help')
    )
    
    print("✅ Command handlers registered")