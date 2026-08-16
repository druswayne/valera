import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv


SLOT_ORDER = ["helmet", "chest", "pants", "gloves", "boots", "weapon_main", "weapon_off"]
GRADE_ORDER = {"d": 0, "c": 1, "b": 2, "a": 3, "s": 4}


def _clean_uri(uri: str | None) -> str:
    if not uri:
        return ""
    s = uri.strip()
    s = s.strip("'").strip('"')
    return s


def map_equipment_slot(slot: str) -> str:
    slot = (slot or "").strip().lower()
    if slot in ("weapon_main", "weapon_off"):
        return "weapon"
    return slot


def compute_sort_order(set_index: int, slot: str) -> int:
    # sort_order is used only within grade in app.py
    try:
        slot_idx = SLOT_ORDER.index(slot)
    except ValueError:
        slot_idx = 999
    return set_index * len(SLOT_ORDER) + slot_idx


def parse_args():
    p = argparse.ArgumentParser(description="Import equipment items from equipment_sets_by_grade.json")
    p.add_argument("--json-path", default="equipment_sets_by_grade.json", help="Path to JSON source file")
    p.add_argument("--dry-run", action="store_true", help="Only validate/print counts, do not touch DB")
    p.add_argument("--limit", type=int, default=0, help="Limit number of items processed (0 = no limit)")
    return p.parse_args()


def validate_payload(payload: dict) -> None:
    if not isinstance(payload, dict):
        raise ValueError("JSON root must be an object")
    grades = payload.get("grades")
    if not isinstance(grades, list) or not grades:
        raise ValueError("JSON must contain non-empty 'grades' list")
    for g in grades:
        grade = (g.get("grade") or "").strip().lower()
        if grade not in GRADE_ORDER:
            raise ValueError(f"Unknown grade in JSON: {grade!r}")
        sets = g.get("sets")
        if not isinstance(sets, list) or not sets:
            raise ValueError("Each grade must contain non-empty 'sets' list")
        for s in sets:
            items = s.get("items")
            if not isinstance(items, list) or not items:
                raise ValueError("Each set must contain non-empty 'items' list")
            for it in items:
                slot = (it.get("slot") or "").strip().lower()
                if slot not in SLOT_ORDER:
                    raise ValueError(f"Unknown slot in JSON: {slot!r}")
                name = (it.get("name") or "").strip()
                if not name:
                    raise ValueError("Item name is required")
                price = it.get("price")
                try:
                    int(price)
                except (TypeError, ValueError):
                    raise ValueError(f"Item price must be int-like, got {price!r} for {name!r}")
                effects = it.get("effects")
                if not isinstance(effects, list):
                    raise ValueError(f"Item effects must be list for {name!r}")
                for e in effects:
                    if "effect_type" not in e:
                        raise ValueError(f"Effect missing effect_type for {name!r}")
                    if "percent_change" not in e:
                        raise ValueError(f"Effect missing percent_change for {name!r}")
                # image_filename is required by the task (already added previously),
                # but keep validation soft: allow empty/null to not break old datasets.


def main():
    args = parse_args()
    root_dir = Path(__file__).resolve().parent
    # Проверяем SQLALCHEMY_DATABASE_URI до импорта app — подтягиваем .env здесь.
    dotenv_path = root_dir / ".env"
    if dotenv_path.exists():
        load_dotenv(dotenv_path=str(dotenv_path), override=False)

    json_path = (root_dir / args.json_path).resolve()

    if not json_path.exists():
        print(f"JSON file not found: {json_path}", file=sys.stderr)
        return 2

    with open(json_path, "r", encoding="utf-8") as f:
        payload = json.load(f)

    validate_payload(payload)

    items_to_import: list[dict] = []
    for g in payload["grades"]:
        grade = g["grade"].strip().lower()
        for set_index, st in enumerate(g["sets"]):
            for it in st["items"]:
                items_to_import.append(
                    {
                        "grade": grade,
                        "set_index": set_index,
                        **it,
                    }
                )

    if args.limit and args.limit > 0:
        items_to_import = items_to_import[: args.limit]

    if args.dry_run:
        print(f"[dry-run] items validated: {len(items_to_import)}")
        return 0

    # app.py requires SQLALCHEMY_DATABASE_URI, so check before import for nicer error message.
    uri = _clean_uri(os.getenv("SQLALCHEMY_DATABASE_URI"))
    if not uri:
        print(
            "SQLALCHEMY_DATABASE_URI is not set. "
            "Set it in environment/.env and retry. Example: "
            "postgresql://postgres:1@localhost:5432/data",
            file=sys.stderr,
        )
        return 2

    # Lazy import so --dry-run can work without DB config.
    from app import (
        app,
        db,
        ShopItem,
        ShopItemEffect,
        SHOP_CATEGORY_EQUIPMENT,
        SHOP_CONTEXT_TERRITORY,
    )

    created = 0
    updated = 0

    with app.app_context():
        for row in items_to_import:
            slot = (row.get("slot") or "").strip().lower()
            grade = (row.get("grade") or "").strip().lower()
            name = (row.get("name") or "").strip()
            description = row.get("description") or None
            price = int(row.get("price") or 0)
            image_filename_present = "image_filename" in row
            image_filename = row.get("image_filename") if image_filename_present else None
            effects = row.get("effects") or []

            equipment_slot = map_equipment_slot(slot)
            sort_order = compute_sort_order(int(row.get("set_index") or 0), slot)

            # Stable identity to avoid collisions for duplicate names in JSON.
            existing_q = (
                ShopItem.query.filter(
                    ShopItem.shop_context == SHOP_CONTEXT_TERRITORY,
                    ShopItem.category == SHOP_CATEGORY_EQUIPMENT,
                    ShopItem.name == name,
                    ShopItem.equipment_slot == equipment_slot,
                    ShopItem.grade == grade,
                )
            )
            existing_list = existing_q.all()
            existing = existing_list[0] if existing_list else None

            # If DB has duplicates for same key, keep the first and delete the rest.
            if len(existing_list) > 1:
                for dup_item in existing_list[1:]:
                    db.session.delete(dup_item)

            is_new = existing is None
            if is_new:
                item = ShopItem(
                    name=name,
                    description=description,
                    price=price,
                    category=SHOP_CATEGORY_EQUIPMENT,
                    shop_context=SHOP_CONTEXT_TERRITORY,
                    equipment_slot=equipment_slot,
                    grade=grade,
                    sort_order=sort_order,
                    image_filename=(image_filename or None) if image_filename_present else None,
                )
                db.session.add(item)
                db.session.flush()
            else:
                item = existing
                item.description = description
                item.price = price
                item.equipment_slot = equipment_slot
                item.grade = grade
                item.sort_order = sort_order
                if image_filename_present:
                    item.image_filename = image_filename or None

                # Replace effects completely (equipment bonuses depend on the current effect list).
                ShopItemEffect.query.filter_by(shop_item_id=item.id).delete()
                db.session.flush()

            for e in effects:
                effect_type = (e.get("effect_type") or "").strip().lower()
                percent_change = float(e.get("percent_change", 0) or 0)
                eff = ShopItemEffect(
                    shop_item_id=item.id,
                    effect_type=effect_type,
                    percent_change=percent_change,
                    target=None,
                    duration_minutes=None,
                )
                db.session.add(eff)

            if is_new:
                created += 1
            else:
                updated += 1

        db.session.commit()

    print(f"Import finished. created={created}, updated={updated}, total={len(items_to_import)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

