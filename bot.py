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
    con=db();cur=con.cursor()
    cur.execute("SELECT expires FROM users WHERE id=?", (uid,))
    r=cur.fetchone()
    con.close()
    return r and datetime.fromisoformat(r[0]) > datetime.utcnow()

def has_session(uid):
    con=db();cur=con.cursor()
    cur.execute("SELECT session FROM tg_sessions WHERE user_id=?", (uid,))
    r=cur.fetchone()
    con.close()
    return bool(r)

# ---------------- DASHBOARD ----------------
def dashboard():
    return ReplyKeyboardMarkup(
        [
            ["📁 Folders", "⏰ Scheduler"],
            ["📢 Broadcast", "⚙️ Settings"],
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

# ---------------- FOLDER MENU ----------------
async def folders_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Create Folder", callback_data="folder_create")],
        [InlineKeyboardButton("➕ Add Group", callback_data="group_add")],
        [InlineKeyboardButton("🗑️ Delete Folder", callback_data="folder_delete")],
        [InlineKeyboardButton("🔙 Back", callback_data="back_dashboard")]
    ])
    await update.message.reply_text("📁 Folder Manager", reply_markup=kb)

# ---------------- INLINE HANDLER ----------------
async def inline_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    data = q.data

    con=db();cur=con.cursor()

    # ADMIN PLAN
    if is_admin(uid) and data in ["trial","monthly","yearly"]:
        context.user_data["admin_plan"]=data
        await q.message.reply_text("Send User ID:")
        return

    # FOLDER CREATE
    if data=="folder_create":
        context.user_data["folder_step"]="name"
        await q.message.reply_text("Send folder name:")
        return

    # LIST FOLDERS FOR ADD GROUP
    if data=="group_add":
        cur.execute("SELECT id,name FROM folders WHERE user_id=?", (uid,))
        rows=cur.fetchall()
        if not rows:
            await q.message.reply_text("❌ No folder found.")
            return
        kb=[[InlineKeyboardButton(n,callback_data=f"addgrp_{i}")] for i,n in rows]
        await q.message.reply_text("Select folder:",reply_markup=InlineKeyboardMarkup(kb))
        return

    if data.startswith("addgrp_"):
        context.user_data["add_group"]=int(data.split("_")[1])
        await q.message.reply_text("Send Group ID / Username / Link:")
        return

    # DELETE FOLDER
    if data=="folder_delete":
        cur.execute("SELECT id,name FROM folders WHERE user_id=?", (uid,))
        rows=cur.fetchall()
        if not rows:
            await q.message.reply_text("❌ No folder found.")
            return
        kb=[[InlineKeyboardButton(n,callback_data=f"delf_{i}")] for i,n in rows]
        await q.message.reply_text("Select folder to delete:",reply_markup=InlineKeyboardMarkup(kb))
        return

    if data.startswith("delf_"):
        context.user_data["confirm_del"]=int(data.split("_")[1])
        kb=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Yes",callback_data="del_yes")],
            [InlineKeyboardButton("❌ Cancel",callback_data="del_no")]
        ])
        await q.message.reply_text("Confirm delete?",reply_markup=kb)
        return

    if data=="del_yes":
        fid=context.user_data.pop("confirm_del")
        cur.execute("DELETE FROM folders WHERE id=?", (fid,))
        cur.execute("DELETE FROM groups WHERE folder_id=?", (fid,))
        con.commit()
        await q.message.reply_text("✅ Folder deleted")
        return

    if data=="del_no":
        context.user_data.pop("confirm_del",None)
        await q.message.reply_text("❌ Cancelled")
        return

    if data=="back_dashboard":
        await q.message.reply_text("🏠 Dashboard",reply_markup=dashboard())

    con.close()

# ---------------- TEXT ROUTER ----------------
async def router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid=update.effective_user.id
    text=update.message.text

    # ADMIN ASSIGN
    if is_admin(uid) and "admin_plan" in context.user_data:
        plan=context.user_data.pop("admin_plan")
        days=3 if plan=="trial" else 30 if plan=="monthly" else 365
        exp=datetime.utcnow()+timedelta(days=days)
        con=db();cur=con.cursor()
        cur.execute("INSERT OR REPLACE INTO users VALUES (?,?,?)",(int(text),plan,exp.isoformat()))
        con.commit();con.close()
        await update.message.reply_text("✅ Access Granted")
        await context.bot.send_message(int(text),"🎉 Access activated\nSend /start")
        return

    # LOGIN FLOW
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
        await update.message.reply_text("Enter OTP:")
        return
    if step=="otp":
        client=tg_clients[uid]
        await client.sign_in(phone=context.user_data["phone"],code=text.replace(" ",""))
        session=client.session.save()
        con=db();cur=con.cursor()
        cur.execute("INSERT OR REPLACE INTO tg_sessions VALUES (?,?)",(uid,session))
        con.commit();con.close()
        context.user_data.clear()
        await update.message.reply_text("✅ Login Successful\nSend /start")
        return

    # CREATE FOLDER
    if context.user_data.get("folder_step"):
        con=db();cur=con.cursor()
        cur.execute("INSERT INTO folders(user_id,name) VALUES (?,?)",(uid,text))
        con.commit();con.close()
        context.user_data.pop("folder_step")
        await update.message.reply_text("✅ Folder Created")
        return

    # ADD GROUP
    if context.user_data.get("add_group"):
        fid=context.user_data.pop("add_group")
        con=db();cur=con.cursor()
        cur.execute("INSERT INTO groups(folder_id,identifier) VALUES (?,?)",(fid,text))
        con.commit();con.close()
        await update.message.reply_text("✅ Group Added")
        return

    # DASHBOARD BUTTONS
    if text=="📁 Folders":
        await folders_menu(update,context)

# ---------------- INIT ----------------
init_db()

request=HTTPXRequest(connect_timeout=30,read_timeout=30,write_timeout=30,pool_timeout=30)
app=ApplicationBuilder().token(TOKEN).request(request).build()

app.add_handler(CommandHandler("start",start))
app.add_handler(CallbackQueryHandler(inline_handler))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,router))

print("🤖 BOT RUNNING (FULL FOLDER SYSTEM)")
app.run_polling(stop_signals=None)

while True:
    time.sleep(3600)