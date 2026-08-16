import argparse
import json
import math
from pathlib import Path


SLOTS = ["helmet", "chest", "pants", "gloves", "boots", "weapon_main", "weapon_off"]
PRIMARY_SLOTS_OFFENSE = {"weapon_main", "gloves"}
PRIMARY_SLOTS_DEFENSE = {"weapon_off", "chest", "pants", "helmet"}


def _int_round(x: float) -> int:
    # Always round to integer percent_change (app stores floats but UI expects nice ints usually)
    return int(round(x))


def parse_args():
    p = argparse.ArgumentParser(description="Diversify equipment bonuses in equipment_sets_by_grade.json")
    p.add_argument("--json-path", default="equipment_sets_by_grade.json", help="Path to JSON source file")
    p.add_argument("--dry-run", action="store_true", help="Validate/preview changes only")
    p.add_argument("--only-grade", default="", help="Optional: limit to one grade: d/c/b/a/s")
    return p.parse_args()


def main():
    args = parse_args()
    root_dir = Path(__file__).resolve().parent
    json_path = (root_dir / args.json_path).resolve()

    with open(json_path, "r", encoding="utf-8") as f:
        payload = json.load(f)

    if "grades" not in payload or not isinstance(payload["grades"], list):
        raise ValueError("Invalid JSON: missing 'grades' list")

    # Compute base reward values from current data (so changes are consistent with your current magnitudes).
    base_reward = {
        "d": {"xp_reward": 1, "nums_reward": 1},
        "c": {"xp_reward": 4, "nums_reward": 4},
        "b": {"xp_reward": 8, "nums_reward": 8},
        "a": {"xp_reward": 14, "nums_reward": 14},
        "s": {"xp_reward": 14, "nums_reward": 12},
    }
    # override with actual averages if available
    tmp = {gr: {"xp_reward": [], "nums_reward": []} for gr in base_reward.keys()}
    for g in payload["grades"]:
        gr = (g.get("grade") or "").strip().lower()
        if gr not in tmp:
            continue
        for st in g.get("sets", []):
            for it in st.get("items", []):
                for e in it.get("effects", []):
                    et = e.get("effect_type")
                    pc = e.get("percent_change")
                    if et in ("xp_reward", "nums_reward") and isinstance(pc, (int, float)):
                        tmp[gr][et].append(float(pc))
    for gr in tmp:
        for et in ("xp_reward", "nums_reward"):
            arr = tmp[gr][et]
            if arr:
                base_reward[gr][et] = _int_round(sum(arr) / len(arr))

    # Compute base positive values for primary stats to prevent "primary becomes 0"
    # (e.g., if previous data already has zeros/negatives).
    base_primary = {gr: {"damage": 1, "defense": 1, "max_energy": 1} for gr in base_reward.keys()}
    prim_tmp = {gr: {"damage": [], "defense": [], "max_energy": []} for gr in base_reward.keys()}
    for g in payload["grades"]:
        gr = (g.get("grade") or "").strip().lower()
        if gr not in prim_tmp:
            continue
        for st in g.get("sets", []):
            for it in st.get("items", []):
                for e in it.get("effects", []):
                    et = e.get("effect_type")
                    pc = e.get("percent_change")
                    if et in ("damage", "defense", "max_energy") and isinstance(pc, (int, float)):
                        pc_f = float(pc)
                        if pc_f > 0:
                            prim_tmp[gr][et].append(pc_f)
    for gr in prim_tmp:
        for et in ("damage", "defense", "max_energy"):
            arr = prim_tmp[gr][et]
            if arr:
                base_primary[gr][et] = _int_round(sum(arr) / len(arr))

    changed_items = 0
    negative_count = 0
    s_three_effects = 0
    before_types = {}
    after_types = {}

    for g in payload["grades"]:
        grade = (g.get("grade") or "").strip().lower()
        if not grade:
            continue
        if args.only_grade and grade != args.only_grade.strip().lower():
            continue

        sets = g.get("sets", [])
        for set_index, st in enumerate(sets):
            items = st.get("items", [])
            for slot_index, it in enumerate(items):
                slot = (it.get("slot") or "").strip().lower()
                if slot not in SLOTS:
                    continue

                before = tuple(sorted((e.get("effect_type") for e in it.get("effects", []))))
                before_types[(grade, st.get("set_name"), it.get("name"))] = before

                effects_map = {}
                for e in it.get("effects", []):
                    et = e.get("effect_type")
                    pc = e.get("percent_change")
                    if et in ("damage", "defense", "max_energy", "xp_reward", "nums_reward") and isinstance(pc, (int, float)):
                        effects_map[et] = float(pc)

                effect_types = set(effects_map.keys())
                cur_effect_count = len(effect_types)

                # Determine primary positive stat type
                primary_type = None
                primary_value = 0.0
                if grade == "s":
                    if slot == "weapon_main":
                        primary_type = "damage" if "damage" in effects_map else None
                    elif slot == "weapon_off":
                        primary_type = "defense" if "defense" in effects_map else None
                    elif slot in ("boots", "pants"):
                        primary_type = "max_energy" if "max_energy" in effects_map else None

                if primary_type is None:
                    # choose the largest positive among relevant types (prefer non-zero primary)
                    for candidate in ("damage", "defense", "max_energy"):
                        if candidate in effects_map:
                            cand_val = float(effects_map[candidate])
                            if cand_val > 0 and (primary_type is None or cand_val >= primary_value):
                                primary_type = candidate
                                primary_value = cand_val

                if primary_type is None:
                    # nothing to do
                    continue

                slot_idx = SLOTS.index(slot)

                new_map = dict(effects_map)

                if grade == "s":
                    # Ensure we never turn primary into 0 for weapon_main/offense.
                    if primary_value <= 0:
                        primary_value = float(base_primary[grade][primary_type])
                        effects_map[primary_type] = primary_value

                    # S: aim for 3 effects per item: primary + reward + tradeoff negative
                    # 1) Boost primary a bit (varies by set_index parity)
                    primary_mult = 1.15 if (set_index + slot_idx) % 2 == 0 else 1.10
                    new_map[primary_type] = float(_int_round(primary_value * primary_mult))

                    # 2) Reward type: alternate by slot and set_index
                    #    - offensive slots prefer xp_reward
                    #    - armor-ish slots prefer nums_reward
                    if slot in ("weapon_main", "gloves"):
                        reward_type = "xp_reward"
                    elif slot in ("weapon_off", "chest", "pants"):
                        reward_type = "nums_reward"
                    else:
                        reward_type = "xp_reward" if (set_index % 2 == 0) else "nums_reward"

                    reward_val_base = base_reward[grade][reward_type]
                    reward_gain = 1.10 if (set_index + slot_idx) % 2 == 0 else 1.00
                    new_map[reward_type] = float(_int_round(reward_val_base * reward_gain))

                    # 3) Tradeoff: reduce the opposite stat
                    if slot in PRIMARY_SLOTS_OFFENSE:
                        trade_type = "defense"
                        if trade_type == primary_type:
                            trade_type = "max_energy"
                    elif slot in PRIMARY_SLOTS_DEFENSE:
                        trade_type = "damage"
                        if trade_type == primary_type:
                            trade_type = "max_energy"
                    else:
                        trade_type = "damage" if primary_type == "max_energy" else "defense"
                        if trade_type == primary_type:
                            trade_type = "max_energy"

                    # negative value magnitude depends on primary_value and set_index
                    neg_frac = 0.12 if (set_index % 2 == 0) else 0.18
                    neg_value = -max(1.0, abs(primary_value) * neg_frac)
                    new_map[trade_type] = float(_int_round(neg_value))

                    # Finalize: keep only 3 effect types (primary/reward/tradeoff) for clarity
                    keep = {primary_type, reward_type, trade_type}
                    it["effects"] = [
                        {"effect_type": et, "percent_change": int(new_map[et])}
                        for et in sorted(keep)
                    ]

                else:
                    # For d/c/b/a: increase variety by adding a reward to some 1-effect items
                    if cur_effect_count == 1 and primary_type in ("damage", "defense", "max_energy"):
                        # add only on ~half items for variety control
                        if (set_index + slot_idx) % 2 == 1:
                            it["effects"] = it.get("effects", [])
                            continue

                        # reward type by slot
                        if slot in ("weapon_main", "gloves"):
                            reward_type = "xp_reward"
                        elif slot in ("weapon_off", "boots", "pants", "chest"):
                            reward_type = "nums_reward"
                        else:
                            reward_type = "xp_reward"

                        reward_val = base_reward[grade][reward_type]
                        it["effects"] = [
                            {"effect_type": primary_type, "percent_change": int(round(primary_value))},
                            {"effect_type": reward_type, "percent_change": int(reward_val)},
                        ]

                # Track stats
                after = tuple(sorted((e.get("effect_type") for e in it.get("effects", []))))
                after_types[(grade, st.get("set_name"), it.get("name"))] = after

                if tuple(sorted(e.get("effect_type") for e in it.get("effects", []))) != before:
                    changed_items += 1

                neg = any(float(e.get("percent_change", 0)) < 0 for e in it.get("effects", []))
                if neg:
                    negative_count += 1
                if grade == "s" and len(it.get("effects", [])) >= 3:
                    s_three_effects += 1

    if args.dry_run:
        print(
            f"[dry-run] changed_items={changed_items}, negative_items={negative_count}, s_items_with_3plus={s_three_effects}"
        )
        return 0

    # Write back
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=True, indent=2)
    print(
        f"Done. changed_items={changed_items}, negative_items={negative_count}, s_items_with_3plus={s_three_effects}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

