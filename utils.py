"""
Utility Functions
Helper functions for JSON operations, authorization, and common tasks
✅ God Eye functions removed
"""

import json
import os
import time
import re
from datetime import datetime
from config import USERS_FILE, OWNERS, user_sessions


def load_json(file_path, default=None):
    """
    Load JSON data from file
    
    Args:
        file_path: Path to JSON file
        default: Default value if file doesn't exist or is invalid
    
    Returns:
        Loaded data or default value
    """
    if default is None:
        default = {}
    
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"⚠️ Error loading {file_path}: {e}")
    
    return default


def save_json(file_path, data):
    """
    Save data to JSON file
    
    Args:
        file_path: Path to JSON file
        data: Data to save
    
    Returns:
        True if successful, False otherwise
    """
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"❌ Error saving {file_path}: {e}")
        return False


def is_authorized(user_id):
    """
    Check if user is authorized to use the bot
    
    Args:
        user_id: Telegram user ID
    
    Returns:
        True if authorized, False otherwise
    """
    users = load_json(USERS_FILE, {})
    return str(user_id) in users or user_id in OWNERS


def is_owner(user_id):
    """
    Check if user is an owner
    
    Args:
        user_id: Telegram user ID
    
    Returns:
        True if owner, False otherwise
    """
    return user_id in OWNERS


def get_user_plan(user_id):
    """
    Get user's remaining plan days
    
    Args:
        user_id: Telegram user ID
    
    Returns:
        Number of days remaining
    """
    users = load_json(USERS_FILE, {})
    user_info = users.get(str(user_id), {})
    return user_info.get('plan_days', 0)


def get_user_info(user_id):
    """
    Get complete user information
    
    Args:
        user_id: Telegram user ID
    
    Returns:
        Dictionary with user info
    """
    users = load_json(USERS_FILE, {})
    return users.get(str(user_id), {
        'plan_days': 0,
        'plan_type': 'Free',
        'started': 'N/A'
    })


def is_logged_in(user_id, sessions_file):
    """
    Check if user is logged in
    
    Args:
        user_id: Telegram user ID
        sessions_file: Path to sessions file
    
    Returns:
        True if logged in, False otherwise
    """
    sessions = load_json(sessions_file, {})
    return str(user_id) in sessions


def get_session_info(user_id, sessions_file):
    """
    Get user's session information
    
    Args:
        user_id: Telegram user ID
        sessions_file: Path to sessions file
    
    Returns:
        Session dictionary or None
    """
    sessions = load_json(sessions_file, {})
    return sessions.get(str(user_id))


def get_user_settings(user_id, settings_file):
    """
    Get user's settings
    
    Args:
        user_id: Telegram user ID
        settings_file: Path to settings file
    
    Returns:
        Dictionary with user settings
    """
    settings = load_json(settings_file, {})
    default_settings = {
        'timezone': 'UTC',
        'delay': 0,
        'simulation': 'None',
        'forward_mode': 'Copy'
    }
    
    user_settings = settings.get(str(user_id), {})
    for key, value in default_settings.items():
        if key not in user_settings:
            user_settings[key] = value
    
    return user_settings


def update_user_setting(user_id, settings_file, key, value):
    """
    Update a specific user setting
    
    Args:
        user_id: User ID
        settings_file: Path to settings file
        key: Setting key
        value: Setting value
    
    Returns:
        True if successful, False otherwise
    """
    settings = load_json(settings_file, {})
    
    if str(user_id) not in settings:
        settings[str(user_id)] = {}
    
    settings[str(user_id)][key] = value
    return save_json(settings_file, settings)


def format_time_ago(timestamp):
    """
    Format timestamp to human-readable "time ago" string
    
    Args:
        timestamp: Unix timestamp
    
    Returns:
        Formatted string (e.g., "5m ago", "2h ago")
    """
    diff = time.time() - timestamp
    
    if diff < 60:
        return f"{int(diff)}s ago"
    elif diff < 3600:
        return f"{int(diff/60)}m ago"
    elif diff < 86400:
        return f"{int(diff/3600)}h ago"
    else:
        return f"{int(diff/86400)}d ago"


def get_current_time():
    """
    Get current time formatted
    
    Returns:
        Current time string
    """
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def extract_chat_id(text):
    """
    Extract chat ID from text (handles links and IDs)
    Returns INTEGER for numeric IDs, STRING for usernames
    
    Args:
        text: Text containing chat ID or link
    
    Returns:
        Integer chat ID or string username
    """
    text = str(text).strip()
    
    # If already a negative number (channel/group ID)
    if text.startswith('-100'):
        return int(text)
    
    if text.startswith('-'):
        try:
            return int(text)
        except:
            pass
    
    # If it's a Telegram link
    if 't.me/' in text or 'telegram.me/' in text:
        # Remove protocol and domain
        text = text.replace('https://', '').replace('http://', '')
        text = text.replace('t.me/', '').replace('telegram.me/', '')
        
        # Handle private channel link: c/1234567890/123
        if text.startswith('c/'):
            parts = text.split('/')
            if len(parts) >= 2:
                channel_id = parts[1]
                return int(f"-100{channel_id}")
        
        # Handle regular link: username or username/123
        else:
            username = text.split('/')[0].split('?')[0]
            # If it's a username (starts with letter or @)
            if username and (username[0].isalpha() or username[0] == '@'):
                return username.replace('@', '')
            # If it's numeric, convert to channel ID
            elif username.isdigit():
                return int(f"-100{username}")
    
    # If it's a direct numeric ID
    try:
        chat_id_num = int(text)
        
        # If it's already negative, return as is
        if chat_id_num < 0:
            return chat_id_num
        
        # If it's a large positive number (likely a channel ID without -100)
        if len(str(chat_id_num)) >= 10:
            return int(f"-100{chat_id_num}")
        
        # Small positive number (user ID or bot ID)
        return chat_id_num
    except:
        pass
    
    # If nothing worked, return as username (STRING)
    return text.replace('@', '')


def is_valid_otp_format(otp):
    """
    Check if OTP is in correct format (1-2-3-4-5)
    
    Args:
        otp: OTP string
    
    Returns:
        True if valid format, False otherwise
    """
    return '-' in otp and len(otp.replace('-', '')) >= 5


def sanitize_otp(otp):
    """
    Remove dashes from OTP
    
    Args:
        otp: OTP string with dashes
    
    Returns:
        Clean OTP string
    """
    return otp.replace('-', '').strip()


def get_progress_bar(percentage):
    """
    Generate ASCII progress bar
    
    Args:
        percentage: Progress percentage (0-100)
    
    Returns:
        Progress bar string
    """
    filled = int(percentage / 10)
    empty = 10 - filled
    return f"`{'▰' * filled}{'▱' * empty}` {percentage}%"


def get_status_emoji(status):
    """
    Get emoji for status
    
    Args:
        status: Boolean status
    
    Returns:
        Status emoji
    """
    return "✅ ON" if status else "❌ OFF"


def get_connection_status(logged_in):
    """
    Get connection status text
    
    Args:
        logged_in: Boolean login status
    
    Returns:
        Status string with emoji
    """
    return "🟢 **CONNECTED**" if logged_in else "🔴 **NOT CONNECTED**"


async def forward_post_from_link(client, post_link, target_chat, mode='Copy'):
    """
    Forward post from Telegram link
    Handles INTEGER and STRING chat IDs properly
    
    Args:
        client: Telethon client
        post_link: Post link (t.me/channel/123)
        target_chat: Target chat ID (INTEGER or STRING username)
        mode: 'Copy' or 'Forward'
    
    Returns:
        True if successful, False otherwise
    """
    try:
        post_link = str(post_link).strip()
        
        # Remove protocol
        post_link = post_link.replace('https://', '').replace('http://', '')
        post_link = post_link.replace('t.me/', '').replace('telegram.me/', '')
        
        # Parse link formats
        if post_link.startswith('c/'):
            # Private channel: c/1234567890/123
            parts = post_link.split('/')
            if len(parts) < 3:
                print(f"❌ Invalid private channel link format: {post_link}")
                return False
            
            channel_id = int(f"-100{parts[1]}")
            message_id = int(parts[2])
        else:
            # Public channel: username/123 or username
            parts = post_link.split('/')
            channel_username = parts[0].split('?')[0]
            
            if len(parts) < 2:
                print(f"❌ No message ID in link: {post_link}")
                return False
            
            try:
                message_id = int(parts[1].split('?')[0])
            except:
                print(f"❌ Invalid message ID: {parts[1]}")
                return False
            
            # Try to get channel ID from username
            try:
                channel_entity = await client.get_entity(channel_username)
                channel_id = channel_entity.id
            except Exception as e:
                print(f"❌ Cannot find channel: {channel_username} - {e}")
                return False
        
        # Get the message
        try:
            message = await client.get_messages(channel_id, ids=message_id)
        except Exception as e:
            print(f"❌ Cannot get message {message_id} from {channel_id}: {e}")
            return False
        
        if not message:
            print(f"❌ Message not found: {message_id}")
            return False
        
        # Forward to target
        try:
            if mode == 'Copy':
                # Copy without attribution (send as new message)
                if message.media:
                    await client.send_file(
                        target_chat,
                        message.media,
                        caption=message.message if message.message else ""
                    )
                else:
                    await client.send_message(target_chat, message.message)
            else:
                # Forward with attribution
                await client.forward_messages(target_chat, message_id, channel_id)
            
            return True
            
        except Exception as e:
            print(f"❌ Cannot send to {target_chat}: {e}")
            return False
        
    except Exception as e:
        print(f"❌ Error forwarding post: {e}")
        return False


async def parse_groups_input(user_id, groups_input):
    """
    Parse comma-separated group links/IDs
    
    Args:
        user_id: User ID
        groups_input: Comma-separated group links/IDs
    
    Returns:
        List of group dictionaries with id and title
    """
    group_list = [g.strip() for g in groups_input.split(',') if g.strip()]
    result = []
    
    for group_input in group_list:
        if not group_input:
            continue
        
        group_id = extract_chat_id(group_input)
        
        if user_id in user_sessions:
            try:
                chat = await user_sessions[user_id].get_entity(group_id)
                result.append({
                    'id': chat.id,
                    'title': chat.title if hasattr(chat, 'title') else str(chat.id),
                    'link': group_input
                })
            except Exception as e:
                print(f"⚠️ Could not fetch group {group_id}: {e}")
                result.append({
                    'id': group_id,
                    'title': f"Group {group_id}",
                    'link': group_input
                })
        else:
            result.append({
                'id': group_id,
                'title': f"Group {group_id}",
                'link': group_input
            })
    
    return result


def parse_time_string(time_str):
    """
    Parse time string supporting 12-hour and 24-hour formats
    
    Args:
        time_str: Time string (11:00 PM, 23:00, or YYYY-MM-DD HH:MM)
    
    Returns:
        Dictionary with hour, minute, and optional date
    """
    time_str = time_str.strip()
    
    try:
        # Check if 12-hour format (AM/PM)
        if 'am' in time_str.lower() or 'pm' in time_str.lower():
            time_str_clean = time_str.replace(' ', '').upper()
            
            if 'PM' in time_str_clean:
                time_part = time_str_clean.replace('PM', '').strip()
                hour, minute = map(int, time_part.split(':'))
                if hour != 12:
                    hour += 12
            else:  # AM
                time_part = time_str_clean.replace('AM', '').strip()
                hour, minute = map(int, time_part.split(':'))
                if hour == 12:
                    hour = 0
            
            return {
                'type': 'daily',
                'hour': hour,
                'minute': minute
            }
        
        elif ' ' in time_str:
            # Has date: YYYY-MM-DD HH:MM
            dt = datetime.strptime(time_str, '%Y-%m-%d %H:%M')
            return {
                'type': 'date',
                'datetime': dt,
                'hour': dt.hour,
                'minute': dt.minute
            }
        else:
            # Only time: HH:MM (24-hour)
            hour, minute = map(int, time_str.split(':'))
            return {
                'type': 'daily',
                'hour': hour,
                'minute': minute
            }
    except Exception as e:
        print(f"⚠️ Error parsing time '{time_str}': {e}")
        return None


def convert_to_12hour(hour, minute):
    """
    Convert 24-hour time to 12-hour format
    
    Args:
        hour: Hour (0-23)
        minute: Minute (0-59)
    
    Returns:
        Formatted 12-hour time string
    """
    period = "AM" if hour < 12 else "PM"
    display_hour = hour % 12
    if display_hour == 0:
        display_hour = 12
    return f"{display_hour}:{minute:02d} {period}"


async def get_all_groups_from_folders(user_id, folders_file):
    """
    Get all groups from all folders for a user
    
    Args:
        user_id: User ID
        folders_file: Path to folders file
    
    Returns:
        List of all group IDs
    """
    folders = load_json(folders_file, {}).get(str(user_id), {})
    all_groups = []
    
    for folder_name, groups in folders.items():
        for group in groups:
            if group['id'] not in all_groups:
                all_groups.append(group['id'])
    
    return all_groups


async def get_groups_from_folder_names(user_id, folder_names, folders_file):
    """
    Get groups from specific folder names
    
    Args:
        user_id: User ID
        folder_names: Comma-separated folder names
        folders_file: Path to folders file
    
    Returns:
        List of group IDs
    """
    folders = load_json(folders_file, {}).get(str(user_id), {})
    folder_list = [f.strip() for f in folder_names.split(',') if f.strip()]
    
    selected_groups = []
    for folder_name in folder_list:
        if folder_name in folders:
            for group in folders[folder_name]:
                if group['id'] not in selected_groups:
                    selected_groups.append(group['id'])
    
    return selected_groups