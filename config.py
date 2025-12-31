"""
Bot Configuration File
Contains all constants, credentials, and file paths
FULL VERSION – FIXED
"""

import os

# ============================================
# BOT CREDENTIALS (UPDATED)
# ============================================
BOT_TOKEN = "8456691972:AAGI_Y5pSZhZL5XXEssm2Yi4CI2pEGzBLEI"
OWNER_API_ID = 36363448
OWNER_API_HASH = "2920b3f570b33122db81fde2df17f6ce"

# ============================================
# BOT OWNERS / ADMINS
# ============================================
# ONLY THIS ID IS ADMIN / OWNER
OWNERS = {
    5510835149: "t.me/NEOECHOO"
}

# ============================================
# FILE PATHS
# ============================================
DATA_DIR = "bot_data"

USERS_FILE = f"{DATA_DIR}/users.json"
SESSIONS_FILE = f"{DATA_DIR}/sessions.json"
FOLDERS_FILE = f"{DATA_DIR}/folders.json"
SCHEDULES_FILE = f"{DATA_DIR}/schedules.json"
SETTINGS_FILE = f"{DATA_DIR}/settings.json"
ADMINS_FILE = f"{DATA_DIR}/admins.json"

# Create data directory if not exists
os.makedirs(DATA_DIR, exist_ok=True)

# ============================================
# RUNTIME STORAGE (DO NOT SAVE)
# ============================================
user_sessions = {}   # Active Telethon clients
temp_data = {}       # Temp flow storage
user_activity = {}   # AFK / last activity tracking

# ============================================
# BOT TEXT MESSAGES
# ============================================
UNAUTHORIZED_MSG = (
    "🚫 **ACCESS DENIED**\n\n"
    "You don't have permission to use this bot.\n\n"
    "💬 Contact admin for access."
)

SETUP_START_MSG = (
    "🔧 **ACCOUNT SETUP**\n\n"
    "📝 Please send your **API ID**\n\n"
    "ℹ️ Get it from:\n"
    "`https://my.telegram.org/apps`"
)

LOGIN_SUCCESS_MSG = (
    "✅ **SYSTEM CONNECTED**\n\n"
    "🎉 Your Telegram account is now linked.\n"
    "🚀 All features unlocked.\n\n"
    "Type /start to open menu."
)

# ============================================
# MAIN MENU KEYBOARD (GOD EYE REMOVED)
# ============================================
def get_main_keyboard():
    from telethon import Button

    return [
        [
            Button.text("📂 Folders", resize=True),
            Button.text("⏰ Scheduler", resize=True)
        ],
        [
            Button.text("📢 Broadcast", resize=True),
            Button.text("🌍 Timezone", resize=True)
        ],
        [
            Button.text("⚙️ Console", resize=True)
        ],
        [
            Button.text("💎 Plan", resize=True),
            Button.text("❓ Help", resize=True)
        ],
        [
            Button.text("💬 Support", resize=True)
        ]
    ]

# ============================================
# TIMEZONE OPTIONS
# ============================================
TIMEZONES = {
    "Asia/Dhaka": "🌏 Asia/Dhaka (GMT+6)",
    "Asia/Kolkata": "🌏 Asia/Kolkata (GMT+5:30)",
    "Asia/Dubai": "🌏 Asia/Dubai (GMT+4)",
    "Europe/London": "🌍 Europe/London (GMT+0)",
    "America/New_York": "🌎 New York (GMT-5)",
    "America/Los_Angeles": "🌎 Los Angeles (GMT-8)"
}

# ============================================
# DELAY OPTIONS (SECONDS)
# ============================================
DELAY_OPTIONS = [0, 1, 2, 3, 5, 10]

# ============================================
# SIMULATION TYPES
# ============================================
SIMULATION_TYPES = ["None", "Typing", "Recording"]

# ============================================
# FORWARD MODES
# ============================================
FORWARD_MODES = {
    "Copy": "📋 Copy (Hide Source)",
    "Forward": "↗️ Forward (Show Source)"
}

# ============================================
# FLOOD CONTROL
# ============================================
MAX_MESSAGES_PER_SECOND = 20
FLOOD_WAIT_TIME = 60

# ============================================
# AFK SETTINGS
# ============================================
AFK_REPLY_COOLDOWN = 300  # seconds