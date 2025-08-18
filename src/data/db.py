import sqlite3


DB_NAME = 'users.db'

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            whatsapp_id TEXT PRIMARY KEY,
            refresh_token TEXT NOT NULL,
            spreadsheet_id TEXT
        )
    ''')
    conn.commit()
    conn.close()

def save_user_token(whatsapp_id, refresh_token):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute('INSERT OR REPLACE INTO users (whatsapp_id, refresh_token) VALUES (?, ?)', (whatsapp_id, refresh_token))
    conn.commit()
    conn.close()

def save_spreadsheet_id(whatsapp_id, spreadsheet_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute('UPDATE users SET spreadsheet_id = ? WHERE whatsapp_id = ?', (spreadsheet_id, whatsapp_id))
    conn.commit()
    conn.close()

def get_user(whatsapp_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute('SELECT refresh_token, spreadsheet_id FROM users WHERE whatsapp_id = ?', (whatsapp_id,))
    user_data = cursor.fetchone()
    conn.close()
    if user_data:
        return {'refresh_token': user_data[0], 'spreadsheet_id': user_data[1]}
    return None

init_db()
