"""
Простой бэкап и восстановление PostgreSQL из SQLALCHEMY_DATABASE_URI (.env).

Бэкап: читает все таблицы схемы public и сохраняет в JSON (gzip).
Восстановление: очищает таблицы и заливает данные обратно.

Примеры:
  python backup_db.py backup
  python backup_db.py backup -o backups/my_backup.json.gz
  python backup_db.py restore backups/valera_20260615_110809.json.gz --yes
"""
from __future__ import annotations

import argparse
import base64
import gzip
import json
import os
import sys
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID

from dotenv import load_dotenv
from sqlalchemy import MetaData, create_engine, inspect, text
from sqlalchemy.dialects.postgresql import BYTEA
from sqlalchemy.engine import Engine
from sqlalchemy.sql.sqltypes import LargeBinary

ROOT_DIR = Path(__file__).resolve().parent
DEFAULT_BACKUP_DIR = ROOT_DIR / "backups"
BATCH_SIZE = 500


def _clean_uri(uri: str) -> str:
    return uri.strip().strip("'").strip('"')


def get_database_uri() -> str:
    dotenv_path = ROOT_DIR / ".env"
    if dotenv_path.exists():
        load_dotenv(dotenv_path=str(dotenv_path), override=False)
    else:
        load_dotenv()

    uri = _clean_uri(os.getenv("SQLALCHEMY_DATABASE_URI", ""))
    if not uri:
        print(
            "Не задана переменная SQLALCHEMY_DATABASE_URI в .env",
            file=sys.stderr,
        )
        sys.exit(1)
    return uri


def create_db_engine() -> Engine:
    return create_engine(get_database_uri())


def _encode_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (bytes, bytearray, memoryview)):
        return {
            "__type__": "bytes",
            "value": base64.b64encode(bytes(value)).decode("ascii"),
        }
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, datetime):
        return {"__type__": "datetime", "value": value.isoformat()}
    if isinstance(value, date):
        return {"__type__": "date", "value": value.isoformat()}
    if isinstance(value, Decimal):
        return {"__type__": "decimal", "value": str(value)}
    if isinstance(value, bytes):
        return {
            "__type__": "bytes",
            "value": base64.b64encode(value).decode("ascii"),
        }
    if isinstance(value, UUID):
        return {"__type__": "uuid", "value": str(value)}
    if isinstance(value, (list, dict)):
        return value
    return str(value)


def _decode_value(value: Any) -> Any:
    if not isinstance(value, dict) or "__type__" not in value:
        return value

    kind = value["__type__"]
    raw = value["value"]
    if kind == "datetime":
        return datetime.fromisoformat(raw)
    if kind == "date":
        return date.fromisoformat(raw)
    if kind == "decimal":
        return Decimal(raw)
    if kind == "bytes":
        return base64.b64decode(raw.encode("ascii"))
    if kind == "uuid":
        return UUID(raw)
    return raw


def _decode_row(row: dict[str, Any]) -> dict[str, Any]:
    return {key: _decode_value(val) for key, val in row.items()}


def _is_binary_column(column) -> bool:
    return isinstance(column.type, (LargeBinary, BYTEA))


def _coerce_binary_value(value: Any) -> bytes | None:
    if value is None:
        return None
    if isinstance(value, (bytes, bytearray, memoryview)):
        return bytes(value)
    if isinstance(value, str):
        # Старые бэкапы: memoryview попадал в JSON как "<memory at 0x...>"
        if value.startswith("<memory at"):
            return b""
        try:
            return base64.b64decode(value.encode("ascii"))
        except Exception:
            return value.encode("utf-8")
    return bytes(value)


def _coerce_row_for_table(row: dict[str, Any], table) -> dict[str, Any]:
    coerced: dict[str, Any] = {}
    for column in table.columns:
        if column.name not in row:
            continue
        value = row[column.name]
        if _is_binary_column(column):
            coerced[column.name] = _coerce_binary_value(value)
        else:
            coerced[column.name] = value
    return coerced


def _public_tables(engine: Engine) -> list[str]:
    inspector = inspect(engine)
    if engine.dialect.name == "postgresql":
        return sorted(inspector.get_table_names(schema="public"))
    return sorted(inspector.get_table_names())


def backup_database(output_path: Path) -> None:
    engine = create_db_engine()
    tables = _public_tables(engine)
    if not tables:
        print("Таблицы не найдены.", file=sys.stderr)
        sys.exit(1)

    payload: dict[str, Any] = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "dialect": engine.dialect.name,
        "database_uri_masked": _mask_uri(get_database_uri()),
        "tables": {},
    }

    with engine.connect() as conn:
        for table_name in tables:
            result = conn.execute(text(f'SELECT * FROM "{table_name}"'))
            columns = list(result.keys())
            rows = [
                {col: _encode_value(row[idx]) for idx, col in enumerate(columns)}
                for row in result.fetchall()
            ]
            payload["tables"][table_name] = {
                "columns": columns,
                "rows": rows,
            }
            print(f"  {table_name}: {len(rows)} строк")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")

    if output_path.suffix == ".gz" or str(output_path).endswith(".json.gz"):
        with gzip.open(output_path, "wb") as f:
            f.write(data)
    else:
        output_path.write_bytes(data)

    total_rows = sum(len(t["rows"]) for t in payload["tables"].values())
    print(f"\nБэкап сохранён: {output_path}")
    print(f"Таблиц: {len(tables)}, строк: {total_rows}")


def _mask_uri(uri: str) -> str:
    if "@" not in uri:
        return uri
    prefix, suffix = uri.split("@", 1)
    if "://" in prefix:
        scheme, creds = prefix.split("://", 1)
        if ":" in creds:
            user = creds.split(":", 1)[0]
            return f"{scheme}://{user}:***@{suffix}"
    return f"***@{suffix}"


def _load_backup(path: Path) -> dict[str, Any]:
    if not path.exists():
        print(f"Файл бэкапа не найден: {path}", file=sys.stderr)
        sys.exit(1)

    if path.suffix == ".gz" or str(path).endswith(".json.gz"):
        with gzip.open(path, "rt", encoding="utf-8") as f:
            return json.load(f)
    return json.loads(path.read_text(encoding="utf-8"))


def restore_database(backup_path: Path, *, skip_confirm: bool) -> None:
    payload = _load_backup(backup_path)
    tables_data: dict[str, Any] = payload.get("tables", {})
    if not tables_data:
        print("В бэкапе нет данных.", file=sys.stderr)
        sys.exit(1)

    engine = create_db_engine()
    table_names = sorted(tables_data.keys())
    total_rows = sum(len(t.get("rows", [])) for t in tables_data.values())
    existing_tables = set(_public_tables(engine))
    tables_to_restore = [name for name in table_names if name in existing_tables]
    missing_tables = [name for name in table_names if name not in existing_tables]

    print(f"Бэкап от: {payload.get('created_at', '?')}")
    print(f"Таблиц: {len(table_names)}, строк: {total_rows}")
    print(f"Источник: {payload.get('database_uri_masked', '?')}")
    print(f"Целевая БД: {_mask_uri(get_database_uri())}")

    if missing_tables:
        print(f"\nВ целевой БД нет {len(missing_tables)} таблиц из бэкапа (будут пропущены):")
        for name in missing_tables:
            row_count = len(tables_data[name].get("rows", []))
            note = f", {row_count} строк потеряно" if row_count else ""
            print(f"  - {name}{note}")
        print("Подсказка: сначала запустите app.py — он создаст недостающие таблицы из моделей.")

    if not tables_to_restore:
        print("Нет общих таблиц для восстановления.", file=sys.stderr)
        sys.exit(1)

    if not skip_confirm:
        answer = input(
            "\nВНИМАНИЕ: все данные в этих таблицах будут удалены и заменены. "
            "Продолжить? [yes/N]: "
        ).strip().lower()
        if answer != "yes":
            print("Отменено.")
            return

    metadata = MetaData()
    metadata.reflect(bind=engine, schema="public" if engine.dialect.name == "postgresql" else None)

    with engine.begin() as conn:
        if engine.dialect.name == "postgresql":
            conn.execute(text("SET session_replication_role = replica"))

        quoted = ", ".join(f'"{name}"' for name in tables_to_restore)
        conn.execute(text(f"TRUNCATE TABLE {quoted} RESTART IDENTITY CASCADE"))

        for table_name in tables_to_restore:
            table_info = tables_data[table_name]
            rows = [_decode_row(row) for row in table_info.get("rows", [])]
            if not rows:
                print(f"  {table_name}: 0 строк")
                continue

            table = metadata.tables.get(table_name)
            if table is None:
                if engine.dialect.name == "postgresql":
                    table = metadata.tables.get(f"public.{table_name}")
            if table is None:
                print(f"  {table_name}: пропуск (таблица не найдена в БД)", file=sys.stderr)
                continue

            prepared_rows = [
                _coerce_row_for_table(row, table)
                for row in rows
            ]

            for start in range(0, len(prepared_rows), BATCH_SIZE):
                chunk = prepared_rows[start : start + BATCH_SIZE]
                conn.execute(table.insert(), chunk)

            print(f"  {table_name}: {len(rows)} строк")

        if engine.dialect.name == "postgresql":
            conn.execute(text("SET session_replication_role = DEFAULT"))

    print(f"\nВосстановление завершено из {backup_path}")


def _default_backup_path() -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return DEFAULT_BACKUP_DIR / f"valera_{ts}.json.gz"


def main() -> None:
    parser = argparse.ArgumentParser(description="Бэкап и восстановление БД Valera")
    subparsers = parser.add_subparsers(dest="command", required=True)

    backup_parser = subparsers.add_parser("backup", help="Создать бэкап")
    backup_parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Путь к файлу бэкапа (.json или .json.gz)",
    )

    restore_parser = subparsers.add_parser("restore", help="Восстановить из бэкапа")
    restore_parser.add_argument("backup_file", type=Path, help="Файл бэкапа")
    restore_parser.add_argument(
        "--yes",
        action="store_true",
        help="Не спрашивать подтверждение",
    )

    args = parser.parse_args()

    if args.command == "backup":
        output = args.output or _default_backup_path()
        print("Создаю бэкап...")
        backup_database(output.resolve())
    elif args.command == "restore":
        restore_database(args.backup_file.resolve(), skip_confirm=args.yes)


if __name__ == "__main__":
    main()
