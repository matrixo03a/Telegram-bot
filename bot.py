"""
MAIN BOT LAUNCHER
Starts:
✅ User Forwarder Bot
✅ Scheduler System
✅ Admin Bot (auto-start)
"""

import asyncio
from telethon import TelegramClient

from config import (
    BOT_TOKEN,
    OWNER_API_ID,
    OWNER_API_HASH,
    user_sessions
)

from handlers import register_command_handlers
from callbacks import register_callback_handlers
from message_flow import register_message_handlers
from scheduler import start_scheduler

# ============================================
# START ADMIN BOT (BACKGROUND)
# ============================================

async def start_admin_bot():
    try:
        import admin_bot
        asyncio.create_task(admin_bot.main())
        print("👑 Admin bot started")
    except Exception as e:
        print(f"⚠️ Admin bot failed: {e}")

# ============================================
# MAIN USER BOT
# ============================================

async def main():
    print("🚀 Starting Auto Forwarder Bot...")

    bot = TelegramClient(
        "forwarder_bot",
        OWNER_API_ID,
        OWNER_API_HASH
    )

    await bot.start(bot_token=BOT_TOKEN)

    me = await bot.get_me()
    print(f"✅ Bot started: @{me.username}")
    print(f"🆔 Bot ID: {me.id}")

    # Register handlers
    register_command_handlers(bot)
    register_callback_handlers(bot)
    register_message_handlers(bot)

    # Start scheduler
    start_scheduler()
    print("⏰ Scheduler running")

    # Start admin bot
    await start_admin_bot()

    print("🎉 SYSTEM READY — PRESS CTRL+C TO STOP")
    await bot.run_until_disconnected()

# ============================================
# CLEAN SHUTDOWN
# ============================================

async def shutdown():
    print("\n⚠️ Shutting down bot...")

    for uid, client in list(user_sessions.items()):
        try:
            await client.disconnect()
            print(f"🔌 User session closed: {uid}")
        except:
            pass

    print("✅ Shutdown complete")

# ============================================
# ENTRY POINT
# ============================================

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        asyncio.run(shutdown())
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        asyncio.run(shutdown())