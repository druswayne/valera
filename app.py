from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, send_from_directory, send_file, after_this_request
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
from functools import wraps
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.pool import ThreadPoolExecutor
from sqlalchemy import case, cast, Float, Index, and_, func
from sqlalchemy.exc import IntegrityError
import json
import random
import os
import logging

try:
    from generate_boss_tasks import (
        generate_expression_task,
        generate_territory_computations,
        generate_equation_task,
        generate_fraction_property_task,
        generate_common_denominator_task,
        generate_proper_improper_fraction_task,
        generate_add_sub_fractions_task,
        generate_mul_div_fractions_task,
        generate_territory_gcd_lcm_task,
        generate_territory_motion_task,
        generate_territory_fraction_word_task,
        generate_territory_two_unknowns_task,
        generate_mixed_numbers_task,
        generate_joint_work_task,
    )
except ImportError:
    generate_expression_task = None
    generate_territory_computations = None
    generate_equation_task = None
    generate_fraction_property_task = None
    generate_common_denominator_task = None
    generate_proper_improper_fraction_task = None
    generate_add_sub_fractions_task = None
    generate_mul_div_fractions_task = None
    generate_territory_gcd_lcm_task = None
    generate_territory_motion_task = None
    generate_territory_fraction_word_task = None
    generate_territory_two_unknowns_task = None
    generate_mixed_numbers_task = None
    generate_joint_work_task = None
import re
import shutil
import tempfile
current_path = os.path.dirname(__file__)
os.chdir(current_path)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def now_utc_plus_3():
    """Текущее время сервера + 3 часа (для сохранения времени решения)."""
    return datetime.now() + timedelta(hours=3)

def list_animation_frame_urls(animation_name: str):
    """
    Возвращает отсортированный список URL кадров анимации из static/animation/<animation_name>/.
    Поддерживает изменение количества кадров и замену файлов без правок в шаблонах.
    """
    folder = os.path.join(app.root_path, 'static', 'animation', animation_name)
    try:
        filenames = [
            f for f in os.listdir(folder)
            if os.path.isfile(os.path.join(folder, f)) and f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp'))
        ]
    except FileNotFoundError:
        return []

    def sort_key(name: str):
        stem = os.path.splitext(name)[0]
        # Если имя файла — число (1.png, 10.png), сортируем по числу
        if stem.isdigit():
            return (0, int(stem))
        # Иначе — лексикографически
        return (1, stem.lower())

    filenames.sort(key=sort_key)
    return [url_for('static', filename=f'animation/{animation_name}/{fn}') for fn in filenames]

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///valera.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads/tasks'
app.config['AVATAR_FOLDER'] = 'static/uploads/avatars'
app.config['CLAN_FLAG_FOLDER'] = 'static/uploads/clan_flags'
app.config['SHOP_IMAGE_FOLDER'] = 'static/uploads/shop'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}


def _avatar_static_filename(avatar_filename):
    """Путь для url_for('static', filename=...): убирает лишний 'static/' если есть."""
    if not avatar_filename:
        return None
    s = avatar_filename.strip()
    if s.startswith('static/'):
        s = s[len('static/'):]
    return s

# Константы валидации
MAX_USER_NAME_LENGTH = 200
MIN_USER_NAME_LENGTH = 2

# Настройка планировщика задач
jobstores = {
    'default': SQLAlchemyJobStore(url='sqlite:///jobs.sqlite')
}
executors = {
    'default': ThreadPoolExecutor(20)
}
job_defaults = {
    'coalesce': False,
    'max_instances': 3
}
scheduler = BackgroundScheduler(jobstores=jobstores, executors=executors, job_defaults=job_defaults)

db = SQLAlchemy(app)

# Настройка Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Пожалуйста, войдите в систему для доступа к этой странице.'
login_manager.login_message_category = 'info'

# Модели
class Clan(db.Model):
    """Клан — участник битвы за территорию"""
    __tablename__ = 'clan'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    color = db.Column(db.String(20), default='#6b7280', nullable=False)
    flag_filename = db.Column(db.String(255), nullable=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    owner = db.relationship('User', foreign_keys=[owner_id], backref=db.backref('owned_clan', uselist=False), lazy=True)
    members_rel = db.relationship('User', back_populates='clan_obj', foreign_keys='User.clan_id', lazy=True)  # участники клана
    join_requests = db.relationship('ClanJoinRequest', backref='clan', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'color': self.color,
            'flag_url': url_for('static', filename=_avatar_static_filename(self.flag_filename)) if self.flag_filename else None,
            'owner_id': self.owner_id,
            'member_count': User.query.filter_by(clan_id=self.id).count()
        }


class ClanJoinRequest(db.Model):
    """Заявка на вступление в клан"""
    __tablename__ = 'clan_join_request'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    clan_id = db.Column(db.Integer, db.ForeignKey('clan.id'), nullable=False)
    status = db.Column(db.String(20), default='pending', nullable=False)  # pending, accepted, rejected
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='clan_join_requests', lazy=True)


class ClanChatMessage(db.Model):
    """Сообщение в чате клана"""
    __tablename__ = 'clan_chat_message'
    id = db.Column(db.Integer, primary_key=True)
    clan_id = db.Column(db.Integer, db.ForeignKey('clan.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    clan = db.relationship('Clan', backref=db.backref('chat_messages', lazy=True, order_by='ClanChatMessage.created_at'))
    user = db.relationship('User', backref='clan_chat_messages', lazy=True)


# Константы уровней и урона
# Базовые характеристики (без вложенных очков навыков)
USER_BASE_DAMAGE = 5
USER_BASE_DEFENSE = 5
USER_BASE_ENERGY = 10
INITIAL_SKILL_POINTS = 10
SKILL_POINTS_PER_LEVEL = 3

# Базовый XP за уровень после 10-го
XP_BASE_PER_LEVEL = 80  # было 100; прокачка ускорена на 20%
# Ускоренная прокачка до 10 уровня (примерно в 2 раза быстрее)
XP_BASE_PER_LEVEL_BELOW_10 = 40

def xp_required_for_level(level):
    """Суммарный опыт для достижения уровня level.

    Для уровней 2–10 используется уменьшенная база XP, чтобы ускорить раннюю прокачку.
    """
    if level <= 1:
        return 0
    base = XP_BASE_PER_LEVEL_BELOW_10 if level <= 10 else XP_BASE_PER_LEVEL
    return base * level * (level - 1) // 2

def xp_to_next_level(current_level):
    """Опыт, нужный для перехода с current_level на current_level+1."""
    base = XP_BASE_PER_LEVEL_BELOW_10 if current_level < 10 else XP_BASE_PER_LEVEL
    return base * current_level

def user_damage_by_level(level):
    """Урон персонажа (legacy). Используйте user.damage."""
    return USER_BASE_DAMAGE

def skill_points_total_for_level(level):
    """Всего очков навыков на уровне level."""
    return INITIAL_SKILL_POINTS + max(0, level - 1) * SKILL_POINTS_PER_LEVEL


def nums_reward_range_for_level(level):
    """Диапазон награды в Нумах за правильное решение задачи в зависимости от уровня. Возвращает (min_nums, max_nums)."""
    level = max(1, min(100, int(level or 1)))
    base = 40 + level * 5
    spread = 5 + level // 3
    low = max(10, base - spread)
    high = base + spread
    return (low, high)


def roll_nums_reward(level):
    """Случайная награда в Нумах за правильное решение с разбросом по уровню."""
    low, high = nums_reward_range_for_level(level)
    return random.randint(low, high)


class TerritoryTask(db.Model):
    """Задача для битвы за территорию (с опытом за решение)"""
    __tablename__ = 'territory_task'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    text = db.Column(db.Text, nullable=False)
    correct_answer = db.Column(db.String(200), nullable=False)
    image_filename = db.Column(db.String(255), nullable=True)
    xp_reward = db.Column(db.Integer, default=10, nullable=False)

    def to_dict_public(self):
        """Без правильного ответа — для выдачи клиенту"""
        d = {
            'id': self.id,
            'title': self.title,
            'text': self.text,
            'image_url': url_for('static', filename=self.image_filename) if self.image_filename else None,
            'xp_reward': self.xp_reward
        }
        if self.title == 'Основное свойство дроби' and '|' in (self.correct_answer or ''):
            d['answer_type'] = 'fraction'
        if self.title == 'Общий знаменатель' and self.correct_answer and self.correct_answer.count('|') >= 3:
            d['answer_type'] = 'common_denominator'
        if self.title == 'Правильные/неправильные дроби' and self.correct_answer and '|' in self.correct_answer:
            d['answer_type'] = 'mixed_fraction' if self.correct_answer.count('|') == 2 else 'fraction'
        if self.title in ('Сложение и вычитание дробей', 'Умножение и деление дробей', 'Смешанные числа'):
            d['answer_type'] = 'add_sub_fractions'
            if self.correct_answer and '|' in self.correct_answer:
                parts = self.correct_answer.split('|')
                d['int_part_zero'] = (len(parts) >= 1 and parts[0].strip() == '0')
        return d


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    character_name = db.Column(db.String(200), nullable=True)
    avatar_filename = db.Column(db.String(255), nullable=True)
    clan_id = db.Column(db.Integer, db.ForeignKey('clan.id'), nullable=True)
    level = db.Column(db.Integer, default=1, nullable=False)
    experience = db.Column(db.Integer, default=0, nullable=False)
    damage_skill = db.Column(db.Integer, default=0, nullable=False)
    defense_skill = db.Column(db.Integer, default=0, nullable=False)
    energy_skill = db.Column(db.Integer, default=0, nullable=False)
    current_energy = db.Column(db.Integer, nullable=True)  # None = полный запас
    energy_last_refill_at = db.Column(db.DateTime, nullable=True)  # время последнего восстановления
    nums_balance = db.Column(db.Integer, default=0, nullable=False)  # Нумы (валюта за правильные решения задач)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    clan_obj = db.relationship('Clan', back_populates='members_rel', foreign_keys=[clan_id], lazy=True)
    territory_stats_rel = db.relationship('UserTerritoryStats', backref='user', uselist=False, lazy=True, cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_territory_stats(self):
        """Получить статистику по территории (создаёт запись при необходимости)"""
        stats = UserTerritoryStats.query.filter_by(user_id=self.id).first()
        if not stats:
            stats = UserTerritoryStats(user_id=self.id)
            db.session.add(stats)
            db.session.flush()
        return stats

    def add_experience(self, xp):
        """Добавить опыт; возвращает (new_level, leveled_up)."""
        self.experience = (self.experience or 0) + xp
        new_level = self.level or 1
        while new_level < 100 and self.experience >= xp_required_for_level(new_level + 1):
            new_level += 1
        old_level = self.level or 1
        self.level = new_level
        return new_level, new_level > old_level

    @property
    def damage(self):
        """Текущий урон персонажа: база 5 + очки навыков."""
        return USER_BASE_DAMAGE + (self.damage_skill or 0)

    @property
    def defense(self):
        """Защита: база 5 + очки навыков."""
        return USER_BASE_DEFENSE + (self.defense_skill or 0)

    @property
    def energy(self):
        """Макс. энергия: база 5 + очки навыков."""
        return USER_BASE_ENERGY + (self.energy_skill or 0)

    def ensure_energy_refill(self):
        """Восстанавливать энергию каждые 30 мин на 20% от макс."""
        now = datetime.utcnow()
        max_e = self.energy
        last = self.energy_last_refill_at
        if last is None:
            if self.current_energy is None:
                self.current_energy = max_e
            self.energy_last_refill_at = now
            return
        elapsed_min = (now - last).total_seconds() / 60.0
        intervals = int(elapsed_min // 30)
        if intervals <= 0:
            return
        per_interval = max(1, round(max_e * 0.2))
        cur = self.current_energy if self.current_energy is not None else max_e
        self.current_energy = min(max_e, cur + intervals * per_interval)
        self.energy_last_refill_at = last + timedelta(minutes=intervals * 30)

    @property
    def current_energy_value(self):
        """Текущая энергия (после ensure_energy_refill)."""
        self.ensure_energy_refill()
        if self.current_energy is None:
            return self.energy
        return max(0, self.current_energy)

    @property
    def skill_points_total(self):
        """Всего очков навыков (старт 10 + за уровни)."""
        return skill_points_total_for_level(self.level or 1)

    @property
    def skill_points_available(self):
        """Свободные очки навыков."""
        spent = (self.damage_skill or 0) + (self.defense_skill or 0) + (self.energy_skill or 0)
        return max(0, self.skill_points_total - spent)

    @property
    def xp_in_current_level(self):
        """Опыт в рамках текущего уровня (от начала уровня до следующего)."""
        total = self.experience or 0
        base = xp_required_for_level(self.level or 1)
        return total - base

    @property
    def xp_needed_for_next_level(self):
        """Опыт, нужный для следующего уровня (в рамках текущего)."""
        return xp_to_next_level(self.level or 1)

    @property
    def total_damage_dealt(self):
        stats = UserTerritoryStats.query.filter_by(user_id=self.id).first()
        return (stats.total_damage_dealt or 0) if stats else 0

    @property
    def total_influence_points(self):
        stats = UserTerritoryStats.query.filter_by(user_id=self.id).first()
        return (stats.total_influence_points or 0) if stats else 0


class UserTerritoryStats(db.Model):
    """Статистика пользователя в битве за территорию"""
    __tablename__ = 'user_territory_stats'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True, nullable=False)
    total_damage_dealt = db.Column(db.Integer, default=0, nullable=False)  # урон при атаке чужих областей
    total_influence_points = db.Column(db.Integer, default=0, nullable=False)  # очки при защите своей области


# --- Лавка предметов (усиления / проклятия), покупка за Нумы ---
SHOP_CATEGORY_ENHANCEMENT = 'enhancement'
SHOP_CATEGORY_CURSE = 'curse'
SHOP_EFFECT_TYPES = ['damage', 'defense', 'current_energy', 'max_energy', 'xp_reward', 'nums_reward']


# Контекст лавки: territory = битва за территорию (кабинет), game = лавка призов на странице игры
SHOP_CONTEXT_TERRITORY = 'territory'
SHOP_CONTEXT_GAME = 'game'


class ShopItem(db.Model):
    """Товар лавки: усиление/проклятие (territory) или приз в прайсе (game)."""
    __tablename__ = 'shop_item'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    image_filename = db.Column(db.String(255), nullable=True)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Integer, nullable=False, default=0)  # в Нумах (territory) или в монетах (game)
    category = db.Column(db.String(20), nullable=False)  # enhancement / curse (territory) или для game
    sort_order = db.Column(db.Integer, default=0, nullable=False)
    shop_context = db.Column(db.String(20), nullable=False, default=SHOP_CONTEXT_TERRITORY)  # territory | game
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    effects = db.relationship('ShopItemEffect', backref='shop_item', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        """Для совместимости со старым API (game, api/shop-items)."""
        return {'id': self.id, 'name': self.name, 'price': self.price}


# Действие предмета лавки территории: self = личное, clan = на весь клан, region = на область
SHOP_EFFECT_TARGET_SELF = 'self'
SHOP_EFFECT_TARGET_CLAN = 'clan'
SHOP_EFFECT_TARGET_REGION = 'region'


class ShopItemEffect(db.Model):
    """Один эффект товара: тип (атака/защита/...), % изменения, действие (self/clan/region), длительность в минутах (NULL = без ограничения)"""
    __tablename__ = 'shop_item_effect'
    id = db.Column(db.Integer, primary_key=True)
    shop_item_id = db.Column(db.Integer, db.ForeignKey('shop_item.id'), nullable=False)
    effect_type = db.Column(db.String(30), nullable=False)  # damage, defense, current_energy, max_energy, xp_reward, nums_reward
    percent_change = db.Column(db.Float, nullable=False)  # для усиления > 0, для проклятия < 0
    target = db.Column(db.String(20), nullable=True)  # 'self' | 'clan' | 'region'
    duration_minutes = db.Column(db.Integer, nullable=True)  # NULL = неограниченно


class UserShopPurchase(db.Model):
    """Покупка пользователя в лавке (инвентарь)"""
    __tablename__ = 'user_shop_purchase'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    shop_item_id = db.Column(db.Integer, db.ForeignKey('shop_item.id'), nullable=False)
    purchased_at = db.Column(db.DateTime, default=datetime.utcnow)
    used_at = db.Column(db.DateTime, nullable=True)  # когда активирован (пока не используется)
    user = db.relationship('User', backref=db.backref('shop_purchases', lazy=True))
    shop_item = db.relationship('ShopItem', backref=db.backref('purchases', lazy=True))


class ActiveItemBuff(db.Model):
    """Активное улучшение от использованного предмета (с длительностью или разовое).
    Один из: user_id (личное), clan_id (на клан), region_index (на область)."""
    __tablename__ = 'active_item_buff'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    clan_id = db.Column(db.Integer, db.ForeignKey('clan.id'), nullable=True)
    region_index = db.Column(db.Integer, nullable=True)
    shop_item_id = db.Column(db.Integer, db.ForeignKey('shop_item.id'), nullable=False)
    used_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    one_shot = db.Column(db.Boolean, default=False, nullable=False)  # разовое: применить и удалить после одного действия
    user = db.relationship('User', backref=db.backref('active_buffs', lazy=True))
    clan = db.relationship('Clan', backref=db.backref('active_buffs', lazy=True))
    shop_item = db.relationship('ShopItem', backref=db.backref('active_buffs', lazy=True))


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

class Class(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    students_balance = db.Column(db.Integer, default=0)
    valera_balance = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    territory_fill_color = db.Column(db.String(20), nullable=True)
    territory_heraldry_filename = db.Column(db.String(255), nullable=True)
    students = db.relationship('Student', backref='class_obj', lazy=True, cascade='all, delete-orphan')
    student_selections = db.relationship('StudentSelection', backref='class_obj', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'students_balance': self.students_balance,
            'valera_balance': self.valera_balance,
            'total_balance': self.students_balance + self.valera_balance
        }

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey('class.id'), nullable=False)
    rating = db.Column(db.Integer, default=0, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    selections = db.relationship('StudentSelection', backref='student', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'class_id': self.class_id,
            'rating': self.rating or 0
        }

class StudentSelection(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey('class.id'), nullable=False)
    selected_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'student_id': self.student_id,
            'class_id': self.class_id,
            'selected_at': self.selected_at.isoformat() if self.selected_at else None
        }

class Prize(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    prize_type = db.Column(db.String(20), nullable=False)  # 'valera' или 'students'
    students_change = db.Column(db.Integer, default=0, nullable=False)  # Изменение баланса учащихся
    valera_change = db.Column(db.Integer, default=0, nullable=False)  # Изменение баланса Валеры
    probability = db.Column(db.String(20), default='medium', nullable=False)  # 'high', 'medium', 'low'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'prize_type': self.prize_type,
            'students_change': self.students_change,
            'valera_change': self.valera_change,
            'probability': self.probability
        }

class WeeklyTask(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    image_filename = db.Column(db.String(255), nullable=True)
    correct_answer = db.Column(db.String(200), nullable=False)
    is_active = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)  # Дата последнего обновления
    
    # Связь с решениями
    solutions = db.relationship('TaskSolution', backref='task', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'image_filename': self.image_filename,
            'correct_answer': self.correct_answer,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None
        }
    
    def is_solved(self):
        """Проверяет, решена ли задача"""
        return TaskSolution.query.filter_by(
            task_id=self.id,
            is_correct=True
        ).first() is not None

class TaskSolution(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('weekly_task.id'), nullable=False)
    user_name = db.Column(db.String(100), nullable=False)
    answer = db.Column(db.String(200), nullable=False)
    is_correct = db.Column(db.Boolean, default=False, nullable=False)
    solved_at = db.Column(db.DateTime, default=now_utc_plus_3)
    
    def to_dict(self):
        return {
            'id': self.id,
            'task_id': self.task_id,
            'user_name': self.user_name,
            'answer': self.answer,
            'is_correct': self.is_correct,
            'solved_at': self.solved_at.isoformat() if self.solved_at else None
        }

# Модели для рейд босса
class Boss(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    rewards_list = db.Column(db.Text, nullable=True)  # Список наград (текст)
    is_active = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    tasks = db.relationship('BossTask', backref='boss', lazy=True, cascade='all, delete-orphan')
    solutions = db.relationship('BossTaskSolution', backref='boss', lazy=True, cascade='all, delete-orphan')
    drops = db.relationship('BossDrop', backref='boss', lazy=True, cascade='all, delete-orphan')
    drop_rewards = db.relationship('BossDropReward', backref='boss', lazy=True, cascade='all, delete-orphan')
    
    def get_total_health(self) -> int:
        """Суммарное здоровье босса (сумма points всех задач) без загрузки всех задач в память."""
        from sqlalchemy import func
        total = db.session.query(func.sum(BossTask.points)).filter(BossTask.boss_id == self.id).scalar()
        return int(total or 0)

    def to_dict(self):
        total_health = self.get_total_health()
        return {
            'id': self.id,
            'name': self.name,
            'rewards_list': self.rewards_list,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'total_health': total_health,
            'current_health': self.get_current_health(total_health=total_health)
        }
    
    def get_current_health(self, total_health: int | None = None) -> int:
        """Возвращает текущее здоровье босса (сумма очков всех задач минус нанесенный урон)"""
        from sqlalchemy import func
        if total_health is None:
            total_health = self.get_total_health()
        # Вычисляем суммарный урон из правильно решенных задач
        damage_dealt = db.session.query(func.sum(BossTask.points)).join(
            BossTaskSolution, BossTaskSolution.task_id == BossTask.id
        ).filter(
            BossTaskSolution.boss_id == self.id,
            BossTaskSolution.is_correct == True
        ).scalar() or 0
        return int(max(0, int(total_health) - int(damage_dealt or 0)))

class BossTask(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    boss_id = db.Column(db.Integer, db.ForeignKey('boss.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    image_filename = db.Column(db.String(255), nullable=True)
    correct_answer = db.Column(db.String(200), nullable=False)
    points = db.Column(db.Integer, nullable=False, default=0)  # Стоимость в баллах (урон)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Индексы для оптимизации частых запросов
    __table_args__ = (
        Index('idx_boss_task_boss_id', 'boss_id'),
    )
    
    solutions = db.relationship('BossTaskSolution', backref='task', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self, is_solved_override: bool | None = None):
        """
        Возвращает dict для фронта/админки.
        is_solved_override: если передан, не делаем дополнительный запрос к BossTaskSolution.
        """
        return {
            'id': self.id,
            'boss_id': self.boss_id,
            'title': self.title,
            'description': self.description,
            'image_filename': self.image_filename,
            'correct_answer': self.correct_answer,
            'points': self.points,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'is_solved': bool(is_solved_override) if is_solved_override is not None else self.is_solved()
        }
    
    def is_solved(self):
        """Проверяет, решена ли задача правильно"""
        return BossTaskSolution.query.filter_by(
            task_id=self.id,
            is_correct=True
        ).first() is not None

class BossTaskSolution(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    boss_id = db.Column(db.Integer, db.ForeignKey('boss.id'), nullable=False)
    task_id = db.Column(db.Integer, db.ForeignKey('boss_task.id'), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey('class.id'), nullable=False)
    user_name = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('boss_user.id'), nullable=True)  # Связь с пользователем
    answer = db.Column(db.String(200), nullable=False)
    is_correct = db.Column(db.Boolean, default=False, nullable=False)
    solved_at = db.Column(db.DateTime, default=now_utc_plus_3)
    
    # Индексы для оптимизации запросов
    __table_args__ = (
        Index('idx_boss_task_solution_boss_id', 'boss_id'),
        Index('idx_boss_task_solution_task_id', 'task_id'),
        Index('idx_boss_task_solution_user_id', 'user_id'),
        Index('idx_boss_task_solution_is_correct', 'is_correct'),
        Index('idx_boss_task_solution_boss_task_correct', 'boss_id', 'task_id', 'is_correct'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'boss_id': self.boss_id,
            'task_id': self.task_id,
            'class_id': self.class_id,
            'user_name': self.user_name,
            'user_id': self.user_id,
            'answer': self.answer,
            'is_correct': self.is_correct,
            'solved_at': self.solved_at.isoformat() if self.solved_at else None
        }

class BossUser(db.Model):
    """Пользователь босса (сохраненные имена)"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)  # Фамилия и Имя
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Связи
    solutions = db.relationship('BossTaskSolution', backref='user', lazy=True)
    drop_rewards = db.relationship('BossDropReward', backref='user', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class BossDrop(db.Model):
    """Дроп босса"""
    id = db.Column(db.Integer, primary_key=True)
    boss_id = db.Column(db.Integer, db.ForeignKey('boss.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)  # Название дропа
    probability = db.Column(db.String(20), nullable=False)  # 'high', 'medium', 'very_low'
    # Максимальное количество этого дропа для одного пользователя (BossUser.id).
    # None/NULL = без ограничений.
    max_per_user = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Связи
    rewards = db.relationship('BossDropReward', backref='drop', lazy=True)
    
    # Индексы для оптимизации запросов
    __table_args__ = (
        Index('idx_boss_drop_boss_id', 'boss_id'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'boss_id': self.boss_id,
            'name': self.name,
            'probability': self.probability,
            'max_per_user': self.max_per_user,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def get_probability_value(self):
        """Возвращает числовое значение вероятности для расчета"""
        if self.probability == 'high':
            return 0.3  # 30%
        elif self.probability == 'medium':
            return 0.15  # 15%
        elif self.probability == 'very_low':
            return 0.05  # 5%
        return 0.1  # По умолчанию 10%

class BossDropReward(db.Model):
    """Выпавший дроп пользователю"""
    id = db.Column(db.Integer, primary_key=True)
    boss_id = db.Column(db.Integer, db.ForeignKey('boss.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('boss_user.id'), nullable=False)
    drop_id = db.Column(db.Integer, db.ForeignKey('boss_drop.id'), nullable=False)
    # Эти поля нужны, чтобы в админке показать, каким классом пользователь отвечал
    # в момент получения дропа (и при необходимости связать выдачу с задачей).
    task_id = db.Column(db.Integer, db.ForeignKey('boss_task.id'), nullable=True)
    class_id = db.Column(db.Integer, db.ForeignKey('class.id'), nullable=True)
    received_at = db.Column(db.DateTime, default=datetime.utcnow)

    task = db.relationship('BossTask', foreign_keys=[task_id], lazy=True)
    class_obj = db.relationship('Class', foreign_keys=[class_id], lazy=True)
    
    __table_args__ = (
        Index('idx_boss_drop_reward_boss_id', 'boss_id'),
        Index('idx_boss_drop_reward_user_id', 'user_id'),
        Index('idx_boss_drop_reward_drop_id', 'drop_id'),
        Index('idx_boss_drop_reward_boss_user', 'boss_id', 'user_id'),
        Index('idx_boss_drop_reward_received_at', 'received_at'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'boss_id': self.boss_id,
            'user_id': self.user_id,
            'drop_id': self.drop_id,
            'task_id': self.task_id,
            'class_id': self.class_id,
            'class_name': self.class_obj.name if self.class_obj else None,
            'user_name': self.user.name if self.user else '',
            'drop_name': self.drop.name if self.drop else '',
            'received_at': self.received_at.isoformat() if self.received_at else None
        }


# Генератор заданий для битвы за территорию (название; логика генерации — позже)
class TaskGenerator(db.Model):
    __tablename__ = 'task_generator'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)


# Битва за территорию: настройки областей (название, описание, заблокирована ли, генератор заданий)
class TerritoryRegionConfig(db.Model):
    __tablename__ = 'territory_region_config'
    id = db.Column(db.Integer, primary_key=True)
    region_index = db.Column(db.Integer, unique=True, nullable=False)
    display_name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=True)  # подсказка при наведении на название области
    is_locked = db.Column(db.Boolean, default=False, nullable=False)
    task_generator_id = db.Column(db.Integer, db.ForeignKey('task_generator.id'), nullable=True)
    task_generator = db.relationship('TaskGenerator', foreign_keys=[task_generator_id], lazy=True)


# Битва за территорию: состояние области (владелец, сила)
class TerritoryRegionState(db.Model):
    __tablename__ = 'territory_region_state'
    id = db.Column(db.Integer, primary_key=True)
    region_index = db.Column(db.Integer, unique=True, nullable=False)
    owner_class_id = db.Column(db.Integer, db.ForeignKey('class.id'), nullable=True)
    owner_clan_id = db.Column(db.Integer, db.ForeignKey('clan.id'), nullable=True)
    strength = db.Column(db.Integer, default=0, nullable=False)
    owner_class = db.relationship('Class', foreign_keys=[owner_class_id], lazy=True)
    owner_clan = db.relationship('Clan', foreign_keys=[owner_clan_id], lazy=True)
    __table_args__ = (
        Index('idx_territory_region_state_region', 'region_index'),
        Index('idx_territory_region_state_owner', 'owner_class_id'),
        Index('idx_territory_region_state_owner_clan', 'owner_clan_id'),
    )


# Битва за территорию: общие настройки (регистрация участников, захват областей)
class TerritoryBattleSetting(db.Model):
    __tablename__ = 'territory_battle_setting'
    id = db.Column(db.Integer, primary_key=True)
    registration_enabled = db.Column(db.Boolean, default=True, nullable=False)
    capture_enabled = db.Column(db.Boolean, default=True, nullable=False)
    capture_start_time = db.Column(db.DateTime, nullable=True)
    capture_end_time = db.Column(db.DateTime, nullable=True)


def get_territory_registration_enabled():
    """Проверить, включена ли регистрация участников в битве за территорию."""
    s = TerritoryBattleSetting.query.first()
    if not s:
        s = TerritoryBattleSetting(registration_enabled=True)
        db.session.add(s)
        db.session.commit()
    return s.registration_enabled


def get_territory_capture_settings():
    """Вернуть (capture_enabled, capture_start_time, capture_end_time). datetime — или None."""
    s = TerritoryBattleSetting.query.first()
    if not s:
        s = TerritoryBattleSetting(registration_enabled=True)
        db.session.add(s)
        db.session.commit()
    return (
        getattr(s, 'capture_enabled', True),
        getattr(s, 'capture_start_time', None),
        getattr(s, 'capture_end_time', None)
    )


# Декоратор для проверки прав администратора
def admin_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            flash('Доступ запрещен. Требуются права администратора.', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# Функции валидации
def validate_user_name(name):
    """
    Валидация имени пользователя
    Возвращает (is_valid, error_message)
    """
    if not name or not name.strip():
        return False, 'Имя не может быть пустым'
    
    name = name.strip()
    
    if len(name) < MIN_USER_NAME_LENGTH:
        return False, f'Имя должно содержать минимум {MIN_USER_NAME_LENGTH} символа'
    
    if len(name) > MAX_USER_NAME_LENGTH:
        return False, f'Имя не может быть длиннее {MAX_USER_NAME_LENGTH} символов'
    
    # Проверка на опасные символы (XSS защита)
    dangerous_patterns = ['<', '>', '&', '"', "'", '/', '\\', 'javascript:', 'onerror=', 'onclick=']
    for pattern in dangerous_patterns:
        if pattern.lower() in name.lower():
            return False, 'Имя содержит недопустимые символы'
    
    # Разрешаем только буквы, цифры, пробелы, дефисы и точки
    if not re.match(r'^[а-яА-ЯёЁa-zA-Z0-9\s\-\.]+$', name):
        return False, 'Имя может содержать только буквы, цифры, пробелы, дефисы и точки'
    
    return True, None

def validate_user_id(user_id):
    """
    Валидация и проверка существования user_id
    Возвращает (is_valid, user_object, error_message)
    """
    if user_id is None:
        return False, None, 'ID пользователя не указан'
    
    try:
        user_id = int(user_id)
    except (ValueError, TypeError):
        return False, None, 'Неверный формат ID пользователя'
    
    user = BossUser.query.get(user_id)
    if not user:
        return False, None, 'Пользователь не найден'
    
    return True, user, None

def process_drop_reward(boss_id, user_id, task_id, class_id=None, allow_multiple_drops_per_task=False):
    """
    Обрабатывает выпадение дропа при правильном ответе
    Возвращает (drop_reward_object, error_message)
    Использует транзакции для атомарности
    
    Args:
        boss_id: ID босса
        user_id: ID пользователя
        task_id: ID задачи
        allow_multiple_drops_per_task: Если False, пользователь может получить дроп только один раз за задачу
    """
    try:
        # Проверяем существование пользователя
        is_valid, user, error = validate_user_id(user_id)
        if not is_valid:
            return None, error
        
        # Получаем все дропы для этого босса
        drops = BossDrop.query.filter_by(boss_id=boss_id).all()
        if not drops:
            return None, None  # Нет дропов - это нормально

        # Учитываем лимит max_per_user для конкретного пользователя (по BossUser.id)
        # Если лимит достигнут — исключаем этот дроп из выбора.
        from sqlalchemy import func
        existing_counts = dict(
            db.session.query(BossDropReward.drop_id, func.count(BossDropReward.id))
            .filter(
                BossDropReward.boss_id == boss_id,
                BossDropReward.user_id == user_id
            )
            .group_by(BossDropReward.drop_id)
            .all()
        )

        eligible_drops = []
        for drop in drops:
            max_per_user = getattr(drop, 'max_per_user', None)
            if max_per_user is not None and max_per_user > 0:
                if existing_counts.get(drop.id, 0) >= max_per_user:
                    continue
            eligible_drops.append(drop)

        if not eligible_drops:
            logger.info(f"Нет доступных дропов для user_id={user_id} (все упёрлись в лимит max_per_user)")
            return None, None
        
        # Проверяем, не получил ли уже пользователь дроп за эту задачу
        if not allow_multiple_drops_per_task:
            # Проверяем напрямую по BossDropReward.task_id (логика "один дроп за одну задачу")
            existing_reward = BossDropReward.query.filter_by(
                boss_id=boss_id,
                user_id=user_id,
                task_id=task_id
            ).first()
            
            if existing_reward:
                logger.info(f"Пользователь {user_id} уже получил дроп за задачу {task_id}")
                return None, None  # Уже получил дроп за эту задачу
        
        # Сначала проверяем, выпал ли вообще шанс на дроп (20% вероятность)
        drop_chance = random.random()
        if drop_chance > 0.2:  # 20% вероятность получить дроп
            logger.info(f"Дроп не выпал: drop_chance={drop_chance:.3f} > 0.2 (пользователь {user_id}, задача {task_id})")
            return None, None  # Дроп не выпал
        
        logger.info(f"Дроп выпал! drop_chance={drop_chance:.3f} <= 0.2 (пользователь {user_id}, задача {task_id})")
        
        # Если шанс выпал, выбираем конкретный дроп с учетом их вероятностей
        # Всегда нормализуем вероятности для корректного расчета
        total_probability = sum(drop.get_probability_value() for drop in eligible_drops)
        
        if total_probability <= 0:
            return None, None
        
        # Нормализуем вероятности (сумма должна быть = 1.0)
        rand_value = random.random()
        cumulative = 0
        selected_drop = None
        
        for drop in eligible_drops:
            # Нормализуем вероятность каждого дропа
            prob = drop.get_probability_value() / total_probability
            cumulative += prob
            if rand_value <= cumulative:
                selected_drop = drop
                break
        
        # Если дроп выпал, сохраняем его в транзакции
        if selected_drop:
            try:
                # Доп. проверка лимита перед сохранением (защита от параллельных выдач)
                max_per_user = getattr(selected_drop, 'max_per_user', None)
                if max_per_user is not None and max_per_user > 0:
                    current_count = BossDropReward.query.filter_by(
                        boss_id=boss_id,
                        user_id=user_id,
                        drop_id=selected_drop.id
                    ).count()
                    if current_count >= max_per_user:
                        logger.info(
                            f"Лимит дропа достигнут: user_id={user_id}, drop_id={selected_drop.id}, "
                            f"count={current_count}, max_per_user={max_per_user}"
                        )
                        return None, None

                # Дополнительная проверка на дубликаты перед сохранением
                # (защита от race condition)
                duplicate_check = BossDropReward.query.filter_by(
                    boss_id=boss_id,
                    user_id=user_id,
                    task_id=task_id
                ).first()
                
                if duplicate_check and not allow_multiple_drops_per_task:
                    logger.info(f"Дроп уже был выдан пользователю {user_id} за задачу {task_id} (race condition)")
                    return None, None
                
                drop_reward = BossDropReward(
                    boss_id=boss_id,
                    user_id=user_id,
                    drop_id=selected_drop.id,
                    task_id=task_id,
                    class_id=class_id
                )
                db.session.add(drop_reward)
                db.session.commit()
                
                logger.info(f"Дроп выпал: user_id={user_id}, drop_id={selected_drop.id}, boss_id={boss_id}, task_id={task_id}")
                return drop_reward, None
            except IntegrityError as e:
                db.session.rollback()
                logger.error(f"Ошибка целостности при сохранении дропа: {e}")
                # Возможно, дроп уже был сохранен параллельно
                return None, None
            except Exception as e:
                db.session.rollback()
                logger.error(f"Неожиданная ошибка при сохранении дропа: {e}")
                return None, 'Ошибка при сохранении дропа'
        
        return None, None  # Дроп не выпал - это нормально
        
    except Exception as e:
        logger.error(f"Ошибка при обработке дропа: {e}")
        db.session.rollback()
        return None, 'Ошибка при обработке дропа'

# Функция для проверки расширения файла
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Функция обновления задачи недели
def update_weekly_task():
    """Обновляет задачу недели, выбирая случайную из нерешенных задач"""
    with app.app_context():
        try:
            # Получаем все задачи, которые еще не решены
            all_tasks = WeeklyTask.query.all()
            if not all_tasks:
                print("Нет задач для обновления")
                return
            
            unsolved_tasks = [task for task in all_tasks if not task.is_solved()]
            
            if not unsolved_tasks:
                # Если все задачи решены, активируем первую задачу
                print("Все задачи решены. Активирую первую задачу.")
                first_task = all_tasks[0]
                WeeklyTask.query.update({WeeklyTask.is_active: False})
                first_task.is_active = True
                first_task.last_updated = datetime.utcnow()
                db.session.commit()
                print(f"Задача недели обновлена (все задачи решены): {first_task.title}")
                return
            
            # Выбираем случайную задачу из нерешенных
            new_task = random.choice(unsolved_tasks)
            
            # Деактивируем все задачи
            WeeklyTask.query.update({WeeklyTask.is_active: False})
            
            # Активируем новую задачу
            new_task.is_active = True
            new_task.last_updated = datetime.utcnow()
            
            db.session.commit()
            print(f"Задача недели обновлена: {new_task.title}")
        except Exception as e:
            db.session.rollback()
            print(f"Ошибка при обновлении задачи недели: {e}")

# Функция для получения следующего воскресенья в 09:00
def get_next_sunday_9am():
    """Возвращает datetime следующего воскресенья в 09:00"""
    now = datetime.now()
    # Воскресенье = 6 (0 = понедельник, 6 = воскресенье)
    days_until_sunday = (6 - now.weekday()) % 7
    
    # Если сегодня воскресенье
    if days_until_sunday == 0:
        # Проверяем, прошло ли уже 09:00
        target_time = now.replace(hour=9, minute=0, second=0, microsecond=0)
        if now >= target_time:
            # Если уже прошло 09:00, берем следующее воскресенье
            days_until_sunday = 7
    
    next_sunday = now.replace(hour=9, minute=0, second=0, microsecond=0) + timedelta(days=days_until_sunday)
    return next_sunday

# Создание таблиц
with app.app_context():
    db.create_all()
    
    # Миграция: добавление новых колонок в таблицу Prize, если их нет
    try:
        from sqlalchemy import inspect, text
        
        inspector = inspect(db.engine)
        
        # Проверяем, существует ли таблица prize
        if 'prize' in inspector.get_table_names():
            columns = [col['name'] for col in inspector.get_columns('prize')]
            
            with db.engine.begin() as conn:
                if 'students_change' not in columns:
                    conn.execute(text('ALTER TABLE prize ADD COLUMN students_change INTEGER DEFAULT 0'))
                    print("Добавлена колонка students_change в таблицу prize")
                
                if 'valera_change' not in columns:
                    conn.execute(text('ALTER TABLE prize ADD COLUMN valera_change INTEGER DEFAULT 0'))
                    print("Добавлена колонка valera_change в таблицу prize")
                
                if 'probability' not in columns:
                    conn.execute(text("ALTER TABLE prize ADD COLUMN probability VARCHAR(20) DEFAULT 'medium'"))
                    print("Добавлена колонка probability в таблицу prize")
    except Exception as e:
        print(f"Ошибка при миграции таблицы prize: {e}")
        # Если таблица не существует, db.create_all() создаст её с нужными колонками
    
    # Миграция: добавление колонки rating в таблицу student, если её нет
    try:
        from sqlalchemy import inspect, text
        
        inspector = inspect(db.engine)
        if 'student' in inspector.get_table_names():
            columns = [col['name'] for col in inspector.get_columns('student')]
            if 'rating' not in columns:
                with db.engine.begin() as conn:
                    conn.execute(text('ALTER TABLE student ADD COLUMN rating INTEGER DEFAULT 0'))
                    print("Добавлена колонка rating в таблицу student")
    except Exception as e:
        print(f"Ошибка при миграции таблицы student (rating): {e}")
    
    # Миграция: добавление таблиц для задач недели
    try:
        from sqlalchemy import inspect, text
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        
        if 'weekly_task' not in tables or 'task_solution' not in tables:
            db.create_all()
            print("Созданы таблицы для задач недели")
        else:
            # Проверяем наличие колонки last_updated
            if 'weekly_task' in tables:
                columns = [col['name'] for col in inspector.get_columns('weekly_task')]
                if 'last_updated' not in columns:
                    with db.engine.begin() as conn:
                        conn.execute(text('ALTER TABLE weekly_task ADD COLUMN last_updated DATETIME'))
                        print("Добавлена колонка last_updated в таблицу weekly_task")
    except Exception as e:
        print(f"Ошибка при создании таблиц для задач: {e}")
        db.create_all()
    
    # Миграция: добавление таблиц для рейд босса
    try:
        from sqlalchemy import inspect, text
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        
        if 'boss' not in tables or 'boss_task' not in tables or 'boss_task_solution' not in tables:
            db.create_all()
            print("Созданы таблицы для рейд босса")
        
        # Миграция: добавление новых таблиц для пользователей, дропов и выпавших дропов
        if 'boss_user' not in tables:
            db.create_all()
            print("Созданы таблицы для пользователей босса")
        
        if 'boss_drop' not in tables:
            db.create_all()
            print("Созданы таблицы для дропов босса")
        
        if 'boss_drop_reward' not in tables:
            db.create_all()
            print("Созданы таблицы для выпавших дропов")
        
        # Миграция: добавление колонки user_id в boss_task_solution, если её нет
        if 'boss_task_solution' in tables:
            columns = [col['name'] for col in inspector.get_columns('boss_task_solution')]
            if 'user_id' not in columns:
                with db.engine.begin() as conn:
                    # SQLite не поддерживает REFERENCES в ALTER TABLE, добавляем просто INTEGER
                    conn.execute(text('ALTER TABLE boss_task_solution ADD COLUMN user_id INTEGER'))
                    print("Добавлена колонка user_id в таблицу boss_task_solution")

        # Миграция: добавление колонки max_per_user в boss_drop, если её нет
        if 'boss_drop' in tables:
            columns = [col['name'] for col in inspector.get_columns('boss_drop')]
            if 'max_per_user' not in columns:
                with db.engine.begin() as conn:
                    conn.execute(text('ALTER TABLE boss_drop ADD COLUMN max_per_user INTEGER'))
                    print("Добавлена колонка max_per_user в таблицу boss_drop")

        # Миграция: добавление колонок task_id и class_id в boss_drop_reward, если их нет
        if 'boss_drop_reward' in tables:
            columns = [col['name'] for col in inspector.get_columns('boss_drop_reward')]
            if 'task_id' not in columns:
                with db.engine.begin() as conn:
                    # SQLite: без REFERENCES в ALTER TABLE
                    conn.execute(text('ALTER TABLE boss_drop_reward ADD COLUMN task_id INTEGER'))
                    print("Добавлена колонка task_id в таблицу boss_drop_reward")
            if 'class_id' not in columns:
                with db.engine.begin() as conn:
                    conn.execute(text('ALTER TABLE boss_drop_reward ADD COLUMN class_id INTEGER'))
                    print("Добавлена колонка class_id в таблицу boss_drop_reward")
        
        # Создание индексов для оптимизации (если их еще нет)
        try:
            # Проверяем и создаем индексы для boss_task
            if 'boss_task' in tables:
                existing_indexes = [idx['name'] for idx in inspector.get_indexes('boss_task')]
                if 'idx_boss_task_boss_id' not in existing_indexes:
                    with db.engine.begin() as conn:
                        conn.execute(text('CREATE INDEX IF NOT EXISTS idx_boss_task_boss_id ON boss_task(boss_id)'))
                        print("Создан индекс idx_boss_task_boss_id")

            # Проверяем и создаем индексы для boss_task_solution
            if 'boss_task_solution' in tables:
                existing_indexes = [idx['name'] for idx in inspector.get_indexes('boss_task_solution')]
                indexes_to_create = [
                    ('idx_boss_task_solution_boss_id', 'boss_id'),
                    ('idx_boss_task_solution_task_id', 'task_id'),
                    ('idx_boss_task_solution_user_id', 'user_id'),
                    ('idx_boss_task_solution_is_correct', 'is_correct'),
                ]
                for idx_name, col_name in indexes_to_create:
                    if idx_name not in existing_indexes:
                        with db.engine.begin() as conn:
                            conn.execute(text(f'CREATE INDEX IF NOT EXISTS {idx_name} ON boss_task_solution({col_name})'))
                            print(f"Создан индекс {idx_name}")

                # Уникальный индекс: только ОДНО правильное решение на задачу (защита от race condition)
                # SQLite поддерживает partial indexes (WHERE ...) в современных версиях.
                with db.engine.begin() as conn:
                    conn.execute(text(
                        'CREATE UNIQUE INDEX IF NOT EXISTS uq_boss_task_solution_one_correct_per_task '
                        'ON boss_task_solution(boss_id, task_id) WHERE is_correct = 1'
                    ))
                    print("Проверен/создан уникальный индекс uq_boss_task_solution_one_correct_per_task")
            
            # Проверяем и создаем индексы для boss_drop
            if 'boss_drop' in tables:
                existing_indexes = [idx['name'] for idx in inspector.get_indexes('boss_drop')]
                if 'idx_boss_drop_boss_id' not in existing_indexes:
                    with db.engine.begin() as conn:
                        conn.execute(text('CREATE INDEX IF NOT EXISTS idx_boss_drop_boss_id ON boss_drop(boss_id)'))
                        print("Создан индекс idx_boss_drop_boss_id")
            
            # Проверяем и создаем индексы для boss_drop_reward
            if 'boss_drop_reward' in tables:
                existing_indexes = [idx['name'] for idx in inspector.get_indexes('boss_drop_reward')]
                indexes_to_create = [
                    ('idx_boss_drop_reward_boss_id', 'boss_id'),
                    ('idx_boss_drop_reward_user_id', 'user_id'),
                    ('idx_boss_drop_reward_drop_id', 'drop_id'),
                ]
                for idx_name, col_name in indexes_to_create:
                    if idx_name not in existing_indexes:
                        with db.engine.begin() as conn:
                            conn.execute(text(f'CREATE INDEX IF NOT EXISTS {idx_name} ON boss_drop_reward({col_name})'))
                            print(f"Создан индекс {idx_name}")

                # Уникальный индекс: один дроп за одну задачу для пользователя (если task_id указан)
                with db.engine.begin() as conn:
                    conn.execute(text(
                        'CREATE UNIQUE INDEX IF NOT EXISTS uq_boss_drop_reward_one_per_task '
                        'ON boss_drop_reward(boss_id, user_id, task_id) WHERE task_id IS NOT NULL'
                    ))
                    print("Проверен/создан уникальный индекс uq_boss_drop_reward_one_per_task")
        except Exception as e:
            print(f"Ошибка при создании индексов: {e}")
            # Индексы не критичны, продолжаем работу
    except Exception as e:
        print(f"Ошибка при создании таблиц для рейд босса: {e}")
        db.create_all()
    
    # Миграция: таблицы и настройки для битвы за территорию
    try:
        from sqlalchemy import inspect, text
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        
        if 'territory_region_config' not in tables or 'territory_region_state' not in tables:
            db.create_all()
            print("Созданы таблицы для битвы за территорию")
        
        # Таблица и колонка генератора заданий — до любого запроса к TerritoryRegionConfig
        if 'task_generator' not in tables:
            db.create_all()
            print("Создана таблица task_generator")
        if 'territory_region_config' in tables:
            columns = [col['name'] for col in inspector.get_columns('territory_region_config')]
            with db.engine.begin() as conn:
                if 'task_generator_id' not in columns:
                    conn.execute(text('ALTER TABLE territory_region_config ADD COLUMN task_generator_id INTEGER'))
                    print("Добавлена колонка task_generator_id в territory_region_config")
                if 'description' not in columns:
                    conn.execute(text('ALTER TABLE territory_region_config ADD COLUMN description TEXT'))
                    print("Добавлена колонка description в territory_region_config")
        
        if 'class' in tables:
            columns = [col['name'] for col in inspector.get_columns('class')]
            with db.engine.begin() as conn:
                if 'territory_fill_color' not in columns:
                    conn.execute(text('ALTER TABLE class ADD COLUMN territory_fill_color VARCHAR(20)'))
                    print("Добавлена колонка territory_fill_color в class")
                if 'territory_heraldry_filename' not in columns:
                    conn.execute(text('ALTER TABLE class ADD COLUMN territory_heraldry_filename VARCHAR(255)'))
                    print("Добавлена колонка territory_heraldry_filename в class")
        
        # Регионы Болгарии (28 областей): BG-01..BG-26, BG-28 Yambol, BG-27 Shumen
        BULGARIA_REGION_COUNT = 28
        default_bulgaria_names = [
            'Blagoevgrad', 'Burgas', 'Varna', 'Veliko Tarnovo', 'Vidin', 'Vratsa', 'Gabrovo', 'Dobrich',
            'Kardzhali', 'Kyustendil', 'Lovech', 'Montana', 'Pazardzhik', 'Pernik', 'Pleven', 'Plovdiv',
            'Razgrad', 'Ruse', 'Silistra', 'Sliven', 'Smolyan', 'Sofia-Grad', 'Sofia', 'Stara Zagora',
            'Targovishte', 'Haskovo', 'Yambol', 'Shumen'
        ]
        if 'territory_region_config' in tables and TerritoryRegionConfig.query.count() == 0:
            for i, name in enumerate(default_bulgaria_names):
                cfg = TerritoryRegionConfig(region_index=i, display_name=name, is_locked=(i == 21))  # Sofia-Grad
                db.session.add(cfg)
            db.session.commit()
            print("Заполнены настройки областей по умолчанию (Болгария)")
        elif 'territory_region_config' in tables:
            # Миграция: добавить недостающие регионы (если было 14, добавить 14..27)
            existing_indices = {r.region_index for r in TerritoryRegionConfig.query.all()}
            for i in range(BULGARIA_REGION_COUNT):
                if i not in existing_indices and i < len(default_bulgaria_names):
                    db.session.add(TerritoryRegionConfig(region_index=i, display_name=default_bulgaria_names[i], is_locked=(i == 21)))
            db.session.commit()
            if 'territory_region_state' in tables:
                existing_state_indices = {s.region_index for s in TerritoryRegionState.query.all()}
                for i in range(BULGARIA_REGION_COUNT):
                    if i not in existing_state_indices:
                        db.session.add(TerritoryRegionState(region_index=i, owner_class_id=None, owner_clan_id=None, strength=0))
                db.session.commit()
        
        if 'territory_region_state' in tables and TerritoryRegionState.query.count() == 0:
            for i in range(BULGARIA_REGION_COUNT):
                state = TerritoryRegionState(region_index=i, owner_class_id=None, owner_clan_id=None, strength=0)
                db.session.add(state)
            db.session.commit()
            print("Заполнены начальные состояния областей")
        
        if 'territory_battle_setting' not in tables:
            db.create_all()
            print("Создана таблица territory_battle_setting")
        tables = inspector.get_table_names()
        if 'territory_battle_setting' in tables:
            columns = [col['name'] for col in inspector.get_columns('territory_battle_setting')]
            with db.engine.begin() as conn:
                if 'capture_enabled' not in columns:
                    conn.execute(text('ALTER TABLE territory_battle_setting ADD COLUMN capture_enabled BOOLEAN DEFAULT 1 NOT NULL'))
                    print("Добавлена колонка capture_enabled в territory_battle_setting")
                if 'capture_start_time' not in columns:
                    conn.execute(text('ALTER TABLE territory_battle_setting ADD COLUMN capture_start_time DATETIME'))
                    print("Добавлена колонка capture_start_time в territory_battle_setting")
                if 'capture_end_time' not in columns:
                    conn.execute(text('ALTER TABLE territory_battle_setting ADD COLUMN capture_end_time DATETIME'))
                    print("Добавлена колонка capture_end_time в territory_battle_setting")
        if 'territory_battle_setting' in tables and TerritoryBattleSetting.query.count() == 0:
            s = TerritoryBattleSetting(registration_enabled=True)
            db.session.add(s)
            db.session.commit()
            print("Создана запись настроек битвы за территорию")
    except Exception as e:
        print(f"Ошибка при миграции битвы за территорию: {e}")
        db.create_all()

    # Лавка предметов (shop_item, shop_item_effect, user_shop_purchase)
    try:
        from sqlalchemy import inspect as _inspect
        inspector = _inspect(db.engine)
        tables = inspector.get_table_names()
        if 'shop_item' not in tables or 'shop_item_effect' not in tables or 'user_shop_purchase' not in tables:
            db.create_all()
            print("Созданы таблицы лавки: shop_item, shop_item_effect, user_shop_purchase")
        if 'shop_item' in tables:
            columns = [col['name'] for col in inspector.get_columns('shop_item')]
            with db.engine.begin() as conn:
                if 'image_filename' not in columns:
                    conn.execute(text('ALTER TABLE shop_item ADD COLUMN image_filename VARCHAR(255)'))
                    print("Добавлена колонка image_filename в shop_item")
                if 'description' not in columns:
                    conn.execute(text('ALTER TABLE shop_item ADD COLUMN description TEXT'))
                    print("Добавлена колонка description в shop_item")
                if 'category' not in columns:
                    conn.execute(text("ALTER TABLE shop_item ADD COLUMN category VARCHAR(20) DEFAULT 'enhancement'"))
                    print("Добавлена колонка category в shop_item")
                if 'sort_order' not in columns:
                    conn.execute(text('ALTER TABLE shop_item ADD COLUMN sort_order INTEGER DEFAULT 0'))
                    print("Добавлена колонка sort_order в shop_item")
                if 'shop_context' not in columns:
                    conn.execute(text("ALTER TABLE shop_item ADD COLUMN shop_context VARCHAR(20) NOT NULL DEFAULT 'territory'"))
                    print("Добавлена колонка shop_context в shop_item")
    except Exception as e:
        print(f"Ошибка при создании таблиц лавки: {e}")
        db.create_all()

    # Миграция: кланы и пользователи (character_name, clan_id, avatar, territory stats)
    try:
        from sqlalchemy import inspect, text
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        if 'clan' not in tables or 'clan_join_request' not in tables or 'user_territory_stats' not in tables or 'clan_chat_message' not in tables:
            db.create_all()
            print("Созданы таблицы clan, clan_join_request, user_territory_stats, clan_chat_message")
        if 'user' in tables:
            columns = [col['name'] for col in inspector.get_columns('user')]
            with db.engine.begin() as conn:
                if 'character_name' not in columns:
                    conn.execute(text('ALTER TABLE user ADD COLUMN character_name VARCHAR(200)'))
                    print("Добавлена колонка character_name в user")
                if 'avatar_filename' not in columns:
                    conn.execute(text('ALTER TABLE user ADD COLUMN avatar_filename VARCHAR(255)'))
                    print("Добавлена колонка avatar_filename в user")
                if 'clan_id' not in columns:
                    conn.execute(text('ALTER TABLE user ADD COLUMN clan_id INTEGER'))
                    print("Добавлена колонка clan_id в user")
                if 'level' not in columns:
                    conn.execute(text('ALTER TABLE user ADD COLUMN level INTEGER DEFAULT 1'))
                    print("Добавлена колонка level в user")
                if 'experience' not in columns:
                    conn.execute(text('ALTER TABLE user ADD COLUMN experience INTEGER DEFAULT 0'))
                    print("Добавлена колонка experience в user")
                if 'damage_skill' not in columns:
                    conn.execute(text('ALTER TABLE user ADD COLUMN damage_skill INTEGER DEFAULT 0'))
                    print("Добавлена колонка damage_skill в user")
                if 'defense_skill' not in columns:
                    conn.execute(text('ALTER TABLE user ADD COLUMN defense_skill INTEGER DEFAULT 0'))
                    print("Добавлена колонка defense_skill в user")
                if 'energy_skill' not in columns:
                    conn.execute(text('ALTER TABLE user ADD COLUMN energy_skill INTEGER DEFAULT 0'))
                    print("Добавлена колонка energy_skill в user")
                if 'current_energy' not in columns:
                    conn.execute(text('ALTER TABLE user ADD COLUMN current_energy INTEGER'))
                    print("Добавлена колонка current_energy в user")
                if 'energy_last_refill_at' not in columns:
                    conn.execute(text('ALTER TABLE user ADD COLUMN energy_last_refill_at TIMESTAMP'))
                    print("Добавлена колонка energy_last_refill_at в user")
                if 'nums_balance' not in columns:
                    conn.execute(text('ALTER TABLE user ADD COLUMN nums_balance INTEGER DEFAULT 0 NOT NULL'))
                    print("Добавлена колонка nums_balance в user")
        if 'territory_task' not in tables:
            db.create_all()
            print("Создана таблица territory_task")
        if 'territory_task' in tables and TerritoryTask.query.count() == 0:
            default_tasks = [
                ('Сумма', 'Чему равна сумма 15 + 27?', '42', 10),
                ('Произведение', 'Чему равно 6 × 8?', '48', 10),
                ('Квадрат', 'Чему равен квадрат числа 7?', '49', 10),
                ('Уравнение', 'Найдите x: 2x + 10 = 24', '7', 15),
                ('Периметр', 'Периметр квадрата 20 см. Чему равна сторона?', '5', 10),
                ('Дробь', 'Сократите дробь 12/18 до несократимой. Напишите только числитель.', '2', 15),
                ('Степень', 'Чему равно 2^5?', '32', 10),
                ('Проценты', '20% от 150 — это сколько?', '30', 10),
                ('Площадь', 'Площадь прямоугольника 24 см², одна сторона 4 см. Чему равна вторая?', '6', 15),
                ('Среднее', 'Среднее арифметическое чисел 10, 20 и 30?', '20', 10),
            ]
            for title, text, answer, xp in default_tasks:
                db.session.add(TerritoryTask(title=title, text=text, correct_answer=answer, xp_reward=xp))
            db.session.commit()
            print("Заполнены задачи для битвы за территорию")
        if 'territory_region_state' in tables:
            columns = [col['name'] for col in inspector.get_columns('territory_region_state')]
            if 'owner_clan_id' not in columns:
                with db.engine.begin() as conn:
                    conn.execute(text('ALTER TABLE territory_region_state ADD COLUMN owner_clan_id INTEGER'))
                    print("Добавлена колонка owner_clan_id в territory_region_state")
    except Exception as e:
        print(f"Ошибка при миграции кланов: {e}")
        db.create_all()

    # Создание директорий для загрузки изображений
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(os.path.join(app.root_path, 'static', 'uploads', 'territory_heraldry'), exist_ok=True)
    os.makedirs(os.path.join(app.root_path, app.config['AVATAR_FOLDER']), exist_ok=True)
    os.makedirs(os.path.join(app.root_path, app.config['CLAN_FLAG_FOLDER']), exist_ok=True)
    
    # Создание администратора по умолчанию (если его нет)
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        admin = User(username='admin', is_admin=True)
        admin.set_password('admin')  # Пароль по умолчанию - измените его!
        db.session.add(admin)
        db.session.commit()
    
    # Проверяем, есть ли активная задача, если нет - создаем из нерешенных
    active_task = WeeklyTask.query.filter_by(is_active=True).first()
    if not active_task:
        all_tasks = WeeklyTask.query.all()
        if all_tasks:
            unsolved_tasks = [task for task in all_tasks if not task.is_solved()]
            if unsolved_tasks:
                # Выбираем случайную задачу из нерешенных
                new_task = random.choice(unsolved_tasks)
                new_task.is_active = True
                new_task.last_updated = datetime.utcnow()
                db.session.commit()
                print(f"Активирована задача недели: {new_task.title}")
            elif all_tasks:
                # Если все задачи решены, активируем первую
                first_task = all_tasks[0]
                first_task.is_active = True
                first_task.last_updated = datetime.utcnow()
                db.session.commit()
                print(f"Активирована задача недели (все задачи решены): {first_task.title}")
    
    # Запуск планировщика задач
    if not scheduler.running:
        scheduler.start()
        
        # Проверяем, не пропущена ли дата обновления задачи
        active_task = WeeklyTask.query.filter_by(is_active=True).first()
        if active_task and active_task.last_updated:
            # Вычисляем следующее воскресенье от времени последнего обновления
            task_update_time = active_task.last_updated
            if task_update_time.tzinfo:
                task_update_time = task_update_time.replace(tzinfo=None)
            
            # Вычисляем следующее воскресенье в 09:00 от времени обновления задачи
            days_until_sunday = (6 - task_update_time.weekday()) % 7
            if days_until_sunday == 0:
                target_time = task_update_time.replace(hour=9, minute=0, second=0, microsecond=0)
                if task_update_time >= target_time:
                    days_until_sunday = 7
            
            next_sunday_from_update = task_update_time.replace(hour=9, minute=0, second=0, microsecond=0) + timedelta(days=days_until_sunday)
            
            # Если следующее воскресенье уже прошло, обновляем задачу сейчас
            now = datetime.now()
            if next_sunday_from_update < now:
                print(f"Обнаружена пропущенная дата обновления задачи ({next_sunday_from_update}). Обновляю задачу сейчас...")
                update_weekly_task()
                print("Задача обновлена. Планирую следующее обновление на воскресенье в 09:00")
        
        # Добавляем регулярную задачу на каждое воскресенье в 09:00
        scheduler.add_job(
            update_weekly_task,
            'cron',
            day_of_week='sun',
            hour=9,
            minute=0,
            id='update_weekly_task',
            replace_existing=True
        )
        print("Планировщик задач запущен. Задача недели будет обновляться каждое воскресенье в 09:00")

# Маршруты авторизации
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = (request.form.get('username') or '').strip()
        password = request.form.get('password')
        
        user = User.query.filter(func.lower(User.username) == username.lower()).first() if username else None
        
        if user and user.check_password(password):
            login_user(user)
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            if user.is_admin:
                return redirect(url_for('index'))
            return redirect(url_for('cabinet'))
        else:
            flash('Неверное имя пользователя или пароль', 'error')
    
    return render_template('login.html', registration_enabled=get_territory_registration_enabled())

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы успешно вышли из системы', 'info')
    return redirect(url_for('territory_battle_page'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if not get_territory_registration_enabled():
        flash('Регистрация временно отключена администратором.', 'info')
        return redirect(url_for('index'))
    if current_user.is_authenticated:
        return redirect(url_for('cabinet'))
    clans = Clan.query.order_by(Clan.name).all()
    if request.method == 'POST':
        username = (request.form.get('username') or '').strip()
        password = request.form.get('password')
        password_confirm = request.form.get('password_confirm')
        character_name = (request.form.get('character_name') or '').strip()
        clan_id = request.form.get('clan_id', type=int)
        if not username or len(username) < 3:
            flash('Логин должен быть не менее 3 символов', 'error')
            return render_template('register.html', clans=clans)
        if User.query.filter(func.lower(User.username) == username.lower()).first():
            flash('Такой логин уже занят', 'error')
            return render_template('register.html', clans=clans)
        if not password or len(password) < 6:
            flash('Пароль должен быть не менее 6 символов', 'error')
            return render_template('register.html', clans=clans)
        if password != password_confirm:
            flash('Пароли не совпадают', 'error')
            return render_template('register.html', clans=clans)
        is_valid, err = validate_user_name(character_name if character_name else 'A')
        if character_name and not is_valid:
            flash(err or 'Некорректное имя персонажа', 'error')
            return render_template('register.html', clans=clans)
        user = User(username=username, character_name=character_name or username)
        user.set_password(password)
        db.session.add(user)
        db.session.flush()
        if clan_id:
            clan = Clan.query.get(clan_id)
            if clan:
                req = ClanJoinRequest(user_id=user.id, clan_id=clan.id, status='pending')
                db.session.add(req)
        db.session.commit()
        login_user(user)
        flash('Регистрация успешна! Добро пожаловать.', 'info')
        return redirect(url_for('cabinet'))
    return render_template('register.html', clans=clans)


@app.route('/cabinet')
@login_required
def cabinet():
    # Администратор не имеет доступа к личному кабинету
    if current_user.is_admin:
        flash('Администратор не имеет доступа к личному кабинету.', 'info')
        return redirect(url_for('index'))
    """Личный кабинет пользователя"""
    user = current_user
    user.ensure_energy_refill()
    db.session.commit()
    clan = user.clan_obj
    pending_request = ClanJoinRequest.query.filter_by(
        user_id=user.id, status='pending'
    ).first()
    clan_data = None
    if clan:
        territories = TerritoryRegionState.query.filter_by(owner_clan_id=clan.id).order_by(
            TerritoryRegionState.region_index
        ).all()
        regions_cfg = {r.region_index: r.display_name for r in TerritoryRegionConfig.query.all()}
        clan_data = {
            'clan': clan.to_dict(),
            'members': [{'id': u.id, 'username': u.username, 'character_name': u.character_name or u.username,
                        'avatar_url': url_for('static', filename=_avatar_static_filename(u.avatar_filename)) if u.avatar_filename else None,
                        'level': u.level or 1, 'is_owner': u.id == clan.owner_id} for u in clan.members_rel],
            'territories': [{'region_index': t.region_index, 'display_name': regions_cfg.get(t.region_index, f'Зона {t.region_index+1}'), 'strength': t.strength} for t in territories],
            'pending_requests': [{'id': r.id, 'user_id': r.user_id, 'username': r.user.username, 'character_name': r.user.character_name or r.user.username} for r in clan.join_requests if r.status == 'pending'] if user.id == clan.owner_id else []
        }
    return render_template(
        'cabinet.html',
        user=user,
        clan_data=clan_data,
        pending_request=pending_request,
        avatar_url=url_for('static', filename=_avatar_static_filename(user.avatar_filename)) if user.avatar_filename else None
    )


@app.route('/api/cabinet/profile', methods=['POST'])
@login_required
def api_cabinet_profile():
    """Обновить профиль: character_name, avatar"""
    user = current_user
    data = request.form
    character_name = (data.get('character_name') or '').strip()
    if character_name:
        is_valid, err = validate_user_name(character_name)
        if not is_valid:
            return jsonify({'success': False, 'error': err}), 400
        user.character_name = character_name
    if 'avatar' in request.files:
        f = request.files['avatar']
        if f and f.filename and f.filename.rsplit('.', 1)[-1].lower() in ALLOWED_EXTENSIONS:
            folder = os.path.join(app.root_path, app.config['AVATAR_FOLDER'])
            os.makedirs(folder, exist_ok=True)
            filename = f'user_{user.id}_{secure_filename(f.filename)}'
            f.save(os.path.join(folder, filename))
            # Путь относительно static (без "static/"), иначе url_for даёт /static/static/...
            user.avatar_filename = f'uploads/avatars/{filename}'
    db.session.commit()
    return jsonify({'success': True, 'avatar_url': url_for('static', filename=_avatar_static_filename(user.avatar_filename)) if user.avatar_filename else None})


@app.route('/api/cabinet/skills', methods=['POST'])
@login_required
def api_cabinet_skills():
    """Сохранить распределение очков навыков (damage_skill, defense_skill, energy_skill)."""
    user = current_user
    if user.is_admin:
        return jsonify({'success': False, 'error': 'Администратор не участвует'}), 403
    data = request.get_json() or request.form
    try:
        d = int(data.get('damage_skill', 0))
        df = int(data.get('defense_skill', 0))
        e = int(data.get('energy_skill', 0))
    except (TypeError, ValueError):
        return jsonify({'success': False, 'error': 'Некорректные значения'}), 400
    if d < 0 or df < 0 or e < 0:
        return jsonify({'success': False, 'error': 'Значения не могут быть отрицательными'}), 400
    if d < (user.damage_skill or 0) or df < (user.defense_skill or 0) or e < (user.energy_skill or 0):
        return jsonify({'success': False, 'error': 'Нельзя уменьшить уже сохранённые характеристики. Можно только тратить новые очки.'}), 400
    total_allowed = skill_points_total_for_level(user.level or 1)
    if d + df + e > total_allowed:
        return jsonify({'success': False, 'error': f'Нельзя потратить больше {total_allowed} очков'}), 400
    user.damage_skill = d
    user.defense_skill = df
    user.energy_skill = e
    db.session.commit()
    user.ensure_energy_refill()
    return jsonify({
        'success': True,
        'damage': user.damage,
        'defense': user.defense,
        'energy': user.energy,
        'current_energy': user.current_energy_value,
        'skill_points_available': user.skill_points_available,
    })


def _shop_item_to_dict(item, include_effects=False):
    """Словарь товара для API (image_url, без эффектов по умолчанию)."""
    d = {
        'id': item.id,
        'name': item.name,
        'description': item.description or '',
        'price': item.price,
        'category': item.category,
        'image_url': url_for('static', filename=_avatar_static_filename(item.image_filename)) if item.image_filename else None,
    }
    if include_effects:
        d['effects'] = [
            {'effect_type': e.effect_type, 'percent_change': e.percent_change, 'target': e.target, 'duration_minutes': e.duration_minutes}
            for e in item.effects
        ]
    return d


def _active_buffs_query(user_id=None, clan_id=None, region_index=None):
    """Базовый запрос активных баффов по одному из критериев (все ещё действующие по времени)."""
    now = datetime.utcnow()
    q = ActiveItemBuff.query
    if user_id is not None:
        q = q.filter(ActiveItemBuff.user_id == user_id)
    if clan_id is not None:
        q = q.filter(ActiveItemBuff.clan_id == clan_id)
    if region_index is not None:
        q = q.filter(ActiveItemBuff.region_index == region_index)
    return q


def _is_buff_effect_active(effect, used_at, one_shot, now):
    """Эффект активен, если: разовый ещё не использован; с длительностью — used_at + duration >= now."""
    if one_shot:
        return True
    if effect.duration_minutes is None:
        return True
    from datetime import timedelta
    expires = used_at + timedelta(minutes=effect.duration_minutes)
    return now <= expires


def get_active_buffs_for_display(user_id=None, clan_id=None, region_index=None):
    """Список активных баффов для отображения (название, иконка, время использования, макс. время окончания).
    Возвращаются только баффы с длительностью действия (для отображения иконок на странице битвы)."""
    now = datetime.utcnow()
    from datetime import timedelta
    rows = _active_buffs_query(user_id=user_id, clan_id=clan_id, region_index=region_index).all()
    out = []
    for b in rows:
        item = b.shop_item
        if not item:
            continue
        max_end = None
        has_duration = False
        for e in item.effects:
            if e.duration_minutes is not None:
                has_duration = True
                end = b.used_at + timedelta(minutes=e.duration_minutes)
                if max_end is None or end > max_end:
                    max_end = end
        if b.one_shot and not has_duration:
            max_end = None
        if max_end is None:
            continue
        if now > max_end:
            continue
        static_path = _avatar_static_filename(item.image_filename) if item.image_filename else None
        image_url = url_for('static', filename=static_path, _external=True) if static_path else None
        used_iso = b.used_at.isoformat() if b.used_at else None
        expires_iso = max_end.isoformat() if max_end else None
        used_display = b.used_at.strftime('%d.%m.%Y %H:%M') if b.used_at else None
        expires_display = max_end.strftime('%d.%m.%Y %H:%M') if max_end else None
        out.append({
            'id': b.id,
            'shop_item_id': item.id,
            'name': item.name,
            'description': item.description or '',
            'image_url': image_url,
            'used_at': used_iso,
            'expires_at': expires_iso,
            'used_at_display': used_display,
            'expires_at_display': expires_display,
            'one_shot': b.one_shot,
        })
    return out


def _get_multipliers_for_action(user_id, clan_id, region_index, is_attack):
    """
    Суммарные множители (1 + sum(percent/100)) по типам эффектов для одного действия.
    user_id, clan_id — для личных/клановых баффов; region_index — для баффов области.
    is_attack: True = атака чужой области (damage), False = защита своей (defense).
    Возвращает dict: damage_pct, defense_pct, xp_reward_pct, nums_reward_pct (суммы процентов).
    """
    now = datetime.utcnow()
    damage_pct = 0.0
    defense_pct = 0.0
    xp_reward_pct = 0.0
    nums_reward_pct = 0.0

    def apply_effects(buff):
        nonlocal damage_pct, defense_pct, xp_reward_pct, nums_reward_pct
        item = buff.shop_item
        if not item:
            return
        for e in item.effects:
            if not _is_buff_effect_active(e, buff.used_at, buff.one_shot, now):
                continue
            pct = e.percent_change or 0
            if item.category == SHOP_CATEGORY_CURSE and pct > 0:
                pct = -pct
            elif item.category == SHOP_CATEGORY_ENHANCEMENT and pct < 0:
                pct = -pct
            if e.effect_type == 'damage':
                damage_pct += pct
            elif e.effect_type == 'defense':
                defense_pct += pct
            elif e.effect_type == 'xp_reward':
                xp_reward_pct += pct
            elif e.effect_type == 'nums_reward':
                nums_reward_pct += pct

    # Личные и клановые баффы (для текущего пользователя)
    if user_id is not None:
        for b in _active_buffs_query(user_id=user_id).all():
            apply_effects(b)
        if clan_id is not None:
            for b in _active_buffs_query(clan_id=clan_id).all():
                apply_effects(b)
    # Баффы области
    if region_index is not None:
        for b in _active_buffs_query(region_index=region_index).all():
            apply_effects(b)

    return {
        'damage_pct': damage_pct,
        'defense_pct': defense_pct,
        'xp_reward_pct': xp_reward_pct,
        'nums_reward_pct': nums_reward_pct,
    }


def _consume_one_shot_buffs(user_id, clan_id, region_index):
    """Удалить разовые баффы после применения действия (вызывать после применения урона/опыта/нумов)."""
    q = _active_buffs_query(user_id=user_id, clan_id=clan_id, region_index=region_index).filter(ActiveItemBuff.one_shot == True)
    for b in q.all():
        db.session.delete(b)


@app.route('/api/shop/items')
@login_required
def api_shop_items():
    """Список товаров лавки по категориям (для блока «Лавка предметов» в битве за территорию)."""
    items = ShopItem.query.filter_by(shop_context=SHOP_CONTEXT_TERRITORY).order_by(ShopItem.category, ShopItem.sort_order, ShopItem.id).all()
    by_category = {'enhancement': [], 'curse': []}
    for item in items:
        by_category.setdefault(item.category, []).append(_shop_item_to_dict(item))
    return jsonify({'success': True, 'items': by_category})


@app.route('/api/shop/item/<int:item_id>')
@login_required
def api_shop_item_detail(item_id):
    """Один товар для модалки (с эффектами для отображения). Только лавка территории."""
    item = ShopItem.query.get(item_id)
    if not item or item.shop_context != SHOP_CONTEXT_TERRITORY:
        return jsonify({'success': False, 'error': 'Товар не найден'}), 404
    return jsonify({'success': True, 'item': _shop_item_to_dict(item, include_effects=True)})


@app.route('/api/shop/purchase', methods=['POST'])
@login_required
def api_shop_purchase():
    """Покупка товара за Нумы."""
    if current_user.is_admin:
        return jsonify({'success': False, 'error': 'Администратор не участвует'}), 403
    data = request.get_json() or {}
    item_id = data.get('item_id')
    if not item_id:
        return jsonify({'success': False, 'error': 'Укажите item_id'}), 400
    item = ShopItem.query.get(item_id)
    if not item or item.shop_context != SHOP_CONTEXT_TERRITORY:
        return jsonify({'success': False, 'error': 'Товар не найден'}), 404
    balance = current_user.nums_balance or 0
    if balance < item.price:
        return jsonify({'success': False, 'error': 'Недостаточно Нумов', 'balance': balance, 'price': item.price}), 400
    current_user.nums_balance = balance - item.price
    purchase = UserShopPurchase(user_id=current_user.id, shop_item_id=item.id)
    db.session.add(purchase)
    db.session.commit()
    return jsonify({
        'success': True,
        'balance': current_user.nums_balance,
        'purchase_id': purchase.id,
    })


@app.route('/api/cabinet/inventory')
@login_required
def api_cabinet_inventory():
    """Список купленных товаров лавки территории (инвентарь)."""
    purchases = UserShopPurchase.query.filter(
        UserShopPurchase.user_id == current_user.id
    ).join(ShopItem, UserShopPurchase.shop_item_id == ShopItem.id).filter(
        ShopItem.shop_context == SHOP_CONTEXT_TERRITORY
    ).order_by(UserShopPurchase.purchased_at.desc()).all()
    out = []
    for p in purchases:
        out.append({
            'id': p.id,
            'item_id': p.shop_item_id,
            'name': p.shop_item.name,
            'image_url': url_for('static', filename=_avatar_static_filename(p.shop_item.image_filename)) if p.shop_item.image_filename else None,
            'purchased_at': p.purchased_at.isoformat() if p.purchased_at else None,
            'category': p.shop_item.category,
        })
    return jsonify({'success': True, 'inventory': out})


@app.route('/api/cabinet/inventory/<int:purchase_id>/use', methods=['POST'])
@login_required
def api_cabinet_inventory_use(purchase_id):
    """Использовать предмет из инвентаря. Для предметов «на область» в body передать region_index."""
    if current_user.is_admin:
        return jsonify({'success': False, 'error': 'Администратор не участвует'}), 403
    purchase = UserShopPurchase.query.filter_by(id=purchase_id, user_id=current_user.id).first()
    if not purchase:
        return jsonify({'success': False, 'error': 'Покупка не найдена'}), 404
    item = purchase.shop_item
    if not item or item.shop_context != SHOP_CONTEXT_TERRITORY:
        return jsonify({'success': False, 'error': 'Предмет не найден'}), 404
    effects = list(item.effects)
    if not effects:
        db.session.delete(purchase)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Предмет использован'})

    data = request.get_json() or {}
    targets = {e.target for e in effects if e.target}
    region_index = data.get('region_index')
    data_clan_id = data.get('clan_id')
    if SHOP_EFFECT_TARGET_REGION in targets:
        if region_index is None:
            return jsonify({'success': False, 'error': 'Укажите область (region_index) для применения'}), 400
        region_index = int(region_index)
        if TerritoryRegionConfig.query.filter_by(region_index=region_index).first() is None:
            return jsonify({'success': False, 'error': 'Область не найдена'}), 400
    if SHOP_EFFECT_TARGET_CLAN in targets:
        if data_clan_id is None:
            return jsonify({'success': False, 'error': 'Укажите клан (clan_id) для применения'}), 400
        clan_id = int(data_clan_id)
        if Clan.query.get(clan_id) is None:
            return jsonify({'success': False, 'error': 'Клан не найден'}), 400
        # Разрешено применять на любой выбранный клан (свой или чужой)
    else:
        clan_id = None

    # Определяем одну запись баффа: личное, клан или область
    user_id = None
    reg_idx = None
    if SHOP_EFFECT_TARGET_REGION in targets:
        reg_idx = region_index
    elif SHOP_EFFECT_TARGET_CLAN in targets:
        pass
    else:
        user_id = current_user.id

    # Разовые (без длительности) = one_shot: сработает один раз при следующем действии
    has_duration = any(e.duration_minutes is not None for e in effects)
    one_shot = not has_duration

    # Мгновенные эффекты при использовании (улучшения — плюс, проклятия — минус)
    for e in effects:
        if e.effect_type == 'current_energy' and (e.target == SHOP_EFFECT_TARGET_SELF or not e.target):
            current_user.ensure_energy_refill()
            max_e = current_user.energy
            cur = current_user.current_energy if current_user.current_energy is not None else max_e
            pct = e.percent_change or 0
            if item.category == SHOP_CATEGORY_CURSE and pct > 0:
                pct = -pct
            elif item.category == SHOP_CATEGORY_ENHANCEMENT and pct < 0:
                pct = -pct
            add = int(max_e * pct / 100)
            current_user.current_energy = min(max_e, max(0, cur + add))
        elif e.effect_type == 'current_energy' and e.target == SHOP_EFFECT_TARGET_CLAN and clan_id:
            for u in User.query.filter_by(clan_id=clan_id).all():
                u.ensure_energy_refill()
                max_e = u.energy
                cur = u.current_energy if u.current_energy is not None else max_e
                pct = e.percent_change or 0
                if item.category == SHOP_CATEGORY_CURSE and pct > 0:
                    pct = -pct
                elif item.category == SHOP_CATEGORY_ENHANCEMENT and pct < 0:
                    pct = -pct
                add = int(max_e * pct / 100)
                u.current_energy = min(max_e, max(0, cur + add))

    buff = ActiveItemBuff(
        user_id=user_id,
        clan_id=clan_id,
        region_index=reg_idx,
        shop_item_id=item.id,
        used_at=datetime.utcnow(),
        one_shot=one_shot,
    )
    db.session.add(buff)
    db.session.delete(purchase)
    db.session.commit()
    return jsonify({
        'success': True,
        'message': 'Предмет использован',
        'buff_id': buff.id,
        'one_shot': one_shot,
    })


@app.route('/api/clans')
def api_clans_list():
    """Список кланов для выбора при вступлении"""
    clans = Clan.query.order_by(Clan.name).all()
    return jsonify([c.to_dict() for c in clans])


@app.route('/api/clan/create', methods=['POST'])
@login_required
def api_clan_create():
    """Создать клан (только если пользователь не в клане)"""
    if current_user.clan_id:
        return jsonify({'success': False, 'error': 'Вы уже в клане'}), 400
    data = request.form
    name = (data.get('name') or '').strip()
    color = (data.get('color') or '#6b7280').strip()
    if not name or len(name) < 2:
        return jsonify({'success': False, 'error': 'Название клана должно быть не менее 2 символов'}), 400
    if Clan.query.filter_by(name=name).first():
        return jsonify({'success': False, 'error': 'Клан с таким названием уже существует'}), 400
    clan = Clan(name=name, color=color, owner_id=current_user.id)
    db.session.add(clan)
    db.session.flush()
    if 'flag' in request.files:
        f = request.files['flag']
        if f and f.filename and f.filename.rsplit('.', 1)[-1].lower() in ALLOWED_EXTENSIONS:
            folder = os.path.join(app.root_path, app.config['CLAN_FLAG_FOLDER'])
            filename = f'clan_{clan.id}_{secure_filename(f.filename)}'
            f.save(os.path.join(folder, filename))
            clan.flag_filename = f'uploads/clan_flags/{filename}'
    current_user.clan_id = clan.id
    db.session.commit()
    return jsonify({'success': True, 'clan': clan.to_dict()})


@app.route('/api/clan/<int:clan_id>/update', methods=['POST'])
@login_required
def api_clan_update(clan_id):
    """Владелец клана может изменить только эмблему; название клана создатель менять не может."""
    clan = Clan.query.get_or_404(clan_id)
    if clan.owner_id != current_user.id:
        return jsonify({'success': False, 'error': 'Только владелец может редактировать клан'}), 403
    data = request.form
    # Имя клана владелец (создатель) менять не может — не обновляем name
    if 'flag' in request.files:
        f = request.files['flag']
        if f and f.filename and f.filename.rsplit('.', 1)[-1].lower() in ALLOWED_EXTENSIONS:
            folder = os.path.join(app.root_path, app.config['CLAN_FLAG_FOLDER'])
            os.makedirs(folder, exist_ok=True)
            filename = f'clan_{clan.id}_{secure_filename(f.filename)}'
            f.save(os.path.join(folder, filename))
            clan.flag_filename = f'uploads/clan_flags/{filename}'
    db.session.commit()
    return jsonify({'success': True, 'clan': clan.to_dict()})


@app.route('/api/clan/leave', methods=['POST'])
@login_required
def api_clan_leave():
    """Выйти из клана"""
    if not current_user.clan_id:
        return jsonify({'success': False, 'error': 'Вы не в клане'}), 400
    clan = current_user.clan_obj
    if clan.owner_id == current_user.id:
        if len(clan.members_rel) > 1:
            return jsonify({'success': False, 'error': 'Владелец не может выйти, пока в клане есть другие участники. Передайте владение или исключите их.'}), 400
        db.session.delete(clan)
    current_user.clan_id = None
    db.session.commit()
    return jsonify({'success': True})


@app.route('/api/clan/join-request', methods=['POST'])
@login_required
def api_clan_join_request():
    """Подать заявку на вступление в клан (только одну активную)"""
    if current_user.clan_id:
        return jsonify({'success': False, 'error': 'Вы уже в клане'}), 400
    data = request.get_json() or {}
    clan_id_raw = data.get('clan_id')
    try:
        clan_id = int(clan_id_raw) if clan_id_raw is not None else None
    except (TypeError, ValueError):
        clan_id = None
    if not clan_id:
        return jsonify({'success': False, 'error': 'Укажите clan_id'}), 400
    clan = Clan.query.get(clan_id)
    if not clan:
        return jsonify({'success': False, 'error': 'Клан не найден'}), 404
    existing = ClanJoinRequest.query.filter_by(user_id=current_user.id, status='pending').first()
    if existing:
        return jsonify({'success': False, 'error': 'У вас уже есть активная заявка. Отмените её перед подачей новой.'}), 400
    req = ClanJoinRequest(user_id=current_user.id, clan_id=clan_id, status='pending')
    db.session.add(req)
    db.session.commit()
    return jsonify({'success': True})


@app.route('/api/clan/cancel-request', methods=['POST'])
@login_required
def api_clan_cancel_request():
    """Отменить заявку на вступление"""
    req = ClanJoinRequest.query.filter_by(user_id=current_user.id, status='pending').first()
    if not req:
        return jsonify({'success': False, 'error': 'Нет активной заявки'}), 400
    db.session.delete(req)
    db.session.commit()
    return jsonify({'success': True})


@app.route('/api/clan/<int:clan_id>/accept/<int:request_id>', methods=['POST'])
@login_required
def api_clan_accept_request(clan_id, request_id):
    """Принять заявку (только владелец клана)"""
    clan = Clan.query.get_or_404(clan_id)
    if clan.owner_id != current_user.id:
        return jsonify({'success': False, 'error': 'Только владелец может принять заявку'}), 403
    req = ClanJoinRequest.query.filter_by(id=request_id, clan_id=clan_id, status='pending').first()
    if not req:
        return jsonify({'success': False, 'error': 'Заявка не найдена'}), 404
    req.user.clan_id = clan_id
    req.status = 'accepted'
    db.session.commit()
    return jsonify({'success': True})


@app.route('/api/clan/<int:clan_id>/reject/<int:request_id>', methods=['POST'])
@login_required
def api_clan_reject_request(clan_id, request_id):
    """Отклонить заявку (только владелец клана)"""
    clan = Clan.query.get_or_404(clan_id)
    if clan.owner_id != current_user.id:
        return jsonify({'success': False, 'error': 'Только владелец может отклонить заявку'}), 403
    req = ClanJoinRequest.query.filter_by(id=request_id, clan_id=clan_id, status='pending').first()
    if not req:
        return jsonify({'success': False, 'error': 'Заявка не найдена'}), 404
    req.status = 'rejected'
    db.session.commit()
    return jsonify({'success': True})


@app.route('/api/clan/<int:clan_id>/kick/<int:user_id>', methods=['POST'])
@login_required
def api_clan_kick(clan_id, user_id):
    """Исключить участника из клана (только владелец)"""
    clan = Clan.query.get_or_404(clan_id)
    if clan.owner_id != current_user.id:
        return jsonify({'success': False, 'error': 'Только владелец может исключить участника'}), 403
    target = User.query.get_or_404(user_id)
    if target.clan_id != clan_id:
        return jsonify({'success': False, 'error': 'Пользователь не в вашем клане'}), 400
    if target.id == clan.owner_id:
        return jsonify({'success': False, 'error': 'Нельзя исключить владельца'}), 400
    target.clan_id = None
    db.session.commit()
    return jsonify({'success': True})


@app.route('/api/clan/chat/unread-count')
@login_required
def api_clan_chat_unread_count():
    """Количество новых сообщений от других участников (id > after_id). Параметр: after_id (опционально)."""
    if not current_user.clan_id:
        return jsonify({'success': False, 'error': 'Вы не в клане'}), 400
    after_id = request.args.get('after_id', type=int) or 0
    count = ClanChatMessage.query.filter(
        ClanChatMessage.clan_id == current_user.clan_id,
        ClanChatMessage.id > after_id,
        ClanChatMessage.user_id != current_user.id,
    ).count()
    return jsonify({'success': True, 'count': count})


@app.route('/api/clan/chat', methods=['GET'])
@login_required
def api_clan_chat_list():
    """Список сообщений чата клана (только для участников клана).
    Параметры: limit (по умолчанию 20), before_id (подгрузить старые), after_id (только новые, для опроса).
    """
    if not current_user.clan_id:
        return jsonify({'success': False, 'error': 'Вы не в клане'}), 400
    limit = min(int(request.args.get('limit', 20)), 100)
    before_id = request.args.get('before_id', type=int)
    after_id = request.args.get('after_id', type=int)
    base = ClanChatMessage.query.filter_by(clan_id=current_user.clan_id)

    if after_id:
        # Только новые сообщения (для опроса)
        messages = base.filter(ClanChatMessage.id > after_id).order_by(ClanChatMessage.id.asc()).all()
        items = [
            {'id': m.id, 'user_id': m.user_id, 'author_name': m.user.character_name or m.user.username,
             'text': m.text, 'created_at': m.created_at.isoformat() if m.created_at else None}
            for m in messages
        ]
        return jsonify({'success': True, 'messages': items})
    if before_id:
        # Подгрузка старых сообщений
        messages = base.filter(ClanChatMessage.id < before_id).order_by(
            ClanChatMessage.id.desc()
        ).limit(limit + 1).all()
        has_more = len(messages) > limit
        messages = list(reversed(messages[:limit]))
        items = [
            {'id': m.id, 'user_id': m.user_id, 'author_name': m.user.character_name or m.user.username,
             'text': m.text, 'created_at': m.created_at.isoformat() if m.created_at else None}
            for m in messages
        ]
        return jsonify({'success': True, 'messages': items, 'has_more': has_more})
    # Первая загрузка: последние limit сообщений
    total = base.count()
    messages = base.order_by(ClanChatMessage.id.desc()).limit(limit).all()
    messages = list(reversed(messages))
    items = [
        {'id': m.id, 'user_id': m.user_id, 'author_name': m.user.character_name or m.user.username,
         'text': m.text, 'created_at': m.created_at.isoformat() if m.created_at else None}
        for m in messages
    ]
    return jsonify({'success': True, 'messages': items, 'has_more': total > limit})


@app.route('/api/clan/chat', methods=['POST'])
@login_required
def api_clan_chat_send():
    """Отправить сообщение в чат клана."""
    if not current_user.clan_id:
        return jsonify({'success': False, 'error': 'Вы не в клане'}), 400
    data = request.get_json() or request.form
    text = (data.get('text') or '').strip()
    if not text:
        return jsonify({'success': False, 'error': 'Текст сообщения не может быть пустым'}), 400
    if len(text) > 2000:
        return jsonify({'success': False, 'error': 'Сообщение слишком длинное'}), 400
    msg = ClanChatMessage(clan_id=current_user.clan_id, user_id=current_user.id, text=text)
    db.session.add(msg)
    db.session.commit()
    return jsonify({
        'success': True,
        'message': {
            'id': msg.id,
            'user_id': msg.user_id,
            'author_name': current_user.character_name or current_user.username,
            'text': msg.text,
            'created_at': msg.created_at.isoformat() if msg.created_at else None,
        }
    })


# Главная страница - рейтинг классов
@app.route('/')
def index():
    # Сортируем по отношению баллов учащихся к баллам Валеры
    # Если valera_balance = 0 и students_balance > 0, то отношение = очень большое число (класс выше)
    # Если valera_balance = 0 и students_balance = 0, то отношение = 0 (класс ниже)
    # Иначе: students_balance / valera_balance
    ratio = case(
        (Class.valera_balance == 0, case(
            (Class.students_balance > 0, 999999.0),  # Очень большое число для классов с баллами учащихся, но без баллов Валеры
            else_=0.0  # Если оба баланса = 0, то отношение = 0
        )),
        else_=cast(Class.students_balance, Float) / cast(Class.valera_balance, Float)
    )
    classes = Class.query.order_by(ratio.desc()).all()
    return render_template('rating.html', classes=classes, registration_enabled=get_territory_registration_enabled())

# Страница игры для класса
@app.route('/class/<int:class_id>')
@admin_required
def class_game(class_id):
    class_obj = db.get_or_404(Class, class_id)
    valera_prizes = Prize.query.filter_by(prize_type='valera').all()
    students_prizes = Prize.query.filter_by(prize_type='students').all()
    shop_items = ShopItem.query.filter_by(shop_context=SHOP_CONTEXT_GAME).order_by(ShopItem.price).all()
    return render_template('game.html',
                         class_obj=class_obj,
                         valera_prizes=[p.to_dict() for p in valera_prizes],
                         students_prizes=[p.to_dict() for p in students_prizes],
                         shop_items=shop_items)

# API для получения баланса
@app.route('/api/class/<int:class_id>/balance')
def get_balance(class_id):
    class_obj = db.get_or_404(Class, class_id)
    return jsonify({
        'students_balance': class_obj.students_balance,
        'valera_balance': class_obj.valera_balance
    })

# API для применения изменения баланса (дельт)
@app.route('/api/class/<int:class_id>/balance/delta', methods=['POST'])
def apply_balance_delta(class_id):
    """
    Атомарно применяет изменения (дельты) к балансу учащихся и Валеры.
    В отличие от /balance (POST), который принимает абсолютные значения,
    этот эндпоинт добавляет изменения на стороне сервера.
    """
    class_obj = db.get_or_404(Class, class_id)
    data = request.get_json(silent=True) or {}

    try:
        students_delta = int(data.get('students_delta', 0) or 0)
        valera_delta = int(data.get('valera_delta', 0) or 0)
    except (TypeError, ValueError):
        return jsonify({'success': False, 'error': 'Некорректные значения дельт'}), 400

    class_obj.students_balance = (class_obj.students_balance or 0) + students_delta
    class_obj.valera_balance = (class_obj.valera_balance or 0) + valera_delta
    db.session.commit()

    return jsonify({
        'success': True,
        'students_balance': class_obj.students_balance,
        'valera_balance': class_obj.valera_balance
    })

# API для обновления баланса
@app.route('/api/class/<int:class_id>/balance', methods=['POST'])
def update_balance(class_id):
    class_obj = db.get_or_404(Class, class_id)
    data = request.json
    if 'students_balance' in data:
        class_obj.students_balance = data['students_balance']
    if 'valera_balance' in data:
        class_obj.valera_balance = data['valera_balance']
    db.session.commit()
    return jsonify({'success': True})

# Панель администратора - классы
@app.route('/admin/classes')
@admin_required
def admin_classes():
    classes = Class.query.all()
    return render_template('admin/classes.html', classes=classes)

# API для управления классами
@app.route('/api/classes', methods=['POST'])
@admin_required
def create_class():
    data = request.json
    if Class.query.filter_by(name=data['name']).first():
        return jsonify({'success': False, 'error': 'Класс с таким названием уже существует'}), 400
    
    new_class = Class(
        name=data['name'],
        students_balance=0,
        valera_balance=0
    )
    db.session.add(new_class)
    db.session.commit()
    return jsonify({'success': True, 'class': new_class.to_dict()})

@app.route('/api/classes/<int:class_id>', methods=['PUT'])
@admin_required
def update_class(class_id):
    class_obj = db.get_or_404(Class, class_id)
    data = request.json
    
    if 'name' in data:
        if Class.query.filter_by(name=data['name']).first() and Class.query.filter_by(name=data['name']).first().id != class_id:
            return jsonify({'success': False, 'error': 'Класс с таким названием уже существует'}), 400
        class_obj.name = data['name']
    if 'students_balance' in data:
        class_obj.students_balance = data['students_balance']
    if 'valera_balance' in data:
        class_obj.valera_balance = data['valera_balance']
    
    db.session.commit()
    return jsonify({'success': True, 'class': class_obj.to_dict()})

@app.route('/api/classes/<int:class_id>', methods=['DELETE'])
@admin_required
def delete_class(class_id):
    class_obj = db.get_or_404(Class, class_id)
    db.session.delete(class_obj)
    db.session.commit()
    return jsonify({'success': True})

# API для управления учащимися
@app.route('/api/classes/<int:class_id>/students', methods=['GET'])
@admin_required
def get_students(class_id):
    class_obj = db.get_or_404(Class, class_id)
    students = Student.query.filter_by(class_id=class_id).all()
    
    students_payload = []
    for s in students:
        payload = s.to_dict()
        payload['selection_count'] = StudentSelection.query.filter_by(
            student_id=s.id,
            class_id=class_id
        ).count()
        students_payload.append(payload)
    
    return jsonify({'success': True, 'students': students_payload})

@app.route('/api/classes/<int:class_id>/students', methods=['POST'])
@admin_required
def add_students(class_id):
    class_obj = db.get_or_404(Class, class_id)
    data = request.json
    
    if 'names' not in data or not data['names']:
        return jsonify({'success': False, 'error': 'Не указаны имена учащихся'}), 400
    
    # Разбиваем строку имен через запятую
    names_list = [name.strip() for name in data['names'].split(',') if name.strip()]
    
    if not names_list:
        return jsonify({'success': False, 'error': 'Не указаны имена учащихся'}), 400
    
    added_students = []
    for name in names_list:
        # Проверяем, не существует ли уже учащийся с таким именем в этом классе
        existing = Student.query.filter_by(class_id=class_id, name=name).first()
        if not existing:
            student = Student(name=name, class_id=class_id)
            db.session.add(student)
            added_students.append(student)
    
    db.session.commit()
    return jsonify({'success': True, 'students': [s.to_dict() for s in added_students]})

@app.route('/api/students/<int:student_id>', methods=['PUT'])
@admin_required
def update_student(student_id):
    student = db.get_or_404(Student, student_id)
    data = request.json
    
    if 'name' in data:
        # Проверяем, не существует ли уже учащийся с таким именем в этом классе
        existing = Student.query.filter_by(class_id=student.class_id, name=data['name']).first()
        if existing and existing.id != student_id:
            return jsonify({'success': False, 'error': 'Учащийся с таким именем уже существует в этом классе'}), 400
        student.name = data['name']
    
    db.session.commit()
    return jsonify({'success': True, 'student': student.to_dict()})

@app.route('/api/students/<int:student_id>', methods=['DELETE'])
@admin_required
def delete_student(student_id):
    student = db.get_or_404(Student, student_id)
    db.session.delete(student)
    db.session.commit()
    return jsonify({'success': True})

# API для случайного выбора учащегося
@app.route('/api/class/<int:class_id>/students/random', methods=['GET'])
@admin_required
def get_students_for_random(class_id):
    class_obj = db.get_or_404(Class, class_id)
    students = Student.query.filter_by(class_id=class_id).all()
    
    if not students:
        return jsonify({'success': False, 'error': 'В классе нет учащихся'}), 400
    
    # Подсчитываем количество выборов для каждого учащегося
    selection_counts = {}
    for student in students:
        count = StudentSelection.query.filter_by(student_id=student.id, class_id=class_id).count()
        selection_counts[student.id] = count
    
    # Находим минимальное количество выборов
    min_count = min(selection_counts.values()) if selection_counts else 0
    
    # Вычисляем веса: чем меньше выборов, тем больше вес
    # Вес = (min_count + 1) / (count + 1)
    student_weights = []
    for student in students:
        count = selection_counts[student.id]
        weight = (min_count + 1) / (count + 1)
        student_weights.append({
            'student': student.to_dict(),
            'weight': weight,
            'selection_count': count
        })
    
    return jsonify({'success': True, 'students': student_weights})

@app.route('/api/class/<int:class_id>/students/<int:student_id>/select', methods=['POST'])
@admin_required
def confirm_student_selection(class_id, student_id):
    class_obj = db.get_or_404(Class, class_id)
    student = db.get_or_404(Student, student_id)
    
    # Проверяем, что учащийся принадлежит классу
    if student.class_id != class_id:
        return jsonify({'success': False, 'error': 'Учащийся не принадлежит этому классу'}), 400
    
    # Сохраняем выбор
    selection = StudentSelection(student_id=student_id, class_id=class_id)
    db.session.add(selection)
    db.session.commit()
    
    return jsonify({'success': True, 'selection': selection.to_dict()})

@app.route('/api/class/<int:class_id>/students/<int:student_id>/rate', methods=['POST'])
@admin_required
def rate_student(class_id, student_id):
    db.get_or_404(Class, class_id)
    student = db.get_or_404(Student, student_id)
    
    # Проверяем, что учащийся принадлежит классу
    if student.class_id != class_id:
        return jsonify({'success': False, 'error': 'Учащийся не принадлежит этому классу'}), 400
    
    data = request.get_json(silent=True) or {}
    delta = data.get('delta', None)
    
    try:
        delta_int = int(delta)
    except (TypeError, ValueError):
        return jsonify({'success': False, 'error': 'Некорректная оценка'}), 400
    
    if delta_int not in (-1, 0, 1):
        return jsonify({'success': False, 'error': 'Оценка должна быть -1, 0 или 1'}), 400
    
    student.rating = (student.rating or 0) + delta_int
    db.session.commit()
    
    return jsonify({'success': True, 'student': student.to_dict()})


@app.route('/api/class/<int:class_id>/students/<int:student_id>/redeem-rating', methods=['POST'])
@admin_required
def redeem_student_rating(class_id, student_id):
    db.get_or_404(Class, class_id)
    student = db.get_or_404(Student, student_id)
    
    # Проверяем, что учащийся принадлежит классу
    if student.class_id != class_id:
        return jsonify({'success': False, 'error': 'Учащийся не принадлежит этому классу'}), 400
    
    data = request.get_json(silent=True) or {}
    action = data.get('action', None)
    rating = student.rating or 0
    
    # reward_9: >=5, списать 5
    # reward_10: >=10, списать 10
    # (оставляем совместимость со старым reward_8 -> reward_9, reward_9 -> reward_10)
    if action in ('reward_9', 'reward_8'):
        if rating < 5:
            return jsonify({'success': False, 'error': 'Недостаточно рейтинга для получения 9 баллов'}), 400
        student.rating = rating - 5
    elif action in ('reward_10', 'reward_9_old'):
        if rating < 10:
            return jsonify({'success': False, 'error': 'Недостаточно рейтинга для получения 10 баллов'}), 400
        student.rating = rating - 10
    elif action == 'redeem_2':
        if rating > -3:
            return jsonify({'success': False, 'error': 'Это действие доступно только при рейтинге -3 или ниже'}), 400
        student.rating = rating + 3
    else:
        return jsonify({'success': False, 'error': 'Некорректное действие'}), 400
    
    db.session.commit()
    return jsonify({'success': True, 'student': student.to_dict()})

# Панель администратора - призы
@app.route('/admin/prizes')
@admin_required
def admin_prizes():
    valera_prizes = Prize.query.filter_by(prize_type='valera').all()
    students_prizes = Prize.query.filter_by(prize_type='students').all()
    shop_items = ShopItem.query.filter_by(shop_context=SHOP_CONTEXT_GAME).order_by(ShopItem.price).all()
    return render_template('admin/prizes.html',
                         valera_prizes=valera_prizes,
                         students_prizes=students_prizes,
                         shop_items=shop_items)

# API для управления призами
@app.route('/api/prizes', methods=['POST'])
@admin_required
def create_prize():
    data = request.json
    new_prize = Prize(
        name=data['name'],
        prize_type=data['prize_type'],
        students_change=data.get('students_change', 0),
        valera_change=data.get('valera_change', 0),
        probability=data.get('probability', 'medium')
    )
    db.session.add(new_prize)
    db.session.commit()
    return jsonify({'success': True, 'prize': new_prize.to_dict()})

@app.route('/api/prizes/<int:prize_id>', methods=['PUT'])
@admin_required
def update_prize(prize_id):
    prize = db.get_or_404(Prize, prize_id)
    data = request.json
    
    if 'name' in data:
        prize.name = data['name']
    if 'prize_type' in data:
        prize.prize_type = data['prize_type']
    if 'students_change' in data:
        prize.students_change = data['students_change']
    if 'valera_change' in data:
        prize.valera_change = data['valera_change']
    if 'probability' in data:
        prize.probability = data['probability']
    
    db.session.commit()
    return jsonify({'success': True, 'prize': prize.to_dict()})

@app.route('/api/prizes/<int:prize_id>', methods=['DELETE'])
@admin_required
def delete_prize(prize_id):
    prize = db.get_or_404(Prize, prize_id)
    db.session.delete(prize)
    db.session.commit()
    return jsonify({'success': True})

# API для управления призами магазина
@app.route('/api/shop-items', methods=['POST'])
@admin_required
def create_shop_item():
    """Создать товар лавки призов (game). Используется в admin/prizes."""
    data = request.json
    new_item = ShopItem(
        name=data.get('name', '').strip() or 'Товар',
        price=int(data.get('price', 0)),
        category=data.get('category', 'game'),
        shop_context=SHOP_CONTEXT_GAME
    )
    db.session.add(new_item)
    db.session.commit()
    return jsonify({'success': True, 'item': new_item.to_dict()})

@app.route('/api/shop-items/<int:item_id>', methods=['PUT'])
@admin_required
def update_shop_item(item_id):
    item = db.get_or_404(ShopItem, item_id)
    if item.shop_context != SHOP_CONTEXT_GAME:
        return jsonify({'success': False, 'error': 'Товар не найден'}), 404
    data = request.json
    
    if 'name' in data:
        item.name = data['name']
    if 'price' in data:
        item.price = data['price']
    
    db.session.commit()
    return jsonify({'success': True, 'item': item.to_dict()})

@app.route('/api/shop-items/<int:item_id>', methods=['DELETE'])
@admin_required
def delete_shop_item(item_id):
    item = db.get_or_404(ShopItem, item_id)
    if item.shop_context != SHOP_CONTEXT_GAME:
        return jsonify({'success': False, 'error': 'Товар не найден'}), 404
    db.session.delete(item)
    db.session.commit()
    return jsonify({'success': True})

# Страница задачи недели
@app.route('/weekly-task')
def weekly_task():
    # Получаем таблицу лидеров (первые решившие для всех задач) с пагинацией
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    # Получаем все задачи, которые были решены
    all_tasks = WeeklyTask.query.all()
    leaders_list = []
    for task in all_tasks:
        first_solver = TaskSolution.query.filter_by(
            task_id=task.id,
            is_correct=True
        ).order_by(TaskSolution.solved_at.asc()).first()
        if first_solver:
            leaders_list.append({
                'task_title': task.title,
                'user_name': first_solver.user_name,
                'solved_at': first_solver.solved_at
            })
    
    # Сортируем по дате решения (от новых к старым)
    leaders_list.sort(key=lambda x: x['solved_at'], reverse=True)
    
    # Создаем пагинацию вручную
    total = len(leaders_list)
    start = (page - 1) * per_page
    end = start + per_page
    leaders_page = leaders_list[start:end]
    
    # Создаем объект пагинации
    class Pagination:
        def __init__(self, page, per_page, total):
            self.page = page
            self.per_page = per_page
            self.total = total
            self.pages = (total + per_page - 1) // per_page if total > 0 else 1
            self.has_prev = page > 1
            self.has_next = page < self.pages
            self.prev_num = page - 1 if self.has_prev else None
            self.next_num = page + 1 if self.has_next else None
    
    leaders_paginated = Pagination(page, per_page, total)
    leaders_paginated.items = leaders_page
    
    active_task = WeeklyTask.query.filter_by(is_active=True).first()
    if not active_task:
        return render_template('weekly_task.html', task=None, first_solver=None, leaders_paginated=leaders_paginated, is_task_solved=False, next_update_time=None, next_update_timestamp=None)
    
    # Получаем первое правильное решение
    first_solution = TaskSolution.query.filter_by(
        task_id=active_task.id,
        is_correct=True
    ).order_by(TaskSolution.solved_at.asc()).first()
    
    is_task_solved = first_solution is not None
    
    # Вычисляем следующее воскресенье в 09:00 на основе времени последнего обновления задачи
    next_update_time = None
    next_update_timestamp = None
    
    # Определяем базовое время для вычисления
    if active_task.last_updated:
        task_update_time = active_task.last_updated
        if task_update_time.tzinfo:
            task_update_time = task_update_time.replace(tzinfo=None)
    else:
        # Если last_updated не установлено, используем created_at или текущее время
        task_update_time = active_task.created_at if active_task.created_at else datetime.now()
        if task_update_time.tzinfo:
            task_update_time = task_update_time.replace(tzinfo=None)
    
    # Вычисляем следующее воскресенье в 09:00 от времени обновления задачи
    # Воскресенье = 6 (0 = понедельник, 6 = воскресенье)
    days_until_sunday = (6 - task_update_time.weekday()) % 7
    
    if days_until_sunday == 0:
        # Если обновление было в воскресенье, проверяем время
        target_time = task_update_time.replace(hour=9, minute=0, second=0, microsecond=0)
        if task_update_time >= target_time:
            # Если обновление было в 09:00 или после, берем следующее воскресенье
            days_until_sunday = 7
    
    next_sunday = task_update_time.replace(hour=9, minute=0, second=0, microsecond=0) + timedelta(days=days_until_sunday)
    
    # Проверяем, не в прошлом ли это время. Если да, вычисляем следующее воскресенье от текущего времени
    now = datetime.now()
    if next_sunday < now:
        # Если следующее воскресенье уже прошло, вычисляем следующее от текущего времени
        next_sunday = get_next_sunday_9am()
    
    # Передаем и строку для отладки, и timestamp для JavaScript
    next_update_time = next_sunday.isoformat()
    next_update_timestamp = int(next_sunday.timestamp() * 1000)  # В миллисекундах для JavaScript
    
    return render_template('weekly_task.html', 
                         task=active_task, 
                         first_solver=first_solution,
                         leaders_paginated=leaders_paginated,
                         is_task_solved=is_task_solved,
                         next_update_time=next_update_time,
                         next_update_timestamp=next_update_timestamp)

# API для отправки ответа на задачу
@app.route('/api/weekly-task/submit', methods=['POST'])
def submit_task_answer():
    data = request.json
    user_name = data.get('user_name', '').strip()
    answer = data.get('answer', '').strip()
    
    if not user_name or not answer:
        return jsonify({'success': False, 'error': 'Имя и ответ обязательны'}), 400
    
    active_task = WeeklyTask.query.filter_by(is_active=True).first()
    if not active_task:
        return jsonify({'success': False, 'error': 'Нет активной задачи'}), 404
    
    # Проверяем, не решена ли уже задача
    existing_solution = TaskSolution.query.filter_by(
        task_id=active_task.id,
        is_correct=True
    ).first()
    
    if existing_solution:
        return jsonify({'success': False, 'error': 'Задача уже решена'}), 400
    
    # Проверяем правильность ответа (без учета регистра и пробелов)
    is_correct = active_task.correct_answer.strip().lower() == answer.strip().lower()
    
    # Сохраняем решение
    solution = TaskSolution(
        task_id=active_task.id,
        user_name=user_name,
        answer=answer,
        is_correct=is_correct,
        solved_at=now_utc_plus_3()
    )
    db.session.add(solution)
    db.session.commit()
    
    if is_correct:
        return jsonify({
            'success': True,
            'correct': True,
            'user_name': user_name,
            'answer': active_task.correct_answer
        })
    else:
        return jsonify({
            'success': True,
            'correct': False,
            'message': 'Неверный ответ. Попробуйте еще раз!'
        })

# Панель администратора - задачи
@app.route('/admin/tasks')
@admin_required
def admin_tasks():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    tasks = WeeklyTask.query.order_by(WeeklyTask.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    # Проверяем для каждой задачи, решена ли она правильно
    tasks_solved = {}
    for task in tasks.items:
        has_solution = TaskSolution.query.filter_by(
            task_id=task.id,
            is_correct=True
        ).first() is not None
        tasks_solved[task.id] = has_solution
    
    return render_template('admin/tasks.html', tasks=tasks, tasks_solved=tasks_solved)


@app.route('/admin/change-password', methods=['POST'])
@admin_required
def admin_change_password():
    current_password = (request.form.get('current_password') or '').strip()
    new_password = request.form.get('new_password') or ''
    new_password_confirm = request.form.get('new_password_confirm') or ''

    def _safe_back_redirect():
        ref = request.referrer or ''
        try:
            if ref and request.host_url and ref.startswith(request.host_url):
                return redirect(ref)
        except Exception:
            pass
        return redirect(url_for('admin_tasks'))

    # Базовая валидация
    if not current_password or not new_password or not new_password_confirm:
        flash('Заполните все поля для смены пароля.', 'error')
        return _safe_back_redirect()

    if not current_user.check_password(current_password):
        flash('Текущий пароль указан неверно.', 'error')
        return _safe_back_redirect()

    if new_password != new_password_confirm:
        flash('Новый пароль и повтор не совпадают.', 'error')
        return _safe_back_redirect()

    if len(new_password) < 6:
        flash('Новый пароль должен быть не короче 6 символов.', 'error')
        return _safe_back_redirect()

    current_user.set_password(new_password)
    db.session.commit()
    flash('Пароль администратора успешно изменён.', 'info')
    return _safe_back_redirect()

# API для получения списка задач (с пагинацией)
@app.route('/api/tasks')
@admin_required
def get_tasks():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    tasks = WeeklyTask.query.order_by(WeeklyTask.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    return jsonify({
        'tasks': [task.to_dict() for task in tasks.items],
        'total': tasks.total,
        'pages': tasks.pages,
        'current_page': tasks.page,
        'has_next': tasks.has_next,
        'has_prev': tasks.has_prev
    })

# API для создания задачи
@app.route('/api/tasks', methods=['POST'])
@admin_required
def create_task():
    try:
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip() or None
        correct_answer = request.form.get('correct_answer', '').strip()
        is_active = request.form.get('is_active', 'false').lower() == 'true'
        
        if not title or not correct_answer:
            return jsonify({'success': False, 'error': 'Название и правильный ответ обязательны'}), 400
        
        # Если задача должна быть активной, деактивируем все остальные
        if is_active:
            WeeklyTask.query.update({WeeklyTask.is_active: False})
        
        # Обработка загрузки изображения
        image_filename = None
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                # Добавляем timestamp для уникальности
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"{timestamp}_{filename}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                image_filename = filename
        
        new_task = WeeklyTask(
            title=title,
            description=description,
            image_filename=image_filename,
            correct_answer=correct_answer,
            is_active=is_active
        )
        db.session.add(new_task)
        db.session.commit()
        
        return jsonify({'success': True, 'task': new_task.to_dict()})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

# API для обновления задачи
@app.route('/api/tasks/<int:task_id>', methods=['PUT'])
@admin_required
def update_task(task_id):
    try:
        task = db.get_or_404(WeeklyTask, task_id)
        
        # Получаем данные из form-data или JSON
        if request.is_json:
            data = request.json
            title = data.get('title', '').strip()
            description = data.get('description', '').strip() or None
            correct_answer = data.get('correct_answer', '').strip()
            is_active = data.get('is_active', False)
            delete_image = data.get('delete_image', False)
        else:
            title = request.form.get('title', '').strip()
            description = request.form.get('description', '').strip() or None
            correct_answer = request.form.get('correct_answer', '').strip()
            is_active = request.form.get('is_active', 'false').lower() == 'true'
            delete_image = request.form.get('delete_image', 'false').lower() == 'true'
        
        if title:
            task.title = title
        if description is not None:
            task.description = description
        if correct_answer:
            task.correct_answer = correct_answer
        
        # Обработка изображения
        if delete_image and task.image_filename:
            # Удаляем старое изображение
            old_filepath = os.path.join(app.config['UPLOAD_FOLDER'], task.image_filename)
            if os.path.exists(old_filepath):
                os.remove(old_filepath)
            task.image_filename = None
        
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename and allowed_file(file.filename):
                # Удаляем старое изображение, если есть
                if task.image_filename:
                    old_filepath = os.path.join(app.config['UPLOAD_FOLDER'], task.image_filename)
                    if os.path.exists(old_filepath):
                        os.remove(old_filepath)
                
                # Сохраняем новое изображение
                filename = secure_filename(file.filename)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"{timestamp}_{filename}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                task.image_filename = filename
        
        # Обработка активности задачи
        if is_active != task.is_active:
            if is_active:
                # Деактивируем все остальные задачи
                WeeklyTask.query.filter(WeeklyTask.id != task_id).update({WeeklyTask.is_active: False})
            task.is_active = is_active
        
        db.session.commit()
        return jsonify({'success': True, 'task': task.to_dict()})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

# API для удаления задачи
@app.route('/api/tasks/<int:task_id>', methods=['DELETE'])
@admin_required
def delete_task(task_id):
    task = db.get_or_404(WeeklyTask, task_id)
    
    # Удаляем изображение, если есть
    if task.image_filename:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], task.image_filename)
        if os.path.exists(filepath):
            os.remove(filepath)
    
    db.session.delete(task)
    db.session.commit()
    return jsonify({'success': True})

# API для переключения активности задачи
@app.route('/api/tasks/<int:task_id>/toggle-active', methods=['POST'])
@admin_required
def toggle_task_active(task_id):
    task = db.get_or_404(WeeklyTask, task_id)
    
    if task.is_active:
        task.is_active = False
    else:
        # Деактивируем все остальные задачи
        WeeklyTask.query.filter(WeeklyTask.id != task_id).update({WeeklyTask.is_active: False})
        task.is_active = True
    
    db.session.commit()
    return jsonify({'success': True, 'task': task.to_dict()})

# Маршрут для получения изображений задач
@app.route('/uploads/tasks/<filename>')
def uploaded_task_image(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# API для получения времени до следующего обновления задачи
@app.route('/api/weekly-task/next-update')
def get_next_update_time():
    """Возвращает время до следующего обновления задачи недели"""
    next_sunday = get_next_sunday_9am()
    now = datetime.now()
    time_until = next_sunday - now
    
    return jsonify({
        'next_update': next_sunday.isoformat(),
        'seconds_until': int(time_until.total_seconds()),
        'days': time_until.days,
        'hours': time_until.seconds // 3600,
        'minutes': (time_until.seconds % 3600) // 60
    })

# ==================== РЕЙД БОССА ====================

# Панель администратора - рейд босса
@app.route('/admin/boss-raid')
@admin_required
def admin_boss_raid():
    bosses = Boss.query.all()
    return render_template('admin/boss_raid.html', bosses=bosses)


# Панель администратора - настройки битвы за территорию
@app.route('/admin/territory-battle')
@admin_required
def admin_territory_battle():
    regions = TerritoryRegionConfig.query.order_by(TerritoryRegionConfig.region_index).all()
    clans = Clan.query.order_by(Clan.name).all()
    generators = TaskGenerator.query.order_by(TaskGenerator.name).all()
    registration_enabled = get_territory_registration_enabled()
    capture_enabled, capture_start_time, capture_end_time = get_territory_capture_settings()
    capture_start_time_iso = capture_start_time.strftime('%Y-%m-%dT%H:%M') if capture_start_time else ''
    capture_end_time_iso = capture_end_time.strftime('%Y-%m-%dT%H:%M') if capture_end_time else ''
    shop_items = ShopItem.query.filter_by(shop_context=SHOP_CONTEXT_TERRITORY).order_by(ShopItem.category, ShopItem.sort_order, ShopItem.id).all()
    return render_template('admin/territory_battle.html', regions=regions, clans=clans, generators=generators, registration_enabled=registration_enabled, capture_enabled=capture_enabled, capture_start_time_iso=capture_start_time_iso, capture_end_time_iso=capture_end_time_iso, shop_items=shop_items)


@app.route('/admin/territory-battle/generators', methods=['POST'])
@admin_required
def admin_territory_generator_create():
    """Создать генератор заданий (только название)."""
    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'success': False, 'error': 'Укажите название генератора'}), 400
    g = TaskGenerator(name=name)
    db.session.add(g)
    db.session.commit()
    return jsonify({'success': True, 'id': g.id, 'name': g.name})


@app.route('/admin/territory-battle/settings', methods=['POST'])
@admin_required
def admin_territory_settings():
    """Включить/отключить регистрацию участников, захват областей и время старта."""
    data = request.get_json() or {}
    enabled = data.get('registration_enabled')
    if enabled is None:
        return jsonify({'success': False, 'error': 'registration_enabled required'}), 400
    s = TerritoryBattleSetting.query.first()
    if not s:
        s = TerritoryBattleSetting(registration_enabled=bool(enabled))
        db.session.add(s)
    else:
        s.registration_enabled = bool(enabled)
    if 'capture_enabled' in data:
        s.capture_enabled = bool(data['capture_enabled'])
    if 'capture_start_time' in data:
        val = data['capture_start_time']
        if val is None or (isinstance(val, str) and not val.strip()):
            s.capture_start_time = None
        else:
            try:
                from datetime import datetime
                st = datetime.fromisoformat(str(val).strip().replace('Z', '+00:00'))
                s.capture_start_time = st.replace(tzinfo=None) if st.tzinfo else st
            except (ValueError, TypeError):
                s.capture_start_time = None
    if 'capture_end_time' in data:
        val = data['capture_end_time']
        if val is None or (isinstance(val, str) and not val.strip()):
            s.capture_end_time = None
        else:
            try:
                from datetime import datetime
                et = datetime.fromisoformat(str(val).strip().replace('Z', '+00:00'))
                s.capture_end_time = et.replace(tzinfo=None) if et.tzinfo else et
            except (ValueError, TypeError):
                s.capture_end_time = None
    db.session.commit()
    return jsonify({
        'success': True,
        'registration_enabled': s.registration_enabled,
        'capture_enabled': s.capture_enabled,
        'capture_start_time': s.capture_start_time.isoformat() if s.capture_start_time else None,
        'capture_end_time': s.capture_end_time.isoformat() if s.capture_end_time else None
    })


@app.route('/admin/territory-battle/region/<int:region_index>', methods=['POST'])
@admin_required
def admin_territory_region_save(region_index):
    data = request.get_json() or {}
    cfg = TerritoryRegionConfig.query.filter_by(region_index=region_index).first()
    if not cfg:
        cfg = TerritoryRegionConfig(region_index=region_index, display_name=data.get('display_name', ''), is_locked=False)
        db.session.add(cfg)
    cfg.display_name = data.get('display_name', cfg.display_name)
    if 'description' in data:
        cfg.description = (data.get('description') or '').strip() or None
    cfg.is_locked = bool(data.get('is_locked', cfg.is_locked))
    if 'task_generator_id' in data:
        gen_id = data.get('task_generator_id')
        cfg.task_generator_id = int(gen_id) if gen_id else None
    db.session.commit()
    return jsonify({'success': True})


@app.route('/admin/territory-battle/class/<int:class_id>', methods=['POST'])
@admin_required
def admin_territory_class_save(class_id):
    class_obj = db.get_or_404(Class, class_id)
    if request.content_type and 'multipart/form-data' in request.content_type:
        class_obj.territory_fill_color = request.form.get('territory_fill_color') or class_obj.territory_fill_color
        f = request.files.get('territory_heraldry')
        if f and f.filename and secure_filename(f.filename):
            ext = os.path.splitext(f.filename)[1].lower()
            if ext in {'.png', '.jpg', '.jpeg', '.gif', '.webp'}:
                filename = f'class_{class_id}_{secure_filename(f.filename)}'
                folder = os.path.join(app.root_path, 'static', 'uploads', 'territory_heraldry')
                os.makedirs(folder, exist_ok=True)
                path = os.path.join(folder, filename)
                f.save(path)
                class_obj.territory_heraldry_filename = f'uploads/territory_heraldry/{filename}'
    else:
        data = request.get_json() or {}
        class_obj.territory_fill_color = data.get('territory_fill_color') if data.get('territory_fill_color') is not None else class_obj.territory_fill_color
    db.session.commit()
    return jsonify({'success': True, 'territory_fill_color': class_obj.territory_fill_color, 'territory_heraldry_filename': class_obj.territory_heraldry_filename})


@app.route('/admin/territory-battle/clan/<int:clan_id>/members', methods=['GET'])
@admin_required
def admin_territory_clan_members(clan_id):
    """Возвращает список участников клана."""
    clan = db.get_or_404(Clan, clan_id)
    members = User.query.filter_by(clan_id=clan_id).order_by(User.character_name, User.username).all()
    data = [{
        'id': u.id,
        'username': u.username,
        'character_name': u.character_name or u.username,
        'is_owner': u.id == clan.owner_id
    } for u in members]
    return jsonify({'success': True, 'clan_name': clan.name, 'members': data})


@app.route('/admin/territory-battle/clan/<int:clan_id>/delete', methods=['POST'])
@admin_required
def admin_territory_clan_delete(clan_id):
    """Удаляет клан: исключает участников, сбрасывает владение областями, удаляет клан."""
    clan = db.get_or_404(Clan, clan_id)
    # Исключить всех участников
    User.query.filter_by(clan_id=clan_id).update({'clan_id': None})
    # Сбросить владение областями
    TerritoryRegionState.query.filter_by(owner_clan_id=clan_id).update({'owner_clan_id': None, 'strength': 0})
    # Удалить заявки на вступление (cascade сработает при удалении клана)
    ClanJoinRequest.query.filter_by(clan_id=clan_id).delete()
    db.session.delete(clan)
    db.session.commit()
    return jsonify({'success': True})


@app.route('/admin/territory-battle/clan/<int:clan_id>', methods=['POST'])
@admin_required
def admin_territory_clan_save(clan_id):
    clan = db.get_or_404(Clan, clan_id)
    if request.content_type and 'multipart/form-data' in request.content_type:
        name = (request.form.get('clan_name') or '').strip()
        if name:
            existing = Clan.query.filter(Clan.name == name, Clan.id != clan_id).first()
            if existing:
                return jsonify({'success': False, 'error': 'Клан с таким названием уже существует'}), 400
            clan.name = name
        clan.color = request.form.get('territory_fill_color') or clan.color
        f = request.files.get('territory_heraldry')
        if f and f.filename and secure_filename(f.filename):
            ext = os.path.splitext(f.filename)[1].lower()
            if ext in {'.png', '.jpg', '.jpeg', '.gif', '.webp'}:
                folder = os.path.join(app.root_path, app.config['CLAN_FLAG_FOLDER'])
                filename = f'clan_{clan_id}_{secure_filename(f.filename)}'
                path = os.path.join(folder, filename)
                f.save(path)
                clan.flag_filename = f'uploads/clan_flags/{filename}'
    else:
        data = request.get_json() or {}
        if data.get('territory_fill_color') is not None:
            clan.color = data.get('territory_fill_color')
        name = (data.get('clan_name') or '').strip()
        if name:
            existing = Clan.query.filter(Clan.name == name, Clan.id != clan_id).first()
            if existing:
                return jsonify({'success': False, 'error': 'Клан с таким названием уже существует'}), 400
            clan.name = name
    db.session.commit()
    return jsonify({'success': True, 'territory_fill_color': clan.color, 'territory_heraldry_filename': clan.flag_filename, 'clan_name': clan.name})


TERRITORY_DEFAULT_NAMES = [
    'Jihočeský', 'Jihomoravský', 'Karlovarský', 'Královéhradecký', 'Liberecký',
    'Moravskoslezský', 'Olomoucký', 'Pardubický', 'Zlínský', 'Plzeňský',
    'Prague', 'Středočeský', 'Ústecký', 'Vysočina'
]


@app.route('/admin/territory-battle/reset', methods=['POST'])
@admin_required
def admin_territory_reset():
    """Сброс битвы за территорию: области без владельца, статистика пользователей и кланов — обнуление. Названия областей, описания и генераторы не меняются. Требуется пароль администратора."""
    data = request.get_json() or {}
    password = (data.get('password') or '').strip()
    if not password:
        return jsonify({'success': False, 'error': 'Введите пароль администратора'}), 400
    if not current_user.check_password(password):
        return jsonify({'success': False, 'error': 'Неверный пароль'}), 403
    for state in TerritoryRegionState.query.all():
        state.owner_class_id = None
        state.owner_clan_id = None
        state.strength = 0
    for stats in UserTerritoryStats.query.all():
        stats.total_damage_dealt = 0
        stats.total_influence_points = 0
    for u in User.query.all():
        u.level = 1
        u.experience = 0
        u.damage_skill = 0
        u.defense_skill = 0
        u.energy_skill = 0
        u.current_energy = None
        u.energy_last_refill_at = None
    for i in range(28):
        st = TerritoryRegionState.query.filter_by(region_index=i).first()
        if st:
            st.owner_class_id = None
            st.owner_clan_id = None
            st.strength = 0
        else:
            db.session.add(TerritoryRegionState(region_index=i, owner_class_id=None, owner_clan_id=None, strength=0))
    db.session.commit()
    return jsonify({'success': True})


# --- Админ: редактор лавки (в разделе битвы за территорию) ---
@app.route('/api/admin/shop/items')
@admin_required
def api_admin_shop_items():
    """Список товаров лавки битвы за территорию для админки."""
    items = ShopItem.query.filter_by(shop_context=SHOP_CONTEXT_TERRITORY).order_by(ShopItem.category, ShopItem.sort_order, ShopItem.id).all()
    out = []
    for item in items:
        d = _shop_item_to_dict(item, include_effects=True)
        out.append(d)
    return jsonify({'success': True, 'items': out})


def _shop_save_image(file, item_id=None):
    """Сохранить загруженное изображение товара; вернуть путь относительно static (uploads/shop/...)."""
    if not file or not file.filename:
        return None
    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else 'jpg'
    if ext not in ('jpg', 'jpeg', 'png', 'gif', 'webp'):
        return None
    folder = os.path.join(app.root_path, app.config['SHOP_IMAGE_FOLDER'])
    os.makedirs(folder, exist_ok=True)
    prefix = 'item_' + (str(item_id) if item_id else 'new')
    filename = f'{prefix}_{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}.{ext}'
    filepath = os.path.join(folder, filename)
    file.save(filepath)
    return f'uploads/shop/{filename}'


@app.route('/api/admin/shop/item', methods=['POST'])
@admin_required
def api_admin_shop_item_create():
    """Создать товар лавки. Form: name, description, price, category, image; effects = JSON array."""
    name = (request.form.get('name') or '').strip()
    if not name:
        return jsonify({'success': False, 'error': 'Укажите название'}), 400
    try:
        price = int(request.form.get('price', 0))
    except (TypeError, ValueError):
        price = 0
    category = (request.form.get('category') or '').strip().lower()
    if category not in (SHOP_CATEGORY_ENHANCEMENT, SHOP_CATEGORY_CURSE):
        category = SHOP_CATEGORY_ENHANCEMENT
    description = (request.form.get('description') or '').strip() or None
    effects_json = request.form.get('effects', '[]')
    try:
        effects_list = json.loads(effects_json) if isinstance(effects_json, str) else (effects_json if isinstance(effects_json, list) else [])
    except Exception:
        effects_list = []
    item = ShopItem(name=name, description=description, price=price, category=category, shop_context=SHOP_CONTEXT_TERRITORY)
    db.session.add(item)
    db.session.flush()
    if 'image' in request.files:
        path = _shop_save_image(request.files['image'], item.id)
        if path:
            item.image_filename = path
    _valid_targets = (SHOP_EFFECT_TARGET_SELF, SHOP_EFFECT_TARGET_CLAN, SHOP_EFFECT_TARGET_REGION)
    for e in effects_list:
        t = (e.get('target') or '').strip().lower()
        target = t if t in _valid_targets else SHOP_EFFECT_TARGET_SELF
        eff = ShopItemEffect(
            shop_item_id=item.id,
            effect_type=e.get('effect_type') or 'damage',
            percent_change=float(e.get('percent_change', 0)),
            target=target,
            duration_minutes=int(e['duration_minutes']) if e.get('duration_minutes') not in (None, '') else None,
        )
        db.session.add(eff)
    db.session.commit()
    return jsonify({'success': True, 'item': _shop_item_to_dict(item, include_effects=True)})


@app.route('/api/admin/shop/item/<int:item_id>', methods=['POST', 'PUT', 'DELETE'])
@admin_required
def api_admin_shop_item_update_delete(item_id):
    item = ShopItem.query.get(item_id)
    if not item or item.shop_context != SHOP_CONTEXT_TERRITORY:
        return jsonify({'success': False, 'error': 'Товар не найден'}), 404
    if request.method == 'DELETE':
        db.session.delete(item)
        db.session.commit()
        return jsonify({'success': True})
    name = (request.form.get('name') or '').strip()
    if name:
        item.name = name
    description = request.form.get('description')
    if description is not None:
        item.description = description.strip() or None
    try:
        price = int(request.form.get('price', item.price))
        item.price = price
    except (TypeError, ValueError):
        pass
    category = (request.form.get('category') or '').strip().lower()
    if category in (SHOP_CATEGORY_ENHANCEMENT, SHOP_CATEGORY_CURSE):
        item.category = category
    effects_json = request.form.get('effects', '[]')
    try:
        effects_list = json.loads(effects_json) if isinstance(effects_json, str) else (effects_json if isinstance(effects_json, list) else [])
    except Exception:
        effects_list = []
    if 'image' in request.files and request.files['image'].filename:
        path = _shop_save_image(request.files['image'], item.id)
        if path:
            item.image_filename = path
    if request.form.get('delete_image') in ('1', 'true', 'yes'):
        item.image_filename = None
    ShopItemEffect.query.filter_by(shop_item_id=item.id).delete()
    _valid_targets = (SHOP_EFFECT_TARGET_SELF, SHOP_EFFECT_TARGET_CLAN, SHOP_EFFECT_TARGET_REGION)
    for e in effects_list:
        t = (e.get('target') or '').strip().lower()
        target = t if t in _valid_targets else SHOP_EFFECT_TARGET_SELF
        eff = ShopItemEffect(
            shop_item_id=item.id,
            effect_type=e.get('effect_type') or 'damage',
            percent_change=float(e.get('percent_change', 0)),
            target=target,
            duration_minutes=int(e['duration_minutes']) if e.get('duration_minutes') not in (None, '') else None,
        )
        db.session.add(eff)
    db.session.commit()
    return jsonify({'success': True, 'item': _shop_item_to_dict(item, include_effects=True)})


def _resolve_primary_db_path() -> str | None:
    """
    Возвращает путь к основному SQLite-файлу приложения (valera.db).
    Пытаемся аккуратно поддержать разные варианты размещения (instance/ и cwd).
    """
    # На практике для Flask-SQLAlchemy sqlite:///valera.db обычно кладёт файл в instance/.
    try:
        engine_db = getattr(db.engine.url, "database", None)
    except Exception:
        engine_db = None

    candidates: list[str] = []
    if engine_db:
        candidates.append(engine_db)
        if not os.path.isabs(engine_db):
            candidates.append(os.path.join(app.instance_path, engine_db))
            candidates.append(os.path.join(current_path, engine_db))

    # Явный хинт: стандартный файл в instance/valera.db
    candidates.append(os.path.join(app.instance_path, "valera.db"))
    candidates.append(os.path.join(current_path, "valera.db"))

    for path in candidates:
        try:
            if path and os.path.exists(path) and os.path.isfile(path):
                return os.path.abspath(path)
        except Exception:
            continue
    return None


@app.route('/admin/download-db', methods=['GET'])
@admin_required
def admin_download_db():
    """
    Скачивание файла БД (только для админа).
    Отдаём копию файла, чтобы не упираться в блокировки/частичную запись.
    """
    db_path = _resolve_primary_db_path()
    if not db_path:
        return jsonify({'success': False, 'error': 'Файл базы данных не найден'}), 404

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    download_name = f"valera_{timestamp}.db"

    tmp_dir = tempfile.gettempdir()
    tmp_path = os.path.join(tmp_dir, download_name)
    try:
        shutil.copy2(db_path, tmp_path)
    except Exception as e:
        logger.error(f"Не удалось создать копию БД для скачивания: {e}")
        return jsonify({'success': False, 'error': 'Не удалось подготовить файл для скачивания'}), 500

    @after_this_request
    def _cleanup(response):
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass
        return response

    return send_file(tmp_path, as_attachment=True, download_name=download_name)

# API для создания босса
@app.route('/api/bosses', methods=['POST'])
@admin_required
def create_boss():
    data = request.json
    name = data.get('name', '').strip()
    rewards_list = data.get('rewards_list', '').strip() or None
    
    if not name:
        return jsonify({'success': False, 'error': 'Имя босса обязательно'}), 400
    
    new_boss = Boss(
        name=name,
        rewards_list=rewards_list,
        is_active=False
    )
    db.session.add(new_boss)
    db.session.commit()
    return jsonify({'success': True, 'boss': new_boss.to_dict()})

# API для обновления босса
@app.route('/api/bosses/<int:boss_id>', methods=['PUT'])
@admin_required
def update_boss(boss_id):
    boss = db.get_or_404(Boss, boss_id)
    data = request.json
    
    if 'name' in data:
        boss.name = data['name'].strip()
    if 'rewards_list' in data:
        boss.rewards_list = data['rewards_list'].strip() or None
    
    boss.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'success': True, 'boss': boss.to_dict()})

# API для удаления босса
@app.route('/api/bosses/<int:boss_id>', methods=['DELETE'])
@admin_required
def delete_boss(boss_id):
    boss = db.get_or_404(Boss, boss_id)
    
    # Удаляем изображения задач босса
    for task in boss.tasks:
        if task.image_filename:
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], task.image_filename)
            if os.path.exists(filepath):
                os.remove(filepath)
    
    db.session.delete(boss)
    db.session.commit()
    return jsonify({'success': True})

# API для переключения активности босса
@app.route('/api/bosses/<int:boss_id>/toggle-active', methods=['POST'])
@admin_required
def toggle_boss_active(boss_id):
    boss = db.get_or_404(Boss, boss_id)
    
    if boss.is_active:
        boss.is_active = False
    else:
        # Деактивируем всех остальных боссов
        Boss.query.filter(Boss.id != boss_id).update({Boss.is_active: False})
        boss.is_active = True
    
    boss.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'success': True, 'boss': boss.to_dict()})

# API для получения задач босса
@app.route('/api/bosses/<int:boss_id>/tasks')
@admin_required
def get_boss_tasks(boss_id):
    """
    Возвращает задачи босса постранично, чтобы не выгружать всё сразу.
    Query params:
      - page (1..)
      - per_page (1..100)
    """
    db.get_or_404(Boss, boss_id)

    try:
        page = int(request.args.get('page', 1))
    except Exception:
        page = 1
    try:
        per_page = int(request.args.get('per_page', 20))
    except Exception:
        per_page = 20

    if page < 1:
        page = 1
    if per_page < 1:
        per_page = 1
    if per_page > 100:
        per_page = 100

    pagination = (
        BossTask.query
        .filter_by(boss_id=boss_id)
        .order_by(BossTask.created_at.desc(), BossTask.id.desc())
        .paginate(page=page, per_page=per_page, error_out=False)
    )

    return jsonify({
        'success': True,
        'tasks': [task.to_dict() for task in pagination.items],
        'page': page,
        'per_page': per_page,
        'total': pagination.total,
        'pages': pagination.pages
    })


# API для получения одной задачи босса (для редактирования без загрузки всех задач)
@app.route('/api/bosses/<int:boss_id>/tasks/<int:task_id>', methods=['GET'])
@admin_required
def get_boss_task(boss_id, task_id):
    db.get_or_404(Boss, boss_id)
    task = db.get_or_404(BossTask, task_id)
    if task.boss_id != boss_id:
        return jsonify({'success': False, 'error': 'Задача не принадлежит этому боссу'}), 400
    return jsonify({'success': True, 'task': task.to_dict()})

# API для получения количества задач босса (без загрузки самих задач)
@app.route('/api/bosses/<int:boss_id>/tasks/count')
@admin_required
def get_boss_tasks_count(boss_id):
    from sqlalchemy import func
    _ = db.get_or_404(Boss, boss_id)  # 404 если босса нет
    count = db.session.query(func.count(BossTask.id)).filter(BossTask.boss_id == boss_id).scalar() or 0
    return jsonify({'success': True, 'count': int(count)})

# API для создания задачи босса
@app.route('/api/bosses/<int:boss_id>/tasks', methods=['POST'])
@admin_required
def create_boss_task(boss_id):
    boss = db.get_or_404(Boss, boss_id)
    
    try:
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip() or None
        correct_answer = request.form.get('correct_answer', '').strip()
        points = int(request.form.get('points', 0))
        
        if not title or not correct_answer:
            return jsonify({'success': False, 'error': 'Название и правильный ответ обязательны'}), 400
        
        if points < 0:
            return jsonify({'success': False, 'error': 'Стоимость в баллах не может быть отрицательной'}), 400
        
        # Обработка загрузки изображения
        image_filename = None
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"boss_{timestamp}_{filename}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                image_filename = filename
        
        new_task = BossTask(
            boss_id=boss_id,
            title=title,
            description=description,
            image_filename=image_filename,
            correct_answer=correct_answer,
            points=points
        )
        db.session.add(new_task)
        db.session.commit()
        
        return jsonify({'success': True, 'task': new_task.to_dict()})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

# API для обновления задачи босса
@app.route('/api/bosses/<int:boss_id>/tasks/<int:task_id>', methods=['PUT'])
@admin_required
def update_boss_task(boss_id, task_id):
    boss = db.get_or_404(Boss, boss_id)
    task = db.get_or_404(BossTask, task_id)
    
    if task.boss_id != boss_id:
        return jsonify({'success': False, 'error': 'Задача не принадлежит этому боссу'}), 400
    
    try:
        if request.is_json:
            data = request.json
            title = data.get('title', '').strip()
            description = data.get('description', '').strip() or None
            correct_answer = data.get('correct_answer', '').strip()
            points = data.get('points', task.points)
            delete_image = data.get('delete_image', False)
        else:
            title = request.form.get('title', '').strip()
            description = request.form.get('description', '').strip() or None
            correct_answer = request.form.get('correct_answer', '').strip()
            points = request.form.get('points', task.points)
            if isinstance(points, str):
                try:
                    points = int(points)
                except ValueError:
                    points = task.points
            delete_image = request.form.get('delete_image', 'false').lower() == 'true'
        
        if title:
            task.title = title
        if description is not None:
            task.description = description
        if correct_answer:
            task.correct_answer = correct_answer
        if points is not None and points >= 0:
            task.points = points
        
        # Обработка изображения
        if delete_image and task.image_filename:
            old_filepath = os.path.join(app.config['UPLOAD_FOLDER'], task.image_filename)
            if os.path.exists(old_filepath):
                os.remove(old_filepath)
            task.image_filename = None
        
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename and allowed_file(file.filename):
                if task.image_filename:
                    old_filepath = os.path.join(app.config['UPLOAD_FOLDER'], task.image_filename)
                    if os.path.exists(old_filepath):
                        os.remove(old_filepath)
                
                filename = secure_filename(file.filename)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"boss_{timestamp}_{filename}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                task.image_filename = filename
        
        db.session.commit()
        return jsonify({'success': True, 'task': task.to_dict()})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

# API для удаления задачи босса
@app.route('/api/bosses/<int:boss_id>/tasks/<int:task_id>', methods=['DELETE'])
@admin_required
def delete_boss_task(boss_id, task_id):
    boss = db.get_or_404(Boss, boss_id)
    task = db.get_or_404(BossTask, task_id)
    
    if task.boss_id != boss_id:
        return jsonify({'success': False, 'error': 'Задача не принадлежит этому боссу'}), 400
    
    # Удаляем изображение, если есть
    if task.image_filename:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], task.image_filename)
        if os.path.exists(filepath):
            os.remove(filepath)
    
    db.session.delete(task)
    db.session.commit()
    return jsonify({'success': True})

# Страница рейд босса (доступна для всех)
@app.route('/raid-boss')
def raid_boss_page():
    # Получаем активного босса, если есть, иначе последнего созданного
    active_boss = Boss.query.filter_by(is_active=True).first()
    if not active_boss:
        # Если нет активного, берем последнего созданного босса
        active_boss = Boss.query.order_by(Boss.created_at.desc()).first()
    
    boss_animation_frames = list_animation_frame_urls('boss')

    if not active_boss:
        return render_template('raid_boss.html', boss=None, classes=[], boss_animation_frames=boss_animation_frames)
    
    # Получаем все классы для выбора
    classes = Class.query.all()
    
    # Вычисляем урон по классам
    class_damage = {}
    for class_obj in classes:
        damage = db.session.query(db.func.sum(BossTask.points)).join(
            BossTaskSolution, BossTaskSolution.task_id == BossTask.id
        ).filter(
            BossTaskSolution.boss_id == active_boss.id,
            BossTaskSolution.class_id == class_obj.id,
            BossTaskSolution.is_correct == True
        ).scalar() or 0
        class_damage[class_obj.id] = damage
    
    return render_template(
        'raid_boss.html',
        boss=active_boss,
        classes=classes,
        class_damage=class_damage,
        boss_animation_frames=boss_animation_frames
    )


# Битва за территорию
TERRITORY_MAX_STRENGTH = 1000
TERRITORY_STRENGTH_STEP_SAME = 25
TERRITORY_STRENGTH_STEP_OTHER = 25

@app.route('/territory-battle')
def territory_battle_page():
    # Администратор видит страницу как незарегистрированный пользователь (только просмотр, без участия)
    registration_enabled = get_territory_registration_enabled()
    capture_enabled, capture_start_time, capture_end_time = get_territory_capture_settings()
    is_admin = current_user.is_authenticated and getattr(current_user, 'is_admin', False)
    if is_admin:
        clan_id = None
        can_participate = False
        user_logged_in = False
    else:
        clan_id = current_user.clan_id if current_user.is_authenticated else None
        user_logged_in = current_user.is_authenticated
        can_participate = user_logged_in and registration_enabled and capture_enabled
    clans = Clan.query.order_by(Clan.name).all()
    clans_json = []
    for c in clans:
        clans_json.append({
            'id': c.id,
            'name': c.name,
            'territory_fill_color': c.color or '#6b7280',
            'territory_heraldry_url': url_for('static', filename=_avatar_static_filename(c.flag_filename)) if c.flag_filename else None
        })
    regions_config = TerritoryRegionConfig.query.order_by(TerritoryRegionConfig.region_index).all()
    regions_json = [{'region_index': r.region_index, 'display_name': r.display_name, 'description': r.description or '', 'is_locked': r.is_locked} for r in regions_config]
    states = TerritoryRegionState.query.order_by(TerritoryRegionState.region_index).all()
    state_by_index = {s.region_index: {'owner_clan_id': s.owner_clan_id, 'strength': s.strength} for s in states}
    current_energy = None
    energy_max = None
    avatar_url = None
    clan_flag_url = None
    if user_logged_in and not is_admin and current_user.is_authenticated:
        current_user.ensure_energy_refill()
        current_energy = _user_current_energy_cached(current_user)
        energy_max = current_user.energy
        avatar_url = url_for('static', filename=_avatar_static_filename(current_user.avatar_filename)) if getattr(current_user, 'avatar_filename', None) else None
        if getattr(current_user, 'clan_obj', None) and getattr(current_user.clan_obj, 'flag_filename', None):
            clan_flag_url = url_for('static', filename=_avatar_static_filename(current_user.clan_obj.flag_filename))

    capture_start_time_iso = capture_start_time.isoformat() if capture_start_time else None
    capture_start_time_ms = int(capture_start_time.timestamp() * 1000) if capture_start_time else None
    capture_end_time_ms = int(capture_end_time.timestamp() * 1000) if capture_end_time else None
    clan_pending_join_count = 0
    if user_logged_in and not is_admin and getattr(current_user, 'clan_obj', None) and current_user.clan_obj.owner_id == current_user.id:
        clan_pending_join_count = ClanJoinRequest.query.filter_by(clan_id=current_user.clan_obj.id, status='pending').count()
    # Активные баффы для отображения иконок (только с длительностью; разовые не показываем в списке)
    user_active_buffs = []
    clan_active_buffs = []
    region_active_buffs = {}
    # Баффы областей показываем всем (на карте видно, какие области под эффектами)
    for r in regions_config:
        region_active_buffs[r.region_index] = get_active_buffs_for_display(region_index=r.region_index)
    if user_logged_in and not is_admin and current_user.is_authenticated:
        user_active_buffs = get_active_buffs_for_display(user_id=current_user.id)
        if clan_id:
            clan_active_buffs = get_active_buffs_for_display(clan_id=clan_id)
    return render_template(
        'territory_battle.html',
        clans=clans,
        clans_json=clans_json,
        regions_json=regions_json,
        territory_state_json=state_by_index,
        current_user_clan_id=clan_id,
        is_authenticated=can_participate,
        user_logged_in=user_logged_in,
        registration_enabled=registration_enabled,
        capture_enabled=capture_enabled,
        capture_start_time_iso=capture_start_time_iso,
        capture_start_time_ms=capture_start_time_ms,
        capture_end_time_ms=capture_end_time_ms,
        current_energy=current_energy,
        energy_max=energy_max,
        avatar_url=avatar_url,
        clan_flag_url=clan_flag_url,
        clan_pending_join_count=clan_pending_join_count,
        user_active_buffs=user_active_buffs,
        clan_active_buffs=clan_active_buffs,
        region_active_buffs=region_active_buffs,
    )


@app.route('/api/territory/regions')
def api_territory_regions():
    """Список областей для выбора (например, при использовании предмета «на область»)."""
    regions = TerritoryRegionConfig.query.order_by(TerritoryRegionConfig.region_index).all()
    return jsonify([{'region_index': r.region_index, 'display_name': r.display_name or f'Область {r.region_index + 1}'} for r in regions])


@app.route('/api/territory-battle/server-time')
def api_territory_server_time():
    """Текущее время сервера в Unix ms для синхронизации таймера обратного отсчёта."""
    import time
    return jsonify({'server_time_ms': int(time.time() * 1000)})


@app.route('/territory-battle/rules')
def territory_battle_rules():
    """Страница с обучением и правилами битвы за территорию."""
    return render_template('territory_battle_rules.html')


@app.route('/territory-battle/clans-top')
def territory_clans_top():
    """Топ-10 кланов: сначала по числу контролируемых областей (убыв.), затем по урону+защите (убыв.).
    Если кланов с областями меньше 10, добиваем до 10 кланами с 0 областей (ранжируем их по урону+защите)."""
    # Число областей по каждому клану (включая кланы с 0 областей)
    all_clans_territory = db.session.query(
        Clan.id,
        func.coalesce(func.count(TerritoryRegionState.region_index), 0).label('territory_count')
    ).outerjoin(TerritoryRegionState, Clan.id == TerritoryRegionState.owner_clan_id).group_by(Clan.id).all()

    if not all_clans_territory:
        return render_template('territory_clans_top.html', clans_data=[])

    # Сумма (урон + очки защиты) по каждому клану (кланы без участников/статистики дают 0)
    score_expr = func.coalesce(UserTerritoryStats.total_damage_dealt, 0) + func.coalesce(UserTerritoryStats.total_influence_points, 0)
    clan_scores_rows = db.session.query(
        User.clan_id,
        func.coalesce(func.sum(score_expr), 0).label('clan_score')
    ).outerjoin(UserTerritoryStats, User.id == UserTerritoryStats.user_id).filter(
        User.clan_id.isnot(None)
    ).group_by(User.clan_id).all()
    clan_score_by_id = {row[0]: int(row[1] or 0) for row in clan_scores_rows}

    # Сортировка: сначала по числу областей (убыв.), затем по урон+защита (убыв.); берём топ-10
    sorted_clans = sorted(
        all_clans_territory,
        key=lambda r: (r[1], clan_score_by_id.get(r[0], 0)),
        reverse=True
    )[:10]
    clan_ids = [r[0] for r in sorted_clans]

    # Все кланы топ-10 одним запросом
    clans = Clan.query.filter(Clan.id.in_(clan_ids)).all()
    clan_by_id = {c.id: c for c in clans}

    # Топ участников по (урон + очки защиты) для этих кланов; в Python берём по 10 на клан
    all_members = db.session.query(User, UserTerritoryStats).outerjoin(
        UserTerritoryStats, User.id == UserTerritoryStats.user_id
    ).filter(User.clan_id.in_(clan_ids)).order_by(User.clan_id, score_expr.desc()).all()

    # Группируем: для каждого клана — не более 10 участников (уже отсортированы по score)
    top_per_clan = {}
    for u, stats in all_members:
        cid = u.clan_id
        if cid not in top_per_clan:
            top_per_clan[cid] = []
        if len(top_per_clan[cid]) < 10:
            top_per_clan[cid].append((u, stats))

    clans_data = []
    for clan_id, territory_count in sorted_clans:
        clan = clan_by_id.get(clan_id)
        if not clan:
            continue
        flag_url = url_for('static', filename=_avatar_static_filename(clan.flag_filename)) if clan.flag_filename else None
        members_data = []
        for u, stats in top_per_clan.get(clan_id, []):
            avatar_url = url_for('static', filename=_avatar_static_filename(u.avatar_filename)) if getattr(u, 'avatar_filename', None) else None
            dmg = (stats.total_damage_dealt or 0) if stats else 0
            inf = (stats.total_influence_points or 0) if stats else 0
            members_data.append({
                'id': u.id,
                'character_name': u.character_name or u.username,
                'level': u.level or 1,
                'avatar_url': avatar_url,
                'total_damage_dealt': dmg,
                'total_influence_points': inf,
            })
        clans_data.append({
            'id': clan.id,
            'name': clan.name,
            'flag_url': flag_url,
            'territory_count': territory_count,
            'members': members_data,
        })
    return render_template('territory_clans_top.html', clans_data=clans_data)


def _normalize_answer(s):
    return re.sub(r'\s+', ' ', str(s).strip().lower()) if s else ''


def _territory_difficulty_from_level(level: int) -> int:
    """Определить уровень сложности (1–3) по уровню игрока."""
    if level < 10:
        return 1
    if level <= 20:
        return 2
    return 3


# Имя генератора (из БД) -> функция(difficulty) -> задача или None
TERRITORY_GENERATOR_BY_NAME = {
    'Вычисления': lambda d: generate_territory_computations(difficulty=d) if generate_territory_computations else None,
    'Уравнения': lambda d: generate_equation_task(difficulty=d) if generate_equation_task else None,
    'НОД и НОК': lambda d: generate_territory_gcd_lcm_task(difficulty=d) if generate_territory_gcd_lcm_task else None,
    'Основное свойство дроби': lambda d: generate_fraction_property_task(difficulty=d) if generate_fraction_property_task else None,
    'Общий знаменатель': lambda d: generate_common_denominator_task(difficulty=d) if generate_common_denominator_task else None,
    'Правильные/неправильные дроби': lambda d: generate_proper_improper_fraction_task(difficulty=d) if generate_proper_improper_fraction_task else None,
    'Сложение и вычитание дробей': lambda d: generate_add_sub_fractions_task(difficulty=d) if generate_add_sub_fractions_task else None,
    'Умножение и деление дробей': lambda d: generate_mul_div_fractions_task(difficulty=d) if generate_mul_div_fractions_task else None,
    'Задачи на движение': lambda d: generate_territory_motion_task(difficulty=d) if generate_territory_motion_task else None,
    'Задачи на дроби': lambda d: generate_territory_fraction_word_task(difficulty=d) if generate_territory_fraction_word_task else None,
    'сумма/разность и части': lambda d: generate_territory_two_unknowns_task(difficulty=d) if generate_territory_two_unknowns_task else None,
    'Смешанные числа': lambda d: generate_mixed_numbers_task(difficulty=d) if generate_mixed_numbers_task else None,
    'Совместная работа': lambda d: generate_joint_work_task(difficulty=d) if generate_joint_work_task else None,
}


def _user_current_energy_cached(user):
    """Текущая энергия пользователя без повторного вызова ensure_energy_refill (вызывать после одного refill)."""
    return max(0, user.current_energy if user.current_energy is not None else user.energy)


@app.route('/api/territory-battle/task')
@login_required
def api_territory_task():
    """Выдать задачу для битвы за территорию. Списывает 1 энергию при выдаче (при открытии модалки)."""
    if current_user.is_admin:
        return jsonify({'success': False, 'error': 'Администратор не участвует в битве'}), 403
    if not get_territory_registration_enabled():
        return jsonify({'success': False, 'error': 'Регистрация участников отключена'}), 403
    capture_enabled, _, _ = get_territory_capture_settings()
    if not capture_enabled:
        return jsonify({'success': False, 'error': 'Захват областей отключён. Ожидайте времени старта.'}), 403
    if not current_user.clan_id:
        return jsonify({'success': False, 'error': 'Для участия нужен клан'}), 400
    current_user.ensure_energy_refill()
    energy_now = _user_current_energy_cached(current_user)
    if energy_now < 1:
        return jsonify({'success': False, 'error': 'Недостаточно энергии. Восстанавливается каждые 30 мин (+20% от макс.).'}), 400
    current_user.current_energy = energy_now - 1
    db.session.commit()
    energy_after = energy_now - 1

    region_index = request.args.get('region_index', type=int)
    difficulty = _territory_difficulty_from_level(current_user.level or 1)

    # Область с привязанным генератором — генерируем задачу по имени генератора из БД
    if region_index is not None:
        cfg = TerritoryRegionConfig.query.filter_by(region_index=region_index).first()
        if cfg and cfg.task_generator_id:
            gen = TaskGenerator.query.get(cfg.task_generator_id)
            if gen and gen.name and gen.name.strip() in TERRITORY_GENERATOR_BY_NAME:
                gen_fn = TERRITORY_GENERATOR_BY_NAME[gen.name.strip()]
                if gen_fn:
                    try:
                        gen_task = gen_fn(difficulty)
                        if gen_task:
                            task = TerritoryTask(
                                title=gen_task.get('title', 'Задача'),
                                text=gen_task.get('description', ''),
                                correct_answer=gen_task.get('correct_answer', ''),
                                xp_reward=gen_task.get('points', 20)
                            )
                            db.session.add(task)
                            db.session.commit()
                            task_dict = task.to_dict_public()
                            if gen_task.get('display_frac1'):
                                task_dict['display_frac1'] = gen_task['display_frac1']
                            if gen_task.get('display_frac2'):
                                task_dict['display_frac2'] = gen_task['display_frac2']
                            if gen_task.get('display_frac'):
                                task_dict['display_frac'] = gen_task['display_frac']
                            if gen_task.get('display_operator') is not None:
                                task_dict['display_operator'] = gen_task['display_operator']
                            if 'int_part_zero' in gen_task:
                                task_dict['int_part_zero'] = gen_task['int_part_zero']
                            return jsonify({
                                'success': True,
                                'task': task_dict,
                                'current_energy': energy_after
                            })
                    except Exception as e:
                        logger.exception('Ошибка генерации задачи для области %s (генератор %s): %s',
                                         region_index, gen.name, e)
    # Иначе — случайная задача из БД
    task = TerritoryTask.query.order_by(db.func.random()).first()
    if not task:
        return jsonify({'success': False, 'error': 'Нет доступных задач'}), 404
    return jsonify({
        'success': True,
        'task': task.to_dict_public(),
        'current_energy': energy_after
    })


@app.route('/api/territory-battle/apply-action', methods=['POST'])
@login_required
def api_territory_apply_action():
    """Проверить ответ, начислить опыт, применить урон/влияние по области."""
    if current_user.is_admin:
        return jsonify({'success': False, 'error': 'Администратор не участвует в битве'}), 403
    if not get_territory_registration_enabled():
        return jsonify({'success': False, 'error': 'Регистрация участников отключена'}), 403
    capture_enabled, _, _ = get_territory_capture_settings()
    if not capture_enabled:
        return jsonify({'success': False, 'error': 'Захват областей отключён. Ожидайте времени старта.'}), 403
    data = request.get_json() or {}
    region_index = data.get('region_index')
    task_id = data.get('task_id')
    answer = data.get('answer')
    if region_index is None or task_id is None:
        return jsonify({'success': False, 'error': 'region_index, task_id required'}), 400
    region_index = int(region_index)
    if not current_user.clan_id:
        return jsonify({'success': False, 'error': 'Для участия в битве нужен клан'}), 400
    current_user.ensure_energy_refill()
    current_energy = _user_current_energy_cached(current_user)
    stats = current_user.get_territory_stats()
    task = TerritoryTask.query.get(task_id)
    if not task:
        return jsonify({'success': False, 'error': 'Задача не найдена'}), 404
    # Ответ-дробь: только числитель и знаменатель (num|den); в БД может быть старый формат int|num|den
    if task.title == 'Основное свойство дроби' and task.correct_answer and '|' in task.correct_answer:
        try:
            correct_parts = [p.strip() for p in task.correct_answer.split('|')]
            user_parts = [p.strip() for p in (answer or '').split('|')]
            # Из эталона: старый формат "0|6|7" -> числитель и знаменатель (индексы 1 и 2)
            if len(correct_parts) >= 3:
                correct_num, correct_den = correct_parts[1], correct_parts[2]
            elif len(correct_parts) == 2:
                correct_num, correct_den = correct_parts[0], correct_parts[1]
            else:
                correct_num, correct_den = '', ''
            # Ответ пользователя: только числитель и знаменатель (два поля)
            if len(user_parts) >= 3:
                user_num, user_den = user_parts[1], user_parts[2]
            elif len(user_parts) == 2:
                user_num, user_den = user_parts[0], user_parts[1]
            else:
                user_num, user_den = '', ''
            # Сравниваем как числа (чтобы "6" и "06" засчитывались)
            try:
                u_n, u_d = int(user_num or 0), int(user_den or 0)
                c_n, c_d = int(correct_num or 0), int(correct_den or 0)
                correct = (u_d > 0 and c_d > 0 and u_n == c_n and u_d == c_d)
            except (ValueError, TypeError):
                correct = (user_num == correct_num and user_den == correct_den)
        except Exception:
            correct = False
    elif task.title == 'Общий знаменатель' and task.correct_answer and task.correct_answer.count('|') >= 3:
        try:
            correct_parts = [p.strip() for p in task.correct_answer.split('|')]
            user_parts = [p.strip() for p in (answer or '').split('|')]
            if len(correct_parts) >= 4 and len(user_parts) >= 4:
                try:
                    correct = (
                        int(user_parts[0] or 0) == int(correct_parts[0] or 0)
                        and int(user_parts[1] or 0) == int(correct_parts[1] or 0)
                        and int(user_parts[2] or 0) == int(correct_parts[2] or 0)
                        and int(user_parts[3] or 0) == int(correct_parts[3] or 0)
                    )
                except (ValueError, TypeError):
                    correct = (
                        user_parts[0] == correct_parts[0] and user_parts[1] == correct_parts[1]
                        and user_parts[2] == correct_parts[2] and user_parts[3] == correct_parts[3]
                    )
            else:
                correct = False
        except Exception:
            correct = False
    elif task.title in ('Сложение и вычитание дробей', 'Умножение и деление дробей', 'Смешанные числа') and task.correct_answer and task.correct_answer.count('|') >= 2:
        try:
            correct_parts = [p.strip() for p in task.correct_answer.split('|')]
            user_parts = [p.strip() for p in (answer or '').split('|')]
            if len(correct_parts) >= 3 and len(user_parts) >= 3:
                try:
                    correct = (
                        int(user_parts[0] or 0) == int(correct_parts[0] or 0)
                        and int(user_parts[1] or 0) == int(correct_parts[1] or 0)
                        and int(user_parts[2] or 0) == int(correct_parts[2] or 0)
                    )
                except (ValueError, TypeError, IndexError):
                    correct = False
            else:
                correct = False
        except Exception:
            correct = False
    elif task.title == 'Правильные/неправильные дроби' and task.correct_answer and '|' in task.correct_answer:
        try:
            correct_parts = [p.strip() for p in task.correct_answer.split('|')]
            user_parts = [p.strip() for p in (answer or '').split('|')]
            if len(correct_parts) == 3:
                try:
                    correct = (
                        int(user_parts[0] or 0) == int(correct_parts[0] or 0)
                        and int(user_parts[1] or 0) == int(correct_parts[1] or 0)
                        and int(user_parts[2] or 0) == int(correct_parts[2] or 0)
                    )
                except (ValueError, TypeError, IndexError):
                    correct = False
            elif len(correct_parts) == 2:
                if len(user_parts) >= 3:
                    user_num, user_den = user_parts[1], user_parts[2]
                elif len(user_parts) == 2:
                    user_num, user_den = user_parts[0], user_parts[1]
                else:
                    user_num, user_den = '', ''
                try:
                    correct = (
                        int(user_num or 0) == int(correct_parts[0] or 0)
                        and int(user_den or 0) == int(correct_parts[1] or 0)
                        and int(user_den or 0) > 0
                    )
                except (ValueError, TypeError):
                    correct = False
            else:
                correct = False
        except Exception:
            correct = False
    else:
        correct = _normalize_answer(answer) == _normalize_answer(task.correct_answer)
    clan_id = current_user.clan_id
    cfg = TerritoryRegionConfig.query.filter_by(region_index=region_index).first()
    if cfg and cfg.is_locked:
        return jsonify({'success': False, 'error': 'Region is locked'}), 400
    state = TerritoryRegionState.query.filter_by(region_index=region_index).first()
    if not state:
        state = TerritoryRegionState(region_index=region_index, owner_class_id=None, owner_clan_id=None, strength=0)
        db.session.add(state)
    # Энергия уже списана при открытии модалки с заданием (api_territory_task)
    # Урон при атаке (чужая/нейтральная область), защита при усилении своей
    is_own_region = (state.owner_clan_id == clan_id)
    base_power = current_user.defense if is_own_region else current_user.damage
    mult = _get_multipliers_for_action(current_user.id, clan_id, region_index, is_attack=not is_own_region)
    power_pct = mult['defense_pct'] if is_own_region else mult['damage_pct']
    power = max(1, int(round(base_power * (1 + power_pct / 100.0))))
    if not correct:
        db.session.commit()
        return jsonify({
            'success': True, 'correct': False,
            'owner_clan_id': state.owner_clan_id, 'strength': state.strength,
            'current_energy': current_energy
        })
    # Множители опыта и нумов от баффов
    xp_mult = 1 + (mult['xp_reward_pct'] / 100.0)
    nums_mult = 1 + (mult['nums_reward_pct'] / 100.0)
    effective_xp = max(0, int(round(task.xp_reward * xp_mult)))
    # Начисляем опыт
    new_level, leveled_up = current_user.add_experience(effective_xp)
    if leveled_up:
        # При достижении нового уровня энергия восстанавливается до максимума
        current_user.current_energy = current_user.energy
        current_energy = current_user.energy
    # Начисляем Нумы за правильное решение (с разбросом по уровню)
    nums_gained = max(0, int(round(roll_nums_reward(current_user.level) * nums_mult)))
    current_user.nums_balance = (current_user.nums_balance or 0) + nums_gained
    if state.owner_clan_id is None:
        state.owner_clan_id = clan_id
        state.strength = min(TERRITORY_MAX_STRENGTH, state.strength + power)
        stats.total_influence_points += power
    elif state.owner_clan_id == clan_id:
        state.strength = min(TERRITORY_MAX_STRENGTH, state.strength + power)
        stats.total_influence_points += power
    else:
        state.strength = max(0, state.strength - power)
        stats.total_damage_dealt += power
        if state.strength == 0:
            state.owner_clan_id = clan_id
            state.strength = power
            stats.total_influence_points += power
    _consume_one_shot_buffs(current_user.id, clan_id, region_index)
    db.session.commit()
    xp_needed = current_user.xp_needed_for_next_level
    xp_pct = round((current_user.xp_in_current_level / xp_needed * 100), 1) if xp_needed else 100
    return jsonify({
        'success': True, 'correct': True,
        'owner_clan_id': state.owner_clan_id, 'strength': state.strength,
        'xp_gained': effective_xp, 'level': new_level, 'leveled_up': leveled_up,
        'nums_gained': nums_gained,
        'player_nums_balance': current_user.nums_balance or 0,
        'current_energy': current_energy,
        'player_level': current_user.level,
        'player_xp_in_level': current_user.xp_in_current_level,
        'player_xp_needed': xp_needed,
        'player_xp_pct': xp_pct,
        'player_damage': current_user.damage,
        'player_defense': current_user.defense
    })


# Тестовая страница для просмотра анимации сундука (без логики рейда/дропа)
@app.route('/chest-test')
def chest_test_page():
    return render_template('chest_test.html')

# API для получения случайной доступной задачи босса
@app.route('/api/raid-boss/task', methods=['GET'])
def get_random_boss_task():
    from sqlalchemy import func
    active_boss = Boss.query.filter_by(is_active=True).first()
    if not active_boss:
        return jsonify({'success': False, 'error': 'Нет активного босса'}), 404
    
    # Получаем задачи, которые ещё не решены, ОДНИМ запросом (без N+1)
    solved_exists = db.session.query(BossTaskSolution.id).filter(
        BossTaskSolution.task_id == BossTask.id,
        BossTaskSolution.is_correct == True
    ).exists()
    available_query = (
        BossTask.query
        .filter(BossTask.boss_id == active_boss.id)
        .filter(~solved_exists)
        .order_by(BossTask.id.asc())
    )
    
    total_available = available_query.count()
    if total_available <= 0:
        return jsonify({
            'success': True, 
            'boss_defeated': True,
            'message': 'Босс побежден! Все задачи решены.'
        })
    
    # Выбираем случайную задачу (без загрузки всех задач в память)
    offset = random.randrange(total_available)
    random_task = available_query.offset(offset).limit(1).first()
    if not random_task:
        # Редкий случай гонки/изменений: считаем, что задач больше нет
        return jsonify({
            'success': True,
            'boss_defeated': True,
            'message': 'Босс побежден! Все задачи решены.'
        })

    return jsonify({
        'success': True,
        # Мы гарантировали, что задача не решена, поэтому не делаем лишний запрос в to_dict()
        'task': random_task.to_dict(is_solved_override=False),
        'boss_defeated': False
    })

# API для сохранения имени пользователя
@app.route('/api/raid-boss/save-user', methods=['POST'])
def save_boss_user():
    try:
        data = request.json
        if not data:
            return jsonify({'success': False, 'error': 'Данные не получены'}), 400
        
        name = data.get('name', '').strip()
        user_id = data.get('user_id', None)  # текущий ID пользователя (если меняем имя)
        
        # Валидация имени
        is_valid, error_message = validate_user_name(name)
        if not is_valid:
            logger.warning(f"Попытка сохранить невалидное имя: {name}")
            return jsonify({'success': False, 'error': error_message}), 400

        # Если user_id передан и валиден — обновляем имя у этого же пользователя (ID НЕ меняем).
        if user_id is not None and str(user_id).strip() != '':
            is_uid_valid, user_obj, uid_error = validate_user_id(user_id)
            if is_uid_valid and user_obj:
                user_obj.name = name
                db.session.commit()
                logger.info(f"Обновлено имя пользователя: user_id={user_obj.id}, name={name}")
                return jsonify({
                    'success': True,
                    'user_id': user_obj.id,
                    'user_name': user_obj.name
                })

            logger.warning(f"Передан невалидный user_id для смены имени: {user_id} ({uid_error}). Создаю нового пользователя.")

        # Иначе создаем нового пользователя (имя НЕ уникально)
        try:
            new_user = BossUser(name=name)
            db.session.add(new_user)
            db.session.commit()
            logger.info(f"Создан новый пользователь: user_id={new_user.id}, name={name}")
            return jsonify({
                'success': True,
                'user_id': new_user.id,
                'user_name': new_user.name
            })
        except Exception as e:
            db.session.rollback()
            logger.error(f"Неожиданная ошибка при создании пользователя: {e}")
            return jsonify({'success': False, 'error': 'Ошибка при создании пользователя'}), 500
            
    except Exception as e:
        logger.error(f"Критическая ошибка в save_boss_user: {e}")
        return jsonify({'success': False, 'error': 'Внутренняя ошибка сервера'}), 500

# API для отправки ответа на задачу босса
@app.route('/api/raid-boss/submit', methods=['POST'])
def submit_boss_task_answer():
    try:
        data = request.json
        if not data:
            return jsonify({'success': False, 'error': 'Данные не получены'}), 400
        
        task_id = data.get('task_id')
        class_id = data.get('class_id')
        user_name = data.get('user_name', '').strip()
        user_id = data.get('user_id')  # ID пользователя из куки
        answer = data.get('answer', '').strip()
        
        # Валидация обязательных полей
        if not task_id or not class_id or not answer:
            return jsonify({'success': False, 'error': 'Все поля обязательны'}), 400
        
        # Валидация и проверка user_id на сервере
        validated_user = None
        if user_id:
            is_valid, validated_user, error = validate_user_id(user_id)
            if not is_valid:
                logger.warning(f"Невалидный user_id: {user_id}, ошибка: {error}")
                # Не блокируем отправку ответа, но не обрабатываем дроп
                user_id = None
            else:
                # Используем валидированное имя пользователя
                if validated_user and not user_name:
                    user_name = validated_user.name
        
        # Если имя пользователя не указано, используем название класса
        if not user_name:
            class_obj = Class.query.get(class_id)
            if class_obj:
                user_name = class_obj.name
            else:
                user_name = 'Аноним'
        
        # Получаем задачу и босса
        try:
            task = db.get_or_404(BossTask, task_id)
        except Exception:
            return jsonify({'success': False, 'error': 'Задача не найдена'}), 404
        
        active_boss = Boss.query.filter_by(is_active=True, id=task.boss_id).first()
        
        if not active_boss:
            return jsonify({'success': False, 'error': 'Босс не активен'}), 404
        
        # Проверяем, не решена ли задача уже
        if task.is_solved():
            return jsonify({'success': False, 'error': 'Задача уже решена'}), 400
        
        # Проверяем правильность ответа
        is_correct = task.correct_answer.strip().lower() == answer.strip().lower()

        # Записываем в БД ТОЛЬКО правильные решения
        if not is_correct:
            return jsonify({
                'success': True,
                'correct': False,
                'message': 'Неверный ответ. Попробуйте еще раз!',
                'update_progress': True,
                'is_correct': False
            })

        # Сохраняем правильное решение (уникальный partial индекс защищает от race condition)
        try:
            solution = BossTaskSolution(
                boss_id=active_boss.id,
                task_id=task.id,
                class_id=class_id,
                user_name=user_name,
                user_id=validated_user.id if validated_user else None,
                answer=answer,
                is_correct=True
            )
            db.session.add(solution)
            db.session.commit()
            logger.info(
                f"Правильный ответ сохранен: task_id={task_id}, "
                f"user_id={validated_user.id if validated_user else None}"
            )
        except IntegrityError:
            # Кто-то успел записать правильный ответ параллельно
            db.session.rollback()
            return jsonify({'success': False, 'error': 'Задача уже решена другим пользователем'}), 400
        except Exception as e:
            db.session.rollback()
            logger.error(f"Ошибка при сохранении правильного ответа: {e}")
            return jsonify({'success': False, 'error': 'Ошибка при сохранении ответа'}), 500

        # Обрабатываем дроп только если user_id валиден
        try:
            drop_reward = None
            if validated_user:
                drop_reward, drop_error = process_drop_reward(
                    active_boss.id,
                    validated_user.id,
                    task.id,
                    class_id=class_id
                )
                if drop_error:
                    logger.warning(f"Ошибка при обработке дропа: {drop_error}")

            response_data = {
                'success': True,
                'correct': True,
                'message': f'Правильно! Вы нанесли {task.points} урона боссу!',
                'update_progress': True,
                'is_correct': True
            }

            if drop_reward:
                response_data['drop_reward'] = {
                    'drop_name': drop_reward.drop.name if drop_reward.drop else '',
                    'drop_id': drop_reward.drop_id,
                    # вероятность/редкость дропа для UI (high/medium/very_low)
                    'probability': drop_reward.drop.probability if drop_reward.drop else None
                }

            return jsonify(response_data)
        except Exception as e:
            logger.error(f"Ошибка при обработке дропа/ответа: {e}")
            return jsonify({
                'success': True,
                'correct': True,
                'message': f'Правильно! Вы нанесли {task.points} урона боссу!',
                'update_progress': True,
                'is_correct': True
            })
            
    except Exception as e:
        logger.error(f"Критическая ошибка в submit_boss_task_answer: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'error': 'Внутренняя ошибка сервера'}), 500

# API для получения статистики босса
@app.route('/api/raid-boss/stats')
def get_boss_stats():
    # Получаем boss_id из параметров запроса, если есть
    boss_id = request.args.get('boss_id', type=int)
    
    if boss_id:
        boss = Boss.query.get(boss_id)
    else:
        # Если не указан, ищем активного, иначе последнего
        boss = Boss.query.filter_by(is_active=True).first()
        if not boss:
            boss = Boss.query.order_by(Boss.created_at.desc()).first()
    
    if not boss:
        return jsonify({'success': False, 'error': 'Нет босса'}), 404
    
    # Получаем все классы
    classes = Class.query.all()
    class_damage = {}
    
    for class_obj in classes:
        damage = db.session.query(db.func.sum(BossTask.points)).join(
            BossTaskSolution, BossTaskSolution.task_id == BossTask.id
        ).filter(
            BossTaskSolution.boss_id == boss.id,
            BossTaskSolution.class_id == class_obj.id,
            BossTaskSolution.is_correct == True
        ).scalar() or 0
        class_damage[class_obj.id] = {
            'class_name': class_obj.name,
            'damage': damage
        }
    
    total_health = boss.get_total_health()
    current_health = boss.get_current_health(total_health=total_health)
    
    return jsonify({
        'success': True,
        'boss': {
            'id': boss.id,
            'name': boss.name,
            'total_health': total_health,
            'current_health': current_health,
            'is_active': boss.is_active
        },
        'class_damage': class_damage
    })


# Публичное API: топ игроков по классу для страницы рейд-босса
# Важно: отдаём данные ТОЛЬКО после победы босса (HP=0), чтобы не подсвечивать результаты во время рейда.
@app.route('/api/raid-boss/top-users-by-class', methods=['GET'])
def raid_boss_top_users_by_class():
    # boss_id можно передать явно; иначе используем активного, либо последнего созданного
    boss_id = request.args.get('boss_id', type=int)
    limit = request.args.get('limit', default=10, type=int)
    class_id = request.args.get('class_id', type=int)

    if limit is None or limit <= 0:
        limit = 10
    # страхуем от слишком больших значений
    limit = min(int(limit), 50)

    if boss_id:
        boss = Boss.query.get(boss_id)
    else:
        boss = Boss.query.filter_by(is_active=True).first()
        if not boss:
            boss = Boss.query.order_by(Boss.created_at.desc()).first()

    if not boss:
        return jsonify({'success': False, 'error': 'Нет босса'}), 404

    total_health = boss.get_total_health()
    current_health = boss.get_current_health(total_health=total_health)
    if current_health > 0:
        return jsonify({'success': False, 'error': 'Босс ещё не побеждён'}), 403

    # Для публичной страницы рейда склеиваем одинаковые имена (без учёта регистра)
    _, top_by_class = _get_boss_top_players_by_class_merged_names_data(boss_id=boss.id, limit=limit)

    if class_id is not None:
        class_id_int = int(class_id)
        cls_block = next((x for x in top_by_class if int(x.get('class_id')) == class_id_int), None)
        if not cls_block:
            # если данных нет — возвращаем пустой список (класс мог существовать, но без участников)
            class_obj = Class.query.get(class_id_int)
            return jsonify({
                'success': True,
                'boss': boss.to_dict(),
                'class_id': class_id_int,
                'class_name': class_obj.name if class_obj else None,
                'users': []
            })
        return jsonify({
            'success': True,
            'boss': boss.to_dict(),
            'class_id': int(cls_block.get('class_id')),
            'class_name': cls_block.get('class_name'),
            'users': cls_block.get('users', [])
        })

    return jsonify({
        'success': True,
        'boss': boss.to_dict(),
        'top_by_class': top_by_class
    })

# API для управления дропами босса
@app.route('/api/bosses/<int:boss_id>/drops', methods=['GET'])
@admin_required
def get_boss_drops(boss_id):
    boss = db.get_or_404(Boss, boss_id)
    drops = BossDrop.query.filter_by(boss_id=boss_id).all()
    return jsonify({'success': True, 'drops': [drop.to_dict() for drop in drops]})

@app.route('/api/bosses/<int:boss_id>/drops', methods=['POST'])
@admin_required
def create_boss_drop(boss_id):
    boss = db.get_or_404(Boss, boss_id)
    data = request.json
    name = data.get('name', '').strip()
    probability = data.get('probability', 'medium')
    max_per_user_raw = data.get('max_per_user', None)
    
    if not name:
        return jsonify({'success': False, 'error': 'Название дропа обязательно'}), 400
    
    if probability not in ['high', 'medium', 'very_low']:
        return jsonify({'success': False, 'error': 'Неверная вероятность'}), 400

    max_per_user = None
    if max_per_user_raw is not None and str(max_per_user_raw).strip() != '':
        try:
            max_per_user = int(max_per_user_raw)
        except (ValueError, TypeError):
            return jsonify({'success': False, 'error': 'Неверный формат max_per_user'}), 400
        if max_per_user <= 0:
            max_per_user = None  # 0/отрицательное = без ограничений
    
    new_drop = BossDrop(
        boss_id=boss_id,
        name=name,
        probability=probability,
        max_per_user=max_per_user
    )
    db.session.add(new_drop)
    db.session.commit()
    
    return jsonify({'success': True, 'drop': new_drop.to_dict()})

@app.route('/api/bosses/<int:boss_id>/drops/<int:drop_id>', methods=['PUT'])
@admin_required
def update_boss_drop(boss_id, drop_id):
    boss = db.get_or_404(Boss, boss_id)
    drop = db.get_or_404(BossDrop, drop_id)
    
    if drop.boss_id != boss_id:
        return jsonify({'success': False, 'error': 'Дроп не принадлежит этому боссу'}), 400
    
    data = request.json
    if 'name' in data:
        drop.name = data['name'].strip()
    if 'probability' in data:
        if data['probability'] not in ['high', 'medium', 'very_low']:
            return jsonify({'success': False, 'error': 'Неверная вероятность'}), 400
        drop.probability = data['probability']
    if 'max_per_user' in data:
        raw = data.get('max_per_user', None)
        if raw is None or str(raw).strip() == '':
            drop.max_per_user = None
        else:
            try:
                value = int(raw)
            except (ValueError, TypeError):
                return jsonify({'success': False, 'error': 'Неверный формат max_per_user'}), 400
            drop.max_per_user = None if value <= 0 else value
    
    db.session.commit()
    return jsonify({'success': True, 'drop': drop.to_dict()})

@app.route('/api/bosses/<int:boss_id>/drops/<int:drop_id>', methods=['DELETE'])
@admin_required
def delete_boss_drop(boss_id, drop_id):
    boss = db.get_or_404(Boss, boss_id)
    drop = db.get_or_404(BossDrop, drop_id)
    
    if drop.boss_id != boss_id:
        return jsonify({'success': False, 'error': 'Дроп не принадлежит этому боссу'}), 400
    
    db.session.delete(drop)
    db.session.commit()
    return jsonify({'success': True})

# API для получения списка пользователей босса
@app.route('/api/bosses/<int:boss_id>/users', methods=['GET'])
@admin_required
def get_boss_users(boss_id):
    boss = db.get_or_404(Boss, boss_id)
    # Получаем всех пользователей, которые решали задачи этого босса
    users = db.session.query(BossUser).join(
        BossTaskSolution, BossTaskSolution.user_id == BossUser.id
    ).filter(
        BossTaskSolution.boss_id == boss_id
    ).distinct().all()
    
    return jsonify({'success': True, 'users': [user.to_dict() for user in users]})


def _get_boss_top_users_by_class_data(boss_id: int, limit: int = 10):
    """
    Возвращает (boss, top_by_class) для boss_id.

    top_by_class: список объектов:
      {class_id, class_name, users: [{user_id, user_name, solved_correct, last_correct_at, position}]}

    Правила:
    - "Основной" класс пользователя выбирается по большинству его правильных решений.
      Тай-брейк: более поздний solved_at, затем меньший class_id.
    - Число решенных задач для рейтинга = количество правильных решений пользователя В ЕГО ОСНОВНОМ КЛАССЕ.
      (Это устраняет ситуацию, когда пользователь попадает в топ класса за счёт решений другим классом.)
    - Ранжирование внутри класса: solved_correct desc, last_correct_at desc, user_id asc.
    """
    from sqlalchemy import func

    boss = db.get_or_404(Boss, boss_id)

    # Считаем, сколько правильных решений каждый пользователь отправил за каждый класс
    class_counts = db.session.query(
        BossTaskSolution.user_id.label('user_id'),
        BossTaskSolution.class_id.label('class_id'),
        func.count(BossTaskSolution.id).label('cnt'),
        func.max(BossTaskSolution.solved_at).label('last_at')
    ).filter(
        BossTaskSolution.boss_id == boss_id,
        BossTaskSolution.is_correct == True,
        BossTaskSolution.user_id.isnot(None)
    ).group_by(
        BossTaskSolution.user_id,
        BossTaskSolution.class_id
    ).subquery()

    # Ранжируем классы внутри каждого пользователя, чтобы выбрать "основной"
    main_class_ranked = db.session.query(
        class_counts.c.user_id.label('user_id'),
        class_counts.c.class_id.label('main_class_id'),
        func.row_number().over(
            partition_by=class_counts.c.user_id,
            order_by=(
                class_counts.c.cnt.desc(),
                class_counts.c.last_at.desc(),
                class_counts.c.class_id.asc()
            )
        ).label('rn')
    ).subquery()

    main_class = db.session.query(
        main_class_ranked.c.user_id,
        main_class_ranked.c.main_class_id
    ).filter(
        main_class_ranked.c.rn == 1
    ).subquery()

    # Для рейтинга берём счётчик/последнюю дату ИМЕННО по основному классу
    main_class_stats = db.session.query(
        class_counts.c.user_id.label('user_id'),
        class_counts.c.class_id.label('class_id'),
        class_counts.c.cnt.label('solved_correct'),
        class_counts.c.last_at.label('last_correct_at')
    ).subquery()

    ranked = db.session.query(
        main_class.c.main_class_id.label('class_id'),
        Class.name.label('class_name'),
        BossUser.id.label('user_id'),
        BossUser.name.label('user_name'),
        main_class_stats.c.solved_correct.label('solved_correct'),
        main_class_stats.c.last_correct_at.label('last_correct_at'),
        func.row_number().over(
            partition_by=main_class.c.main_class_id,
            order_by=(
                main_class_stats.c.solved_correct.desc(),
                main_class_stats.c.last_correct_at.desc(),
                BossUser.id.asc()
            )
        ).label('pos')
    ).join(
        BossUser, BossUser.id == main_class.c.user_id
    ).join(
        Class, Class.id == main_class.c.main_class_id
    ).join(
        main_class_stats,
        db.and_(
            main_class_stats.c.user_id == main_class.c.user_id,
            main_class_stats.c.class_id == main_class.c.main_class_id
        )
    ).subquery()

    rows = db.session.query(
        ranked.c.class_id,
        ranked.c.class_name,
        ranked.c.user_id,
        ranked.c.user_name,
        ranked.c.solved_correct,
        ranked.c.last_correct_at,
        ranked.c.pos
    ).filter(
        ranked.c.pos <= int(limit)
    ).order_by(
        ranked.c.class_name.asc(),
        ranked.c.pos.asc()
    ).all()

    by_class: dict[int, dict] = {}
    for r in rows:
        class_id = int(r.class_id)
        if class_id not in by_class:
            by_class[class_id] = {
                'class_id': class_id,
                'class_name': r.class_name,
                'users': []
            }
        by_class[class_id]['users'].append({
            'user_id': int(r.user_id),
            'user_name': r.user_name,
            'solved_correct': int(r.solved_correct or 0),
            'last_correct_at': r.last_correct_at.isoformat() if r.last_correct_at else None,
            'position': int(r.pos)
        })

    return boss, list(by_class.values())


def _get_boss_top_players_by_class_merged_names_data(boss_id: int, limit: int = 10):
    """
    Версия топа по классам, которая объединяет пользователей с одинаковыми именами
    (без учёта регистра) и суммирует число правильных решений.

    Возвращает (boss, top_by_class), где top_by_class:
      {class_id, class_name, users: [{user_id, user_name, solved_correct, last_correct_at, position}]}

    Примечание:
    - В этом режиме один "пользователь" может соответствовать нескольким BossUser.id.
      Для стабильности отдаём user_id = минимальный BossUser.id среди объединённых.
    """
    import re
    from sqlalchemy import func

    boss = db.get_or_404(Boss, boss_id)

    def canonical_name_key(raw: str) -> str:
        """
        Делает ключ, одинаковый для:
          - разного регистра
          - лишних пробелов/пунктуации
          - перестановки слов (например, "иванов иван" == "иван иванов")
        """
        s = (raw or '').strip().lower()
        if not s:
            return ''
        s = s.replace('ё', 'е')
        # всё, что не буква/цифра — в пробел
        s = re.sub(r'[^0-9a-zа-я]+', ' ', s, flags=re.IGNORECASE)
        parts = [p for p in s.split() if p]
        if not parts:
            return ''
        parts.sort()
        return ' '.join(parts)

    # База: считаем по "сырому" ключу (lower(trim(name))) и классу, затем уже склеиваем в Python
    raw_key_expr = func.lower(func.trim(BossUser.name))
    base_rows = db.session.query(
        raw_key_expr.label('raw_key'),
        BossTaskSolution.class_id.label('class_id'),
        func.count(BossTaskSolution.id).label('cnt'),
        func.max(BossTaskSolution.solved_at).label('last_at'),
        func.min(BossUser.id).label('min_user_id'),
        func.min(BossUser.name).label('any_name')
    ).join(
        BossUser, BossUser.id == BossTaskSolution.user_id
    ).filter(
        BossTaskSolution.boss_id == boss_id,
        BossTaskSolution.is_correct == True,
        BossTaskSolution.user_id.isnot(None),
        BossUser.name.isnot(None),
        func.length(func.trim(BossUser.name)) > 0
    ).group_by(
        raw_key_expr,
        BossTaskSolution.class_id
    ).all()

    # 1) Склеиваем варианты имён в один ключ + суммируем по классу
    per_name_class: dict[tuple[str, int], dict] = {}
    # для отображения имени: выберем вариант с наибольшим суммарным cnt (тай-брейк: last_at)
    display_choice: dict[str, dict] = {}

    for r in base_rows:
        raw_key = str(r.raw_key or '').strip()
        canon = canonical_name_key(raw_key)
        if not canon:
            continue
        class_id = int(r.class_id)
        cnt = int(r.cnt or 0)
        last_at = r.last_at
        min_user_id = int(r.min_user_id) if r.min_user_id is not None else None
        any_name = r.any_name

        k = (canon, class_id)
        agg = per_name_class.get(k)
        if not agg:
            per_name_class[k] = {
                'canon': canon,
                'class_id': class_id,
                'cnt': cnt,
                'last_at': last_at,
                'min_user_id': min_user_id,
            }
        else:
            agg['cnt'] += cnt
            if last_at and (agg['last_at'] is None or last_at > agg['last_at']):
                agg['last_at'] = last_at
            if min_user_id is not None:
                if agg['min_user_id'] is None or min_user_id < agg['min_user_id']:
                    agg['min_user_id'] = min_user_id

        dc = display_choice.get(canon)
        score = (cnt, last_at or 0)
        if not dc or score > dc['score']:
            display_choice[canon] = {
                'score': score,
                'name': any_name or raw_key
            }

    # 2) Для каждого канонического имени выбираем "основной" класс
    per_name: dict[str, dict] = {}
    for (canon, class_id), st in per_name_class.items():
        cur = per_name.get(canon)
        cand = (st['cnt'], st['last_at'] or 0, -class_id)  # -class_id чтобы меньший class_id был "больше" при сравнении
        if not cur or cand > cur['best']:
            per_name[canon] = {
                'best': cand,
                'main_class_id': class_id,
                'solved_correct': st['cnt'],
                'last_correct_at': st['last_at'],
                'min_user_id': st['min_user_id'],
            }

    # 3) Группируем по основному классу и ранжируем
    class_names = {c.id: c.name for c in Class.query.all()}
    by_class_users: dict[int, list] = {}
    for canon, info in per_name.items():
        class_id = int(info['main_class_id'])
        by_class_users.setdefault(class_id, []).append({
            'canon': canon,
            'user_id': info['min_user_id'],
            'user_name': (display_choice.get(canon) or {}).get('name') or canon,
            'solved_correct': int(info['solved_correct'] or 0),
            'last_correct_at': info['last_correct_at'],
        })

    top_by_class: list[dict] = []
    for class_id, users in by_class_users.items():
        users.sort(key=lambda u: (
            -int(u['solved_correct'] or 0),
            -(u['last_correct_at'].timestamp() if u['last_correct_at'] else 0),
            u['canon']
        ))
        users = users[: int(limit)]
        out_users = []
        for idx, u in enumerate(users, start=1):
            out_users.append({
                'user_id': u['user_id'],
                'user_name': u['user_name'],
                'solved_correct': int(u['solved_correct'] or 0),
                'last_correct_at': u['last_correct_at'].isoformat() if u['last_correct_at'] else None,
                'position': idx
            })
        top_by_class.append({
            'class_id': int(class_id),
            'class_name': class_names.get(class_id),
            'users': out_users
        })

    top_by_class.sort(key=lambda x: (x.get('class_name') or ''))
    return boss, top_by_class


# API: топ-10 пользователей по каждому классу (класс определяется по большинству отправленных решений)
@app.route('/api/bosses/<int:boss_id>/top-users-by-class', methods=['GET'])
@admin_required
def get_boss_top_users_by_class(boss_id):
    boss, top_by_class = _get_boss_top_users_by_class_data(boss_id=boss_id, limit=10)
    return jsonify({
        'success': True,
        'boss': boss.to_dict(),
        'top_by_class': top_by_class
    })


# Админ-страница: топ-10 по классам (таблица)
@app.route('/admin/bosses/<int:boss_id>/top-users-by-class', methods=['GET'])
@admin_required
def admin_boss_top_users_by_class(boss_id):
    boss, top_by_class = _get_boss_top_users_by_class_data(boss_id=boss_id, limit=10)
    return render_template(
        'admin/boss_top_users_by_class.html',
        boss=boss,
        boss_dict=boss.to_dict(),
        top_by_class=top_by_class
    )

# API для получения списка выпавших дропов
@app.route('/api/bosses/<int:boss_id>/drop-rewards', methods=['GET'])
@admin_required
def get_boss_drop_rewards(boss_id):
    boss = db.get_or_404(Boss, boss_id)
    rewards = BossDropReward.query.filter_by(boss_id=boss_id).order_by(
        BossDropReward.received_at.desc()
    ).all()
    
    # Для старых записей (до добавления class_id/task_id) пробуем аккуратно восстановить класс
    # по последнему правильному ответу пользователя по этому боссу.
    response_rewards = []
    for reward in rewards:
        data = reward.to_dict()
        if not data.get('class_id'):
            inferred_solution = BossTaskSolution.query.filter_by(
                boss_id=boss_id,
                user_id=reward.user_id,
                is_correct=True
            ).order_by(BossTaskSolution.solved_at.desc()).first()
            if inferred_solution:
                data['class_id'] = inferred_solution.class_id
                inferred_class = Class.query.get(inferred_solution.class_id)
                data['class_name'] = inferred_class.name if inferred_class else None
        response_rewards.append(data)

    return jsonify({'success': True, 'rewards': response_rewards})

# Обработчик завершения приложения для остановки планировщика
@app.teardown_appcontext
def shutdown_scheduler(exception):
    pass  # Планировщик будет работать в фоне


if __name__ == '__main__':
    try:
        app.run(debug=True)
    finally:
        # Останавливаем планировщик при завершении приложения
        if scheduler.running:
            scheduler.shutdown()
