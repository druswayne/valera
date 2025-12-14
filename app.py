from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from functools import wraps
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///valera.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

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
    return User.query.get(int(user_id))

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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'prize_type': self.prize_type
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

# Создание таблиц
with app.app_context():
    db.create_all()
    
    # Создание администратора по умолчанию (если его нет)
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        admin = User(username='admin', is_admin=True)
        admin.set_password('admin')  # Пароль по умолчанию - измените его!
        db.session.add(admin)
        db.session.commit()

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
def class_game(class_id):
    class_obj = Class.query.get_or_404(class_id)
    valera_prizes = Prize.query.filter_by(prize_type='valera').all()
    students_prizes = Prize.query.filter_by(prize_type='students').all()
    shop_items = ShopItem.query.order_by(ShopItem.price).all()
    return render_template('game.html', 
                         class_obj=class_obj,
                         valera_prizes=[p.name for p in valera_prizes],
                         students_prizes=[p.name for p in students_prizes],
                         shop_items=shop_items)

# API для получения баланса
@app.route('/api/class/<int:class_id>/balance')
def get_balance(class_id):
    class_obj = Class.query.get_or_404(class_id)
    return jsonify({
        'students_balance': class_obj.students_balance,
        'valera_balance': class_obj.valera_balance
    })

# API для обновления баланса
@app.route('/api/class/<int:class_id>/balance', methods=['POST'])
def update_balance(class_id):
    class_obj = Class.query.get_or_404(class_id)
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
    class_obj = Class.query.get_or_404(class_id)
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
    class_obj = Class.query.get_or_404(class_id)
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
        prize_type=data['prize_type']
    )
    db.session.add(new_prize)
    db.session.commit()
    return jsonify({'success': True, 'prize': new_prize.to_dict()})

@app.route('/api/prizes/<int:prize_id>', methods=['PUT'])
@admin_required
def update_prize(prize_id):
    prize = Prize.query.get_or_404(prize_id)
    data = request.json
    
    if 'name' in data:
        prize.name = data['name']
    if 'prize_type' in data:
        prize.prize_type = data['prize_type']
    
    db.session.commit()
    return jsonify({'success': True, 'prize': prize.to_dict()})

@app.route('/api/prizes/<int:prize_id>', methods=['DELETE'])
@admin_required
def delete_prize(prize_id):
    prize = Prize.query.get_or_404(prize_id)
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
    item = ShopItem.query.get_or_404(item_id)
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
    item = ShopItem.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    return jsonify({'success': True})


