from flask import Flask, request, render_template_string
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
from datetime import datetime, timedelta
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'uznavaykin-super-2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# МОДЕЛИ
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True)
    password = db.Column(db.String(120))
    role = db.Column(db.String(20), default='start')
    is_admin = db.Column(db.Boolean, default=False)

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def get_online_stats():
    return {'total': 2, 'start': 1, 'vip': 0, 'premium': 1, 'admin': 0}

@app.route('/')
def index():
    return '''
    <!DOCTYPE html>
    <html>
    <head><title>Узнавайкин</title><meta charset="utf-8"></head>
    <body style="font-family:Arial;">
        <h1>🏠 Узнавайкин</h1>
        {% if current_user.is_authenticated %}
            <p>👤 {{current_user.username}} ({{current_user.role|upper}}) 
            | <a href="/profile">Профиль</a> | <a href="/logout">Выход</a></p>
            {% if current_user.role != "premium" %}
            <p><a href="/buy/vip" style="color:blue">[VIP 100₽]</a> 
            | <a href="/buy/premium" style="color:gold">[PREMIUM 200₽]</a></p>
            {% endif %}
        {% else %}
            <p><a href="/login">🔐 Войти</a> | <a href="/register">📝 Регистрация</a></p>
        {% endif %}
        <p>👥 Онлайн: {{stats.total}} (S:{{stats.start}} V:{{stats.vip}} P:{{stats.premium}} A:{{stats.admin}})</p>
        <hr>
        <p><a href="/catalog">📁 Каталог</a> | <a href="/community">💬 TG</a></p>
        {% if current_user.is_admin %}<p><a href="/admin">🔧 Админ</a></p>{% endif %}
    </body>
    </html>
    '''.format(stats=get_online_stats())

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if not User.query.filter_by(username=username).first():
            user = User(username=username)
            user.password = bcrypt.generate_password_hash(password).decode('utf-8')
            db.session.add(user)
            db.session.commit()
            return '<h2>✅ Зарегистрирован! <a href="/login">Войти</a></h2>'
    return '''
    <h2>📝 Регистрация</h2>
    <form method="post">
        Логин: <input name="username" required><br><br>
        Пароль: <input name="password" type="password" required><br><br>
        <button>Зарегистрироваться</button>
    </form>
    <p><a href="/login">Уже есть аккаунт?</a></p>
    '''

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            return '<h2>✅ Вошёл! <a href="/">На главную</a></h2>'
        return '<h2>❌ Неверный логин/пароль <a href="/login">Повторить</a></h2>'
    return '''
    <h2>🔐 Вход</h2>
    <form method="post">
        Логин: <input name="username" required><br><br>
        Пароль: <input name="password" type="password" required><br><br>
        <button>Войти</button>
    </form>
    <p><a href="/register">Нет аккаунта?</a></p>
    '''

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return '<h2>👋 Выход <a href="/">Главная</a></h2>'

@app.route('/buy/<role>')
@login_required
def buy_role(role):
    current_user.role = role
    db.session.commit()
    return f'<h2>✅ Купил {role.upper()}! <a href="/">Главная</a></h2>'

@app.route('/profile/')
@login_required
def profile():
    stats = get_online_stats()
    return f'''
    <h1>👤 {current_user.username}</h1>
    <p>Роль: {current_user.role.upper()}</p>
    <p>Онлайн: {stats["total"]}</p>
    <a href="/">🏠 Главная</a>
    '''

@app.route('/catalog')
def catalog():
    cats = Category.query.all()
    html = '<h1>📁 Каталог</h1><a href="/">🏠</a><br>'
    for cat in cats:
        html += f'<div style="margin:10px;border:1px solid #ccc;padding:10px;">📁 {cat.name}</div>'
    return html

@app.route('/community')
def community():
    return '''
    <h1>💬 Сообщество</h1>
    <a href="https://t.me/ssylkanatelegramkanalyznaikin">Telegram канал</a>
    <br><a href="/">🏠 Главная</a>
    '''

@app.route('/admin', methods=['GET', 'POST'])
@login_required
def admin():
    if not current_user.is_admin:
        return '<h2>❌ Только админы!</h2><a href="/">Главная</a>'
    if request.method == 'POST':
        name = request.form['name']
        cat = Category(name=name)
        db.session.add(cat)
        db.session.commit()
        return '<h2>✅ Категория добавлена! <a href="/admin">Продолжить</a></h2>'
    return '''
    <h1>🔧 Админ панель</h1>
    <a href="/">🏠</a>
    <h3>Добавить категорию:</h3>
    <form method="post">
        <input name="name" placeholder="Название категории">
        <button>Добавить</button>
    </form>
    '''

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        
        # Создаём админов
        for user_data in [
            {'username': 'CatNap', 'password': '120187', 'is_admin': True},
            {'username': 'Назар', 'password': '120187', 'is_admin': True}
        ]:
            user = User.query.filter_by(username=user_data['username']).first()
            if not user:
                user = User(**user_data)
                user.password = bcrypt.generate_password_hash(user_data['password']).decode('utf-8')
                db.session.add(user)
        db.session.commit()
        
        # Создаём категории
        for name in ['Minecraft', 'World of Tanks', 'Блоки', 'Танки']:
            if not Category.query.filter_by(name=name).first():
                db.session.add(Category(name=name))
        db.session.commit()
    
    app.run(debug=False)
