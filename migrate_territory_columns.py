"""Добавить колонки capture_enabled и capture_start_time в territory_battle_setting.
Запуск: python migrate_territory_columns.py
"""
import sqlite3
import os

# Путь к БД (instance/valera.db типично для Flask)
db_path = os.path.join(os.path.dirname(__file__), 'instance', 'valera.db')
if not os.path.exists(db_path):
    db_path = os.path.join(os.path.dirname(__file__), 'valera.db')
if not os.path.exists(db_path):
    print('БД не найдена. Укажите путь к instance/valera.db')
    exit(1)

conn = sqlite3.connect(db_path)
cur = conn.cursor()
cur.execute("PRAGMA table_info(territory_battle_setting)")
columns = [r[1] for r in cur.fetchall()]

if 'capture_enabled' not in columns:
    cur.execute('ALTER TABLE territory_battle_setting ADD COLUMN capture_enabled BOOLEAN DEFAULT 1 NOT NULL')
    print('Добавлена колонка capture_enabled')
if 'capture_start_time' not in columns:
    cur.execute('ALTER TABLE territory_battle_setting ADD COLUMN capture_start_time DATETIME')
    print('Добавлена колонка capture_start_time')
if 'capture_end_time' not in columns:
    cur.execute('ALTER TABLE territory_battle_setting ADD COLUMN capture_end_time DATETIME')
    print('Добавлена колонка capture_end_time')

conn.commit()
conn.close()
print('Готово.')
