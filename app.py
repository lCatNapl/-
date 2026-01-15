import os
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, render_template_string
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'uznavaykin-2026-super')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///site.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# МОДЕЛИ
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), default='start')  # start, vip, premium, admin
    is_admin = db.Column(db.Boolean, default=False)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    views_count = db.Column(db.Integer, default=0)

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('category.id'))

class Info(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    views = db.Column(db.Integer, default=0)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def get_online_stats():
    cutoff = datetime.utcnow() - timedelta(minutes=5)
    online_users = User.query.filter(User.last_seen > cutoff).all()
    counts = {'start': 0, 'vip': 0, 'premium': 0, 'admin': 0, 'total': 0}
    for user in online_users:
        counts['total'] += 1
        if user.is_admin:
            counts['admin'] += 1
        elif user.role == 'premium':
            counts['premium'] += 1
        elif user.role == 'vip':
            counts['vip'] += 1
        else:
            counts['start'] += 1
    return counts

@app.before_request
def update_last_seen():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.utcnow()
        try:
            db.session.commit()
        except:
            pass

# ✅ ФИКС 3,4: ЛОГИН/РЕГИСТРАЦИЯ ПО USERNAME
@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        if User.query.filter_by(email=email).first() or User.query.filter_by(username=username).first():
            flash('❌ Пользователь существует!')
            return redirect(url_for('register'))
        user = User(username=username, email=email, role='start')
        user.password = bcrypt.generate_password_hash(password).decode('utf-8')
        db.session.add(user)
        db.session.commit()
        flash('✅ Зарегистрирован!')
        return redirect(url_for('login'))
    return render_template_string('''
    <!DOCTYPE html>
    <html><head><title>Регистрация</title></head><body>
    <h2>👤 Регистрация</h2>
    <form method="post">
        Логин: <input name="username" required><br><br>
        Email: <input name="email" type="email" required><br><br>
        Пароль: <input name="password" type="password" required><br><br>
        <button>Зарегистрироваться</button> | <a href="/login">Войти</a>
    </form>
    </body></html>
    ''')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            flash('✅ Вход выполнен!')
            return redirect(url_for('index'))
        flash('❌ Неверный логин/пароль!')
    return render_template_string('''
    <!DOCTYPE html>
    <html><head><title>Вход</title></head><body>
    <h2>🔐 Вход</h2>
    <form method="post">
        Логин: <input name="username" required><br><br>
        Пароль: <input name="password" type="password" required><br><br>
        <button>Войти</button> | <a href="/register">Регистрация</a>
    </form>
    <hr>
    <p><b>Админы:</b><br>CatNap<br>Назар</p>
    </body></html>
    ''')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('👋 Выход выполнен!')
    return redirect(url_for('index'))

# ✅ ФИКС 2: Админы = PREMIUM
@app.route('/buy/<role>')
@login_required
def buy_role(role):
    prices = {'vip': 100, 'premium': 200}
    if role in prices and current_user.role != 'admin':  # Админы не покупают
        current_user.role = role
        db.session.commit()
        flash(f'✅ Куплено {role.upper()} за {prices[role]}₽!')
    elif current_user.is_admin:
        current_user.role = 'premium'  # ФИКС 2
        db.session.commit()
        flash('✅ Админ = PREMIUM!')
    return redirect(url_for('index'))

@app.route('/')
def index():
    stats = get_online_stats()
    return render_template_string('''
    <!DOCTYPE html>
    <html><head><title>Узнавайкин</title></head><body>
    <h1>🏠 Главная</h1>
    {% if current_user.is_authenticated %}
        <p>👤 {{current_user.username}} ({{current_user.role|upper}}) | 
        <a href="/profile/">Профиль</a> | <a href="/logout">Выход</a></p>
        <p><a href="/buy/vip">[VIP 100₽]</a> | <a href="/buy/premium">[PREMIUM 200₽]</a></p>
    {% else %}
        <p><a href="/login">Войти</a> | <a href="/register">Регистрация</a></p>
    {% endif %}
    <p>👥 Онлайн: {{stats.total}} (S:{{stats.start}} V:{{stats.vip}} P:{{stats.premium}} A:{{stats.admin}})</p>
    <p><a href="/catalog/">📁 Каталог</a> | <a href="/community/">💬 Сообщество</a></p>
    {% if current_user.is_admin %}
        <p><a href="/admin/">🔧 Админ панель</a></p>
    {% endif %}
    </body></html>
    ''')

@app.route('/catalog/')
def catalog():
    # ✅ ФИКС 1: Рабочий каталог
    categories = Category.query.filter_by(parent_id=None).all()
    cat_html = ""
    for cat in categories:
        cat_html += f"<div style='margin-left:20px;border:1px solid gray;padding:10px;'><b>📁 {cat.name}</b></div>"
        subcats = Category.query.filter_by(parent_id=cat.id).all()
        for subcat in subcats:
            cat_html += f"<div style='margin-left:40px;'>-- {subcat.name}</div>"
    return render_template_string(f'''
    <!DOCTYPE html>
    <html><head><title>Каталог</title></head><body>
    <h1>📁 Каталог</h1>
    <a href="/">🏠</a>
    <div>{cat_html}</div>
    </body></html>
    ''')

@app.route('/profile/')
@login_required
def profile():
    stats = get_online_stats()
    return render_template_string(f'''
    <!DOCTYPE html>
    <html><head><title>Профиль</title></head><body>
    <h1>👤 {{current_user.username}}</h1>
    <p>Роль: {{current_user.role|upper}}</p>
    <p>Просмотров: {{current_user.views_count}}</p>
    <p>Онлайн: {{stats.total}}</p>
    <a href="/">🏠</a>
    </body></html>
    ''')

@app.route('/community/')
def community():
    return render_template_string('''
    <!DOCTYPE html>
    <html><head><title>Сообщество</title></head><body>
    <h1>💬 Сообщество</h1>
    <a href="https://t.me/ssylkanatelegramkanalyznaikin" target="_blank">🚀 Telegram</a>
    <p><a href="/">🏠</a></p>
    </body></html>
    ''')

@app.route('/admin/', methods=['GET', 'POST'])
@login_required
def admin_panel():
    if not current_user.is_admin:
        flash('❌ Только для админов!')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        if 'add_category' in request.form:
            new_cat = Category(name=request.form['cat_name'])
            if request.form.get('parent_id'):
                new_cat.parent_id = int(request.form['parent_id'])
            db.session.add(new_cat)
            db.session.commit()
            flash('✅ Категория добавлена!')
        elif 'add_info' in request.form:
            new_info = Info(
                title=request.form['title'],
                description=request.form['description'],
                category_id=1  # Первая категория
            )
            db.session.add(new_info)
            db.session.commit()
            flash('✅ Информация добавлена!')
    
    categories = Category.query.all()
    return render_template_string('''
    <!DOCTYPE html>
    <html><head><title>Админ</title></head><body>
    <h1>🔧 Админ панель</h1>
    <a href="/">🏠</a>
    
    <h3>➕ Категория</h3>
    <form method="POST">
        Название: <input name="cat_name" required>
        <button name="add_category">Добавить</button>
    </form>
    
    <h3>Категории:</h3>
    {% for cat in categories %}
    <div>{{cat.name}} (ID: {{cat.id}})</div>
    {% endfor %}
    </body></html>
    ''', categories=categories)

# Инициализация БД
with app.app_context():
    db.create_all()
    
    # ✅ ФИКС 2: Админы = PREMIUM
    admins = [
        {'username': 'CatNap', 'email': 'nazartrahov10@gmail.com', 'password': '120187', 'role': 'premium', 'is_admin': True},
        {'username': 'Назар', 'email': 'nazartrahov1@gmail.com', 'password': '120187', 'role': 'premium', 'is_admin': True},
    ]
    
    for admin_data in admins:
        admin = User.query.filter_by(username=admin_data['username']).first()
        if not admin:
            admin = User(**admin_data)
            admin.password = bcrypt.generate_password_hash(admin_data['password']).decode('utf-8')
            db.session.add(admin)
        else:
            admin.role = 'premium'  # ФИКС для существующих
            admin.is_admin = True
        db.session.commit()
    
    if not Category.query.first():
        Category(name='Minecraft').save()
        Category(name='World of Tanks').save()

if __name__ == '__main__':
    app.run(debug=True)

