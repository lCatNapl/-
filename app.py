import os
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash
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
    infos = db.relationship('Info', backref='category', lazy=True)

class Info(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    views = db.Column(db.Integer, default=0)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ФИКС 2: Реальная онлайн статистика (только АКТИВНЫЕ за 5 мин)
def get_online_stats():
    cutoff = datetime.utcnow() - timedelta(minutes=5)
    online_users = User.query.filter(User.last_seen > cutoff).all()
    
    counts = {'start': 0, 'vip': 0, 'premium': 0, 'admin': 0, 'total': len(online_users)}
    for user in online_users:
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
        db.session.commit()

# 🆕 РЕГИСТРАЦИЯ + ЛОГИН (ФИКС 1)
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        if not User.query.filter_by(email=email).first():
            user = User(username=username, email=email, role='start')
            user.password = bcrypt.generate_password_hash(password).decode('utf-8')
            db.session.add(user)
            db.session.commit()
            flash('✅ Зарегистрирован! Войди.')
            return redirect(url_for('login'))
        flash('❌ Email занят!')
    return '''
    <form method="post">
        <h2>Регистрация</h2>
        Имя: <input name="username" required><br>
        Email: <input name="email" type="email" required><br>  
        Пароль: <input name="password" type="password" required><br>
        <button>Зарегистрироваться</button>
        <a href="/login">Войти</a>
    </form>
    '''

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        
        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            flash('✅ Вошёл!')
            return redirect(url_for('index'))
        flash('❌ Неверный email/пароль!')
    
    return '''
    <form method="post">
        <h2>Вход</h2>
        Email: <input name="email" type="email" required><br>
        Пароль: <input name="password" type="password" required><br>
        <button>Войти</button>
        <a href="/register">Регистрация</a><br>
        <b>Админы:</b> CatNap / 120187 | Назар / 120187
    </form>
    '''

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

# 🆕 ФИКС 3: ПОКУПКИ VIP/PREMIUM
@app.route('/buy/<role>')
@login_required
def buy_role(role):
    prices = {'vip': 100, 'premium': 200}
    if role in prices:
        current_user.role = role
        db.session.commit()
        flash(f'✅ Купил {role.upper()} за {prices[role]}₽!')
    return redirect(url_for('index'))

# ОСНОВНЫЕ СТРАНИЦЫ
@app.route('/')
def index():
    popular = Info.query.order_by(Info.views.desc()).limit(6).all()
    stats = get_online_stats()
    return render_template('index.html', popular=popular, stats=stats)

@app.route('/catalog/')
def catalog():
    root_cats = Category.query.filter_by(parent_id=None).all()
    return render_template('catalog.html', categories=root_cats)

@app.route('/info/<int:info_id>')
def info_detail(info_id):
    info = Info.query.get_or_404(info_id)
    info.views += 1
    if current_user.is_authenticated:
        current_user.views_count += 1
        db.session.commit()
    return render_template('info.html', info=info)

@app.route('/profile/')
@login_required
def profile():
    stats = get_online_stats()
    return render_template('profile.html', stats=stats)

@app.route('/admin/', methods=['GET', 'POST'])
@login_required
def admin_panel():
    if not current_user.is_admin:
        flash('❌ Только админы!')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        if 'add_category' in request.form:
            cat = Category(name=request.form['cat_name'])
            if request.form.get('parent_id'):
                cat.parent_id = int(request.form['parent_id'])
            db.session.add(cat)
            flash('✅ Категория!')
        elif 'add_info' in request.form:
            info = Info(
                title=request.form['title'],
                description=request.form['description'],
                category_id=int(request.form['category_id'])
            )
            db.session.add(info)
            flash('✅ Инфо!')
        db.session.commit()
    
    categories = Category.query.filter_by(parent_id=None).all()
    infos = Info.query.all()
    return render_template('admin.html', categories=categories, infos=infos)

# ИНИЦИАЛИЗАЦИЯ
with app.app_context():
    db.create_all()
    
    # Админы
    admins = [
        {'username': 'CatNap', 'email': 'nazartrahov10@gmail.com', 'password': '120187', 'is_admin': True},
        {'username': 'Назар', 'email': 'nazartrahov1@gmail.com', 'password': '120187', 'is_admin': True},
    ]
    for admin in admins:
        if not User.query.filter_by(email=admin['email']).first():
            user = User(**admin)
            user.password = bcrypt.generate_password_hash(admin['password']).decode('utf-8')
            db.session.add(user)
    
    # Примеры категорий
    if not Category.query.first():
        cats = [Category(name='Minecraft'), Category(name='World of Tanks')]
        db.session.add_all(cats)
        db.session.commit()

if __name__ == '__main__':
    app.run(debug=True)
