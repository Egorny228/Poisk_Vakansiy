import sqlite3
from datetime import datetime

DB_NAME = "vacancies.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    
    # Таблица пользователей
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            query TEXT NOT NULL,
            city TEXT NOT NULL,
            salary_from INTEGER DEFAULT 0,
            last_check TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Таблица отправленных вакансий (чтобы не дублировать)
    cur.execute('''
        CREATE TABLE IF NOT EXISTS sent_vacancies (
            vacancy_id TEXT PRIMARY KEY,
            user_id INTEGER,
            sent_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

def add_user(user_id, query, city, salary_from=0):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('''
        INSERT OR REPLACE INTO users (user_id, query, city, salary_from, last_check)
        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
    ''', (user_id, query, city, salary_from))
    conn.commit()
    conn.close()

def remove_user(user_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('DELETE FROM users WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()

def get_all_users():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('SELECT user_id, query, city, salary_from FROM users')
    users = cur.fetchall()
    conn.close()
    return users

def mark_vacancy_sent(vacancy_id, user_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('''
        INSERT OR IGNORE INTO sent_vacancies (vacancy_id, user_id, sent_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
    ''', (vacancy_id, user_id))
    conn.commit()
    conn.close()

def is_vacancy_sent(vacancy_id, user_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('SELECT 1 FROM sent_vacancies WHERE vacancy_id = ? AND user_id = ?', 
                (vacancy_id, user_id))
    result = cur.fetchone()
    conn.close()
    return result is not None