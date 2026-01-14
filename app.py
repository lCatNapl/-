"""
Узнавайкин - Игровой каталог с подпиской
Flask приложение с аутентификацией, подписками и каталогом игр
"""

import os
import secrets
import time
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

# Инициализация
app = Flask(__name__)
app.config['SECRET_KEY'] = 'uznavaykin-secret-key-2026-change-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///uznavaykin.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Базы данных и безопасность
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# ========================================
# МОДЕЛИ БАЗЫ ДАННЫХ
# ========================================

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    subscription_type = db.Column(db.String(20), default='start')
    subscription_status = db.Column(db.String(20), default='active')
    subscription_end = db.Column(db.DateTime)
    telegram_link = db.Column(db.String(100))
    profile_color = db.Column(db.String(7), default='#4A90E2')
    premium_slots_used = db.Column(db.Integer, default=0)
    vip_slots_used = db.Column(db.Integer, default=0)
    avatar = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def get_description_level(self):
        return self.subscription_type
    
    def can_use_premium(self):
        return self.subscription_type == 'premium' or self.premium_slots_used < 1
    
    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
    
    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

class Game(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description_start = db.Column(db.Text)
    description_vip = db.Column(db.Text)
    description_premium = db.Column(db.Text)
    image_start = db.Column(db.String(300))
    image_vip = db.Column(db.String(300))
    image_premium_3d = db.Column(db.String(300))
    category = db.Column(db.String(50), default='action')
    rating = db.Column(db.Float, default=0.0)
    is_featured = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def get_description(self, user_type='start'):
        if user_type == 'premium' and self.description_premium:
            return self.description_premium
        elif user_type in ['vip', 'premium'] and self.description_vip:
            return self.description_vip
        return self.description_start or "Описание игры скоро появится..."
    
    def get_image(self, user_type='start'):
        if user_type == 'premium' and self.image_premium_3d:
            return self.image_premium_3d
        elif user_type in ['vip', 'premium'] and self.image_vip:
            return self.image_vip
        return self.image_start or '/static/images/default-game.jpg'

class SubscriptionPlan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    price = db.Column(db.Integer, nullable=False)  # рубли
    duration_days = db.Column(db.Integer, default=30)
    features = db.Column(db.Text)
    is_lifetime_bonus = db.Column(db.Boolean, default=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ========================================
# МАРШРУТЫ - ОСНОВНЫЕ СТРАНИЦЫ
# ========================================

@app.route('/')
def index():
    """Главная страница с каталогом игр"""
    games = Game.query.order_by(Game.is_featured.desc(), Game.rating.desc()).limit(12).all()
    return render_template('index.html', games=games)

@app.route('/catalog')
@login_required
def catalog():
    """Полный каталог игр с фильтрами"""
    page = request.args.get('page', 1, type=int)
    category = request.args.get('category', 'all')
    
    query = Game.query
    if category != 'all':
        query = query.filter(Game.category == category)
    
    games = query.order_by(Game.rating.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    return render_template('catalog.html', games=games)

@app.route('/game/<int:game_id>')
@login_required
def game_detail(game_id):
    """Детальная страница игры"""
    game = Game.query.get_or_404(game_id)
    return render_template('game_detail.html', game=game)

# ========================================
# АУТЕНТИФИКАЦИЯ
# ========================================

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Регистрация нового пользователя"""
    if current_user.is_authenticated:
        return redirect(url_for('profile'))
    
    if request.method == 'POST':
        username = request.form['username'].strip()
        email = request.form['email'].strip().lower()
        password = request.form['password']
        
        if User.query.filter_by(username=username).first():
            flash('Имя пользователя уже занято', 'error')
            return render_template('register.html')
        
        if User.query.filter_by(email=email).first():
            flash('Email уже зарегистрирован', 'error')
            return render_template('register.html')
        
        if len(password) < 6:
            flash('Пароль должен содержать минимум 6 символов', 'error')
            return render_template('register.html')
        
        user = User(
            username=username,
            email=email
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        flash('Регистрация успешна! Теперь войдите в аккаунт.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Вход в аккаунт"""
    if current_user.is_authenticated:
        return redirect(url_for('profile'))
    
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        password = request.form['password']
        
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            flash('Добро пожаловать обратно!', 'success')
            return redirect(url_for('profile'))
        else:
            flash('Неверный email или пароль', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    """Выход из аккаунта"""
    logout_user()
    flash('Вы вышли из аккаунта', 'info')
    return redirect(url_for('index'))

# ========================================
# ПРОФИЛЬ И ПОДПИСКИ
# ========================================

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """Личный кабинет"""
    if request.method == 'POST':
        current_user.username = request.form.get('username', current_user.username)
        current_user.email = request.form.get('email', current_user.email).lower()
        current_user.profile_color = request.form.get('profile_color', current_user.profile_color)
        current_user.telegram_link = request.form.get('telegram_link', current_user.telegram_link)
        
        if 'avatar' in request.files:
            file = request.files['avatar']
            if file.filename:
                filename = secure_filename(file.filename)
                avatar_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{current_user.id}_{filename}")
                file.save(avatar_path)
                current_user.avatar = f"/uploads/{current_user.id}_{filename}"
        
        db.session.commit()
        flash('Профиль обновлен!', 'success')
    
    plans = SubscriptionPlan.query.all()
    return render_template('profile.html', plans=plans)

@app.route('/subscribe/<plan_name>')
@login_required
def subscribe(plan_name):
    """Переход на оплату подписки"""
    plan = SubscriptionPlan.query.filter_by(name=plan_name).first_or_404()
    
    # Проверка бонусных слотов
    if plan_name == 'premium' and current_user.premium_slots_used >= 1:
        flash('Бонусный Premium слот уже использован', 'error')
        return redirect(url_for('profile'))
    
    if plan_name == 'vip' and current_user.vip_slots_used >= 3:
        flash('Все бонусные VIP слоты использованы', 'error')
        return redirect(url_for('profile'))
    
    # Тестовый режим - сразу активируем подписку
    current_user.subscription_type = plan_name
    current_user.subscription_status = 'active'
    
    if plan.is_lifetime_bonus:
        current_user.subscription_end = None  # Навсегда
        if plan_name == 'premium':
            current_user.premium_slots_used += 1
        elif plan_name == 'vip':
            current_user.vip_slots_used += 1
    else:
        current_user.subscription_end = datetime.utcnow() + timedelta(days=plan.duration_days)
    
    db.session.commit()
    flash(f'Подписка {plan_name.upper()} активирована!', 'success')
    return redirect(url_for('profile'))

@app.route('/link-telegram')
@login_required
def link_telegram():
    """Генерация ссылки для Telegram"""
    token = secrets.token_urlsafe(16)
    current_user.telegram_token = token
    db.session.commit()
    
    bot_link = f"https://t.me/uznavaykin_bot?start={token}"
    return jsonify({'telegram_link': bot_link})

# ========================================
# АДМИН ПАНЕЛЬ (простая)
# ========================================

@app.route('/admin/games', methods=['GET', 'POST'])
@login_required
def admin_games():
    """Добавление игр (только для админа)"""
    if current_user.username != 'admin':  # Простая проверка
        flash('Доступ запрещен', 'error')
        return redirect(url_for('catalog'))
    
    if request.method == 'POST':
        game = Game(
            title=request.form['title'],
            description_start=request.form['description_start'],
            description_vip=request.form.get('description_vip', ''),
            description_premium=request.form.get('description_premium', ''),
            category=request.form.get('category', 'action'),
            image_start=request.form.get('image_start'),
            image_vip=request.form.get('image_vip'),
            image_premium_3d=request.form.get('image_premium_3d'),
            rating=float(request.form.get('rating', 0)),
            is_featured=bool(request.form.get('featured'))
        )
        db.session.add(game)
        db.session.commit()
        flash('Игра добавлена!', 'success')
    
    games = Game.query.all()
    return render_template('admin_games.html', games=games)

# ========================================
# API ЭНДПОИНТЫ
# ========================================

@app.route('/api/games')
def api_games():
    """JSON API для каталога"""
    games = Game.query.limit(50).all()
    return jsonify([{
        'id': g.id,
        'title': g.title,
        'category': g.category,
        'rating': g.rating,
        'image': g.get_image(current_user.subscription_type if current_user.is_authenticated else 'start')
    } for g in games])

# ========================================
# ИНИЦИАЛИЗАЦИЯ БАЗЫ
# ========================================

def init_db():
    """Создание начальных данных"""
    with app.app_context():
        db.create_all()
        
        # Создаем планы подписок если их нет
        plans_data = [
            ('start', 0, 999999, 'Базовый доступ'),
            ('vip', 100, 30, 'Новые темы, изображения, статус VIP'),
            ('premium', 200, 30, '3D изображения, лучшие темы, статус Premium, 1 Premium + 3 VIP навсегда')
        ]
        
        for name, price, days, features in plans_data:
            if not SubscriptionPlan.query.filter_by(name=name).first():
                plan = SubscriptionPlan(name=name, price=price, duration_days=days, features=features)
                if name == 'premium':
                    plan.is_lifetime_bonus = True
                db.session.add(plan)
        
        # Создаем админа Назар
        if not User.query.filter_by(username='Назар').first():
            admin = User(username='Назар', email='nazartrahov1@gmail.com')
            admin.set_password('120187')
            admin.subscription_type = 'premium'  # Админ сразу Premium
            db.session.add(admin)
            print("✅ Админ 'Назар' создан с паролем '120187'")
        
        db.session.commit()
        print("✅ База данных инициализирована!")

if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    init_db()
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
