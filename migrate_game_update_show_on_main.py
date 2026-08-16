"""Добавить колонку show_on_main в таблицу game_update.

Запуск: python migrate_game_update_show_on_main.py
"""
import os
import sqlite3


def main() -> None:
    base_dir = os.path.dirname(__file__)
    db_path = os.path.join(base_dir, 'instance', 'valera.db')
    if not os.path.exists(db_path):
        db_path = os.path.join(base_dir, 'valera.db')
    if not os.path.exists(db_path):
        print('БД не найдена. Укажите путь к instance/valera.db')
        return

    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(game_update)")
        columns = [row[1] for row in cur.fetchall()]

        if 'show_on_main' not in columns:
            cur.execute(
                'ALTER TABLE game_update '
                'ADD COLUMN show_on_main BOOLEAN DEFAULT 0 NOT NULL'
            )
            print('Добавлена колонка show_on_main в game_update')
        else:
            print('Колонка show_on_main уже существует в game_update')

        conn.commit()
    finally:
        conn.close()
    print('Готово.')


if __name__ == '__main__':
    main()

