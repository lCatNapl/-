from flask import Flask, render_template, request, jsonify
import sqlite3
import json
import re

app = Flask(__name__)
app.config['SECRET_KEY'] = 'uznayakin-2026'

def init_db():
    conn = sqlite3.connect('games.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS games (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,
        description TEXT,
        icon TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        game_id INTEGER,
        name TEXT,
        parent_id INTEGER DEFAULT 0,
        description TEXT,
        FOREIGN KEY(game_id) REFERENCES games(id)
    )''')
    
    # Заполняем БД
    games_data = [
        ('Minecraft', 'Песочница с блоками и выживанием', '🟫'),
        ('World of Tanks', 'Командные бои на танках', '🛡️')
    ]
    c.executemany("INSERT OR IGNORE INTO games (name, description, icon) VALUES (?, ?, ?)", games_data)
    
    # Получаем ID игр
    c.execute("SELECT id FROM games WHERE name='Minecraft'")
    mc_id = c.fetchone()[0]
    c.execute("SELECT id FROM games WHERE name='World of Tanks'")
    wot_id = c.fetchone()[0]
    
    # Категории
    categories = [
        # Minecraft
        (mc_id, 'Блоки', 0, 'Все блоки Minecraft'),
        (mc_id, 'Биомы', 0, 'Типы миров и ландшафты'),
        (mc_id, 'Камень', 1, 'Каменные блоки'),
        (mc_id, 'Дерево', 1, 'Деревянные блоки'),
        (mc_id, 'Лес', 2, 'Обычный лесной биом'),
        (mc_id, 'Пустыня', 2, 'Песчаные просторы'),
        # World of Tanks
        (wot_id, 'Танки', 0, 'Все танки по нациям'),
        (wot_id, '1 уровень', 1, 'Легчайшие танки'),
        (wot_id, 'СССР', 1, 'Советская техника'),
        (wot_id, 'Германия', 1, 'Немецкие танки')
    ]
    c.executemany("INSERT OR IGNORE INTO categories (game_id, name, parent_id, description) VALUES (?, ?, ?, ?)", categories)
    
    conn.commit()
    conn.close()

def translate_query(query):
    """Переводы для поиска"""
    translations = {
        'minecraft': 'майнкрафт mine блок block',
        'mine': 'шахта майнкрафт',
        'block': 'блок камень дерево',
        'tank': 'танк танк',
        'wot': 'танки world of tanks',
        'биом': 'biome лес пустыня',
        'лес': 'forest биом',
        'пустыня': 'desert биом'
    }
    result = query
    for eng, rus in translations.items():
        if eng in query.lower():
            result += ' ' + rus
    return result

@app.route('/')
def index():
    query = request.args.get('q', '').lower().strip()
    conn = sqlite3.connect('games.db')
    c = conn.cursor()
    
    if query:
        # УМНЫЙ ПОИСК
        search_results = []
        
        # Поиск игр
        c.execute("SELECT id, name, description, icon FROM games WHERE LOWER(name) LIKE ? OR LOWER(name) LIKE ?",
                 (f'%{query}%', f'%{translate_query(query)}%'))
        search_results.extend([{'type': 'game', **dict(row)} for row in c.fetchall()])
        
        # Поиск категорий
        c.execute("""
            SELECT g.id as game_id, g.name as game_name, g.icon, c.id as cat_id, c.name, c.description, 'category' as type
            FROM categories c JOIN games g ON c.game_id = g.id 
            WHERE LOWER(c.name) LIKE ? OR LOWER(c.description) LIKE ? OR LOWER(g.name) LIKE ?
        """, (f'%{query}%', f'%{query}%', f'%{query}%'))
        search_results.extend([dict(row) for row in c.fetchall()])
        
        conn.close()
        return render_template('index.html', games=search_results, query=query, is_search=True)
    
    # Все игры
    c.execute("SELECT id, name, description, icon FROM games")
    games = c.fetchall()
    conn.close()
    return render_template('index.html', games=games, query='', is_search=False)

@app.route('/game/<int:game_id>')
def game_page(game_id):
    conn = sqlite3.connect('games.db')
    c = conn.cursor()
    c.execute("SELECT name, description, icon FROM games WHERE id=?", (game_id,))
    game = c.fetchone()
    c.execute("SELECT id, name, description FROM categories WHERE game_id=? AND parent_id=0", (game_id,))
    main_cats = c.fetchall()
    conn.close()
    return render_template('category.html', game=game, main_cats=main_cats, game_id=game_id)

@app.route('/api/search')
def api_search():
    query = request.args.get('q', '')
    # AJAX поиск (для живого поиска)
    return jsonify({'results': []})

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000, host='0.0.0.0')
