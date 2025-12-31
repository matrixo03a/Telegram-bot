"""
Callback Handlers
Handles all inline button actions
FULL PRODUCTION VERSION
"""

from telethon import events, Button
from config import (
    SESSIONS_FILE, SETTINGS_FILE, temp_data, user_sessions,
    get_main_keyboard
)
from utils import load_json, save_json, is_authorized


# ======================================================
# MAIN CALLBACK HANDLER
# ======================================================

async def callback_handler(event, bot):
    user_id = event.sender_id
    data = event.data.decode()

    if not is_authorized(user_id):
        await event.answer("Unauthorized", alert=True)
        return

    # ----------------------------------------------
    # LOGOUT CONFIRM
    # ----------------------------------------------
    if data == "confirm_logout":
        sessions = load_json(SESSIONS_FILE, {})

        if str(user_id) in sessions:
            del sessions[str(user_id)]
            save_json(SESSIONS_FILE, sessions)

        # Disconnect active session
        if user_id in user_sessions:
            try:
                await user_sessions[user_id].disconnect()
            except:
                pass
            user_sessions.pop(user_id, None)

        temp_data.pop(user_id, None)

        await event.edit(
            "✅ **LOGOUT SUCCESSFUL**\n\n"
            "Your account has been disconnected.\n\n"
            "Use /setup to login again."
        )
        return

    # ----------------------------------------------
    # LOGOUT CANCEL
    # ----------------------------------------------
    if data == "cancel_logout":
        await event.edit(
            "❌ **LOGOUT CANCELLED**\n\n"
            "You are still logged in.",
            buttons=get_main_keyboard()
        )
        return

    # ----------------------------------------------
    # TASK / BROADCAST CANCEL
    # ----------------------------------------------
    if data in ("cancel_task", "cancel_broadcast"):
        temp_data.pop(user_id, None)
        await event.edit(
            "❌ **CANCELLED**\n\n"
            "Operation cancelled.\n\n"
            "Type /start to return to menu."
        )
        return

    # ----------------------------------------------
    # BACK TO MAIN MENU
    # ----------------------------------------------
    if data == "back_main":
        await event.edit(
            "🏠 **MAIN MENU**",
            buttons=get_main_keyboard()
        )
        return

    # ----------------------------------------------
    # TIMEZONE BUTTON (HANDLED IN CALLBACKS FLOW)
    # ----------------------------------------------
    if data == "timezone":
        from callbacks_timezone import show_timezone_menu
        await show_timezone_menu(event, bot)
        return

    # ----------------------------------------------
    # UNKNOWN CALLBACK
    # ----------------------------------------------
    await event.answer("⚠️ Unknown action", alert=True)


# ======================================================
# REGISTER CALLBACK HANDLERS
# ======================================================

def register_callback_handlers(bot):
    bot.add_event_handler(
        lambda e: callback_handler(e, bot),
        events.CallbackQuery
    )

    print("✅ Callback handlers registered")