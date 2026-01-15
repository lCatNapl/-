import os
from datetime import datetime, timedelta
from flask import Flask, render_template_string, request, redirect, url_for, flash
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
    role = db.Column(db.String(20), default='start')
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

# РЕГИСТРАЦИЯ
@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        if User.query.filter((User.username == username) | (User.email == email)).first():
            return render_template_string('''<h2>❌ Пользователь существует!</h2><a href="/register">Повторить</a>''')
        user = User(username=username, email=email, role='start')
        user.password = bcrypt.generate_password_hash(password).decode('utf-8')
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template_string('''
    <h2>👤 Регистрация</h2>
    <form method="post">
        Логин: <input name="username" required><br><br>
        Email: <input name="email" type="email" required><br><br>
        Пароль: <input name="password" type="password" required><br><br>
        <button>Зарегистрироваться</button>
    </form><a href="/login">Войти</a>
    ''')

# ЛОГИН
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
            return redirect(url_for('index'))
        return render_template_string('''<h2>❌ Неверный логин/пароль</h2><a href="/login">Повторить</a>''')
    return render_template_string('''
    <h2>🔐 Вход</h2>
    <form method="post">
        Логин: <input name="username" required><br><br>
        Пароль: <input name="password" type="password" required><br><br>
        <button>Войти</button>
    </form>
    <a href="/register">Регистрация</a>
    ''')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

# ПОКУПКИ
@app.route('/buy/<role>')
@login_required
def buy_role(role):
    if current_user.is_admin:
        current_user.role = 'premium'
    elif role == 'vip':
        current_user.role = 'vip'
    elif role == 'premium':
        current_user.role = 'premium'
    db.session.commit()
    return redirect(url_for('index'))

# ГЛАВНАЯ
@app.route('/')
def index():
    stats = get_online_stats()
    return render_template_string('''
    <h1>🏠 Узнавайкин</h1>
    {% if current_user.is_authenticated %}
        <p>👤 {{current_user.username}} ({{current_user.role|upper}}) 
        <a href="/profile/">[Профиль]</a> <a href="/logout">[Выход]</a></p>
        {% if current_user.role != "premium" %}
        <p><a href="/buy/vip">[VIP]</a> <a href="/buy/premium">[PREMIUM]</a></p>
        {% endif %}
    {% else %}
        <p><a href="/login">[Войти]</a> <a href="/register">[Регистрация]</a></p>
    {% endif %}
    <p>👥 Онлайн {{stats.total}}: S{{stats.start}} V{{stats.vip}} P{{stats.premium}} A{{stats.admin}}</p>
    <p><a href="/catalog/">📁 Каталог</a> | <a href="/community/">💬 TG</a></p>
    {% if current_user.is_admin %}<p><a href="/admin/">🔧 Админ</a></p>{% endif %}
    ''')

# КАТАЛОГ
@app.route('/catalog/')
def catalog():
    categories = Category.query.filter_by(parent_id=None).all()
    html = "<h1>📁 Каталог</h1><a href='/'>🏠</a><br>"
    for cat in categories:
        html += f"<b>📁 {cat.name}</b><br>"
        subcats = Category.query.filter_by(parent_id=cat.id).all()
        for sub in subcats:
            html += f"  └─ {sub.name}<br>"
    return html

# ПРОФИЛЬ
@app.route('/profile/')
@login_required
def profile():
    stats = get_online_stats()
    return render_template_string(f'''
    <h1>👤 {current_user.username}</h1>
    <p>Роль: {current_user.role.upper()}</p>
    <p>Просмотров: {current_user.views_count}</p>
    <p>Онлайн: {stats.total}</p>
    <a href="/">🏠</a>
    ''')

@app.route('/community/')
def community():
    return '''
    <h1>💬 Сообщество</h1>
    <a href="https://t.me/ssylkanatelegramkanalyznaikin">Telegram</a>
    <br><a href="/">🏠</a>
    '''

@app.route('/admin/', methods=['GET', 'POST'])
@login_required
def admin_panel():
    if not current_user.is_admin:
        return redirect(url_for('index'))
    if request.method == 'POST':
        if request.form.get('cat_name'):
            cat = Category(name=request.form['cat_name'])
            db.session.add(cat)
            db.session.commit()
        elif request.form.get('title'):
            info = Info(title=request.form['title'], category_id=1)
            db.session.add(info)
            db.session.commit()
    categories = Category.query.all()
    return '''
    <h1>🔧 Админ</h1><a href="/">🏠</a>
    <h3>Категория:</h3><form method=post>
    <input name=cat_name> <button>Добавить</button></form>
    <h3>Категории:</h3>
    ''' + ''.join([f'<div>{c.name} (ID:{c.id})</div>' for c in categories])

# ✅ ФИКС ИНИЦИАЛИЗАЦИЯ БД
with app.app_context():
    db.create_all()
    
    # Админы PREMIUM
    admins = [
        {'username': 'CatNap', 'email': 'catnap@uznavaykin.ru', 'password': '120187', 'role': 'premium', 'is_admin': True},
        {'username': 'Назар', 'email': 'nazartrahov1@gmail.com', 'password': '120187', 'role': 'premium', 'is_admin': True}
    ]
    
    for admin_data in admins:
        admin = User.query.filter_by(username=admin_data['username']).first()
        if not admin:
            admin = User(**admin_data)
            admin.password = bcrypt.generate_password_hash(admin_data['password']).decode('utf-8')
            db.session.add(admin)
        else:
            admin.role = 'premium'
            admin.is_admin = True
        db.session.commit()
    
    # ✅ ФИКС: Правильное создание категорий
    if not Category.query.first():
        minecraft = Category(name='Minecraft')
        wot = Category(name='World of Tanks')
        db.session.add(minecraft)
        db.session.add(wot)
        db.session.commit()

if __name__ == '__main__':
    app.run(debug=True)
