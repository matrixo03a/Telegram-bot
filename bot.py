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
    CREATE TABLE IF NOT EXISTS groups(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        folder_id INTEGER,
        identifier TEXT
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


def has_session(uid):
    con = db()
    cur = con.cursor()
    cur.execute("SELECT session FROM tg_sessions WHERE user_id=?", (uid,))
    r = cur.fetchone()
    con.close()
    return bool(r)


def dashboard():
    return ReplyKeyboardMarkup(
        [
            ["📢 Broadcast"],
            ["📁 Folders", "⏰ Scheduler"],
            ["⚙️ Settings", "🚪 Logout"],
        ],
        resize_keyboard=True,
    )


tg_clients = {}


# ---------------- START ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id

    # ADMIN
    if is_admin(uid):
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎁 Trial (3 Days)", callback_data="trial")],
            [InlineKeyboardButton("📅 Monthly", callback_data="monthly")],
            [InlineKeyboardButton("📆 Yearly", callback_data="yearly")]
        ])
        await update.message.reply_text("👑 Admin Panel", reply_markup=kb)
        return

    # NO ACCESS
    if not has_active_plan(uid):
        await update.message.reply_text(
            "🚫 ACCESS DENIED\n\n"
            "You don't have access to use this bot.\n"
            "Please contact the owner/admin."
        )
        return

    # ACCESS BUT NOT LOGGED IN
    if not has_session(uid):
        context.user_data.clear()
        context.user_data["login_step"] = "api_id"
        await update.message.reply_text(
            "🔐 ACCOUNT SETUP\n\nPlease enter your API ID:"
        )
        return

    # LOGGED IN → WELCOME + DASHBOARD
    await update.message.reply_text(
        "👋 Welcome!\n\n"
        "Your Telegram account is connected successfully.\n"
        "Choose an option below 👇",
        reply_markup=dashboard()
    )


# ---------------- ADMIN INLINE ----------------
async def inline_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    data = q.data

    con = db()
    cur = con.cursor()

    # ADMIN PLAN ASSIGN
    if is_admin(uid) and data in ["trial", "monthly", "yearly"]:
        context.user_data["admin_plan"] = data
        await q.message.reply_text("Send User ID:")
        return

    # ---------- FOLDERS ----------
    if data == "f_create":
        context.user_data["folder_step"] = "create"
        await q.message.reply_text("📂 Send new folder name:")
        return

    if data == "g_add":
        cur.execute("SELECT id,name FROM folders WHERE user_id=?", (uid,))
        rows = cur.fetchall()
        kb = [[InlineKeyboardButton(n, callback_data=f"addgrp_{i}")] for i, n in rows]
        await q.message.reply_text("Select folder:", reply_markup=InlineKeyboardMarkup(kb))
        return

    if data.startswith("addgrp_"):
        context.user_data["add_group"] = int(data.split("_")[1])
        await q.message.reply_text(
            "Send group:\n"
            "- Chat ID\n"
            "- @username\n"
            "- Invite link"
        )
        return

    if data == "f_delete":
        cur.execute("SELECT id,name FROM folders WHERE user_id=?", (uid,))
        rows = cur.fetchall()
        kb = [[InlineKeyboardButton(n, callback_data=f"delf_{i}")] for i, n in rows]
        await q.message.reply_text("Select folder to delete:", reply_markup=InlineKeyboardMarkup(kb))
        return

    if data.startswith("delf_"):
        context.user_data["confirm_del"] = int(data.split("_")[1])
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Yes", callback_data="del_yes")],
            [InlineKeyboardButton("❌ Cancel", callback_data="del_no")]
        ])
        await q.message.reply_text("⚠️ Confirm delete?", reply_markup=kb)
        return

    if data == "del_yes":
        fid = context.user_data.pop("confirm_del")
        cur.execute("DELETE FROM folders WHERE id=?", (fid,))
        cur.execute("DELETE FROM groups WHERE folder_id=?", (fid,))
        con.commit()
        await q.message.reply_text("✅ Folder deleted")
        return

    if data == "del_no":
        context.user_data.pop("confirm_del", None)
        await q.message.reply_text("❌ Cancelled")
        return

    con.close()


# ---------------- FOLDERS MENU ----------------
async def folders_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Create Folder", callback_data="f_create")],
        [InlineKeyboardButton("➕ Add Group", callback_data="g_add")],
        [InlineKeyboardButton("🗑️ Delete Folder", callback_data="f_delete")],
    ])
    await update.message.reply_text("📁 Folder Manager", reply_markup=kb)


# ---------------- TEXT ROUTER ----------------
async def router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = update.message.text

    # HARD BLOCK IF NOT LOGGED IN
    if not has_session(uid):
        step = context.user_data.get("login_step")
        if not step:
            await update.message.reply_text("🔐 Please complete account setup first.\nSend /start")
            return

    # ADMIN PLAN ASSIGN
    if is_admin(uid) and "admin_plan" in context.user_data:
        plan = context.user_data.pop("admin_plan")
        days = 3 if plan == "trial" else 30 if plan == "monthly" else 365
        exp = datetime.utcnow() + timedelta(days=days)

        con = db()
        cur = con.cursor()
        cur.execute(
            "INSERT OR REPLACE INTO users VALUES (?,?,?)",
            (int(text), plan, exp.isoformat())
        )
        con.commit()
        con.close()

        await update.message.reply_text("✅ Access Granted")
        await context.bot.send_message(
            int(text),
            "🎉 ACCESS GRANTED\n\nNow send /start to setup your account."
        )
        return

    # LOGIN FLOW
    step = context.user_data.get("login_step")

    if step == "api_id":
        context.user_data["api_id"] = int(text)
        context.user_data["login_step"] = "api_hash"
        await update.message.reply_text("Enter API HASH:")
        return

    if step == "api_hash":
        context.user_data["api_hash"] = text
        context.user_data["login_step"] = "phone"
        await update.message.reply_text("Enter phone number:")
        return

    if step == "phone":
        client = TelegramClient(
            StringSession(),
            context.user_data["api_id"],
            context.user_data["api_hash"]
        )
        await client.connect()
        await client.send_code_request(text)

        tg_clients[uid] = client
        context.user_data["phone"] = text
        context.user_data["login_step"] = "otp"
        await update.message.reply_text("Enter OTP (123456):")
        return

    if step == "otp":
        client = tg_clients[uid]
        await client.sign_in(
            phone=context.user_data["phone"],
            code=text.replace(" ", "")
        )
        session = client.session.save()

        con = db()
        cur = con.cursor()
        cur.execute(
            "INSERT OR REPLACE INTO tg_sessions VALUES (?,?)",
            (uid, session)
        )
        con.commit()
        con.close()

        context.user_data.clear()
        await update.message.reply_text(
            "✅ ACCOUNT CONNECTED SUCCESSFULLY\n\nSend /start to open dashboard"
        )
        return

    # CREATE FOLDER
    if context.user_data.get("folder_step") == "create":
        con = db()
        cur = con.cursor()
        cur.execute("INSERT INTO folders(user_id,name) VALUES (?,?)", (uid, text))
        con.commit()
        con.close()
        context.user_data.pop("folder_step")
        await update.message.reply_text("✅ Folder created")
        return

    # ADD GROUP
    if context.user_data.get("add_group"):
        fid = context.user_data.pop("add_group")
        con = db()
        cur = con.cursor()
        cur.execute("INSERT INTO groups(folder_id,identifier) VALUES (?,?)", (fid, text))
        con.commit()
        con.close()
        await update.message.reply_text("✅ Group added")
        return

    # DASHBOARD BUTTONS
    if text == "📁 Folders":
        await folders_menu(update, context)
    elif text == "📢 Broadcast":
        await update.message.reply_text("📢 Broadcast (next step)")
    elif text == "⏰ Scheduler":
        await update.message.reply_text("⏰ Scheduler (next step)")
    elif text == "⚙️ Settings":
        await update.message.reply_text("⚙️ Settings")
    elif text == "🚪 Logout":
        await update.message.reply_text("👋 Logged out")


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
app.add_handler(CallbackQueryHandler(inline_handler))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, router))

print("🤖 BOT RUNNING (WELCOME + FULL FOLDERS)")
app.run_polling(stop_signals=None)

while True:
    time.sleep(3600)