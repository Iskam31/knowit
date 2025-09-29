import psycopg2
import psycopg2.extras
from datetime import datetime, timedelta
from typing import Optional
from .config import DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT

def _get_conn():
    return psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )

def init_db():
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        tg_id BIGINT PRIMARY KEY,
        is_active BOOLEAN DEFAULT FALSE,
        requests_left INT DEFAULT 0,
        expire_ts BIGINT DEFAULT NULL,
        subscription_type TEXT DEFAULT NULL
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS payments (
        id SERIAL PRIMARY KEY,
        tg_id BIGINT,
        provider TEXT,
        amount INT,
        currency TEXT,
        status TEXT DEFAULT 'pending',
        payload TEXT,
        created_ts BIGINT DEFAULT EXTRACT(EPOCH FROM NOW())
    )
    """)
    conn.commit()
    conn.close()

def get_user(tg_id: int):
    conn = _get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("SELECT * FROM users WHERE tg_id = %s", (tg_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None

def ensure_user(tg_id: int):
    if get_user(tg_id) is None:
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute("INSERT INTO users (tg_id, is_active, requests