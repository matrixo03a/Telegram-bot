import sqlite3
from config import DB_PATH

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