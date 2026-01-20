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
from sqlalchemy import case, cast, Float, Index, and_
from sqlalchemy.exc import IntegrityError
import random
import os
import logging
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

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///valera.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads/tasks'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

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
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

class Class(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    students_balance = db.Column(db.Integer, default=0)
    valera_balance = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
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

class ShopItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    price = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'price': self.price
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
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'rewards_list': self.rewards_list,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'total_health': sum(task.points for task in self.tasks) if self.tasks else 0,
            'current_health': self.get_current_health()
        }
    
    def get_current_health(self):
        """Возвращает текущее здоровье босса (сумма очков всех задач минус нанесенный урон)"""
        from sqlalchemy import func
        total_health = sum(task.points for task in self.tasks) if self.tasks else 0
        # Вычисляем суммарный урон из правильно решенных задач
        damage_dealt = db.session.query(func.sum(BossTask.points)).join(
            BossTaskSolution, BossTaskSolution.task_id == BossTask.id
        ).filter(
            BossTaskSolution.boss_id == self.id,
            BossTaskSolution.is_correct == True
        ).scalar() or 0
        return max(0, total_health - damage_dealt)

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
    
    def to_dict(self):
        return {
            'id': self.id,
            'boss_id': self.boss_id,
            'title': self.title,
            'description': self.description,
            'image_filename': self.image_filename,
            'correct_answer': self.correct_answer,
            'points': self.points,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'is_solved': self.is_solved()
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
    
    # Индексы для оптимизации запросов
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
    
    # Создание директории для загрузки изображений
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
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
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('index'))
        else:
            flash('Неверное имя пользователя или пароль', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы успешно вышли из системы', 'info')
    return redirect(url_for('index'))

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
    return render_template('rating.html', classes=classes)

# Страница игры для класса
@app.route('/class/<int:class_id>')
@admin_required
def class_game(class_id):
    class_obj = db.get_or_404(Class, class_id)
    valera_prizes = Prize.query.filter_by(prize_type='valera').all()
    students_prizes = Prize.query.filter_by(prize_type='students').all()
    shop_items = ShopItem.query.order_by(ShopItem.price).all()
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

# Панель администратора - призы
@app.route('/admin/prizes')
@admin_required
def admin_prizes():
    valera_prizes = Prize.query.filter_by(prize_type='valera').all()
    students_prizes = Prize.query.filter_by(prize_type='students').all()
    shop_items = ShopItem.query.order_by(ShopItem.price).all()
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
    data = request.json
    new_item = ShopItem(
        name=data['name'],
        price=data['price']
    )
    db.session.add(new_item)
    db.session.commit()
    return jsonify({'success': True, 'item': new_item.to_dict()})

@app.route('/api/shop-items/<int:item_id>', methods=['PUT'])
@admin_required
def update_shop_item(item_id):
    item = db.get_or_404(ShopItem, item_id)
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
    boss = db.get_or_404(Boss, boss_id)
    tasks = BossTask.query.filter_by(boss_id=boss_id).all()
    return jsonify({'success': True, 'tasks': [task.to_dict() for task in tasks]})

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
    
    if not active_boss:
        return render_template('raid_boss.html', boss=None, classes=[])
    
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
    
    return render_template('raid_boss.html', 
                         boss=active_boss, 
                         classes=classes,
                         class_damage=class_damage)

# API для получения случайной доступной задачи босса
@app.route('/api/raid-boss/task', methods=['GET'])
def get_random_boss_task():
    active_boss = Boss.query.filter_by(is_active=True).first()
    if not active_boss:
        return jsonify({'success': False, 'error': 'Нет активного босса'}), 404
    
    # Получаем все задачи, которые еще не решены
    all_tasks = BossTask.query.filter_by(boss_id=active_boss.id).all()
    available_tasks = [task for task in all_tasks if not task.is_solved()]
    
    if not available_tasks:
        return jsonify({
            'success': True, 
            'boss_defeated': True,
            'message': 'Босс побежден! Все задачи решены.'
        })
    
    # Выбираем случайную задачу
    random_task = random.choice(available_tasks)
    return jsonify({
        'success': True,
        'task': random_task.to_dict(),
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
                    'drop_id': drop_reward.drop_id
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
    
    total_health = sum(task.points for task in boss.tasks)
    current_health = boss.get_current_health()
    
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
