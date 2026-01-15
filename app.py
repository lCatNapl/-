import os
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
from sqlalchemy import or_
from collections import defaultdict

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
    is_permanent = db.Column(db.Boolean, default=False)
    is_admin = db.Column(db.Boolean, default=False)
    views_count = db.Column(db.Integer, default=0)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('category.id'))
    parent = db.relationship('Category', remote_side=[id], backref='children')
    infos = db.relationship('Info', backref='category_tree', lazy=True)

class Info(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    views = db.Column(db.Integer, default=0)
    image_url = db.Column(db.String(200))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def get_online_stats():
    cutoff = datetime.utcnow() - timedelta(minutes=5)
    online_users = User.query.filter(User.last_seen > cutoff).all()
    start_count = vip_count = premium_count = admin_count = 0
    for user in online_users:
        if user.is_admin:
            admin_count += 1
        elif user.role == 'premium':
            premium_count += 1
        elif user.role == 'vip':
            vip_count += 1
        else:
            start_count += 1
    return {'start': start_count, 'vip': vip_count, 'premium': premium_count, 'admin': admin_count, 'total': len(online_users)}

@app.before_request
def update_last_seen():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.utcnow()
        db.session.commit()

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
    show_3d = current_user.is_authenticated and current_user.role == 'premium'
    return render_template('info.html', info=info, show_3d=show_3d)

@app.route('/profile/')
@login_required
def profile():
    stats = get_online_stats()
    return render_template('profile.html', stats=stats)

@app.route('/community/')
def community():
    return render_template('community.html', telegram_url='https://t.me/ssylkanatelegramkanalyznaikin')

@app.route('/admin/', methods=['GET', 'POST'])
@login_required
def admin_panel():
    if not current_user.is_admin:
        flash('❌ Только для админов!')
        return redirect(url_for('index'))
    
    root_categories = Category.query.filter_by(parent_id=None).all()
    
    if request.method == 'POST':
        if 'add_category' in request.form:
            new_cat = Category(name=request.form['cat_name'])
            if request.form.get('parent_id'):
                new_cat.parent_id = int(request.form['parent_id'])
            db.session.add(new_cat)
            flash('✅ Категория добавлена!')
        
        elif 'add_info' in request.form:
            new_info = Info(
                title=request.form['title'],
                description=request.form['description'],
                category_id=int(request.form['category_id'])
            )
            db.session.add(new_info)
            flash('✅ Запись добавлена!')
        
        elif 'delete_cat' in request.form:
            cat = Category.query.get_or_404(int(request.form['cat_id']))
            db.session.delete(cat)
            flash('✅ Категория удалена!')
        
        elif 'delete_info' in request.form:
            info = Info.query.get_or_404(int(request.form['info_id']))
            db.session.delete(info)
            flash('✅ Запись удалена!')
        
        db.session.commit()
    
    all_infos = Info.query.all()
    return render_template('admin.html', categories=root_categories, infos=all_infos)

# Инициализация БД
with app.app_context():
    db.create_all()
    
    admins = [
        {'username': 'CatNap', 'email': 'nazartrahov10@gmail.com', 'password': '120187', 'role': 'admin', 'is_permanent': True, 'is_admin': True},
        {'username': 'Назар', 'email': 'nazartrahov1@gmail.com', 'password': '120187', 'role': 'admin', 'is_permanent': True, 'is_admin': True},
    ]
    
    for admin in admins:
        if not User.query.filter_by(email=admin['email']).first():
            user = User(**admin)
            user.password = bcrypt.generate_password_hash(admin['password']).decode('utf-8')
            db.session.add(user)
    
    if not Category.query.first():
        minecraft = Category(name='Minecraft')
        wot = Category(name='World of Tanks')
        db.session.add_all([minecraft, wot])
        db.session.commit()

if __name__ == '__main__':
    app.run(debug=True)
