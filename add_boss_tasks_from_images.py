#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Добавляет задачи в boss_tasks.json на основе изображений из папки static/uploads/tasks/taski.

Правила:
- одно изображение = одна задача
- имя файла: a_b_c.jpg
  - b = correct_answer
-  - c = points (ИГНОРИРУЕТСЯ: для всех задач с картинкой points = 150)
- description отсутствует (поле не добавляется)
- image_path добавляется (относительно корня проекта), чтобы задачи можно было импортировать через add_boss_tasks.py

Запуск:
  python add_boss_tasks_from_images.py
  python add_boss_tasks_from_images.py --dry-run
  python add_boss_tasks_from_images.py --images-dir "static/uploads/tasks/taski" --tasks-json "boss_tasks.json"
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
from datetime import datetime
from typing import Any, Dict, List, Tuple


ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}


def _to_posix(path: str) -> str:
    return path.replace("\\", "/")


def _norm_key(path: str) -> str:
    # Нормализуем путь для сравнения (на Windows регистр не важен)
    return _to_posix(os.path.normpath(path)).lower()


def _iter_images(root_dir: str) -> List[str]:
    images: List[str] = []
    for dirpath, _dirnames, filenames in os.walk(root_dir):
        for fn in filenames:
            ext = os.path.splitext(fn)[1].lower()
            if ext in ALLOWED_EXTENSIONS:
                images.append(os.path.join(dirpath, fn))
    images.sort(key=lambda p: _norm_key(p))
    return images


def _parse_filename(filename: str) -> Tuple[str, str, int]:
    """
    Возвращает (a, correct_answer, points) по имени файла a_b_c.ext
    """
    stem = os.path.splitext(os.path.basename(filename))[0]
    parts = stem.split("_")
    if len(parts) < 3:
        raise ValueError("ожидается формат a_b_c.ext")
    a = "_".join(parts[:-2]).strip()
    correct_answer = parts[-2].strip()
    points_raw = parts[-1].strip()
    points = int(points_raw)
    # По требованию: для задач с картинкой points всегда 150 (независимо от c)
    points = 150
    return a, correct_answer, points


def _load_tasks_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict) or "tasks" not in data or not isinstance(data["tasks"], list):
        raise ValueError("Неверный формат boss_tasks.json: ожидался объект с ключом 'tasks' (список)")
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description="Добавляет задачи в boss_tasks.json из изображений (a_b_c.jpg).")
    parser.add_argument("--tasks-json", default="boss_tasks.json", help="Путь к boss_tasks.json")
    parser.add_argument(
        "--images-dir",
        default=os.path.join("static", "uploads", "tasks", "taski"),
        help="Папка с изображениями (рекурсивно)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Ничего не записывать, только показать статистику")
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Не создавать .bak копию boss_tasks.json перед записью",
    )

    args = parser.parse_args()

    project_dir = os.path.dirname(os.path.abspath(__file__))
    tasks_json_path = args.tasks_json
    if not os.path.isabs(tasks_json_path):
        tasks_json_path = os.path.join(project_dir, tasks_json_path)
    images_dir = args.images_dir
    if not os.path.isabs(images_dir):
        images_dir = os.path.join(project_dir, images_dir)

    if not os.path.exists(tasks_json_path):
        raise FileNotFoundError(f"Файл не найден: {tasks_json_path}")
    if not os.path.isdir(images_dir):
        raise FileNotFoundError(f"Папка не найдена: {images_dir}")

    data = _load_tasks_json(tasks_json_path)
    tasks: List[Dict[str, Any]] = data["tasks"]

    # Обновляем уже существующие "картинковые" задачи (из нужной папки) до points=150
    # Чтобы не затрагивать другие типы задач с картинками (если они появятся в будущем),
    # ограничиваемся только путями внутри static/uploads/tasks/taski/.
    images_root_rel = _to_posix(os.path.join("static", "uploads", "tasks", "taski")) + "/"
    updated_existing = 0
    for t in tasks:
        if not isinstance(t, dict):
            continue
        img = t.get("image_path") or t.get("image")
        if not isinstance(img, str):
            continue
        img_norm = _to_posix(os.path.normpath(img)).replace("\\", "/")
        if img_norm.lower().startswith(images_root_rel.lower()):
            if t.get("points") != 150:
                t["points"] = 150
                updated_existing += 1

    # Уже добавленные (чтобы скрипт был идемпотентным)
    existing_image_keys = set()
    for t in tasks:
        if isinstance(t, dict):
            img = t.get("image_path") or t.get("image")
            if isinstance(img, str) and img.strip():
                existing_image_keys.add(_norm_key(img.strip()))

    images = _iter_images(images_dir)

    added = 0
    skipped_existing = 0
    skipped_bad_name = 0
    skipped_bad_points = 0

    for img_abs in images:
        rel = os.path.relpath(img_abs, project_dir)
        rel_posix = _to_posix(rel)

        if _norm_key(rel_posix) in existing_image_keys:
            skipped_existing += 1
            continue

        try:
            a, correct_answer, points = _parse_filename(img_abs)
        except ValueError:
            skipped_bad_name += 1
            continue
        except Exception:
            skipped_bad_name += 1
            continue

        # points уже int, но если имя внезапно не число — пропускаем
        if not isinstance(points, int):
            skipped_bad_points += 1
            continue

        # title произвольный, но сделаем стабильным/читаемым
        title_num = a if a else os.path.splitext(os.path.basename(img_abs))[0]
        title = f"Задача по картинке #{title_num}"

        task: Dict[str, Any] = {
            "title": title,
            "correct_answer": correct_answer,
            "points": points,
            "image_path": rel_posix,
        }

        tasks.append(task)
        existing_image_keys.add(_norm_key(rel_posix))
        added += 1

    if args.dry_run:
        print(
            "DRY RUN:\n"
            f"- найдено изображений: {len(images)}\n"
            f"- будет добавлено задач: {added}\n"
            f"- будет обновлено существующих taskski points->150: {updated_existing}\n"
            f"- пропущено (уже есть по image_path): {skipped_existing}\n"
            f"- пропущено (неверное имя a_b_c): {skipped_bad_name}\n"
            f"- пропущено (неверные points): {skipped_bad_points}"
        )
        return 0

    if added == 0 and updated_existing == 0:
        print(
            "Новых задач не найдено.\n"
            f"- изображений: {len(images)}\n"
            f"- обновлено существующих taskski points->150: {updated_existing}\n"
            f"- уже было: {skipped_existing}\n"
            f"- неверное имя: {skipped_bad_name}"
        )
        return 0

    if not args.no_backup:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = tasks_json_path + f".bak_{ts}"
        shutil.copy2(tasks_json_path, backup_path)
        print(f"Создан бэкап: {backup_path}")

    with open(tasks_json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(
        "Готово:\n"
        f"- найдено изображений: {len(images)}\n"
        f"- добавлено задач: {added}\n"
        f"- обновлено существующих taskski points->150: {updated_existing}\n"
        f"- пропущено (уже есть по image_path): {skipped_existing}\n"
        f"- пропущено (неверное имя a_b_c): {skipped_bad_name}\n"
        f"- пропущено (неверные points): {skipped_bad_points}\n"
        f"- записано в: {tasks_json_path}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

