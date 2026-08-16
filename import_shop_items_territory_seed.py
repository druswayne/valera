import argparse
import json
from pathlib import Path


def parse_args():
    p = argparse.ArgumentParser(description="Import/update shop items for territory from JSON seed")
    p.add_argument("--json-path", default="shop_items_territory_seed.json", help="Path to seed JSON")
    p.add_argument("--dry-run", action="store_true", help="Validate JSON only, do not touch DB")
    return p.parse_args()


def main():
    args = parse_args()
    root_dir = Path(__file__).resolve().parent
    json_path = (root_dir / args.json_path).resolve()

    if not json_path.exists():
        raise SystemExit(f"JSON file not found: {json_path}")

    from seed_shop_items_territory import load_seed_items, upsert_shop_item
    from app import app, db

    items = load_seed_items(str(json_path))

    if args.dry_run:
        print(f"[dry-run] items validated: {len(items)}")
        return 0

    with app.app_context():
        for item_data in items:
            upsert_shop_item(item_data)
        db.session.commit()

    print(f"Import finished. processed={len(items)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

