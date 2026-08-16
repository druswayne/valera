#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Добавить колонку current_turn_user_id в таблицу pvp_duel, если её нет."""
import os
import sys

# Корень проекта
os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.getcwd())

def main():
    import sqlite3
    for db_path in [os.path.join('instance', 'valera.db'), 'valera.db']:
        if os.path.exists(db_path):
            break
    else:
        print('БД valera.db не найдена в instance/ или в корне.')
        return 1
    conn = sqlite3.connect(db_path)
    cur = conn.execute('PRAGMA table_info(pvp_duel)')
    cols = [row[1] for row in cur.fetchall()]
    if 'current_turn_user_id' not in cols:
        conn.execute('ALTER TABLE pvp_duel ADD COLUMN current_turn_user_id INTEGER REFERENCES user(id)')
        conn.commit()
        print('Колонка current_turn_user_id добавлена в pvp_duel.')
    else:
        print('Колонка current_turn_user_id уже есть.')
    conn.close()
    return 0

if __name__ == '__main__':
    sys.exit(main())
