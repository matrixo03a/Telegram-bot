from telethon import TelegramClient
from telethon.sessions import StringSession
from database import db

tg_clients = {}

async def login_flow(update, context):
    uid = update.effective_user.id
    text = update.message.text.strip()
    step = context.user_data.get("login_step")

    if step == "api_id":
        context.user_data["api_id"] = int(text)
        context.user_data["login_step"] = "api_hash"
        await update.message.reply_text("Enter API HASH:")
        return True

    if step == "api_hash":
        context.user_data["api_hash"] = text
        context.user_data["login_step"] = "phone"
        await update.message.reply_text("Enter phone number:")
        return True

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
        return True

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
        return True

    return False