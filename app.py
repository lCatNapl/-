import os
from datetime import datetime, timedelta

from flask import (
    Flask, render_template, request,
    redirect, url_for, flash
)
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, UserMixin,
    login_user, login_required,
    logout_user, current_user
)
from flask_bcrypt import Bcrypt
from sqlalchemy import or_

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'uznavaykin-info-2026!')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Путь к БД
INSTANCE_PATH = os.path.join(os.path.dirname(__file__), 'instance')
os.makedirs(INSTANCE_PATH, exist_ok=True)
DB_PATH = os.path.join(INSTANCE_PATH, 'uznavaykin.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_PATH}'

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'


# ===================== МОДЕЛИ =====================

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120))
    password_hash = db.Column(db.String(120), nullable=False)
    subscription = db.Column(db.String(20), default='start')  # start | vip | premium
    subscription_expires = db.Column(db.DateTime)
    avatar = db.Column(db.String(200))
    bio = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class GameInfo(db.Model):
    """
    Примеры:
    Майнкрафт - Блоки - Дёрн
    Танки - СССР - 5 уровень - КВ-1
    """
    id = db.Column(db.Integer, primary_key=True)
    game = db.Column(db.String(50), nullable=False)      # "Майнкрафт", "Танки"
    faction = db.Column(db.String(50))                  # "Блоки", "СССР", "Руды", "Германия" и т.п.
    item = db.Column(db.String(50), nullable=False)     # "Дёрн", "КВ-1", "Т-34" и т.д.
    level = db.Column(db.Integer)                       # Уровень (для танков)
    description = db.Column(db.Text)
    image = db.Column(db.String(200))                   # путь к картинке
    is_premium = db.Column(db.Boolean, default=False)   # true = только для Premium
    views = db.Column(db.Integer, default=0)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def get_user_privilege() -> str:
    """Возвращает текущую привилегию: start / vip / premium."""
    if not current_user.is_authenticated:
        return 'start'
    if current_user.subscription_expires and current_user.subscription_expires < datetime.utcnow():
        return 'start'
    return current_user.subscription or 'start'


def get_theme_for_game(game_name: str) -> str:
    """Тема по игре: minecraft / wot / default."""
    if game_name == 'Майнкрафт':
        return 'minecraft'
    if game_name == 'Танки':
        return 'wot'
    return 'default'


# =============== ИНИЦИАЛИЗАЦИЯ БАЗЫ ===============

with app.app_context():
    db.create_all()

    # Админы с премиумом «навсегда» (условно до 31.12.2030)
    admins = [
        {
            'username': 'CatNap',
            'email': 'nazartrahov1@gmail.com',
            'password': '120187',
            'subscription': 'premium'
        },
        {
            'username': 'Назар',
            'email': 'nazartrahov1@gmail.com',
            'password': '120187',
            'subscription': 'premium'
        },
    ]

    for admin_data in admins:
        existing = User.query.filter_by(username=admin_data['username']).first()
        if not existing:
            admin = User(
                username=admin_data['username'],
                email=admin_data['email'],
                password_hash=bcrypt.generate_password_hash(
                    admin_data['password']
                ).decode('utf-8'),
                subscription=admin_data['subscription'],
                subscription_expires=datetime(2030, 12, 31, 23, 59, 59),
            )
            db.session.add(admin)
            print(f"✅ СУПЕР-АДМИН '{admin_data['username']}' создан с PREMIUM до 31.12.2030")
        else:
            existing.subscription = 'premium'
            existing.subscription_expires = datetime(2030, 12, 31, 23, 59, 59)
            print(f"✅ Админ '{admin_data['username']}' обновлён (Premium до 31.12.2030)")

    # Базовая инфа, если пусто
    if GameInfo.query.count() == 0:
        base_items = [
            # Майнкрафт — Start
            GameInfo(
                game="Майнкрафт",
                faction="Блоки",
                item="Дёрн",
                description="Обычный блок земли с травой. Подходит для строительства и ферм.",
                image="/static/img/mc_dirt.png",
                is_premium=False,
            ),
            GameInfo(
                game="Майнкрафт",
                faction="Блоки",
                item="Камень",
                description="Базовый строительный блок. Добывается из обычного камня киркой.",
                image="/static/img/mc_stone.png",
                is_premium=False,
            ),
            # Танки — Start
            GameInfo(
                game="Танки",
                faction="СССР",
                item="Т-34",
                level=5,
                description="Знаменитый советский средний танк. Баланс подвижности и брони.",
                image="/static/img/wot_t34.png",
                is_premium=False,
            ),
            GameInfo(
                game="Танки",
                faction="СССР",
                item="КВ-1",
                level=5,
                description="Тяжёлый танк СССР с крепкой лобовой бронёй.",
                image="/static/img/wot_kv1.png",
                is_premium=False,
            ),
            # VIP (расширенная инфа)
            GameInfo(
                game="Майнкрафт",
                faction="Руды",
                item="Лазурит",
                description="Синяя руда, используется для чар и декора. Доступно с VIP.",
                image="/static/img/mc_lapis.png",
                is_premium=False,
            ),
            GameInfo(
                game="Танки",
                faction="СССР",
                item="ИС-3",
                level=7,
                description="Тяжёлый танк с характерным «щучьим носом» и хорошим орудием.",
                image="/static/img/wot_is3.png",
                is_premium=False,
            ),
            # Premium (3D / топ инфа)
            GameInfo(
                game="Майнкрафт",
                faction="Мобы",
                item="Эндермен (3D)",
                description="Высокий чёрный моб из Энда. 3D-модель и расширенное описание для Premium.",
                image="/static/img/mc_enderman_3d.png",
                is_premium=True,
            ),
            GameInfo(
                game="Танки",
                faction="Германия",
                item="Маус (3D)",
                level=10,
                description="Супертяжёлый танк Германии. 3D‑модель и топовая аналитика для Premium.",
                image="/static/img/wot_maus_3d.png",
                is_premium=True,
            ),
        ]
        db.session.add_all(base_items)
        db.session.commit()
        print("✅ Базовая информация по Майнкрафту и Танкам добавлена")


# ===================== МАРШРУТЫ =====================

@app.route('/')
def index():
    privilege = get_user_privilege()

    if privilege == 'premium':
        featured = GameInfo.query.order_by(
            GameInfo.is_premium.desc(),
            GameInfo.views.desc()
        ).limit(8).all()
    else:
        featured = GameInfo.query.filter(
            or_(GameInfo.is_premium == False, GameInfo.is_premium.is_(None))
        ).order_by(GameInfo.views.desc()).limit(8).all()

    return render_template(
        'index.html',
        featured=featured,
        privilege=privilege,
        theme='default'
    )


@app.route('/catalog/<game_name>')
def catalog(game_name):
    privilege = get_user_privilege()
    theme = get_theme_for_game(game_name)

    base_query = GameInfo.query.filter_by(game=game_name)

    if privilege == 'premium':
        infos = base_query.order_by(
            GameInfo.is_premium.desc(),
            GameInfo.faction,
            GameInfo.item
        ).all()
    else:
        infos = base_query.filter(
            or_(GameInfo.is_premium == False, GameInfo.is_premium.is_(None))
        ).order_by(GameInfo.faction, GameInfo.item).all()

    factions = [
        f[0] for f in db.session.query(GameInfo.faction)
        .filter_by(game=game_name).distinct().all()
        if f[0]
    ]

    return render_template(
        'catalog.html',
        game_name=game_name,
        infos=infos,
        factions=factions,
        privilege=privilege,
        theme=theme,
    )


@app.route('/info/<int:info_id>')
def info_detail(info_id):
    privilege = get_user_privilege()
    info = GameInfo.query.get_or_404(info_id)
    theme = get_theme_for_game(info.game)

    if info.is_premium and privilege != 'premium':
        flash('Эта информация доступна только для Premium.')
        return redirect(url_for('index'))

    info.views += 1
    db.session.commit()

    return render_template(
        'info_detail.html',
        info=info,
        privilege=privilege,
        theme=theme
    )


@app.route('/profile')
@login_required
def profile():
    privilege = get_user_privilege()
    return render_template('profile.html', privilege=privilege, theme='default')


@app.route('/profile/edit', methods=['POST'])
@login_required
def edit_profile():
    current_user.bio = request.form.get('bio', '').strip()
    current_user.avatar = request.form.get('avatar', '').strip()
    db.session.commit()
    flash('Профиль обновлён.')
    return redirect(url_for('profile'))


@app.route('/subscribe/<sub_type>')
@login_required
def subscribe(sub_type):
    if sub_type not in ('vip', 'premium'):
        flash('Неизвестный тип подписки.')
        return redirect(url_for('profile'))

    # Обычным пользователям подписка на 30 дней
    expires = datetime.utcnow() + timedelta(days=30)
    current_user.subscription = sub_type
    current_user.subscription_expires = expires
    db.session.commit()
    flash(f'Подписка {sub_type.upper()} активирована на 30 дней.')
    return redirect(url_for('profile'))


# ===================== АУТЕНТИФИКАЦИЯ =====================

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        user = User.query.filter_by(username=username).first()
        if user and bcrypt.check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('index'))

        flash('Неверный логин или пароль.')
    return render_template('login.html', theme='default')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        email = request.form.get('email', '').strip() or None

        if not username or not password:
            flash('Логин и пароль обязательны.')
            return redirect(url_for('register'))

        if User.query.filter_by(username=username).first():
            flash('Пользователь с таким логином уже существует.')
            return redirect(url_for('register'))

        password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
        user = User(username=username, email=email, password_hash=password_hash)
        db.session.add(user)
        db.session.commit()
        flash('Регистрация успешна! Теперь войдите.')
        return redirect(url_for('login'))

    return render_template('register.html', theme='default')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))


# ===================== ЗАПУСК =====================

if __name__ == '__main__':
    app.run(debug=True)
