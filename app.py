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

# Заменяем функцию smart_search() на простую:
def smart_search(query):
    all_infos = Info.query.all()
    results = []
    query_lower = query.lower()
    
    # Простой поиск БЕЗ C-расширений
    translations = {
        'minecraft': ['майнкрафт', 'майк', 'mc', 'minecraft'],
        'wargaming': ['ворлд оф танкс', 'танки', 'wot', 'world of tanks'],
        'дерн': ['grass', 'трава'], 'земля': ['dirt', 'грунт'],
        'ссср': ['советский союз', 'russia', 'совок']
    }
    
    for info in all_infos:
        score = 0
        # Точное совпадение
        if query_lower in info.title.lower() or query_lower in info.description.lower():
            score += 100
        
        # Простое fuzzy (без Levenshtein)
        def simple_fuzzy(s1, s2):
            min_len = min(len(s1), len(s2))
            matches = sum(1 for a, b in zip(s1, s2) if a == b)
            return (matches / min_len) * 100 if min_len > 0 else 0
        
        score += simple_fuzzy(query_lower, info.title.lower())
        score += simple_fuzzy(query_lower, info.category.lower())
        
        # Переводы
        for eng, rus in translations.items():
            if query_lower in str(rus) + [eng]:
                if eng in info.title.lower() or eng in info.category.lower():
                    score += 50
        
        if score > 30:
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

# Замени ВСЮ секцию with app.app_context(): на ЭТО:

with app.app_context():
    db.create_all()
    
    # ✅ ФИКС 1: Проверяем ПЕРЕД созданием
    admins = [
        {'username': 'CatNap', 'email': 'nazartrahov10@gmail.com', 'password': '120187', 'role': 'admin', 'is_permanent': True},
        {'username': 'Назар', 'email': 'nazartrahov1@gmail.com', 'password': '120187', 'role': 'admin', 'is_permanent': True},
    ]
    
    for admin in admins:
        if not User.query.filter_by(email=admin['email']).first():
            user = User(**admin)
            user.password = bcrypt.generate_password_hash(admin['password']).decode('utf-8')
            db.session.add(user)
    
    # ✅ ФИКС 2: Info тоже проверяем
    if not Info.query.first():
        minecraft_blocks = [
            {'title': 'Дёрн', 'category': 'Minecraft', 'subcategory': 'Блоки', 'description': 'Получение
Разрушение
Дёрн может быть добыт чем угодно, но лопаты добывают его эффективнее всего. Следует отметить, что при добыче инструментом без чар «Шёлкового касания» выпадет блок земли. Также в Творческом режиме можно получить дёрн нажатием СКМ по блоку.
Натуральная генерация
Дёрн генерируется на верхнем слое блоков земли во многих биомах Обычного мира, если он находится под открытым небом. Также он может заменять собой блоки земли при особых условиях (см. Рост травы ниже).
Дёрн генерируется в составе некоторых структур деревень, а также биомов саванны, равнин и тайги, что позволяет добыть его даже в мирах с необычной генерацией, в которых дёрн располагается иначе.
Странник Края
Странник Края может подобрать дёрн, что делает возможным его получение после смерти странника без использования Шёлкового касания.
Рост травы

Область, в которой распространяется дёрн от исходного блока
Спонтанно дёрн вырастает только при генерации мира. Затем дёрн может только разрастаться заменяя собой блоки земли, но не каменистой земли. Без участия игроков этот процесс зависит от времени дня. Чтобы дёрн заменил собой землю, должны быть соблюдены следующие условия:
Блок земли, на месте которого ожидается дёрн (далее — целевой блок) должен быть в области 3×3×5 (длина×ширина×высота), центром которой является блок прямо под блоком травы, откуда дёрн должен разрастаться (далее — исходный блок);
Над целевым блоком должен быть свет величиной в 9 или больше;
Блок прямо над блоком земли должен пропускать свет так, чтобы он доходил до блока земли. Конкретный уровень освещения значения не имеет. Это значит, что блоки, пропускающие свет частично, такие как ступени и плиты, не должны быть обращены к блоку земли сторонами, закрывающими свет.
Блок прямо над блоком земли не должен быть лавой, водой или затопленным вариантом любого блока.
Хотя вода и лава пропускают свет лишь частично (они уменьшают свет от неба на 1 уровень и не влияют на свет от блоков), другие блоки с частичной светопроницаемостью, как лёд или блоки слизи, не препятствуют росту дёрна на блоке земли. Дёрн может расти и под другими прозрачными блоками, в том числе под стеклом, забором или факелами. Дёрн переходит непосредственно от одного блока к одному из соседних, и на это не влияет то, какие блоки находятся между ними. Блоки дёрна разрастаются со случайными интервалами, и выбор любого из подходящих блоков в зоне роста равновероятен. Поскольку дёрн может распространяться на 3 уровня вниз, как правило, вниз по склону он разрастается быстрее, чем вверх по склону.
Окраска дёрна зависит от биома, в котором он находится. Дёрн всегда будет использовать набор цветового тона, привязанный к данному биому, независимо от размещения блока.

Оттенки цветов, которые может принимать дёрн
Гибель травы
Дёрн может завянуть (блок может превратиться в землю), если над ним стоит блок, уменьшающий величину получаемого света до 4 или ниже, включая непрозрачные блоки, или дёрн в темноте[1]. Под прозрачными блоками дёрн не увядает.
Обработка дёрна мотыгой преобразует его в блок грядки.
Дёрн также могут съесть овцы (первоначальный блок заменяется на блок земли).
Дёрн также может быть преобразован в травяную тропинку с помощью лопаты.
Использование
Многие животные всегда появляются на дёрне.
Если в память не загружены другие животные, то несколько из них появляются на дёрне.
Овцы едят траву с этих блоков, превращая их в землю и заново отращивая свою шерсть, если её срезали ножницами ранее.
Костная мука, использованная на дёрне, может вырастить высокую траву и цветы.
Снежный дёрн
Дёрн, на котором находится снег или блок снега, меняет окрас травы на белый, если снег убрать, то блок станет вновь зелёным.
Переработка
В случае Bedrock Edition дёрн, помещённый в компостер, с 30-процентной вероятностью увеличит уровень перегноя на 1.
'},
            {'title': 'Земля', 'category': 'Minecraft', 'subcategory': 'Блоки', 'description': 'Получение
Разрушение
Земля очень легко уничтожается любым инструментом, даже рукой. В любом случае при добыче выпадает блок.
Натуральная генерация
Земля на карте генерируется в изобилии: верхний слой (размером в 3—4 блока) между дёрном или снегом и камнем практически полностью состоит из земли. Более того, скопления земли можно найти в подземельях на всех высотах и на дне глубоких водоёмов.
Торговля
Странствующий торговец иногда может продавать подзол, который при своей добычи инструментом, не зачарованным на шёлковое касание, дропает землю. Это весьма неэффективный, но всё же бесконечный источник земли, так как странствующий торговец — моб, а значит, может спауниться в неограниченном количестве.
Использование
Земля — один из видов блоков, на которые можно посадить растения.
На земле можно сделать грядку, используя мотыгу. После вспахивания земли мотыгой верхняя текстура блока становится «ребристой», а после размещения рядом источника воды приобретает тёмно-коричневый цвет и становится пригодной для посадки семян. Семена можно посадить и на сухую грядку, но такие грядки затаптываются быстрее и могут сами превратиться обратно в землю через некоторое время, если на грядке ничего не растёт.
Земля покрывается дёрном в том случае, если она не является каменистой, рядом находится блок земли, покрытый травой, и она подвергается воздействию света 4-го уровня или выше (подробнее этот процесс описан в статье Дёрн). Также земля может превратиться в мицелий, если рядом есть другой блок мицелия.
Каменистую же землю можно использовать для получения обычной с помощью мотыги. Таким образом, из гравия и двух блоков земли можно создать множество блоков земли — это помогает, например, в выживании на острове.
'},
        ]
        wot_tanks = [
            {'title': 'Т-34', 'category': 'World of Tanks', 'subcategory': 'Танки', 'subsubcategory': 'СССР', 'level': '5 уровень'},
            {'title': 'КВ-1', 'category': 'World of Tanks', 'subcategory': 'Танки', 'subsubcategory': 'СССР', 'level': '5 уровень'},
            {'title': 'КВ-1С', 'category': 'World of Tanks', 'subcategory': 'Танки', 'subsubcategory': 'СССР', 'level': '6 уровень'},
        ]
        for item in minecraft_blocks + wot_tanks:
            if not Info.query.filter_by(title=item['title']).first():
                info = Info(**item)
                db.session.add(info)
        db.session.commit()


if __name__ == '__main__':
    app.run(debug=True)


