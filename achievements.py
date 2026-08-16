# -*- coding: utf-8 -*-
"""Система достижений личного кабинета."""

from datetime import datetime
import sys


def _app_module():
    """Модуль с db и моделями (при `python app.py` это __main__, не дубликат app)."""
    main = sys.modules.get('__main__')
    if main is not None and hasattr(main, 'db'):
        return main
    import app as app_module
    return app_module


def _db():
    return _app_module().db

# Ключи счётчиков
COUNTER_TERRITORY_CORRECT = 'territory_correct'
COUNTER_TERRITORY_DAMAGE = 'territory_damage'
COUNTER_TERRITORY_INFLUENCE = 'territory_influence'
COUNTER_TERRITORY_CAPTURES = 'territory_captures'
COUNTER_NEUTRAL_CAPTURES = 'neutral_captures'
COUNTER_LEVEL = 'level'
COUNTER_NUMS_EARNED = 'nums_earned'
COUNTER_NUMS_SPENT = 'nums_spent'
COUNTER_NUMS_BALANCE_MAX = 'nums_balance_max'
COUNTER_SHOP_PURCHASES = 'shop_purchases'
COUNTER_CHESTS_OPENED = 'chests_opened'
COUNTER_ITEMS_USED = 'items_used'
COUNTER_ITEMS_SOLD = 'items_sold'
COUNTER_EQUIP_ACTIONS = 'equip_actions'
COUNTER_WEAPON_ENCHANT_MAX = 'weapon_enchant_max'
COUNTER_EQUIPMENT_SLOTS = 'equipment_slots_filled'
COUNTER_PVP_WINS = 'pvp_wins'
COUNTER_PVP_DUELS = 'pvp_duels'
COUNTER_PVP_WAGER_WINS = 'pvp_wager_wins'
COUNTER_PVP_ARENA_VISITS = 'pvp_arena_visits'
COUNTER_CLAN_CREATED = 'clan_created'
COUNTER_CLAN_JOINED = 'clan_joined'
COUNTER_CLAN_CHAT = 'clan_chat_messages'
COUNTER_CLAN_RANK_TIER = 'clan_rank_tier'
COUNTER_CLAN_APPLICATIONS = 'clan_applications'
COUNTER_DEMOGORGON_HITS = 'demogorgon_hits'
COUNTER_STRUCTURES_BUILT = 'structures_built'
COUNTER_MARKERS_SET = 'markers_set'
COUNTER_NUMS_TRANSFERRED = 'nums_transferred'
COUNTER_SKILLS_SPENT = 'skills_spent'
COUNTER_MAX_ENERGY = 'max_energy'
COUNTER_AVATAR_SET = 'avatar_set'
COUNTER_RENAMES = 'character_renames'
COUNTER_BUFFS_APPLIED = 'buffs_applied'

ACHIEVEMENT_CATEGORIES = {
    'territory': 'Битва за территорию',
    'progress': 'Прогресс',
    'economy': 'Экономика',
    'shop': 'Лавка и инвентарь',
    'equipment': 'Снаряжение',
    'pvp': 'PvP Арена',
    'clan': 'Клан',
    'world': 'Мир и события',
    'profile': 'Профиль',
}

# code, title, description, icon, category, counter_key, target, hidden, reward_nums
ACHIEVEMENTS = [
    # --- Территория ---
    ('territory_first_answer', 'Первый шаг', 'Верно решите первую задачу на карте', '⚔️', 'territory', COUNTER_TERRITORY_CORRECT, 1, False, 5),
    ('territory_answers_10', 'Разведчик', '10 верных ответов на карте', '🗺️', 'territory', COUNTER_TERRITORY_CORRECT, 10, False, 10),
    ('territory_answers_50', 'Завоеватель', '50 верных ответов на карте', '🏴', 'territory', COUNTER_TERRITORY_CORRECT, 50, False, 25),
    ('territory_answers_100', 'Ветеран карты', '100 верных ответов на карте', '🎖️', 'territory', COUNTER_TERRITORY_CORRECT, 100, False, 50),
    ('territory_answers_500', 'Легенда фронта', '500 верных ответов на карте', '👑', 'territory', COUNTER_TERRITORY_CORRECT, 500, False, 100),
    ('territory_damage_100', 'Удар по врагу', 'Нанесите 100 урона чужим кланам', '💥', 'territory', COUNTER_TERRITORY_DAMAGE, 100, False, 15),
    ('territory_damage_1000', 'Гроза кланов', 'Нанесите 1000 урона чужим кланам', '🔥', 'territory', COUNTER_TERRITORY_DAMAGE, 1000, False, 40),
    ('territory_damage_10000', 'Разрушитель', 'Нанесите 10000 урона чужим кланам', '☄️', 'territory', COUNTER_TERRITORY_DAMAGE, 10000, False, 150),
    ('territory_influence_100', 'Страж рубежа', 'Принесите клану 100 очков влияния', '🛡️', 'territory', COUNTER_TERRITORY_INFLUENCE, 100, False, 15),
    ('territory_influence_1000', 'Оплот клана', 'Принесите клану 1000 очков влияния', '🏰', 'territory', COUNTER_TERRITORY_INFLUENCE, 1000, False, 40),
    ('territory_influence_5000', 'Несокрушимый', 'Принесите клану 5000 очков влияния', '⚜️', 'territory', COUNTER_TERRITORY_INFLUENCE, 5000, False, 120),
    ('territory_capture_1', 'Захватчик', 'Захватите область у другого клана', '🚩', 'territory', COUNTER_TERRITORY_CAPTURES, 1, False, 20),
    ('territory_capture_10', 'Покоритель', '10 захватов чужих областей', '🏆', 'territory', COUNTER_TERRITORY_CAPTURES, 10, False, 60),
    ('neutral_capture_1', 'Пионер', 'Захватите нейтральную область', '🌄', 'territory', COUNTER_NEUTRAL_CAPTURES, 1, False, 10),
    # --- Прогресс ---
    ('level_5', 'Новичок', 'Достигните 5 уровня', '📈', 'progress', COUNTER_LEVEL, 5, False, 10),
    ('level_10', 'Боец', 'Достигните 10 уровня', '⭐', 'progress', COUNTER_LEVEL, 10, False, 20),
    ('level_25', 'Мастер', 'Достигните 25 уровня', '🌟', 'progress', COUNTER_LEVEL, 25, False, 50),
    ('level_50', 'Элита', 'Достигните 50 уровня', '💫', 'progress', COUNTER_LEVEL, 50, False, 100),
    ('level_100', 'Титан', 'Достигните 100 уровня', '🔱', 'progress', COUNTER_LEVEL, 100, True, 250),
    ('skills_10', 'Учёный тактик', 'Распределите 10 очков навыков', '📚', 'progress', COUNTER_SKILLS_SPENT, 10, False, 10),
    ('skills_30', 'Стратег', 'Распределите 30 очков навыков', '🧠', 'progress', COUNTER_SKILLS_SPENT, 30, False, 30),
    ('energy_25', 'Запас сил', 'Максимальная энергия 25 и выше', '⚡', 'progress', COUNTER_MAX_ENERGY, 25, False, 15),
    ('energy_40', 'Неутомимый', 'Максимальная энергия 40 и выше', '🔋', 'progress', COUNTER_MAX_ENERGY, 40, False, 35),
    # --- Экономика ---
    ('nums_earned_100', 'Первые Нумы', 'Заработайте 100 Нумов за решения', '💰', 'economy', COUNTER_NUMS_EARNED, 100, False, 10),
    ('nums_earned_1000', 'Копилка', 'Заработайте 1000 Нумов', '💎', 'economy', COUNTER_NUMS_EARNED, 1000, False, 30),
    ('nums_earned_10000', 'Банкир', 'Заработайте 10000 Нумов', '🏦', 'economy', COUNTER_NUMS_EARNED, 10000, False, 100),
    ('nums_spent_500', 'Покупатель', 'Потратьте 500 Нумов в лавке', '🛍️', 'economy', COUNTER_NUMS_SPENT, 500, False, 15),
    ('nums_spent_5000', 'Меценат', 'Потратьте 5000 Нумов', '💸', 'economy', COUNTER_NUMS_SPENT, 5000, False, 50),
    ('nums_balance_1000', 'Богач', 'Накопите 1000 Нумов на балансе', '🤑', 'economy', COUNTER_NUMS_BALANCE_MAX, 1000, False, 25),
    ('nums_transfer_1', 'Щедрость', 'Переведите Нумы другому игроку', '🤝', 'economy', COUNTER_NUMS_TRANSFERRED, 1, False, 10),
    ('nums_transfer_1000', 'Меценат друзей', 'Переведите 1000 Нумов другим', '🎁', 'economy', COUNTER_NUMS_TRANSFERRED, 1000, False, 40),
    # --- Лавка ---
    ('shop_first', 'Первая покупка', 'Купите предмет в лавке', '🛒', 'shop', COUNTER_SHOP_PURCHASES, 1, False, 5),
    ('shop_10', 'Постоянный клиент', '10 покупок в лавке', '🏪', 'shop', COUNTER_SHOP_PURCHASES, 10, False, 25),
    ('shop_50', 'Оптовик', '50 покупок в лавке', '📦', 'shop', COUNTER_SHOP_PURCHASES, 50, False, 75),
    ('chest_first', 'Любопытство', 'Откройте сундук', '🎁', 'shop', COUNTER_CHESTS_OPENED, 1, False, 10),
    ('chest_10', 'Кладоискатель', 'Откройте 10 сундуков', '📿', 'shop', COUNTER_CHESTS_OPENED, 10, False, 40),
    ('chest_50', 'Хранитель сокровищ', 'Откройте 50 сундуков', '👝', 'shop', COUNTER_CHESTS_OPENED, 50, False, 120),
    ('item_use_1', 'В деле', 'Используйте предмет из инвентаря', '✨', 'shop', COUNTER_ITEMS_USED, 1, False, 5),
    ('item_use_25', 'Алхимик', '25 использований предметов', '🧪', 'shop', COUNTER_ITEMS_USED, 25, False, 35),
    ('item_sell_5', 'Торговец', 'Продайте 5 предметов', '♻️', 'shop', COUNTER_ITEMS_SOLD, 5, False, 15),
    # --- Снаряжение ---
    ('equip_first', 'Вооружён', 'Наденьте предмет снаряжения', '🗡️', 'equipment', COUNTER_EQUIP_ACTIONS, 1, False, 5),
    ('equip_full', 'Полный комплект', 'Заполните все 6 слотов снаряжения', '🛡️', 'equipment', COUNTER_EQUIPMENT_SLOTS, 6, False, 50),
    ('enchant_5', 'Заточка +5', 'Заточите оружие до +5', '🔨', 'equipment', COUNTER_WEAPON_ENCHANT_MAX, 5, False, 20),
    ('enchant_10', 'Заточка +10', 'Заточите оружие до +10', '⚒️', 'equipment', COUNTER_WEAPON_ENCHANT_MAX, 10, False, 50),
    ('enchant_20', 'Мастер кузни', 'Заточите оружие до +20', '🔥', 'equipment', COUNTER_WEAPON_ENCHANT_MAX, 20, True, 150),
    # --- PvP ---
    ('pvp_arena', 'На арену!', 'Войдите на PvP Арену', '🏟️', 'pvp', COUNTER_PVP_ARENA_VISITS, 1, False, 5),
    ('pvp_first_win', 'Первая кровь', 'Победите в дуэли', '🥇', 'pvp', COUNTER_PVP_WINS, 1, False, 15),
    ('pvp_wins_5', 'Дуэлянт', '5 побед в дуэлях', '⚔️', 'pvp', COUNTER_PVP_WINS, 5, False, 30),
    ('pvp_wins_25', 'Гладиатор', '25 побед в дуэлях', '🏅', 'pvp', COUNTER_PVP_WINS, 25, False, 75),
    ('pvp_wins_100', 'Чемпион арены', '100 побед в дуэлях', '👑', 'pvp', COUNTER_PVP_WINS, 100, True, 200),
    ('pvp_duels_10', 'Боец арены', 'Участвуйте в 10 дуэлях', '🎯', 'pvp', COUNTER_PVP_DUELS, 10, False, 20),
    ('pvp_wager_win', 'На кону', 'Победите в дуэли со ставкой', '💵', 'pvp', COUNTER_PVP_WAGER_WINS, 1, False, 25),
    # --- Клан ---
    ('clan_join', 'В строю', 'Вступите в клан', '🛡️', 'clan', COUNTER_CLAN_JOINED, 1, False, 10),
    ('clan_create', 'Основатель', 'Создайте свой клан', '🏰', 'clan', COUNTER_CLAN_CREATED, 1, False, 30),
    ('clan_chat_1', 'Голос клана', 'Напишите в чат клана', '💬', 'clan', COUNTER_CLAN_CHAT, 1, False, 5),
    ('clan_chat_50', 'Оратор', '50 сообщений в чате клана', '📢', 'clan', COUNTER_CLAN_CHAT, 50, False, 40),
    ('clan_rank_3', 'Привилегия', 'Получите звание Маркиз или выше', '🎖️', 'clan', COUNTER_CLAN_RANK_TIER, 3, False, 35),
    ('clan_apply', 'Ищу братство', 'Подайте заявку в клан', '📜', 'clan', COUNTER_CLAN_APPLICATIONS, 1, False, 5),
    # --- Мир ---
    ('demogorgon_1', 'Охотник на демонов', 'Нанесите урон армии Демогоргонов', '😈', 'world', COUNTER_DEMOGORGON_HITS, 1, False, 15),
    ('structure_1', 'Строитель', 'Постройте сооружение на карте', '🏗️', 'world', COUNTER_STRUCTURES_BUILT, 1, False, 20),
    ('marker_1', 'Тактик', 'Поставьте метку клана на карте', '📍', 'world', COUNTER_MARKERS_SET, 1, False, 10),
    ('buff_1', 'Усиление', 'Примените бафф на себя или клан', '💊', 'world', COUNTER_BUFFS_APPLIED, 1, False, 10),
    # --- Профиль ---
    ('avatar_set', 'Лицо героя', 'Установите аватар', '🖼️', 'profile', COUNTER_AVATAR_SET, 1, False, 5),
    ('rename_1', 'Новое имя', 'Смените имя персонажа', '✏️', 'profile', COUNTER_RENAMES, 1, False, 5),
]

ACHIEVEMENT_BY_CODE = {a[0]: a for a in ACHIEVEMENTS}

CLAN_RANK_TIERS = {
    None: 0,
    'vassal': 1,
    'knight': 2,
    'baron': 2,
    'count': 2,
    'marquis': 3,
    'duke': 4,
}


def _models():
    m = _app_module()
    return m.UserStatCounter, m.UserAchievement


def _get_counter_row(user_id, key):
    db = _db()
    UserStatCounter, _ = _models()
    row = UserStatCounter.query.filter_by(user_id=user_id, counter_key=key).first()
    if not row:
        row = UserStatCounter(user_id=user_id, counter_key=key, value=0)
        db.session.add(row)
        db.session.flush()
    return row


def get_counter(user_id, key):
    UserStatCounter, _ = _models()
    row = UserStatCounter.query.filter_by(user_id=user_id, counter_key=key).first()
    return (row.value or 0) if row else 0


def increment_counter(user_id, key, delta=1):
    if not delta:
        return
    row = _get_counter_row(user_id, key)
    row.value = max(0, (row.value or 0) + delta)


def set_counter_max(user_id, key, value):
    row = _get_counter_row(user_id, key)
    row.value = max(row.value or 0, int(value))


def set_counter_if_higher(user_id, key, value):
    set_counter_max(user_id, key, value)


def _count_pvp_wins(user_id):
    PvPDuel = _app_module().PvPDuel
    return PvPDuel.query.filter_by(winner_id=user_id).count()


def _count_pvp_duels(user_id):
    from sqlalchemy import or_
    PvPDuel = _app_module().PvPDuel
    return PvPDuel.query.filter(
        or_(PvPDuel.challenger_id == user_id, PvPDuel.defender_id == user_id),
        PvPDuel.status == 'finished',
    ).count()


def _count_pvp_wager_wins(user_id):
    PvPDuel = _app_module().PvPDuel
    return PvPDuel.query.filter(
        PvPDuel.winner_id == user_id,
        PvPDuel.wager > 0,
    ).count()


def _count_shop_purchases(user_id):
    m = _app_module()
    UserShopPurchase = m.UserShopPurchase
    ShopItem = m.ShopItem
    SHOP_CONTEXT_TERRITORY = m.SHOP_CONTEXT_TERRITORY
    return (
        UserShopPurchase.query.filter_by(user_id=user_id)
        .join(ShopItem)
        .filter(ShopItem.shop_context == SHOP_CONTEXT_TERRITORY)
        .count()
    )


def _count_chests_opened(user_id):
    m = _app_module()
    UserShopPurchase = m.UserShopPurchase
    ShopItem = m.ShopItem
    SHOP_CONTEXT_TERRITORY = m.SHOP_CONTEXT_TERRITORY
    SHOP_CATEGORY_CHEST = m.SHOP_CATEGORY_CHEST
    return (
        UserShopPurchase.query.filter(
            UserShopPurchase.user_id == user_id,
            UserShopPurchase.chest_opened_at.isnot(None),
        )
        .join(ShopItem)
        .filter(
            ShopItem.shop_context == SHOP_CONTEXT_TERRITORY,
            ShopItem.category == SHOP_CATEGORY_CHEST,
        )
        .count()
    )


def _equipment_slots_filled(user_id):
    UserEquipment = _app_module().UserEquipment
    return UserEquipment.query.filter_by(user_id=user_id).count()


def _max_weapon_enchant(user_id):
    m = _app_module()
    UserShopPurchase = m.UserShopPurchase
    ShopItem = m.ShopItem
    SHOP_CONTEXT_TERRITORY = m.SHOP_CONTEXT_TERRITORY
    row = (
        UserShopPurchase.query.filter_by(user_id=user_id)
        .join(ShopItem)
        .filter(ShopItem.shop_context == SHOP_CONTEXT_TERRITORY)
        .order_by(UserShopPurchase.weapon_enchant_level.desc())
        .first()
    )
    return int(row.weapon_enchant_level or 0) if row else 0


def sync_user_achievement_counters(user_id):
    """Синхронизировать счётчики из существующих данных (ретроактивно)."""
    m = _app_module()
    db = m.db
    User = m.User
    UserTerritoryStats = m.UserTerritoryStats
    Clan = m.Clan

    user = db.session.get(User, user_id)
    if not user or user.is_admin:
        return

    stats = UserTerritoryStats.query.filter_by(user_id=user_id).first()
    if stats:
        set_counter_max(user_id, COUNTER_TERRITORY_DAMAGE, stats.total_damage_dealt or 0)
        set_counter_max(user_id, COUNTER_TERRITORY_INFLUENCE, stats.total_influence_points or 0)

    set_counter_max(user_id, COUNTER_LEVEL, user.level or 1)
    set_counter_max(user_id, COUNTER_NUMS_BALANCE_MAX, user.nums_balance or 0)
    set_counter_max(
        user_id,
        COUNTER_SKILLS_SPENT,
        (user.damage_skill or 0) + (user.defense_skill or 0) + (user.energy_skill or 0),
    )
    set_counter_max(user_id, COUNTER_MAX_ENERGY, user.energy)

    set_counter_max(user_id, COUNTER_PVP_WINS, _count_pvp_wins(user_id))
    set_counter_max(user_id, COUNTER_PVP_DUELS, _count_pvp_duels(user_id))
    set_counter_max(user_id, COUNTER_PVP_WAGER_WINS, _count_pvp_wager_wins(user_id))
    set_counter_max(user_id, COUNTER_SHOP_PURCHASES, _count_shop_purchases(user_id))
    set_counter_max(user_id, COUNTER_CHESTS_OPENED, _count_chests_opened(user_id))
    set_counter_max(user_id, COUNTER_EQUIPMENT_SLOTS, _equipment_slots_filled(user_id))
    set_counter_max(user_id, COUNTER_WEAPON_ENCHANT_MAX, _max_weapon_enchant(user_id))

    if user.avatar_filename:
        set_counter_max(user_id, COUNTER_AVATAR_SET, 1)
    if user.clan_id:
        set_counter_max(user_id, COUNTER_CLAN_JOINED, 1)
    clan_owned = Clan.query.filter_by(owner_id=user_id).first()
    if clan_owned:
        set_counter_max(user_id, COUNTER_CLAN_CREATED, 1)
    tier = CLAN_RANK_TIERS.get(user.clan_rank, 0)
    if user.clan_id and user.clan_obj and user.id == user.clan_obj.owner_id:
        tier = max(tier, 5)
    set_counter_max(user_id, COUNTER_CLAN_RANK_TIER, tier)


def check_and_unlock_achievements(user_id):
    """Проверить все достижения; вернуть список только что разблокированных кодов."""
    m = _app_module()
    db = m.db
    User = m.User
    _, UserAchievement = _models()

    user = db.session.get(User, user_id)
    if not user or user.is_admin:
        return []

    unlocked_codes = {
        r.achievement_code
        for r in UserAchievement.query.filter_by(user_id=user_id).all()
    }
    newly = []

    for code, title, desc, icon, cat, counter_key, target, hidden, reward in ACHIEVEMENTS:
        if code in unlocked_codes:
            continue
        current = get_counter(user_id, counter_key)
        if current < target:
            continue
        row = UserAchievement(user_id=user_id, achievement_code=code, unlocked_at=datetime.now())
        db.session.add(row)
        if reward > 0:
            user.nums_balance = (user.nums_balance or 0) + reward
        newly.append({
            'code': code,
            'title': title,
            'description': desc,
            'icon': icon,
            'reward_nums': reward,
        })
        unlocked_codes.add(code)

    return newly


def achievement_hook(user_id, *, commit=True):
    """Синхронизировать и проверить достижения после игрового действия."""
    db = _db()
    sync_user_achievement_counters(user_id)
    newly = check_and_unlock_achievements(user_id)
    if commit:
        db.session.commit()
    return newly


def get_achievements_payload(user_id):
    """Данные для UI: список достижений с прогрессом."""
    _, UserAchievement = _models()
    unlocked = {
        r.achievement_code: r.unlocked_at.isoformat() if r.unlocked_at else None
        for r in UserAchievement.query.filter_by(user_id=user_id).all()
    }
    items = []
    unlocked_count = 0
    for code, title, desc, icon, cat, counter_key, target, hidden, reward in ACHIEVEMENTS:
        is_unlocked = code in unlocked
        if is_unlocked:
            unlocked_count += 1
        current = get_counter(user_id, counter_key)
        if hidden and not is_unlocked:
            items.append({
                'code': code,
                'title': '???',
                'description': 'Секретное достижение',
                'icon': '❓',
                'category': cat,
                'category_label': ACHIEVEMENT_CATEGORIES.get(cat, cat),
                'target': target,
                'current': min(current, target),
                'unlocked': False,
                'hidden': True,
                'reward_nums': 0,
                'unlocked_at': None,
            })
        else:
            items.append({
                'code': code,
                'title': title,
                'description': desc,
                'icon': icon,
                'category': cat,
                'category_label': ACHIEVEMENT_CATEGORIES.get(cat, cat),
                'target': target,
                'current': min(current, target),
                'unlocked': is_unlocked,
                'hidden': False,
                'reward_nums': reward,
                'unlocked_at': unlocked.get(code),
            })
    return {
        'total': len(ACHIEVEMENTS),
        'unlocked_count': unlocked_count,
        'achievements': items,
        'categories': [{'id': k, 'label': v} for k, v in ACHIEVEMENT_CATEGORIES.items()],
    }


def get_extended_stats(user_id):
    """Расширенная статистика для блока «Статистика»."""
    User = _app_module().User
    user = User.query.get(user_id)
    if not user:
        return {}
    return {
        'territory_correct': get_counter(user_id, COUNTER_TERRITORY_CORRECT),
        'territory_damage': get_counter(user_id, COUNTER_TERRITORY_DAMAGE),
        'territory_influence': get_counter(user_id, COUNTER_TERRITORY_INFLUENCE),
        'territory_captures': get_counter(user_id, COUNTER_TERRITORY_CAPTURES),
        'level': user.level or 1,
        'nums_balance': user.nums_balance or 0,
        'nums_earned': get_counter(user_id, COUNTER_NUMS_EARNED),
        'shop_purchases': get_counter(user_id, COUNTER_SHOP_PURCHASES),
        'chests_opened': get_counter(user_id, COUNTER_CHESTS_OPENED),
        'pvp_wins': get_counter(user_id, COUNTER_PVP_WINS),
        'pvp_duels': get_counter(user_id, COUNTER_PVP_DUELS),
    }
