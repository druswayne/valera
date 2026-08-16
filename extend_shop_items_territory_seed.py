import argparse
import json
from pathlib import Path


def parse_args():
    p = argparse.ArgumentParser(description="Extend shop_items_territory_seed.json with more buffs/debuffs")
    p.add_argument("--json-path", default="shop_items_territory_seed.json", help="Path to seed JSON")
    p.add_argument("--max-add", type=int, default=0, help="Max number of new items to add (0 = all)")
    return p.parse_args()


def main():
    args = parse_args()
    root_dir = Path(__file__).resolve().parent
    json_path = (root_dir / args.json_path).resolve()

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("Expected JSON array at root")

    existing_names = {it.get("name") for it in data if isinstance(it, dict)}

    # Добавляем новые предметы с большей вариативностью: 2 эффекта в одном предмете,
    # разные комбинации effect_type/target/duration.
    # Замечание: effect_type='current_energy' реализован в app.py только для target self и clan,
    # поэтому для region используем только damage/defense/xp_reward/nums_reward.
    new_items = [
        # --- ENHANCEMENTS (баффы) ---
        {
            "name": "Адреналин форпоста",
            "description": "Личный рывок: вы моментально восстанавливаете энергию и усиливаете атаку на короткий период.",
            "category": "enhancement",
            "price": 420,
            "effects": [
                {"effect_type": "current_energy", "percent_change": 35, "target": "self", "duration_minutes": None},
                {"effect_type": "damage", "percent_change": 18, "target": "self", "duration_minutes": 30},
            ],
        },
        {
            "name": "Железная стойка",
            "description": "Защитный импульс: повышает вашу защиту и даёт небольшой бонус к опыту за задачи.",
            "category": "enhancement",
            "price": 520,
            "effects": [
                {"effect_type": "defense", "percent_change": 18, "target": "self", "duration_minutes": 45},
                {"effect_type": "xp_reward", "percent_change": 15, "target": "self", "duration_minutes": 45},
            ],
        },
        {
            "name": "Клановый таран",
            "description": "Слаженное наступление: клан получает бонус и к атаке, и к защите.",
            "category": "enhancement",
            "price": 3800,
            "effects": [
                {"effect_type": "damage", "percent_change": 16, "target": "clan", "duration_minutes": 60},
                {"effect_type": "defense", "percent_change": 12, "target": "clan", "duration_minutes": 60},
            ],
        },
        {
            "name": "Пробуждение тактики",
            "description": "Учебный штурм: усиливает опыт клана и повышает награды в Нумах.",
            "category": "enhancement",
            "price": 4200,
            "effects": [
                {"effect_type": "xp_reward", "percent_change": 25, "target": "clan", "duration_minutes": 60},
                {"effect_type": "nums_reward", "percent_change": 15, "target": "clan", "duration_minutes": 60},
            ],
        },
        {
            "name": "Экономика обучения",
            "description": "Провинциальный резонанс: за задачи в регионе больше опыта и Нумов.",
            "category": "enhancement",
            "price": 3000,
            "effects": [
                {"effect_type": "xp_reward", "percent_change": 18, "target": "region", "duration_minutes": 45},
                {"effect_type": "nums_reward", "percent_change": 18, "target": "region", "duration_minutes": 45},
            ],
        },
        {
            "name": "Пыл наступления",
            "description": "Фронтовое воодушевление: усиливает атаку в регионе и добавляет награду в Нумах.",
            "category": "enhancement",
            "price": 2600,
            "effects": [
                {"effect_type": "damage", "percent_change": 22, "target": "region", "duration_minutes": 45},
                {"effect_type": "nums_reward", "percent_change": 12, "target": "region", "duration_minutes": 45},
            ],
        },
        {
            "name": "Аура командования",
            "description": "Клановый приток сил: восстанавливает текущую энергию всем в клане и повышает защиту на время атаки.",
            "category": "enhancement",
            "price": 3400,
            "effects": [
                {"effect_type": "current_energy", "percent_change": 60, "target": "clan", "duration_minutes": None},
                {"effect_type": "defense", "percent_change": 14, "target": "clan", "duration_minutes": 45},
            ],
        },
        {
            "name": "Заряд ритма",
            "description": "Бодрость перед боем: ускоряет обучение и усиливает награды за задачи в регионе.",
            "category": "enhancement",
            "price": 2300,
            "effects": [
                {"effect_type": "xp_reward", "percent_change": 20, "target": "region", "duration_minutes": 60},
                {"effect_type": "nums_reward", "percent_change": 20, "target": "region", "duration_minutes": 60},
            ],
        },
        {
            "name": "Северная фортуна",
            "description": "Региональная удача: повышает Нумы за задачи и уменьшает потери при защите.",
            "category": "enhancement",
            "price": 2400,
            "effects": [
                {"effect_type": "nums_reward", "percent_change": 24, "target": "region", "duration_minutes": 60},
                {"effect_type": "defense", "percent_change": 10, "target": "region", "duration_minutes": 60},
            ],
        },
        {
            "name": "Благословение клана",
            "description": "Клановая поддержка: повышает опыт и защиту на время штурма.",
            "category": "enhancement",
            "price": 4400,
            "effects": [
                {"effect_type": "xp_reward", "percent_change": 22, "target": "clan", "duration_minutes": 60},
                {"effect_type": "defense", "percent_change": 14, "target": "clan", "duration_minutes": 60},
            ],
        },
        {
            "name": "Крепость региона",
            "description": "Областная оборона: серьёзно укрепляет защиту в выбранной области.",
            "category": "enhancement",
            "price": 3600,
            "effects": [
                {"effect_type": "defense", "percent_change": 30, "target": "region", "duration_minutes": 60},
            ],
        },
        {
            "name": "Поддержка экспедиции",
            "description": "Командный бонус: даёт клану и опыт, и Нумы за задачи на этой территории.",
            "category": "enhancement",
            "price": 4100,
            "effects": [
                {"effect_type": "xp_reward", "percent_change": 22, "target": "region", "duration_minutes": 60},
                {"effect_type": "nums_reward", "percent_change": 15, "target": "region", "duration_minutes": 60},
            ],
        },

        # --- CURSES (дебаффы) ---
        {
            "name": "Яд неудачи",
            "description": "Клановая порча: повышает урон против клана-цели (для атакующих) и ухудшает их защиту.",
            "category": "curse",
            "price": 4700,
            "effects": [
                {"effect_type": "damage", "percent_change": 18, "target": "clan", "duration_minutes": 60},
                {"effect_type": "defense", "percent_change": 12, "target": "clan", "duration_minutes": 60},
            ],
        },
        {
            "name": "Сломанная воля",
            "description": "Дебафф опыта: клан-цель получает меньше опыта за задачи.",
            "category": "curse",
            "price": 3900,
            "effects": [
                {"effect_type": "xp_reward", "percent_change": 28, "target": "clan", "duration_minutes": 60},
            ],
        },
        {
            "name": "Опустошение казны",
            "description": "Клановая порча экономики: за задачи платят заметно меньше Нумов.",
            "category": "curse",
            "price": 5200,
            "effects": [
                {"effect_type": "nums_reward", "percent_change": 28, "target": "clan", "duration_minutes": 120},
            ],
        },
        {
            "name": "Туман учёбы",
            "description": "Областное проклятие: в регионе сложнее развиваться — меньше опыта за задачи.",
            "category": "curse",
            "price": 2500,
            "effects": [
                {"effect_type": "xp_reward", "percent_change": 26, "target": "region", "duration_minutes": 60},
            ],
        },
        {
            "name": "Обескровленный фронт",
            "description": "Областная порча: снижает урон и ухудшает экономику региона.",
            "category": "curse",
            "price": 3000,
            "effects": [
                {"effect_type": "damage", "percent_change": 22, "target": "region", "duration_minutes": 45},
                {"effect_type": "nums_reward", "percent_change": 12, "target": "region", "duration_minutes": 45},
            ],
        },
        {
            "name": "Разбитые щиты гарнизона",
            "description": "Областной дебафф: защитники в регионе теряют устойчивость.",
            "category": "curse",
            "price": 3100,
            "effects": [
                {"effect_type": "defense", "percent_change": 26, "target": "region", "duration_minutes": 45},
            ],
        },
        {
            "name": "Клановый спад",
            "description": "Порча для атакующего клана: дебафф и урона, и защиты на время размена.",
            "category": "curse",
            "price": 4600,
            "effects": [
                {"effect_type": "damage", "percent_change": 14, "target": "clan", "duration_minutes": 45},
                {"effect_type": "defense", "percent_change": 18, "target": "clan", "duration_minutes": 45},
            ],
        },
        {
            "name": "Разлад обучения",
            "description": "Сочетание дебаффов: снижает и опыт, и Нумы в регионе.",
            "category": "curse",
            "price": 2700,
            "effects": [
                {"effect_type": "xp_reward", "percent_change": 18, "target": "region", "duration_minutes": 60},
                {"effect_type": "nums_reward", "percent_change": 18, "target": "region", "duration_minutes": 60},
            ],
        },
        {
            "name": "Истощение застав",
            "description": "Клановое подавление энергии: мгновенно уменьшает текущую энергию и мешает держать линию.",
            "category": "curse",
            "price": 4100,
            "effects": [
                {"effect_type": "current_energy", "percent_change": 45, "target": "clan", "duration_minutes": None},
                {"effect_type": "defense", "percent_change": 10, "target": "clan", "duration_minutes": 30},
            ],
        },
        {
            "name": "Плохая примета штурма",
            "description": "Региональный дебафф: атакующие получают меньше выгоды, и урон падает.",
            "category": "curse",
            "price": 2400,
            "effects": [
                {"effect_type": "damage", "percent_change": 20, "target": "region", "duration_minutes": 60},
            ],
        },
        {
            "name": "Кошмар гарнизона",
            "description": "Сильное областное проклятие: резко снижает защиту и урезает награды в Нумах.",
            "category": "curse",
            "price": 5400,
            "effects": [
                {"effect_type": "defense", "percent_change": 30, "target": "region", "duration_minutes": 60},
                {"effect_type": "nums_reward", "percent_change": 18, "target": "region", "duration_minutes": 60},
            ],
        },
        {
            "name": "Порча координации",
            "description": "Слабость клана: снижает и урон, и защиту — клан легче пробить.",
            "category": "curse",
            "price": 4700,
            "effects": [
                {"effect_type": "damage", "percent_change": 18, "target": "clan", "duration_minutes": 45},
                {"effect_type": "defense", "percent_change": 18, "target": "clan", "duration_minutes": 45},
            ],
        },
    ]

    to_add = []
    for it in new_items:
        if it["name"] in existing_names:
            continue
        to_add.append(it)
        if args.max_add and args.max_add > 0 and len(to_add) >= args.max_add:
            break

    if not to_add:
        print("No new items to add (all names already exist).")
        return 0

    data.extend(to_add)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"Added {len(to_add)} new items to {json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

