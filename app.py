from flask import Flask, request, redirect, url_for, session
import os

app = Flask(__name__)
app.secret_key = 'uznavaykin-2026-super-secret'

# ДАННЫЕ В ПАМЯТИ (иерархия + пользователи)
categories = {
    'Minecraft': ['Блоки', 'Биомы'],
    'World of Tanks': ['Танки', 'Карты']
}
category_contents = {
    'Minecraft/Блоки': ['Дёрн', 'Земля', 'Камень', 'Песок'],
    'Minecraft/Биомы': ['Саванна', 'Лес', 'Пустыня'],
    'World of Tanks/Танки': ['СССР', 'Германия'],
    'World of Tanks/СССР': ['Т-34', 'Т-50'],
    'World of Tanks/Германия': ['Pz.IV', 'Тигр']
}

users = {
    'CatNap': {'password': '120187', 'role': 'premium', 'admin': True},
    'Назар': {'password': '120187', 'role': 'premium', 'admin': True}
}
user_roles = {}
online_users = {}  # {username: timestamp}

@app.route('/', methods=['GET', 'POST'])
def index():
    current_user = session.get('user')
    stats = calculate_online_stats()
    
    html = '''
    <!DOCTYPE html>
    <html><head><title>Узнавайкин</title>
    <meta charset="utf-8">
    <style>body{font-family:Arial;padding:20px;max-width:900px;margin:auto;}
    button{padding:10px 20px;margin:5px;background:#007bff;color:white;border:none;border-radius:5px;cursor:pointer;}
    .cat{display:block;margin:10px;padding:15px;border:2px solid #ddd;border-radius:10px;}
    a{color:#007bff;text-decoration:none;}</style></head>
    <body>
    '''
    
    if current_user:
        role = user_roles.get(current_user, 'start')
        html += f'''
        <h1>🏠 Узнавайкин</h1>
        <div style="background:#e9ecef;padding:15px;border-radius:10px;">
            👤 <b>{current_user}</b> ({role.upper()}) 
            | <a href="/profile">👤 Профиль</a> | <a href="/logout">🚪 Выход</a>
        </div>
        '''
        if role != 'premium':
            html += '''
            <div style="margin:20px 0;">
                <a href="/buy/vip" style="background:#28a745;color:white;padding:12px 25px;">VIP 100₽</a>
                <a href="/buy/premium" style="background:gold;color:black;padding:12px 25px;">PREMIUM 200₽</a>
            </div>
            '''
    else:
        html += '''
        <h1>🏠 Узнавайкин</h1>
        <div style="margin:20px 0;">
            <a href="/login" style="background:#28a745;color:white;padding:15px 30px;">🔐 ВОЙТИ</a>
            <a href="/register" style="background:#ffc107;color:black;padding:15px 30px;">📝 РЕГИСТРАЦИЯ</a>
        </div>
        '''
    
    html += f'''
        <div style="background:#d4edda;padding:10px;border-radius:5px;">
            👥 Онлайн: <b>{stats['total']}</b> (Start:{stats['start']} VIP:{stats['vip']} Premium:{stats['premium']} Admin:{stats['admin']})
        </div>
        <hr>
        <div style="display:flex;gap:20px;">
            <a href="/catalog" style="background:#17a2b8;color:white;padding:15px 30px;">📁 КАТАЛОГ</a>
            <a href="/community" style="background:#6c757d;color:white;padding:15px 30px;">💬 TELEGRAM</a>
        </div>
    '''
    
    if current_user and users.get(current_user, {}).get('admin'):
        html += '<p style="margin-top:20px;"><a href="/admin" style="background:#dc3545;color:white;padding:15px 30px;">🔧 АДМИН ПАНЕЛЬ</a></p>'
    
    html += '</body></html>'
    return html

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        
        # Авторегистрация + админы
        if username in users and users[username]['password'] == password:
            session['user'] = username
            user_roles[username] = users[username]['role']
            online_users[username] = get_timestamp()
            return redirect(url_for('index'))
        elif username not in users:
            # Новый пользователь
            users[username] = {'password': password, 'role': 'start', 'admin': False}
            user_roles[username] = 'start'
            session['user'] = username
            online_users[username] = get_timestamp()
            return redirect(url_for('index'))
        
        return '''
        <h2 style="color:red;">❌ Неверный логин/пароль!</h2>
        <a href="/login">← Попробовать снова</a>
        '''
    
    return '''
    <!DOCTYPE html>
    <html><head><title>Вход</title>
    <style>body{font-family:Arial;padding:50px;text-align:center;background:#f8f9fa;}
    form{max-width:400px;margin:auto;background:white;padding:30px;border-radius:10px;box-shadow:0 0 20px rgba(0,0,0,0.1);}</style></head>
    <body>
    <h1>🔐 Узнавайкин — Вход</h1>
    <form method="post">
        <div style="margin:20px 0;">
            <input name="username" placeholder="Логин" style="width:100%;padding:15px;font-size:16px;border:2px solid #ddd;border-radius:5px;box-sizing:border-box;" required>
        </div>
        <div style="margin:20px 0;">
            <input name="password" type="password" placeholder="Пароль" style="width:100%;padding:15px;font-size:16px;border:2px solid #ddd;border-radius:5px;box-sizing:border-box;" required>
        </div>
        <button style="width:100%;padding:15px;background:#007bff;color:white;border:none;border-radius:5px;font-size:18px;cursor:pointer;">🚀 ВОЙТИ</button>
    </form>
    <p style="margin-top:30px;font-size:14px;">
        👑 <b>Админы:</b> CatNap / 120187 | Назар / 120187
    </p>
    </body></html>
    '''

@app.route('/logout')
def logout():
    if 'user' in session:
        session.pop('user')
    return redirect(url_for('index'))

@app.route('/buy/<role>')
def buy_role(role):
    if 'user' in session:
        user_roles[session['user']] = role
        online_users[session['user']] = get_timestamp()
    return redirect(url_for('index'))

def get_timestamp():
    from datetime import datetime
    return datetime.now().timestamp()

def calculate_online_stats():
    now = get_timestamp()
    stats = {'start': 0, 'vip': 0, 'premium': 0, 'admin': 0, 'total': 0}
    
    for username, timestamp in online_users.items():
        if now - timestamp < 300:  # 5 минут
            role = user_roles.get(username, 'start')
            stats['total'] += 1
            if users.get(username, {}).get('admin'):
                stats['admin'] += 1
            elif role == 'premium':
                stats['premium'] += 1
            elif role == 'vip':
                stats['vip'] += 1
            else:
                stats['start'] += 1
    return stats

@app.route('/profile')
def profile():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    user = session['user']
    role = user_roles.get(user, 'start')
    stats = calculate_online_stats()
    
    return f'''
    <!DOCTYPE html>
    <html><head><title>Профиль {user}</title>
    <style>body{{font-family:Arial;padding:50px;background:#f8f9fa;}}
    .profile-card{{background:white;max-width:500px;margin:auto;padding:30px;border-radius:15px;box-shadow:0 10px 30px rgba(0,0,0,0.1);}}</style></head>
    <body>
    <div class="profile-card">
        <h1>👤 {user}</h1>
        <h2 style="color:#007bff;">Роль: {role.upper()}</h2>
        <p><b>Онлайн:</b> {stats['total']} пользователей</p>
        <div style="margin:20px 0;padding:15px;background:#e9ecef;border-radius:10px;">
            📊 Start: {stats['start']} | VIP: {stats['vip']} | Premium: {stats['premium']} | Admin: {stats['admin']}
        </div>
        <a href="/" style="background:#28a745;color:white;padding:12px 25px;border-radius:5px;">🏠 Главная</a>
    </div>
    </body></html>
    '''

@app.route('/catalog')
def catalog():
    html = '''
    <!DOCTYPE html>
    <html><head><title>Каталог</title>
    <meta charset="utf-8">
    <style>body{font-family:Arial;padding:20px;background:#f8f9fa;}
    .category{background:#fff;margin:15px;padding:20px;border-radius:10px;box-shadow:0 5px 15px rgba(0,0,0,0.1);cursor:pointer;}
    .subcategory{background:#e9ecef;margin:10px 20px;padding:15px;border-radius:8px;}
    .item{background:#f8f9fa;margin:8px 15px;padding:12px;border-radius:5px;}
    a{color:#007bff;text-decoration:none;}</style></head>
    <body>
    <h1 style="text-align:center;">📁 КАТАЛОГ</h1>
    <div style="text-align:center;margin:20px;">
        <a href="/" style="background:#6c757d;color:white;padding:12px 25px;border-radius:5px;">🏠 Главная</a>
    </div>
    '''
    
    current_user = session.get('user')
    if current_user and users.get(current_user, {}).get('admin'):
        html += '<div style="text-align:center;margin:20px;"><a href="/admin" style="background:#dc3545;color:white;padding:12px 25px;border-radius:5px;">🔧 Админ панель</a></div>'
    
    # Главные категории
    for main_cat in ['Minecraft', 'World of Tanks']:
        html += f'''
        <div class="category">
            <h2>📁 {main_cat}</h2>
        '''
        # Подкатегории
        for sub_cat in categories.get(main_cat, []):
            full_path = f"{main_cat}/{sub_cat}"
            html += f'''
            <div class="subcategory">
                <h3>📂 {sub_cat}</h3>
            '''
            # Элементы
            for item in category_contents.get(full_path, []):
                html += f'<div class="item">📄 {item}</div>'
            html += '</div>'
        html += '</div>'
    
    html += '</body></html>'
    return html

@app.route('/community')
def community():
    return '''
    <!DOCTYPE html>
    <html><head><title>Сообщество</title>
    <style>body{font-family:Arial;padding:50px;text-align:center;background:#f8f9fa;}</style></head>
    <body>
    <h1>💬 Сообщество Узнавайкин</h1>
    <h2><a href="https://t.me/ssylkanatelegramkanalyznaikin" style="color:#0088cc;font-size:24px;">🚀 Telegram канал</a></h2>
    <p style="margin:30px 0;font-size:18px;">Присоединяйся к нам!</p>
    <a href="/" style="background:#28a745;color:white;padding:15px 30px;border-radius:5px;">🏠 На главную</a>
    </body></html>
    '''

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    current_user = session.get('user')
    if not current_user or not users.get(current_user, {}).get('admin'):
        return '<h1 style="color:red;">❌ Только для админов!</h1><a href="/">Главная</a>'
    
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add_category':
            name = request.form['name'].strip()
            parent = request.form.get('parent', '').strip()
            if name and parent:
                full_path = f"{parent}/{name}"
                if parent not in categories:
                    categories[parent] = []
                category_contents[full_path] = []
                return redirect(url_for('admin'))
            elif name:
                categories[name] = []
                return redirect(url_for('admin'))
        
        elif action == 'add_info':
            title = request.form['title'].strip()
            folder = request.form['folder'].strip()
            info = request.form['info'].strip()
            photo = request.form.get('photo', '').strip()
            if title and folder:
                if folder not in category_contents:
                    category_contents[folder] = []
                category_contents[folder].append({
                    'title': title, 
                    'info': info, 
                    'photo': photo
                })
                return redirect(url_for('admin'))
    
    html = '''
    <!DOCTYPE html>
    <html><head><title>Админ</title>
    <style>body{font-family:Arial;padding:30px;background:#f8f9fa;}
    .section{background:white;margin:20px 0;padding:25px;border-radius:10px;box-shadow:0 5px 15px rgba(0,0,0,0.1);}
    input,textarea,select{width:100%;padding:12px;margin:8px 0;border:2px solid #ddd;border-radius:5px;box-sizing:border-box;}
    button{{padding:12px 25px;background:#dc3545;color:white;border:none;border-radius:5px;cursor:pointer;}}</style></head>
    <body>
    '''
    
    html += f'''
    <h1>🔧 Админ панель ({current_user})</h1>
    <a href="/" style="background:#28a745;color:white;padding:12px 25px;border-radius:5px;">🏠 Главная</a>
    
    <div class="section">
        <h2>➕ Добавить категорию</h2>
        <form method="post">
            <input name="name" placeholder="Название категории (Блоки)" required>
            <select name="parent">
                <option value="">Корневая категория</option>
                <option value="Minecraft">Minecraft</option>
                <option value="World of Tanks">World of Tanks</option>
            </select>
            <input type="hidden" name="action" value="add_category">
            <button>📁 ДОБАВИТЬ КАТЕГОРИЮ</button>
        </form>
    </div>
    
    <div class="section">
        <h2>➕ Добавить информацию</h2>
        <form method="post">
            <input name="title" placeholder="Название (Т-34)" required>
            <select name="folder">
                <option value="">Выберите папку...</option>
    '''
    
    # Список всех папок
    for full_path in category_contents.keys():
        html += f'<option value="{full_path}">{full_path}</option>'
    
    html += '''
            </select>
            <textarea name="info" placeholder="Информация..." rows="4"></textarea>
            <input name="photo" placeholder="Ссылка на фото (не обязательно)">
            <input type="hidden" name="action" value="add_info">
            <button>📄 ДОБАВИТЬ ИНФОРМАЦИЮ</button>
        </form>
    </div>
    '''
    
    html += '</body></html>'
    return html

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0')
