"""
Скрипт формирует отчёт в txt:
1) Топ-3 клана: для каждого — название и все участники по урону+защите.
2) Топ-10 PvE по суммарному урону и защите.
3) Топ-10 PvP по числу выигранных дуэлей (как на /game-rating?tab=pvp).
"""
from app import (
    app,
    db,
    User,
    Clan,
    UserTerritoryStats,
    TerritoryRegionState,
    PvPDuel,
)
from sqlalchemy import func


def _member_display(user, stats):
    dmg = (stats.total_damage_dealt or 0) if stats else 0
    inf = (stats.total_influence_points or 0) if stats else 0
    name = user.character_name or user.username or f"User#{user.id}"
    return name, dmg, inf, dmg + inf


def _append_clan_block(lines, rank, clan_id, territory_count, members_by_clan):
    clan = db.session.get(Clan, clan_id)
    cname = clan.name if clan else f"Клан id={clan_id}"
    lines.append(f"Место {rank}: {cname}  (территорий: {territory_count})")
    members = members_by_clan.get(clan_id, [])
    if not members:
        lines.append("  Участников нет.")
    else:
        owner_id = clan.owner_id if clan else None
        lines.append("  Участники (по суммарному урону и защите, убыв.):")
        for pos, (u, stats) in enumerate(members, 1):
            name, dmg, inf, total = _member_display(u, stats)
            leader_mark = " (лидер)" if owner_id and u.id == owner_id else ""
            lines.append(f"    {pos}. {name}{leader_mark}  — урон: {dmg}, защита: {inf}, всего: {total}")
    lines.append("")


def main() -> None:
    with app.app_context():
        # Рейтинг кланов: как на странице «Топ кланов» — территория (убыв.), затем сумма (урон+защита) участников
        all_clans_territory = db.session.query(
            Clan.id,
            func.coalesce(func.count(TerritoryRegionState.region_index), 0).label('territory_count')
        ).outerjoin(TerritoryRegionState, Clan.id == TerritoryRegionState.owner_clan_id).group_by(Clan.id).all()

        score_expr = func.coalesce(UserTerritoryStats.total_damage_dealt, 0) + func.coalesce(
            UserTerritoryStats.total_influence_points, 0
        )
        clan_scores_rows = db.session.query(
            User.clan_id,
            func.coalesce(func.sum(score_expr), 0).label('clan_score')
        ).outerjoin(UserTerritoryStats, User.id == UserTerritoryStats.user_id).filter(
            User.clan_id.isnot(None)
        ).group_by(User.clan_id).all()
        clan_score_by_id = {row[0]: int(row[1] or 0) for row in clan_scores_rows}

        sorted_clans = sorted(
            all_clans_territory,
            key=lambda r: (r[1], clan_score_by_id.get(r[0], 0)),
            reverse=True
        )

        score_expr = func.coalesce(UserTerritoryStats.total_damage_dealt, 0) + func.coalesce(
            UserTerritoryStats.total_influence_points, 0
        )
        clan_ids_all = [r[0] for r in sorted_clans]
        all_members = []
        if clan_ids_all:
            all_members = db.session.query(User, UserTerritoryStats).outerjoin(
                UserTerritoryStats, User.id == UserTerritoryStats.user_id
            ).filter(User.clan_id.in_(clan_ids_all)).order_by(
                User.clan_id, score_expr.desc()
            ).all()

        members_by_clan = {}
        for u, stats in all_members:
            cid = u.clan_id
            if cid not in members_by_clan:
                members_by_clan[cid] = []
            members_by_clan[cid].append((u, stats))

        pve_score = func.coalesce(UserTerritoryStats.total_damage_dealt, 0) + func.coalesce(
            UserTerritoryStats.total_influence_points, 0
        )
        pve_rows = db.session.query(User, UserTerritoryStats).outerjoin(
            UserTerritoryStats, User.id == UserTerritoryStats.user_id
        ).order_by(pve_score.desc()).limit(10).all()

        wins_subq = db.session.query(
            PvPDuel.winner_id,
            func.count(PvPDuel.id).label('wins')
        ).filter(
            PvPDuel.status == 'finished',
            PvPDuel.winner_id.isnot(None)
        ).group_by(PvPDuel.winner_id).subquery()

        pvp_rows = db.session.query(User, func.coalesce(wins_subq.c.wins, 0).label('wins')).outerjoin(
            wins_subq, User.id == wins_subq.c.winner_id
        ).order_by(func.coalesce(wins_subq.c.wins, 0).desc(), User.id.asc()).limit(10).all()

        lines = []
        lines.append("=" * 60)
        lines.append("ОТЧЁТ: ТОП-3 КЛАНОВ, ТОП-10 PvE, ТОП-10 PvP")
        lines.append("=" * 60)
        lines.append("")

        lines.append("1) ТОП-3 КЛАНА — все участники каждого")
        lines.append("-" * 40)
        if not sorted_clans:
            lines.append("Нет кланов.")
            lines.append("")
        else:
            for rank, (clan_id, territory_count) in enumerate(sorted_clans[:3], start=1):
                _append_clan_block(lines, rank, clan_id, territory_count, members_by_clan)

        lines.append("2) ТОП-10 PvE (по суммарному урону и защите)")
        lines.append("-" * 40)
        if not pve_rows:
            lines.append("Нет данных.")
        else:
            for rank, (u, stats) in enumerate(pve_rows, 1):
                name, dmg, inf, total = _member_display(u, stats)
                lines.append(f"  {rank}. {name}  — урон: {dmg}, защита: {inf}, всего: {total}")
        lines.append("")

        lines.append("3) ТОП-10 PvP (по выигранным дуэлям)")
        lines.append("-" * 40)
        if not pvp_rows:
            lines.append("Нет данных.")
        else:
            for rank, (u, wins) in enumerate(pvp_rows, 1):
                name = u.character_name or u.username or f"User#{u.id}"
                w = int(wins or 0)
                lines.append(f"  {rank}. {name}  — побед: {w}")
        lines.append("")
        lines.append("=" * 60)

        report_text = "\n".join(lines)
        out_path = "report_rating_top.txt"
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(report_text)
        print(f"Отчёт записан в файл: {out_path}")


if __name__ == "__main__":
    main()
