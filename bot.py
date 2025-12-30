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


async def inline_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    if is_admin(q.from_user.id):
        context.user_data["plan"] = q.data
        await q.message.reply_text("Send User ID:")


async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = update.message.text

    if is_admin(uid) and "plan" in context.user_data:
        plan = context.user_data.pop("plan")
        days = 3 if plan == "trial" else 30 if plan == "monthly" else 365
        exp = datetime.utcnow() + timedelta(days=days)

        con = db()
        cur = con.cursor()
        cur.execute(
            "INSERT OR REPLACE INTO users VALUES (?,?,?)",
            (int(text), plan, exp.isoformat()),
        )
        con.commit()
        con.close()

        await update.message.reply_text("✅ Access granted")
        await context.bot.send_message(
            int(text), "🎉 Access activated!\nSend /start"
        )
        return


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
app.add_handler(CallbackQueryHandler(inline_handler))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

print("🤖 BOT RUNNING (FINAL FIXED VERSION)")
app.run_polling()