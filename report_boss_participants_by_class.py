import argparse
import os
import sqlite3
from dataclasses import dataclass
import sys
import re


@dataclass(frozen=True)
class BossInfo:
    id: int
    name: str | None


def _force_utf8_output() -> None:
    """
    На Windows консоль/терминал иногда по умолчанию в cp1251/cp866, из-за чего кириллица
    превращается в "����". Принудительно переключаем stdout/stderr на UTF-8.
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        except Exception:
            pass


_SPACE_RE = re.compile(r"\s+")


def _canon_person_name(value: str | None) -> str | None:
    """
    Нормализует имя для дедупликации:
    - trim + схлопывание пробелов
    - нижний регистр (casefold)
    - ё -> е
    - простая нормализация уменьшительных форм (например: "ваня" -> "иван")
    """
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None

    s = s.replace("\u00A0", " ")  # NBSP
    s = _SPACE_RE.sub(" ", s)
    s = s.casefold().replace("ё", "е")

    parts = s.split(" ")
    if parts:
        first = parts[0]
        # минимально необходимое по запросу + пару частых вариантов
        first_map = {
            "ваня": "иван",
            "ванька": "иван",
            "ванечка": "иван",
        }
        parts[0] = first_map.get(first, first)
    return " ".join(parts)


def _connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    # SQL-функция для использования в запросах
    conn.create_function("canon_name", 1, _canon_person_name)
    return conn


def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1",
        (table_name,),
    ).fetchone()
    return row is not None


def _get_default_boss(conn: sqlite3.Connection) -> BossInfo | None:
    # 1) активный
    row = conn.execute(
        "SELECT id, name FROM boss WHERE is_active = 1 ORDER BY updated_at DESC, id DESC LIMIT 1"
    ).fetchone()
    if row:
        return BossInfo(int(row["id"]), row["name"])

    # 2) последний созданный
    row = conn.execute(
        "SELECT id, name FROM boss ORDER BY created_at DESC, id DESC LIMIT 1"
    ).fetchone()
    if row:
        return BossInfo(int(row["id"]), row["name"])

    return None


def _get_boss_by_id(conn: sqlite3.Connection, boss_id: int) -> BossInfo | None:
    row = conn.execute("SELECT id, name FROM boss WHERE id = ?", (boss_id,)).fetchone()
    if not row:
        return None
    return BossInfo(int(row["id"]), row["name"])


def _fmt_class_name(class_id: int | None, class_name: str | None) -> str:
    if class_name:
        return class_name
    if class_id is None:
        return "(класс не указан)"
    return f"(класс удалён: id={class_id})"


def _print_table(rows: list[sqlite3.Row], *, title: str) -> None:
    print(title)
    if not rows:
        print("Нет данных.")
        return

    header = ["#", "Класс", "Пользователей"]
    items: list[tuple[str, str, str]] = []
    for i, r in enumerate(rows, start=1):
        items.append(
            (
                str(i),
                _fmt_class_name(r["class_id"], r["class_name"]),
                str(r["users"]),
            )
        )

    widths = [
        max(len(header[0]), max(len(x[0]) for x in items)),
        max(len(header[1]), max(len(x[1]) for x in items)),
        max(len(header[2]), max(len(x[2]) for x in items)),
    ]

    def _line(cols: tuple[str, str, str]) -> str:
        return "  ".join(c.ljust(w) for c, w in zip(cols, widths, strict=True))

    print(_line((header[0], header[1], header[2])))
    print(_line(tuple("-" * w for w in widths)))  # type: ignore[arg-type]
    for it in items:
        print(_line(it))


def _query_participants_by_class(
    conn: sqlite3.Connection,
    *,
    boss_id: int,
    correct_only: bool,
    mode: str,
    dedup_by_name: bool,
) -> list[sqlite3.Row]:
    """
    mode:
      - "main": каждому пользователю назначается один "главный" класс (как в топах: по числу решений, тай-брейк по времени)
      - "used": пользователь считается в каждом классе, где он участвовал
    """
    where = "s.boss_id = ?"
    params: list[object] = [boss_id]
    if correct_only:
        where += " AND s.is_correct IS TRUE"

    # user_key:
    # - по умолчанию: если есть user_id — считаем по нему, иначе по имени как есть
    # - если dedup_by_name: всегда считаем по нормализованному имени (игнорируем user_id)
    user_key_expr = (
        "canon_name(s.user_name)"
        if dedup_by_name
        else "COALESCE(CAST(s.user_id AS TEXT), 'name:' || s.user_name)"
    )
    base_cte = f"""
        WITH base AS (
            SELECT
                s.class_id AS class_id,
                c.name AS class_name,
                {user_key_expr} AS user_key,
                s.solved_at AS solved_at
            FROM boss_task_solution s
            LEFT JOIN class c ON c.id = s.class_id
            WHERE {where}
        )
    """

    if mode == "used":
        sql = (
            base_cte
            + """
            SELECT
                class_id,
                class_name,
                COUNT(DISTINCT user_key) AS users
            FROM base
            GROUP BY class_id, class_name
            ORDER BY users DESC, class_name ASC
            """
        )
        return list(conn.execute(sql, params).fetchall())

    if mode == "main":
        # "главный" класс пользователя: максимальный cnt, затем более поздний last_at, затем меньший class_id
        sql = (
            base_cte
            + """
            , class_counts AS (
                SELECT
                    user_key,
                    class_id,
                    MAX(class_name) AS class_name,
                    COUNT(*) AS cnt,
                    MAX(solved_at) AS last_at
                FROM base
                GROUP BY user_key, class_id
            ),
            ranked AS (
                SELECT
                    user_key,
                    class_id,
                    class_name,
                    ROW_NUMBER() OVER (
                        PARTITION BY user_key
                        ORDER BY cnt DESC, last_at DESC, class_id ASC
                    ) AS rn
                FROM class_counts
            ),
            main_class AS (
                SELECT user_key, class_id, class_name
                FROM ranked
                WHERE rn = 1
            )
            SELECT
                class_id,
                class_name,
                COUNT(*) AS users
            FROM main_class
            GROUP BY class_id, class_name
            ORDER BY users DESC, class_name ASC
            """
        )
        return list(conn.execute(sql, params).fetchall())

    raise ValueError(f"Unknown mode: {mode}")


def _query_participant_names_by_class(
    conn: sqlite3.Connection,
    *,
    boss_id: int,
    correct_only: bool,
    mode: str,
    dedup_by_name: bool,
) -> list[sqlite3.Row]:
    """
    Возвращает строки: {class_id, class_name, display_name, user_key}
    display_name — "самое свежее" написание имени для данного (user_key, class_id).
    """
    where = "s.boss_id = ?"
    params: list[object] = [boss_id]
    if correct_only:
        where += " AND s.is_correct IS TRUE"

    user_key_expr = (
        "canon_name(s.user_name)"
        if dedup_by_name
        else "COALESCE(CAST(s.user_id AS TEXT), 'name:' || s.user_name)"
    )

    sql_base = f"""
        WITH base AS (
            SELECT
                s.class_id AS class_id,
                c.name AS class_name,
                {user_key_expr} AS user_key,
                s.user_name AS user_name_raw,
                s.solved_at AS solved_at
            FROM boss_task_solution s
            LEFT JOIN class c ON c.id = s.class_id
            WHERE {where}
        ),
        name_pick AS (
            SELECT
                class_id,
                class_name,
                user_key,
                user_name_raw AS display_name,
                ROW_NUMBER() OVER (
                    PARTITION BY class_id, user_key
                    ORDER BY solved_at DESC
                ) AS rn
            FROM base
            WHERE user_key IS NOT NULL
        ),
        latest_name AS (
            SELECT class_id, class_name, user_key, display_name
            FROM name_pick
            WHERE rn = 1
        )
    """

    if mode == "used":
        sql = (
            sql_base
            + """
            SELECT class_id, class_name, display_name, user_key
            FROM latest_name
            ORDER BY class_name ASC, display_name ASC
            """
        )
        return list(conn.execute(sql, params).fetchall())

    if mode == "main":
        sql = (
            sql_base
            + """
            , class_counts AS (
                SELECT
                    user_key,
                    class_id,
                    COUNT(*) AS cnt,
                    MAX(solved_at) AS last_at
                FROM base
                WHERE user_key IS NOT NULL
                GROUP BY user_key, class_id
            ),
            ranked AS (
                SELECT
                    user_key,
                    class_id,
                    ROW_NUMBER() OVER (
                        PARTITION BY user_key
                        ORDER BY cnt DESC, last_at DESC, class_id ASC
                    ) AS rn
                FROM class_counts
            ),
            main_class AS (
                SELECT user_key, class_id
                FROM ranked
                WHERE rn = 1
            )
            SELECT
                ln.class_id AS class_id,
                ln.class_name AS class_name,
                ln.display_name AS display_name,
                ln.user_key AS user_key
            FROM latest_name ln
            JOIN main_class mc
              ON mc.user_key = ln.user_key AND mc.class_id = ln.class_id
            ORDER BY ln.class_name ASC, ln.display_name ASC
            """
        )
        return list(conn.execute(sql, params).fetchall())

    raise ValueError(f"Unknown mode: {mode}")


def _print_names_by_class(rows: list[sqlite3.Row]) -> None:
    if not rows:
        print("\nСписки участников: нет данных.")
        return

    # группируем по class_id + class_name
    groups: dict[tuple[int | None, str | None], list[str]] = {}
    for r in rows:
        key = (r["class_id"], r["class_name"])
        groups.setdefault(key, []).append(str(r["display_name"]))

    print("\nСписки участников по классам:")
    # сортировка: по имени класса, затем по id
    def _group_sort_key(k: tuple[int | None, str | None]):
        class_id, class_name = k
        return (_fmt_class_name(class_id, class_name), class_id if class_id is not None else 10**9)

    for (class_id, class_name) in sorted(groups.keys(), key=_group_sort_key):
        names = sorted(set(groups[(class_id, class_name)]), key=lambda x: _canon_person_name(x) or x)
        print(f"\n- {_fmt_class_name(class_id, class_name)}: {len(names)}")
        for n in names:
            print(f"  {n}")


def main() -> int:
    _force_utf8_output()
    parser = argparse.ArgumentParser(
        description=(
            "Отчёт: сколько уникальных пользователей участвовали в рейд-боссе по классам "
            "(по результатам решений задач)."
        )
    )
    parser.add_argument(
        "--db",
        default=os.path.join("instance", "valera.db"),
        help="Путь к SQLite базе (по умолчанию: instance/valera.db)",
    )
    parser.add_argument(
        "--boss-id",
        type=int,
        default=None,
        help="ID босса. Если не указан — берётся активный, иначе последний.",
    )
    parser.add_argument(
        "--any",
        action="store_true",
        help="Считать участие по любым попыткам (не только по правильным решениям).",
    )
    parser.add_argument(
        "--mode",
        choices=["main", "used"],
        default="main",
        help=(
            "main: каждому пользователю назначается один главный класс; "
            "used: пользователь учитывается в каждом классе, где отвечал."
        ),
    )
    parser.add_argument(
        "--dedup-by-name",
        action="store_true",
        help=(
            "Не различать участников с одинаковыми ФИО: без учёта регистра, ё/е и некоторых форм имени "
            "(например: Ваня=Иван). В этом режиме user_id игнорируется."
        ),
    )
    parser.add_argument(
        "--list-names",
        action="store_true",
        help="Дополнительно вывести списки участников (имена) по классам.",
    )

    args = parser.parse_args()
    db_path = args.db

    if not os.path.exists(db_path):
        print(f"База не найдена: {db_path}")
        return 2

    conn = _connect(db_path)
    try:
        for t in ("boss", "boss_task_solution", "class"):
            if not _table_exists(conn, t):
                print(f"В базе нет таблицы `{t}`. Проверьте, что это правильная база: {db_path}")
                return 2

        boss: BossInfo | None
        if args.boss_id is not None:
            boss = _get_boss_by_id(conn, args.boss_id)
            if boss is None:
                print(f"Босс с id={args.boss_id} не найден.")
                return 2
        else:
            boss = _get_default_boss(conn)
            if boss is None:
                print("В базе нет ни одного босса.")
                return 2

        correct_only = not bool(args.any)
        rows = _query_participants_by_class(
            conn,
            boss_id=boss.id,
            correct_only=correct_only,
            mode=args.mode,
            dedup_by_name=bool(args.dedup_by_name),
        )

        total_user_key_expr = (
            "canon_name(user_name)"
            if args.dedup_by_name
            else "COALESCE(CAST(user_id AS TEXT), 'name:' || user_name)"
        )
        total_users_row = conn.execute(
            f"""
            SELECT COUNT(DISTINCT {total_user_key_expr}) AS total_users
            FROM boss_task_solution
            WHERE boss_id = ?
            {"AND is_correct IS TRUE" if correct_only else ""}
            """,
            (boss.id,),
        ).fetchone()
        total_users = int(total_users_row["total_users"] if total_users_row else 0)

        title = (
            f"Босс: id={boss.id}"
            + (f", name={boss.name}" if boss.name else "")
            + f"\nРежим: {'только правильные решения' if correct_only else 'любые попытки'}; "
            + f"классы: {args.mode}"
            + (f"; дедуп: по имени" if args.dedup_by_name else "")
            + f"\nВсего уникальных участников: {total_users}\n"
        )
        _print_table(rows, title=title)

        if args.list_names:
            name_rows = _query_participant_names_by_class(
                conn,
                boss_id=boss.id,
                correct_only=correct_only,
                mode=args.mode,
                dedup_by_name=bool(args.dedup_by_name),
            )
            _print_names_by_class(name_rows)
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())

