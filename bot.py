"""
Main Bot Launcher - UPDATED
✅ Auto-starts admin bot
"""

import asyncio
from telethon import TelegramClient

from config import (
    BOT_TOKEN, OWNER_API_ID, OWNER_API_HASH, 
    SESSIONS_FILE, DATA_DIR, user_sessions
)
from utils import load_json
from handlers import register_command_handlers
from callbacks import register_callback_handlers
from message_flow import register_message_handlers
from scheduler import start_scheduler


# ============================================
# RESTORE USER SESSIONS
# ============================================

async def restore_user_sessions():
    """Restore user sessions from saved data"""
    sessions = load_json(SESSIONS_FILE, {})
    restored_count = 0
    
    print("\n🔄 Restoring user sessions...")
    
    for user_id_str, session_info in sessions.items():
        try:
            user_id = int(user_id_str)
            api_id = session_info.get('api_id')
            api_hash = session_info.get('api_hash')
            
            if not api_id or not api_hash:
                print(f"⚠️ Skipping user {user_id}: Missing API credentials")
                continue
            
            # Create client for user
            session_name = f"{DATA_DIR}/user_{user_id}"
            client = TelegramClient(session_name, api_id, api_hash)
            
            # Connect
            await client.connect()
            
            # Check if authorized
            if await client.is_user_authorized():
                user_sessions[user_id] = client
                restored_count += 1
                print(f"✅ Restored session for user {user_id}")
            else:
                print(f"⚠️ User {user_id} session expired")
                await client.disconnect()
                
        except Exception as e:
            print(f"❌ Failed to restore session for user {user_id_str}: {e}")
    
    print(f"✅ Restored {restored_count} user session(s)\n")


# ============================================
# AUTO-START ADMIN BOT
# ============================================

async def start_admin_bot():
    """Start admin bot automatically"""
    try:
        print("\n👑 Starting Admin Bot...")
        
        # Import and run admin bot
        import admin_bot
        
        # Run admin bot in background
        asyncio.create_task(admin_bot.main())
        
        print("✅ Admin Bot started successfully!\n")
    except Exception as e:
        print(f"⚠️ Admin Bot failed to start: {e}\n")


# ============================================
# STARTUP BANNER
# ============================================

def print_startup_banner():
    """Print startup banner"""
    banner = """
    ╔═══════════════════════════════════════╗
    ║                                      ║
    ║     🤖 AUTO FORWARDER BOT 🤖        ║
    ║                                      ║
    ║     Version: 2.1 (Enhanced)         ║
    ║     Status: Starting...             ║
    ║                                      ║
    ╚═══════════════════════════════════════╝
    """
    print(banner)


def print_success_banner():
    """Print success banner"""
    banner = """
    ╔═══════════════════════════════════════╗
    ║                                      ║
    ║     ✅ BOT STARTED SUCCESSFULLY     ║
    ║                                      ║
    ║     📱 Main Bot: Running            ║
    ║     👑 Admin Bot: Running           ║
    ║     ⚡ All systems operational      ║
    ║     🚀 Scheduler active             ║
    ║                                      ║
    ║     Press Ctrl+C to stop            ║
    ║                                      ║
    ╚═══════════════════════════════════════╝
    """
    print(banner)


# ============================================
# MAIN BOT FUNCTION
# ============================================

async def main():
    """Main bot function"""
    
    # Print startup banner
    print_startup_banner()
    
    # Create bot client
    print("🔧 Initializing bot client...")
    bot = TelegramClient('forwarder_bot', OWNER_API_ID, OWNER_API_HASH)
    
    # Start bot
    print("🚀 Starting bot...")
    await bot.start(bot_token=BOT_TOKEN)
    
    # Get bot info
    me = await bot.get_me()
    print(f"✅ Bot started: @{me.username}")
    print(f"🆔 Bot ID: {me.id}")
    
    # Restore user sessions
    await restore_user_sessions()
    
    # Register all handlers
    print("\n📝 Registering handlers...")
    register_command_handlers(bot)
    register_callback_handlers(bot)
    register_message_handlers(bot)
    
    # Start the scheduler system
    print("\n⏰ Starting scheduler system...")
    start_scheduler(bot)
    
    # ✅ AUTO-START ADMIN BOT
    await start_admin_bot()
    
    # Print success banner
    print_success_banner()
    
    # Keep bot running
    await bot.run_until_disconnected()


# ============================================
# CLEANUP ON EXIT
# ============================================

async def cleanup():
    """Cleanup function on bot shutdown"""
    print("\n\n⚠️ Shutting down bot...")
    
    # Stop scheduler
    try:
        from scheduler import stop_scheduler
        stop_scheduler()
        print("✅ Scheduler stopped")
    except:
        pass
    
    # Disconnect all user sessions
    disconnected = 0
    for user_id, client in list(user_sessions.items()):
        try:
            await client.disconnect()
            disconnected += 1
            print(f"✅ Disconnected user {user_id}")
        except Exception as e:
            print(f"⚠️ Error disconnecting user {user_id}: {e}")
    
    print(f"\n✅ Disconnected {disconnected} user session(s)")
    print("👋 Bot stopped successfully!")


# ============================================
# RUN BOT
# ============================================

if __name__ == "__main__":
    try:
        # Run bot
        asyncio.run(main())
        
    except KeyboardInterrupt:
        # Handle Ctrl+C
        print("\n⚠️ Received shutdown signal...")
        asyncio.run(cleanup())
        
    except Exception as e:
        # Handle errors
        print(f"\n❌ Fatal error: {e}")
        asyncio.run(cleanup())