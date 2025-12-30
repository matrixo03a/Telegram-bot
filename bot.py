from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from telegram.request import HTTPXRequest
from datetime import datetime, timedelta
import sqlite3

from telethon import TelegramClient
from telethon.sessions import StringSession

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
    CREATE TABLE IF NOT EXISTS tg_sessions(
        user_id INTEGER PRIMARY KEY,
        session TEXT
    );
    CREATE TABLE IF NOT EXISTS folders(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        name TEXT
    );
    """)
    con.commit()
    con.close()

# ---------------- HELPERS ----------------
def is_admin(uid): return uid == ADMIN_ID

def has_active_plan(uid):
    con=db();cur=con.cursor()
    cur.execute("SELECT expires FROM users WHERE id=?", (uid,))
    r=cur.fetchone();con.close()
    return r and datetime.fromisoformat(r[0]) > datetime.utcnow()

def has_session(uid):
    con=db();cur=con.cursor()
    cur.execute("SELECT session FROM tg_sessions WHERE user_id=?", (uid,))
    r=cur.fetchone();con.close()
    return bool(r)

# ---------------- DASHBOARD UI ----------------
def dashboard():
    return ReplyKeyboardMarkup(
        [
            ["⚙️ Settings", "📊 Analytics"],
            ["📁 Folders", "⏰ Scheduler"],
            ["📢 Broadcast", "📜 Logs"],
            ["📘 Help", "🚪 Logout"]
        ],
        resize_keyboard=True
    )

tg_clients = {}

# ---------------- START ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id

    if is_admin(uid):
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎁 Trial (3 Days)", callback_data="trial")],
            [InlineKeyboardButton("📅 Monthly", callback_data="monthly")],
            [InlineKeyboardButton("📆 Yearly", callback_data="yearly")]
        ])
        await update.message.reply_text("👑 Admin Panel", reply_markup=kb)
        return

    if not has_active_plan(uid):
        await update.message.reply_text(
            "⚠️ SUBSCRIPTION EXPIRED\n\nContact admin to renew."
        )
        return

    if not has_session(uid):
        context.user_data.clear()
        context.user_data["login"] = "api_id"
        await update.message.reply_text("🔐 Enter API ID:")
        return

    await update.message.reply_text("🏠 Dashboard", reply_markup=dashboard())

# ---------------- INLINE (ADMIN) ----------------
async def inline_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    if is_admin(q.from_user.id):
        context.user_data["admin_plan"] = q.data
        await q.message.reply_text("Send User ID:")

# ---------------- TEXT ROUTER ----------------
async def router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = update.message.text

    # ---------- ADMIN PLAN ----------
    if is_admin(uid) and "admin_plan" in context.user_data:
        plan = context.user_data.pop("admin_plan")
        days = 3 if plan=="trial" else 30 if plan=="monthly" else 365
        name = "Trial" if days==3 else "Monthly" if days==30 else "Yearly"
        exp = datetime.utcnow() + timedelta(days=days)

        con=db();cur=con.cursor()
        cur.execute("INSERT OR REPLACE INTO users VALUES (?,?,?)",(int(text),name,exp.isoformat()))
        con.commit();con.close()

        await update.message.reply_text("✅ Access Granted")
        await context.bot.send_message(
            int(text),
            f"🎉 {name} Activated\n⏳ {days} days\n\nSend /start"
        )
        return

    # ---------- LOGIN FLOW ----------
    step = context.user_data.get("login")
    if step=="api_id":
        context.user_data["api_id"]=int(text)
        context.user_data["login"]="api_hash"
        await update.message.reply_text("Enter API HASH:")
        return

    if step=="api_hash":
        context.user_data["api_hash"]=text
        context.user_data["login"]="phone"
        await update.message.reply_text("Enter phone number:")
        return

    if step=="phone":
        client=TelegramClient(
            StringSession(),
            context.user_data["api_id"],
            context.user_data["api_hash"]
        )
        await client.connect()
        await client.send_code_request(text)

        tg_clients[uid]=client
        context.user_data["phone"]=text
        context.user_data["login"]="otp"
        await update.message.reply_text("Enter OTP (123456):")
        return

    if step=="otp":
        client=tg_clients[uid]
        await client.sign_in(
            phone=context.user_data["phone"],
            code=text.replace(" ","")
        )
        session=client.session.save()

        con=db();cur=con.cursor()
        cur.execute("INSERT OR REPLACE INTO tg_sessions VALUES (?,?)",(uid,session))
        con.commit();con.close()

        context.user_data.clear()
        await update.message.reply_text("✅ Login Successful!\nSend /start")
        return

    # ---------- DASHBOARD BUTTONS ----------
    if text=="⚙️ Settings":
        await update.message.reply_text("⚙️ Settings\n• Account: Connected\n• Timezone: UTC")
    elif text=="📊 Analytics":
        await update.message.reply_text("📊 Analytics\n• Active folders\n• Schedules\n• Broadcasts")
    elif text=="📁 Folders":
        await update.message.reply_text("📁 Folders\nSend folder name to create.")
        context.user_data["mk_folder"]=True
    elif context.user_data.get("mk_folder"):
        con=db();cur=con.cursor()
        cur.execute("INSERT INTO folders(user_id,name) VALUES (?,?)",(uid,text))
        con.commit();con.close()
        context.user_data.pop("mk_folder")
        await update.message.reply_text("✅ Folder Created")
    elif text=="⏰ Scheduler":
        await update.message.reply_text("⏰ Scheduler\n(Coming next step)")
    elif text=="📢 Broadcast":
        await update.message.reply_text("📢 Broadcast\nSend message to broadcast (demo)")
    elif text=="📜 Logs":
        await update.message.reply_text("📜 Logs\nNo errors logged.")
    elif text=="📘 Help":
        await update.message.reply_text("📘 Help\nContact admin for support.")
    elif text=="🚪 Logout":
        await update.message.reply_text("👋 Logged out")

# ---------------- INIT ----------------
init_db()

request = HTTPXRequest(
    connect_timeout=30,
    read_timeout=30,
    write_timeout=30,
    pool_timeout=30
)

app = ApplicationBuilder().token(TOKEN).request(request).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(inline_handler))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, router))

print("🤖 Dashboard Bot Running (Volt-style UI)…")
app.run_polling()