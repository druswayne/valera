# -*- coding: utf-8 -*-
"""Дерево умений (RPG skill tree) для личного кабинета."""

from __future__ import annotations

import sys

ABILITY_MIN_LEVEL = 5
ABILITY_POINTS_FIRST_LEVEL = 5
ABILITY_POINTS_INTERVAL = 5

TIER_LABELS = {1: 'I', 2: 'II', 3: 'III'}
TIER_TITLES = {1: 'Основа', 2: 'Развитие', 3: 'Мастерство'}
SLOT_ORDER = {'left': 0, 'center': 1, 'right': 2}


def _app_module():
    import app as app_module
    main = sys.modules.get('__main__')
    if main is not None and getattr(main, '__file__', None) == getattr(app_module, '__file__', None):
        return main
    return app_module


def _db():
    return _app_module().db


BRANCHES = [
    {'id': 'warrior', 'name': 'Воин', 'color': '#c45a4a', 'description': 'Урон и захват территорий', 'icon': '⚔'},
    {'id': 'guardian', 'name': 'Страж', 'color': '#5a8ac4', 'description': 'Защита и удержание областей', 'icon': '🛡'},
    {'id': 'sage', 'name': 'Мудрец', 'color': '#d4a84b', 'description': 'Опыт, нумы и энергия', 'icon': '📜'},
    {'id': 'tactician', 'name': 'Тактик', 'color': '#5ab87a', 'description': 'Атака и оборона на карте', 'icon': '🏹'},
    {'id': 'duelist', 'name': 'Дуэлянт', 'color': '#9a6ac4', 'description': 'PvP-дуэли (с 5 уровня)', 'icon': '⚔️'},
]

BRANCH_IDS = {b['id'] for b in BRANCHES}
BRANCH_ORDER = {b['id']: i for i, b in enumerate(BRANCHES)}
BRANCH_BY_ID = {b['id']: b for b in BRANCHES}

# branch: warrior | guardian | sage | tactician | duelist
ABILITIES = {
    # --- Воин: ветка урона ---
    'w_blade': {
        'code': 'w_blade', 'name': 'Мастерство клинка', 'branch': 'warrior', 'icon': '⚔',
        'description': 'Повышает урон при захвате областей.',
        'max_rank': 3, 'cost_per_rank': 1, 'min_level': 1, 'requires': [],
        'tier': 1, 'slot': 'center',
        'bonuses': {'damage_pct': 3}, 'bonus_text': '+3% к урону за ранг',
    },
    'w_cleave': {
        'code': 'w_cleave', 'name': 'Сокрушительный удар', 'branch': 'warrior', 'icon': '🗡',
        'description': 'Плоский урон к атаке.',
        'max_rank': 2, 'cost_per_rank': 1, 'min_level': 1,
        'requires': [{'code': 'w_blade', 'rank': 2}],
        'tier': 2, 'slot': 'left',
        'bonuses': {'damage_add': 2}, 'bonus_text': '+2 к атаке за ранг',
    },
    'w_fury': {
        'code': 'w_fury', 'name': 'Ярость берсерка', 'branch': 'warrior', 'icon': '🔥',
        'description': 'Процентный урон при захвате.',
        'max_rank': 2, 'cost_per_rank': 1, 'min_level': 1,
        'requires': [{'code': 'w_blade', 'rank': 2}],
        'tier': 2, 'slot': 'right',
        'bonuses': {'damage_pct': 4}, 'bonus_text': '+4% к урону за ранг',
    },
    'w_rampage': {
        'code': 'w_rampage', 'name': 'Неистовство', 'branch': 'warrior', 'icon': '💥',
        'description': 'Мощный финальный урон (путь силы).',
        'max_rank': 1, 'cost_per_rank': 2, 'min_level': 1,
        'requires': [{'code': 'w_cleave', 'rank': 2}],
        'tier': 3, 'slot': 'left',
        'bonuses': {'damage_pct': 8}, 'bonus_text': '+8% к урону',
    },
    'w_berserk': {
        'code': 'w_berserk', 'name': 'Бешенство', 'branch': 'warrior', 'icon': '☄',
        'description': 'Финальный урон и плоская атака (путь ярости).',
        'max_rank': 1, 'cost_per_rank': 2, 'min_level': 1,
        'requires': [{'code': 'w_fury', 'rank': 2}],
        'tier': 3, 'slot': 'right',
        'bonuses': {'damage_pct': 5, 'damage_add': 3}, 'bonus_text': '+5% урона и +3 атаки',
    },
    # --- Страж ---
    'g_shield': {
        'code': 'g_shield', 'name': 'Стойкость', 'branch': 'guardian', 'icon': '🛡',
        'description': 'Усиливает защиту области вашего клана.',
        'max_rank': 3, 'cost_per_rank': 1, 'min_level': 1, 'requires': [],
        'tier': 1, 'slot': 'center',
        'bonuses': {'defense_pct': 3}, 'bonus_text': '+3% к защите за ранг',
    },
    'g_wall': {
        'code': 'g_wall', 'name': 'Крепкая броня', 'branch': 'guardian', 'icon': '🧱',
        'description': 'Плоская защита.',
        'max_rank': 2, 'cost_per_rank': 1, 'min_level': 1,
        'requires': [{'code': 'g_shield', 'rank': 2}],
        'tier': 2, 'slot': 'left',
        'bonuses': {'defense_add': 2}, 'bonus_text': '+2 к защите за ранг',
    },
    'g_ward': {
        'code': 'g_ward', 'name': 'Оберег', 'branch': 'guardian', 'icon': '✦',
        'description': 'Процентная защита территории.',
        'max_rank': 2, 'cost_per_rank': 1, 'min_level': 1,
        'requires': [{'code': 'g_shield', 'rank': 2}],
        'tier': 2, 'slot': 'right',
        'bonuses': {'defense_pct': 4}, 'bonus_text': '+4% к защите за ранг',
    },
    'g_aegis': {
        'code': 'g_aegis', 'name': 'Эгида', 'branch': 'guardian', 'icon': '✨',
        'description': 'Сильная защита (путь брони).',
        'max_rank': 1, 'cost_per_rank': 2, 'min_level': 1,
        'requires': [{'code': 'g_wall', 'rank': 2}],
        'tier': 3, 'slot': 'left',
        'bonuses': {'defense_pct': 8}, 'bonus_text': '+8% к защите',
    },
    'g_bastion': {
        'code': 'g_bastion', 'name': 'Бастион', 'branch': 'guardian', 'icon': '🏰',
        'description': 'Защита и плоская броня (путь оберега).',
        'max_rank': 1, 'cost_per_rank': 2, 'min_level': 1,
        'requires': [{'code': 'g_ward', 'rank': 2}],
        'tier': 3, 'slot': 'right',
        'bonuses': {'defense_pct': 5, 'defense_add': 3}, 'bonus_text': '+5% защиты и +3 брони',
    },
    # --- Мудрец ---
    's_study': {
        'code': 's_study', 'name': 'Учёность', 'branch': 'sage', 'icon': '📜',
        'description': 'Больше опыта за правильные ответы.',
        'max_rank': 3, 'cost_per_rank': 1, 'min_level': 1, 'requires': [],
        'tier': 1, 'slot': 'center',
        'bonuses': {'xp_reward_pct': 4}, 'bonus_text': '+4% к опыту за ранг',
    },
    's_greed': {
        'code': 's_greed', 'name': 'Удача торговца', 'branch': 'sage', 'icon': '💰',
        'description': 'Больше нумов за ответы.',
        'max_rank': 2, 'cost_per_rank': 1, 'min_level': 1,
        'requires': [{'code': 's_study', 'rank': 2}],
        'tier': 2, 'slot': 'left',
        'bonuses': {'nums_reward_pct': 4}, 'bonus_text': '+4% к нумам за ранг',
    },
    's_focus': {
        'code': 's_focus', 'name': 'Внутренняя сила', 'branch': 'sage', 'icon': '⚡',
        'description': 'Максимальный запас энергии.',
        'max_rank': 2, 'cost_per_rank': 1, 'min_level': 1,
        'requires': [{'code': 's_study', 'rank': 2}],
        'tier': 2, 'slot': 'right',
        'bonuses': {'max_energy_add': 3}, 'bonus_text': '+3 к макс. энергии за ранг',
    },
    's_archive': {
        'code': 's_archive', 'name': 'Архивариус', 'branch': 'sage', 'icon': '📚',
        'description': 'Опыт и нумы (путь торговца).',
        'max_rank': 1, 'cost_per_rank': 2, 'min_level': 1,
        'requires': [{'code': 's_greed', 'rank': 2}],
        'tier': 3, 'slot': 'left',
        'bonuses': {'nums_reward_pct': 8, 'xp_reward_pct': 4}, 'bonus_text': '+8% нумов и +4% опыта',
    },
    's_flow': {
        'code': 's_flow', 'name': 'Поток энергии', 'branch': 'sage', 'icon': '🌟',
        'description': 'Энергия и опыт (путь силы).',
        'max_rank': 1, 'cost_per_rank': 2, 'min_level': 1,
        'requires': [{'code': 's_focus', 'rank': 2}],
        'tier': 3, 'slot': 'right',
        'bonuses': {'max_energy_add': 6, 'xp_reward_pct': 6}, 'bonus_text': '+6 энергии и +6% опыта',
    },
    # --- Тактик ---
    't_leadership': {
        'code': 't_leadership', 'name': 'Лидерство', 'branch': 'tactician', 'icon': '🎖',
        'description': 'Базовый бонус к атаке и защите на карте.',
        'max_rank': 3, 'cost_per_rank': 1, 'min_level': 1, 'requires': [],
        'tier': 1, 'slot': 'center',
        'bonuses': {'damage_pct': 1, 'defense_pct': 1}, 'bonus_text': '+1% к урону и защите за ранг',
    },
    't_assault': {
        'code': 't_assault', 'name': 'Натиск', 'branch': 'tactician', 'icon': '🏹',
        'description': 'Урон при атаке чужих областей.',
        'max_rank': 2, 'cost_per_rank': 1, 'min_level': 1,
        'requires': [{'code': 't_leadership', 'rank': 2}],
        'tier': 2, 'slot': 'left',
        'bonuses': {'damage_pct': 3}, 'bonus_text': '+3% к урону при атаке за ранг',
    },
    't_phalanx': {
        'code': 't_phalanx', 'name': 'Фаланга', 'branch': 'tactician', 'icon': '🛡',
        'description': 'Защита при обороне своих областей.',
        'max_rank': 2, 'cost_per_rank': 1, 'min_level': 1,
        'requires': [{'code': 't_leadership', 'rank': 2}],
        'tier': 2, 'slot': 'right',
        'bonuses': {'defense_pct': 3}, 'bonus_text': '+3% к защите при обороне за ранг',
    },
    't_command': {
        'code': 't_command', 'name': 'Командование', 'branch': 'tactician', 'icon': '👑',
        'description': 'Мастерство атаки и обороны.',
        'max_rank': 2, 'cost_per_rank': 2, 'min_level': 1,
        'requires': [{'code': 't_assault', 'rank': 2}, {'code': 't_phalanx', 'rank': 2}],
        'tier': 3, 'slot': 'center',
        'bonuses': {'damage_pct': 3, 'defense_pct': 3}, 'bonus_text': '+3% к урону и защите за ранг',
    },
    # --- Дуэлянт ---
    'd_riposte': {
        'code': 'd_riposte', 'name': 'Боевая стойка', 'branch': 'duelist', 'icon': '⚔️',
        'description': 'Урон в PvP-дуэлях.',
        'max_rank': 3, 'cost_per_rank': 1, 'min_level': ABILITY_MIN_LEVEL, 'requires': [],
        'tier': 1, 'slot': 'center',
        'bonuses': {'pvp_damage_pct': 5}, 'bonus_text': '+5% к PvP-урону за ранг',
    },
    'd_endure': {
        'code': 'd_endure', 'name': 'Живучесть', 'branch': 'duelist', 'icon': '❤',
        'description': 'Здоровье в дуэлях.',
        'max_rank': 2, 'cost_per_rank': 1, 'min_level': ABILITY_MIN_LEVEL,
        'requires': [{'code': 'd_riposte', 'rank': 1}],
        'tier': 2, 'slot': 'left',
        'bonuses': {'pvp_hp_add': 10}, 'bonus_text': '+10 HP в дуэли за ранг',
    },
    'd_precision': {
        'code': 'd_precision', 'name': 'Точность', 'branch': 'duelist', 'icon': '🎯',
        'description': 'Плоский урон в PvP.',
        'max_rank': 2, 'cost_per_rank': 1, 'min_level': ABILITY_MIN_LEVEL,
        'requires': [{'code': 'd_riposte', 'rank': 2}],
        'tier': 2, 'slot': 'right',
        'bonuses': {'pvp_damage_add': 2}, 'bonus_text': '+2 к PvP-урону за ранг',
    },
    'd_finisher': {
        'code': 'd_finisher', 'name': 'Добивающий удар', 'branch': 'duelist', 'icon': '💀',
        'description': 'Мощный PvP-урон (путь живучести).',
        'max_rank': 1, 'cost_per_rank': 2, 'min_level': ABILITY_MIN_LEVEL,
        'requires': [{'code': 'd_endure', 'rank': 2}, {'code': 'd_riposte', 'rank': 3}],
        'tier': 3, 'slot': 'left',
        'bonuses': {'pvp_damage_add': 5, 'pvp_hp_add': 15}, 'bonus_text': '+5 урона и +15 HP',
    },
    'd_lethal': {
        'code': 'd_lethal', 'name': 'Смертельный удар', 'branch': 'duelist', 'icon': '⚡',
        'description': 'Максимальный PvP-урон (путь точности).',
        'max_rank': 1, 'cost_per_rank': 2, 'min_level': ABILITY_MIN_LEVEL,
        'requires': [{'code': 'd_precision', 'rank': 2}, {'code': 'd_riposte', 'rank': 3}],
        'tier': 3, 'slot': 'right',
        'bonuses': {'pvp_damage_pct': 12, 'pvp_damage_add': 3}, 'bonus_text': '+12% и +3 к PvP-урону',
    },
}


def get_user_ability_class(user):
    return (getattr(user, 'ability_class', None) or '').strip() or None


def ability_points_total_for_level(level):
    level = max(1, int(level or 1))
    if level < ABILITY_POINTS_FIRST_LEVEL:
        return 0
    return 1 + (level - ABILITY_POINTS_FIRST_LEVEL) // ABILITY_POINTS_INTERVAL


def _empty_bonuses():
    return {
        'damage_add': 0, 'defense_add': 0, 'max_energy_add': 0,
        'damage_pct': 0.0, 'defense_pct': 0.0,
        'xp_reward_pct': 0.0, 'nums_reward_pct': 0.0,
        'pvp_damage_pct': 0.0, 'pvp_damage_add': 0, 'pvp_hp_add': 0,
    }


def get_user_ability_ranks(user_id):
    UserAbility = _app_module().UserAbility
    rows = UserAbility.query.filter_by(user_id=user_id).all()
    return {r.ability_code: int(r.rank or 0) for r in rows}


def _ranks_for_class(ranks, chosen_class):
    if not chosen_class:
        return {}
    return {c: r for c, r in ranks.items() if ABILITIES.get(c, {}).get('branch') == chosen_class}


def ability_points_spent(ranks=None, user_id=None, chosen_class=None):
    if ranks is None:
        ranks = get_user_ability_ranks(user_id)
    if chosen_class is None and user_id is not None:
        User = _app_module().User
        user = User.query.get(user_id)
        chosen_class = get_user_ability_class(user) if user else None
    if chosen_class:
        ranks = _ranks_for_class(ranks, chosen_class)
    spent = 0
    for code, rank in ranks.items():
        ab = ABILITIES.get(code)
        if not ab or rank <= 0:
            continue
        spent += rank * int(ab.get('cost_per_rank', 1) or 1)
    return spent


def ability_points_available(user):
    total = ability_points_total_for_level(user.level or 1)
    chosen = get_user_ability_class(user)
    spent = ability_points_spent(user_id=user.id, chosen_class=chosen)
    return max(0, total - spent)


def aggregate_ability_bonuses(ranks=None, user_id=None, chosen_class=None):
    if ranks is None:
        ranks = get_user_ability_ranks(user_id)
    if chosen_class is None and user_id is not None:
        User = _app_module().User
        user = User.query.get(user_id)
        chosen_class = get_user_ability_class(user) if user else None
    if not chosen_class:
        return _empty_bonuses()
    ranks = _ranks_for_class(ranks, chosen_class)
    result = _empty_bonuses()
    for code, rank in ranks.items():
        if rank <= 0:
            continue
        ab = ABILITIES.get(code)
        if not ab:
            continue
        for key, per_rank in (ab.get('bonuses') or {}).items():
            if key not in result:
                continue
            if isinstance(result[key], int):
                result[key] += int(per_rank) * rank
            else:
                result[key] += float(per_rank) * rank
    return result


def _requirements_met(ability, ranks, user_level):
    if (user_level or 1) < int(ability.get('min_level', 1) or 1):
        return False
    for req in ability.get('requires') or []:
        need_rank = int(req.get('rank', 1) or 1)
        have = ranks.get(req['code'], 0)
        if have < need_rank:
            return False
    return True


def can_upgrade_ability(user, ability_code, ranks=None):
    ability = ABILITIES.get(ability_code)
    if not ability:
        return False, 'Неизвестное умение'
    chosen = get_user_ability_class(user)
    if not chosen:
        return False, 'Сначала выберите класс'
    if ability['branch'] != chosen:
        return False, 'Умение другого класса'
    if ranks is None:
        ranks = get_user_ability_ranks(user.id)
    current = ranks.get(ability_code, 0)
    max_rank = int(ability.get('max_rank', 1) or 1)
    if current >= max_rank:
        return False, 'Максимальный ранг'
    if not _requirements_met(ability, ranks, user.level):
        min_lvl = int(ability.get('min_level', 1) or 1)
        if (user.level or 1) < min_lvl:
            return False, f'Нужен {min_lvl} уровень'
        return False, 'Не выполнены требования'
    cost = int(ability.get('cost_per_rank', 1) or 1)
    if ability_points_available(user) < cost:
        return False, 'Недостаточно очков умений'
    return True, None


def choose_ability_class(user, branch_id):
    branch_id = (branch_id or '').strip()
    if branch_id not in BRANCH_IDS:
        return False, 'Неизвестный класс'
    if get_user_ability_class(user):
        return False, 'Класс уже выбран и не может быть изменён'
    if branch_id == 'duelist' and (user.level or 1) < ABILITY_MIN_LEVEL:
        return False, f'Класс «Дуэлянт» доступен с {ABILITY_MIN_LEVEL} уровня'
    user.ability_class = branch_id
    UserAbility = _app_module().UserAbility
    for row in UserAbility.query.filter_by(user_id=user.id).all():
        ab = ABILITIES.get(row.ability_code)
        if not ab or ab.get('branch') != branch_id:
            _db().session.delete(row)
    return True, None


def upgrade_ability(user, ability_code):
    ok, reason = can_upgrade_ability(user, ability_code)
    if not ok:
        return False, reason
    UserAbility = _app_module().UserAbility
    row = UserAbility.query.filter_by(user_id=user.id, ability_code=ability_code).first()
    if not row:
        row = UserAbility(user_id=user.id, ability_code=ability_code, rank=0)
        _db().session.add(row)
    row.rank = (row.rank or 0) + 1
    return True, None


def _requires_text(ability):
    reqs = ability.get('requires') or []
    if not reqs:
        return ''
    parts = []
    for req in reqs:
        ab = ABILITIES.get(req['code'])
        name = ab['name'] if ab else req['code']
        need = int(req.get('rank', 1) or 1)
        parts.append(f'{name} (ранг {need})')
    return 'Требуется: ' + ', '.join(parts)


def ability_node_state(user, ability_code, ranks=None, chosen_class=None):
    ability = ABILITIES.get(ability_code)
    if not ability:
        return None
    if chosen_class is None:
        chosen_class = get_user_ability_class(user)
    if ranks is None:
        ranks = get_user_ability_ranks(user.id)
    rank = ranks.get(ability_code, 0)
    max_rank = int(ability.get('max_rank', 1) or 1)
    requires_text = _requires_text(ability)
    branch = ability['branch']

    if chosen_class and branch != chosen_class:
        return {
            'code': ability_code,
            'name': ability['name'],
            'description': ability['description'],
            'branch': branch,
            'icon': ability.get('icon', '★'),
            'rank': rank,
            'max_rank': max_rank,
            'cost_per_rank': int(ability.get('cost_per_rank', 1) or 1),
            'bonus_text': ability.get('bonus_text', ''),
            'requires': ability.get('requires') or [],
            'requires_text': requires_text,
            'min_level': int(ability.get('min_level', 1) or 1),
            'tier': int(ability.get('tier', 1) or 1),
            'slot': ability.get('slot', 'center') or 'center',
            'tier_label': TIER_LABELS.get(int(ability.get('tier', 1) or 1), ''),
            'tier_title': TIER_TITLES.get(int(ability.get('tier', 1) or 1), ''),
            'status': 'foreign',
            'status_label': 'Другой класс',
            'lock_reason': 'Выбран другой класс',
            'can_upgrade': False,
        }

    if not chosen_class:
        min_lvl = int(ability.get('min_level', 1) or 1)
        lock_reason = None
        if branch == 'duelist' and (user.level or 1) < ABILITY_MIN_LEVEL:
            status = 'locked'
            lock_reason = f'Класс доступен с {ABILITY_MIN_LEVEL} уровня'
        else:
            status = 'preview'
            lock_reason = 'Выберите класс, чтобы прокачивать'
        return {
            'code': ability_code,
            'name': ability['name'],
            'description': ability['description'],
            'branch': branch,
            'icon': ability.get('icon', '★'),
            'rank': 0,
            'max_rank': max_rank,
            'cost_per_rank': int(ability.get('cost_per_rank', 1) or 1),
            'bonus_text': ability.get('bonus_text', ''),
            'requires': ability.get('requires') or [],
            'requires_text': requires_text,
            'min_level': min_lvl,
            'tier': int(ability.get('tier', 1) or 1),
            'slot': ability.get('slot', 'center') or 'center',
            'tier_label': TIER_LABELS.get(int(ability.get('tier', 1) or 1), ''),
            'tier_title': TIER_TITLES.get(int(ability.get('tier', 1) or 1), ''),
            'status': status,
            'status_label': 'Превью' if status == 'preview' else 'Заблокировано',
            'lock_reason': lock_reason,
            'can_upgrade': False,
        }

    reqs_ok = _requirements_met(ability, ranks, user.level)
    can_up, lock_reason = can_upgrade_ability(user, ability_code, ranks=ranks)
    if rank >= max_rank:
        status = 'maxed'
        lock_reason = None
    elif not reqs_ok:
        status = 'locked'
        min_lvl = int(ability.get('min_level', 1) or 1)
        if (user.level or 1) < min_lvl:
            lock_reason = f'Нужен {min_lvl} уровень персонажа'
        else:
            lock_reason = requires_text or 'Требования не выполнены'
    elif can_up:
        status = 'available'
        lock_reason = None
    elif rank > 0:
        status = 'progress'
        lock_reason = lock_reason or 'Недостаточно очков умений'
    else:
        status = 'waiting'
        lock_reason = lock_reason or 'Недостаточно очков умений'
    status_labels = {
        'maxed': 'Максимум',
        'locked': 'Заблокировано',
        'available': 'Можно улучшить',
        'progress': 'В процессе',
        'waiting': 'Открыто',
    }
    return {
        'code': ability_code,
        'name': ability['name'],
        'description': ability['description'],
        'branch': branch,
        'icon': ability.get('icon', '★'),
        'rank': rank,
        'max_rank': max_rank,
        'cost_per_rank': int(ability.get('cost_per_rank', 1) or 1),
        'bonus_text': ability.get('bonus_text', ''),
        'requires': ability.get('requires') or [],
        'requires_text': requires_text,
        'min_level': int(ability.get('min_level', 1) or 1),
        'tier': int(ability.get('tier', 1) or 1),
        'slot': ability.get('slot', 'center') or 'center',
        'tier_label': TIER_LABELS.get(int(ability.get('tier', 1) or 1), ''),
        'tier_title': TIER_TITLES.get(int(ability.get('tier', 1) or 1), ''),
        'status': status,
        'status_label': status_labels.get(status, ''),
        'lock_reason': lock_reason,
        'can_upgrade': can_up,
    }


def get_abilities_payload(user):
    chosen = get_user_ability_class(user)
    ranks = get_user_ability_ranks(user.id)
    nodes = []
    for code in sorted(ABILITIES.keys(), key=lambda c: (BRANCH_ORDER.get(ABILITIES[c]['branch'], 99), c)):
        node = ability_node_state(user, code, ranks=ranks, chosen_class=chosen)
        if node:
            nodes.append(node)
    bonuses = aggregate_ability_bonuses(ranks=ranks, chosen_class=chosen)
    branch_meta = []
    for b in BRANCHES:
        meta = dict(b)
        if not chosen:
            meta['state'] = 'selectable'
            if b['id'] == 'duelist' and (user.level or 1) < ABILITY_MIN_LEVEL:
                meta['state'] = 'locked'
                meta['lock_reason'] = f'Доступен с {ABILITY_MIN_LEVEL} уровня'
        elif b['id'] == chosen:
            meta['state'] = 'chosen'
        else:
            meta['state'] = 'foreign'
            meta['lock_reason'] = 'Выбран другой класс'
        branch_meta.append(meta)
    chosen_info = BRANCH_BY_ID.get(chosen) if chosen else None
    return {
        'branches': branch_meta,
        'abilities': nodes,
        'class_chosen': bool(chosen),
        'chosen_class': chosen,
        'chosen_class_name': chosen_info['name'] if chosen_info else None,
        'chosen_class_color': chosen_info['color'] if chosen_info else None,
        'ability_points_total': ability_points_total_for_level(user.level or 1),
        'ability_points_spent': ability_points_spent(ranks=ranks, chosen_class=chosen),
        'ability_points_available': ability_points_available(user),
        'bonuses_summary': bonuses,
        'min_level': ABILITY_MIN_LEVEL,
    }
