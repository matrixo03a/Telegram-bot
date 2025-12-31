import time
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
from telegram.request import HTTPXRequest

from config import TOKEN
from database import init_db
from helpers import has_active_plan, has_session
from modules.dashboard import dashboard
from modules.folders import folders_menu
from modules.broadcast import broadcast_menu
from modules.auth import login_flow

# ---------------- START ----------------
async def start(update, context):
    uid = update.effective_user.id

    if not has_active_plan(uid):
        await update.message.reply_text("🚫 ACCESS DENIED")
        return

    if not has_session(uid):
        context.user_data["login_step"] = "api_id"
        await update.message.reply_text("🔐 Enter API ID:")
        return

    await update.message.reply_text(
        "👋 Welcome!",
        reply_markup=dashboard()
    )

# ---------------- ROUTER ----------------
async def router(update, context):
    uid = update.effective_user.id
    text = update.message.text

    # login flow
    if context.user_data.get("login_step"):
        handled = await login_flow(update, context)
        if handled:
            return

    if not has_session(uid):
        await update.message.reply_text("🔐 Send /start")
        return

    if text == "📁 Folders":
        await folders_menu(update, context)

    elif text == "📢 Broadcast":
        await broadcast_menu(update, context)

# ---------------- INIT ----------------
init_db()

request = HTTPXRequest(
    connect_timeout=30,
    read_timeout=30,
    write_timeout=30,
    pool_timeout=30,
)

app = ApplicationBuilder().token(TOKEN).request(request).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, router))

print("🤖 Modular Bot Running")
app.run_polling(stop_signals=None)

while True:
    time.sleep(3600)