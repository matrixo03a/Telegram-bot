"""
Scheduler System - Auto Post at Scheduled Times
FIXED: Now properly checks time with timezone support
"""

import asyncio
from datetime import datetime, timedelta
import pytz
from config import SCHEDULES_FILE, FOLDERS_FILE, SETTINGS_FILE, user_sessions
from utils import (
    load_json, save_json, forward_post_from_link, 
    get_user_settings, get_groups_from_folder_names,
    get_all_groups_from_folders, parse_groups_input,
    convert_to_12hour
)


class SchedulerManager:
    """Manages scheduled posts"""
    
    def __init__(self, bot):
        self.bot = bot
        self.running = False
        self.last_minute_checked = {}  # Track last checked minute per schedule
    
    async def start(self):
        """Start the scheduler"""
        self.running = True
        print("✅ Scheduler started")
        
        while self.running:
            await self.check_schedules()
            await asyncio.sleep(10)  # Check every 10 seconds
    
    async def stop(self):
        """Stop the scheduler"""
        self.running = False
        print("ℹ️ Scheduler stopped")
    
    async def check_schedules(self):
        """Check all schedules and execute if time matches"""
        schedules = load_json(SCHEDULES_FILE, {})
        
        for user_id, user_schedules in schedules.items():
            user_id_int = int(user_id)
            
            # Get user timezone
            user_settings = get_user_settings(user_id_int, SETTINGS_FILE)
            user_tz_str = user_settings.get('timezone', 'UTC')
            
            try:
                user_tz = pytz.timezone(user_tz_str)
                current_time = datetime.now(user_tz)
            except:
                current_time = datetime.now()
            
            for task_name, schedule_data in user_schedules.items():
                schedule_key = f"{user_id}_{task_name}"
                current_minute = f"{current_time.hour:02d}:{current_time.minute:02d}"
                
                # Skip if we already checked this minute for this schedule
                if self.last_minute_checked.get(schedule_key) == current_minute:
                    continue
                
                if await self.should_execute(schedule_data, current_time):
                    # Mark this minute as checked
                    self.last_minute_checked[schedule_key] = current_minute
                    
                    # Execute in background
                    asyncio.create_task(
                        self.execute_schedule(user_id, task_name, schedule_data)
                    )
    
    async def should_execute(self, schedule_data, current_time):
        """Check if schedule should execute now"""
        parsed_times = schedule_data.get('parsed_times', [])
        
        for time_data in parsed_times:
            if time_data['type'] == 'daily':
                # Check if current time matches
                if (current_time.hour == time_data['hour'] and 
                    current_time.minute == time_data['minute']):
                    
                    # Additional check: prevent double execution
                    last_run = schedule_data.get('last_run')
                    if last_run:
                        try:
                            last_run_dt = datetime.fromisoformat(last_run)
                            time_diff = (current_time.replace(tzinfo=None) - last_run_dt).total_seconds()
                            if time_diff < 60:  # Less than 1 minute
                                return False
                        except:
                            pass
                    
                    return True
            
            elif time_data['type'] == 'date':
                # One-time execution at specific date/time
                target_dt = time_data['datetime']
                if (current_time.year == target_dt.year and
                    current_time.month == target_dt.month and
                    current_time.day == target_dt.day and
                    current_time.hour == target_dt.hour and
                    current_time.minute == target_dt.minute):
                    
                    # Check if already executed
                    last_run = schedule_data.get('last_run')
                    if last_run:
                        return False
                    
                    return True
        
        return False
    
    async def execute_schedule(self, user_id, task_name, schedule_data):
        """Execute a scheduled post"""
        print(f"🚀 Executing schedule: {task_name} for user {user_id}")
        
        user_id_int = int(user_id)
        
        # Check if user is logged in
        if user_id_int not in user_sessions:
            print(f"⚠️ User {user_id} not logged in")
            return
        
        client = user_sessions[user_id_int]
        
        post_link = schedule_data.get('post', '')
        target_type = schedule_data.get('target', 'all')
        
        # Get user settings
        user_settings = get_user_settings(user_id_int, SETTINGS_FILE)
        delay = user_settings.get('delay', 0)
        mode = user_settings.get('forward_mode', 'Copy')
        
        # Determine target groups
        target_groups = []
        
        if target_type == 'all':
            target_groups = await get_all_groups_from_folders(user_id_int, FOLDERS_FILE)
        elif target_type == 'folder':
            folder_names = schedule_data.get('folders', '')
            target_groups = await get_groups_from_folder_names(user_id_int, folder_names, FOLDERS_FILE)
        elif target_type == 'groups':
            groups_input = schedule_data.get('groups', '')
            groups_data = await parse_groups_input(user_id_int, groups_input)
            target_groups = [g['id'] for g in groups_data]
        
        if not target_groups:
            print(f"⚠️ No target groups for schedule {task_name}")
            try:
                await client.send_message(
                    user_id_int,
                    f"⚠️ **SCHEDULE FAILED**\n\n"
                    f"📋 Task: `{task_name}`\n"
                    f"❌ Error: No target groups found\n\n"
                    f"Please check your schedule settings."
                )
            except:
                pass
            return
        
        success_count = 0
        failed_count = 0
        
        # Send initial notification
        try:
            notification_msg = await client.send_message(
                user_id_int,
                f"🚀 **SCHEDULE EXECUTING**\n\n"
                f"📋 Task: `{task_name}`\n"
                f"📢 Target Groups: {len(target_groups)}\n\n"
                f"⏳ Starting broadcast..."
            )
        except:
            notification_msg = None
        
        # Execute forwarding
        for idx, group_id in enumerate(target_groups):
            try:
                success = await forward_post_from_link(client, post_link, group_id, mode)
                
                if success:
                    success_count += 1
                else:
                    failed_count += 1
                
                # Update progress every 5 groups or at end
                if notification_msg and ((idx + 1) % 5 == 0 or (idx + 1) == len(target_groups)):
                    progress = int(((idx + 1) / len(target_groups)) * 100)
                    try:
                        await notification_msg.edit(
                            f"🚀 **SCHEDULE EXECUTING**\n\n"
                            f"📋 Task: `{task_name}`\n"
                            f"📊 Progress: {idx + 1}/{len(target_groups)}\n"
                            f"✅ Success: {success_count}\n"
                            f"❌ Failed: {failed_count}\n\n"
                            f"`{'▰' * (progress // 10)}{'▱' * (10 - progress // 10)}` {progress}%"
                        )
                    except:
                        pass
                
                # Apply delay
                if delay > 0 and (idx + 1) < len(target_groups):
                    await asyncio.sleep(delay)
                    
            except Exception as e:
                failed_count += 1
                print(f"❌ Failed to post to {group_id}: {e}")
        
        # Update schedule data
        schedules = load_json(SCHEDULES_FILE, {})
        if user_id in schedules and task_name in schedules[user_id]:
            schedules[user_id][task_name]['last_run'] = datetime.now().isoformat()
            
            next_run = self.calculate_next_run(schedule_data, user_settings.get('timezone', 'UTC'))
            schedules[user_id][task_name]['next_run'] = next_run
            
            save_json(SCHEDULES_FILE, schedules)
        
        # Send professional completion notification
        try:
            current_time_str = convert_to_12hour(datetime.now().hour, datetime.now().minute)
            next_run_info = next_run if next_run != "Not scheduled" else "N/A"
            success_rate = int((success_count/len(target_groups))*100) if len(target_groups) > 0 else 0
            
            # Choose emoji based on success rate
            if success_rate == 100:
                status_emoji = "🎉"
                status_text = "PERFECT SUCCESS"
            elif success_rate >= 80:
                status_emoji = "✅"
                status_text = "COMPLETED"
            elif success_rate >= 50:
                status_emoji = "⚠️"
                status_text = "PARTIALLY COMPLETED"
            else:
                status_emoji = "❌"
                status_text = "COMPLETED WITH ERRORS"
            
            completion_msg = (
                f"╔═══════════════════════════╗\n"
                f"║  {status_emoji} AUTO POST {status_text}  ║\n"
                f"╚═══════════════════════════╝\n\n"
                
                f"📋 **Schedule Details:**\n"
                f"├─ Task Name: `{task_name}`\n"
                f"├─ Target: {target_type.title()}\n"
                f"├─ Executed At: `{current_time_str}`\n"
                f"└─ Total Groups: {len(target_groups)}\n\n"
                
                f"📊 **Execution Report:**\n"
                f"┌─────────────────────┐\n"
                f"│ ✅ Successful: {success_count:>4}  │\n"
                f"│ ❌ Failed:     {failed_count:>4}  │\n"
                f"│ 📈 Success Rate: {success_rate:>2}% │\n"
                f"└─────────────────────┘\n\n"
                
                f"⏰ **Next Scheduled Run:**\n"
                f"`{next_run_info}`\n\n"
                
                f"──────────────────────────\n"
                f"⚡ **POWERED BY SHADOW FLEX**\n"
                f"🤖 Automated Posting System"
            )
            
            if notification_msg:
                await notification_msg.edit(completion_msg)
            else:
                # If notification_msg is None, send new message
                await client.send_message(user_id_int, completion_msg)
                
        except Exception as e:
            print(f"❌ Failed to send notification: {e}")
        
        print(f"✅ Schedule {task_name} completed: {success_count}/{len(target_groups)} successful")
    
    def calculate_next_run(self, schedule_data, timezone_str='UTC'):
        """Calculate next run time with timezone support"""
        parsed_times = schedule_data.get('parsed_times', [])
        
        try:
            user_tz = pytz.timezone(timezone_str)
            current_time = datetime.now(user_tz)
        except:
            current_time = datetime.now()
        
        next_times = []
        
        for time_data in parsed_times:
            if time_data['type'] == 'daily':
                # Calculate next occurrence
                next_time = current_time.replace(
                    hour=time_data['hour'],
                    minute=time_data['minute'],
                    second=0,
                    microsecond=0
                )
                
                # If time already passed today, schedule for tomorrow
                if next_time <= current_time:
                    next_time += timedelta(days=1)
                
                next_times.append(next_time)
        
        if next_times:
            next_run = min(next_times)
            
            # Format output
            if next_run.date() == current_time.date():
                return f"Today at {convert_to_12hour(next_run.hour, next_run.minute)}"
            elif next_run.date() == (current_time + timedelta(days=1)).date():
                return f"Tomorrow at {convert_to_12hour(next_run.hour, next_run.minute)}"
            else:
                return f"{next_run.strftime('%b %d')} at {convert_to_12hour(next_run.hour, next_run.minute)}"
        
        return "Not scheduled"


scheduler = None


def start_scheduler(bot):
    """Start the scheduler system"""
    global scheduler
    
    if scheduler is None:
        scheduler = SchedulerManager(bot)
        asyncio.create_task(scheduler.start())
        print("✅ Scheduler system initialized")
    
    return scheduler


def stop_scheduler():
    """Stop the scheduler system"""
    global scheduler
    
    if scheduler:
        asyncio.create_task(scheduler.stop())
        scheduler = None