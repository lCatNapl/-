import os
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
from sqlalchemy import desc, func

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'uznavaykin-secret-2026!')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# База данных
INSTANCE_PATH = os.path.join(os.path.dirname(__file__), 'instance')
os.makedirs(INSTANCE_PATH, exist_ok=True)
DB_PATH = os.path.join(INSTANCE_PATH, 'uznavaykin.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_PATH}'

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# МОДЕЛИ
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True)
    password_hash = db.Column(db.String(120), nullable=False)
    subscription = db.Column(db.String(20), default='start')  # start, vip, premium
    subscription_expires = db.Column(db.DateTime)
    avatar = db.Column(db.String(200))
    bio = db.Column(db.Text)
    plays_total = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Game(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    image = db.Column(db.String(200))
    rating = db.Column(db.Float, default=0.0)
    is_featured = db.Column(db.Boolean, default=False)
    plays = db.Column(db.Integer, default=0)
    category = db.Column(db.String(50), default='arcade')

class Purchase(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    subscription = db.Column(db.String(20), nullable=False)
    price = db.Column(db.Integer, nullable=False)  # рубли
    purchased_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User', backref='purchases')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Инициализация БД
with app.app_context():
    db.create_all()
    
    # Тестовые игры
    if Game.query.count() == 0:
        games = [
            Game(name="Змейка 3D", description="Классика в 3D с новыми эффектами", image="snake3d.jpg", rating=4.9, is_featured=True, category="arcade"),
            Game(name="Тетрис Neo", description="Современный тетрис с неоновыми эффектами", image="tetrisneo.jpg", rating=4.8, is_featured=True, category="puzzle"),
            Game(name="Космические Бои", description="Динамичные космические сражения", image="space.jpg", rating=4.7, category="shooter"),
        ]
        for game in games:
            db.session.add(game)
        db.session.commit()

def get_user_subscription(user_id):
    user = User.query.get(user_id)
    if user and user.subscription_expires and user.subscription_expires > datetime.utcnow():
        return user.subscription
    return 'start'

# МАРШРУТЫ
@app.route('/')
def index():
    featured = Game.query.filter_by(is_featured=True).limit(6).all()
    popular = Game.query.order_by(Game.plays.desc()).limit(8).all()
    return render_template('index.html', featured=featured, popular=popular)

@app.route('/catalog')
def catalog():
    category = request.args.get('category', 'all')
    if category == 'all':
        games = Game.query.order_by(desc(Game.rating), desc(Game.plays)).all()
    else:
        games = Game.query.filter_by(category=category).all()
    categories = db.session.query(Game.category).distinct().all()
    return render_template('catalog.html', games=games, categories=[c[0] for c in categories])

@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html')

@app.route('/profile/edit', methods=['POST'])
@login_required
def edit_profile():
    current_user.bio = request.form.get('bio', '')
    current_user.avatar = request.form.get('avatar', '')
    db.session.commit()
    flash('Профиль обновлен!')
    return redirect(url_for('profile'))

@app.route('/subscribe/<sub_type>')
@login_required
def subscribe(sub_type):
    prices = {'vip': 100, 'premium': 200}
    if sub_type in prices:
        expires = datetime.utcnow() + timedelta(days=30)
        purchase = Purchase(user_id=current_user.id, subscription=sub_type, price=prices[sub_type])
        db.session.add(purchase)
        current_user.subscription = sub_type
        current_user.subscription_expires = expires
        db.session.commit()
        flash(f'Подписка {sub_type.upper()} активирована на 30 дней!')
    return redirect(url_for('profile'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and bcrypt.check_password_hash(user.password_hash, request.form['password']):
            login_user(user)
            return redirect(url_for('index'))
        flash('Неверные данные!')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        if not User.query.filter_by(username=request.form['username']).first():
            password = bcrypt.generate_password_hash(request.form['password']).decode('utf-8')
            user = User(username=request.form['username'], password_hash=password)
            db.session.add(user)
            db.session.commit()
            flash('Регистрация успешна!')
            return redirect(url_for('login'))
        flash('Пользователь существует!')
    return render_template('register.html')

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/play/<int:game_id>')
def play(game_id):
    game = Game.query.get_or_404(game_id)
    if current_user.is_authenticated:
        current_user.plays_total += 1
        game.plays += 1
        db.session.commit()
    return render_template('game_detail.html', game=game)

if __name__ == '__main__':
    app.run(debug=True)
