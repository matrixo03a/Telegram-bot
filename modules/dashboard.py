from telegram import ReplyKeyboardMarkup

def dashboard():
    return ReplyKeyboardMarkup(
        [
            ["📢 Broadcast"],
            ["📁 Folders", "⏰ Scheduler"],
            ["⚙️ Settings", "🚪 Logout"],
        ],
        resize_keyboard=True
    )