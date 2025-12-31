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
from modules.folders import folders_manager_view

# ---------------- START ----------------
async def start(update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id

    if not has_active_plan(uid):
        await update.message.reply_text("🚫 ACCESS DENIED\nContact admin.")
        return

    if not has_session(uid):
        context.user_data["login_step"] = "api_id"
        await update.message.reply_text("🔐 Enter API ID:")
        return

    await update.message.reply_text(
        "👋 Welcome!\nChoose an option below 👇",
        reply_markup=dashboard()
    )

# ---------------- TEXT ROUTER ----------------
async def text_router(update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = update.message.text

    if not has_session(uid):
        await update.message.reply_text("🔐 Send /start")
        return

    if text == "📁 Folders":
        await folders_manager_view(update, context)
        return

    if text == "📢 Broadcast":
        await update.message.reply_text("📢 Broadcast (next step)")
        return

    if text == "⏰ Scheduler":
        await update.message.reply_text("⏰ Scheduler (next step)")
        return

    if text == "⚙️ Settings":
        await update.message.reply_text("⚙️ Settings")
        return

    if text == "🚪 Logout":
        await update.message.reply_text("👋 Logged out")
        return

# ---------------- INLINE ROUTER ----------------
async def inline_router(update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data

    if data == "back_dashboard":
        await q.message.reply_text(
            "⬅️ Back",
            reply_markup=dashboard()
        )
        return

    if data == "close":
        await q.message.delete()
        return

    if data == "f_create":
        context.user_data["folder_step"] = "create"
        await q.message.reply_text("Send folder name to create:")
        return

    if data == "f_view":
        await q.message.reply_text("📋 View folders (next step)")
        return

    if data == "f_rename":
        await q.message.reply_text("✏️ Rename folder (next step)")
        return

    if data == "f_delete":
        await q.message.reply_text("🗑️ Delete folder (next step)")
        return

    if data == "g_move":
        await q.message.reply_text("🔁 Move groups (next step)")
        return

    if data == "g_add":
        context.user_data["add_group"] = True
        await q.message.reply_text(
            "Send group details (comma separated):\n"
            "- @username\n"
            "- -100xxxx\n"
            "- https://t.me/..."
        )
        return

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
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_router))
app.add_handler(CallbackQueryHandler(inline_router))

print("🤖 BOT RUNNING (Folders Manager WORKING)")
app.run_polling(stop_signals=None)

while True:
    time.sleep(3600)