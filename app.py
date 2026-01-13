from flask import Flask, render_template, request
import sqlite3
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'uznayakin-2026'

DB_PATH = 'games.db'


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    # Если файла ещё нет — создаём и заполняем
    need_seed = not os.path.exists(DB_PATH)

    conn = get_db_connection()
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
        description TEXT
    )''')

    if need_seed:
        # Первичное заполнение
        games_data = [
            ('Minecraft', 'Бесконечный мир из блоков', '🟫'),
            ('World of Tanks', 'Эпические танковые бои', '🛡️'),
            ('Tetris', 'Классическая головоломка', '🟦'),
            ('Dota 2', 'Командная стратегия на 5х5', '⚔️')
        ]
        c.executemany(
            "INSERT OR IGNORE INTO games (name, description, icon) VALUES (?, ?, ?)",
            games_data
        )

        # Получаем id игр
        c.execute("SELECT id, name FROM games")
        ids = {row['name']: row['id'] for row in c.fetchall()}

        categories = [
            # Minecraft
            (ids.get('Minecraft'), 'Блоки', 0, 'Все виды блоков'),
            (ids.get('Minecraft'), 'Биомы', 0, 'Разные типы миров'),
            (ids.get('Minecraft'), 'Камень', 1, 'Каменные блоки'),
            (ids.get('Minecraft'), 'Дерево', 1, 'Деревянные блоки'),
            (ids.get('Minecraft'), 'Лес', 2, 'Лесной биом'),
            (ids.get('Minecraft'), 'Пустыня', 2, 'Песчаный биом'),

            # World of Tanks
            (ids.get('World of Tanks'), 'Танки', 0, 'Все танки по нациям'),
            (ids.get('World of Tanks'), '1 уровень', 1, 'Стартовые танки'),
            (ids.get('World of Tanks'), 'СССР', 1, 'Советская техника'),
            (ids.get('World of Tanks'), 'Германия', 1, 'Немецкие танки'),
        ]

        c.executemany(
            "INSERT OR IGNORE INTO categories (game_id, name, parent_id, description) VALUES (?, ?, ?, ?)",
            categories
        )

    conn.commit()
    conn.close()


def smart_search(query: str) -> str:
    """Расширение запроса простыми «переводами»."""
    translations = {
        'блок': 'block stone wood',
        'block': 'блок камень дерево',
        'танк': 'tank wot',
        'tank': 'танк world of tanks',
        'биом': 'biome лес пустыня',
        'лес': 'forest biome',
        'пустыня': 'desert biome',
        'mine': 'minecraft майнкрафт',
        'майн': 'minecraft mine',
    }
    expanded = query
    low = query.lower()
    for key, extra in translations.items():
        if key in low:
            expanded += ' ' + extra
    return expanded


@app.before_request
def ensure_db():
    # На Render при первом запросе БД может ещё не быть — создаём/обновляем
    if not os.path.exists(DB_PATH):
        init_db()


@app.route('/')
def index():
    query = request.args.get('q', '').strip()
    conn = get_db_connection()
    c = conn.cursor()

    if query:
        q = query.lower()
        expanded = smart_search(q)

        # Поиск по играм
        c.execute("""
            SELECT id, name, description, icon
            FROM games
            WHERE LOWER(name) LIKE ? OR LOWER(description) LIKE ?
        """, (f'%{q}%', f'%{expanded}%'))
        games = c.fetchall()

        # Поиск по категориям (какие игры связаны)
        c.execute("""
            SELECT DISTINCT g.id, g.name, g.description, g.icon
            FROM games g
            JOIN categories c ON g.id = c.game_id
            WHERE LOWER(c.name) LIKE ? OR LOWER(c.description) LIKE ?
        """, (f'%{q}%', f'%{expanded}%'))
        via_cats = c.fetchall()

        # Объединяем и убираем дубли по id
        all_rows = {row['id']: row for row in games}
        for row in via_cats:
            all_rows[row['id']] = row

        conn.close()
        return render_template(
            'index.html',
            games=list(all_rows.values()),
            query=query,
            is_search=True
        )

    # Без поиска: просто список всех игр
    c.execute("SELECT id, name, description, icon FROM games ORDER BY name")
    games = c.fetchall()
    conn.close()
    return render_template(
        'index.html',
        games=games,
        query='',
        is_search=False
    )


@app.route('/game/<int:game_id>')
def game_page(game_id):
    conn = get_db_connection()
    c = conn.cursor()

    c.execute("SELECT name, description, icon FROM games WHERE id=?", (game_id,))
    game = c.fetchone()

    if not game:
        conn.close()
        return "Игра не найдена", 404

    c.execute("""
        SELECT id, name, description
        FROM categories
        WHERE game_id=? AND parent_id=0
        ORDER BY name
    """, (game_id,))
    main_cats = c.fetchall()

    conn.close()
    return render_template(
        'category.html',
        game=game,
        main_cats=main_cats,
        game_id=game_id
    )


if __name__ == '__main__':
    # Локальный запуск
    init_db()
    app.run(debug=True, port=5000, host='0.0.0.0')
