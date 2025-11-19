import sqlite3
import os
from datetime import datetime
from contextlib import contextmanager

# Path to the SQLite database file
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "shared", "rulebot.db")

@contextmanager
def get_db_connection():
    """Get a connection to the SQLite database with proper cleanup."""
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row  # Enable dictionary-like access
        yield conn
    except sqlite3.Error as e:
        if conn:
            conn.rollback()
        raise e
    finally:
        if conn:
            conn.close()

def init_db():
    """Create tables if they don't exist."""
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()

            # Table for storing bots
            cur.execute("""
                CREATE TABLE IF NOT EXISTS bots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    slug TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    owner_id TEXT,
                    theme TEXT DEFAULT 'light',
                    avatar TEXT,
                    visibility TEXT DEFAULT 'unlisted',
                    fallback_message TEXT DEFAULT 'Sorry, I didn''t understand that. Can you rephrase your question?',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
            """)

            # Table for storing Q&A pairs for each bot
            cur.execute("""
                CREATE TABLE IF NOT EXISTS qna (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    bot_id INTEGER NOT NULL,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    keywords TEXT,
                    priority INTEGER DEFAULT 1,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (bot_id) REFERENCES bots (id) ON DELETE CASCADE
                );
            """)

            # Table for basic stats
            cur.execute("""
                CREATE TABLE IF NOT EXISTS bot_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    bot_id INTEGER NOT NULL,
                    date TEXT NOT NULL,
                    daily_sessions INTEGER DEFAULT 0,
                    message_count INTEGER DEFAULT 0,
                    FOREIGN KEY (bot_id) REFERENCES bots (id) ON DELETE CASCADE,
                    UNIQUE(bot_id, date)
                );
            """)

            # Table for users (light auth)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT UNIQUE NOT NULL,
                    magic_token TEXT,
                    token_expires_at TEXT,
                    created_at TEXT NOT NULL
                );
            """)

            conn.commit()
            print("Database initialized successfully.")
    except sqlite3.Error as e:
        print(f"Database initialization error: {e}")
        raise

def add_bot(slug, name, owner_id=None, theme='light', avatar=None, visibility='unlisted', fallback_message=None):
    """Add a new bot to the database."""
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            now = datetime.utcnow().isoformat()
            
            if fallback_message is None:
                fallback_message = "Sorry, I didn't understand that. Can you rephrase your question?"
            
            cur.execute("""
                INSERT INTO bots (slug, name, owner_id, theme, avatar, visibility, fallback_message, created_at, updated_at) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (slug, name, owner_id, theme, avatar, visibility, fallback_message, now, now))
            
            conn.commit()
            return cur.lastrowid
    except sqlite3.IntegrityError:
        print(f"Bot with slug '{slug}' already exists.")
        return None
    except sqlite3.Error as e:
        print(f"Error adding bot: {e}")
        return None

def add_qna(bot_id, question, answer, keywords=None, priority=1):
    """Add a Q&A pair to a specific bot."""
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            now = datetime.utcnow().isoformat()
            
            cur.execute("""
                INSERT INTO qna (bot_id, question, answer, keywords, priority, created_at) 
                VALUES (?, ?, ?, ?, ?, ?)
            """, (bot_id, question, answer, keywords, priority, now))
            
            conn.commit()
            return cur.lastrowid
    except sqlite3.Error as e:
        print(f"Error adding Q&A: {e}")
        return None

def fetch_qna(bot_id):
    """Fetch all Q&A pairs for a specific bot, ordered by priority (highest first)."""
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT id, question, answer, keywords, priority 
                FROM qna 
                WHERE bot_id = ? 
                ORDER BY priority DESC, id ASC
            """, (bot_id,))
            return cur.fetchall()
    except sqlite3.Error as e:
        print(f"Error fetching Q&A: {e}")
        return []

def fetch_bot_by_slug(slug):
    """Fetch bot information by its slug."""
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT id, slug, name, owner_id, theme, avatar, visibility, fallback_message, created_at, updated_at 
                FROM bots 
                WHERE slug = ?
            """, (slug,))
            return cur.fetchone()
    except sqlite3.Error as e:
        print(f"Error fetching bot: {e}")
        return None

def fetch_bot_by_id(bot_id):
    """Fetch bot information by its ID."""
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT id, slug, name, owner_id, theme, avatar, visibility, fallback_message, created_at, updated_at 
                FROM bots 
                WHERE id = ?
            """, (bot_id,))
            return cur.fetchone()
    except sqlite3.Error as e:
        print(f"Error fetching bot: {e}")
        return None

def update_bot(bot_id, **kwargs):
    """Update bot fields."""
    if not kwargs:
        return False
    
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            
            # Add updated_at timestamp
            kwargs['updated_at'] = datetime.utcnow().isoformat()
            
            # Build dynamic SQL
            set_clause = ", ".join([f"{key} = ?" for key in kwargs.keys()])
            values = list(kwargs.values()) + [bot_id]
            
            cur.execute(f"UPDATE bots SET {set_clause} WHERE id = ?", values)
            conn.commit()
            
            return cur.rowcount > 0
    except sqlite3.Error as e:
        print(f"Error updating bot: {e}")
        return False

def delete_qna(qna_id):
    """Delete a Q&A pair by ID."""
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM qna WHERE id = ?", (qna_id,))
            conn.commit()
            return cur.rowcount > 0
    except sqlite3.Error as e:
        print(f"Error deleting Q&A: {e}")
        return False

def increment_bot_stats(bot_id, sessions=0, messages=0):
    """Increment daily stats for a bot."""
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            today = datetime.utcnow().date().isoformat()
            
            cur.execute("""
                INSERT INTO bot_stats (bot_id, date, daily_sessions, message_count)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(bot_id, date) DO UPDATE SET
                    daily_sessions = daily_sessions + ?,
                    message_count = message_count + ?
            """, (bot_id, today, sessions, messages, sessions, messages))
            
            conn.commit()
            return True
    except sqlite3.Error as e:
        print(f"Error updating bot stats: {e}")
        return False

def create_user(email):
    """Create a new user."""
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            now = datetime.utcnow().isoformat()
            
            cur.execute("""
                INSERT INTO users (email, created_at) 
                VALUES (?, ?)
            """, (email, now))
            
            conn.commit()
            return cur.lastrowid
    except sqlite3.IntegrityError:
        print(f"User with email '{email}' already exists.")
        return None
    except sqlite3.Error as e:
        print(f"Error creating user: {e}")
        return None

def fetch_user_by_email(email):
    """Fetch user by email."""
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id, email, created_at FROM users WHERE email = ?", (email,))
            return cur.fetchone()
    except sqlite3.Error as e:
        print(f"Error fetching user: {e}")
        return None

if __name__ == "__main__":
    # Initialize database tables if not present
    init_db()
    
    # Test basic functionality
    print("Testing database operations...")
    
    # Test bot creation
    bot_id = add_bot("test-bot", "Test Bot", theme="dark")
    if bot_id:
        print(f"Created bot with ID: {bot_id}")
        
        # Test Q&A addition
        qna_id = add_qna(bot_id, "What is your name?", "I'm a test bot!", "name,bot", 5)
        if qna_id:
            print(f"Added Q&A with ID: {qna_id}")
        
        # Test fetching
        bot = fetch_bot_by_slug("test-bot")
        if bot:
            print(f"Found bot: {dict(bot)}")
        
        qnas = fetch_qna(bot_id)
        print(f"Found {len(qnas)} Q&A pairs")
        
    print("Database test completed.")