#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Скрипт для добавления задач к боссу из JSON файла

Использование:
    python add_boss_tasks.py tasks.json --boss-id 1
    python add_boss_tasks.py tasks.json --boss-name "Имя босса"
"""

import json
import os
import sys
import argparse
from datetime import datetime
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash

# Добавляем текущую директорию в путь для импорта app
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, Boss, BossTask

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    """Проверяет, разрешено ли расширение файла"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def copy_image_file(image_path, upload_folder):
    """Копирует файл изображения в папку загрузок"""
    if not image_path or not os.path.exists(image_path):
        return None
    
    # Получаем имя файла
    filename = os.path.basename(image_path)
    
    # Проверяем расширение
    if not allowed_file(filename):
        print(f"Предупреждение: файл {filename} имеет недопустимое расширение. Пропускаю.")
        return None
    
    # Создаем безопасное имя файла
    safe_filename = secure_filename(filename)
    
    # Добавляем timestamp для уникальности
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    new_filename = f"boss_{timestamp}_{safe_filename}"
    
    # Путь для сохранения
    dest_path = os.path.join(upload_folder, new_filename)
    
    # Копируем файл
    import shutil
    shutil.copy2(image_path, dest_path)
    
    return new_filename

def add_tasks_from_json(json_file, boss_id=None, boss_name=None, image_base_path=None):
    """
    Добавляет задачи к боссу из JSON файла
    
    Args:
        json_file: путь к JSON файлу
        boss_id: ID босса (приоритет над boss_name)
        boss_name: имя босса
        image_base_path: базовый путь для поиска изображений (если не указан, используется директория JSON файла)
    """
    # Читаем JSON файл
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Ошибка: файл {json_file} не найден")
        return False
    except json.JSONDecodeError as e:
        print(f"Ошибка: неверный формат JSON файла: {e}")
        return False
    
    # Определяем базовый путь для изображений
    if image_base_path is None:
        image_base_path = os.path.dirname(os.path.abspath(json_file))
    
    with app.app_context():
        # Находим босса
        if boss_id:
            boss = Boss.query.get(boss_id)
            if not boss:
                print(f"Ошибка: босс с ID {boss_id} не найден")
                return False
        elif boss_name:
            boss = Boss.query.filter_by(name=boss_name).first()
            if not boss:
                print(f"Ошибка: босс с именем '{boss_name}' не найден")
                return False
        else:
            print("Ошибка: необходимо указать либо --boss-id, либо --boss-name")
            return False
        
        print(f"Найден босс: {boss.name} (ID: {boss.id})")
        
        # Получаем папку для загрузки изображений
        upload_folder = app.config.get('UPLOAD_FOLDER', 'static/uploads/tasks')
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder, exist_ok=True)
        
        # Обрабатываем задачи
        tasks_data = data.get('tasks', [])
        if not tasks_data:
            print("Ошибка: в JSON файле нет массива 'tasks'")
            return False
        
        added_count = 0
        skipped_count = 0
        
        for task_data in tasks_data:
            try:
                # Проверяем обязательные поля
                title = task_data.get('title', '').strip()
                correct_answer = task_data.get('correct_answer', '').strip()
                
                if not title:
                    print(f"Пропущена задача: отсутствует поле 'title'")
                    skipped_count += 1
                    continue
                
                if not correct_answer:
                    print(f"Пропущена задача '{title}': отсутствует поле 'correct_answer'")
                    skipped_count += 1
                    continue
                
                # Получаем опциональные поля
                description = task_data.get('description', '').strip() or None
                points = task_data.get('points', 0)
                
                # Проверяем, что points - это число
                try:
                    points = int(points)
                    if points < 0:
                        print(f"Предупреждение: для задачи '{title}' указано отрицательное значение points. Устанавливаю 0.")
                        points = 0
                except (ValueError, TypeError):
                    print(f"Предупреждение: для задачи '{title}' указано неверное значение points. Устанавливаю 0.")
                    points = 0
                
                # Обрабатываем изображение
                image_filename = None
                image_path = task_data.get('image_path') or task_data.get('image')
                
                if image_path:
                    # Если путь относительный, делаем его абсолютным относительно image_base_path
                    if not os.path.isabs(image_path):
                        image_path = os.path.join(image_base_path, image_path)
                    
                    image_filename = copy_image_file(image_path, upload_folder)
                    if image_filename:
                        print(f"  Изображение скопировано: {image_filename}")
                    else:
                        print(f"  Предупреждение: не удалось скопировать изображение для задачи '{title}'")
                
                # Создаем задачу
                new_task = BossTask(
                    boss_id=boss.id,
                    title=title,
                    description=description,
                    image_filename=image_filename,
                    correct_answer=correct_answer,
                    points=points
                )
                
                db.session.add(new_task)
                db.session.commit()
                
                print(f"✓ Добавлена задача: {title} (points: {points})")
                added_count += 1
                
            except Exception as e:
                db.session.rollback()
                print(f"Ошибка при добавлении задачи '{task_data.get('title', 'неизвестно')}': {e}")
                skipped_count += 1
                continue
        
        print(f"\nИтого: добавлено {added_count} задач, пропущено {skipped_count} задач")
        return True

def main():
    parser = argparse.ArgumentParser(
        description='Добавляет задачи к боссу из JSON файла',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Пример JSON файла:
{
    "tasks": [
        {
            "title": "Название задачи",
            "description": "Описание задачи (опционально)",
            "correct_answer": "Правильный ответ",
            "points": 10,
            "image_path": "path/to/image.png"
        },
        {
            "title": "Другая задача",
            "correct_answer": "Ответ",
            "points": 5
        }
    ]
}
        """
    )
    
    parser.add_argument('json_file', help='Путь к JSON файлу с задачами')
    parser.add_argument('--boss-id', type=int, help='ID босса')
    parser.add_argument('--boss-name', help='Имя босса')
    parser.add_argument('--image-base-path', help='Базовый путь для поиска изображений (по умолчанию: директория JSON файла)')
    
    args = parser.parse_args()
    
    if not args.boss_id and not args.boss_name:
        parser.error("Необходимо указать либо --boss-id, либо --boss-name")
    
    success = add_tasks_from_json(
        args.json_file,
        boss_id=args.boss_id,
        boss_name=args.boss_name,
        image_base_path=args.image_base_path
    )
    
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
