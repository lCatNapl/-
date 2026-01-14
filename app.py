import os
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
from sqlalchemy import desc

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-prod!')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# ✅ Создаем папку instance для БД
INSTANCE_PATH = os.path.join(os.path.dirname(__file__), 'instance')
os.makedirs(INSTANCE_PATH, exist_ok=True)
DB_PATH = os.path.join(INSTANCE_PATH, 'games.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_PATH}'

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# ✅ МОДЕЛИ (оставьте как есть)
class Game(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    rating = db.Column(db.Float, default=0.0)
    is_featured = db.Column(db.Boolean, default=False)
    plays = db.Column(db.Integer, default=0)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ✅ ИНИЦИАЛИЗАЦИЯ БД ПРИ КАЖДОМ ЗАПУСКЕ (GUNICORN + LOCAL)
def init_database():
    """Инициализация БД при запуске - РАБОТАЕТ с Gunicorn"""
    try:
        with app.app_context():
            db.create_all()
            
            # ✅ Тестовые данные (Game определена выше)
            if Game.query.count() == 0:
                test_games = [
                    Game(name="Змейка", description="Классическая змейка", rating=4.8, is_featured=True),
                    Game(name="Тетрис", description="Классический тетрис", rating=4.7, is_featured=True),
                    Game(name="Крестики-нолики", description="Игра на двоих", rating=4.2),
                ]
                for game in test_games:
                    db.session.add(game)
                db.session.commit()
                print("✅ Тестовые данные добавлены")
            print("✅ База данных готова!")
    except Exception as e:
        print(f"⚠️ Ошибка БД: {e}")

# ✅ МАРШРУТЫ
@app.route('/')
def index():
    games = Game.query.order_by(desc(Game.is_featured), desc(Game.rating)).limit(12).all()
    return render_template('index.html', games=games)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and bcrypt.check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('index'))
        flash('Неверные данные!')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = bcrypt.generate_password_hash(request.form['password']).decode('utf-8')
        if not User.query.filter_by(username=username).first():
            user = User(username=username, password_hash=password)
            db.session.add(user)
            db.session.commit()
            flash('Регистрация успешна!')
            return redirect(url_for('login'))
        flash('Пользователь уже существует!')
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/play/<int:game_id>')
def play(game_id):
    game = Game.query.get_or_404(game_id)
    game.plays += 1
    db.session.commit()
    return f"Игра {game.name} (просмотров: {game.plays})"

# ✅ ЕДИНСТВЕННЫЙ if __name__ - ВЫЗЫВАЕТ ИНИЦИАЛИЗАЦИЮ
if __name__ == '__main__':
    init_database()  # ✅ Запуск ИНИЦИАЛИЗАЦИИ
    app.run(debug=True)
