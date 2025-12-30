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
        identifier TEXT UNIQUE
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
            "🚫 ACCESS DENIED\n\nPlease contact admin."
        )
        return

    if not has_session(uid):
        context.user_data.clear()
        context.user_data["login_step"] = "api_id"
        await update.message.reply_text("🔐 Enter API ID:")
        return

    await update.message.reply_text(
        "👋 Welcome!\nChoose an option below 👇",
        reply_markup=dashboard()
    )


# ---------------- FOLDERS UI ----------------
async def folders_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    con = db()
    cur = con.cursor()

    # Ensure default folder
    cur.execute(
        "SELECT id FROM folders WHERE user_id=? AND name='Default Folder'", (uid,)
    )
    row = cur.fetchone()
    if not row:
        cur.execute(
            "INSERT INTO folders(user_id,name) VALUES (?,?)",
            (uid, "Default Folder")
        )
        con.commit()

    con.close()

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Add Groups", callback_data="add_groups")],
        [InlineKeyboardButton("🗂 View Groups", callback_data="view_groups")],
        [InlineKeyboardButton("⬅️ Back", callback_data="back_dashboard")]
    ])

    await update.message.reply_text(
        "📁 *Default Folder*\n\n"
        "➕ ADD GROUPS TO Default Folder\n\n"
        "Send group details (one or more, separated by comma):\n\n"
        "• Username: @groupname\n"
        "• Group ID: -1001234567890\n"
        "• Multiple: -100111, @group2, 123456\n\n"
        "Type /cancel to abort",
        reply_markup=kb,
        parse_mode="Markdown"
    )


# ---------------- INLINE HANDLER ----------------
async def inline_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    data = q.data

    if data == "back_dashboard":
        await q.message.reply_text(
            "👋 Welcome back!",
            reply_markup=dashboard()
        )
        return

    if data == "add_groups":
        context.user_data["add_groups"] = True
        await q.message.reply_text("📨 Send group IDs / usernames:")
        return

    if data == "view_groups":
        con = db()
        cur = con.cursor()
        cur.execute("""
            SELECT g.identifier FROM groups g
            JOIN folders f ON f.id = g.folder_id
            WHERE f.user_id=? AND f.name='Default Folder'
        """, (uid,))
        rows = cur.fetchall()
        con.close()

        if not rows:
            await q.message.reply_text("📭 No groups added yet.")
        else:
            txt = "📋 *Groups in Default Folder:*\n\n"
            txt += "\n".join(f"• `{r[0]}`" for r in rows)
            await q.message.reply_text(txt, parse_mode="Markdown")


# ---------------- TEXT ROUTER ----------------
async def router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = update.message.text.strip()

    # BLOCK before login
    if not has_session(uid):
        if not context.user_data.get("login_step"):
            await update.message.reply_text("🔐 Send /start to login")
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
        cur.execute(
            "INSERT OR REPLACE INTO tg_sessions VALUES (?,?)",
            (uid, session)
        )
        con.commit()
        con.close()

        context.user_data.clear()
        await update.message.reply_text("✅ Login successful\nSend /start")
        return

    # ADD GROUPS FLOW
    if context.user_data.get("add_groups"):
        if text.lower() == "/cancel":
            context.user_data.pop("add_groups")
            await update.message.reply_text("❌ Cancelled")
            return

        identifiers = [x.strip() for x in text.split(",")]
        added = skipped = failed = 0

        con = db()
        cur = con.cursor()
        cur.execute(
            "SELECT id FROM folders WHERE user_id=? AND name='Default Folder'", (uid,)
        )
        folder_id = cur.fetchone()[0]

        for g in identifiers:
            try:
                cur.execute(
                    "INSERT OR IGNORE INTO groups(folder_id,identifier) VALUES (?,?)",
                    (folder_id, g)
                )
                if cur.rowcount:
                    added += 1
                else:
                    skipped += 1
            except:
                failed += 1

        con.commit()
        con.close()
        context.user_data.pop("add_groups")

        await update.message.reply_text(
            "✅ *OPERATION COMPLETE*\n\n"
            f"✅ Added: {added}\n"
            f"⏩ Skipped (existing): {skipped}\n"
            f"❌ Failed: {failed}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Back", callback_data="back_dashboard")]
            ])
        )
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

print("🤖 BOT RUNNING (Volt-style Folders)")
app.run_polling(stop_signals=None)

while True:
    time.sleep(3600)