from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
from functools import wraps
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.pool import ThreadPoolExecutor
import random
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///valera.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads/tasks'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

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

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'students_balance': self.students_balance,
            'valera_balance': self.valera_balance,
            'total_balance': self.students_balance + self.valera_balance
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
    solved_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'task_id': self.task_id,
            'user_name': self.user_name,
            'answer': self.answer,
            'is_correct': self.is_correct,
            'solved_at': self.solved_at.isoformat() if self.solved_at else None
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
            unsolved_tasks = [task for task in all_tasks if not task.is_solved()]
            
            if not unsolved_tasks:
                print("Нет нерешенных задач для обновления")
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

# Функция для получения следующего воскресенья в 12:00
def get_next_sunday_12pm():
    """Возвращает datetime следующего воскресенья в 12:00"""
    now = datetime.now()
    # Воскресенье = 6 (0 = понедельник, 6 = воскресенье)
    days_until_sunday = (6 - now.weekday()) % 7
    
    # Если сегодня воскресенье
    if days_until_sunday == 0:
        # Проверяем, прошло ли уже 12:00
        target_time = now.replace(hour=12, minute=0, second=0, microsecond=0)
        if now >= target_time:
            # Если уже прошло 12:00, берем следующее воскресенье
            days_until_sunday = 7
    
    next_sunday = now.replace(hour=12, minute=0, second=0, microsecond=0) + timedelta(days=days_until_sunday)
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
        # Добавляем задачу на каждое воскресенье в 12:00
        scheduler.add_job(
            update_weekly_task,
            'cron',
            day_of_week='sun',
            hour=12,
            minute=0,
            id='update_weekly_task',
            replace_existing=True
        )
        print("Планировщик задач запущен. Задача недели будет обновляться каждое воскресенье в 12:00")

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
    classes = Class.query.order_by((Class.students_balance + Class.valera_balance).desc()).all()
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
    
    # Вычисляем следующее воскресенье в 12:00 на основе времени последнего обновления задачи
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
    
    # Вычисляем следующее воскресенье в 12:00
    # Воскресенье = 6 (0 = понедельник, 6 = воскресенье)
    days_until_sunday = (6 - task_update_time.weekday()) % 7
    
    if days_until_sunday == 0:
        # Если обновление было в воскресенье, проверяем время
        target_time = task_update_time.replace(hour=12, minute=0, second=0, microsecond=0)
        if task_update_time >= target_time:
            # Если обновление было в 12:00 или после, берем следующее воскресенье
            days_until_sunday = 7
    
    next_sunday = task_update_time.replace(hour=12, minute=0, second=0, microsecond=0) + timedelta(days=days_until_sunday)
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
        is_correct=is_correct
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
    next_sunday = get_next_sunday_12pm()
    now = datetime.now()
    time_until = next_sunday - now
    
    return jsonify({
        'next_update': next_sunday.isoformat(),
        'seconds_until': int(time_until.total_seconds()),
        'days': time_until.days,
        'hours': time_until.seconds // 3600,
        'minutes': (time_until.seconds % 3600) // 60
    })

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
