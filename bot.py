from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from telegram.request import HTTPXRequest
from datetime import datetime, timedelta
import sqlite3, asyncio

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
        user_id INTEGER,
        folder_id INTEGER,
        chat_id TEXT
    );
    CREATE TABLE IF NOT EXISTS schedules(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        folder_id INTEGER,
        text TEXT,
        time TEXT,
        active INTEGER
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
    return r and datetime.fromisoformat(r[0])>datetime.utcnow()

def has_session(uid):
    con=db();cur=con.cursor()
    cur.execute("SELECT session FROM tg_sessions WHERE user_id=?", (uid,))
    r=cur.fetchone();con.close()
    return bool(r)

def dashboard():
    return ReplyKeyboardMarkup(
        [
            ["Folders","Groups"],
            ["Forward","Schedule"],
            ["Broadcast"],
            ["Status","Logout"]
        ],
        resize_keyboard=True
    )

tg_clients={}

# ---------------- START ----------------
async def start(update:Update,context:ContextTypes.DEFAULT_TYPE):
    uid=update.effective_user.id

    if is_admin(uid):
        kb=InlineKeyboardMarkup([
            [InlineKeyboardButton("🎁 Trial",callback_data="trial")],
            [InlineKeyboardButton("📅 Monthly",callback_data="monthly")],
            [InlineKeyboardButton("📆 Yearly",callback_data="yearly")]
        ])
        await update.message.reply_text("👑 Admin Panel",reply_markup=kb)
        return

    if not has_active_plan(uid):
        await update.message.reply_text("⛔ No active plan.")
        return

    if not has_session(uid):
        context.user_data.clear()
        context.user_data["login"]="api_id"
        await update.message.reply_text("🔐 Enter API ID:")
        return

    await update.message.reply_text("🏠 Dashboard",reply_markup=dashboard())

# ---------------- INLINE ----------------
async def inline_handler(update:Update,context:ContextTypes.DEFAULT_TYPE):
    q=update.callback_query;await q.answer()

    if is_admin(q.from_user.id):
        context.user_data["admin_plan"]=q.data
        await q.message.reply_text("Send User ID:")

# ---------------- TEXT ROUTER ----------------
async def router(update:Update,context:ContextTypes.DEFAULT_TYPE):
    uid=update.effective_user.id
    text=update.message.text

    # -------- ADMIN --------
    if is_admin(uid) and "admin_plan" in context.user_data:
        plan=context.user_data.pop("admin_plan")
        days=3 if plan=="trial" else 30 if plan=="monthly" else 365
        name="Trial" if days==3 else "Monthly" if days==30 else "Yearly"
        exp=datetime.utcnow()+timedelta(days=days)

        con=db();cur=con.cursor()
        cur.execute("INSERT OR REPLACE INTO users VALUES (?,?,?)",(int(text),name,exp.isoformat()))
        con.commit();con.close()

        await update.message.reply_text("✅ Access given")
        await context.bot.send_message(int(text),f"🎉 Access {name} ({days} days)\nSend /start")
        return

    # -------- LOGIN FLOW --------
    step=context.user_data.get("login")
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
        client=TelegramClient(StringSession(),context.user_data["api_id"],context.user_data["api_hash"])
        await client.connect()
        await client.send_code_request(text)
        tg_clients[uid]=client
        context.user_data["phone"]=text
        context.user_data["login"]="otp"
        await update.message.reply_text("Enter OTP (123456):")
        return
    if step=="otp":
        client=tg_clients[uid]
        await client.sign_in(phone=context.user_data["phone"],code=text.replace(" ",""))
        session=client.session.save()
        con=db();cur=con.cursor()
        cur.execute("INSERT OR REPLACE INTO tg_sessions VALUES (?,?)",(uid,session))
        con.commit();con.close()
        context.user_data.clear()
        await update.message.reply_text("✅ Login success\nSend /start")
        return

    # -------- FOLDERS --------
    if text=="Folders":
        await update.message.reply_text("Send folder name to create:")
        context.user_data["mk_folder"]=True
        return
    if context.user_data.get("mk_folder"):
        con=db();cur=con.cursor()
        cur.execute("INSERT INTO folders(user_id,name) VALUES (?,?)",(uid,text))
        con.commit();con.close()
        context.user_data.pop("mk_folder")
        await update.message.reply_text("📁 Folder created")
        return

    # -------- GROUPS --------
    if text=="Groups":
        await update.message.reply_text("Send: folder_id chat_id")
        context.user_data["add_group"]=True
        return
    if context.user_data.get("add_group"):
        f,c=text.split()
        con=db();cur=con.cursor()
        cur.execute("INSERT INTO groups(user_id,folder_id,chat_id) VALUES (?,?,?)",(uid,f,c))
        con.commit();con.close()
        context.user_data.pop("add_group")
        await update.message.reply_text("👥 Group added")
        return

    # -------- FORWARD --------
    if text=="Forward":
        await update.message.reply_text("Send: folder_id message")
        context.user_data["forward"]=True
        return
    if context.user_data.get("forward"):
        fid,msg=text.split(" ",1)
        con=db();cur=con.cursor()
        cur.execute("SELECT chat_id FROM groups WHERE user_id=? AND folder_id=?",(uid,fid))
        chats=cur.fetchall();con.close()
        for c in chats:
            await context.bot.send_message(c[0],msg)
        context.user_data.pop("forward")
        await update.message.reply_text("✅ Forwarded")
        return

    # -------- STATUS --------
    if text=="Status":
        con=db();cur=con.cursor()
        cur.execute("SELECT plan,expires FROM users WHERE id=?",(uid,))
        r=cur.fetchone();con.close()
        d=(datetime.fromisoformat(r[1])-datetime.utcnow()).days
        await update.message.reply_text(f"📦 {r[0]}\n📆 {d} days left")
        return

    if text=="Logout":
        await update.message.reply_text("👋 Logged out")

# ---------------- INIT ----------------
init_db()
request=HTTPXRequest(connect_timeout=30,read_timeout=30,write_timeout=30,pool_timeout=30)
app=ApplicationBuilder().token(TOKEN).request(request).build()

app.add_handler(CommandHandler("start",start))
app.add_handler(CallbackQueryHandler(inline_handler))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,router))

print("🤖 ALL-IN-ONE BOT RUNNING…")
app.run_polling()