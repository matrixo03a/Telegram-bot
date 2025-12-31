# modules/folders.py
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from database import db

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


async def folders_manager_view(update, context):
    uid = update.effective_user.id

    # ensure Default Folder
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

    keyboard = InlineKeyboardMarkup([
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
        reply_markup=keyboard,
        parse_mode="Markdown"
    )