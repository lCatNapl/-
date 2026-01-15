from flask import Flask, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = 'uznavaykin-2026-super-secret'

# Фейковые данные в памяти
users = {
    'CatNap': {'password': '120187', 'role': 'premium', 'admin': True},
    'Назар': {'password': '120187', 'role': 'premium', 'admin': True}
}
user_roles = {}
categories = ['Minecraft', 'World of Tanks', 'Блоки', 'Танки', 'СССР', 'Германия']

@app.route('/', methods=['GET', 'POST'])
def index():
    current_user = session.get('user')
    stats = {'total': 3, 'start': 2, 'vip': 0, 'premium': 1, 'admin': 2}
    
    html = '''
    <!DOCTYPE html>
    <html><head><title>Узнавайкин</title>
    <meta charset="utf-8">
    <style>body{font-family:Arial;padding:20px;max-width:800px;margin:auto;}</style></head>
    <body>
    '''
    
    if current_user:
        role = user_roles.get(current_user, 'start')
        html += f'''
        <h1>🏠 Узнавайкин</h1>
        <p>👤 <b>{current_user}</b> ({role.upper()}) 
        | <a href="/profile">👤 Профиль</a> | <a href="/logout">🚪 Выход</a></p>
        '''
        if role != 'premium':
            html += '''
            <p><a href="/buy/vip" style="background:blue;color:white;padding:10px;">[VIP 100₽]</a> 
            <a href="/buy/premium" style="background:gold;color:black;padding:10px;">[PREMIUM 200₽]</a></p>
            '''
    else:
        html += '''
        <h1>🏠 Узнавайкин</h1>
        <p><a href="/login" style="background:green;color:white;padding:10px;">🔐 ВОЙТИ</a> 
        | <a href="/register" style="background:orange;color:white;padding:10px;">📝 РЕГИСТРАЦИЯ</a></p>
        '''
    
    html += f'''
        <p><b>👥 Онлайн:</b> {stats['total']} (S:{stats['start']} V:{stats['vip']} P:{stats['premium']} A:{stats['admin']})</p>
        <hr>
        <p><a href="/catalog">📁 Каталог</a> | <a href="/community">💬 Telegram</a></p>
    '''
    
    if current_user and users.get(current_user, {}).get('admin'):
        html += '<p><a href="/admin" style="background:red;color:white;padding:10px;">🔧 АДМИН ПАНЕЛЬ</a></p>'
    
    html += '</body></html>'
    return html

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if username in users and users[username]['password'] == password:
            session['user'] = username
            user_roles[username] = users[username]['role']
            return redirect(url_for('index'))
        elif username not in users:
            # Регистрация новых
            users[username] = {'password': password, 'role': 'start', 'admin': False}
            user_roles[username] = 'start'
            session['user'] = username
            return redirect(url_for('index'))
        
        return '''
        <!DOCTYPE html>
        <html><head><title>Ошибка</title></head><body>
        <h2>❌ Неверный логин/пароль!</h2>
        <a href="/login">← Назад</a>
        </body></html>
        '''
    
    return '''
    <!DOCTYPE html>
    <html><head><title>Вход</title>
    <style>body{font-family:Arial;padding:50px;text-align:center;}</style></head>
    <body>
    <h1>🔐 Вход / Регистрация</h1>
    <form method="post" style="max-width:300px;margin:auto;">
        <p>Логин: <input name="username" style="width:100%;padding:10px;" required></p>
        <p>Пароль: <input name="password" type="password" style="width:100%;padding:10px;" required></p>
        <button style="width:100%;padding:15px;background:green;color:white;border:none;font-size:18px;">ВОЙТИ</button>
    </form>
    <p><small>Админы: CatNap / 120187 | Назар / 120187</small></p>
    </body></html>
    '''

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('index'))

@app.route('/buy/<role>')
def buy_role(role):
    if 'user' in session:
        user_roles[session['user']] = role
    return redirect(url_for('index'))

@app.route('/profile')
def profile():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    user = session['user']
    role = user_roles.get(user, 'start')
    return f'''
    <!DOCTYPE html>
    <html><head><title>Профиль</title></head><body style="font-family:Arial;padding:50px;">
    <h1>👤 {user}</h1>
    <h2>Роль: <span style="color:gold;">{role.upper()}</span></h2>
    <p><a href="/">🏠 Главная</a></p>
    </body></html>
    '''

@app.route('/catalog')
def catalog():
    html = '''
    <!DOCTYPE html>
    <html><head><title>Каталог</title></head><body style="font-family:Arial;padding:20px;">
    <h1>📁 Каталог</h1>
    <a href="/">🏠 Главная</a>
    '''
    
    for i, cat in enumerate(categories):
        html += f'''
        <div style="margin:20px;border:2px solid #ccc;padding:20px;border-radius:10px;">
            📁 <b>{cat}</b>
        </div>
        '''
    
    html += '</body></html>'
    return html

@app.route('/community')
def community():
    return '''
    <!DOCTYPE html>
    <html><head><title>Сообщество</title></head><body style="font-family:Arial;padding:50px;text-align:center;">
    <h1>💬 Сообщество</h1>
    <h2><a href="https://t.me/ssylkanatelegramkanalyznaikin" style="color:blue;">Telegram канал</a></h2>
    <p><a href="/">🏠 Главная</a></p>
    </body></html>
    '''

@app.route('/admin')
def admin():
    if 'user' not in session or not users.get(session['user'], {}).get('admin'):
        return '<h1>❌ Только для админов!</h1><a href="/">Главная</a>'
    
    return '''
    <!DOCTYPE html>
    <html><head><title>Админ</title></head><body style="font-family:Arial;padding:50px;">
    <h1>🔧 Админ панель</h1>
    <p>Добавляй категории:</p>
    <form method="post" action="/admin/add">
        <input name="category" placeholder="Название категории">
        <button>Добавить</button>
    </form>
    <p><a href="/">🏠 Главная</a></p>
    </body></html>
    '''

@app.route('/admin/add', methods=['POST'])
def admin_add():
    if 'user' in session and users.get(session['user'], {}).get('admin'):
        new_cat = request.form['category']
        if new_cat:
            categories.append(new_cat)
    
    return redirect(url_for('admin'))

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0')
