"""
Перемешать области карты между топ-10 кланами по рейтингу страницы «Топ кланов».

Критерий топа совпадает с /game-rating?tab=clans (app.game_rating_page):
число занятых территорий (убыв.), при равенстве — сумма (урон + защита) участников.

Берутся все области из territory_region_config с is_locked = false; для каждой
области владелец выбирается случайно из топ-10 (равные шансы у каждого клана).
Число областей у кланов получается неравномерным (как при бросках кубика).
Без флага --seed результат при каждом запуске другой; с --seed — тот же самый.
Кланы из топа без земель до перетасовки тоже могут получить области. Заблокированные
области не меняются.

Сила (strength) на перераспределённых областях — случайное целое от 0 до 1000
(для каждой области отдельно), owner_class_id = NULL.

Все метки на карте (clan_territory_marker) снимаются — иначе остаются ссылки
на чужие области.

Запуск:
  python shuffle_territory_regions_top10_clans.py
  python shuffle_territory_regions_top10_clans.py --apply
  python shuffle_territory_regions_top10_clans.py --apply --seed 42
"""
from __future__ import annotations

import argparse
import random
import sys
from collections import Counter
from typing import Dict, List, Sequence

from sqlalchemy import func

from app import (
    app,
    db,
    Clan,
    ClanTerritoryMarker,
    TerritoryRegionConfig,
    TerritoryRegionState,
    User,
    UserTerritoryStats,
)


def _top_clan_ids(limit: int = 10) -> List[int]:
    """Как game_rating_page (tab=clans): территории, затем очки клана."""
    all_clans_territory = (
        db.session.query(
            Clan.id,
            func.coalesce(func.count(TerritoryRegionState.region_index), 0).label(
                "territory_count"
            ),
        )
        .outerjoin(TerritoryRegionState, Clan.id == TerritoryRegionState.owner_clan_id)
        .group_by(Clan.id)
        .all()
    )

    score_expr = func.coalesce(UserTerritoryStats.total_damage_dealt, 0) + func.coalesce(
        UserTerritoryStats.total_influence_points, 0
    )
    clan_scores_rows = (
        db.session.query(
            User.clan_id,
            func.coalesce(func.sum(score_expr), 0).label("clan_score"),
        )
        .outerjoin(UserTerritoryStats, User.id == UserTerritoryStats.user_id)
        .filter(User.clan_id.isnot(None))
        .group_by(User.clan_id)
        .all()
    )
    clan_score_by_id: Dict[int, int] = {int(row[0]): int(row[1] or 0) for row in clan_scores_rows}

    sorted_clans = sorted(
        all_clans_territory,
        key=lambda r: (int(r[1] or 0), clan_score_by_id.get(int(r[0]), 0)),
        reverse=True,
    )
    return [int(r[0]) for r in sorted_clans[:limit]]


def _unlocked_region_indices() -> List[int]:
    rows = (
        db.session.query(TerritoryRegionConfig.region_index)
        .filter(TerritoryRegionConfig.is_locked.is_(False))
        .order_by(TerritoryRegionConfig.region_index.asc())
        .all()
    )
    return [int(r[0]) for r in rows]


def _random_owner_assignments(top_ids: List[int], n: int) -> List[int]:
    """Для каждой из n областей — независимый случайный клан из top_ids (неравномерно по итогу)."""
    if not top_ids or n == 0:
        return []
    return [random.choice(top_ids) for _ in range(n)]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Записать изменения в БД (без флага — только просмотр плана)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Seed для random (воспроизводимость)",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    dry_run = not args.apply

    with app.app_context():
        top_ids = _top_clan_ids(10)
        if not top_ids:
            print("Нет кланов в базе.", file=sys.stderr)
            return 1

        indices = _unlocked_region_indices()
        if not indices:
            print(
                "Нет разблокированных областей в territory_region_config. Нечего распределять.",
                file=sys.stderr,
            )
            return 1

        states: List[TerritoryRegionState] = (
            TerritoryRegionState.query.filter(TerritoryRegionState.region_index.in_(indices))
            .order_by(TerritoryRegionState.region_index.asc())
            .all()
        )
        by_index = {s.region_index: s for s in states}
        missing = [i for i in indices if i not in by_index]
        if missing:
            print(
                f"Предупреждение: нет строк territory_region_state для region_index {missing}; "
                "создаём при --apply.",
                file=sys.stderr,
            )

        if args.seed is not None:
            random.seed(args.seed)

        n = len(indices)
        new_owners = _random_owner_assignments(top_ids, n)
        new_strengths = [random.randint(0, 1000) for _ in range(n)]

        before_owners = [int(by_index[i].owner_clan_id) if i in by_index and by_index[i].owner_clan_id is not None else None for i in indices]

        print("Топ кланов (id), порядок как на странице рейтинга:", top_ids)
        print(f"Разблокированных областей: {n}, region_index: {indices}")
        print("Было owner_clan_id (по порядку регионов):", before_owners)
        print("Станет owner_clan_id (случайно по одному на область):", new_owners)
        print("Станет strength (0..1000 по каждой области):", new_strengths)
        print("Распределение после (счётчик по клану):", dict(Counter(new_owners)))

        if dry_run:
            print("\nРежим просмотра (--apply не указан). БД не изменена.")
            return 0

        for idx, new_cid, strv in zip(indices, new_owners, new_strengths):
            st = by_index.get(idx)
            if st is None:
                st = TerritoryRegionState(
                    region_index=idx,
                    owner_class_id=None,
                    owner_clan_id=new_cid,
                    strength=strv,
                )
                db.session.add(st)
                by_index[idx] = st
            else:
                st.owner_clan_id = new_cid
                st.owner_class_id = None
                st.strength = strv

        ClanTerritoryMarker.query.delete(synchronize_session=False)
        db.session.commit()
        print("\nГотово: области перераспределены, strength случайный 0..1000, все метки сняты.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
