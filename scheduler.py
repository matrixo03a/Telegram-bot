"""
Scheduler System
Auto posting engine with timezone support
FULL PRODUCTION VERSION
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
    def __init__(self):
        self.running = False
        self.last_run = {}

    async def start(self):
        self.running = True
        print("✅ Scheduler started")

        while self.running:
            await self.check()
            await asyncio.sleep(15)

    async def stop(self):
        self.running = False

    async def check(self):
        schedules = load_json(SCHEDULES_FILE, {})

        for user_id, tasks in schedules.items():
            uid = int(user_id)
            if uid not in user_sessions:
                continue

            settings = get_user_settings(uid, SETTINGS_FILE)
            tz = pytz.timezone(settings.get("timezone", "UTC"))
            now = datetime.now(tz)

            for name, data in tasks.items():
                key = f"{user_id}:{name}"
                if self.last_run.get(key) == now.strftime("%Y-%m-%d %H:%M"):
                    continue

                for t in data.get("parsed_times", []):
                    if t["type"] == "daily":
                        if now.hour == t["hour"] and now.minute == t["minute"]:
                            self.last_run[key] = now.strftime("%Y-%m-%d %H:%M")
                            asyncio.create_task(self.execute(uid, name, data))

    async def execute(self, user_id, task_name, data):
        client = user_sessions[user_id]
        post = data["post"]

        settings = get_user_settings(user_id, SETTINGS_FILE)
        delay = settings.get("delay", 0)
        mode = settings.get("forward_mode", "Copy")

        targets = []

        if data["target"] == "all":
            targets = await get_all_groups_from_folders(user_id, FOLDERS_FILE)
        elif data["target"] == "folder":
            targets = await get_groups_from_folder_names(
                user_id, data["folders"], FOLDERS_FILE
            )
        elif data["target"] == "groups":
            groups = await parse_groups_input(user_id, data["groups"])
            targets = [g["id"] for g in groups]

        if not targets:
            return

        success = 0
        for gid in targets:
            try:
                await forward_post_from_link(client, post, gid, mode)
                success += 1
                if delay:
                    await asyncio.sleep(delay)
            except:
                pass

        schedules = load_json(SCHEDULES_FILE, {})
        schedules[str(user_id)][task_name]["last_run"] = datetime.now().isoformat()
        save_json(SCHEDULES_FILE, schedules)

        await client.send_message(
            user_id,
            f"✅ **SCHEDULE COMPLETED**\n\n"
            f"📋 Task: `{task_name}`\n"
            f"📢 Groups: {len(targets)}\n"
            f"✅ Success: {success}"
        )


scheduler = None


def start_scheduler():
    global scheduler
    if not scheduler:
        scheduler = SchedulerManager()
        asyncio.create_task(scheduler.start())
    return scheduler