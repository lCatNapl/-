import os
from datetime import datetime, timedelta
from collections import defaultdict
from flask import (
    Flask, render_template, request, redirect, url_for, flash, session, jsonify
)
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, UserMixin, login_user, login_required,
    logout_user, current_user
)
from flask_bcrypt import Bcrypt
from sqlalchemy import or_, func
from werkzeug.utils import secure_filename
import fuzzywuzzy.fuzz
from fuzzywuzzy import process

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'uznavaykin-2026-super')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///site.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

# ПУНКТЫ 1,4: Роли пользователей (1,2,3 - админы, остальные Start по умолчанию)
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), default='start')  # start, vip, premium, admin
    is_permanent = db.Column(db.Boolean, default=False)
    views_count = db.Column(db.Integer, default=0)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Info(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(100), nullable=False)  # Minecraft/World of Tanks
    subcategory = db.Column(db.String(100))  # Блоки/Танки
    subsubcategory = db.Column(db.String(100))  # Дёрн/СССР
    level = db.Column(db.String(50))  # 1 уровень
    description = db.Column(db.Text)
    views = db.Column(db.Integer, default=0)
    image_url = db.Column(db.String(200))
    is_3d = db.Column(db.Boolean, default=False)

# ПУНКТ 9: Умный поиск
def smart_search(query):
    all_infos = Info.query.all()
    results = []
    query_lower = query.lower()
    
    # Точный поиск + fuzzy + переводы + похожие
    translations = {
        'minecraft': ['майнкрафт', 'майк', 'mc'],
        'wargaming': ['ворлд оф танкс', 'танки', 'wot', 'world of tanks'],
        'дерн': ['grass', 'трава'], 'земля': ['dirt', 'грунт'],
        'ссср': ['советский союз', 'russia', 'совок']
    }
    
    for info in all_infos:
        score = 0
        # Точное совпадение
        if query_lower in info.title.lower() or query_lower in info.description.lower():
            score += 100
        # Fuzzy similarity
        score += fuzzywuzzy.fuzz.ratio(query_lower, info.title.lower())
        score += fuzzywuzzy.fuzz.ratio(query_lower, info.category.lower())
        
        # Переводы и наводки
        for eng, rus in translations.items():
            if query_lower in rus or eng in query_lower:
                if eng in info.title.lower() or eng in info.category.lower():
                    score += 50
        
        if score > 30:  # Порог релевантности
            results.append((info, score))
    
    return sorted(results, key=lambda x: x[1], reverse=True)[:10]

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ПУНКТ 4: Подсчёт онлайн по ролям (последние 5 минут)
def get_online_stats():
    cutoff = datetime.utcnow() - timedelta(minutes=5)
    online_users = User.query.filter(User.last_seen > cutoff).all()
    
    start_count = vip_count = premium_count = admin_count = 0
    for user in online_users:
        if user.is_permanent and user.id in [1,2,3]:
            admin_count += 1
        elif user.role == 'premium':
            premium_count += 1
        elif user.role == 'vip':
            vip_count += 1
        else:
            start_count += 1
    
    return {
        'start': start_count, 'vip': vip_count, 
        'premium': premium_count, 'admin': admin_count,
        'total': len(online_users)
    }

@app.before_request
def update_last_seen():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.utcnow()
        db.session.commit()

@app.route('/')
def index():
    # ПУНКТ 7: Главная - топ по просмотрам + быстрый поиск
    popular = Info.query.order_by(Info.views.desc()).limit(6).all()
    stats = get_online_stats()
    return render_template('index.html', popular=popular, stats=stats)

@app.route('/catalog/')
@app.route('/catalog/<path:category_path>')
def catalog(category_path=None):
    # ПУНКТ 6: Каталог по структуре
    infos = Info.query.all()
    
    catalog_structure = {
        'Minecraft': {
            'Блоки': ['Дёрн', 'Земля', 'Камень', 'Песок', 'Гравий'],
            'Биомы': ['Саванна', 'Лес', 'Пустыня', 'Горы', 'Океан']
        },
        'World of Tanks': {
            'Танки': {
                'СССР': ['1 уровень', '2 уровень', '3 уровень', 'Тяжёлые', 'ЛТ'],
                'Германия': ['1 уровень', '2 уровень', 'Тяжёлые', 'ПТ', 'Арта']
            }
        }
    }
    
    return render_template('catalog.html', 
                         catalog=catalog_structure, 
                         category_path=category_path)

@app.route('/search/')
def search():
    query = request.args.get('q', '')
    if query:
        results = smart_search(query)
    else:
        results = []
    return render_template('search.html', query=query, results=results)

@app.route('/info/<int:info_id>')
def info_detail(info_id):
    info = Info.query.get_or_404(info_id)
    info.views += 1
    current_user.views_count += 1 if current_user.is_authenticated else 0
    db.session.commit()
    
    # ПУНКТ 1: 3D только для Premium
    show_3d = current_user.is_authenticated and current_user.role == 'premium'
    
    # ПУНКТ 3: Показываем просмотры
    return render_template('info.html', info=info, show_3d=show_3d)

@app.route('/profile/')
@login_required
def mega_profile():
    # ПУНКТ 8: Мега профиль
    stats = get_online_stats()
    user_infos = Info.query.filter_by().order_by(Info.views.desc()).limit(10).all()
    return render_template('profile.html', stats=stats, user_infos=user_infos)

@app.route('/community/')
def community():
    # ПУНКТ 5: Только Telegram ссылка
    return render_template('community.html', telegram_url='https://t.me/ssylkanatelegramkanalyznaikin')

# Остальные роуты (login/register) остаются как были...

with app.app_context():
    db.create_all()
    
    # ПУНКТ 1,4: Админы 1,2,3 - навсегда
    admins = [
        {'username': 'CatNap', 'email': 'nazartrahov1@gmail.com', 'password': '120187', 'role': 'admin', 'is_permanent': True},
        {'username': 'Назар', 'email': 'nazartrahov1@gmail.com', 'password': '120187', 'role': 'admin', 'is_permanent': True},
    ]
    
    for admin in admins:
        if not User.query.filter_by(username=admin['username']).first():
            user = User(**admin)
            user.password = bcrypt.generate_password_hash(admin['password']).decode('utf-8')
            db.session.add(user)
    
    # ПУНКТ 6: Заполняем каталог
    if not Info.query.first():
        minecraft_blocks = [
            {'title': 'Дёрн', 'category': 'Minecraft', 'subcategory': 'Блоки', 'description': 'Верхний слой земли с травой.'},
            {'title': 'Земля', 'category': 'Minecraft', 'subcategory': 'Блоки', 'description': 'Обычная земля.'},
        ]
        wot_tanks = [
            {'title': 'Т-34', 'category': 'World of Tanks', 'subcategory': 'Танки', 'subsubcategory': 'СССР', 'level': '5 уровень'},
        ]
        for item in minecraft_blocks + wot_tanks:
            info = Info(**item)
            db.session.add(info)
        db.session.commit()

if __name__ == '__main__':
    app.run(debug=True)
