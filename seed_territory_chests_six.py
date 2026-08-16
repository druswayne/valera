#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Добавляет в лавку территории новые сундуки (по умолчанию: 5 обычных, 5 редких, 3 очень редких).

  — у каждого ≥12 вариантов дропа (grant — товар лавки, не сундук);
  — description варианта = название товара-награды;
  — дешёвые награды — tier high, дорогие — very_low;
  — цена сундука ≈ матожидание стоимости награды;
  — уже существующие сундуки в БД не удаляются (имена с префиксом NEW_CHEST_PREFIX).

Товары-награды в диапазоне цен; при нехватке создаются плейсхолдеры (картинки item/standart/).

Повторный запуск добавит ещё один такой же набор — при необходимости удаляйте дубликаты вручную в админке.
"""
from __future__ import annotations

import os
import sys
import logging

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import (  # noqa: E402
    app,
    db,
    ShopItem,
    ShopChestDropOption,
    SHOP_CONTEXT_TERRITORY,
    SHOP_CATEGORY_CHEST,
    SHOP_CATEGORY_EQUIPMENT,
    CHEST_TYPE_NORMAL,
    CHEST_TYPE_RARE,
    CHEST_TYPE_VERY_RARE,
    CHEST_DROP_CHANCE_TIER_HIGH,
    CHEST_DROP_CHANCE_TIER_MEDIUM,
    CHEST_DROP_CHANCE_TIER_VERY_LOW,
    CHEST_DROP_CHANCE_WEIGHTS,
)

# Плейсхолдеры-награды (как раньше)
AUTOPREFIX = "[Автосид-лавка] "
# Новые сундуки этим скриптом — другой префикс, чтобы не трогать уже созданные
NEW_CHEST_PREFIX = "[Автосид-лавка+] "
DROP_COUNT = 12
CHEST_IMAGE = "item/standart/breastplate.png"
LOG_FILE = "seed_territory_chests_six.log"
ERROR_LOG_FILE = "seed_territory_chests_six_errors.log"

PLACEHOLDER_SLOTS_IMGS = [
    ("helmet", "item/standart/helmet.png"),
    ("gloves", "item/standart/gloves.png"),
    ("pants", "item/standart/trousers.png"),
    ("chest", "item/standart/breastplate.png"),
    ("weapon", "item/standart/weapon.png"),
]


logger = logging.getLogger("seed_territory_chests_six")
error_logger = logging.getLogger("seed_territory_chests_six_errors")


def _setup_logging() -> None:
    if logger.handlers and error_logger.handlers:
        return

    log_dir = os.path.dirname(os.path.abspath(__file__))
    log_path = os.path.join(log_dir, LOG_FILE)
    err_log_path = os.path.join(log_dir, ERROR_LOG_FILE)

    log_format = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")

    logger.setLevel(logging.INFO)
    logger.propagate = False
    error_logger.setLevel(logging.ERROR)
    error_logger.propagate = False

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(logging.INFO)
    stream_handler.setFormatter(log_format)

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(log_format)

    error_file_handler = logging.FileHandler(err_log_path, encoding="utf-8")
    error_file_handler.setLevel(logging.ERROR)
    error_file_handler.setFormatter(log_format)

    logger.addHandler(stream_handler)
    logger.addHandler(file_handler)
    error_logger.addHandler(error_file_handler)

def _enrich_specs_from_grant_names(specs: list[dict]) -> None:
    """Текст варианта дропа для игрока = название товара-награды (как в каталоге лавки)."""
    for sp in specs:
        g = db.session.get(ShopItem, int(sp["grant_id"]))
        nm = (g.name or "").strip() if g else "Награда"
        sp["title"] = None
        sp["description"] = nm


def _pick_pool(pmin: int, pmax: int, need: int) -> list[ShopItem]:
    q = (
        ShopItem.query.filter(
            ShopItem.shop_context == SHOP_CONTEXT_TERRITORY,
            ShopItem.category != SHOP_CATEGORY_CHEST,
            ShopItem.price >= pmin,
            ShopItem.price <= pmax,
        )
        .order_by(ShopItem.price.asc(), ShopItem.id.asc())
        .all()
    )
    if len(q) >= need:
        return q
    created: list[ShopItem] = []
    n_missing = max(need - len(q), 6)
    span = max(1, min(50_000, pmax - pmin))
    for i in range(n_missing):
        price = int(pmin + (i + 1) * span / (n_missing + 2))
        price = max(pmin, min(pmax, price))
        slot, img = PLACEHOLDER_SLOTS_IMGS[i % len(PLACEHOLDER_SLOTS_IMGS)]
        name = f"{AUTOPREFIX}награда {slot} #{price}"
        it = ShopItem(
            name=name,
            description="Служебный предмет для дропа сундуков (сид).",
            price=price,
            category=SHOP_CATEGORY_EQUIPMENT,
            shop_context=SHOP_CONTEXT_TERRITORY,
            equipment_slot=slot,
            grade="d",
            image_filename=img,
            sort_order=9000 + i,
        )
        db.session.add(it)
        created.append(it)
    db.session.flush()
    q2 = (
        ShopItem.query.filter(
            ShopItem.shop_context == SHOP_CONTEXT_TERRITORY,
            ShopItem.category != SHOP_CATEGORY_CHEST,
            ShopItem.price >= pmin,
            ShopItem.price <= pmax,
        )
        .order_by(ShopItem.price.asc(), ShopItem.id.asc())
        .all()
    )
    return q2 if q2 else (q + created)


def _slice_by_price_thirds(items: list[ShopItem]) -> tuple[list[ShopItem], list[ShopItem], list[ShopItem]]:
    if not items:
        return [], [], []
    L = len(items)
    a = max(1, L // 3)
    b = max(a + 1, (2 * L) // 3)
    low = items[:a]
    mid = items[a:b] or items[a : a + 1]
    highp = items[b:] or items[-1:]
    return low, mid, highp


def _rotate_pool(items: list[ShopItem], rotation: int) -> list[ShopItem]:
    """Сдвиг списка по цене, чтобы у сундуков одного типа отличался набор строк дропа."""
    items_sorted = sorted(items, key=lambda x: (x.price, x.id))
    L = len(items_sorted)
    if L == 0 or rotation == 0:
        return items_sorted
    k = (rotation * max(1, L // 5)) % L
    return items_sorted[k:] + items_sorted[:k]


def _build_specs(items: list[ShopItem], n: int, rotation: int = 0) -> list[dict]:
    low, mid, highp = _slice_by_price_thirds(_rotate_pool(items, rotation))
    per = n // 3
    rest = n - per * 3
    specs: list[dict] = []
    for i in range(per):
        specs.append({"tier": CHEST_DROP_CHANCE_TIER_HIGH, "grant_id": low[i % len(low)].id})
    for i in range(per):
        specs.append({"tier": CHEST_DROP_CHANCE_TIER_MEDIUM, "grant_id": mid[i % len(mid)].id})
    for i in range(per):
        specs.append({"tier": CHEST_DROP_CHANCE_TIER_VERY_LOW, "grant_id": highp[i % len(highp)].id})
    for i in range(rest):
        specs.append({"tier": CHEST_DROP_CHANCE_TIER_VERY_LOW, "grant_id": highp[i % len(highp)].id})
    return specs


def _ev_price(specs: list[dict], price_by_id: dict[int, int]) -> int:
    tw = sum(CHEST_DROP_CHANCE_WEIGHTS[s["tier"]] for s in specs)
    if tw <= 0:
        return 0
    s_ev = sum(
        CHEST_DROP_CHANCE_WEIGHTS[s["tier"]] / tw * int(price_by_id.get(s["grant_id"], 0))
        for s in specs
    )
    return int(round(s_ev))


def _next_chest_sort_order_base() -> int:
    last = (
        ShopItem.query.filter_by(shop_context=SHOP_CONTEXT_TERRITORY, category=SHOP_CATEGORY_CHEST)
        .order_by(ShopItem.sort_order.desc())
        .first()
    )
    return int(last.sort_order) + 30 if last and last.sort_order is not None else 150


def _add_chest(
    name: str,
    description: str,
    chest_type: str,
    specs: list[dict],
    price_by_id: dict[int, int],
    *,
    sort_order: int,
) -> None:
    price = max(1, _ev_price(specs, price_by_id))
    chest = ShopItem(
        name=name,
        description=description,
        price=price,
        category=SHOP_CATEGORY_CHEST,
        shop_context=SHOP_CONTEXT_TERRITORY,
        chest_type=chest_type,
        image_filename=CHEST_IMAGE,
        chest_image_open_filename=None,
        sort_order=sort_order,
    )
    db.session.add(chest)
    db.session.flush()
    for i, sp in enumerate(specs, start=1):
        db.session.add(
            ShopChestDropOption(
                shop_item_id=chest.id,
                title=(sp.get("title") or "").strip() or None,
                description=(sp.get("description") or "").strip() or None,
                chance_tier=sp["tier"],
                max_per_user=99,
                grant_shop_item_id=int(sp["grant_id"]),
                sort_order=i,
            )
        )


def main():
    _setup_logging()

    # 5 обычных + 5 редких + 3 очень редких; старые записи в БД не трогаем.
    chests_meta: list[tuple[str, str, str, int, int]] = [
        # обычные (до 1000)
        (
            f"{NEW_CHEST_PREFIX}Дубовый ящик землепроходца",
            "Крепёж из жилы и дуба — везут под скамьей у повозки. Содержимое до тысячи нумов.",
            CHEST_TYPE_NORMAL,
            1,
            1000,
        ),
        (
            f"{NEW_CHEST_PREFIX}Ларчик лекаря из Нижнего брода",
            "Смола, травы и мелочь для обмена на постоялом дворе. Дары до тысячи нумов.",
            CHEST_TYPE_NORMAL,
            1,
            1000,
        ),
        (
            f"{NEW_CHEST_PREFIX}Сундук с якорем и цепью",
            "Морская клейма на крышке. Улов и сувениры до тысячи нумов.",
            CHEST_TYPE_NORMAL,
            1,
            1000,
        ),
        (
            f"{NEW_CHEST_PREFIX}Железный сундук сторожа ворот",
            "Тяжёлый замок и ржавый гвоздь вместо ручки. Внутри — мелкие ценности до тысячи нумов.",
            CHEST_TYPE_NORMAL,
            1,
            1000,
        ),
        (
            f"{NEW_CHEST_PREFIX}Шкатулка с выжженным волчьим следом",
            "Охотничий знак на крышке. Трофеи и безделушки до тысячи нумов.",
            CHEST_TYPE_NORMAL,
            1,
            1000,
        ),
        # редкие (1000–5000)
        (
            f"{NEW_CHEST_PREFIX}Бронзовый сундук пилигрима-алхимика",
            "Патина и запах серы. Содержимое от тысячи до пяти тысяч нумов.",
            CHEST_TYPE_RARE,
            1000,
            5000,
        ),
        (
            f"{NEW_CHEST_PREFIX}Ларец с витиеватым гербом",
            "Герб выцарапан иглой по лаку. Родовые и гильдейские дары: 1000–5000 нумов.",
            CHEST_TYPE_RARE,
            1000,
            5000,
        ),
        (
            f"{NEW_CHEST_PREFIX}Сундук с двумя замками коменданта",
            "Два ключа — два хранителя. Клады от тысячи до пяти тысяч нумов.",
            CHEST_TYPE_RARE,
            1000,
            5000,
        ),
        (
            f"{NEW_CHEST_PREFIX}Ящик с воском и перстнем печати",
            "Сургуч во фляжке. Ценности от тысячи до пяти тысяч нумов.",
            CHEST_TYPE_RARE,
            1000,
            5000,
        ),
        (
            f"{NEW_CHEST_PREFIX}Кованый ларь фамильного оружейника",
            "Зарубки на ободе — счёт заказов. Награды от тысячи до пяти тысяч нумов.",
            CHEST_TYPE_RARE,
            1000,
            5000,
        ),
        # очень редкие (>5000 в дорогой трети пула)
        (
            f"{NEW_CHEST_PREFIX}Саркофаг алхимика королевского двора",
            "Камень и свинцовая обшивка. Встречаются дары дороже пяти тысяч нумов.",
            CHEST_TYPE_VERY_RARE,
            5001,
            999_999,
        ),
        (
            f"{NEW_CHEST_PREFIX}Сундук с чешуйчатой интарсией",
            "Резьба из тёмного дерева и перламутра. Редчайшие сокровища.",
            CHEST_TYPE_VERY_RARE,
            5001,
            999_999,
        ),
        (
            f"{NEW_CHEST_PREFIX}Кристальный гробец звёздных картографов",
            "Грани ловят свет. За стеклом — то, что не кладут в обычные лавки.",
            CHEST_TYPE_VERY_RARE,
            5001,
            999_999,
        ),
    ]

    logger.info("Запуск сидирования сундуков территории.")

    with app.app_context():
        try:
            sort_base = _next_chest_sort_order_base()

            for idx, (name, desc, ctype, pmin, pmax) in enumerate(chests_meta):
                pool = _pick_pool(pmin, pmax, DROP_COUNT)
                specs = _build_specs(pool, DROP_COUNT, rotation=idx + 1)
                _enrich_specs_from_grant_names(specs)
                ids = {s["grant_id"] for s in specs}
                price_by: dict[int, int] = {}
                for gid in ids:
                    g = db.session.get(ShopItem, gid)
                    if g:
                        price_by[gid] = int(g.price or 0)
                _add_chest(name, desc, ctype, specs, price_by, sort_order=sort_base + idx * 5)
                logger.info(
                    "OK: %r, цена=%s, вариантов=%s",
                    name,
                    max(1, _ev_price(specs, price_by)),
                    len(specs),
                )

            db.session.commit()
            logger.info(
                "Готово: добавлено %s сундуков (5+5+3), старые записи не удалялись.",
                len(chests_meta),
            )
        except Exception:
            db.session.rollback()
            logger.exception("Ошибка при сидировании. Транзакция откатана.")
            error_logger.exception("Критическая ошибка при сидировании сундуков.")
            raise


if __name__ == "__main__":
    main()
