import os
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
from sqlalchemy import desc

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'uznavaykin-info-2026!')
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
    email = db.Column(db.String(120))
    password_hash = db.Column(db.String(120), nullable=False)
    subscription = db.Column(db.String(20), default='start')
    subscription_expires = db.Column(db.DateTime)
    avatar = db.Column(db.String(200))
    bio = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class GameInfo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    game = db.Column(db.String(50), nullable=False)  # Майнкрафт, Танки
    faction = db.Column(db.String(50))  # Блоки, СССР
    item = db.Column(db.String(50))  # Дёрн, КВ-1
    level = db.Column(db.Integer)
    description = db.Column(db.Text)
    image = db.Column(db.String(200))
    is_premium = db.Column(db.Boolean, default=False)  # Только для Premium
    views = db.Column(db.Integer, default=0)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def get_user_privilege():
    if not current_user.is_authenticated:
        return 'start'
    if current_user.subscription == 'premium' and current_user.subscription_expires and current_user.subscription_expires > datetime.utcnow():
        return 'premium'
    if current_user.subscription == 'vip' and current_user.subscription_expires and current_user.subscription_expires > datetime.utcnow():
        return 'vip'
    return 'start'

# Инициализация БД с ИНФО
with app.app_context():
    db.create_all()
    
    if GameInfo.query.count() == 0:
        info_data = [
            # Майнкрафт START
            GameInfo(game="Майнкрафт", faction="Блоки", item="Дёрн", description="Обычная трава для строительства", image="grass.png"),
            GameInfo(game="Майнкрафт", faction="Блоки", item="Камень", description="Базовый строительный блок", image="stone.png"),
            
            # Танки START  
            GameInfo(game="Танки", faction="СССР", item="Т-34", level=5, description="Средний танк СССР", image="t34.png"),
            
            # VIP ЭКСКЛЮЗИВ
            GameInfo(game="Майнкрафт", faction="Руды", item="Лазурит", description="Редкая синяя руда для декора", image="lapis.png", is_premium=False),
            GameInfo(game="Танки", faction="СССР", item="ИС-3", level=7, description="Тяжёлый танк конца войны", image="is3.png", is_premium=False),
            
            # PREMIUM 3D
            GameInfo(game="Майнкрафт", faction="Мобы", item="Эндермен", description="Таинственный моб из Энда с 3D моделью", image="ender3d.png", is_premium=True),
            GameInfo(game="Танки", faction="Германия", item="Маус", level=10, description="Супертяж с 3D моделью", image="maus3d.png", is_premium=True),
        ]
        for info in info_data:
            db.session.add(info)
        db.session.commit()

# МАРШРУТЫ
@app.route('/')
def index():
    privilege = get_user_privilege()
    featured = GameInfo.query.filter(GameInfo.is_premium == (privilege == 'premium')).limit(6).all()
    return render_template('index.html', featured=featured, privilege=privilege)

@app.route('/catalog/<game_name>')
def catalog(game_name):
    privilege = get_user_privilege()
    infos = GameInfo.query.filter_by(game=game_name).filter(
        GameInfo.is_premium == False | (GameInfo.is_premium == True & privilege == 'premium')
    ).all()
    return render_template('catalog.html', game_name=game_name, infos=infos, privilege=privilege)

@app.route('/info/<int:info_id>')
def info(info_id):
    info_item = GameInfo.query.get_or_404(info_id)
    info_item.views += 1
    db.session.commit()
    privilege = get_user_privilege()
    return render_template('info_detail.html', info=info_item, privilege=privilege)

@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html')

@app.route('/subscribe/<sub_type>')
@login_required
def subscribe(sub_type):
    prices = {'vip': 100, 'premium': 200}
    if sub_type in prices:
        expires = datetime.utcnow() + timedelta(days=30)
        current_user.subscription = sub_type
        current_user.subscription_expires = expires
        db.session.commit()
        flash(f'✅ {sub_type.upper()} активирован на 30 дней!')
    return redirect(url_for('profile'))

# Остальные маршруты (login/register) как раньше...
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and bcrypt.check_password_hash(user.password_hash, request.form['password']):
            login_user(user)
            return redirect(url_for('index'))
        flash('❌ Неверные данные!')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        if not User.query.filter_by(username=request.form['username']).first():
            password = bcrypt.generate_password_hash(request.form['password']).decode('utf-8')
            user = User(username=request.form['username'])
            user.password_hash = password
            db.session.add(user)
            db.session.commit()
            flash('✅ Регистрация успешна!')
            return redirect(url_for('login'))
        flash('❌ Пользователь существует!')
    return render_template('register.html')

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
