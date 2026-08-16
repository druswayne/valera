"""Добавить колонку last_seen_at в таблицу pvp_arena_presence для серверной проверки неактивности на арене.
Запуск: python migrate_pvp_arena_last_seen.py
"""
import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), 'instance', 'valera.db')
if not os.path.exists(db_path):
    db_path = os.path.join(os.path.dirname(__file__), 'valera.db')
if not os.path.exists(db_path):
    print('БД не найдена. Укажите путь к instance/valera.db')
    exit(1)

conn = sqlite3.connect(db_path)
cur = conn.cursor()
cur.execute("PRAGMA table_info(pvp_arena_presence)")
columns = [r[1] for r in cur.fetchall()]

if 'last_seen_at' not in columns:
    cur.execute('ALTER TABLE pvp_arena_presence ADD COLUMN last_seen_at DATETIME')
    cur.execute("UPDATE pvp_arena_presence SET last_seen_at = entered_at")
    conn.commit()
    print('Добавлена колонка last_seen_at в pvp_arena_presence.')
else:
    print('Колонка last_seen_at уже есть.')

conn.close()
print('Готово.')
