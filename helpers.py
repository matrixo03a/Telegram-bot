from datetime import datetime
from database import db
from config import ADMIN_ID

def is_admin(uid):
    return uid == ADMIN_ID

def has_active_plan(uid):
    con = db()
    cur = con.cursor()
    cur.execute("SELECT expires FROM users WHERE id=?", (uid,))
    row = cur.fetchone()
    con.close()
    return row and datetime.fromisoformat(row[0]) > datetime.utcnow()

def has_session(uid):
    con = db()
    cur = con.cursor()
    cur.execute("SELECT session FROM tg_sessions WHERE user_id=?", (uid,))
    row = cur.fetchone()
    con.close()
    return bool(row)