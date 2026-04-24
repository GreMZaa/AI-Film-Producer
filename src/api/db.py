import sqlite3
import os
from datetime import datetime
from src.api.config import settings

def get_db_connection():
    db_url = settings.database_url_resolved
    db_path = db_url.replace("sqlite:///", "")
    
    # Ensure directory exists (only if not in read-only environment or if it's /tmp)
    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.exists(db_dir):
        try:
            os.makedirs(db_dir, exist_ok=True)
        except Exception as e:
            # On Vercel, we might not be able to create directories outside /tmp
            if not os.environ.get("VERCEL"):
                raise e
            
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        is_premium BOOLEAN DEFAULT 0,
        subscription_type TEXT, -- 'bootleg', 'indie'
        priority_level INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_payment_at TIMESTAMP
    )
    ''')
    
    # Create transactions table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        amount FLOAT,
        currency TEXT,
        status TEXT,
        telegram_payment_charge_id TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (user_id)
    )
    ''')
    
    conn.commit()
    conn.close()

def get_user(user_id: int):
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE user_id = ?', (user_id,)).fetchone()
    conn.close()
    return user

def create_or_update_user(user_id: int, username: str = None):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO users (user_id, username)
    VALUES (?, ?)
    ON CONFLICT(user_id) DO UPDATE SET
    username = excluded.username
    ''', (user_id, username))
    conn.commit()
    conn.close()

def set_user_premium(user_id: int, sub_type: str, priority: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
    UPDATE users 
    SET is_premium = 1, 
        subscription_type = ?, 
        priority_level = ?,
        last_payment_at = ?
    WHERE user_id = ?
    ''', (sub_type, priority, datetime.now().isoformat(), user_id))
    conn.commit()
    conn.close()

def log_transaction(user_id: int, amount: float, currency: str, status: str, charge_id: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO transactions (user_id, amount, currency, status, telegram_payment_charge_id)
    VALUES (?, ?, ?, ?, ?)
    ''', (user_id, amount, currency, status, charge_id))
    conn.commit()
    conn.close()

# Initialize on import
init_db()
