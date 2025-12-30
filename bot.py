import time
import sqlite3
from datetime import datetime, timedelta

from telegram import (
    Update,
    ReplyKeyboardMarkup,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
from telegram.request import HTTPXRequest

# ================= CONFIG =================
TOKEN = "8456691972:AAGI_Y5pSZhZL5XXEssm2Yi4CI2pEGzBLEI"
ADMIN_ID = 5510835149
DB_PATH = "bot.db"
# =========================================


# ---------------- DATABASE ----------------
def db():
    return sqlite3.connect(DB_PATH)


def init_db():
    con = db()
    cur = con.cursor()
    cur.executescript("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY,
        plan TEXT,
        expires TEXT
    );
    """)
    con.commit()
    con.close()


# ---------------- HELPERS ----------------
def is_admin(uid):
    return uid == ADMIN_ID


def has_active_plan(uid):
    con = db()
    cur = con.cursor()
    cur.execute("SELECT expires FROM users WHERE id=?", (uid,))
    r = cur.fetchone()
    con.close()
    return r and datetime.fromisoformat(r[0]) > datetime.utcnow()


def dashboard():
    return ReplyKeyboardMarkup(
        [
            ["⚙️ Settings", "📊 Analytics"],
            ["📁 Folders", "⏰ Scheduler"],
            ["📢 Broadcast", "🚪 Logout"],
        ],
        resize_keyboard=True,
    )


# ---------------- HANDLERS ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id

    if is_admin(uid):
        kb = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("🎁 Trial", callback_data="trial")],
                [InlineKeyboardButton("📅 Monthly", callback_data="monthly")],
                [InlineKeyboardButton("📆 Yearly", callback_data="yearly")],
            ]
        )
        await update.message.reply_text("👑 Admin Panel", reply_markup=kb)
        return

    if not has_active_plan(uid):
        await update.message.reply_text(
            "⚠️ SUBSCRIPTION EXPIRED\nContact admin."
        )
        return

    await update.message.reply_text("🏠 Dashboard", reply_markup=dashboard())


async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ BOT IS ALIVE")


# ---------------- MAIN ----------------
init_db()

request = HTTPXRequest(
    connect_timeout=30,
    read_timeout=30,
    write_timeout=30,
    pool_timeout=30,
)

app = ApplicationBuilder().token(TOKEN).request(request).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("ping", ping))

print("🤖 BOT RUNNING – KEEP ALIVE MODE")

# 🔥 START POLLING IN BACKGROUND
app.run_polling(stop_signals=None)

# 🔥 KEEP PROCESS ALIVE FOR FLY.IO
while True:
    time.sleep(3600)