import json
import os

from app import (
    app,
    db,
    ShopItem,
    ShopItemEffect,
    SHOP_CONTEXT_TERRITORY,
    SHOP_CATEGORY_ENHANCEMENT,
    SHOP_CATEGORY_CURSE,
    SHOP_EFFECT_TARGET_SELF,
    SHOP_EFFECT_TARGET_CLAN,
    SHOP_EFFECT_TARGET_REGION,
)


SEED_FILENAME = "shop_items_territory_seed.json"


def load_seed_items(path: str):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("Ожидался список предметов в JSON.")
    return data


def upsert_shop_item(item_data: dict):
    """
    Создать или обновить товар лавки битвы за территорию по имени и контексту.
    Эффекты всегда перезаписываются из JSON.
    """
    name = (item_data.get("name") or "").strip()
    if not name:
        print("Пропуск записи без имени:", item_data)
        return

    category = (item_data.get("category") or "").strip().lower()
    if category not in (SHOP_CATEGORY_ENHANCEMENT, SHOP_CATEGORY_CURSE):
        print(f"Пропуск '{name}': неизвестная категория {category!r}")
        return

    try:
        price = int(item_data.get("price") or 0)
    except (TypeError, ValueError):
        price = 0

    description = (item_data.get("description") or "").strip() or None
    effects_list = item_data.get("effects") or []

    # По имени и контексту territory
    item = ShopItem.query.filter_by(
        name=name,
        shop_context=SHOP_CONTEXT_TERRITORY,
    ).first()

    is_new = item is None
    if is_new:
        item = ShopItem(
            name=name,
            description=description,
            price=price,
            category=category,
            shop_context=SHOP_CONTEXT_TERRITORY,
        )
        db.session.add(item)
    else:
        item.description = description
        item.price = price
        item.category = category

    # Сносим старые эффекты и создаём заново
    ShopItemEffect.query.filter_by(shop_item_id=item.id if not is_new else None).delete()
    db.session.flush()

    valid_targets = {SHOP_EFFECT_TARGET_SELF, SHOP_EFFECT_TARGET_CLAN, SHOP_EFFECT_TARGET_REGION}

    for e in effects_list:
        effect_type = (e.get("effect_type") or "damage").strip()
        try:
            percent_change = float(e.get("percent_change", 0.0))
        except (TypeError, ValueError):
            percent_change = 0.0

        target = (e.get("target") or "").strip().lower() or None
        if target not in valid_targets:
            target = SHOP_EFFECT_TARGET_SELF

        duration_value = e.get("duration_minutes", None)
        if duration_value in ("", None):
            duration_minutes = None
        else:
            try:
                duration_minutes = int(duration_value)
            except (TypeError, ValueError):
                duration_minutes = None

        eff = ShopItemEffect(
            shop_item_id=item.id,
            effect_type=effect_type,
            percent_change=percent_change,
            target=target,
            duration_minutes=duration_minutes,
        )
        db.session.add(eff)

    print(f"{'Создан' if is_new else 'Обновлён'} товар: {name!r}, категория={category}, цена={price}")


def main():
    root_dir = os.path.dirname(os.path.abspath(__file__))
    seed_path = os.path.join(root_dir, SEED_FILENAME)
    if not os.path.exists(seed_path):
        raise SystemExit(f"Файл с данными не найден: {seed_path}")

    items = load_seed_items(seed_path)

    with app.app_context():
        for item_data in items:
            upsert_shop_item(item_data)
        db.session.commit()
        print(f"Готово, обработано записей: {len(items)}")


if __name__ == "__main__":
    main()

