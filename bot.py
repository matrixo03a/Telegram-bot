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


def get_folder_stats(uid):
    con = db()
    cur = con.cursor()

    cur.execute("SELECT COUNT(*) FROM folders WHERE user_id=?", (uid,))
    total_folders = cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*)
        FROM groups g
        JOIN folders f ON f.id = g.folder_id
        WHERE f.user_id=?
    """, (uid,))
    total_groups = cur.fetchone()[0]

    con.close()
    return total_folders, total_groups


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

    if is_admin(uid):
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎁 Trial (3 Days)", callback_data="trial")],
            [InlineKeyboardButton("📅 Monthly", callback_data="monthly")],
            [InlineKeyboardButton("📆 Yearly", callback_data="yearly")]
        ])
        await update.message.reply_text("👑 Admin Panel", reply_markup=kb)
        return

    if not has_active_plan(uid):
        await update.message.reply_text("🚫 ACCESS DENIED\n\nPlease contact admin.")
        return

    if not has_session(uid):
        context.user_data.clear()
        context.user_data["login_step"] = "api_id"
        await update.message.reply_text("🔐 Enter API ID:")
        return

    await update.message.reply_text(
        "👋 Welcome!\n\nYour account is connected.\nChoose an option 👇",
        reply_markup=dashboard()
    )


# ---------------- FOLDERS MANAGER ----------------
async def folders_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id

    con = db()
    cur = con.cursor()
    cur.execute(
        "SELECT id FROM folders WHERE user_id=? AND name='Default Folder'",
        (uid,)
    )
    if not cur.fetchone():
        cur.execute(
            "INSERT INTO folders(user_id,name) VALUES (?,?)",
            (uid, "Default Folder")
        )
        con.commit()
    con.close()

    total_folders, total_groups = get_folder_stats(uid)

    text = (
        "📁 *FOLDERS MANAGER*\n\n"
        f"📊 Total Folders: *{total_folders}*\n"
        f"📂 Total Groups: *{total_groups}*\n\n"
        "Organize your groups efficiently:"
    )

    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("➕ Create Folder", callback_data="f_create"),
            InlineKeyboardButton("📋 View Folders", callback_data="f_view"),
        ],
        [
            InlineKeyboardButton("✏️ Rename Folder", callback_data="f_rename"),
            InlineKeyboardButton("🗑️ Delete Folder", callback_data="f_delete"),
        ],
        [
            InlineKeyboardButton("🔁 Move Groups", callback_data="g_move"),
            InlineKeyboardButton("➕ Add Groups", callback_data="g_add"),
        ],
        [
            InlineKeyboardButton("⬅️ Back", callback_data="back_dashboard"),
            InlineKeyboardButton("❌ Close", callback_data="close"),
        ],
    ])

    await update.message.reply_text(
        text,
        reply_markup=kb,
        parse_mode="Markdown",
    )


# ---------------- INLINE HANDLER ----------------
async def inline_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    data = q.data

    if data == "back_dashboard":
        await q.message.reply_text("👋 Back to menu", reply_markup=dashboard())
        return

    if data == "close":
        await q.message.delete()
        return

    if data == "f_create":
        context.user_data["folder_step"] = "create"
        await q.message.reply_text("Send folder name to create:")
        return

    if data == "g_add":
        context.user_data["add_group"] = True
        await q.message.reply_text(
            "Send group details (comma separated):\n"
            "- @username\n- -100xxxx\n- https://t.me/..."
        )
        return


# ---------------- ROUTER ----------------
async def router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = update.message.text.strip()

    if not has_session(uid) and not context.user_data.get("login_step"):
        await update.message.reply_text("🔐 Send /start")
        return

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
        await update.message.reply_text("Enter OTP:")
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
        cur.execute("INSERT OR REPLACE INTO tg_sessions VALUES (?,?)", (uid, session))
        con.commit()
        con.close()
        context.user_data.clear()
        await update.message.reply_text("✅ Login done\nSend /start")
        return

    if context.user_data.get("folder_step") == "create":
        con = db()
        cur = con.cursor()
        cur.execute("INSERT INTO folders(user_id,name) VALUES (?,?)", (uid, text))
        con.commit()
        con.close()
        context.user_data.pop("folder_step")

        await update.message.reply_text("📁 Folder created")
        await update.message.reply_text("Send: folder_id message")
        return

    if context.user_data.get("add_group"):
        identifiers = [x.strip() for x in text.split(",")]
        con = db()
        cur = con.cursor()
        cur.execute("SELECT id FROM folders WHERE user_id=? AND name='Default Folder'", (uid,))
        folder_id = cur.fetchone()[0]

        added = skipped = 0
        for g in identifiers:
            cur.execute(
                "INSERT OR IGNORE INTO groups(folder_id,identifier) VALUES (?,?)",
                (folder_id, g)
            )
            if cur.rowcount:
                added += 1
            else:
                skipped += 1

        con.commit()
        con.close()
        context.user_data.pop("add_group")

        await update.message.reply_text(
            f"✅ OPERATION COMPLETE\n\nAdded: {added}\nSkipped: {skipped}"
        )
        return

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

print("🤖 BOT RUNNING (FOLDERS MANAGER READY)")
app.run_polling(stop_signals=None)

while True:
    time.sleep(3600)