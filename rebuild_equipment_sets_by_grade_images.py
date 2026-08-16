import argparse
import json
import re
from pathlib import Path


SLOT_ORDER = ["helmet", "chest", "pants", "gloves", "boots", "weapon_main", "weapon_off"]


def _normalize_tokens(s: str) -> list[str]:
    s = (s or "").lower()
    s = re.sub(r"[^a-z0-9]+", " ", s).strip()
    out: list[str] = []
    for w in s.split():
        # light stemming for common plural forms used in filenames
        if w.endswith("gauntlets"):
            w = w[:-1]  # gauntlets -> gauntlet
        elif w.endswith("gauntlet"):
            pass
        elif w.endswith("gaiters"):
            w = w[:-1]  # gaiters -> gaiter
        elif w.endswith("boots"):
            w = w[:-1]  # boots -> boot
        elif w.endswith("shields"):
            w = w[:-2] + "shield"  # shields -> shield
        out.append(w)
    return [w for w in out if w]


def _icon_stem(fn: str) -> str:
    stem = fn.rsplit(".", 1)[0].lower()
    stem = re.sub(r"[^a-z0-9]+", " ", stem).strip()
    return stem


SLOT_ALLOWED = {
    "helmet": (["helmet", "circlet", "cap"], ["shield"]),
    "chest": (["breastplate", "tunic", "plate", "shirt"], ["gaiter", "hose", "pants", "tights", "boot", "shoe", "glove", "gauntlet", "bracer", "shield", "weapon", "sword", "blade", "circlet", "helmet", "cap"]),
    "pants": (["gaiter", "gaiters", "hose", "pants", "tights", "stockings"], ["helmet", "circlet", "cap", "breastplate", "tunic", "plate", "shirt", "boot", "shoe", "glove", "gauntlet", "bracer", "shield", "weapon", "sword", "blade"]),
    "gloves": (["gloves", "gauntlet", "bracer"], ["helmet", "circlet", "cap", "boot", "shoe", "gaiter", "hose", "pants", "tights", "shield", "weapon", "sword", "blade"]),
    "boots": (["boots", "shoes", "boot"], ["helmet", "circlet", "cap", "gaiter", "hose", "pants", "tights", "glove", "gauntlet", "bracer", "shield", "weapon", "sword", "blade"]),
    "weapon_main": (["weapon_", "sword", "blade", "tallum", "tsurugi"], ["shield"]),
    "weapon_off": (["shield", "hoplon", "aspsis", "aegis"], ["weapon_", "sword", "blade"]),
}


def _candidates_for_slot(icon_stem: str, slot: str) -> bool:
    allowed, excluded = SLOT_ALLOWED.get(slot, ([], []))
    ok_allowed = any(kw in icon_stem for kw in allowed) if allowed else True
    ok_excluded = not any(kw in icon_stem for kw in excluded)
    return ok_allowed and ok_excluded


def _armor_t_part_for_slot(slot: str) -> set[str]:
    # Files like: armor_t84_b_i00.png where:
    #  b = boots, g = gloves, l = pants/legs, u = chest/upper, ul = (upper legs) fallback.
    if slot == "boots":
        return {"b"}
    if slot == "gloves":
        return {"g"}
    if slot == "pants":
        return {"l", "ul"}
    if slot == "chest":
        return {"u", "ul"}
    return set()


def _s_armor_t_priority(base_t: int) -> int:
    """
    Priority for S-grade generic armor_t picks.
    Prefer the “S80/S84-like” tiers first, then other close ones.
    """
    # Higher = more preferred
    return {
        84: 100,
        80: 90,
        85: 80,
        88: 70,
        89: 60,
    }.get(base_t, 0)


def _parse_armor_t_variant(icon_stem_raw: str) -> tuple[int | None, str | None]:
    """
    Extract tier and part code from stems like:
      armor_t84_b_i00
    Returns (t_number, part_code).
    """
    import re

    m = re.search(r"armor_t(\d+)_([a-z]{1,2})_", icon_stem_raw)
    if not m:
        return (None, None)
    return (int(m.group(1)), m.group(2))


def _parse_i_variant(filename: str) -> int:
    """
    Extract numeric i-variant from stems like:
      weapon_forgotten_blade_i01.png -> 1
    """
    import re

    stem = filename.rsplit(".", 1)[0].lower()
    m = re.search(r"_i(\d+)", stem)
    if not m:
        return 0
    try:
        return int(m.group(1))
    except Exception:
        return 0


def best_icon_for_item(
    name: str,
    slot: str,
    grade: str,
    icon_files: list[str],
    icon_stems: dict[str, str],
    icon_stems_raw: dict[str, str],
) -> str | None:
    tokens = _normalize_tokens(name)
    # special mismatch between JSON lore and icon filename in your dataset
    # (Keshanberk is stored as kshanberk in some weapon icons)
    tokens2 = [t for t in tokens if t != "keshanberk"] + (["kshanberk"] if "keshanberk" in tokens else [])

    name_l = (name or "").lower()
    # Explicit overrides for S-tier where icon matching by keywords is ambiguous.
    if grade == "s" and slot == "weapon_main":
        if "forgotten" in name_l:
            # Prefer the higher variant if present.
            if any("weapon_forgotten_blade_i01" == fn.lower().rsplit(".", 1)[0] for fn in icon_files):
                return "weapon_forgotten_blade_i01.png" if any(
                    fn.lower() == "weapon_forgotten_blade_i01.png" for fn in icon_files
                ) else "weapon_forgotten_blade_i00.png"
            return "weapon_forgotten_blade_i00.png"
        if "god" in name_l and "blade" in name_l:
            # In this dataset "God's Blade" maps to etc_soul_of_blade.
            if any(fn.lower() == "etc_soul_of_blade.png" for fn in icon_files):
                return "etc_soul_of_blade.png"

    if grade == "s" and slot == "weapon_off":
        if "imperial" in name_l and "crusader" in name_l and "shield" in name_l:
            # Prefer i02 if available.
            if any(fn.lower() == "shield_imperial_crusader_shield_i02.png" for fn in icon_files):
                return "shield_imperial_crusader_shield_i02.png"
            if any(fn.lower() == "shield_imperial_crusader_shield_i00.png" for fn in icon_files):
                return "shield_imperial_crusader_shield_i00.png"
        if "dragon" in name_l and "shield" in name_l:
            if any(fn.lower() == "shield_dark_dragon_shield_i01.png" for fn in icon_files):
                return "shield_dark_dragon_shield_i01.png"
            if any(fn.lower() == "shield_dark_dragon_shield_i00.png" for fn in icon_files):
                return "shield_dark_dragon_shield_i00.png"

    # For S grade: prefer high-tier generic armor_tXX icons for armor slots,
    # because many “by-name” armor icons are missing in this icon set.
    if grade == "s" and slot in ("chest", "pants", "gloves", "boots"):
        preferred_parts = _armor_t_part_for_slot(slot)
        # (priority, base_t, filename)
        armor_candidates: list[tuple[int, int, str]] = []
        for fn in icon_files:
            stem_raw = icon_stems_raw[fn]
            t_num, part = _parse_armor_t_variant(stem_raw)
            if t_num is None or part is None:
                continue
            if part in preferred_parts:
                # S80/S84/etc in this icon set seem to map to either:
                # - tNN where NN is around 80-89
                # - or t8XX (like t801/t802/t811...) => treat base as t_num//10 (80..81..)
                if 80 <= t_num <= 89:
                    base_t = t_num
                elif t_num in {801, 802, 803, 811, 812, 813}:
                    base_t = t_num // 10
                else:
                    continue
                armor_candidates.append((_s_armor_t_priority(base_t), base_t, fn))
        if armor_candidates:
            # Pick max tier first; tie-break with name token score.
            armor_candidates.sort(
                key=lambda x: (x[0], x[1], _parse_i_variant(x[2])),
                reverse=True,
            )
            top_fn = armor_candidates[0][2]
            # Keep only candidates with the same best priority+base_t
            best_priority = armor_candidates[0][0]
            best_base_t = armor_candidates[0][1]
            top_fns = [
                fn
                for pr, bt, fn in armor_candidates
                if pr == best_priority and bt == best_base_t
            ]

            best_fn = None
            best_sc = -1.0
            best_i = -1
            for fn in top_fns:
                stem = icon_stems[fn]
                sc = 0.0
                for t in tokens2:
                    if t and t in stem:
                        sc += len(t)
                i_var = _parse_i_variant(fn)
                if best_fn is None or sc > best_sc or (sc == best_sc and i_var > best_i):
                    best_fn = fn
                    best_sc = sc
                    best_i = i_var
            return best_fn

    best_fn = None
    best_sc = -1.0
    best_i = -1

    for fn in icon_files:
        stem = icon_stems[fn]
        if not _candidates_for_slot(stem, slot):
            continue

        sc = 0.0
        for t in tokens2:
            if not t:
                continue
            if t in stem:
                sc += len(t)
        # fallback nudge: if nothing matched, still allow generic by slot type
        if best_fn is None and sc == 0.0:
            sc = 0.01

        i_var = _parse_i_variant(fn)
        if sc > best_sc or (sc == best_sc and grade == "s" and i_var > best_i):
            best_sc = sc
            best_fn = fn
            best_i = i_var

    if best_fn is not None:
        return best_fn

    # ultimate fallback: allow any icon (should be rare with slot keywords above)
    for fn in icon_files:
        stem = icon_stems[fn]
        sc = 0.0
        for t in tokens2:
            if t and t in stem:
                sc += len(t)
        if sc > best_sc:
            best_sc = sc
            best_fn = fn
    return best_fn


def parse_args():
    p = argparse.ArgumentParser(description="Rebuild image_filename for equipment_sets_by_grade.json")
    p.add_argument("--json-path", default="equipment_sets_by_grade.json", help="Source JSON with equipment sets")
    p.add_argument("--icons-dir", default=r"static/item/Items", help="Directory with item icons")
    return p.parse_args()


def main():
    args = parse_args()
    root_dir = Path(__file__).resolve().parent
    json_path = (root_dir / args.json_path).resolve()
    icons_dir = (root_dir / args.icons_dir).resolve()

    with open(json_path, "r", encoding="utf-8") as f:
        payload = json.load(f)

    icon_files = [f.name for f in icons_dir.iterdir() if f.is_file()]
    # icon_stems: normalized string (for keyword scoring)
    icon_stems = {fn: _icon_stem(fn) for fn in icon_files}
    # icon_stems_raw: raw filename stem (underscores preserved for armor_tXX parsing)
    icon_stems_raw = {fn: fn.rsplit(".", 1)[0].lower() for fn in icon_files}

    total = 0
    missing = []
    for g in payload.get("grades", []):
        grade = (g.get("grade") or "").strip().lower()
        for st in g.get("sets", []):
            for it in st.get("items", []):
                slot = (it.get("slot") or "").strip().lower()
                name = (it.get("name") or "").strip()
                if slot not in SLOT_ORDER:
                    continue

                best_fn = best_icon_for_item(
                    name=name,
                    slot=slot,
                    grade=grade,
                    icon_files=icon_files,
                    icon_stems=icon_stems,
                    icon_stems_raw=icon_stems_raw,
                )
                total += 1
                if not best_fn:
                    missing.append((slot, name))
                    continue
                it["image_filename"] = f"item/Items/{best_fn}"

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=True, indent=2)

    print(f"Rebuilt image_filename for {total} items. missing={len(missing)}")
    for row in missing[:10]:
        print("  missing:", row)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

