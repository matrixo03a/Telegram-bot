"""
Bot Configuration File
Contains all constants, credentials, and file paths
"""

import os

# ============================================
# BOT CREDENTIALS
# ============================================
# IMPORTANT: Replace these with YOUR OWN credentials from https://my.telegram.org/apps
BOT_TOKEN = "8580899649:AAHiMXu2HXwI4kq3FM0_ceYKm1Be_hH7pRE"  # Get from @BotFather
OWNER_API_ID = 36363448  # YOUR API ID from my.telegram.org
OWNER_API_HASH = "2920b3f570b33122db81fde2df17f6ce"  # YOUR API HASH from my.telegram.org

# ============================================
# BOT OWNERS
# ============================================
OWNERS = {
    2024653852: "t.me/SH4DOW_FLEX",
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

# Create data directory if it doesn't exist
os.makedirs(DATA_DIR, exist_ok=True)

# ============================================
# GLOBAL STORAGE DICTIONARIES
# ============================================
# Runtime storage for active user sessions
user_sessions = {}  # Stores active Telegram client sessions
user_data = {}      # Stores user-specific runtime data
temp_data = {}      # Stores temporary data during setup flows

# NEW: Track user activity for AFK
user_activity = {}  # Stores last activity timestamps

# ============================================
# BOT MESSAGES
# ============================================
UNAUTHORIZED_MSG = (
    "🚫 **ACCESS DENIED**\n\n"
    "❌ You don't have permission to use this bot.\n\n"
    "💎 To get **Free Trial** or **Premium Access**, contact owners below:"
)

SETUP_START_MSG = (
    "🔧 **ACCOUNT SETUP**\n\n"
    "📝 Please provide your **API ID**\n\n"
    "ℹ️ Get it from: `my.telegram.org/apps`\n\n"
    "💡 Send your API ID:"
)

LOGIN_SUCCESS_MSG = (
    "✅ **SYSTEM CONNECTED**\n\n"
    "🎉 Your account has been linked successfully!\n"
    "🚀 You can now use all features.\n\n"
    "Type /start to access the main menu."
)

# ============================================
# KEYBOARD LAYOUTS
# ============================================
def get_main_keyboard():
    """Returns the main menu reply keyboard buttons"""
    from telethon import Button
    return [
        [Button.text("📁 Folders", resize=True), Button.text("⏰ Scheduler", resize=True)],
        [Button.text("📢 Broadcast", resize=True), Button.text("🌍 Timezone", resize=True)],
        [Button.text("👁️ God Eye", resize=True), Button.text("⚙️ Console", resize=True)],
        [Button.text("💎 Plan", resize=True), Button.text("❓ Help", resize=True)],
        [Button.text("💬 Support", resize=True)]
    ]

# ============================================
# TIMEZONE OPTIONS
# ============================================
TIMEZONES = {
    "Asia/Dhaka": "🌏 Asia/Dhaka (GMT+6)",
    "America/New_York": "🌎 America/New_York (GMT-5)",
    "Europe/London": "🌍 Europe/London (GMT+0)",
    "Asia/Kolkata": "🌏 Asia/Kolkata (GMT+5:30)",
    "Asia/Dubai": "🌏 Asia/Dubai (GMT+4)",
    "America/Los_Angeles": "🌎 America/Los_Angeles (GMT-8)"
}

# ============================================
# DELAY OPTIONS (in seconds)
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
    "Copy": "📋 Copy Mode (Hide Source)",
    "Forward": "↗️ Forward Mode (Show Source)"
}

# ============================================
# FLOOD CONTROL SETTINGS
# ============================================
# NEW: Prevent Telegram flood bans
MAX_MESSAGES_PER_SECOND = 20
FLOOD_WAIT_TIME = 60  # seconds to wait if flood detected

# ============================================
# AFK SETTINGS
# ============================================
# NEW: AFK auto-reply cooldown (seconds)
AFK_REPLY_COOLDOWN = 300  # 5 minutes