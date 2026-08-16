from __future__ import annotations

import csv
from datetime import datetime
import sys
import os
import io
import contextlib
from typing import Any

USER_IDS = [4, 7, 8, 10, 11, 13, 14, 16, 17, 19, 20,21, 23,25, 31, 36, 44]


def _fmt_dt(dt: datetime | None) -> str:
    if not dt:
        return ""
    # как в уже существующих экспортных CSV (с пробелом, а не ISO T)
    return dt.strftime("%Y-%m-%d %H:%M:%S.%f")


def _infer_class_for_reward(
    reward: Any,
    *,
    db: Any,
    Class: Any,
    BossTaskSolution: Any,
) -> tuple[int | None, str | None]:
    """
    Для старых записей, где class_id не был сохранён, пытаемся восстановить класс
    по последнему правильному решению пользователя по этому боссу (до момента дропа).
    """
    if reward.class_id:
        class_obj = db.session.get(Class, reward.class_id)
        return reward.class_id, (class_obj.name if class_obj else None)

    inferred_solution = (
        BossTaskSolution.query.filter_by(boss_id=reward.boss_id, user_id=reward.user_id, is_correct=True)
        .filter(BossTaskSolution.solved_at <= reward.received_at)
        .order_by(BossTaskSolution.solved_at.desc())
        .first()
    )
    if not inferred_solution:
        return None, None

    inferred_class = db.session.get(Class, inferred_solution.class_id) if inferred_solution.class_id else None
    return inferred_solution.class_id, (inferred_class.name if inferred_class else None)


def _safe_output_path(path: str) -> str:
    """
    Если файл уже открыт (например, в Excel) и заблокирован, не падаем,
    а создаём новый файл рядом с таймстампом.
    """
    try:
        # Проверяем, что можно открыть на запись/допись
        with open(path, "a", encoding="utf-8"):
            return path
    except PermissionError:
        root, ext = os.path.splitext(path)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{root}_{ts}{ext}"


def main() -> None:
    out_path = _safe_output_path("exports/drops_selected_users.csv")
    summary_path = _safe_output_path("exports/drops_selected_users_summary.csv")

    # На Windows консоль часто не UTF-8. Чтобы не было "кракозябр" — печатаем только ASCII.
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # py3.7+
    except Exception:
        pass

    # В app.py есть русские print() при миграциях/инициализации.
    # Глушим stdout/stderr на время импорта, чтобы не получать "кракозябры" в консоли.
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        from app import app, db, BossDropReward, BossTaskSolution, Class, BossUser  # type: ignore

    with app.app_context():
        rewards = (
            BossDropReward.query.filter(BossDropReward.user_id.in_(USER_IDS))
            .order_by(BossDropReward.user_id.asc(), BossDropReward.received_at.asc(), BossDropReward.id.asc())
            .all()
        )

        # Excel на Windows надёжнее открывает UTF-8 CSV, если есть BOM (utf-8-sig).
        with open(out_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f, delimiter=";")
            writer.writerow(
                [
                    "user_id",
                    "user_name",
                    "drop_name",
                    "received_at",
                    "boss_id",
                    "task_id",
                    "class_id",
                    "class_name",
                    "reward_id",
                    "drop_id",
                ]
            )

            for r in rewards:
                class_id, class_name = _infer_class_for_reward(
                    r,
                    db=db,
                    Class=Class,
                    BossTaskSolution=BossTaskSolution,
                )
                writer.writerow(
                    [
                        r.user_id,
                        r.user.name if r.user else "",
                        r.drop.name if r.drop else "",
                        _fmt_dt(r.received_at),
                        r.boss_id,
                        r.task_id if r.task_id is not None else "",
                        class_id if class_id is not None else "",
                        class_name if class_name is not None else "",
                        r.id,
                        r.drop_id,
                    ]
                )

        # Сводка "для каждого пользователя" (включая тех, у кого 0 дропов)
        counts: dict[int, int] = {uid: 0 for uid in USER_IDS}
        for r in rewards:
            counts[r.user_id] = counts.get(r.user_id, 0) + 1

        users = BossUser.query.filter(BossUser.id.in_(USER_IDS)).all()
        users_by_id = {u.id: u for u in users}

        with open(summary_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f, delimiter=";")
            writer.writerow(["user_id", "user_name", "drops_count", "status"])
            for uid in USER_IDS:
                u = users_by_id.get(uid)
                if not u:
                    writer.writerow([uid, "", counts.get(uid, 0), "user_not_found"])
                else:
                    writer.writerow([uid, u.name, counts.get(uid, 0), "ok"])

    print(f"OK: {out_path}")
    print(f"OK: {summary_path}")


if __name__ == "__main__":
    main()
